<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$allParties = Party::all(true);

$requestedSlugs = [];
if (isset($_GET['parties']) && is_array($_GET['parties'])) {
    $requestedSlugs = array_slice(array_filter(array_map('clean_slug', $_GET['parties'])), 0, 5);
}

$selectedIds = [];
foreach ($requestedSlugs as $slug) {
    $p = Party::findBySlug($slug);
    if ($p !== null) {
        $selectedIds[] = (int) $p['id'];
    }
}

$comparison = $selectedIds !== [] ? Result::compare($selectedIds) : [];

render_page(
    __DIR__ . '/../app/views/compare.php',
    ['allParties' => $allParties, 'selectedSlugs' => $requestedSlugs, 'comparison' => $comparison],
    'Confronta partiti — 2x1000 Open Data',
    'Confronta fino a 5 partiti per scelte, importo, importo medio, quote e ranking nel tempo.'
);
