<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$exportDir = __DIR__ . '/../data/exports';
$manifestPath = $exportDir . '/manifest.json';

$labels = [
    '2x1000_partiti_risultati' => 'Risultati annuali per partito',
    '2x1000_partiti_anagrafica' => 'Anagrafica partiti',
    '2x1000_partiti_codici_annuali' => 'Codici annuali da dichiarazione',
    '2x1000_partiti_totali_annuali' => 'Totali annuali di sistema',
    '2x1000_partiti_fonti' => 'Fonti ufficiali',
    '2x1000_partiti_ripartizione_regionale' => 'Ripartizione regionale delle scelte',
];

$files = [];
$generatedAt = null;

if (is_file($manifestPath)) {
    $manifest = json_decode((string) file_get_contents($manifestPath), true) ?? [];
    $generatedAt = $manifest['generated_at'] ?? null;
    foreach (($manifest['files'] ?? []) as $filename) {
        $base = pathinfo($filename, PATHINFO_FILENAME);
        $ext = pathinfo($filename, PATHINFO_EXTENSION);
        $files[] = ['file' => $filename, 'ext' => $ext, 'label' => ($labels[$base] ?? $base) . ' (' . strtoupper($ext) . ')'];
    }
}

render_page(
    __DIR__ . '/../app/views/open-data.php',
    ['files' => $files, 'generatedAt' => $generatedAt],
    'Open data — 2x1000 Open Data',
    'Scarica i dataset CSV e JSON sul 2x1000 ai partiti politici: risultati, anagrafica, codici, totali annuali e fonti.'
);
