<?php
declare(strict_types=1);

const SKIP_PAGE_HTTP_INIT = true;
require __DIR__ . '/../app/includes/bootstrap.php';
http_init('download');

$exportDir = realpath(__DIR__ . '/../data/exports');
$requested = query_param('file') ?? '';

// Whitelist rigoroso: solo nomi file generati da scripts/export_open_data.php,
// niente concatenazione diretta di input utente nel percorso.
if ($exportDir === false || !preg_match('/^[a-zA-Z0-9_\-]{1,100}\.(csv|json)$/', $requested)) {
    http_response_code(400);
    header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: no-store');
    echo 'Nome file non valido.';
    exit;
}

$realPath = realpath($exportDir . '/' . $requested);

if ($realPath === false || !str_starts_with($realPath, $exportDir . DIRECTORY_SEPARATOR) || !is_file($realPath)) {
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: no-store');
    echo 'File non trovato.';
    exit;
}

// I dataset cambiano solo quando viene rieseguito l'export: ETag e
// Last-Modified permettono al client di non riscaricare un file invariato.
$mtime = (int) filemtime($realPath);
$size = (int) filesize($realPath);
$etag = '"' . dechex($mtime) . '-' . dechex($size) . '"';

header('Cache-Control: public, max-age=3600');
header('ETag: ' . $etag);
header('Last-Modified: ' . gmdate('D, d M Y H:i:s', $mtime) . ' GMT');
// Dati aperti (CC BY 4.0): riusabili anche da applicazioni di altri siti.
header('Access-Control-Allow-Origin: *');

if (etag_matches($etag, $_SERVER['HTTP_IF_NONE_MATCH'] ?? '')) {
    http_response_code(304);
    exit;
}

$mime = str_ends_with($requested, '.json') ? 'application/json' : 'text/csv';
header('Content-Type: ' . $mime . '; charset=utf-8');
header('Content-Disposition: attachment; filename="' . basename($realPath) . '"');
header('Content-Length: ' . $size);
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'HEAD') {
    readfile($realPath);
}
