"""Test delle funzioni euristiche di extract.py: sono i punti in cui un
cambiamento di formato delle fonti ufficiali (MEF/AdE) può produrre dati
sbagliati in silenzio, quindi ogni comportamento qui fissato è una regressione
osservata o un caso reale documentato nei commenti del modulo."""

import pytest

from extract import (
    _rejoin_split_header,
    clean_cell,
    find_col,
    is_direct_file_url,
    is_footer_row,
    locate_header,
    parse_amount,
    parse_int,
    sanitize_filename,
)


# ---------------------------------------------------------------------------
# parse_amount / parse_int — formati numerici italiani delle fonti pubbliche
# ---------------------------------------------------------------------------

class TestParseAmount:
    @pytest.mark.parametrize("raw, expected", [
        ("1.234,56", 1234.56),          # formato italiano completo
        ("1.234.567", 1234567.0),       # più punti = migliaia
        ("941.704", 941704.0),          # un punto + 3 cifre = migliaia (conteggi MEF)
        ("123.5", 123.5),               # un punto + non-3 cifre = decimale
        ("12,5", 12.5),                 # sola virgola = decimale
        ("€ 1.000", 1000.0),            # simbolo euro rimosso
        ("1234", 1234.0),
        ("0", 0.0),
        ("-12,3", -12.3),
    ])
    def test_string_formats(self, raw, expected):
        assert parse_amount(raw) == expected

    @pytest.mark.parametrize("raw", ["", "   ", None, "***", "n.d.", "abc"])
    def test_non_numeric_returns_none(self, raw):
        assert parse_amount(raw) is None

    def test_numbers_pass_through(self):
        assert parse_amount(42) == 42.0
        assert parse_amount(3.14) == 3.14


class TestParseInt:
    def test_thousands(self):
        assert parse_int("1.234") == 1234

    def test_rounds_decimals(self):
        assert parse_int("12,6") == 13

    def test_none(self):
        assert parse_int("***") is None


# ---------------------------------------------------------------------------
# is_footer_row — righe di totale/nota che non sono partiti
# ---------------------------------------------------------------------------

class TestIsFooterRow:
    @pytest.mark.parametrize("name", [
        "Totale", "TOTALE", "totali", "Per memoria: Totale contribuenti",
        "di cui: scelte espresse", "Nota: valori provvisori", "* dato stimato",
        "Fonte: Dipartimento delle Finanze", None, "",
    ])
    def test_footer_rows_detected(self, name):
        assert is_footer_row(name) is True

    @pytest.mark.parametrize("name", [
        "Partito Democratico",
        "Fratelli d'Italia",
        # il confronto è per prefisso, non substring: un nome che contiene
        # una parola chiave a metà frase non va scartato
        "Movimento per il Totale Rinnovamento",
    ])
    def test_party_names_kept(self, name):
        assert is_footer_row(name) is False


# ---------------------------------------------------------------------------
# find_col — individuazione colonne per alias
# ---------------------------------------------------------------------------

class TestFindCol:
    ALIASES = frozenset({"denominazione", "partito", "numero scelte"})

    def test_exact_match(self):
        assert find_col(["anno", "partito", "importo"], self.ALIASES) == 1

    def test_substring_match(self):
        # "denominazione partito" contiene l'alias "denominazione"
        assert find_col(["anno", "denominazione partito"], self.ALIASES) == 1

    def test_empty_cell_never_matches(self):
        # una cella vuota è "contenuta" in qualsiasi alias: senza il guard
        # dedicato, il match parziale scatterebbe sulla prima colonna vuota
        assert find_col(["", "importo"], frozenset({"denominazione"})) is None
        assert find_col(["", "", "partito"], self.ALIASES) == 2

    def test_no_match(self):
        assert find_col(["anno", "importo"], self.ALIASES) is None

    def test_short_aliases_require_exact(self):
        # gli alias <= 4 caratteri non fanno match parziale
        assert find_col(["codicione"], frozenset({"cod"})) is None

    def test_short_cells_never_partial_match(self):
        # una cella brevissima ("z") è contenuta per coincidenza in molti
        # alias ("denominazione" contiene una z): non deve fare match
        assert find_col(["z", "y"], frozenset({"denominazione"})) is None


