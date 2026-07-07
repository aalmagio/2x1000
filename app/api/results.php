<?php
declare(strict_types=1);

require_once __DIR__ . '/_bootstrap.php';

$yearParam = $_GET['year'] ?? null;

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

$years = Result::availableYears();
$all = [];
foreach ($years as $year) {
    $all[] = ['declaration_year' => $year, 'results' => Result::forYear($year)];
}
json_response($all);
