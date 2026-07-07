<?php
declare(strict_types=1);

final class Result
{
    private const METRIC_COLUMNS = [
        'choices' => 'valid_choices',
        'amount' => 'amount',
        'avg_amount' => 'avg_amount_per_choice',
    ];

    /** Ultimo anno di dichiarazione con risultati disponibili. */
    public static function latestYear(): ?int
    {
        $year = db()->query('SELECT MAX(declaration_year) FROM results')->fetchColumn();
        return $year !== null ? (int) $year : null;
    }

    /** Ultimo risultato disponibile per ciascun partito, con variazioni anno su anno. */
    public static function latestForAllParties(): array
    {
        $sql = 'SELECT v.*, (SELECT COUNT(*) FROM results r2 WHERE r2.party_id = v.party_id) AS years_present
                FROM v_results_full v
                JOIN (
                    SELECT party_id, MAX(declaration_year) AS max_year
                    FROM results GROUP BY party_id
                ) latest ON latest.party_id = v.party_id AND latest.max_year = v.declaration_year
                ORDER BY v.canonical_name ASC';
        return db()->query($sql)->fetchAll();
    }

    /** Tutti gli anni disponibili, ordine crescente. */
    public static function availableYears(): array
    {
        return array_map('intval', db()->query('SELECT DISTINCT declaration_year FROM results ORDER BY declaration_year ASC')->fetchAll(PDO::FETCH_COLUMN));
    }

    /** Serie storica completa per un partito, con variazioni anno su anno. */
    public static function forParty(int $partyId): array
    {
        $stmt = db()->prepare('SELECT * FROM v_results_full WHERE party_id = :id ORDER BY declaration_year ASC');
        $stmt->execute(['id' => $partyId]);
        return $stmt->fetchAll();
    }

    /** Risultati di tutti i partiti per un anno di dichiarazione. */
    public static function forYear(int $year): array
    {
        $stmt = db()->prepare('SELECT * FROM v_results_full WHERE declaration_year = :year ORDER BY rank_amount ASC');
        $stmt->execute(['year' => $year]);
        return $stmt->fetchAll();
    }

    /** Classifica top N per un anno e una metrica (choices|amount|avg_amount). */
    public static function top(int $year, string $metric, int $limit = 10): array
    {
        $rankCol = match ($metric) {
            'choices' => 'rank_choices',
            'amount' => 'rank_amount',
            'avg_amount' => 'rank_avg_amount',
            default => 'rank_amount',
        };
        $stmt = db()->prepare("SELECT * FROM v_results_full WHERE declaration_year = :year AND $rankCol IS NOT NULL ORDER BY $rankCol ASC LIMIT :limit");
        $stmt->bindValue('year', $year, PDO::PARAM_INT);
        $stmt->bindValue('limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    /** Dati per il confronto di più partiti (fino a 5), serie storica completa. */
    public static function compare(array $partyIds): array
    {
        if ($partyIds === []) {
            return [];
        }
        $placeholders = implode(',', array_fill(0, count($partyIds), '?'));
        $stmt = db()->prepare("SELECT * FROM v_results_full WHERE party_id IN ($placeholders) ORDER BY party_id ASC, declaration_year ASC");
        $stmt->execute(array_values($partyIds));
        $rows = $stmt->fetchAll();

        $grouped = [];
        foreach ($rows as $row) {
            $grouped[(int) $row['party_id']]['party'] = ['id' => $row['party_id'], 'canonical_name' => $row['canonical_name'], 'slug' => $row['slug']];
            $grouped[(int) $row['party_id']]['years'][] = $row;
        }
        return array_values($grouped);
    }

    /**
     * Classifica di crescita/calo percentuale su una metrica, con soglia minima
     * sul valore dell'anno precedente per evitare distorsioni su numeri piccoli.
     */
    public static function growthRanking(int $year, string $metric, string $direction = 'growth', int $minPrevious = 5000, int $limit = 10): array
    {
        $col = self::METRIC_COLUMNS[$metric] ?? 'valid_choices';
        $order = $direction === 'decline' ? 'ASC' : 'DESC';
        // valid_choices è BIGINT UNSIGNED: la sottrazione va forzata a SIGNED per non
        // andare in overflow quando il valore corrente è minore del precedente.
        [$currExpr, $prevExpr] = $col === 'valid_choices'
            ? ["CAST(curr.$col AS SIGNED)", "CAST(prev.$col AS SIGNED)"]
            : ["curr.$col", "prev.$col"];
        $sql = "SELECT curr.party_id, p.canonical_name, p.slug,
                       curr.$col AS current_value, prev.$col AS previous_value,
                       ROUND(($currExpr - $prevExpr) * 100.0 / prev.$col, 2) AS pct_change,
                       ($currExpr - $prevExpr) AS abs_change
                FROM results curr
                JOIN results prev ON prev.party_id = curr.party_id AND prev.declaration_year = curr.declaration_year - 1
                JOIN parties p ON p.id = curr.party_id
                WHERE curr.declaration_year = :year AND prev.valid_choices >= :min_previous AND prev.$col > 0
                ORDER BY pct_change $order
                LIMIT :limit";
        $stmt = db()->prepare($sql);
        $stmt->bindValue('year', $year, PDO::PARAM_INT);
        $stmt->bindValue('min_previous', $minPrevious, PDO::PARAM_INT);
        $stmt->bindValue('limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    /** Partiti con la maggiore differenza (positiva o negativa) tra quota importo e quota scelte. */
    public static function shareGapRanking(int $year, string $direction = 'positive', int $limit = 10): array
    {
        $order = $direction === 'negative' ? 'ASC' : 'DESC';
        $stmt = db()->prepare("SELECT * FROM v_results_full WHERE declaration_year = :year AND amount_vs_choices_share_gap IS NOT NULL ORDER BY amount_vs_choices_share_gap $order LIMIT :limit");
        $stmt->bindValue('year', $year, PDO::PARAM_INT);
        $stmt->bindValue('limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }

    /** Partiti con la presenza storica più lunga (numero di anni con dati). */
    public static function longestPresenceRanking(int $limit = 10): array
    {
        $sql = 'SELECT p.id AS party_id, p.canonical_name, p.slug, p.first_year, p.last_year,
                       COUNT(r.id) AS years_present
                FROM parties p
                JOIN results r ON r.party_id = p.id
                GROUP BY p.id, p.canonical_name, p.slug, p.first_year, p.last_year
                ORDER BY years_present DESC, p.first_year ASC
                LIMIT :limit';
        $stmt = db()->prepare($sql);
        $stmt->bindValue('limit', $limit, PDO::PARAM_INT);
        $stmt->execute();
        return $stmt->fetchAll();
    }
}
