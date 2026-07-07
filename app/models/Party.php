<?php
declare(strict_types=1);

final class Party
{
    /** Elenco completo partiti, opzionalmente filtrato sugli attivi. */
    public static function all(bool $onlyActive = false): array
    {
        $sql = 'SELECT id, canonical_name, slug, first_year, last_year, is_active, notes FROM parties';
        if ($onlyActive) {
            $sql .= ' WHERE is_active = 1';
        }
        $sql .= ' ORDER BY canonical_name ASC';
        return db()->query($sql)->fetchAll();
    }

    public static function findBySlug(string $slug): ?array
    {
        $stmt = db()->prepare('SELECT id, canonical_name, slug, first_year, last_year, is_active, notes FROM parties WHERE slug = :slug LIMIT 1');
        $stmt->execute(['slug' => $slug]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    public static function findById(int $id): ?array
    {
        $stmt = db()->prepare('SELECT id, canonical_name, slug, first_year, last_year, is_active, notes FROM parties WHERE id = :id LIMIT 1');
        $stmt->execute(['id' => $id]);
        $row = $stmt->fetch();
        return $row ?: null;
    }

    /** Elenco per la pagina "Partiti": ultimo anno disponibile, scelte/importo ultimo anno, anni di presenza. */
    public static function listWithLatest(): array
    {
        return db()->query('SELECT * FROM v_party_summary ORDER BY canonical_name ASC')->fetchAll();
    }

    /** Alias e codici annuali associati a un partito (per la scheda partito). */
    public static function aliases(int $partyId): array
    {
        $stmt = db()->prepare('SELECT alias_name, year_from, year_to, source, notes FROM party_aliases WHERE party_id = :id ORDER BY year_from ASC');
        $stmt->execute(['id' => $partyId]);
        return $stmt->fetchAll();
    }

    public static function codes(int $partyId): array
    {
        $stmt = db()->prepare('SELECT declaration_year, tax_year, code, official_name, source_id FROM party_codes WHERE party_id = :id ORDER BY declaration_year DESC');
        $stmt->execute(['id' => $partyId]);
        return $stmt->fetchAll();
    }
}
