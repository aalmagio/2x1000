#!/usr/bin/env python3
"""
sync_party_aliases.py — Esporta/importa gli alias dei partiti da/verso
data/reference/party_aliases.csv, l'archivio versionato del progetto.

Gli alias (grafie alternative dei partiti, create con add_party_alias.py o
dai merge di merge_parties.py) vivono nel database: senza un export, quel
lavoro di pulizia manuale esisterebbe solo lì e andrebbe rifatto da zero su
ogni nuova installazione. Questo script li rende un asset del repository:

  --export   database -> data/reference/party_aliases.csv (da committare)
  --import   data/reference/party_aliases.csv -> database (upsert, mai delete)

Sul primo `db_updater.py` di un'installazione da zero, `party_aliases` è
ancora vuota: l'euristica di risoluzione dei nomi ricrea come partiti nuovi
proprio le grafie che i merge storici avevano già unito. Per questo
`--import` non si limita a scrivere gli alias: prima verifica se lo slug di
un `alias_name` corrisponde a un partito realmente esistente diverso da
quello di destinazione e, in quel caso, lo unisce con la stessa logica di
`merge_parties.py` (spostando risultati/codici/ripartizione regionale,
bloccandosi se ci sono conflitti da risolvere a mano).

Il CSV usa lo slug del partito (stabile tra installazioni) e non l'id.
Flusso di ricostruzione di un database da zero, senza toccare AdE/MEF:

    python db_updater.py                      # crea partiti/risultati/codici
    python sync_party_aliases.py --import     # ripristina gli alias
    python db_updater.py                      # ora anche le righe regionali risolvono
    php ../scripts/calculate_indicators.php
    php ../scripts/export_open_data.php
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

from common import REPO_ROOT, get_logger, load_dotenv, slugify
from db import db_available, get_connection
from merge_parties import fetch_party, merge_parties

REFERENCE_CSV = REPO_ROOT / "data" / "reference" / "party_aliases.csv"
FIELDNAMES = ["party_slug", "alias_name", "year_from", "year_to", "source", "notes"]


def export_aliases(cur, out_path: Path) -> int:
    cur.execute(
        """
        SELECT p.slug, a.alias_name, a.year_from, a.year_to, a.source, a.notes
        FROM party_aliases a
        JOIN parties p ON p.id = a.party_id
        ORDER BY p.slug ASC, a.alias_name ASC
        """
    )
    rows = cur.fetchall()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDNAMES)
        for slug, alias_name, year_from, year_to, source, notes in rows:
            writer.writerow([
                slug, alias_name,
                year_from if year_from is not None else "",
                year_to if year_to is not None else "",
                source or "", notes or "",
            ])
    return len(rows)


def reconcile_recreated_duplicates(cur, rows: "list[dict]", party_by_slug: "dict[str, int]") -> "list[str]":
    """
    Su un'installazione da zero, il primo `db_updater.py` crea i partiti
    (compresi i doppioni) PRIMA che questo script abbia importato gli alias:
    per quel primo giro, `party_aliases` è vuota, quindi l'euristica di
    risoluzione dei nomi in `upsert_party()` non ha nulla su cui appoggiarsi
    e ricrea come partito nuovo ogni grafia già unita in passato con
    `merge_parties.py`. Qui si rileva il caso — lo slug di un `alias_name`
    corrisponde a un partito ESISTENTE diverso da quello di destinazione
    dell'alias — e si applica lo stesso merge, così l'anagrafica torna
    pulita senza intervento manuale. Muta `party_by_slug` in place.
    """
    merged: list[str] = []
    for row in rows:
        target_slug = (row.get("party_slug") or "").strip()
        alias_name = (row.get("alias_name") or "").strip()
        if not target_slug or not alias_name:
            continue
        target_id = party_by_slug.get(target_slug)
        if target_id is None:
            continue
        dup_slug = slugify(alias_name)
        if dup_slug == target_slug:
            continue
        dup_id = party_by_slug.get(dup_slug)
        if dup_id is None or dup_id == target_id:
            continue

        keep = fetch_party(cur, target_slug)
        merge = fetch_party(cur, dup_slug)
        if keep is None or merge is None:
            continue

        logging.warning(
            f"Partito duplicato ricreato dal primo giro di db_updater.py: #{merge['id']} "
            f"({merge['slug']!r}) corrisponde alla grafia storica {alias_name!r} già "
            f"associata a #{keep['id']} ({keep['slug']!r}) — unione automatica."
        )
        if merge_parties(cur, keep, merge):
            del party_by_slug[dup_slug]
            merged.append(dup_slug)

    return merged


def import_aliases(cur, in_path: Path) -> "tuple[int, int, list[str], list[str]]":
    """Restituisce (inseriti, già_presenti, slug_non_risolti, duplicati_ricreati_uniti)."""
    with open(in_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    cur.execute("SELECT slug, id FROM parties")
    party_by_slug = {slug: pid for slug, pid in cur.fetchall()}

    reconciled = reconcile_recreated_duplicates(cur, rows, party_by_slug)

    inserted, existing = 0, 0
    unresolved: list[str] = []
    for row in rows:
        slug = (row.get("party_slug") or "").strip()
        alias_name = (row.get("alias_name") or "").strip()
        if not slug or not alias_name:
            continue
        party_id = party_by_slug.get(slug)
        if party_id is None:
            unresolved.append(slug)
            continue

        cur.execute(
            "SELECT id FROM party_aliases WHERE party_id = %s AND alias_name = %s",
            (party_id, alias_name),
        )
        if cur.fetchone():
            existing += 1
            continue

        cur.execute(
            """
            INSERT INTO party_aliases (party_id, alias_name, year_from, year_to, source, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                party_id, alias_name,
                int(row["year_from"]) if (row.get("year_from") or "").strip() else None,
                int(row["year_to"]) if (row.get("year_to") or "").strip() else None,
                (row.get("source") or "").strip() or None,
                (row.get("notes") or "").strip() or None,
            ),
        )
        inserted += 1

    return inserted, existing, sorted(set(unresolved)), reconciled


