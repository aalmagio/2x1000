"""Test della logica di riconciliazione di validate_data.py (funzioni pure,
nessun database richiesto)."""

from validate_data import (
    FAIL,
    INFO,
    WARN,
    check_control_totals,
    check_regional_row,
    check_yoy_change,
)


def levels(findings):
    return [f["level"] for f in findings]


class TestControlTotals:
    META_OK = {"control_total_choices": 1000, "control_total_amount": 5000.0}

    def test_matching_totals_pass(self):
        got = check_control_totals(2024, self.META_OK, 1000, 5000.0)
        assert levels(got) == [INFO]

    def test_choices_mismatch_fails(self):
        got = check_control_totals(2024, self.META_OK, 999, 5000.0)
        assert FAIL in levels(got)
        assert "scelte" in got[0]["message"].lower()

    def test_amount_mismatch_fails(self):
        got = check_control_totals(2024, self.META_OK, 1000, 5010.0)
        assert FAIL in levels(got)

    def test_amount_within_tolerance_passes(self):
        # la fonte può arrotondare al centesimo diversamente dalla somma
        got = check_control_totals(2024, self.META_OK, 1000, 5000.40)
        assert levels(got) == [INFO]

    def test_missing_control_totals_is_info(self):
        got = check_control_totals(2024, {}, 1000, 5000.0)
        assert levels(got) == [INFO]
        assert "meta.json" in got[0]["message"]


class TestRegionalRow:
    def test_exact_match_no_suppression_passes(self):
        assert check_regional_row(2024, "Partito A", 100, 100, 0, 2.0) == []

    def test_regional_above_national_fails(self):
        got = check_regional_row(2024, "Partito A", 100, 120, 0, 2.0)
        assert levels(got) == [FAIL]
        assert "SUPERIORE" in got[0]["message"]

    def test_mismatch_without_suppression_fails(self):
        got = check_regional_row(2024, "Partito A", 100, 90, 0, 2.0)
        assert levels(got) == [FAIL]

    def test_small_gap_with_suppression_passes(self):
        # 1% di scarto con valori oscurati: entro soglia
        assert check_regional_row(2024, "Partito A", 1000, 990, 3, 2.0) == []

    def test_large_gap_with_suppression_warns(self):
        got = check_regional_row(2024, "Partito A", 1000, 900, 3, 2.0)
        assert levels(got) == [WARN]

    def test_none_regional_sum_treated_as_zero(self):
        # tutte le regioni oscurate: somma NULL dal DB
        got = check_regional_row(2024, "Partito A", 50, None, 21, 2.0)
        assert levels(got) == [WARN]


class TestYoyChange:
    def test_small_change_passes(self):
        assert check_yoy_change(2024, 2023, "Scelte", 110, 100, 50.0) == []

    def test_large_increase_warns(self):
        got = check_yoy_change(2024, 2023, "Scelte", 200, 100, 50.0)
        assert levels(got) == [WARN]
        assert "+100.0%" in got[0]["message"]

    def test_large_decrease_warns(self):
        got = check_yoy_change(2024, 2023, "Scelte", 40, 100, 50.0)
        assert levels(got) == [WARN]

    def test_zero_previous_skipped(self):
        assert check_yoy_change(2024, 2023, "Scelte", 100, 0, 50.0) == []
