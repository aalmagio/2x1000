-- ============================================================================
-- 2x1000 — Migrazioni per database già esistenti
-- ============================================================================
-- database/schema.sql usa CREATE TABLE IF NOT EXISTS: rieseguirlo su un
-- database già popolato è sicuro e crea automaticamente le tabelle nuove
-- (es. regional_results), ma NON modifica la struttura delle tabelle già
-- esistenti (es. aggiungere un valore a un ENUM). Per quello serve questo
-- file: contiene solo le ALTER TABLE necessarie, in ordine cronologico.
-- Ogni blocco è annotato con la data/motivo; eseguire solo i blocchi non
-- ancora applicati al proprio database.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 2026-07: aggiunta ripartizione regionale delle scelte (regional_results).
-- sources.source_type deve accettare anche questo tipo di fonte.
-- ----------------------------------------------------------------------------
ALTER TABLE sources
  MODIFY COLUMN source_type ENUM(
    'risultati_annuali', 'elenco_ammessi', 'codici_dichiarazione',
    'ripartizione_regionale', 'comunicato', 'altro'
  ) NOT NULL DEFAULT 'altro';
