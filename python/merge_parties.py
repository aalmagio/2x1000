#!/usr/bin/env python3
"""
merge_parties.py — Unisce due righe duplicate dell'anagrafica partiti in una
sola, dopo che sono state confermate come lo stesso partito reale (es. con
l'aiuto di find_duplicate_parties.py).

Cosa fa, in una singola transazione:
  1. Sposta tutte le righe di `results`, `party_codes` e `regional_results`
     del partito "merge" sotto il party_id del partito "keep". Se per lo
     stesso anno (o stesso anno+regione per regional_results) esistono
     già righe per entrambi (un vero conflitto, non solo un doppione), NON
     sovrascrive: lascia la riga di "keep" e segnala il conflitto per una
     verifica manuale.
  2. Registra il nome del partito "merge" come alias storico in
     `party_aliases`, con gli anni in cui era in uso, così il nome non
     scompare dallo storico anche se non è più quello canonico.
  3. Estende first_year/last_year del partito "keep" per includere l'intero
     intervallo del partito "merge".
  4. Elimina la riga (ora vuota) del partito "merge".

Uso:
    python merge_parties.py --keep fratelli-d-italia --merge fratelli-d-italia-alleanza-nazionale
    python merge_parties.py --keep ... --merge ... --dry-run   # mostra cosa farebbe, senza scrivere
"""

from __future__ import annotations

import argparse
import logging
import sys

from common import get_logger, load_dotenv
from db import get_connection


def fetch_party(cur, slug: str) -> "dict | None":
    cur.execute(
        "SELECT id, canonical_name, slug, first_year, last_year FROM parties WHERE slug = %s",
        (slug,),
    )
    row = cur.fetchone()
    if not row:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


