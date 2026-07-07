<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$rows = Result::latestForAllParties();

// Assicura che compaiano anche i partiti anagrafati senza ancora risultati.
$withResults = array_column($rows, null, 'party_id');
foreach (Party::all() as $p) {
    if (!isset($withResults[$p['id']])) {
        $rows[] = [
            'party_id' => $p['id'],
            'canonical_name' => $p['canonical_name'],
            'slug' => $p['slug'],
            'years_present' => 0,
            'declaration_year' => null,
            'valid_choices' => null,
            'amount' => null,
            'avg_amount_per_choice' => null,
            'choices_delta_pct' => null,
        ];
    }
}
usort($rows, fn($a, $b) => strcmp($a['canonical_name'], $b['canonical_name']));

render_page(
    __DIR__ . '/../app/views/parties.php',
    ['rows' => $rows],
    'Partiti — 2x1000 Open Data',
    'Elenco dei partiti politici con dati storici sul 2x1000 IRPEF.'
);
