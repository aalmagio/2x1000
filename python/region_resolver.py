#!/usr/bin/env python3
"""
region_resolver.py — Risoluzione delle etichette regione delle fonti verso
la tabella normalizzata `regions`.

La ripartizione regionale del MEF intesta le righe con il nome della regione
in testo libero ("Trentino Alto Adige (PA Trento)", "Valle D'Aosta", "Non
residenti"...): la grafia può variare da un anno all'altro. Qui si risolve
ogni etichetta allo slug canonico della tabella `regions` (e quindi al suo
codice ISTAT), con la stessa strategia usata per i partiti: match esatto per
slug, poi dizionario di grafie alternative note. Le etichette non risolte
NON bloccano l'import: la riga viene scritta con region_id NULL e segnalata
a fine esecuzione.
"""

from __future__ import annotations

from common import slugify

# Gli slug canonici seminati in database/regions (database/schema.sql): la
# copia statica serve dove il database non è disponibile o non ancora migrato
# (es. la deduplicazione in acquire_regional_results.py). Il test
# test_region_resolver.py verifica che questa lista e quella usata nei test
# restino allineate.
CANONICAL_REGION_SLUGS = frozenset({
    "piemonte", "valle-d-aosta", "lombardia",
    "trentino-alto-adige", "trentino-alto-adige-pa-trento", "trentino-alto-adige-pa-bolzano",
    "veneto", "friuli-venezia-giulia", "liguria", "emilia-romagna",
    "toscana", "umbria", "marche", "lazio", "abruzzo", "molise",
    "campania", "puglia", "basilicata", "calabria", "sicilia", "sardegna",
    "non-residenti",
})

# Grafie alternative note (slug dell'etichetta di fonte -> slug canonico in
# `regions`). Il match esatto sullo slug canonico copre già i casi comuni
# ("Valle d'Aosta", "Friuli Venezia Giulia", "Trentino Alto Adige (PA
# Trento)"...): qui vanno solo le varianti che slugificano diversamente.
REGION_ALIAS_SLUGS = {
    # Valle d'Aosta: denominazione bilingue usata da alcune fonti ISTAT/MEF
    "valle-d-aosta-vallee-d-aoste": "valle-d-aosta",
    "vallee-d-aoste": "valle-d-aosta",
    # Province Autonome: varianti con punteggiatura o per esteso
    "trentino-alto-adige-p-a-trento": "trentino-alto-adige-pa-trento",
    "provincia-autonoma-di-trento": "trentino-alto-adige-pa-trento",
    "provincia-autonoma-trento": "trentino-alto-adige-pa-trento",
    "pa-trento": "trentino-alto-adige-pa-trento",
    "trentino-alto-adige-p-a-bolzano": "trentino-alto-adige-pa-bolzano",
    "provincia-autonoma-di-bolzano": "trentino-alto-adige-pa-bolzano",
    "provincia-autonoma-bolzano": "trentino-alto-adige-pa-bolzano",
    "pa-bolzano": "trentino-alto-adige-pa-bolzano",
    "trentino-alto-adige-sudtirol": "trentino-alto-adige",
    # Friuli: abbreviazioni
    "friuli-v-g": "friuli-venezia-giulia",
    "friuli": "friuli-venezia-giulia",
    # Contribuenti residenti all'estero
    "estero": "non-residenti",
    "non-residenti-estero": "non-residenti",
    "residenti-all-estero": "non-residenti",
    "residenti-estero": "non-residenti",
}


def resolve_region_slug(label: str, known_slugs: "set[str] | dict") -> "str | None":
    """
    Risolve un'etichetta regione di fonte allo slug canonico della tabella
    `regions`, o None se non riconosciuta. known_slugs: gli slug presenti
    in `regions` (set o dict con gli slug come chiavi).
    """
    slug = slugify(label)
    if slug in known_slugs:
        return slug
    alias = REGION_ALIAS_SLUGS.get(slug)
    if alias is not None and alias in known_slugs:
        return alias
    return None
