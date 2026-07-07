<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$availableYears = Result::availableYears();
$latestYear = end($availableYears) ?: null;
$year = clean_year($_GET['year'] ?? null);
if ($year === null || !in_array($year, $availableYears, true)) {
    $year = $latestYear;
}

$currentTotal = $year !== null ? AnnualTotal::forYear($year) : null;
$totals = AnnualTotal::all();
$topChoices = $year !== null ? Result::top($year, 'choices', 10) : [];
$topAmount = $year !== null ? Result::top($year, 'amount', 10) : [];
$yearResults = $year !== null ? Result::forYear($year) : [];

render_page(
    __DIR__ . '/../app/views/dashboard.php',
    compact('year', 'availableYears', 'currentTotal', 'totals', 'topChoices', 'topAmount', 'yearResults'),
    'Dashboard — 2x1000 Open Data',
    'KPI annuali, top 10 partiti per scelte e importo, concentrazione dell\'importo.'
);
