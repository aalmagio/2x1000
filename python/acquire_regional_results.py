#!/usr/bin/env python3
"""
acquire_regional_results.py — Scarica ed estrae la ripartizione regionale
delle scelte del 2x1000 per partito, pubblicata dal Ministero dell'Economia
e delle Finanze (Dipartimento delle Finanze) sullo stesso portale dei
risultati nazionali (vedi acquire_results.py), nodo "tree" con suffisso
"AADUEXM0201" invece di "...0101".

Il file sorgente è a sviluppo ORIZZONTALE: una riga per regione, una colonna
per partito (intestata col nome del partito, non col codice), valori = numero
di scelte. I valori troppo bassi sono oscurati dalla fonte con "***" per
tutela della riservatezza: vengono registrati come "oscurati"
(is_suppressed), non come zero.

Poiché l'intestazione usa il NOME del partito (non il codice), la
corrispondenza nome -> partito viene risolta in db_updater.py confrontando
(dopo normalizzazione) con canonical_name, party_codes.official_name
dell'anno e party_aliases.alias_name — non qui: questo script si limita a
normalizzare la tabella in formato lungo (una riga per regione+partito).

Per ogni anno:
  1. (opzionale) scarica il file dalla pagina ufficiale configurata in
     url_anni_geografia (config.yaml), oppure legge un file già presente in
     data/raw/<anno>/geografia/;
  2. individua la riga di intestazione (nome regione + nomi partito) e la
     colonna regione;
  3. scrive un CSV normalizzato in formato lungo in
     data/processed/regional_results_<anno>.csv, con a fianco un file
     .meta.json usato da db_updater.py per registrare la fonte.

Uso:
    python acquire_regional_results.py --anni 2024
    python acquire_regional_results.py --anni 2024 --no-download
    python acquire_regional_results.py --anni 2024 --input mio_file.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from datetime import date
from pathlib import Path

from common import REPO_ROOT, get_logger, load_config
from extract import fetch_source_file, is_footer_row, locate_header, parse_int, read_table, sha256_file

REGION_ALIASES = frozenset({"regioni", "regione"})

SUPPRESSED_MARKER = "***"

# URL per anno (Dipartimento delle Finanze). Vuoto di default: va compilato
# in config.yaml (sezione url_anni_geografia). Senza URL configurato, lo
# script legge i file già presenti in data/raw/<anno>/geografia/.
YEAR_URLS: dict = {}


def _apply_config(cfg: dict) -> None:
    global YEAR_URLS
    url_anni = cfg.get("url_anni_geografia")
    if url_anni and isinstance(url_anni, dict):
        for anno, url in url_anni.items():
            YEAR_URLS[int(anno)] = str(url)


def parse_regional_table(header: "list[str]", rows: "list[list[str]]") -> "list[dict]":
    """
    Mappa una tabella grezza a sviluppo orizzontale (colonna 0 = regione,
    colonne successive = partiti) in formato lungo:
    [{"region": ..., "party_name": ..., "valid_choices": int|None, "is_suppressed": bool}, ...]
    """
    header, rows = locate_header(header, rows, REGION_ALIASES)
    header_norm = [h.strip().lower() for h in header]

    region_idx = None
    for i, c in enumerate(header_norm):
        if c in REGION_ALIASES:
            region_idx = i
            break
    if region_idx is None:
        logging.error(f"  Colonna regione non trovata. Intestazione: {header}")
        return []

    party_columns = [(i, h.strip()) for i, h in enumerate(header) if i != region_idx and h.strip()]
    if not party_columns:
        logging.error("  Nessuna colonna partito trovata nell'intestazione.")
        return []

    records = []
    for row in rows:
        if region_idx >= len(row):
            continue
        region = row[region_idx].strip()
        if is_footer_row(region):
            continue

        for col_idx, party_name in party_columns:
            if col_idx >= len(row):
                continue
            raw = row[col_idx].strip()
            if not raw:
                continue  # nessun dato riportato per questa cella: non si registra nulla

            if raw == SUPPRESSED_MARKER:
                records.append({
                    "region": region,
                    "party_name": party_name,
                    "valid_choices": None,
                    "is_suppressed": True,
                })
                continue

            choices = parse_int(raw)
            if choices is None:
                continue
            records.append({
                "region": region,
                "party_name": party_name,
                "valid_choices": choices,
                "is_suppressed": False,
            })

    return records


def write_normalized_csv(records: "list[dict]", declaration_year: int, tax_year: int, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["party_name", "region", "declaration_year", "tax_year", "valid_choices", "is_suppressed"])
        for r in records:
            writer.writerow([
                r["party_name"], r["region"], declaration_year, tax_year,
                r["valid_choices"] if r["valid_choices"] is not None else "",
                1 if r["is_suppressed"] else 0,
            ])


def write_meta(meta: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def download_year(year: int, raw_dir: Path, session) -> "Path | None":
    url = YEAR_URLS.get(year)
    if not url:
        logging.info(f"[{year}] Nessun URL configurato in config.yaml (url_anni_geografia)")
        return None

    folder = raw_dir / str(year) / "geografia"
    folder.mkdir(parents=True, exist_ok=True)
    dest = fetch_source_file(url, folder, session)
    if not dest:
        logging.warning(f"[{year}] Nessun file scaricabile trovato per {url}")
    return dest


def find_local_file(raw_dir: Path, year: int) -> "Path | None":
    folder = raw_dir / str(year) / "geografia"
    if not folder.is_dir():
        return None
    for ext in ("*.csv", "*.xlsx", "*.xls"):
        matches = sorted(folder.glob(ext))
        if matches:
            return matches[0]
    return None


def process_year(year: int, args, raw_dir: Path, processed_dir: Path, session=None) -> str:
    """Restituisce 'ok', 'skipped' (anno non configurato, non è un errore) o 'error'."""
    logging.info(f"[{year}] Inizio elaborazione")

    if args.input:
        file_path = Path(args.input)
    elif args.no_download:
        file_path = find_local_file(raw_dir, year)
    else:
        file_path = download_year(year, raw_dir, session) or find_local_file(raw_dir, year)

    if not file_path or not file_path.is_file():
        logging.warning(
            f"[{year}] Nessun file disponibile. Configura l'URL in config.yaml "
            f"(url_anni_geografia) oppure salva manualmente il file ufficiale in "
            f"data/raw/{year}/geografia/ e riesegui con --no-download."
        )
        return "skipped"

    logging.info(f"[{year}] Lettura: {file_path.name}")
    try:
        header, rows = read_table(file_path)
    except Exception as e:
        logging.error(f"[{year}] Errore nella lettura di {file_path.name}: {e}")
        return "error"

    if not header:
        logging.error(f"[{year}] Impossibile determinare l'intestazione di {file_path.name}")
        return "error"

    records = parse_regional_table(header, rows)
    if not records:
        logging.warning(f"[{year}] Nessun dato estratto da {file_path.name}")
        return "error"

    tax_year = args.tax_year if args.tax_year else year - 1
    out_csv = processed_dir / f"regional_results_{year}.csv"
    write_normalized_csv(records, year, tax_year, out_csv)

    n_suppressed = sum(1 for r in records if r["is_suppressed"])
    n_regions = len({r["region"] for r in records})
    n_parties = len({r["party_name"] for r in records})

    meta = {
        "declaration_year": year,
        "tax_year": tax_year,
        "institution": "Ministero dell'Economia e delle Finanze — Dipartimento delle Finanze",
        "source_type": "ripartizione_regionale",
        "url": YEAR_URLS.get(year),
        "source_file": str(file_path.relative_to(REPO_ROOT)) if file_path.is_relative_to(REPO_ROOT) else str(file_path),
        "checksum": sha256_file(file_path),
        "download_date": date.today().isoformat(),
        "row_count": len(records),
        "regions": n_regions,
        "parties": n_parties,
        "suppressed": n_suppressed,
    }
    write_meta(meta, processed_dir / f"regional_results_{year}.meta.json")

    logging.info(
        f"[{year}] => {out_csv.name} ({len(records)} righe, {n_regions} regioni, "
        f"{n_parties} partiti, {n_suppressed} oscurati)"
    )
    return "ok"


def parse_args():
    parser = argparse.ArgumentParser(
        description="2x1000 — Download ed estrazione ripartizione regionale delle scelte dal MEF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Esempi:
  %(prog)s --anni 2024                        # scarica ed estrae l'anno 2024
  %(prog)s --anni 2024 --no-download          # estrae da data/raw/2024/geografia/
  %(prog)s --anni 2024 --input dati_2024.csv  # estrae un file specifico
""",
    )
    parser.add_argument("--anni", type=str, default=None,
                         help="Anni da elaborare, separati da virgola. Default: tutti quelli configurati in url_anni_geografia.")
    parser.add_argument("--no-download", action="store_true",
                         help="Non scaricare: usa i file già presenti in data/raw/<anno>/geografia/")
    parser.add_argument("--input", type=str, default=None,
                         help="Percorso di un file specifico da elaborare (richiede un solo anno in --anni)")
    parser.add_argument("--tax-year", type=int, default=None,
                         help="Anno d'imposta, se diverso da anno_dichiarazione - 1")
    return parser.parse_args()


