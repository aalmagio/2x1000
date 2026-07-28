#!/usr/bin/env python3
"""
backfill_region_ids.py — Valorizza regional_results.region_id sulle righe già
importate prima della normalizzazione delle regioni (tabella `regions`).

Da eseguire una sola volta dopo database/migrations.sql; le importazioni
successive (db_updater.py) valorizzano region_id da sole. Rieseguirlo è
innocuo: aggiorna solo le righe con region_id NULL.

Uso:
    python backfill_region_ids.py            # aggiorna
    python backfill_region_ids.py --dry-run  # mostra solo cosa farebbe
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from common import get_logger, load_dotenv
from db import db_available, get_connection
from region_resolver import resolve_region_slug


def main():
    parser = argparse.ArgumentParser(
        description="2x1000 — Backfill di regional_results.region_id dalle etichette regione")
    parser.add_argument("--dry-run", action="store_true",
                         help="Mostra le corrispondenze senza scrivere nulla")
    args = parser.parse_args()

    get_logger("backfill_region_ids", Path(__file__).resolve().parent)
    load_dotenv()

    if not db_available():
        logging.error("Database non configurato o pymysql non installato (verifica .env).")
        sys.exit(1)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute("SELECT slug, id FROM regions")
            except Exception:
                logging.error(
                    "Tabella `regions` non trovata: esegui prima database/schema.sql "
                    "e database/migrations.sql.")
                sys.exit(1)
            region_index = {slug: region_id for slug, region_id in cur.fetchall()}

            cur.execute(
                "SELECT region, COUNT(*) FROM regional_results "
                "WHERE region_id IS NULL GROUP BY region ORDER BY region")
            pending = cur.fetchall()

            if not pending:
                logging.info("Nessuna riga con region_id NULL: niente da fare.")
                return

            unresolved = []
            updated_total = 0
            for label, row_count in pending:
                slug = resolve_region_slug(label, region_index)
                if slug is None:
                    unresolved.append((label, row_count))
                    continue
                region_id = region_index[slug]
                logging.info(f"{label!r} -> {slug} (id {region_id}), {row_count} righe")
                if not args.dry_run:
                    cur.execute(
                        "UPDATE regional_results SET region_id = %s "
                        "WHERE region = %s AND region_id IS NULL",
                        (region_id, label))
                    updated_total += cur.rowcount

        if args.dry_run:
            logging.info("[DRY-RUN] Nessuna modifica scritta.")
        else:
            conn.commit()
            logging.info(f"Completato: {updated_total} righe aggiornate (commit ok).")

        if unresolved:
            logging.warning(f"{len(unresolved)} etichette non riconosciute (region_id resta NULL):")
            for label, row_count in unresolved:
                logging.warning(f"  - {label!r} ({row_count} righe)")
            logging.warning(
                "Aggiungi le grafie a REGION_ALIAS_SLUGS in region_resolver.py e rilancia.")
    except Exception:
        conn.rollback()
        logging.error("Errore durante il backfill: rollback eseguito", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
