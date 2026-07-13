"""Test di parse_results_table (acquire_results.py): mappatura della tabella
MEF sullo schema normalizzato, estrazione del totale contribuenti e dei
totali di controllo della riga 'Totale'."""

from acquire_results import parse_results_table

HEADER = ["Denominazione", "Numero scelte", "Importo"]
ROWS = [
    ["Partito A", "1.000", "10.000,50"],
    ["Partito B", "500", "5.000,25"],
    ["Totale", "1.500", "15.000,75"],
    ["Per memoria: Totale contribuenti", "40.000.000", ""],
    ["Fonte: Dipartimento delle Finanze", "", ""],
]


def test_parties_extracted():
    records, _, _ = parse_results_table(HEADER, ROWS)
    assert [r["party_name"] for r in records] == ["Partito A", "Partito B"]
    assert records[0]["valid_choices"] == 1000
    assert records[0]["amount"] == 10000.50


def test_total_taxpayers_extracted():
    _, total_taxpayers, _ = parse_results_table(HEADER, ROWS)
    assert total_taxpayers == 40000000


def test_control_totals_extracted():
    _, _, control = parse_results_table(HEADER, ROWS)
    assert control == {
        "control_total_choices": 1500,
        "control_total_amount": 15000.75,
    }


def test_title_rows_before_header():
    # righe di titolo prima della vera intestazione (formato PDF/CSV MEF)
    header = ["ANALISI STATISTICHE - DUE PER MILLE"]
    rows = [["Anno d'imposta 2023"]] + [HEADER] + ROWS
    records, taxpayers, control = parse_results_table(header, rows)
    assert len(records) == 2
    assert taxpayers == 40000000
    assert control["control_total_choices"] == 1500


def test_no_party_column_returns_empty():
    records, taxpayers, control = parse_results_table(["x", "y"], [["1", "2"]])
    assert records == []
    assert taxpayers is None
    assert control == {}
