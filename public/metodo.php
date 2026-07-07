<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

render_page(
    __DIR__ . '/../app/views/method.php',
    [],
    'Metodo — 2x1000 Open Data',
    "Cosa misura e cosa non misura il 2x1000, fonti, normalizzazioni, calcolo degli indicatori e limiti interpretativi."
);
