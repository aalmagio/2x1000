<?php
declare(strict_types=1);

require __DIR__ . '/../app/includes/bootstrap.php';

$exportDir = realpath(__DIR__ . '/../data/exports');
$requested = (string) ($_GET['file'] ?? '');

// Whitelist rigoroso: solo nomi file generati da scripts/export_open_data.php,
// niente concatenazione diretta di input utente nel percorso.
if (!preg_match('/^[a-zA-Z0-9_\-]+\.(csv|json)$/', $requested)) {
    http_response_code(400);
    echo 'Nome file non valido.';
    exit;
}

$path = $exportDir . '/' . $requested;
$realPath = realpath($path);

if ($realPath === false || !str_starts_with($realPath, $exportDir) || !is_file($realPath)) {
    http_response_code(404);
    echo 'File non trovato.';
    exit;
}

$mime = str_ends_with($requested, '.json') ? 'application/json' : 'text/csv';
header('Content-Type: ' . $mime . '; charset=utf-8');
header('Content-Disposition: attachment; filename="' . basename($realPath) . '"');
header('Content-Length: ' . filesize($realPath));
readfile($realPath);
