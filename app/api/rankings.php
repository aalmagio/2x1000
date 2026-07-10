<?php
declare(strict_types=1);

require_once __DIR__ . '/_bootstrap.php';

$validTypes = [
    'choices', 'amount', 'avg_amount',
    'growth_choices', 'growth_amount',
    'decline_choices', 'decline_amount',
    'gap_positive', 'gap_negative',
    'longest_presence',
];

$type = $_GET['type'] ?? null;
if ($type === null || !in_array($type, $validTypes, true)) {
    json_error('Parametro "type" mancante o non valido. Valori ammessi: ' . implode(', ', $validTypes), 400);
}

$limit = clean_int($_GET['limit'] ?? null, 1, 100) ?? 10;

if ($type === 'longest_presence') {
    json_response(Result::longestPresenceRanking($limit));
}

$year = clean_year($_GET['year'] ?? null);
if ($year === null) {
    json_error('Parametro "year" mancante o non valido.', 400);
}
if (!in_array($year, Result::availableYears(), true)) {
    json_error('Anno non trovato.', 404);
}

$region = trim((string) ($_GET['region'] ?? ''));
if ($region !== '') {
    if ($type !== 'choices') {
        json_error('Il parametro "region" è supportato solo per type=choices: la ripartizione regionale include solo il numero di scelte, non importi.', 400);
    }
    if (!in_array($region, RegionalResult::availableRegions(), true)) {
        json_error('Regione non trovata.', 404);
    }
    json_response(RegionalResult::rankingForRegion($year, $region, $limit));
}

$minPrevious = clean_int($_GET['min_previous'] ?? null, 0, 10000000) ?? (int) (env('GROWTH_MIN_PREVIOUS_CHOICES', '5000'));

$result = match ($type) {
    'choices' => Result::top($year, 'choices', $limit),
    'amount' => Result::top($year, 'amount', $limit),
    'avg_amount' => Result::top($year, 'avg_amount', $limit),
    'growth_choices' => Result::growthRanking($year, 'choices', 'growth', $minPrevious, $limit),
    'growth_amount' => Result::growthRanking($year, 'amount', 'growth', $minPrevious, $limit),
    'decline_choices' => Result::growthRanking($year, 'choices', 'decline', $minPrevious, $limit),
    'decline_amount' => Result::growthRanking($year, 'amount', 'decline', $minPrevious, $limit),
    'gap_positive' => Result::shareGapRanking($year, 'positive', $limit),
    'gap_negative' => Result::shareGapRanking($year, 'negative', $limit),
    default => [],
};

json_response($result);
