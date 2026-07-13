"""Test della risoluzione etichetta regione -> slug canonico (region_resolver)."""

import pytest

from region_resolver import resolve_region_slug

# Gli slug seminati in database/schema.sql (tabella `regions`)
KNOWN_SLUGS = {
    "piemonte", "valle-d-aosta", "lombardia",
    "trentino-alto-adige", "trentino-alto-adige-pa-trento", "trentino-alto-adige-pa-bolzano",
    "veneto", "friuli-venezia-giulia", "liguria", "emilia-romagna",
    "toscana", "umbria", "marche", "lazio", "abruzzo", "molise",
    "campania", "puglia", "basilicata", "calabria", "sicilia", "sardegna",
    "non-residenti",
}


@pytest.mark.parametrize("label, expected", [
    # etichette come pubblicate dal MEF (match esatto per slug)
    ("Lombardia", "lombardia"),
    ("Trentino Alto Adige (PA Trento)", "trentino-alto-adige-pa-trento"),
    ("Trentino Alto Adige (PA Bolzano)", "trentino-alto-adige-pa-bolzano"),
    ("Valle d'Aosta", "valle-d-aosta"),
    ("Valle D'Aosta", "valle-d-aosta"),
    ("Friuli Venezia Giulia", "friuli-venezia-giulia"),
    ("Friuli-Venezia Giulia", "friuli-venezia-giulia"),
    ("Emilia Romagna", "emilia-romagna"),
    ("Non residenti", "non-residenti"),
    # varianti note (dizionario alias)
    ("Valle d'Aosta/Vallée d'Aoste", "valle-d-aosta"),
    ("Provincia Autonoma di Trento", "trentino-alto-adige-pa-trento"),
    ("Provincia autonoma di Bolzano", "trentino-alto-adige-pa-bolzano"),
    ("Trentino Alto Adige (P.A. Trento)", "trentino-alto-adige-pa-trento"),
    ("Estero", "non-residenti"),
    ("Residenti all'estero", "non-residenti"),
    ("FRIULI V.G.", "friuli-venezia-giulia"),
])
def test_known_labels_resolved(label, expected):
    assert resolve_region_slug(label, KNOWN_SLUGS) == expected


@pytest.mark.parametrize("label", [
    "Regione Inventata",
    "Totale",
    "",
])
def test_unknown_labels_return_none(label):
    assert resolve_region_slug(label, KNOWN_SLUGS) is None
