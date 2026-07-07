<?php
declare(strict_types=1);

/**
 * Importa/aggiorna l'anagrafica partiti da un CSV normalizzato.
 *
 * Formato atteso (intestazione obbligatoria), separatore virgola, UTF-8:
 *   canonical_name,slug,first_year,last_year,is_active,notes
 *
 * Uso: php scripts/import_parties.php [percorso_csv]
 * Default: data/processed/parties.csv
 */

require_once __DIR__ . '/../app/config/database.php';
require_once __DIR__ . '/../app/includes/helpers.php';

$csvPath = $argv[1] ?? __DIR__ . '/../data/processed/parties.csv';

if (!is_file($csvPath)) {
    fwrite(STDERR, "File non trovato: $csvPath\n");
    exit(1);
}

$pdo = db();
$handle = fopen($csvPath, 'r');
$header = fgetcsv($handle);
if ($header === false) {
    fwrite(STDERR, "CSV vuoto o illeggibile.\n");
    exit(1);
}
$header = array_map('trim', $header);

$required = ['canonical_name', 'slug'];
foreach ($required as $col) {
    if (!in_array($col, $header, true)) {
        fwrite(STDERR, "Colonna obbligatoria mancante nel CSV: $col\n");
        exit(1);
    }
}

$upsert = $pdo->prepare(
    'INSERT INTO parties (canonical_name, slug, first_year, last_year, is_active, notes)
     VALUES (:canonical_name, :slug, :first_year, :last_year, :is_active, :notes)
     ON DUPLICATE KEY UPDATE
        canonical_name = VALUES(canonical_name),
        first_year = VALUES(first_year),
        last_year = VALUES(last_year),
        is_active = VALUES(is_active),
        notes = VALUES(notes)'
);

$count = 0;
while (($fields = fgetcsv($handle)) !== false) {
    $row = array_combine($header, $fields);
    $slug = clean_slug($row['slug'] ?? null) ?? slugify((string) ($row['canonical_name'] ?? ''));
    if ($slug === '' || trim((string) ($row['canonical_name'] ?? '')) === '') {
        fwrite(STDERR, "Riga ignorata (canonical_name o slug mancante): " . implode(',', $fields) . "\n");
        continue;
    }

    $upsert->execute([
        'canonical_name' => trim($row['canonical_name']),
        'slug' => $slug,
        'first_year' => clean_year($row['first_year'] ?? null),
        'last_year' => clean_year($row['last_year'] ?? null),
        'is_active' => isset($row['is_active']) && in_array(trim((string) $row['is_active']), ['0', 'false', 'no'], true) ? 0 : 1,
        'notes' => $row['notes'] ?? null,
    ]);
    $count++;
}

fclose($handle);
echo "Importati/aggiornati $count partiti da $csvPath\n";
