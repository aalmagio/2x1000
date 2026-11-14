<?php
declare(strict_types=1);

/**
 * Livello HTTP condiviso da pagine, API e download: header di sicurezza,
 * metodi ammessi, gestione degli errori senza fuga di dettagli, cache HTTP
 * (Cache-Control + ETag con risposta 304) e lettura sicura dei parametri.
 */

function app_is_production(): bool
{
    return env('APP_ENV', 'production') === 'production';
}

function request_is_https(): bool
{
    return (($_SERVER['HTTPS'] ?? '') !== '' && $_SERVER['HTTPS'] !== 'off')
        || ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https';
}

/**
 * Parametro di query come stringa, oppure null. Scarta gli array
 * (?slug[]=x): passati a funzioni tipizzate causerebbero un TypeError e
 * quindi un errore 500.
 */
function query_param(string $key): ?string
{
    $value = $_GET[$key] ?? null;
    return is_string($value) ? $value : null;
}

/**
 * Codifica JSON sicura dentro un elemento <script>: <, >, & e apici
 * diventano escape \uXXXX, quindi nessun valore può chiudere il tag o
 * aprire un commento HTML.
 */
function js_json(mixed $data): string
{
    return json_encode(
        $data,
        JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR
    );
}

/**
 * Blocco dati per il JavaScript della pagina. Un <script type="application/json">
 * non viene eseguito: permette una CSP senza 'unsafe-inline'. Il JS lo legge
 * con Site.pageData(id).
 */
function json_data_block(string $id, mixed $data): string
{
    return '<script type="application/json" id="' . h($id) . '">' . js_json($data) . '</script>' . "\n";
}

/** Restituisce l'URL solo se è http(s); blocca schemi come javascript: o data:. */
function safe_url(?string $url): ?string
{
    if ($url === null) {
        return null;
    }
    $url = trim($url);
    return preg_match('#^https?://#i', $url) === 1 ? $url : null;
}

/**
 * URL di un asset statico con versione derivata da data e dimensione del
 * file: consente una cache lunga e "immutable" lato browser (vedi
 * public/.htaccess) senza servire file vecchi dopo un deploy.
 */
function asset_url(string $path): string
{
    $path = '/' . ltrim($path, '/');
    $file = __DIR__ . '/../../public' . $path;
    $stat = @stat($file);
    if ($stat === false) {
        return $path;
    }
    return $path . '?v=' . substr(sha1($stat['mtime'] . '-' . $stat['size']), 0, 10);
}

/** Header di sicurezza comuni a tutte le risposte. */
function send_security_headers(string $kind): void
{
    header_remove('X-Powered-By');
    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: DENY');
    header('Referrer-Policy: strict-origin-when-cross-origin');
    header('Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), microphone=(), payment=(), usb=()');

    if ($kind === 'page') {
        // Tutto il JS e il CSS sono file del sito: nessuno script o stile inline.
        header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; "
            . "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
            . "base-uri 'self'; form-action 'self'; frame-ancestors 'none'");
        header('Cross-Origin-Opener-Policy: same-origin');
    } else {
        // JSON e file scaricabili: non devono poter caricare né eseguire nulla.
        header("Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; sandbox");
    }

    if (request_is_https() && app_is_production()) {
        header('Strict-Transport-Security: max-age=31536000');
    }
    if (!app_is_production()) {
        // Gli ambienti di sviluppo non devono finire nei motori di ricerca.
        header('X-Robots-Tag: noindex, nofollow');
    }
}

/** Ammette solo GET e HEAD (più OPTIONS per il preflight CORS delle API). */
function enforce_read_only_method(string $kind): void
{
    $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
    if ($method === 'GET' || $method === 'HEAD') {
        return;
    }
    if ($kind === 'api' && $method === 'OPTIONS') {
        http_response_code(204);
        header('Allow: GET, HEAD, OPTIONS');
        exit;
    }
    http_response_code(405);
    header('Allow: GET, HEAD' . ($kind === 'api' ? ', OPTIONS' : ''));
    header('Cache-Control: no-store');
    if ($kind === 'api') {
        echo json_encode(['error' => 'Metodo non consentito.']);
    } else {
        header('Content-Type: text/plain; charset=utf-8');
        echo 'Metodo non consentito.';
    }
    exit;
}

