#!/usr/bin/env python3
"""
acquire_results.py — Scarica ed estrae i risultati annuali del 2x1000 ai
partiti politici pubblicati dal Ministero dell'Economia e delle Finanze
(Dipartimento delle Finanze).

Analogo a cinque_per_mille.py del progetto 5x1000, adattato al formato più
semplice del 2x1000 (un'unica tabella per anno: partito, scelte, importo).

Per ogni anno:
  1. (opzionale) scarica il file CSV/XLSX/PDF dalla pagina ufficiale configurata
     in url_anni (config.yaml), oppure legge un file già presente in
     data/raw/<anno>/ (utile quando l'URL non è ancora configurato, o il file
     è stato scaricato manualmente);
  2. individua le colonne di partito/scelte/importo tramite alias di colonna
     (i nomi esatti cambiano da un anno all'altro);
  3. scrive un CSV normalizzato in data/processed/mef_results_<anno>.csv,
     con a fianco un file .meta.json (URL, data download, checksum) usato da
     db_updater.py per registrare la fonte.

Uso:
    python acquire_results.py --anni 2024                     # scarica ed estrae
    python acquire_results.py --anni 2024 --no-download        # solo estrazione da data/raw/2024/
    python acquire_results.py --anni 2024 --input mio_file.csv # estrai un file specifico
    python acquire_results.py                                  # tutti gli anni configurati in url_anni
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
from extract import fetch_source_file, find_col, parse_amount, parse_int, read_table, sha256_file

PARTY_ALIASES = frozenset({
    "denominazione", "partito", "partito politico", "denominazione partito",
    "nome partito", "beneficiario",
})
CHOICES_ALIASES = frozenset({
    "numero scelte", "n. scelte", "n scelte", "scelte", "numero di scelte",
    "scelte valide", "numero scelte valide",
})
AMOUNT_ALIASES = frozenset({
    "importo", "importo (euro)", "importo euro", "importo totale",
    "importo assegnato", "ammontare",
})

# URL per anno (Dipartimento delle Finanze / MEF). Vuoto di default: va
# compilato in config.yaml (sezione url_anni_risultati) con le pagine ufficiali
# man mano che vengono verificate. Senza URL configurato, lo script si limita
# a leggere i file già presenti in data/raw/<anno>/.
YEAR_URLS: dict = {}


def _apply_config(cfg: dict) -> None:
    global YEAR_URLS
    url_anni = cfg.get("url_anni_risultati")
    if url_anni and isinstance(url_anni, dict):
        for anno, url in url_anni.items():
            YEAR_URLS[int(anno)] = str(url)


def parse_results_table(header: "list[str]", rows: "list[list[str]]") -> "list[dict]":
    """
    Mappa una tabella grezza (header, rows) sullo schema normalizzato
    [{"party_name": ..., "valid_choices": int, "amount": float}, ...].
    Salta le righe senza nome partito o totalmente numeriche/vuote (righe di
    totale, note a piè di pagina, ecc.).
    """
    header_norm = [h.strip().lower() for h in header]
    party_idx = find_col(header_norm, PARTY_ALIASES)
    choices_idx = find_col(header_norm, CHOICES_ALIASES)
    amount_idx = find_col(header_norm, AMOUNT_ALIASES)

    if party_idx is None:
        logging.error(f"  Colonna partito non trovata. Intestazione: {header}")
        return []
    if choices_idx is None and amount_idx is None:
        logging.error(f"  Nessuna colonna scelte/importo trovata. Intestazione: {header}")
        return []

    records = []
    for row in rows:
        if party_idx >= len(row):
            continue
        name = row[party_idx].strip()
        if not name or name.lower() in ("totale", "totale generale", "totali"):
            continue

        choices = parse_int(row[choices_idx]) if choices_idx is not None and choices_idx < len(row) else None
        amount = parse_amount(row[amount_idx]) if amount_idx is not None and amount_idx < len(row) else None
        if choices is None and amount is None:
            continue

        records.append({
            "party_name": name,
            "valid_choices": choices or 0,
            "amount": amount or 0.0,
        })

    return records


def write_normalized_csv(records: "list[dict]", declaration_year: int, tax_year: int, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["party_name", "declaration_year", "tax_year", "valid_choices", "amount"])
        for r in records:
            writer.writerow([r["party_name"], declaration_year, tax_year, r["valid_choices"], r["amount"]])


def write_meta(meta: dict, out_path: Path) -> None:
    out_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def download_year(year: int, raw_dir: Path, session) -> "Path | None":
    """Scarica il file dei risultati per un anno. Restituisce il path scaricato o None."""
    url = YEAR_URLS.get(year)
    if not url:
        logging.info(f"[{year}] Nessun URL configurato in config.yaml (url_anni_risultati)")
        return None

    folder = raw_dir / str(year)
    folder.mkdir(parents=True, exist_ok=True)
    dest = fetch_source_file(url, folder, session)
    if not dest:
        logging.warning(f"[{year}] Nessun file scaricabile trovato per {url}")
    return dest


def find_local_file(raw_dir: Path, year: int) -> "Path | None":
    """Cerca un file già presente in data/raw/<year>/ (CSV, XLSX o PDF)."""
    folder = raw_dir / str(year)
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
            f"(url_anni_risultati) oppure salva manualmente il file ufficiale in "
            f"data/raw/{year}/ e riesegui con --no-download."
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

    records = parse_results_table(header, rows)
    if not records:
        logging.warning(f"[{year}] Nessun risultato estratto da {file_path.name}")
        return False

    tax_year = args.tax_year if args.tax_year else year - 1
    out_csv = processed_dir / f"mef_results_{year}.csv"
    write_normalized_csv(records, year, tax_year, out_csv)

    meta = {
        "declaration_year": year,
        "tax_year": tax_year,
        "institution": "Ministero dell'Economia e delle Finanze — Dipartimento delle Finanze",
        "source_type": "risultati_annuali",
        "url": YEAR_URLS.get(year),
        "source_file": str(file_path.relative_to(REPO_ROOT)) if file_path.is_relative_to(REPO_ROOT) else str(file_path),
        "checksum": sha256_file(file_path),
        "download_date": date.today().isoformat(),
        "row_count": len(records),
    }
    write_meta(meta, processed_dir / f"mef_results_{year}.meta.json")

    logging.info(f"[{year}] => {out_csv.name} ({len(records)} partiti)")
    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="2x1000 — Download ed estrazione risultati annuali dal MEF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Esempi:
  %(prog)s --anni 2024                        # scarica ed estrae l'anno 2024
  %(prog)s --anni 2024 --no-download          # estrae da data/raw/2024/ (file già presente)
  %(prog)s --anni 2024 --input dati_2024.csv  # estrae un file specifico
""",
    )
    parser.add_argument("--anni", type=str, default=None,
                         help="Anni da elaborare, separati da virgola (es. 2023,2024). "
                              "Default: tutti quelli configurati in url_anni_risultati.")
    parser.add_argument("--no-download", action="store_true",
                         help="Non scaricare: usa i file già presenti in data/raw/<anno>/")
    parser.add_argument("--input", type=str, default=None,
                         help="Percorso di un file specifico da elaborare (richiede un solo anno in --anni)")
    parser.add_argument("--tax-year", type=int, default=None,
                         help="Anno d'imposta, se diverso da anno_dichiarazione - 1")
    return parser.parse_args()


def main():
    args = parse_args()
    get_logger("acquire_results", Path(__file__).resolve().parent)

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
            "Usa --anni ANNO oppure compila url_anni_risultati in config.yaml."
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
