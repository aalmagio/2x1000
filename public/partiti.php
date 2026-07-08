<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$rows = Result::latestForAllParties();

// Esclude i partiti senza presenza storica o senza scelte nell'ultimo anno
// disponibile (anagrafati ma senza dati reali, o con 0 scelte).
$rows = array_values(array_filter($rows, static function (array $r): bool {
    return (int) ($r['years_present'] ?? 0) > 0 && (int) ($r['valid_choices'] ?? 0) > 0;
}));

usort($rows, fn($a, $b) => strcmp($a['canonical_name'], $b['canonical_name']));

render_page(
    __DIR__ . '/../app/views/parties.php',
    ['rows' => $rows],
    'Partiti — 2x1000 Open Data',
    'Elenco dei partiti politici con dati storici sul 2x1000 IRPEF.'
);
