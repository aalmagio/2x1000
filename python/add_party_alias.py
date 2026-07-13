#!/usr/bin/env python3
"""
add_party_alias.py — Registra rapidamente una grafia alternativa (alias) di
un partito già presente in anagrafica, senza fare un merge completo.

Utile in particolare per i nomi che compaiono SOLO nei file di ripartizione
regionale (che intestano le colonne col nome del partito, non col codice):
db_updater.py scarta le righe il cui nome non riconosce e le elenca a fine
esecuzione — questo script serve a registrare quel nome come alias del
partito corretto, così un rilancio di db_updater.py lo risolve.

Per unire due partiti che hanno GIÀ ciascuno righe proprie in results/
party_codes (veri duplicati nell'anagrafica, non solo un nome che compare
altrove), usare merge_parties.py, non questo script.

Uso:
    python add_party_alias.py --party fratelli-d-italia --alias "Fratelli d'Italia Alleanza Nazionale"
    python add_party_alias.py --party fratelli-d-italia --alias "..." --year-from 2013 --year-to 2017
"""

from __future__ import annotations

import argparse
import logging
import sys

from common import get_logger, load_dotenv
from db import get_connection


def main():
    parser = argparse.ArgumentParser(description="Registra un alias (grafia alternativa) per un partito esistente")
    parser.add_argument("--party", required=True, help="Slug del partito a cui associare l'alias")
    parser.add_argument("--alias", required=True, help="Testo esatto della grafia alternativa da registrare")
    parser.add_argument("--year-from", type=int, default=None, help="Primo anno in cui è stata usata questa grafia")
    parser.add_argument("--year-to", type=int, default=None, help="Ultimo anno in cui è stata usata questa grafia")
    parser.add_argument("--source", default="add_party_alias.py", help="Nota sulla provenienza (default: nome script)")
    args = parser.parse_args()

    get_logger("add_party_alias", None)
    load_dotenv()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, canonical_name FROM parties WHERE slug = %s", (args.party,))
            row = cur.fetchone()
            if row is None:
                logging.error(f"Partito non trovato per slug: {args.party}")
                sys.exit(1)
            party_id, canonical_name = row

            cur.execute(
                "SELECT id FROM party_aliases WHERE party_id = %s AND alias_name = %s",
                (party_id, args.alias),
            )
            if cur.fetchone():
                logging.info(f"Alias già presente per #{party_id} ({canonical_name!r}): {args.alias!r} — nulla da fare.")
                return

            cur.execute(
                """
                INSERT INTO party_aliases (party_id, alias_name, year_from, year_to, source, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (party_id, args.alias, args.year_from, args.year_to, args.source, None),
            )
            conn.commit()
            logging.info(f"Alias registrato per #{party_id} ({canonical_name!r}): {args.alias!r}")
            logging.info(
                "Aggiorna l'archivio versionato: python sync_party_aliases.py --export "
                "e committa data/reference/party_aliases.csv"
            )
    except Exception:
        conn.rollback()
        logging.error("Errore durante l'inserimento: rollback eseguito", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