/** Risposta di errore generica: i dettagli vanno solo nel log del server. */
function send_error_response(string $kind): void
{
    if (headers_sent()) {
        return;
    }
    http_response_code(500);
    header('Cache-Control: no-store');
    if ($kind === 'api') {
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode(['error' => 'Errore interno del server.']);
    } else {
        header('Content-Type: text/html; charset=utf-8');
        echo '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><title>Errore</title></head>'
            . '<body><h1>Si è verificato un errore</h1><p>Riprova tra qualche minuto.</p></body></html>';
    }
}

/**
 * Confronta un ETag con l'header If-None-Match del client. Apache, quando
 * comprime la risposta, aggiunge all'ETag il suffisso "-gzip" o "-br": va
 * ignorato, altrimenti il confronto fallirebbe sempre e non si avrebbe mai
 * una risposta 304.
 */
function etag_matches(string $etag, string $ifNoneMatch): bool
{
    $normalize = static fn(string $tag): string => preg_replace('/^W\//', '', preg_replace('/-(?:gzip|br)"$/', '"', trim($tag)));
    foreach (explode(',', $ifNoneMatch) as $candidate) {
        if (trim($candidate) !== '' && $normalize($candidate) === $normalize($etag)) {
            return true;
        }
    }
    return false;
}

/**
 * Chiude la risposta: aggiunge Cache-Control ed ETag alle risposte 200 e
 * risponde 304 senza corpo se il client ha già la stessa versione.
 * Registrata come shutdown function da http_init().
 */
function http_finish(string $kind): void
{
    $body = ob_get_level() > 0 ? (string) ob_get_clean() : '';

    // Errore fatale (non intercettabile come eccezione): niente output parziale.
    $last = error_get_last();
    $fatal = $last !== null && in_array($last['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR], true);
    if ($fatal && app_is_production()) {
        send_error_response($kind);
        return;
    }

    if (headers_sent()) {
        echo $body;
        return;
    }

    if (http_response_code() !== 200) {
        header('Cache-Control: no-store');
        echo $body;
        return;
    }

    $maxAge = app_is_production() ? max(0, (int) env('CACHE_MAX_AGE', '600')) : 0;
    header($maxAge > 0
        ? "Cache-Control: public, max-age=$maxAge, stale-while-revalidate=86400"
        : 'Cache-Control: no-cache');

    $etag = 'W/"' . substr(sha1($body), 0, 20) . '"';
    header('ETag: ' . $etag);

    if (etag_matches($etag, $_SERVER['HTTP_IF_NONE_MATCH'] ?? '')) {
        http_response_code(304);
        header_remove('Content-Type');
        return;
    }

    echo $body;
}

/**
 * Da chiamare una volta, prima di qualunque output.
 *
 * @param string $kind 'page' (HTML), 'api' (JSON) oppure 'download' (file:
 *                     solo header e gestione errori, la cache la gestisce
 *                     download.php).
 */
function http_init(string $kind): void
{
    error_reporting(E_ALL);
    ini_set('log_errors', '1');
    if (app_is_production()) {
        ini_set('display_errors', '0');
    }

    set_exception_handler(static function (Throwable $e) use ($kind): void {
        error_log(sprintf('[2x1000] %s: %s in %s:%d', get_class($e), $e->getMessage(), $e->getFile(), $e->getLine()));
        if (ob_get_level() > 0) {
            ob_clean();
        }
        send_error_response($kind);
        if ($kind === 'page' && !app_is_production() && !headers_sent()) {
            // In sviluppo il dettaglio è utile; in produzione resta solo nel log.
            echo "\n<!-- " . h(get_class($e) . ': ' . $e->getMessage()) . " -->\n";
        }
    });

    send_security_headers($kind);
    enforce_read_only_method($kind);

    if ($kind !== 'download') {
        ob_start();
        register_shutdown_function('http_finish', $kind);
    }
}
