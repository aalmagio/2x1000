<?php
declare(strict_types=1);

final class AnnualTotal
{
    public static function all(): array
    {
        return db()->query('SELECT * FROM annual_totals ORDER BY declaration_year ASC')->fetchAll();
    }

    public static function forYear(int $year): ?array
    {
        $stmt = db()->prepare('SELECT * FROM annual_totals WHERE declaration_year = :year LIMIT 1');
        $stmt->execute(['year' => $year]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    public static function latestYear(): ?int
    {
        $year = db()->query('SELECT MAX(declaration_year) FROM annual_totals')->fetchColumn();
        return $year !== null ? (int) $year : null;
    }
}
