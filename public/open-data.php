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

$descriptions = [
    '2x1000_partiti_risultati' => 'Serie storica dei risultati annuali del 2 per mille IRPEF per partito politico: scelte valide, importo assegnato, quote percentuali, ranking e variazioni annue.',
    '2x1000_partiti_anagrafica' => 'Anagrafica normalizzata dei partiti politici presenti nella serie storica del 2x1000, con slug, anni di presenza e stato.',
    '2x1000_partiti_codici_annuali' => 'Codici da indicare in dichiarazione dei redditi per ciascun partito ammesso al 2x1000, per anno (fonte: Agenzia delle Entrate).',
    '2x1000_partiti_totali_annuali' => 'Totali annuali di sistema del 2x1000: scelte valide, importo totale, tasso di scelta, numero di partiti, concentrazione.',
    '2x1000_partiti_fonti' => 'Elenco delle fonti ufficiali (MEF — Dipartimento delle Finanze, Agenzia delle Entrate) da cui derivano i dati, con URL e checksum.',
    '2x1000_partiti_ripartizione_regionale' => 'Ripartizione regionale delle scelte del 2x1000 per partito e anno, con codice ISTAT della regione.',
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

// JSON-LD schema.org (DataCatalog + Dataset): è ciò che fa indicizzare i
// dataset su Google Dataset Search. Richiede URL assoluti, quindi solo con
// APP_URL configurato.
$datasetsLd = [];
if ((env('APP_URL', '') ?? '') !== '' && $files !== []) {
    $byBase = [];
    foreach ($files as $f) {
        $base = pathinfo($f['file'], PATHINFO_FILENAME);
        $byBase[$base][strtolower($f['ext'])] = $f['file'];
    }
    $creator = [
        '@type' => 'Organization',
        'name' => 'Osservatorio ASSIF sul 5, 2 e 8 per mille',
        'url' => 'https://osservatorio.assif.it',
    ];
    foreach ($byBase as $base => $exts) {
        $distribution = [];
        foreach ($exts as $ext => $filename) {
            $distribution[] = [
                '@type' => 'DataDownload',
                'encodingFormat' => $ext === 'csv' ? 'text/csv' : 'application/json',
                'contentUrl' => base_url('/download.php?file=' . rawurlencode($filename)),
            ];
        }
        $dataset = [
            '@type' => 'Dataset',
            'name' => $labels[$base] ?? $base,
            'description' => $descriptions[$base] ?? ('Dataset ' . $base . ' del 2x1000 ai partiti politici.'),
            'url' => base_url('/open-data.php'),
            'license' => 'https://creativecommons.org/licenses/by/4.0/',
            'isAccessibleForFree' => true,
            'inLanguage' => 'it',
            'creator' => $creator,
            'distribution' => $distribution,
        ];
        if ($generatedAt !== null) {
            $dataset['dateModified'] = $generatedAt;
        }
        $datasetsLd[] = $dataset;
    }
}

render_page(
    __DIR__ . '/../app/views/open-data.php',
    ['files' => $files, 'generatedAt' => $generatedAt, 'datasetsLd' => $datasetsLd],
    'Open data — 2x1000 Open Data',
    'Scarica i dataset CSV e JSON sul 2x1000 ai partiti politici: risultati, anagrafica, codici, totali annuali e fonti.'
);
