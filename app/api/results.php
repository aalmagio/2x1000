<?php
declare(strict_types=1);

require_once __DIR__ . '/_bootstrap.php';

$yearParam = query_param('year');

if ($yearParam !== null) {
    $year = clean_year($yearParam);
    if ($year === null) {
        json_error('Parametro "year" non valido.', 400);
    }
    if (!in_array($year, Result::availableYears(), true)) {
        json_error('Anno non trovato.', 404);
    }
    json_response(Result::forYear($year));
}

// Una sola query per l'intera serie storica, raggruppata per anno in PHP.
$byYear = [];
foreach (Result::all() as $row) {
    $byYear[(int) $row['declaration_year']][] = $row;
}
$all = [];
foreach ($byYear as $year => $rows) {
    $all[] = ['declaration_year' => $year, 'results' => $rows];
}
json_response($all);
