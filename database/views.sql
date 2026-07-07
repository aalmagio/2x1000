-- Viste di comodo per interrogare i dati già arricchiti dagli indicatori.
-- Scritte con self-join (non window functions) per restare compatibili
-- anche con MySQL 5.7 su hosting Plesk più datati.

-- Risultati con nome/slug partito e variazioni anno su anno.
CREATE OR REPLACE VIEW v_results_full AS
SELECT
  r.id,
  r.party_id,
  p.canonical_name,
  p.slug,
  r.declaration_year,
  r.tax_year,
  r.valid_choices,
  r.pct_total_taxpayers,
  r.pct_valid_choices,
  r.amount,
  r.pct_amount,
  r.avg_amount_per_choice,
  r.rank_choices,
  r.rank_amount,
  r.rank_avg_amount,
  (CAST(r.valid_choices AS SIGNED) - CAST(prev.valid_choices AS SIGNED)) AS choices_delta_abs,
  CASE WHEN prev.valid_choices > 0
    THEN ROUND((CAST(r.valid_choices AS SIGNED) - CAST(prev.valid_choices AS SIGNED)) * 100.0 / prev.valid_choices, 2)
    ELSE NULL END AS choices_delta_pct,
  (r.amount - prev.amount) AS amount_delta_abs,
  CASE WHEN prev.amount > 0
    THEN ROUND((r.amount - prev.amount) * 100.0 / prev.amount, 2)
    ELSE NULL END AS amount_delta_pct,
  (r.pct_amount - r.pct_valid_choices) AS amount_vs_choices_share_gap,
  (CAST(r.rank_amount AS SIGNED) - CAST(r.rank_choices AS SIGNED)) AS amount_vs_choices_rank_gap,
  r.source_id
FROM results r
JOIN parties p ON p.id = r.party_id
LEFT JOIN results prev ON prev.party_id = r.party_id AND prev.declaration_year = r.declaration_year - 1;

-- Riepilogo per partito: ultimo anno disponibile e presenza storica.
CREATE OR REPLACE VIEW v_party_summary AS
SELECT
  p.id AS party_id,
  p.canonical_name,
  p.slug,
  p.first_year,
  p.last_year,
  p.is_active,
  (SELECT COUNT(*) FROM results r WHERE r.party_id = p.id) AS years_present,
  latest.declaration_year AS latest_declaration_year,
  latest.valid_choices AS latest_valid_choices,
  latest.amount AS latest_amount,
  latest.avg_amount_per_choice AS latest_avg_amount_per_choice,
  latest.rank_choices AS latest_rank_choices,
  latest.rank_amount AS latest_rank_amount
FROM parties p
LEFT JOIN results latest
  ON latest.party_id = p.id
 AND latest.declaration_year = (SELECT MAX(r2.declaration_year) FROM results r2 WHERE r2.party_id = p.id);