# ---------------------------------------------------------------------------
# locate_header — righe di titolo prima della vera intestazione
# ---------------------------------------------------------------------------

class TestLocateHeader:
    ALIASES = frozenset({"denominazione", "partito"})

    def test_header_already_correct(self):
        header = ["Partito", "Scelte", "Importo"]
        rows = [["A", "1", "2"], ["B", "3", "4"]]
        got_header, got_rows = locate_header(header, rows, self.ALIASES)
        assert got_header == header
        assert got_rows == rows

    def test_title_rows_skipped(self):
        header = ["PARTITI POLITICI AMMESSI AL BENEFICIO"]
        rows = [
            ["Analisi statistiche - Due per mille"],
            ["Denominazione", "Numero scelte", "Importo"],
            ["Partito A", "10", "100"],
            ["Partito B", "20", "200"],
        ]
        got_header, got_rows = locate_header(header, rows, self.ALIASES)
        assert got_header == ["Denominazione", "Numero scelte", "Importo"]
        assert got_rows == [["Partito A", "10", "100"], ["Partito B", "20", "200"]]

    def test_no_match_returns_input(self):
        header = ["x"]
        rows = [["y"], ["z"]]
        assert locate_header(header, rows, self.ALIASES) == (header, rows)


# ---------------------------------------------------------------------------
# _rejoin_split_header — intestazione spezzata da un a-capo non quotato
# (regressione osservata sulla ripartizione regionale MEF: "Lega Nord per
# l'Indipendenza\n della Padania" troncava tutte le colonne successive)
# ---------------------------------------------------------------------------

class TestRejoinSplitHeader:
    def test_split_header_rejoined(self):
        header = ["Regione", "Partito A", "Lega Nord per l'Indipendenza"]
        rows = [
            ["della Padania", "Partito B", "Partito C"],   # continuazione
            ["Lombardia", "1", "2", "3", "4"],
            ["Lazio", "5", "6", "7", "8"],
        ]
        got_header, got_rows = _rejoin_split_header(header, rows)
        assert got_header == [
            "Regione", "Partito A",
            "Lega Nord per l'Indipendenza della Padania",
            "Partito B", "Partito C",
        ]
        assert got_rows == rows[1:]

    def test_normal_header_untouched(self):
        header = ["Regione", "A", "B"]
        rows = [["Lombardia", "1", "2"], ["Lazio", "3", "4"]]
        assert _rejoin_split_header(header, rows) == (header, rows)

    def test_length_mismatch_not_merged(self):
        # la riga dopo l'header non ricompone la lunghezza attesa: non toccare
        header = ["Regione", "A"]
        rows = [["x", "y", "z"], ["Lombardia", "1", "2", "3", "4"], ["Lazio", "5", "6", "7", "8"]]
        assert _rejoin_split_header(header, rows) == (header, rows)

    def test_empty_rows(self):
        assert _rejoin_split_header(["A"], []) == (["A"], [])


# ---------------------------------------------------------------------------
# clean_cell / sanitize_filename / is_direct_file_url
# ---------------------------------------------------------------------------

class TestCleanCell:
    def test_strips_and_collapses(self):
        assert clean_cell("  Partito\n\nDemocratico  ") == "Partito Democratico"

    def test_strips_wrapping_quotes(self):
        assert clean_cell('"Partito A"') == "Partito A"

    def test_none_is_empty(self):
        assert clean_cell(None) == ""


class TestUrlHelpers:
    def test_ade_extension_mid_path(self):
        # link Liferay dell'AdE: nome file a metà path, hash come ultimo segmento
        url = ("https://www.agenziaentrate.gov.it/portale/documents/20143/8673492/"
               "PF1_Tabella+partiti+politici+2025.pdf/07dd2e41-6897-bee5?t=174247")
        assert is_direct_file_url(url) == "pdf"
        name = sanitize_filename(url, 1, "pdf")
        assert name.endswith(".pdf")
        assert "Tabella" in name

    def test_html_page_is_not_direct(self):
        assert is_direct_file_url("https://example.org/pagina/dati-2024") is None

    def test_fallback_name(self):
        assert sanitize_filename("https://example.org/" + "x" * 300, 3, "csv") == "file_03.csv"
