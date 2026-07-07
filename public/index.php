<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$latestYear = AnnualTotal::latestYear();
$latest = $latestYear !== null ? AnnualTotal::forYear($latestYear) : null;
$totals = AnnualTotal::all();

render_page(
    __DIR__ . '/../app/views/home.php',
    ['latestYear' => $latestYear, 'latest' => $latest, 'totals' => $totals],
    '2x1000 Open Data — Partiti politici',
    "Dati ufficiali sulla destinazione del 2 per mille IRPEF ai partiti politici, a cura dell'Osservatorio ASSIF."
);
