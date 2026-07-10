<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$availableYears = Result::availableYears();
$latestYear = end($availableYears) ?: null;
$year = clean_year($_GET['year'] ?? null);
if ($year === null || !in_array($year, $availableYears, true)) {
    $year = $latestYear;
}

$minPrevious = clean_int($_GET['min_previous'] ?? null, 0, 10000000) ?? (int) (env('GROWTH_MIN_PREVIOUS_CHOICES', '5000'));

$availableRegions = RegionalResult::availableRegions();
$region = trim((string) ($_GET['region'] ?? ''));
if ($region !== '' && !in_array($region, $availableRegions, true)) {
    $region = '';
}

$rankings = [];
$regionalRanking = null;
if ($year !== null && $region !== '') {
    $regionalRanking = [
        'region' => $region,
        'rows' => RegionalResult::rankingForRegion($year, $region, 20),
        'suppressed' => RegionalResult::suppressedPartiesForRegion($year, $region),
    ];
} elseif ($year !== null) {
    $rankings = [
        'choices' => ['title' => 'Più scelti', 'rows' => Result::top($year, 'choices', 10), 'cols' => ['choices']],
        'amount' => ['title' => 'Più finanziati', 'rows' => Result::top($year, 'amount', 10), 'cols' => ['amount']],
        'avg_amount' => ['title' => 'Importo medio più alto', 'rows' => Result::top($year, 'avg_amount', 10), 'cols' => ['avg']],
        'growth_choices' => ['title' => 'Maggiore crescita scelte', 'rows' => Result::growthRanking($year, 'choices', 'growth', $minPrevious, 10), 'cols' => ['growth']],
        'growth_amount' => ['title' => 'Maggiore crescita importo', 'rows' => Result::growthRanking($year, 'amount', 'growth', $minPrevious, 10), 'cols' => ['growth']],
        'decline_choices' => ['title' => 'Maggiore calo scelte', 'rows' => Result::growthRanking($year, 'choices', 'decline', $minPrevious, 10), 'cols' => ['growth']],
        'decline_amount' => ['title' => 'Maggiore calo importo', 'rows' => Result::growthRanking($year, 'amount', 'decline', $minPrevious, 10), 'cols' => ['growth']],
        'gap_positive' => ['title' => 'Maggiore differenza positiva (quota importo − quota scelte)', 'rows' => Result::shareGapRanking($year, 'positive', 10), 'cols' => ['gap']],
        'gap_negative' => ['title' => 'Maggiore differenza negativa (quota importo − quota scelte)', 'rows' => Result::shareGapRanking($year, 'negative', 10), 'cols' => ['gap']],
    ];
}
$longestPresence = Result::longestPresenceRanking(10);

render_page(
    __DIR__ . '/../app/views/rankings.php',
    compact('year', 'availableYears', 'minPrevious', 'rankings', 'longestPresence', 'availableRegions', 'region', 'regionalRanking'),
    'Classifiche — 2x1000 Open Data',
    'Classifiche dei partiti per scelte, importo, crescita e presenza storica nel 2x1000.'
);
