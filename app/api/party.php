<?php
declare(strict_types=1);

require_once __DIR__ . '/_bootstrap.php';

$slug = clean_slug($_GET['slug'] ?? null);
if ($slug === null) {
    json_error('Parametro "slug" mancante o non valido.', 400);
}

$party = Party::findBySlug($slug);
if ($party === null) {
    json_error('Partito non trovato.', 404);
}

json_response([
    'party' => $party,
    'aliases' => Party::aliases((int) $party['id']),
    'codes' => Party::codes((int) $party['id']),
    'results' => Result::forParty((int) $party['id']),
    'sources' => Source::forParty((int) $party['id']),
]);
