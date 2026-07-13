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


def test_2015_format_amount_from_teorico_column():
    # Formato MEF 2015/2016: niente colonna "Importo" ma "2‰ teorico" +
    # "Totale 2‰ erogato nel 2015" + "Somme erogate nel 2016 (art. 11 D.L.
    # 149/2013)". L'importo spettante fu erogato in due tranche: la colonna
    # equivalente all'"Importo" degli anni successivi è "2‰ teorico".
    # Regressione: senza l'alias, questi anni finivano in DB con amount = 0.
    header = [
        "Partiti politici", "Scelte valide", "% scelte sul numero contribuenti",
        "% sul totale scelte", "2‰ teorico", "Totale 2‰ erogato nel 2015",
        "Somme erogate nel 2016 in base all'art. 11 D.L. 28 dicembre 2013 n. 149",
    ]
    rows = [
        ["Centro Democratico", "19.958", "0,05%", "1,80%", "177.420", "137.873", "39.546"],
        ["Die Freiheitlichen", "2.949", "0,01%", "0,27%", "28.108", "21.843", "6.265"],
        ["Totale", "22.907", "", "", "205.528", "159.716", "45.811"],
    ]
    records, _, control = parse_results_table(header, rows)
    assert [r["party_name"] for r in records] == ["Centro Democratico", "Die Freiheitlichen"]
    assert records[0]["valid_choices"] == 19958
    assert records[0]["amount"] == 177420.0  # dal "2‰ teorico", non dall'erogato parziale
    assert control == {"control_total_choices": 22907, "control_total_amount": 205528.0}
