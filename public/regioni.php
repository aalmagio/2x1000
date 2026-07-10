<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$availableYears = RegionalResult::availableYears();
$latestYear = end($availableYears) ?: null;
$year = clean_year($_GET['year'] ?? null);
if ($year === null || !in_array($year, $availableYears, true)) {
    $year = $latestYear;
}

$regions = [];
if ($year !== null) {
    $topByRegion = RegionalResult::topPartyByRegion($year);
    foreach (RegionalResult::totalsByYear($year) as $row) {
        $row['top_party'] = $topByRegion[$row['region']] ?? null;
        $regions[] = $row;
    }
}

render_page(
    __DIR__ . '/../app/views/regions.php',
    compact('year', 'availableYears', 'regions'),
    'Regioni — 2x1000 Open Data',
    'Ripartizione regionale delle scelte del 2x1000 ai partiti politici, per anno di dichiarazione.'
);
