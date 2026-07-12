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
import re
import sys
from datetime import date
from pathlib import Path

from common import REPO_ROOT, get_logger, load_config
from extract import fetch_source_file, is_footer_row, locate_header, parse_int, read_table, sha256_file

REGION_ALIASES = frozenset({"regioni", "regione"})

SUPPRESSED_MARKER = "***"

# La tabella regione×partito del Dipartimento delle Finanze è paginata sul
# lato server (query string "page=N"): per gli anni con molti partiti
# ammessi (es. 2018, anno elettorale) la pagina 1 non contiene tutte le
# colonne partito, le successive sì. Non è affidabile assumere un numero
# fisso di pagine (per anni con meno partiti "page=1" è già completa e le
# pagine successive ripetono lo stesso contenuto): si scaricano pagine
# successive finché non ne compare una che non aggiunge nessuna colonna
# partito nuova rispetto a quelle già viste, con un tetto di sicurezza.
MAX_GEO_PAGES = 6

# Colonne di riepilogo che compaiono nella stessa tabella accanto alle colonne
# partito (es. un totale contribuenti o scelte valide per regione): non sono
# partiti e vanno escluse a monte, altrimenti finiscono nell'elenco dei "nomi
# partito non riconosciuti" a ogni esecuzione. Confronto sull'intestazione
# normalizzata (minuscolo, senza "*" di nota finale).
_NON_PARTY_COLUMN_ALIASES = frozenset({
    "numero totale contribuenti",
    "scelte valide",
    "totale scelte valide",
    "totale",
})


def _is_summary_column(header_label: str) -> bool:
    normalized = header_label.strip().lower().rstrip("*").strip()
    return normalized in _NON_PARTY_COLUMN_ALIASES


def _page_url(url: str, page: int) -> str:
    """Sostituisce il parametro page=N nell'URL configurato con il numero indicato."""
    return re.sub(r"page=\d+", f"page={page}", url)


def _header_party_names(header: "list[str]", rows: "list[list[str]]") -> "set[str]":
    """Nomi partito (colonne) di una tabella già ripulita dalle righe di titolo iniziali."""
    header, _ = locate_header(header, rows, REGION_ALIASES)
    header_norm = [h.strip().lower() for h in header]
    names = set()
    for i, h in enumerate(header):
        if not h.strip() or header_norm[i] in REGION_ALIASES or _is_summary_column(h):
            continue
        names.add(h.strip())
    return names

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

    party_columns = []
    excluded_summary = []
    for i, h in enumerate(header):
        if i == region_idx or not h.strip():
            continue
        if _is_summary_column(h):
            excluded_summary.append(h.strip())
            continue
        party_columns.append((i, h.strip()))

    if excluded_summary:
        logging.info(f"  Colonne di riepilogo escluse (non sono partiti): {excluded_summary}")

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


def download_year_pages(year: int, raw_dir: Path, session) -> "list[Path]":
    """
    Scarica la pagina 1 e, finché aggiungono colonne partito nuove, le pagine
    successive (page=2, page=3, ...) fino a MAX_GEO_PAGES. Restituisce i
    percorsi dei file scaricati che hanno contribuito dati nuovi (la pagina 1
    è sempre inclusa se il download riesce).

    Ogni pagina viene scaricata con una sessione HTTP indipendente (nuovi
    cookie): il sito del Dipartimento delle Finanze lega lo stato "pagina
    corrente" alla sessione, per cui riusare la stessa sessione per page=1 e
    page=2 restituisce due volte il contenuto di page=1.
    """
    url = YEAR_URLS.get(year)
    if not url:
        logging.info(f"[{year}] Nessun URL configurato in config.yaml (url_anni_geografia)")
        return []

    folder = raw_dir / str(year) / "geografia"
    files = []
    known_parties: "set[str]" = set()

    for page in range(1, MAX_GEO_PAGES + 1):
        page_folder = folder if page == 1 else folder / f"page{page}"
        page_folder.mkdir(parents=True, exist_ok=True)

        page_session = session
        if session is not None:
            import requests
            page_session = requests.Session()
        try:
            dest = fetch_source_file(_page_url(url, page), page_folder, page_session)
        finally:
            if page_session is not session:
                page_session.close()
        if not dest:
            if page == 1:
                logging.warning(f"[{year}] Nessun file scaricabile trovato per {url}")
            break

        try:
            header, rows = read_table(dest)
        except Exception as e:
            logging.warning(f"[{year}] pagina {page}: errore di lettura di {dest.name} ({e}), ignorata")
            break
        if not header:
            break

        page_parties = _header_party_names(header, rows)
        new_parties = page_parties - known_parties
        if page > 1 and not new_parties:
            logging.info(
                f"[{year}] pagina {page}: nessuna colonna partito nuova rispetto alle {len(known_parties)} "
                f"già trovate, mi fermo qui."
            )
            break

        files.append(dest)
        known_parties |= page_parties
        if page > 1:
            logging.info(f"[{year}] pagina {page}: {len(new_parties)} colonne partito nuove")

    return files