def main():
    parser = argparse.ArgumentParser(
        description="2x1000 — Sincronizza gli alias dei partiti con l'archivio versionato data/reference/")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", action="store_true",
                        help=f"Esporta gli alias dal database in {REFERENCE_CSV.relative_to(REPO_ROOT)}")
    group.add_argument("--import", dest="do_import", action="store_true",
                        help=f"Importa (upsert) gli alias da {REFERENCE_CSV.relative_to(REPO_ROOT)} nel database")
    parser.add_argument("--file", type=str, default=None,
                         help="Percorso CSV alternativo (default: data/reference/party_aliases.csv)")
    args = parser.parse_args()

    get_logger("sync_party_aliases", Path(__file__).resolve().parent)
    load_dotenv()

    if not db_available():
        logging.error("Database non configurato o pymysql non installato (verifica .env).")
        sys.exit(1)

    csv_path = Path(args.file) if args.file else REFERENCE_CSV

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if args.export:
                count = export_aliases(cur, csv_path)
                logging.info(f"Esportati {count} alias in {csv_path}")
                logging.info("Committa il file per renderlo parte dell'archivio del progetto.")
            else:
                if not csv_path.is_file():
                    logging.error(f"File non trovato: {csv_path}")
                    sys.exit(1)
                inserted, existing, unresolved, reconciled = import_aliases(cur, csv_path)
                conn.commit()
                logging.info(f"Import completato: {inserted} alias inseriti, {existing} già presenti.")
                if reconciled:
                    logging.info(
                        f"{len(reconciled)} partiti duplicati (ricreati dal primo giro di db_updater.py) "
                        f"uniti automaticamente: {reconciled}."
                    )
                if unresolved:
                    logging.warning(
                        f"{len(unresolved)} slug non trovati in `parties` (alias saltati): {unresolved}. "
                        f"Esegui prima db_updater.py per creare i partiti, poi rilancia l'import."
                    )
    except Exception:
        conn.rollback()
        logging.error("Errore: rollback eseguito", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
