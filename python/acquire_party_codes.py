#!/usr/bin/env python3
"""
acquire_party_codes.py — Scarica ed estrae l'elenco annuale dei partiti
ammessi al beneficio del 2x1000 e i relativi codici da indicare in
dichiarazione, pubblicati dall'Agenzia delle Entrate.

Stessa logica di acquire_results.py (vedi quel file per i dettagli), con
alias di colonna diversi: qui cerchiamo "codice" e "denominazione ufficiale"
invece di scelte/importo.

Uso:
    python acquire_party_codes.py --anni 2024
    python acquire_party_codes.py --anni 2024 --no-download
    python acquire_party_codes.py --anni 2024 --input elenco_2024.csv
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
from extract import fetch_source_file, find_col, read_table, sha256_file

NAME_ALIASES = frozenset({
    "denominazione", "denominazione ufficiale", "partito", "partito politico",
    "nome partito",
})
CODE_ALIASES = frozenset({
    "codice", "codice partito", "codice da indicare in dichiarazione",
    "codice dichiarazione", "cod.",
})

# URL per anno (Agenzia delle Entrate). Vuoto di default: va compilato in
# config.yaml (sezione url_anni_codici) con le pagine ufficiali man mano che
# vengono verificate. Senza URL configurato, lo script legge i file già
# presenti in data/raw/<anno>/codici/.
YEAR_URLS: dict = {}


def _apply_config(cfg: dict) -> None:
    global YEAR_URLS
    url_anni = cfg.get("url_anni_codici")
    if url_anni and isinstance(url_anni, dict):
        for anno, url in url_anni.items():
            YEAR_URLS[int(anno)] = str(url)


def parse_codes_table(header: "list[str]", rows: "list[list[str]]") -> "list[dict]":
    header_norm = [h.strip().lower() for h in header]
    name_idx = find_col(header_norm, NAME_ALIASES)
    code_idx = find_col(header_norm, CODE_ALIASES)

    if name_idx is None or code_idx is None:
        logging.error(f"  Colonne denominazione/codice non trovate. Intestazione: {header}")
        return []

    records = []
    for row in rows:
        if name_idx >= len(row) or code_idx >= len(row):
            continue
        name = row[name_idx].strip()
        code = row[code_idx].strip()
        if not name or not code:
            continue
        records.append({"official_name": name, "code": code})
    return records


def write_normalized_csv(records: "list[dict]", declaration_year: int, tax_year: int, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["official_name", "declaration_year", "tax_year", "code"])
        for r in records:
            writer.writerow([r["official_name"], declaration_year, tax_year, r["code"]])


def write_meta(meta: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def download_year(year: int, raw_dir: Path, session) -> "Path | None":
    url = YEAR_URLS.get(year)
    if not url:
        logging.info(f"[{year}] Nessun URL configurato in config.yaml (url_anni_codici)")
        return None

    folder = raw_dir / str(year) / "codici"
    folder.mkdir(parents=True, exist_ok=True)
    dest = fetch_source_file(url, folder, session)
    if not dest:
        logging.warning(f"[{year}] Nessun file scaricabile trovato per {url}")
    return dest


def find_local_file(raw_dir: Path, year: int) -> "Path | None":
    folder = raw_dir / str(year) / "codici"
    if not folder.is_dir():
        return None
    for ext in ("*.csv", "*.xlsx", "*.xls", "*.pdf"):
        matches = sorted(folder.glob(ext))
        if matches:
            return matches[0]
    return None


def process_year(year: int, args, raw_dir: Path, processed_dir: Path, session=None) -> bool:
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
            f"(url_anni_codici) oppure salva manualmente il file ufficiale in "
            f"data/raw/{year}/codici/ e riesegui con --no-download."
        )
        return False

    logging.info(f"[{year}] Lettura: {file_path.name}")
    try:
        header, rows = read_table(file_path)
    except Exception as e:
        logging.error(f"[{year}] Errore nella lettura di {file_path.name}: {e}")
        return False

    if not header:
        logging.error(f"[{year}] Impossibile determinare l'intestazione di {file_path.name}")
        return False

    records = parse_codes_table(header, rows)
    if not records:
        logging.warning(f"[{year}] Nessun codice estratto da {file_path.name}")
        return False

    tax_year = args.tax_year if args.tax_year else year - 1
    out_csv = processed_dir / f"ade_codes_{year}.csv"
    write_normalized_csv(records, year, tax_year, out_csv)

    meta = {
        "declaration_year": year,
        "tax_year": tax_year,
        "institution": "Agenzia delle Entrate",
        "source_type": "codici_dichiarazione",
        "url": YEAR_URLS.get(year),
        "source_file": str(file_path.relative_to(REPO_ROOT)) if file_path.is_relative_to(REPO_ROOT) else str(file_path),
        "checksum": sha256_file(file_path),
        "download_date": date.today().isoformat(),
        "row_count": len(records),
    }
    write_meta(meta, processed_dir / f"ade_codes_{year}.meta.json")

    logging.info(f"[{year}] => {out_csv.name} ({len(records)} partiti)")
    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="2x1000 — Download ed estrazione elenco partiti ammessi e codici (Agenzia delle Entrate)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--anni", type=str, default=None,
                         help="Anni da elaborare, separati da virgola. Default: tutti quelli configurati in url_anni_codici.")
    parser.add_argument("--no-download", action="store_true",
                         help="Non scaricare: usa i file già presenti in data/raw/<anno>/codici/")
    parser.add_argument("--input", type=str, default=None,
                         help="Percorso di un file specifico da elaborare (richiede un solo anno in --anni)")
    parser.add_argument("--tax-year", type=int, default=None,
                         help="Anno d'imposta, se diverso da anno_dichiarazione - 1")
    return parser.parse_args()


def main():
    args = parse_args()
    get_logger("acquire_party_codes", Path(__file__).resolve().parent)

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
            "Usa --anni ANNO oppure compila url_anni_codici in config.yaml."
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

    ok, errors = 0, 0
    for year in years:
        try:
            if process_year(year, args, raw_dir, processed_dir, session):
                ok += 1
            else:
                errors += 1
        except Exception as e:
            logging.error(f"[{year}] Errore imprevisto: {e}")
            errors += 1

    if session:
        session.close()

    logging.info(f"Completato: {ok} anni elaborati, {errors} errori/skip")
    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