def main():
    args = parse_args()
    get_logger("acquire_regional_results", Path(__file__).resolve().parent)

    cfg = load_config()
    _apply_config(cfg)

    raw_dir = REPO_ROOT / "data" / "raw"
    processed_dir = REPO_ROOT / "data" / "processed"

    if args.anni:
        years = sorted(int(a.strip()) for a in args.anni.split(",") if a.strip())
    elif YEAR_URLS:
        years = sorted(YEAR_URLS.keys())
    else:
        logging.error(
            "Nessun anno specificato e nessun URL configurato in config.yaml. "
            "Usa --anni ANNO oppure compila url_anni_geografia in config.yaml."
        )
        sys.exit(1)

    if args.input and len(years) != 1:
        logging.error("--input richiede esattamente un anno in --anni")
        sys.exit(1)

    session = None
    if not args.no_download and not args.input:
        try:
            import requests
            session = requests.Session()
        except ImportError:
            logging.warning("requests non installato: salto il download, uso solo i file locali.")

    ok, skipped, errors = 0, 0, 0
    for year in years:
        try:
            result = process_year(year, args, raw_dir, processed_dir, session)
        except Exception as e:
            logging.error(f"[{year}] Errore imprevisto: {e}")
            result = "error"

        if result == "ok":
            ok += 1
        elif result == "skipped":
            skipped += 1
        else:
            errors += 1

    if session:
        session.close()

    logging.info(f"Completato: {ok} anni elaborati, {skipped} saltati (non configurati), {errors} errori")
    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
