<?php
declare(strict_types=1);

require_once __DIR__ . '/_bootstrap.php';

$yearParam = $_GET['year'] ?? null;

if ($yearParam !== null) {
    $year = clean_year($yearParam);
    if ($year === null) {
        json_error('Parametro "year" non valido.', 400);
    }
    $row = AnnualTotal::forYear($year);
    if ($row === null) {
        json_error('Anno non trovato.', 404);
    }
    json_response($row);
}

json_response(AnnualTotal::all());
