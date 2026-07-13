-- 2x1000 Open Data — Partiti politici
-- Schema MySQL / MariaDB
-- Compatibile con MySQL 5.7+/8.x e MariaDB 10.3+

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
-- sources: fonti ufficiali (MEF, Agenzia delle Entrate, comunicati...)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sources (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  institution VARCHAR(255) NOT NULL COMMENT 'es. Ministero Economia e Finanze, Agenzia delle Entrate',
  title VARCHAR(500) NOT NULL,
  url VARCHAR(1000) NULL,
  source_type ENUM('risultati_annuali', 'elenco_ammessi', 'codici_dichiarazione', 'ripartizione_regionale', 'comunicato', 'altro') NOT NULL DEFAULT 'altro',
  publication_date DATE NULL,
  download_date DATE NULL,
  checksum VARCHAR(128) NULL COMMENT 'es. sha256 del file scaricato',
  notes TEXT NULL,
  PRIMARY KEY (id),
  KEY idx_sources_type (source_type),
  KEY idx_sources_institution (institution)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- parties: anagrafica normalizzata dei partiti
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS parties (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  canonical_name VARCHAR(255) NOT NULL,
  slug VARCHAR(150) NOT NULL,
  first_year SMALLINT UNSIGNED NULL COMMENT 'primo anno dichiarazione con dati disponibili',
  last_year SMALLINT UNSIGNED NULL COMMENT 'ultimo anno dichiarazione con dati disponibili',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  notes TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_parties_slug (slug),
  KEY idx_parties_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- party_aliases: denominazioni alternative, cambi nome, sigle
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS party_aliases (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  party_id INT UNSIGNED NOT NULL,
  alias_name VARCHAR(255) NOT NULL,
  year_from SMALLINT UNSIGNED NULL,
  year_to SMALLINT UNSIGNED NULL,
  source VARCHAR(500) NULL,
  notes TEXT NULL,
  PRIMARY KEY (id),
  KEY idx_aliases_party (party_id),
  CONSTRAINT fk_aliases_party FOREIGN KEY (party_id) REFERENCES parties (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- party_codes: codici annuali da indicare in dichiarazione (Agenzia Entrate)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS party_codes (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  party_id INT UNSIGNED NOT NULL,
  declaration_year SMALLINT UNSIGNED NOT NULL COMMENT 'anno in cui si presenta la dichiarazione',
  tax_year SMALLINT UNSIGNED NOT NULL COMMENT 'anno d''imposta di riferimento',
  code VARCHAR(20) NOT NULL COMMENT 'codice da indicare nel modello dichiarativo',
  official_name VARCHAR(255) NOT NULL COMMENT 'denominazione ufficiale riportata dall''Agenzia delle Entrate',
  source_id INT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_codes_party_year (party_id, declaration_year),
  KEY idx_codes_code (code),
  KEY idx_codes_declaration_year (declaration_year),
  KEY idx_codes_tax_year (tax_year),
  KEY idx_codes_source (source_id),
  CONSTRAINT fk_codes_party FOREIGN KEY (party_id) REFERENCES parties (id) ON DELETE CASCADE,
  CONSTRAINT fk_codes_source FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- results: risultati annuali per partito
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS results (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  party_id INT UNSIGNED NOT NULL,
  declaration_year SMALLINT UNSIGNED NOT NULL,
  tax_year SMALLINT UNSIGNED NOT NULL,
  valid_choices BIGINT UNSIGNED NOT NULL DEFAULT 0 COMMENT 'numero di scelte valide',
  pct_total_taxpayers DECIMAL(8,5) NULL COMMENT 'scelte valide / totale contribuenti (%)',
  pct_valid_choices DECIMAL(8,5) NULL COMMENT 'quota sul totale delle scelte valide (%)',
  amount DECIMAL(16,2) NOT NULL DEFAULT 0 COMMENT 'importo assegnato in euro',
  pct_amount DECIMAL(8,5) NULL COMMENT 'quota sull''importo totale (%)',
  avg_amount_per_choice DECIMAL(10,2) NULL COMMENT 'importo medio per scelta (indicatore aggregato, non reddito medio)',
  rank_choices SMALLINT UNSIGNED NULL,
  rank_amount SMALLINT UNSIGNED NULL,
  rank_avg_amount SMALLINT UNSIGNED NULL,
  source_id INT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_results_party_year (party_id, declaration_year),
  KEY idx_results_party (party_id),
  KEY idx_results_declaration_year (declaration_year),
  KEY idx_results_tax_year (tax_year),
  KEY idx_results_source (source_id),
  CONSTRAINT fk_results_party FOREIGN KEY (party_id) REFERENCES parties (id) ON DELETE CASCADE,
  CONSTRAINT fk_results_source FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- annual_totals: totali annuali di sistema
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS annual_totals (
  declaration_year SMALLINT UNSIGNED NOT NULL,
  tax_year SMALLINT UNSIGNED NOT NULL,
  total_taxpayers BIGINT UNSIGNED NULL,
  total_valid_choices BIGINT UNSIGNED NOT NULL DEFAULT 0,
  total_amount DECIMAL(18,2) NOT NULL DEFAULT 0,
  valid_choice_rate DECIMAL(8,5) NULL COMMENT 'scelte valide / totale contribuenti (%)',
  avg_amount_per_choice DECIMAL(10,2) NULL,
  number_of_parties_with_choices SMALLINT UNSIGNED NULL,
  number_of_parties_admitted SMALLINT UNSIGNED NULL,
  top_3_amount_share DECIMAL(8,5) NULL COMMENT 'quota importo dei primi 3 partiti (%)',
  top_5_amount_share DECIMAL(8,5) NULL,
  top_10_amount_share DECIMAL(8,5) NULL,
  source_id INT UNSIGNED NULL,
  PRIMARY KEY (declaration_year),
  KEY idx_totals_tax_year (tax_year),
  KEY idx_totals_source (source_id),
  CONSTRAINT fk_totals_source FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- regions: anagrafica normalizzata delle regioni (codici ISTAT).
-- `regional_results.region` resta il testo libero come da fonte (provenienza);
-- questa tabella dà a ogni etichetta un'identità stabile e il codice ISTAT,
-- prerequisito per mappa coropletica e incroci con altri open data regionali.
-- map_code è il codice della regione su cui la mappa aggrega il dato: le due
-- Province Autonome di Trento e Bolzano (pubblicate separatamente dal MEF)
-- confluiscono entrambe sul Trentino-Alto Adige ('04'); NULL = non
-- rappresentabile sulla mappa (es. "Non residenti").
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regions (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  canonical_name VARCHAR(80) NOT NULL,
  slug VARCHAR(80) NOT NULL,
  istat_code CHAR(2) NULL COMMENT 'codice ISTAT della regione (NULL per righe speciali: PA, non residenti)',
  map_code CHAR(2) NULL COMMENT 'codice regione su cui la mappa aggrega il dato (PA Trento/Bolzano -> 04)',
  PRIMARY KEY (id),
  UNIQUE KEY uniq_regions_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dati di riferimento (INSERT IGNORE: rieseguibile senza effetti collaterali).
INSERT IGNORE INTO regions (canonical_name, slug, istat_code, map_code) VALUES
  ('Piemonte', 'piemonte', '01', '01'),
  ('Valle d''Aosta', 'valle-d-aosta', '02', '02'),
  ('Lombardia', 'lombardia', '03', '03'),
  ('Trentino-Alto Adige', 'trentino-alto-adige', '04', '04'),
  ('Trentino-Alto Adige (PA Trento)', 'trentino-alto-adige-pa-trento', NULL, '04'),
  ('Trentino-Alto Adige (PA Bolzano)', 'trentino-alto-adige-pa-bolzano', NULL, '04'),
  ('Veneto', 'veneto', '05', '05'),
  ('Friuli-Venezia Giulia', 'friuli-venezia-giulia', '06', '06'),
  ('Liguria', 'liguria', '07', '07'),
  ('Emilia-Romagna', 'emilia-romagna', '08', '08'),
  ('Toscana', 'toscana', '09', '09'),
  ('Umbria', 'umbria', '10', '10'),
  ('Marche', 'marche', '11', '11'),
  ('Lazio', 'lazio', '12', '12'),
  ('Abruzzo', 'abruzzo', '13', '13'),
  ('Molise', 'molise', '14', '14'),
  ('Campania', 'campania', '15', '15'),
  ('Puglia', 'puglia', '16', '16'),
  ('Basilicata', 'basilicata', '17', '17'),
  ('Calabria', 'calabria', '18', '18'),
  ('Sicilia', 'sicilia', '19', '19'),
  ('Sardegna', 'sardegna', '20', '20'),
  ('Non residenti', 'non-residenti', NULL, NULL);

-- ---------------------------------------------------------------------------
-- regional_results: ripartizione regionale delle scelte per partito e anno
-- (fonte: Dipartimento delle Finanze, tabella a sviluppo orizzontale
-- regione x partito). is_suppressed distingue "0 scelte reali" da "dato
-- oscurato dalla fonte per soglia di tutela della riservatezza" (riportato
-- come "***" nel file originale quando il numero è troppo basso): in quel
-- caso valid_choices resta NULL e is_suppressed = 1, per non confonderlo
-- con uno zero vero.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS regional_results (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  party_id INT UNSIGNED NOT NULL,
  declaration_year SMALLINT UNSIGNED NOT NULL,
  tax_year SMALLINT UNSIGNED NOT NULL,
  region VARCHAR(60) NOT NULL COMMENT 'nome regione come da fonte, es. "Trentino Alto Adige (PA Trento)", "Non residenti"',
  region_id INT UNSIGNED NULL COMMENT 'FK verso regions: risolto da db_updater.py, NULL se etichetta non riconosciuta',
  valid_choices BIGINT UNSIGNED NULL COMMENT 'NULL se oscurato per riservatezza (vedi is_suppressed)',
  is_suppressed TINYINT(1) NOT NULL DEFAULT 0,
  source_id INT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_regional_party_year_region (party_id, declaration_year, region),
  KEY idx_regional_declaration_year (declaration_year),
  KEY idx_regional_region (region),
  KEY idx_regional_region_id (region_id),
  KEY idx_regional_source (source_id),
  CONSTRAINT fk_regional_party FOREIGN KEY (party_id) REFERENCES parties (id) ON DELETE CASCADE,
  CONSTRAINT fk_regional_region FOREIGN KEY (region_id) REFERENCES regions (id) ON DELETE SET NULL,
  CONSTRAINT fk_regional_source FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
