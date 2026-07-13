#!/usr/bin/env python3
"""
validate_data.py — Controlli di riconciliazione post-import sul database.

I parser di acquisizione lavorano per euristiche (alias di colonna, formati
numerici ambigui): un errore di parsing può finire in produzione in silenzio.
Questo script verifica che i dati scritti nel database siano internamente
coerenti e coerenti con i totali dichiarati dalle fonti ufficiali:

  1. TOTALI DI CONTROLLO — la somma di scelte/importo in `results` per anno
     deve coincidere con la riga "Totale" del file MEF originale (salvata da
     acquire_results.py in mef_results_<anno>.meta.json);
  2. REGIONALE vs NAZIONALE — per ogni partito/anno, la somma delle scelte
     nella ripartizione regionale non può superare il dato nazionale; se
     nessuna regione è oscurata deve coincidere esattamente; se ci sono
     valori oscurati, uno scarto oltre soglia è segnalato come warning;
  3. RISULTATI vs CODICI — partiti con risultati ma senza codice AdE
     nell'anno (warning: possibile mancato accorpamento di grafie) e codici
     senza risultati (info: può essere un partito ammesso senza scelte);
  4. VARIAZIONI ANOMALE — variazione dei totali di sistema anno su anno
     oltre soglia (default ±50%), tipica spia di un import doppio o monco;
  5. COPERTURA — anni con risultati ma senza ripartizione regionale (info).

Esce con codice 1 se almeno un controllo è FAIL (i warning non bloccano).

Uso:
    python validate_data.py                  # tutti gli anni presenti nel DB
    python validate_data.py --anni 2023,2024
    python validate_data.py --gap-threshold 2 --yoy-threshold 50
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from common import REPO_ROOT, get_logger, load_dotenv
from db import db_available, get_connection

logger = logging.getLogger(__name__)

FAIL = "FAIL"
WARN = "WARN"
INFO = "INFO"

# Tolleranza sul confronto dell'importo totale (euro): la fonte può
# arrotondare al centesimo in modo diverso dalla somma delle righe.
AMOUNT_TOLERANCE = 1.0


def finding(level: str, year: "int | None", check: str, message: str) -> dict:
    return {"level": level, "year": year, "check": check, "message": message}


# ---------------------------------------------------------------------------
# Logica di confronto (funzioni pure, testate in python/tests/)
# ---------------------------------------------------------------------------

def check_control_totals(year: int, meta: dict, db_choices: "int | None",
                          db_amount: "float | None") -> "list[dict]":
    """Confronta SUM(results) con la riga 'Totale' del file MEF (meta.json)."""
    findings = []
    ctrl_choices = meta.get("control_total_choices")
    ctrl_amount = meta.get("control_total_amount")

    if ctrl_choices is None and ctrl_amount is None:
        findings.append(finding(
            INFO, year, "totali-controllo",
            "Nessun totale di controllo nel meta.json (file acquisito prima "
            "dell'introduzione del controllo, o fonte senza riga 'Totale'): "
            "riesegui acquire_results.py per generarlo."))
        return findings

    if ctrl_choices is not None and db_choices is not None and int(ctrl_choices) != int(db_choices):
        findings.append(finding(
            FAIL, year, "totali-controllo",
            f"Somma scelte in `results` ({db_choices:,}) diversa dal totale "
            f"dichiarato dal file MEF ({int(ctrl_choices):,}): possibile riga "
            f"persa/duplicata o colonna agganciata male."))
    if ctrl_amount is not None and db_amount is not None and abs(float(ctrl_amount) - float(db_amount)) > AMOUNT_TOLERANCE:
        findings.append(finding(
            FAIL, year, "totali-controllo",
            f"Somma importi in `results` ({db_amount:,.2f} €) diversa dal totale "
            f"dichiarato dal file MEF ({float(ctrl_amount):,.2f} €)."))

    if not findings:
        findings.append(finding(INFO, year, "totali-controllo", "Totali di controllo MEF coincidono."))
    return findings


def check_regional_row(year: int, party_name: str, national: int,
                        regional_sum: "int | None", suppressed_count: int,
                        gap_threshold_pct: float) -> "list[dict]":
    """Coerenza regionale vs nazionale per un singolo partito/anno."""
    findings = []
    regional_sum = int(regional_sum or 0)

    if regional_sum > national:
        findings.append(finding(
            FAIL, year, "regionale-vs-nazionale",
            f"{party_name}: somma regionale ({regional_sum:,}) SUPERIORE al "
            f"dato nazionale ({national:,}) — dato regionale errato o "
            f"partito risolto sulla riga sbagliata."))
    elif suppressed_count == 0 and regional_sum != national:
        findings.append(finding(
            FAIL, year, "regionale-vs-nazionale",
            f"{party_name}: somma regionale ({regional_sum:,}) diversa dal "
            f"nazionale ({national:,}) senza alcun valore oscurato che lo "
            f"giustifichi."))
    elif suppressed_count > 0 and national > 0:
        gap_pct = (national - regional_sum) / national * 100
        if gap_pct > gap_threshold_pct:
            findings.append(finding(
                WARN, year, "regionale-vs-nazionale",
                f"{party_name}: scarto regionale/nazionale {gap_pct:.1f}% "
                f"({regional_sum:,} vs {national:,}) con {suppressed_count} "
                f"valori oscurati — atteso uno scarto piccolo, verifica."))
    return findings


def check_yoy_change(year: int, prev_year: int, label: str, current: float,
                      previous: float, threshold_pct: float) -> "list[dict]":
    """Variazione anno-su-anno dei totali di sistema oltre soglia."""
    if previous <= 0:
        return []
    change_pct = (current - previous) / previous * 100
    if abs(change_pct) > threshold_pct:
        return [finding(
            WARN, year, "variazione-annua",
            f"{label}: variazione {change_pct:+.1f}% rispetto al {prev_year} "
            f"({previous:,.0f} → {current:,.0f}) — oltre la soglia del "
            f"{threshold_pct:.0f}%, verifica che l'import sia completo e non doppio.")]
    return []


# ---------------------------------------------------------------------------
# Esecuzione dei controlli sul database
# ---------------------------------------------------------------------------

def load_meta_for_year(processed_dir: Path, year: int) -> "dict | None":
    meta_path = processed_dir / f"mef_results_{year}.meta.json"
    if meta_path.is_file():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"meta.json illeggibile per il {year}: {e}")
    return None


def run_checks(cur, years: "list[int]", processed_dir: Path,
               gap_threshold: float, yoy_threshold: float) -> "list[dict]":
    findings: list[dict] = []

    # Somme per anno da results (base per controlli 1 e 4)
    cur.execute(
        "SELECT declaration_year, SUM(valid_choices), SUM(amount), COUNT(*) "
        "FROM results GROUP BY declaration_year ORDER BY declaration_year")
    sums_by_year = {int(y): (int(c), float(a), int(n)) for y, c, a, n in cur.fetchall()}

    for year in years:
        if year not in sums_by_year:
            findings.append(finding(WARN, year, "presenza-dati",
                                     "Nessuna riga in `results` per quest'anno."))
            continue
        db_choices, db_amount, n_rows = sums_by_year[year]
        findings.append(finding(INFO, year, "presenza-dati",
                                 f"{n_rows} partiti, {db_choices:,} scelte, {db_amount:,.2f} €."))

        # 1. Totali di controllo dal file MEF
        meta = load_meta_for_year(processed_dir, year)
        if meta is not None:
            findings.extend(check_control_totals(year, meta, db_choices, db_amount))

        # 4. Variazione anno su anno
        prev = sums_by_year.get(year - 1)
        if prev:
            findings.extend(check_yoy_change(year, year - 1, "Scelte totali",
                                              db_choices, prev[0], yoy_threshold))
            findings.extend(check_yoy_change(year, year - 1, "Importo totale",
                                              db_amount, prev[1], yoy_threshold))

        # 2. Regionale vs nazionale per partito
        cur.execute(
            """
            SELECT p.canonical_name, r.valid_choices,
                   SUM(g.valid_choices), SUM(g.is_suppressed)
            FROM results r
            JOIN parties p ON p.id = r.party_id
            JOIN regional_results g
              ON g.party_id = r.party_id AND g.declaration_year = r.declaration_year
            WHERE r.declaration_year = %s
            GROUP BY p.canonical_name, r.valid_choices
            """, (year,))
        regional_rows = cur.fetchall()
        for name, national, regional_sum, suppressed in regional_rows:
            findings.extend(check_regional_row(
                year, name, int(national), regional_sum, int(suppressed or 0), gap_threshold))

        # 5. Copertura regionale
        if not regional_rows:
            findings.append(finding(INFO, year, "copertura-regionale",
                                     "Nessuna ripartizione regionale per quest'anno."))

        # 3a. Risultati senza codice AdE nell'anno
        cur.execute(
            """
            SELECT p.canonical_name
            FROM results r
            JOIN parties p ON p.id = r.party_id
            LEFT JOIN party_codes c
              ON c.party_id = r.party_id AND c.declaration_year = r.declaration_year
            WHERE r.declaration_year = %s AND c.id IS NULL
            ORDER BY r.valid_choices DESC
            """, (year,))
        missing_codes = [row[0] for row in cur.fetchall()]
        if missing_codes:
            sample = ", ".join(missing_codes[:8]) + ("…" if len(missing_codes) > 8 else "")
            findings.append(finding(
                WARN, year, "risultati-senza-codice",
                f"{len(missing_codes)} partiti con risultati ma senza codice AdE "
                f"nell'anno (possibile grafia non accorpata — vedi "
                f"find_duplicate_parties.py): {sample}"))

        # 3b. Codici senza risultati (può essere legittimo: ammesso, zero scelte)
        cur.execute(
            """
            SELECT COUNT(*)
            FROM party_codes c
            LEFT JOIN results r
              ON r.party_id = c.party_id AND r.declaration_year = c.declaration_year
            WHERE c.declaration_year = %s AND r.id IS NULL
            """, (year,))
        codes_without = int(cur.fetchone()[0])
        if codes_without:
            findings.append(finding(
                INFO, year, "codici-senza-risultati",
                f"{codes_without} partiti ammessi (con codice AdE) senza riga "
                f"risultati: normale se non hanno ricevuto scelte, da verificare "
                f"se sono partiti rilevanti."))

    return findings


def report(findings: "list[dict]") -> int:
    """Stampa il report e restituisce l'exit code (1 se almeno un FAIL)."""
    counts = {FAIL: 0, WARN: 0, INFO: 0}
    for f in findings:
        counts[f["level"]] += 1
        year = f["year"] if f["year"] is not None else "-"
        line = f"[{f['level']}] [{year}] ({f['check']}) {f['message']}"
        if f["level"] == FAIL:
            logger.error(line)
        elif f["level"] == WARN:
            logger.warning(line)
        else:
            logger.info(line)

    logger.info("=" * 60)
    logger.info(f"Esito: {counts[FAIL]} FAIL, {counts[WARN]} warning, {counts[INFO]} info")
    if counts[FAIL]:
        logger.error("Riconciliazione FALLITA: correggi i dati segnalati prima di pubblicare.")
        return 1
    logger.info("Riconciliazione OK.")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(
        description="2x1000 — Controlli di riconciliazione post-import sul database")
    parser.add_argument("--anni", type=str, default=None,
                         help="Anni da verificare, separati da virgola (default: tutti quelli in `results`)")
    parser.add_argument("--processed-dir", type=str, default=None,
                         help="Cartella dei meta.json (default: data/processed/)")
    parser.add_argument("--gap-threshold", type=float, default=2.0,
                         help="Soglia %% di scarto regionale/nazionale tollerato in presenza "
                              "di valori oscurati (default: 2)")
    parser.add_argument("--yoy-threshold", type=float, default=50.0,
                         help="Soglia %% di variazione annua dei totali oltre cui segnalare (default: 50)")
    return parser.parse_args()


def main():
    args = parse_args()
    get_logger("validate_data", Path(__file__).resolve().parent)
    load_dotenv()

    if not db_available():
        logging.error(
            "Database non configurato o pymysql non installato. "
            "Verifica .env (DB_HOST/DB_NAME/DB_USER/DB_PASS) e 'pip install pymysql'.")
        sys.exit(1)

    processed_dir = Path(args.processed_dir) if args.processed_dir else REPO_ROOT / "data" / "processed"

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if args.anni:
                years = sorted(int(a.strip()) for a in args.anni.split(",") if a.strip())
            else:
                cur.execute("SELECT DISTINCT declaration_year FROM results ORDER BY declaration_year")
                years = [int(r[0]) for r in cur.fetchall()]

            if not years:
                logging.warning("Nessun anno da verificare (tabella `results` vuota?).")
                sys.exit(0)

            findings = run_checks(cur, years, processed_dir,
                                   args.gap_threshold, args.yoy_threshold)
    finally:
        conn.close()

    sys.exit(report(findings))


if __name__ == "__main__":
    main()
