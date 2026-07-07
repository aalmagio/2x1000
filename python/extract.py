#!/usr/bin/env python3
"""
extract.py — Utilità generiche di download e lettura tabellare, condivise da
acquire_results.py e acquire_party_codes.py.

Le pagine del Ministero dell'Economia e delle Finanze e dell'Agenzia delle
Entrate pubblicano i dati in formati non standardizzati (CSV, XLSX o PDF a
seconda dell'anno): queste funzioni astraggono il download e la lettura in
una tabella (header + righe) indipendentemente dal formato, con lo stesso
approccio "alias di colonna" già usato per l'estrazione dei dati 5x1000.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import os
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

logger = logging.getLogger(__name__)

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB = True
except ImportError:
    HAS_WEB = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

TIMEOUT_PAGE = 60
TIMEOUT_FILE = 120

TABULAR_EXTS = (".csv", ".xlsx", ".xls", ".pdf")

# Link che compaiono quasi su ogni pagina istituzionale ma non sono mai i dati
# cercati (informativa privacy, cookie policy, note legali...). Senza questo
# filtro find_download_links() può "trovare" e scaricare con successo un file
# del tutto irrilevante, facendo sembrare l'acquisizione riuscita quando non
# lo è (visto in produzione: pagine del Dipartimento delle Finanze che non
# espongono alcun link ai dati, solo all'informativa privacy in PDF).
_JUNK_LINK_KEYWORDS = (
    "privacy", "cookie", "note legali", "note-legali", "informativa",
    "accessibilita", "accessibilità", "dichiarazione-accessibilita",
)


def _is_junk_link(href: str, text: str) -> bool:
    haystack = f"{href} {text}".lower()
    return any(kw in haystack for kw in _JUNK_LINK_KEYWORDS)


# Righe che compaiono nelle tabelle di partiti/codici ma non sono un partito:
# totali, note a piè di pagina, riferimenti di memoria ("Per memoria: Totale
# contribuenti"), didascalie. Confrontate come prefisso (non substring) sul
# nome/denominazione già in minuscolo, per non scartare per errore un partito
# il cui nome contenga per coincidenza una di queste parole a metà frase.
_FOOTER_ROW_PREFIXES = (
    "per memoria", "totale", "totali", "di cui", "nota", "n.b.", "n.d.",
    "fonte", "elaborazione", "note:", "*",
)


def is_footer_row(name: "str | None") -> bool:
    """True se `name` è con tutta probabilità una riga di nota/riepilogo e non un partito."""
    if not name:
        return True
    n = name.strip().lower()
    return any(n.startswith(p) for p in _FOOTER_ROW_PREFIXES)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _extract_links_from_html(page_url: str, html_text: str, exts=TABULAR_EXTS) -> dict:
    """Scansiona un HTML già scaricato e restituisce i link ai file scaricabili."""
    result = {ext.lstrip("."): [] for ext in exts}
    soup = BeautifulSoup(html_text, "html.parser")
    skipped_junk = 0
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        href_lower = href.lower()
        text = a_tag.get_text(strip=True)[:80]

        if _is_junk_link(href, text):
            skipped_junk += 1
            continue

        for ext in exts:
            if href_lower.endswith(ext) or f"{ext}" in href_lower:
                full_url = urljoin(page_url, href)
                key = ext.lstrip(".")
                if full_url not in result[key]:
                    result[key].append(full_url)
                    logger.info(f"    Trovato {key.upper()}: {text}")
                break

    if skipped_junk:
        logger.info(f"  Ignorati {skipped_junk} link non pertinenti (privacy/cookie/note legali)")

    total = sum(len(v) for v in result.values())
    logger.info(f"  Totale link trovati: {total}")
    return result


def find_download_links(page_url: str, session, exts=TABULAR_EXTS) -> dict:
    """
    Scarica una pagina HTML e restituisce i link ai file scaricabili,
    raggruppati per estensione: {"csv": [...], "xlsx": [...], "pdf": [...]}.
    """
    result = {ext.lstrip("."): [] for ext in exts}
    if not HAS_WEB:
        logger.error("requests/beautifulsoup4 non installati: impossibile leggere la pagina.")
        return result

    logger.info(f"  Scarico pagina: {page_url}")
    try:
        resp = session.get(page_url, headers=HEADERS, timeout=TIMEOUT_PAGE)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"  Errore nello scaricare la pagina: {e}")
        return result

    return _extract_links_from_html(page_url, resp.text, exts)


def download_file(url: str, dest_path: "str | Path", session) -> bool:
    """Scarica un file da URL e lo salva in dest_path. Restituisce True se riuscito."""
    dest_path = Path(dest_path)
    if dest_path.exists():
        logger.info(f"    File già presente ({dest_path.stat().st_size:,} bytes), salto: {dest_path.name}")
        return True
    if not HAS_WEB:
        logger.error("requests non installato: impossibile scaricare il file.")
        return False

    logger.info(f"    Scarico: {dest_path.name}...")
    try:
        resp = session.get(url, headers=HEADERS, timeout=TIMEOUT_FILE, stream=True)
        resp.raise_for_status()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"    Salvato: {dest_path.name} ({dest_path.stat().st_size:,} bytes)")
        return True
    except requests.RequestException as e:
        logger.error(f"    Errore nel download di {dest_path.name}: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def sanitize_filename(url: str, index: int, ext: str) -> str:
    """
    Genera un nome file pulito dall'URL, con indice progressivo come fallback.

    Alcuni CMS pubblici (es. Agenzia delle Entrate, basati su Liferay) inseriscono
    il nome del file a metà del path, seguito da un segmento di hash/versione:
    .../documents/123/456/Nome+file.pdf/07dd2e41-6897-...?t=169900000
    In quel caso l'ultimo segmento del path (l'hash) non è un nome utile: si
    cerca invece il segmento più vicino alla fine che contiene già l'estensione.
    """
    parsed = urlparse(url)
    segments = [unquote(s) for s in parsed.path.split("/") if s]
    basename = next((s for s in reversed(segments) if f".{ext}" in s.lower()), None)
    if basename is None and segments:
        basename = segments[-1]

    if basename and len(basename) < 200:
        basename = re.sub(r"[^\w\-.() ]", "_", basename)
        if not basename.lower().endswith(f".{ext}"):
            basename += f".{ext}"
        return basename
    return f"file_{index:02d}.{ext}"


def is_direct_file_url(url: str) -> "str | None":
    """
    Se l'URL punta già direttamente a un file (non a una pagina HTML da
    scansionare per trovare i link), restituisce l'estensione rilevata
    ('pdf', 'csv', 'xlsx', 'xls'); altrimenti None.

    Il controllo è per sottostringa (non solo suffisso) perché — come nel caso
    sopra — l'estensione può comparire a metà del path invece che alla fine.
    """
    url_lower = url.lower()
    for ext in ("pdf", "csv", "xlsx", "xls"):
        if f".{ext}" in url_lower:
            return ext
    return None


_CONTENT_TYPE_EXT = {
    "text/csv": "csv",
    "application/csv": "csv",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/pdf": "pdf",
}


def _filename_from_content_disposition(header_value: str) -> "str | None":
    """Estrae il nome file da un header Content-Disposition, se presente."""
    if not header_value:
        return None
    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', header_value)
    return unquote(match.group(1)) if match else None


def fetch_source_file(url: str, dest_folder: "str | Path", session) -> "Path | None":
    """
    Scarica il file dei dati da un URL configurato in config.yaml, che può
    essere:
      - un link diretto a un file (PDF/CSV/XLSX, riconoscibile dall'estensione
        nell'URL stesso) → scaricato subito;
      - un URL che risponde direttamente con il file (es. un parametro
        "export=1" che fa restituire al server un CSV/Excel invece di una
        pagina HTML, senza che l'URL contenga l'estensione) → riconosciuto
        dal Content-Type della risposta e salvato subito, senza cercare link;
      - una vera pagina HTML che elenca i file da scaricare → viene
        scansionata per trovare i link (ordine di preferenza: csv, xlsx, xls, pdf).

    Restituisce il percorso del file scaricato, o None se non è stato
    possibile ottenere nulla.
    """
    dest_folder = Path(dest_folder)
    direct_ext = is_direct_file_url(url)
    if direct_ext:
        dest = dest_folder / sanitize_filename(url, 1, direct_ext)
        return dest if download_file(url, dest, session) else None

    if not HAS_WEB:
        logger.error("requests/beautifulsoup4 non installati: impossibile contattare l'URL.")
        return None

    logger.info(f"  Richiamo URL: {url}")
    try:
        resp = session.get(url, headers=HEADERS, timeout=TIMEOUT_PAGE)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"  Errore nella richiesta: {e}")
        return None

    content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()

    if content_type and not content_type.startswith("text/html"):
        # La risposta non è una pagina HTML da scansionare: è già il file dati
        # (tipico di endpoint con parametro "export=1" che restituiscono
        # direttamente un CSV/Excel invece di renderizzare una pagina).
        filename = _filename_from_content_disposition(resp.headers.get("Content-Disposition", ""))
        if filename:
            dest = dest_folder / re.sub(r"[^\w\-.() ]", "_", filename)
        else:
            ext = _CONTENT_TYPE_EXT.get(content_type)
            if not ext:
                logger.warning(
                    f"  Content-Type non riconosciuto ({content_type or 'assente'}) e nessun "
                    f"nome file nell'header Content-Disposition: impossibile determinare il formato."
                )
                return None
            dest = dest_folder / sanitize_filename(url, 1, ext)

        dest_folder.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        logger.info(f"  Risposta non-HTML ({content_type}): salvata come {dest.name} ({len(resp.content):,} bytes)")
        return dest

    # È una pagina HTML: scansionala per trovare i link ai file
    links = _extract_links_from_html(url, resp.text)
    for ext in ("csv", "xlsx", "xls", "pdf"):
        for idx, file_url in enumerate(links.get(ext, []), 1):
            dest = dest_folder / sanitize_filename(file_url, idx, ext)
            if download_file(file_url, dest, session):
                return dest
    return None


def sha256_file(path: "str | Path") -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Lettura tabellare (CSV / XLSX / PDF) → (header, rows) di stringhe
# ---------------------------------------------------------------------------

def clean_cell(value) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if len(value) >= 2 and value[0] in ("'", '"') and value[-1] == value[0]:
        value = value[1:-1].strip()
    value = re.sub(r"\n+", " ", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value


def _detect_csv_params(path: Path) -> "tuple[str, str]":
    # Se il file inizia con un BOM UTF-8, va decodificato con "utf-8-sig" per
    # rimuoverlo: provando prima "utf-8" semplice la decodifica riesce comunque
    # (il BOM è una sequenza UTF-8 valida), ma lascia il carattere
    # incollato alla prima cella della prima riga.
    with open(path, "rb") as f:
        if f.read(3) == b"\xef\xbb\xbf":
            sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
            try:
                delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t|").delimiter
            except csv.Error:
                delimiter = ";"
            return "utf-8-sig", delimiter

    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-15"):
        try:
            with open(path, "r", encoding=enc) as f:
                sample = f.read(4096)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        enc = "latin-1"
        with open(path, "r", encoding=enc) as f:
            sample = f.read(4096)

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ";"

    return enc, delimiter


def _read_csv(path: Path) -> "tuple[list[str] | None, list[list[str]]]":
    enc, delimiter = _detect_csv_params(path)
    header = None
    rows = []
    with open(path, "r", encoding=enc, errors="replace") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            cleaned = [clean_cell(c) for c in row]
            if all(c == "" for c in cleaned):
                continue
            if header is None:
                header = cleaned
                continue
            rows.append(cleaned)
    return header, rows


def _read_xlsx(path: Path) -> "tuple[list[str] | None, list[list[str]]]":
    import openpyxl
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", "Workbook contains no default style", UserWarning)
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()

    if not all_rows:
        return None, []

    header = [clean_cell(c) for c in all_rows[0]]
    rows = []
    for row in all_rows[1:]:
        cleaned = [clean_cell(c) for c in row]
        if any(c != "" for c in cleaned):
            rows.append(cleaned)
    return header, rows


def _read_pdf(path: Path) -> "tuple[list[str] | None, list[list[str]]]":
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber non installato: impossibile leggere PDF. pip install pdfplumber")
        return None, []

    header = None
    rows = []
    pdf = pdfplumber.open(path)
    try:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table:
                    cleaned = [clean_cell(c) for c in row]
                    if all(c == "" for c in cleaned):
                        continue
                    if header is None:
                        header = cleaned
                        continue
                    if cleaned[:3] == header[:3]:
                        continue  # intestazione ripetuta su ogni pagina
                    rows.append(cleaned)
    finally:
        pdf.close()
    return header, rows


def read_table(path: "str | Path") -> "tuple[list[str] | None, list[list[str]]]":
    """
    Legge un file tabellare (CSV, XLSX/XLS o PDF) e restituisce (header, rows),
    entrambi liste di stringhe pulite. header è None se il file non contiene dati.
    """
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".csv":
        return _read_csv(path)
    if ext in (".xlsx", ".xls"):
        return _read_xlsx(path)
    if ext == ".pdf":
        return _read_pdf(path)
    raise ValueError(f"Formato non supportato: {ext} ({path.name})")


def find_col(header_norm: "list[str]", aliases: "frozenset[str] | set[str]") -> "int | None":
    """
    Trova l'indice della colonna che corrisponde a uno degli alias.
    Prima cerca un match esatto (case-insensitive, già normalizzato), poi
    un match parziale (substring) per gli alias più lunghi di 4 caratteri.
    """
    for i, c in enumerate(header_norm):
        if c in aliases:
            return i
    for i, c in enumerate(header_norm):
        for a in aliases:
            if len(a) > 4 and (a in c or c in a):
                return i
    return None


def parse_amount(value) -> "float | None":
    """Converte un valore grezzo (stringa con virgola/punto, o numero) in float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    s = s.replace("€", "").strip()
    # Formato italiano: punto = separatore migliaia, virgola = decimali.
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif "." in s:
        # Solo punto, nessuna virgola: ambiguo tra migliaia ("941.704" → 941704)
        # e decimale ("123.5" → 123.5). Più punti, o un solo punto seguito da
        # esattamente 3 cifre (il raggruppamento italiano standard), sono
        # trattati come separatore delle migliaia — l'uso più comune nelle
        # fonti pubbliche italiane per conteggi/importi senza decimali.
        parts = s.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[-1]) == 3):
            s = s.replace(".", "")
    s = re.sub(r"[^\d.\-]", "", s)
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_int(value) -> "int | None":
    f = parse_amount(value)
    return int(round(f)) if f is not None else None
