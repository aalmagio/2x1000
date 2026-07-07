-- ============================================================================
-- DATI DEMO / SAMPLE — NON SONO DATI UFFICIALI
-- Questo seed serve solo per avere una piattaforma funzionante in sviluppo.
-- Tutti i nomi dei partiti, gli importi e le scelte sono INVENTATI.
-- Prima della messa in produzione, sostituire con l'import dei dati ufficiali
-- (vedi scripts/import_parties.php e scripts/import_results.php) e RIMUOVERE
-- questo seed.
-- ============================================================================

SET NAMES utf8mb4;

-- ---------------------------------------------------------------------------
-- Fonte demo
-- ---------------------------------------------------------------------------
INSERT INTO sources (id, institution, title, url, source_type, publication_date, download_date, checksum, notes)
VALUES (
  1,
  'DATI DEMO',
  'Dataset dimostrativo generato per lo sviluppo — NON rappresenta dati ufficiali reali',
  NULL,
  'altro',
  NULL,
  NULL,
  NULL,
  'SAMPLE DATA: numeri inventati a scopo di test. Sostituire con le fonti ufficiali MEF/Agenzia delle Entrate prima della produzione.'
);

-- ---------------------------------------------------------------------------
-- Partiti demo (nomi generici, non corrispondono a soggetti reali)
-- ---------------------------------------------------------------------------
INSERT INTO parties (id, canonical_name, slug, first_year, last_year, is_active, notes) VALUES
(1, 'Partito Demo A', 'partito-demo-a', 2020, 2024, 1, 'DATO DEMO/SAMPLE — non un partito realmente esistente'),
(2, 'Partito Demo B', 'partito-demo-b', 2020, 2024, 1, 'DATO DEMO/SAMPLE — non un partito realmente esistente'),
(3, 'Partito Demo C', 'partito-demo-c', 2020, 2024, 1, 'DATO DEMO/SAMPLE — non un partito realmente esistente'),
(4, 'Partito Demo D', 'partito-demo-d', 2020, 2024, 1, 'DATO DEMO/SAMPLE — non un partito realmente esistente'),
(5, 'Partito Demo E', 'partito-demo-e', 2020, 2024, 1, 'DATO DEMO/SAMPLE — non un partito realmente esistente'),
(6, 'Partito Demo F', 'partito-demo-f', 2020, 2024, 1, 'DATO DEMO/SAMPLE — non un partito realmente esistente'),
(7, 'Partito Demo G', 'partito-demo-g', 2020, 2024, 1, 'DATO DEMO/SAMPLE — non un partito realmente esistente'),
(8, 'Partito Demo H', 'partito-demo-h', 2020, 2024, 1, 'DATO DEMO/SAMPLE — non un partito realmente esistente');

-- ---------------------------------------------------------------------------
-- Alias demo (un solo esempio di cambio denominazione)
-- ---------------------------------------------------------------------------
INSERT INTO party_aliases (party_id, alias_name, year_from, year_to, source, notes) VALUES
(1, 'Partito Demo A (ex sigla)', 2020, 2021, 'DEMO', 'DATO DEMO/SAMPLE');

-- ---------------------------------------------------------------------------
-- Codici annuali demo da indicare in dichiarazione
-- ---------------------------------------------------------------------------
INSERT INTO party_codes (party_id, declaration_year, tax_year, code, official_name, source_id) VALUES
(1, 2024, 2023, 'D01', 'PARTITO DEMO A', 1),
(2, 2024, 2023, 'D02', 'PARTITO DEMO B', 1),
(3, 2024, 2023, 'D03', 'PARTITO DEMO C', 1),
(4, 2024, 2023, 'D04', 'PARTITO DEMO D', 1),
(5, 2024, 2023, 'D05', 'PARTITO DEMO E', 1),
(6, 2024, 2023, 'D06', 'PARTITO DEMO F', 1),
(7, 2024, 2023, 'D07', 'PARTITO DEMO G', 1),
(8, 2024, 2023, 'D08', 'PARTITO DEMO H', 1);

-- ---------------------------------------------------------------------------
-- Risultati annuali demo (valid_choices, amount).
-- Gli indicatori derivati (quote, ranking, medie, variazioni) vengono
-- calcolati da scripts/calculate_indicators.php, non inseriti a mano.
-- ---------------------------------------------------------------------------
INSERT INTO results (party_id, declaration_year, tax_year, valid_choices, amount, source_id) VALUES
(1, 2020, 2019, 821063, 14031966.67, 1),
(1, 2021, 2020, 783505, 13852368.40, 1),
(1, 2022, 2021, 845282, 16077263.64, 1),
(1, 2023, 2022, 947466, 16372212.48, 1),
(1, 2024, 2023, 941704, 16112555.44, 1),
(2, 2020, 2019, 572809, 9285233.89, 1),
(2, 2021, 2020, 508175, 7836058.50, 1),
(2, 2022, 2021, 536362, 8753427.84, 1),
(2, 2023, 2022, 503922, 8279438.46, 1),
(2, 2024, 2023, 553581, 8259428.52, 1),
(3, 2020, 2019, 460979, 9989414.93, 1),
(3, 2021, 2020, 448010, 8888518.40, 1),
(3, 2022, 2021, 510035, 10430215.75, 1),
(3, 2023, 2022, 461602, 9065863.28, 1),
(3, 2024, 2023, 511835, 10927677.25, 1),
(4, 2020, 2019, 329377, 5052643.18, 1),
(4, 2021, 2020, 337539, 5373620.88, 1),
(4, 2022, 2021, 331532, 4946457.44, 1),
(4, 2023, 2022, 365991, 5519144.28, 1),
(4, 2024, 2023, 407223, 6100200.54, 1),
(5, 2020, 2019, 224749, 4063461.92, 1),
(5, 2021, 2020, 211608, 3986694.72, 1),
(5, 2022, 2021, 190773, 3561731.91, 1),
(5, 2023, 2022, 173082, 3255672.42, 1),
(5, 2024, 2023, 182019, 3472922.52, 1),
(6, 2020, 2019, 146992, 1724216.16, 1),
(6, 2021, 2020, 139948, 1841715.68, 1),
(6, 2022, 2021, 147640, 1846976.40, 1),
(6, 2023, 2022, 136745, 1743498.75, 1),
(6, 2024, 2023, 126368, 1523998.08, 1),
(7, 2020, 2019, 108981, 2563233.12, 1),
(7, 2021, 2020, 112291, 2659050.88, 1),
(7, 2022, 2021, 124370, 2987367.40, 1),
(7, 2023, 2022, 117137, 2492675.36, 1),
(7, 2024, 2023, 113057, 2504212.55, 1),
(8, 2020, 2019, 48722, 829735.66, 1),
(8, 2021, 2020, 54403, 839438.29, 1),
(8, 2022, 2021, 57502, 898756.26, 1),
(8, 2023, 2022, 64800, 1023840.00, 1),
(8, 2024, 2023, 61658, 940901.08, 1);

-- ---------------------------------------------------------------------------
-- Totali annuali demo: total_taxpayers e number_of_parties_admitted sono
-- input esterni (non derivabili dai risultati); il resto viene calcolato/
-- aggiornato da scripts/calculate_indicators.php.
-- ---------------------------------------------------------------------------
INSERT INTO annual_totals (declaration_year, tax_year, total_taxpayers, number_of_parties_admitted, source_id) VALUES
(2020, 2019, 40100000, 14, 1),
(2021, 2020, 40300000, 13, 1),
(2022, 2021, 40500000, 13, 1),
(2023, 2022, 40800000, 12, 1),
(2024, 2023, 41000000, 12, 1);