def main():
    parser = argparse.ArgumentParser(description="Unisce due partiti duplicati nell'anagrafica")
    parser.add_argument("--keep", required=True, help="Slug del partito da mantenere (diventa quello canonico)")
    parser.add_argument("--merge", required=True, help="Slug del partito da unire ed eliminare")
    parser.add_argument("--dry-run", action="store_true", help="Mostra cosa farebbe senza scrivere nel database")
    args = parser.parse_args()

    get_logger("merge_parties", None)
    load_dotenv()

    if args.keep == args.merge:
        logging.error("--keep e --merge non possono essere lo stesso slug")
        sys.exit(1)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            keep = fetch_party(cur, args.keep)
            merge = fetch_party(cur, args.merge)

            if keep is None:
                logging.error(f"Partito non trovato per slug: {args.keep}")
                sys.exit(1)
            if merge is None:
                logging.error(f"Partito non trovato per slug: {args.merge}")
                sys.exit(1)

            logging.info(f"Mantengo:  #{keep['id']}  {keep['canonical_name']!r}  ({keep['slug']})")
            logging.info(f"Unisco:    #{merge['id']}  {merge['canonical_name']!r}  ({merge['slug']})")

            # --- results: sposta, salta i conflitti (stesso anno su entrambi) ---
            cur.execute("SELECT declaration_year FROM results WHERE party_id = %s", (merge["id"],))
            merge_result_years = {r[0] for r in cur.fetchall()}
            cur.execute("SELECT declaration_year FROM results WHERE party_id = %s", (keep["id"],))
            keep_result_years = {r[0] for r in cur.fetchall()}
            conflicting_result_years = merge_result_years & keep_result_years
            movable_result_years = merge_result_years - conflicting_result_years

            # --- party_codes: stessa logica ---
            cur.execute("SELECT declaration_year FROM party_codes WHERE party_id = %s", (merge["id"],))
            merge_code_years = {r[0] for r in cur.fetchall()}
            cur.execute("SELECT declaration_year FROM party_codes WHERE party_id = %s", (keep["id"],))
            keep_code_years = {r[0] for r in cur.fetchall()}
            conflicting_code_years = merge_code_years & keep_code_years
            movable_code_years = merge_code_years - conflicting_code_years

            # --- regional_results: chiave (declaration_year, region), stessa logica ---
            cur.execute("SELECT declaration_year, region FROM regional_results WHERE party_id = %s", (merge["id"],))
            merge_regional_keys = {(r[0], r[1]) for r in cur.fetchall()}
            cur.execute("SELECT declaration_year, region FROM regional_results WHERE party_id = %s", (keep["id"],))
            keep_regional_keys = {(r[0], r[1]) for r in cur.fetchall()}
            conflicting_regional_keys = merge_regional_keys & keep_regional_keys
            movable_regional_keys = merge_regional_keys - conflicting_regional_keys

            if conflicting_result_years:
                logging.warning(
                    f"Conflitto in results per gli anni {sorted(conflicting_result_years)}: "
                    f"esiste già una riga per #{keep['id']} in quegli anni. "
                    f"La riga di #{merge['id']} per quegli anni NON verrà spostata "
                    f"(resta collegata al partito eliminato finché non la risolvi a mano)."
                )
            if conflicting_code_years:
                logging.warning(
                    f"Conflitto in party_codes per gli anni {sorted(conflicting_code_years)}: "
                    f"stesso motivo, riga non spostata."
                )
            if conflicting_regional_keys:
                logging.warning(
                    f"Conflitto in regional_results per (anno, regione) {sorted(conflicting_regional_keys)}: "
                    f"stesso motivo, riga non spostata."
                )

            new_first = min(x for x in (keep["first_year"], merge["first_year"]) if x is not None)
            new_last = max(x for x in (keep["last_year"], merge["last_year"]) if x is not None)

            logging.info(
                f"results: {len(movable_result_years)} anni spostati, {len(conflicting_result_years)} in conflitto (non spostati)"
            )
            logging.info(
                f"party_codes: {len(movable_code_years)} anni spostati, {len(conflicting_code_years)} in conflitto (non spostati)"
            )
            logging.info(
                f"regional_results: {len(movable_regional_keys)} righe spostate, {len(conflicting_regional_keys)} in conflitto (non spostate)"
            )
            logging.info(f"first_year/last_year di #{keep['id']}: {keep['first_year']}–{keep['last_year']} -> {new_first}–{new_last}")
            logging.info(f"Alias registrato: {merge['canonical_name']!r} ({merge['first_year']}–{merge['last_year']})")

            if args.dry_run:
                logging.info("[DRY-RUN] Nessuna modifica scritta.")
                return

            if movable_result_years:
                cur.execute(
                    "UPDATE results SET party_id = %s WHERE party_id = %s AND declaration_year IN %s",
                    (keep["id"], merge["id"], tuple(movable_result_years)),
                ) if len(movable_result_years) > 1 else cur.execute(
                    "UPDATE results SET party_id = %s WHERE party_id = %s AND declaration_year = %s",
                    (keep["id"], merge["id"], next(iter(movable_result_years))),
                )

            if movable_code_years:
                cur.execute(
                    "UPDATE party_codes SET party_id = %s WHERE party_id = %s AND declaration_year IN %s",
                    (keep["id"], merge["id"], tuple(movable_code_years)),
                ) if len(movable_code_years) > 1 else cur.execute(
                    "UPDATE party_codes SET party_id = %s WHERE party_id = %s AND declaration_year = %s",
                    (keep["id"], merge["id"], next(iter(movable_code_years))),
                )

            for year, region in movable_regional_keys:
                cur.execute(
                    "UPDATE regional_results SET party_id = %s WHERE party_id = %s AND declaration_year = %s AND region = %s",
                    (keep["id"], merge["id"], year, region),
                )

            cur.execute("UPDATE party_aliases SET party_id = %s WHERE party_id = %s", (keep["id"], merge["id"]))

            cur.execute(
                """
                INSERT INTO party_aliases (party_id, alias_name, year_from, year_to, source, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    keep["id"], merge["canonical_name"], merge["first_year"], merge["last_year"],
                    "merge_parties.py",
                    f"Unito da partito duplicato #{merge['id']} (slug: {merge['slug']})",
                ),
            )

            cur.execute(
                "UPDATE parties SET first_year = %s, last_year = %s WHERE id = %s",
                (new_first, new_last, keep["id"]),
            )

            # Il partito "merge" ora ha solo le righe in conflitto (se ce ne sono);
            # se non ne ha più, si può eliminare. Se restano righe in conflitto in
            # results/party_codes/regional_results, la FK CASCADE le eliminerebbe:
            # meglio bloccarsi e lasciare la decisione a chi esegue lo script.
            cur.execute("SELECT COUNT(*) FROM results WHERE party_id = %s", (merge["id"],))
            remaining_results = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM party_codes WHERE party_id = %s", (merge["id"],))
            remaining_codes = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM regional_results WHERE party_id = %s", (merge["id"],))
            remaining_regional = cur.fetchone()[0]

            if remaining_results or remaining_codes or remaining_regional:
                conn.commit()
                logging.warning(
                    f"Partito #{merge['id']} NON eliminato: restano {remaining_results} righe in results, "
                    f"{remaining_codes} in party_codes e {remaining_regional} in regional_results per gli anni/regioni "
                    f"in conflitto elencati sopra. Risolvi il conflitto a mano, poi ri-esegui per completare l'unione."
                )
                return

            cur.execute("DELETE FROM parties WHERE id = %s", (merge["id"],))
            conn.commit()
            logging.info(f"Completato: partito #{merge['id']} unito in #{keep['id']} ed eliminato.")

    except Exception:
        conn.rollback()
        logging.error("Errore durante l'unione: rollback eseguito", exc_info=True)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
