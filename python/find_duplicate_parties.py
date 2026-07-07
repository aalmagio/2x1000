#!/usr/bin/env python3
"""
find_duplicate_parties.py — Individua candidati partiti duplicati
nell'anagrafica, usando tre segnali in ordine di affidabilità decrescente:

  1. CODICE CONDIVISO (alta confidenza): l'Agenzia delle Entrate non
     riassegna mai un codice (es. "C12") a un partito diverso. Se due
     party_id distinti hanno usato lo stesso codice in anni diversi, sono
     quasi certamente lo stesso partito, scritto con ortografia diversa a
     seconda della fonte/anno.

  2. STESSA "CHIAVE GREZZA" (media confidenza): rimuovendo tutta la
     punteggiatura dal nome (non solo convertendola in "-", come fa
     slugify()) restano le stesse lettere. Coglie casi come
     "Demo. S" / "DemoS" che slugify() tratta come diversi.

  3. SOMIGLIANZA TESTUALE (bassa confidenza, solo per revisione manuale):
     nomi molto simili (refusi di trascrizione tipo "d'ltalia" per
     "d'Italia") che superano una soglia di similarità. Non implica affatto
     che siano lo stesso partito: va sempre verificato a mano, magari
     controllando se gli anni di presenza sono consecutivi (rinomina reale)
     o si sovrappongono (entità diverse nello stesso anno).

Non modifica il database: produce solo un report. Per unire due partiti
confermati come duplicati, usare merge_parties.py.

Uso:
    python find_duplicate_parties.py
"""

from __future__ import annotations

import difflib
import re
from collections import defaultdict

from common import load_dotenv
from db import get_connection


def loose_key(name: str) -> str:
    """Nome ridotto alle sole lettere/cifre minuscole, senza punteggiatura né spazi."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def fetch_parties(cur) -> list[dict]:
    cur.execute("SELECT id, canonical_name, slug, first_year, last_year FROM parties ORDER BY canonical_name")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_codes_by_party(cur) -> dict[int, set[str]]:
    cur.execute("SELECT party_id, code FROM party_codes")
    result: dict[int, set[str]] = defaultdict(set)
    for party_id, code in cur.fetchall():
        result[party_id].add(code)
    return result


def print_group(title: str, parties: list[dict]) -> None:
    print(f"\n  {title}")
    for p in sorted(parties, key=lambda x: (x["first_year"] or 0)):
        years = f"{p['first_year']}–{p['last_year']}" if p["first_year"] else "—"
        print(f"    id={p['id']:<4} {p['canonical_name']!r:55} slug={p['slug']:40} anni={years}")


def main():
    load_dotenv()
    conn = get_connection()
    with conn.cursor() as cur:
        parties = fetch_parties(cur)
        codes_by_party = fetch_codes_by_party(cur)

        # 1. Stesso codice usato da più party_id diversi
        code_to_parties: dict[str, set[int]] = defaultdict(set)
        for party_id, codes in codes_by_party.items():
            for code in codes:
                code_to_parties[code].add(party_id)

        by_id = {p["id"]: p for p in parties}
        seen_in_code_groups: set[int] = set()

        print("=" * 70)
        print("1. STESSO CODICE AdE USATO DA PIÙ PARTITI (alta confidenza)")
        print("=" * 70)
        found_any = False
        for code, party_ids in sorted(code_to_parties.items()):
            if len(party_ids) > 1:
                found_any = True
                seen_in_code_groups |= party_ids
                print_group(f"Codice {code!r}:", [by_id[pid] for pid in party_ids if pid in by_id])
        if not found_any:
            print("  Nessun caso trovato.")

        # 2. Stessa chiave grezza (punteggiatura diversa, stesse lettere)
        loose_groups: dict[str, list[dict]] = defaultdict(list)
        for p in parties:
            loose_groups[loose_key(p["canonical_name"])].append(p)

        print("\n" + "=" * 70)
        print("2. STESSA CHIAVE SENZA PUNTEGGIATURA (media confidenza)")
        print("=" * 70)
        found_any = False
        for key, group in sorted(loose_groups.items()):
            if len(group) > 1:
                found_any = True
                print_group(f"Chiave {key!r}:", group)
        if not found_any:
            print("  Nessun caso trovato.")

        # 3. Somiglianza testuale tra chiavi diverse (refusi) — solo per revisione manuale
        #
        # Soglia alta (0.95) e lunghezza minima (12 caratteri): su stringhe
        # corte, una sola lettera diversa alla fine (es. "Partito Demo A" vs
        # "Partito Demo B", chiaramente due entità diverse) produce comunque
        # un rapporto di similarità alto (~0.92) perché il resto della
        # stringa coincide — un falso positivo quasi garantito. Un vero
        # refuso di trascrizione su un nome lungo (es. "d'ltalia" per
        # "d'Italia" dentro un nome di 30+ caratteri) resta sopra 0.95.
        print("\n" + "=" * 70)
        print("3. NOMI SIMILI MA NON IDENTICI (bassa confidenza — verificare a mano)")
        print("=" * 70)
        SIMILARITY_THRESHOLD = 0.95
        MIN_KEY_LENGTH = 12
        keys = [k for k in loose_groups if len(k) >= MIN_KEY_LENGTH]
        found_any = False
        reported_pairs: set[frozenset] = set()
        for i, key_a in enumerate(keys):
            for key_b in keys[i + 1:]:
                if key_a == key_b:
                    continue
                ratio = difflib.SequenceMatcher(None, key_a, key_b).ratio()
                if ratio >= SIMILARITY_THRESHOLD:
                    pair = frozenset((key_a, key_b))
                    if pair in reported_pairs:
                        continue
                    reported_pairs.add(pair)
                    found_any = True
                    print(f"\n  Somiglianza {ratio:.0%} tra:")
                    print_group("", loose_groups[key_a])
                    print_group("", loose_groups[key_b])
        if not found_any:
            print("  Nessun caso trovato.")

        print("\n" + "=" * 70)
        print(f"Totale partiti in anagrafica: {len(parties)}")
        print("Per unire due partiti confermati come duplicati:")
        print("  python merge_parties.py --keep <slug-corretto> --merge <slug-da-eliminare>")


if __name__ == "__main__":
    main()
