<?php
declare(strict_types=1);

/**
 * Genera i dataset open data (CSV + JSON) in data/exports/ a partire dal
 * database. Da eseguire dopo import_parties.php, import_results.php e
 * calculate_indicators.php.
 *
 * Uso: php scripts/export_open_data.php
 */

require_once __DIR__ . '/../app/config/database.php';

$pdo = db();
$exportDir = __DIR__ . '/../data/exports';
if (!is_dir($exportDir) && !mkdir($exportDir, 0775, true) && !is_dir($exportDir)) {
    fwrite(STDERR, "Impossibile creare la cartella $exportDir\n");
    exit(1);
}

function write_csv(string $path, array $rows): void
{
    $fh = fopen($path, 'w');
    fprintf($fh, "\xEF\xBB\xBF"); // BOM per compatibilità Excel
    if ($rows !== []) {
        fputcsv($fh, array_keys($rows[0]));
        foreach ($rows as $row) {
            fputcsv($fh, $row);
        }
    }
    fclose($fh);
}

function write_json(string $path, array $rows): void
{
    file_put_contents($path, json_encode($rows, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
}

$datasets = [
    '2x1000_partiti_risultati' => 'SELECT * FROM v_results_full ORDER BY declaration_year ASC, canonical_name ASC',
    '2x1000_partiti_anagrafica' => 'SELECT id, canonical_name, slug, first_year, last_year, is_active, notes FROM parties ORDER BY canonical_name ASC',
    '2x1000_partiti_codici_annuali' => 'SELECT pc.id, p.slug AS party_slug, p.canonical_name, pc.declaration_year, pc.tax_year, pc.code, pc.official_name, pc.source_id
                                          FROM party_codes pc JOIN parties p ON p.id = pc.party_id
                                          ORDER BY pc.declaration_year DESC, p.canonical_name ASC',
    '2x1000_partiti_totali_annuali' => 'SELECT * FROM annual_totals ORDER BY declaration_year ASC',
    '2x1000_partiti_fonti' => 'SELECT * FROM sources ORDER BY id ASC',
];

$manifest = ['generated_at' => date('c'), 'files' => []];

foreach ($datasets as $name => $sql) {
    $rows = $pdo->query($sql)->fetchAll();
    write_csv("$exportDir/$name.csv", $rows);
    write_json("$exportDir/$name.json", $rows);
    $manifest['files'][] = "$name.csv";
    $manifest['files'][] = "$name.json";
    echo "Esportato $name (" . count($rows) . " righe)\n";
}

file_put_contents("$exportDir/manifest.json", json_encode($manifest, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
echo "Manifest aggiornato: $exportDir/manifest.json\n";
echo "Completato.\n";
