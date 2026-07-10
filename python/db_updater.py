#!/usr/bin/env python3
"""
db_updater.py — Scrive nel database MySQL/MariaDB del sito i dati normalizzati
prodotti da acquire_results.py e acquire_party_codes.py.

Legge le coppie di file in data/processed/:
  mef_results_<anno>.csv   + mef_results_<anno>.meta.json
  ade_codes_<anno>.csv     + ade_codes_<anno>.meta.json

Per ciascuna:
  1. registra (o riusa, per checksum) la fonte in `sources`;
  2. upsert del partito in `parties` per slug (estendendo first_year/last_year);
  3. upsert della riga in `results` o `party_codes` (chiave unica
     party_id+declaration_year, stessa logica di scripts/import_results.php).

Non calcola quote/ranking/medie: quello resta compito di
scripts/calculate_indicators.php (unica fonte di verità per quei calcoli,
condivisa con l'import via CSV lato PHP). Vedi pipeline.py per l'orchestrazione
completa (acquisizione → DB → indicatori → export).

Uso:
    python db_updater.py                 # tutti i file in data/processed/
    python db_updater.py --anni 2024      # solo l'anno 2024
    python db_updater.py --dry-run        # mostra cosa farebbe, senza scrivere
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

from common import REPO_ROOT, get_logger, load_dotenv, slugify
from db import db_available, get_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------

def upsert_source(cur, meta: dict, title: str) -> int:
    """Registra la fonte se non già presente (dedup per checksum), restituisce l'id."""
    checksum = meta.get("checksum")
    if checksum:
        cur.execute("SELECT id FROM sources WHERE checksum = %s LIMIT 1", (checksum,))
        row = cur.fetchone()
        if row:
            return row[0]

    cur.execute(
        """
        INSERT INTO sources (institution, title, url, source_type, download_date, checksum, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            meta.get("institution"),
            title,
            meta.get("url"),
            meta.get("source_type", "altro"),
            meta.get("download_date"),
            checksum,
            f"Acquisito automaticamente da {meta.get('source_file')} "
            f"({meta.get('row_count')} righe) via pipeline Python.",
        ),
    )
    return cur.lastrowid


def upsert_party(cur, canonical_name: str, declaration_year: int) -> int:
    """
    Trova il partito per slug o lo crea. Estende first_year/last_year per
    includere l'anno appena elaborato.
    """
    slug = slugify(canonical_name)
    cur.execute("SELECT id, first_year, last_year FROM parties WHERE slug = %s LIMIT 1", (slug,))
    row = cur.fetchone()

    if row is None:
        cur.execute(
            """
            INSERT INTO parties (canonical_name, slug, first_year, last_year, is_active)
            VALUES (%s, %s, %s, %s, 1)
            """,
            (canonical_name, slug, declaration_year, declaration_year),
        )
        return cur.lastrowid

    party_id, first_year, last_year = row
    new_first = min(first_year, declaration_year) if first_year else declaration_year
    new_last = max(last_year, declaration_year) if last_year else declaration_year
    if new_first != first_year or new_last != last_year:
        cur.execute(
            "UPDATE parties SET first_year = %s, last_year = %s WHERE id = %s",
            (new_first, new_last, party_id),
        )
    return party_id


def upsert_result(cur, party_id: int, declaration_year: int, tax_year: int,
                   valid_choices: int, amount: float, source_id: "int | None") -> None:
    cur.execute(
        """
        INSERT INTO results (party_id, declaration_year, tax_year, valid_choices, amount, source_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            tax_year = VALUES(tax_year),
            valid_choices = VALUES(valid_choices),
            amount = VALUES(amount),
            source_id = VALUES(source_id)
        """,
        (party_id, declaration_year, tax_year, valid_choices, amount, source_id),
    )


def upsert_annual_totals_external(
    cur, declaration_year: int, tax_year: int,
    total_taxpayers: "int | None", number_of_parties_admitted: "int | None",
    source_id: "int | None",
) -> None:
    """
    Registra i valori di annual_totals che sono input esterni non derivabili
    dai soli dati di `results` (totale contribuenti dichiaranti, numero di
    partiti ammessi al beneficio nell'anno). Gli altri campi della tabella
    (quote, ranking, concentrazione) restano compito esclusivo di
    scripts/calculate_indicators.php, per non avere due punti che scrivono lo
    stesso dato con logiche diverse.
    """
    if total_taxpayers is None and number_of_parties_admitted is None:
        return
    cur.execute(
        """
        INSERT INTO annual_totals (declaration_year, tax_year, total_taxpayers, number_of_parties_admitted, source_id)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            total_taxpayers = COALESCE(VALUES(total_taxpayers), annual_totals.total_taxpayers),
            number_of_parties_admitted = COALESCE(VALUES(number_of_parties_admitted), annual_totals.number_of_parties_admitted),
            source_id = COALESCE(annual_totals.source_id, VALUES(source_id))
        """,
        (declaration_year, tax_year, total_taxpayers, number_of_parties_admitted, source_id),
    )


def count_admitted_parties(cur, declaration_year: int) -> "int | None":
    """Numero di partiti ammessi nell'anno: la dimensione dell'elenco codici AdE per quell'anno."""
    cur.execute("SELECT COUNT(*) FROM party_codes WHERE declaration_year = %s", (declaration_year,))
    row = cur.fetchone()
    count = row[0] if row else 0
    return count or None


def upsert_party_code(cur, party_id: int, declaration_year: int, tax_year: int,
                       code: str, official_name: str, source_id: "int | None") -> None:
    cur.execute(
        """
        INSERT INTO party_codes (party_id, declaration_year, tax_year, code, official_name, source_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            tax_year = VALUES(tax_year),
            code = VALUES(code),
            official_name = VALUES(official_name),
            source_id = VALUES(source_id)
        """,
        (party_id, declaration_year, tax_year, code, official_name, source_id),
    )


def upsert_regional_result(cur, party_id: int, declaration_year: int, tax_year: int,
                            region: str, valid_choices: "int | None", is_suppressed: bool,
                            source_id: "int | None") -> None:
    cur.execute(
        """
        INSERT INTO regional_results (party_id, declaration_year, tax_year, region, valid_choices, is_suppressed, source_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            tax_year = VALUES(tax_year),
            valid_choices = VALUES(valid_choices),
            is_suppressed = VALUES(is_suppressed),
            source_id = VALUES(source_id)
        """,
        (party_id, declaration_year, tax_year, region, valid_choices, 1 if is_suppressed else 0, source_id),
    )


def build_party_name_index(cur) -> "dict[str, int]":
    """
    Costruisce l'indice slug(nome) -> party_id usato per risolvere i nomi
    partito nei file che non hanno una colonna codice (es. la ripartizione
    regionale, che intesta le colonne col nome del partito). Le fonti del
    nome, in ordine di popolamento (le successive non sovrascrivono le
    precedenti se già presente lo stesso slug):
      1. parties.canonical_name
      2. party_codes.official_name (la dicitura esatta usata dall'AdE quell'anno)
      3. party_aliases.alias_name (grafie storiche registrate a mano o da merge_parties.py)
    """
    index: dict[str, int] = {}

    cur.execute("SELECT id, canonical_name FROM parties")
    for party_id, name in cur.fetchall():
        index.setdefault(slugify(name), party_id)

    cur.execute("SELECT party_id, official_name FROM party_codes")
    for party_id, name in cur.fetchall():
        index.setdefault(slugify(name), party_id)

    cur.execute("SELECT party_id, alias_name FROM party_aliases")
    for party_id, name in cur.fetchall():
        index.setdefault(slugify(name), party_id)

    return index


# ---------------------------------------------------------------------------
# Elaborazione file
# ---------------------------------------------------------------------------

def _load_meta(csv_path: Path) -> dict:
    # mef_results_2024.csv -> mef_results_2024.meta.json
    meta_path = csv_path.parent / (csv_path.stem + ".meta.json")
    if meta_path.is_file():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {}


def process_results_file(cur, csv_path: Path, dry_run: bool) -> int:
    meta = _load_meta(csv_path)
    declaration_year = meta.get("declaration_year")

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        logger.warning(f"{csv_path.name}: nessuna riga")
        return 0

    declaration_year = declaration_year or int(rows[0]["declaration_year"])
    title = f"Risultati 2x1000 ai partiti politici — dichiarazione {declaration_year}"

    if dry_run:
        logger.info(f"[DRY-RUN] {csv_path.name}: {len(rows)} righe (source={meta.get('institution')})")
        return len(rows)

    source_id = upsert_source(cur, meta, title) if meta else None

    count = 0
    for row in rows:
        party_id = upsert_party(cur, row["party_name"], int(row["declaration_year"]))
        upsert_result(
            cur,
            party_id,
            int(row["declaration_year"]),
            int(row["tax_year"]),
            int(row["valid_choices"]),
            float(row["amount"]),
            source_id,
        )
        count += 1

    tax_year = meta.get("tax_year") or int(rows[0]["tax_year"])
    upsert_annual_totals_external(cur, declaration_year, tax_year, meta.get("total_taxpayers"), None, source_id)

    logger.info(f"{csv_path.name}: {count} risultati aggiornati (anno {declaration_year})")
    return count


def process_codes_file(cur, csv_path: Path, dry_run: bool) -> int:
    meta = _load_meta(csv_path)

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        logger.warning(f"{csv_path.name}: nessuna riga")
        return 0

    declaration_year = meta.get("declaration_year") or int(rows[0]["declaration_year"])
    title = f"Elenco partiti ammessi e codici dichiarazione — {declaration_year}"

    if dry_run:
        logger.info(f"[DRY-RUN] {csv_path.name}: {len(rows)} righe (source={meta.get('institution')})")
        return len(rows)

    source_id = upsert_source(cur, meta, title) if meta else None

    count = 0
    for row in rows:
        party_id = upsert_party(cur, row["official_name"], int(row["declaration_year"]))
        upsert_party_code(
            cur,
            party_id,
            int(row["declaration_year"]),
            int(row["tax_year"]),
            row["code"],
            row["official_name"],
            source_id,
        )
        count += 1

    tax_year = meta.get("tax_year") or int(rows[0]["tax_year"])
    number_of_parties_admitted = count_admitted_parties(cur, declaration_year)
    upsert_annual_totals_external(cur, declaration_year, tax_year, None, number_of_parties_admitted, source_id)

    logger.info(f"{csv_path.name}: {count} codici aggiornati (anno {declaration_year})")
    return count


def process_regional_file(cur, csv_path: Path, dry_run: bool, name_index: "dict[str, int] | None" = None,
                           unresolved: "set[str] | None" = None) -> int:
    """
    name_index: da build_party_name_index(), obbligatorio quando dry_run=False.
    unresolved: set (mutato in place) dove si accumulano i nomi partito che
    non sono stati trovati in name_index, per il report finale — le righe
    corrispondenti vengono scartate, non inventano un partito nuovo.
    """
    meta = _load_meta(csv_path)

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        logger.warning(f"{csv_path.name}: nessuna riga")
        return 0

    declaration_year = meta.get("declaration_year") or int(rows[0]["declaration_year"])
    title = f"Ripartizione regionale delle scelte 2x1000 — dichiarazione {declaration_year}"

    if dry_run:
        logger.info(f"[DRY-RUN] {csv_path.name}: {len(rows)} righe (source={meta.get('institution')})")
        return len(rows)

    source_id = upsert_source(cur, meta, title) if meta else None

    count = 0
    skipped_unresolved = 0
    for row in rows:
        slug = slugify(row["party_name"])
        party_id = name_index.get(slug)
        if party_id is None:
            if unresolved is not None:
                unresolved.add(row["party_name"])
            skipped_unresolved += 1
            continue

        valid_choices = int(row["valid_choices"]) if row["valid_choices"] not in (None, "") else None
        upsert_regional_result(
            cur,
            party_id,
            int(row["declaration_year"]),
            int(row["tax_year"]),
            row["region"],
            valid_choices,
            row["is_suppressed"] in ("1", "True", "true"),
            source_id,
        )
        count += 1

    if skipped_unresolved:
        logger.warning(
            f"{csv_path.name}: {skipped_unresolved} righe scartate per nome partito non riconosciuto "
            f"(vedi elenco a fine esecuzione)"
        )
    logger.info(f"{csv_path.name}: {count} righe di ripartizione regionale aggiornate (anno {declaration_year})")
    return count


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="2x1000 — Scrive nel database i dati normalizzati acquisiti dalle fonti ufficiali",
    )
    parser.add_argument("--anni", type=str, default=None,
                         help="Limita agli anni indicati, separati da virgola (es. 2023,2024)")
    parser.add_argument("--processed-dir", type=str, default=None,
                         help="Cartella con i CSV normalizzati (default: data/processed/)")
    parser.add_argument("--dry-run", action="store_true",
                         help="Analizza i file senza scrivere nulla nel database")
    return parser.parse_args()


def main():
    args = parse_args()
    get_logger("db_updater", Path(__file__).resolve().parent)
    load_dotenv()

    processed_dir = Path(args.processed_dir) if args.processed_dir else REPO_ROOT / "data" / "processed"
    years = None
    if args.anni:
        years = {int(a.strip()) for a in args.anni.split(",") if a.strip()}

    def _year_of(path: Path) -> "int | None":
        try:
            return int(path.stem.rsplit("_", 1)[-1])
        except ValueError:
            return None

    results_files = sorted(p for p in processed_dir.glob("mef_results_*.csv") if not years or _year_of(p) in years)
    codes_files = sorted(p for p in processed_dir.glob("ade_codes_*.csv") if not years or _year_of(p) in years)
    regional_files = sorted(p for p in processed_dir.glob("regional_results_*.csv") if not years or _year_of(p) in years)

    if not results_files and not codes_files and not regional_files:
        logging.warning(f"Nessun file trovato in {processed_dir} (filtro anni: {years or 'tutti'})")
        sys.exit(1)

    if args.dry_run:
        total = 0
        for f in results_files:
            total += process_results_file(None, f, dry_run=True)
        for f in codes_files:
            total += process_codes_file(None, f, dry_run=True)
        for f in regional_files:
            total += process_regional_file(None, f, dry_run=True)
        logging.info(f"[DRY-RUN] Totale righe che verrebbero elaborate: {total}")
        return

    if not db_available():
        logging.error(
            "Database non configurato o pymysql non installato. "
            "Verifica .env (DB_HOST/DB_NAME/DB_USER/DB_PASS) e 'pip install pymysql'."
        )
        sys.exit(1)

    conn = get_connection()
    total = 0
    unresolved: set[str] = set()
    try:
        with conn.cursor() as cur:
            for f in results_files:
                total += process_results_file(cur, f, dry_run=False)
            for f in codes_files:
                total += process_codes_file(cur, f, dry_run=False)

            if regional_files:
                # Costruito qui, dopo results/codes: vede anche i partiti e i
                # codici scritti in questa stessa esecuzione (stessa
                # transazione, non serve un commit intermedio).
                name_index = build_party_name_index(cur)
                for f in regional_files:
                    total += process_regional_file(cur, f, dry_run=False, name_index=name_index, unresolved=unresolved)

        conn.commit()
        logging.info(f"Completato: {total} righe scritte nel database (commit ok)")

        if unresolved:
            logging.warning(
                f"{len(unresolved)} nomi partito nella ripartizione regionale non sono stati riconosciuti "
                f"e le relative righe sono state SCARTATE. Se sono varianti di partiti già in anagrafica, "
                f"registra un alias e rilancia:"
            )
            for name in sorted(unresolved):
                logging.warning(f"  - {name!r}")
            logging.warning(
                "  python add_party_alias.py --party <slug-corretto> --alias \"<nome esatto sopra>\""
            )
    except Exception:
        conn.rollback()
        logging.error("Errore durante la scrittura: rollback eseguito", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
