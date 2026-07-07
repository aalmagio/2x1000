<?php
declare(strict_types=1);

/**
 * Importa i risultati annuali per partito da un CSV normalizzato.
 * Non calcola quote/ranking: eseguire dopo scripts/calculate_indicators.php.
 *
 * Formato atteso (intestazione obbligatoria), separatore virgola, UTF-8:
 *   party_slug,declaration_year,tax_year,valid_choices,amount,source_id
 *
 * Il partito deve già esistere (eseguire prima scripts/import_parties.php).
 * source_id è opzionale e deve riferirsi a una riga già presente in `sources`.
 *
 * Uso: php scripts/import_results.php [percorso_csv]
 * Default: data/processed/results.csv
 */

require_once __DIR__ . '/../app/config/database.php';
require_once __DIR__ . '/../app/includes/helpers.php';

$csvPath = $argv[1] ?? __DIR__ . '/../data/processed/results.csv';

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

$required = ['party_slug', 'declaration_year', 'tax_year', 'valid_choices', 'amount'];
foreach ($required as $col) {
    if (!in_array($col, $header, true)) {
        fwrite(STDERR, "Colonna obbligatoria mancante nel CSV: $col\n");
        exit(1);
    }
}

$findParty = $pdo->prepare('SELECT id FROM parties WHERE slug = :slug LIMIT 1');
$upsert = $pdo->prepare(
    'INSERT INTO results (party_id, declaration_year, tax_year, valid_choices, amount, source_id)
     VALUES (:party_id, :declaration_year, :tax_year, :valid_choices, :amount, :source_id)
     ON DUPLICATE KEY UPDATE
        tax_year = VALUES(tax_year),
        valid_choices = VALUES(valid_choices),
        amount = VALUES(amount),
        source_id = VALUES(source_id)'
);

$count = 0;
$skipped = 0;
while (($fields = fgetcsv($handle)) !== false) {
    $row = array_combine($header, $fields);

    $slug = clean_slug($row['party_slug'] ?? null);
    $declarationYear = clean_year($row['declaration_year'] ?? null);
    $taxYear = clean_year($row['tax_year'] ?? null);

    if ($slug === null || $declarationYear === null || $taxYear === null) {
        fwrite(STDERR, "Riga ignorata (slug o anno non validi): " . implode(',', $fields) . "\n");
        $skipped++;
        continue;
    }

    $findParty->execute(['slug' => $slug]);
    $partyId = $findParty->fetchColumn();
    if ($partyId === false) {
        fwrite(STDERR, "Partito non trovato per slug '$slug' (riga ignorata). Eseguire prima import_parties.php.\n");
        $skipped++;
        continue;
    }

    $upsert->execute([
        'party_id' => (int) $partyId,
        'declaration_year' => $declarationYear,
        'tax_year' => $taxYear,
        'valid_choices' => (int) ($row['valid_choices'] ?? 0),
        'amount' => (float) ($row['amount'] ?? 0),
        'source_id' => isset($row['source_id']) && $row['source_id'] !== '' ? (int) $row['source_id'] : null,
    ]);
    $count++;
}

fclose($handle);
echo "Importati/aggiornati $count risultati da $csvPath ($skipped righe ignorate).\n";
echo "Ricorda di eseguire: php scripts/calculate_indicators.php\n";
