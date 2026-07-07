<?php
declare(strict_types=1);

final class Source
{
    public static function all(): array
    {
        return db()->query('SELECT * FROM sources ORDER BY publication_date DESC, id DESC')->fetchAll();
    }

    public static function findById(int $id): ?array
    {
        $stmt = db()->prepare('SELECT * FROM sources WHERE id = :id LIMIT 1');
        $stmt->execute(['id' => $id]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    /** Fonti distinte associate ai risultati di un partito. */
    public static function forParty(int $partyId): array
    {
        $sql = 'SELECT DISTINCT s.* FROM sources s
                JOIN results r ON r.source_id = s.id
                WHERE r.party_id = :id
                ORDER BY s.publication_date DESC';
        $stmt = db()->prepare($sql);
        $stmt->execute(['id' => $partyId]);
        return $stmt->fetchAll();
    }
}
