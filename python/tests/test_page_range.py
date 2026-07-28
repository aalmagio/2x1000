"""Test di parse_page_range (extract.py) e della configurazione {url, pages}
di acquire_party_codes.py — il meccanismo che permette di estrarre la tabella
partiti da un intervallo di pagine di un documento lungo (es. le istruzioni
del modello 730/2020, dove la tabella non è pubblicata come file a sé)."""

import pytest

import acquire_party_codes
from extract import parse_page_range


class TestParsePageRange:
    def test_single_page(self):
        assert parse_page_range("203") == {203}

    def test_range(self):
        assert parse_page_range("203-206") == {203, 204, 205, 206}

    def test_mixed(self):
        assert parse_page_range("12,14-16") == {12, 14, 15, 16}

    def test_none_and_empty_mean_all_pages(self):
        assert parse_page_range(None) is None
        assert parse_page_range("") is None
        assert parse_page_range("   ") is None

    @pytest.mark.parametrize("bad", ["abc", "0", "10-5", "-3", ","])
    def test_invalid_specs_raise(self, bad):
        with pytest.raises(ValueError):
            parse_page_range(bad)


class TestCodesConfig:
    def setup_method(self):
        acquire_party_codes.YEAR_URLS.clear()
        acquire_party_codes.YEAR_PAGES.clear()

    def test_plain_url_entry(self):
        acquire_party_codes._apply_config({"url_anni_codici": {2024: "https://example.org/tab.pdf"}})
        assert acquire_party_codes.YEAR_URLS[2024] == "https://example.org/tab.pdf"
        assert 2024 not in acquire_party_codes.YEAR_PAGES

    def test_dict_entry_with_pages(self):
        acquire_party_codes._apply_config({"url_anni_codici": {
            2020: {"url": "https://example.org/istruzioni_730.pdf", "pages": "203-206"},
        }})
        assert acquire_party_codes.YEAR_URLS[2020] == "https://example.org/istruzioni_730.pdf"
        assert acquire_party_codes.YEAR_PAGES[2020] == "203-206"

    def test_mixed_entries(self):
        acquire_party_codes._apply_config({"url_anni_codici": {
            2021: "https://example.org/tab2021.pdf",
            2020: {"url": "https://example.org/istr.pdf", "pages": "203"},
        }})
        assert set(acquire_party_codes.YEAR_URLS) == {2020, 2021}
        assert acquire_party_codes.YEAR_PAGES == {2020: "203"}
