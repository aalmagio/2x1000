<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$slug = clean_slug($_GET['slug'] ?? null);
$party = $slug !== null ? Party::findBySlug($slug) : null;

if ($party === null) {
    http_response_code(404);
    render_page(__DIR__ . '/../app/views/not-found.php', ['message' => 'Partito non trovato.'], 'Partito non trovato — 2x1000 Open Data');
    exit;
}

$results = Result::forParty((int) $party['id']);
$latest = $results !== [] ? end($results) : null;

render_page(
    __DIR__ . '/../app/views/party-detail.php',
    [
        'party' => $party,
        'results' => $results,
        'latest' => $latest,
        'aliases' => Party::aliases((int) $party['id']),
        'codes' => Party::codes((int) $party['id']),
        'sources' => Source::forParty((int) $party['id']),
        'regionalResults' => RegionalResult::forParty((int) $party['id']),
    ],
    $party['canonical_name'] . ' — 2x1000 Open Data',
    'Scheda dati 2x1000 per ' . $party['canonical_name']
);
