"""Test di dedup_duplicate_regions (acquire_regional_results.py).

Regressione osservata in produzione: i file MEF 2015/2016 contengono la
stessa riga-regione due volte con grafie diverse ("Veneto"/"Venero",
"Friuli Venezia Giulia"/"Friulia Venezia Giulia"), gonfiando ogni somma
regionale (scoperto da validate_data.py: somma regionale > nazionale)."""

from acquire_regional_results import dedup_duplicate_regions


def rec(region, party, choices, suppressed=False):
    return {"region": region, "party_name": party,
            "valid_choices": choices, "is_suppressed": suppressed}


def regions_of(records):
    return {r["region"] for r in records}


class TestDedupDuplicateRegions:
    def test_typo_duplicate_dropped_keeps_known_label(self):
        records = [
            rec("Veneto", "Partito A", 100), rec("Veneto", "Partito B", 50),
            rec("Venero", "Partito A", 100), rec("Venero", "Partito B", 50),
            rec("Lombardia", "Partito A", 200), rec("Lombardia", "Partito B", 80),
        ]
        got = dedup_duplicate_regions(records)
        assert regions_of(got) == {"Veneto", "Lombardia"}

    def test_known_label_kept_even_if_typo_comes_first(self):
        records = [
            rec("Venero", "Partito A", 100),
            rec("Veneto", "Partito A", 100),
        ]
        got = dedup_duplicate_regions(records)
        assert regions_of(got) == {"Veneto"}

    def test_friulia_variant(self):
        records = [
            rec("Friuli Venezia Giulia", "Partito A", 25425),
            rec("Friulia Venezia Giulia", "Partito A", 25425),
        ]
        got = dedup_duplicate_regions(records)
        assert regions_of(got) == {"Friuli Venezia Giulia"}

    def test_different_values_not_merged(self):
        # etichette simili ma valori diversi: sono due righe legittime
        records = [
            rec("Veneto", "Partito A", 100),
            rec("Venero", "Partito A", 99),
        ]
        got = dedup_duplicate_regions(records)
        assert regions_of(got) == {"Veneto", "Venero"}

    def test_identical_values_but_different_labels_not_merged(self):
        # due regioni vere con per coincidenza gli stessi numeri: etichette
        # non simili, non vanno mai accorpate
        records = [
            rec("Molise", "Partito A", 1200),
            rec("Umbria", "Partito A", 1200),
        ]
        got = dedup_duplicate_regions(records)
        assert regions_of(got) == {"Molise", "Umbria"}

    def test_pa_rows_with_different_values_survive(self):
        # le due Province Autonome hanno etichette molto simili tra loro:
        # devono sopravvivere entrambe perché i valori differiscono
        records = [
            rec("Trentino Alto Adige (P.A. Trento)", "Partito A", 10462),
            rec("Trentino Alto Adige (P.A. Bolzano)", "Partito A", 13744),
        ]
        got = dedup_duplicate_regions(records)
        assert len(regions_of(got)) == 2

    def test_suppressed_signature_counts(self):
        # firma identica include gli oscuramenti
        records = [
            rec("Veneto", "Partito A", None, suppressed=True),
            rec("Venero", "Partito A", None, suppressed=True),
        ]
        got = dedup_duplicate_regions(records)
        assert regions_of(got) == {"Veneto"}

    def test_no_duplicates_returns_input_unchanged(self):
        records = [rec("Lazio", "Partito A", 1), rec("Campania", "Partito A", 2)]
        assert dedup_duplicate_regions(records) == records
