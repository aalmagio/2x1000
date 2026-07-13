<?php
declare(strict_types=1);

/**
 * Genera i dataset open data (CSV + JSON) in data/exports/ a partire dal
 * database. Da eseguire dopo import_parties.php, import_results.php e
 * calculate_indicators.php.
 *
 * I CSV usano il punto e virgola (;) come separatore di campo e i numeri in
 * formato italiano (virgola decimale, punto delle migliaia), per aprirsi
 * correttamente in Excel in italiano con un doppio click. I JSON restano
 * con numeri "macchina" (punto decimale, nessun separatore delle migliaia),
 * dato che il formato JSON non supporta nativamente la notazione italiana:
 * renderli tali richiederebbe trasformarli in stringhe, rompendo qualunque
 * consumo automatico (grafici, script) che si aspetta un numero vero.
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

/** Formatta un numero in stile italiano (virgola decimale, punto delle migliaia); stringa vuota se NULL. */
function it_number(mixed $value, int $decimals): string
{
    if ($value === null || $value === '') {
        return '';
    }
    return number_format((float) $value, $decimals, ',', '.');
}

/** @param array<string,int> $decimals Nome colonna => numero di decimali da applicare in formato italiano. */
function write_csv(string $path, array $rows, array $decimals = []): void
{
    $fh = fopen($path, 'w');
    fprintf($fh, "\xEF\xBB\xBF"); // BOM per compatibilità Excel
    if ($rows !== []) {
        fputcsv($fh, array_keys($rows[0]), ';');
        foreach ($rows as $row) {
            foreach ($decimals as $col => $dec) {
                if (array_key_exists($col, $row)) {
                    $row[$col] = it_number($row[$col], $dec);
                }
            }
            fputcsv($fh, $row, ';');
        }
    }
    fclose($fh);
}

function write_json(string $path, array $rows): void
{
    file_put_contents($path, json_encode($rows, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
}

$datasets = [
    '2x1000_partiti_risultati' => [
        'sql' => 'SELECT * FROM v_results_full ORDER BY declaration_year ASC, canonical_name ASC',
        'decimals' => [
            'valid_choices' => 0, 'choices_delta_abs' => 0,
            'amount' => 2, 'avg_amount_per_choice' => 2, 'amount_delta_abs' => 2,
            'pct_total_taxpayers' => 5, 'pct_valid_choices' => 5, 'pct_amount' => 5,
            'amount_vs_choices_share_gap' => 5,
            'choices_delta_pct' => 2, 'amount_delta_pct' => 2,
        ],
    ],
    '2x1000_partiti_anagrafica' => [
        'sql' => 'SELECT id, canonical_name, slug, first_year, last_year, is_active, notes FROM parties ORDER BY canonical_name ASC',
        'decimals' => [],
    ],
    '2x1000_partiti_codici_annuali' => [
        'sql' => 'SELECT pc.id, p.slug AS party_slug, p.canonical_name, pc.declaration_year, pc.tax_year, pc.code, pc.official_name, pc.source_id
                   FROM party_codes pc JOIN parties p ON p.id = pc.party_id
                   ORDER BY pc.declaration_year DESC, p.canonical_name ASC',
        'decimals' => [],
    ],
    '2x1000_partiti_totali_annuali' => [
        'sql' => 'SELECT * FROM annual_totals ORDER BY declaration_year ASC',
        'decimals' => [
            'total_taxpayers' => 0, 'total_valid_choices' => 0,
            'total_amount' => 2, 'avg_amount_per_choice' => 2,
            'valid_choice_rate' => 5, 'top_3_amount_share' => 5, 'top_5_amount_share' => 5, 'top_10_amount_share' => 5,
        ],
    ],
    '2x1000_partiti_fonti' => [
        'sql' => 'SELECT * FROM sources ORDER BY id ASC',
        'decimals' => [],
    ],
    '2x1000_partiti_ripartizione_regionale' => [
        'sql' => 'SELECT rr.id, rr.party_id, p.slug AS party_slug, p.canonical_name, rr.declaration_year, rr.tax_year,
                          rr.region, rg.istat_code AS region_istat_code, rr.valid_choices, rr.is_suppressed, rr.source_id
                   FROM regional_results rr
                   JOIN parties p ON p.id = rr.party_id
                   LEFT JOIN regions rg ON rg.id = rr.region_id
                   ORDER BY rr.declaration_year DESC, p.canonical_name ASC, rr.region ASC',
        // Database non ancora migrato (tabella regions / colonna region_id assenti):
        // esporta senza codice ISTAT invece di interrompere la rigenerazione.
        'fallback_sql' => 'SELECT rr.id, rr.party_id, p.slug AS party_slug, p.canonical_name, rr.declaration_year, rr.tax_year,
                          rr.region, NULL AS region_istat_code, rr.valid_choices, rr.is_suppressed, rr.source_id
                   FROM regional_results rr JOIN parties p ON p.id = rr.party_id
                   ORDER BY rr.declaration_year DESC, p.canonical_name ASC, rr.region ASC',
        'decimals' => ['valid_choices' => 0],
    ],
];

$manifest = ['generated_at' => date('c'), 'files' => []];

foreach ($datasets as $name => $spec) {
    try {
        $rows = $pdo->query($spec['sql'])->fetchAll();
    } catch (PDOException $e) {
        if (!isset($spec['fallback_sql'])) {
            throw $e;
        }
        fwrite(STDERR, "Avviso: query principale fallita per $name (database non migrato? " .
            $e->getMessage() . "), uso il fallback.\n");
        $rows = $pdo->query($spec['fallback_sql'])->fetchAll();
    }
    write_csv("$exportDir/$name.csv", $rows, $spec['decimals']);
    write_json("$exportDir/$name.json", $rows);
    $manifest['files'][] = "$name.csv";
    $manifest['files'][] = "$name.json";
    echo "Esportato $name (" . count($rows) . " righe)\n";
}

file_put_contents("$exportDir/manifest.json", json_encode($manifest, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
echo "Manifest aggiornato: $exportDir/manifest.json\n";
echo "Completato.\n";
