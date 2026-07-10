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
}
