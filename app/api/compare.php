<?php
declare(strict_types=1);

require_once __DIR__ . '/_bootstrap.php';

$partiesParam = $_GET['parties'] ?? null;
if ($partiesParam === null || trim($partiesParam) === '') {
    json_error('Parametro "parties" mancante (elenco di slug separati da virgola).', 400);
}

$slugs = array_slice(array_filter(array_map('clean_slug', explode(',', $partiesParam))), 0, 5);
if ($slugs === []) {
    json_error('Nessuno slug valido fornito.', 400);
}

$ids = [];
$notFound = [];
foreach ($slugs as $slug) {
    $party = Party::findBySlug($slug);
    if ($party === null) {
        $notFound[] = $slug;
        continue;
    }
    $ids[] = (int) $party['id'];
}

if ($ids === []) {
    json_error('Nessuno dei partiti indicati è stato trovato.', 404);
}

json_response([
    'parties' => Result::compare($ids),
    'not_found' => $notFound,
]);
