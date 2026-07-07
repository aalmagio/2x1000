<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

render_page(
    __DIR__ . '/../app/views/sources.php',
    ['sources' => Source::all()],
    'Fonti — 2x1000 Open Data',
    'Elenco delle fonti ufficiali (MEF, Agenzia delle Entrate) utilizzate per i dati sul 2x1000 ai partiti politici.'
);