def find_local_files(raw_dir: Path, year: int) -> "list[Path]":
    """Pagina 1 nella cartella dell'anno, più eventuali pagine successive già scaricate in precedenza (page2/, page3/, ...)."""
    folder = raw_dir / str(year) / "geografia"
    if not folder.is_dir():
        return []

    files = []
    for ext in ("*.csv", "*.xlsx", "*.xls"):
        matches = sorted(folder.glob(ext))
        if matches:
            files.append(matches[0])
            break

    page = 2
    while True:
        page_folder = folder / f"page{page}"
        if not page_folder.is_dir():
            break
        found = None
        for ext in ("*.csv", "*.xlsx", "*.xls"):
            matches = sorted(page_folder.glob(ext))
            if matches:
                found = matches[0]
                break
        if not found:
            break
        files.append(found)
        page += 1

    return files


def process_year(year: int, args, raw_dir: Path, processed_dir: Path, session=None) -> str:
    """Restituisce 'ok', 'skipped' (anno non configurato, non è un errore) o 'error'."""
    logging.info(f"[{year}] Inizio elaborazione")

    if args.input:
        file_paths = [Path(args.input)]
    elif args.no_download:
        file_paths = find_local_files(raw_dir, year)
    else:
        file_paths = download_year_pages(year, raw_dir, session) or find_local_files(raw_dir, year)

    file_paths = [p for p in file_paths if p and p.is_file()]
    if not file_paths:
        logging.warning(
            f"[{year}] Nessun file disponibile. Configura l'URL in config.yaml "
            f"(url_anni_geografia) oppure salva manualmente il file ufficiale in "
            f"data/raw/{year}/geografia/ e riesegui con --no-download."
        )
        return "skipped"

    merged: "dict[tuple[str, str], dict]" = {}
    known_parties: "set[str]" = set()
    used_paths = []

    for i, file_path in enumerate(file_paths):
        logging.info(f"[{year}] Lettura: {file_path.name}")
        try:
            header, rows = read_table(file_path)
        except Exception as e:
            logging.error(f"[{year}] Errore nella lettura di {file_path.name}: {e}")
            if i == 0:
                return "error"
            continue

        if not header:
            if i == 0:
                logging.error(f"[{year}] Impossibile determinare l'intestazione di {file_path.name}")
                return "error"
            continue

        page_records = parse_regional_table(header, rows)
        page_parties = {r["party_name"] for r in page_records}
        if i > 0 and known_parties and not (page_parties - known_parties):
            continue  # file già scaricato in una run precedente, non aggiunge nulla

        for r in page_records:
            merged[(r["region"], r["party_name"])] = r
        known_parties |= page_parties
        used_paths.append(file_path)

    records = list(merged.values())
    if not records:
        logging.warning(f"[{year}] Nessun dato estratto")
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
        "source_file": ", ".join(
            str(p.relative_to(REPO_ROOT)) if p.is_relative_to(REPO_ROOT) else str(p) for p in used_paths
        ),
        "checksum": ", ".join(sha256_file(p) for p in used_paths),
        "download_date": date.today().isoformat(),
        "row_count": len(records),
        "regions": n_regions,
        "parties": n_parties,
        "suppressed": n_suppressed,
        "pages": len(used_paths),
    }
    write_meta(meta, processed_dir / f"regional_results_{year}.meta.json")

    logging.info(
        f"[{year}] => {out_csv.name} ({len(records)} righe, {n_regions} regioni, "
        f"{n_parties} partiti, {n_suppressed} oscurati, {len(used_paths)} pagine lette)"
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
