#!/usr/bin/env python3
"""
pipeline.py — Orchestratore della pipeline Python di acquisizione dati 2x1000
(analogo a pipeline.py del progetto 5x1000, adattato al flusso più semplice
del 2x1000).

Esegue in sequenza:
  1. acquire_results.py            — risultati annuali dal MEF
  2. acquire_party_codes.py        — elenco partiti ammessi e codici dall'AdE
  3. acquire_regional_results.py   — ripartizione regionale delle scelte dal MEF
  4. db_updater.py                 — scrive i dati normalizzati nel database MySQL
  5. scripts/calculate_indicators.php  — calcola quote, ranking, medie, concentrazione
  6. scripts/export_open_data.php      — rigenera i CSV/JSON pubblicati in data/exports/

I passi 4 e 5 sono script PHP già esistenti nel progetto (scripts/): la
pipeline Python li richiama invece di duplicarne la logica di calcolo, così
i numeri restano identici indipendentemente dal fatto che l'import sia
avvenuto via CSV manuale (import_results.php) o via questa pipeline.

Uso:
    python pipeline.py --anni 2024                       # tutti gli step, anno 2024
    python pipeline.py --anni 2024 --skip-download        # riusa i file già in data/raw/
    python pipeline.py --anni 2024 --only db,indicators,export
    python pipeline.py --anni 2024 --dry-run              # non scrive nel DB, mostra solo cosa farebbe
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

from common import REPO_ROOT, get_logger, load_config, load_dotenv

STEPS_ALL = ["acquire_results", "acquire_codes", "acquire_geo", "db", "indicators", "export"]

PYTHON_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable or "python3"

_DEFAULT_STEP_TIMEOUT = 1800


def run_step(name: str, cmd: "list[str]", cwd: Path, timeout: int) -> bool:
    logging.info(f"\n{'=' * 60}")
    logging.info(f"STEP: {name}")
    logging.info(f"Comando: {' '.join(cmd)}")
    logging.info(f"{'=' * 60}")

    start = time.time()
    proc = None
    try:
        proc = subprocess.Popen(cmd, cwd=cwd)
        proc.wait(timeout=timeout)
        elapsed = time.time() - start
        if proc.returncode == 0:
            logging.info(f"[OK] {name} completato in {elapsed:.0f}s")
            return True
        logging.error(f"[ERRORE] {name} fallito (exit code {proc.returncode})")
        return False
    except subprocess.TimeoutExpired:
        logging.error(f"[TIMEOUT] {name} interrotto dopo {timeout}s")
        if proc is not None:
            proc.kill()
            proc.wait()
        return False
    except Exception as e:
        logging.error(f"[ERRORE] {name}: {e}")
        if proc is not None:
            try:
                proc.kill()
                proc.wait()
            except Exception:
                pass
        return False


def parse_args():
    parser = argparse.ArgumentParser(
        description="2x1000 — Pipeline di acquisizione e aggiornamento dati (fonti → DB)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Esempi:
  %(prog)s --anni 2024
  %(prog)s --anni 2024 --skip-download
  %(prog)s --anni 2024 --only db,indicators,export
  %(prog)s --anni 2024 --dry-run
""",
    )
    parser.add_argument("--anni", type=str, default=None,
                         help="Anni da elaborare, separati da virgola (es. 2023,2024). "
                              "Se omesso, usa gli anni configurati in config.yaml.")
    parser.add_argument("--skip-download", action="store_true",
                         help="Non scaricare: usa i file già presenti in data/raw/")
    parser.add_argument("--only", type=str, default=None,
                         help=f"Esegue solo gli step indicati, separati da virgola. "
                              f"Disponibili: {','.join(STEPS_ALL)}")
    parser.add_argument("--dry-run", action="store_true",
                         help="Passa --dry-run allo step 'db' (non scrive nulla nel database)")
    return parser.parse_args()


def main():
    args = parse_args()
    get_logger("pipeline", PYTHON_DIR)
    load_dotenv()
    cfg = load_config()
    pipeline_cfg = cfg.get("pipeline", {})
    timeouts = pipeline_cfg.get("step_timeouts", {})
    php_binary = pipeline_cfg.get("php_binary", "php")

    steps = STEPS_ALL
    if args.only:
        requested = [s.strip() for s in args.only.split(",") if s.strip()]
        invalid = [s for s in requested if s not in STEPS_ALL]
        if invalid:
            logging.error(f"Step non validi: {invalid}. Disponibili: {STEPS_ALL}")
            sys.exit(1)
        steps = requested

    print("\n" + "=" * 60)
    print("  2x1000 — Pipeline acquisizione e aggiornamento dati")
    print("=" * 60)

    results = {}

    if "acquire_results" in steps:
        cmd = [PYTHON, "acquire_results.py"]
        if args.anni:
            cmd += ["--anni", args.anni]
        if args.skip_download:
            cmd += ["--no-download"]
        results["acquire_results"] = run_step(
            "acquire_results", cmd, PYTHON_DIR, timeouts.get("acquire_results", _DEFAULT_STEP_TIMEOUT)
        )

    if "acquire_codes" in steps:
        cmd = [PYTHON, "acquire_party_codes.py"]
        if args.anni:
            cmd += ["--anni", args.anni]
        if args.skip_download:
            cmd += ["--no-download"]
        results["acquire_codes"] = run_step(
            "acquire_codes", cmd, PYTHON_DIR, timeouts.get("acquire_codes", _DEFAULT_STEP_TIMEOUT)
        )

    if "acquire_geo" in steps:
        cmd = [PYTHON, "acquire_regional_results.py"]
        if args.anni:
            cmd += ["--anni", args.anni]
        if args.skip_download:
            cmd += ["--no-download"]
        results["acquire_geo"] = run_step(
            "acquire_geo", cmd, PYTHON_DIR, timeouts.get("acquire_geo", _DEFAULT_STEP_TIMEOUT)
        )

    if "db" in steps:
        cmd = [PYTHON, "db_updater.py"]
        if args.anni:
            cmd += ["--anni", args.anni]
        if args.dry_run:
            cmd += ["--dry-run"]
        results["db"] = run_step("db", cmd, PYTHON_DIR, timeouts.get("db", _DEFAULT_STEP_TIMEOUT))

    if "indicators" in steps and not args.dry_run:
        cmd = [php_binary, "scripts/calculate_indicators.php"]
        results["indicators"] = run_step(
            "indicators", cmd, REPO_ROOT, timeouts.get("indicators", _DEFAULT_STEP_TIMEOUT)
        )

    if "export" in steps and not args.dry_run:
        cmd = [php_binary, "scripts/export_open_data.php"]
        results["export"] = run_step(
            "export", cmd, REPO_ROOT, timeouts.get("export", _DEFAULT_STEP_TIMEOUT)
        )

    print("\n" + "=" * 60)
    print("  Riepilogo")
    print("=" * 60)
    for step, ok in results.items():
        print(f"  {'OK ' if ok else 'FAIL'} — {step}")

    if any(not ok for ok in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
