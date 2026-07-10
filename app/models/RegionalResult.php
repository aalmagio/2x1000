<?php
declare(strict_types=1);

final class RegionalResult
{
    /** Ripartizione regionale completa (tutti gli anni) per un partito. */
    public static function forParty(int $partyId): array
    {
        $stmt = db()->prepare(
            'SELECT declaration_year, tax_year, region, valid_choices, is_suppressed
             FROM regional_results
             WHERE party_id = :id
             ORDER BY declaration_year DESC, region ASC'
        );
        $stmt->execute(['id' => $partyId]);
        $rows = $stmt->fetchAll();
        foreach ($rows as &$row) {
            $row['is_suppressed'] = (bool) $row['is_suppressed'];
        }
        return $rows;
    }

    /** Anni di dichiarazione con ripartizione regionale disponibile. */
    public static function availableYears(): array
    {
        return array_map('intval', db()->query('SELECT DISTINCT declaration_year FROM regional_results ORDER BY declaration_year ASC')->fetchAll(PDO::FETCH_COLUMN));
    }

    /** Elenco delle regioni presenti in anagrafica (per filtri/select). */
    public static function availableRegions(): array
    {
        return db()->query('SELECT DISTINCT region FROM regional_results ORDER BY region ASC')->fetchAll(PDO::FETCH_COLUMN);
    }

    /** Totale scelte (non oscurate) per regione, per un anno. */
    public static function totalsByYear(int $year): array
    {
        $stmt = db()->prepare(
            'SELECT region,
                    SUM(CASE WHEN is_suppressed = 0 THEN valid_choices ELSE 0 END) AS total_choices,
                    SUM(CASE WHEN is_suppressed = 1 THEN 1 ELSE 0 END) AS suppressed_count
             FROM regional_results
             WHERE declaration_year = :year
             GROUP BY region
             ORDER BY total_choices DESC'
        );
        $stmt->execute(['year' => $year]);
        return $stmt->fetchAll();
    }

    /**
     * Partito con più scelte in ciascuna regione, per un anno (indicizzato per
     * nome regione). Niente funzioni finestra per restare compatibile con
     * MySQL 5.7 (vedi Requisiti nel README): in caso di pareggio esatto tra
     * due partiti nella stessa regione, tiene il primo trovato.
     */
    public static function topPartyByRegion(int $year): array
    {
        $stmt = db()->prepare(
            'SELECT rr.region, rr.valid_choices, p.canonical_name, p.slug
             FROM regional_results rr
             JOIN parties p ON p.id = rr.party_id
             WHERE rr.declaration_year = :year AND rr.is_suppressed = 0
               AND rr.valid_choices = (
                   SELECT MAX(rr2.valid_choices) FROM regional_results rr2
                   WHERE rr2.region = rr.region AND rr2.declaration_year = rr.declaration_year AND rr2.is_suppressed = 0
               )
             ORDER BY rr.region ASC'
        );
        $stmt->execute(['year' => $year]);
        $byRegion = [];
        foreach ($stmt->fetchAll() as $row) {
            $byRegion[$row['region']] ??= $row;
        }
        return $byRegion;
    }

    /** Classifica dei partiti per scelte valide in una regione, per un anno. */
    public static function rankingForRegion(int $year, string $region, int $limit = 50): array
    {
        $stmt = db()->prepare(
            'SELECT rr.valid_choices, p.canonical_name, p.slug
             FROM regional_results rr
             JOIN parties p ON p.id = rr.party_id
             WHERE rr.declaration_year = :year AND rr.region = :region AND rr.is_suppressed = 0
             ORDER BY rr.valid_choices DESC
             LIMIT :limit'
        );
        $stmt->bindValue('year', $year, PDO::PARAM_INT);
        $stmt->bindValue('region', $region, PDO::PARAM_STR);
        $stmt->bindValue('limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    /** Partiti con dato oscurato in una regione/anno (elencati senza valore, per trasparenza). */
    public static function suppressedPartiesForRegion(int $year, string $region): array
    {
        $stmt = db()->prepare(
            'SELECT p.canonical_name, p.slug
             FROM regional_results rr
             JOIN parties p ON p.id = rr.party_id
             WHERE rr.declaration_year = :year AND rr.region = :region AND rr.is_suppressed = 1
             ORDER BY p.canonical_name ASC'
        );
        $stmt->execute(['year' => $year, 'region' => $region]);
        return $stmt->fetchAll();
    }
}
