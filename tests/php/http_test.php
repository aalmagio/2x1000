<?php
declare(strict_types=1);

/**
 * Test senza dipendenze delle funzioni di sicurezza in app/includes/http.php.
 * Uso: php tests/php/http_test.php (eseguito anche in CI).
 */

require_once __DIR__ . '/../../app/config/database.php';
require_once __DIR__ . '/../../app/includes/helpers.php';
require_once __DIR__ . '/../../app/includes/http.php';

$failures = 0;
function check(string $label, bool $ok): void
{
    global $failures;
    if (!$ok) {
        $failures++;
        fwrite(STDERR, "FALLITO: $label\n");
    }
}

// query_param: solo stringhe, mai array
$_GET = ['slug' => 'abc', 'arr' => ['x'], 'nested' => [['x']]];
check('query_param stringa', query_param('slug') === 'abc');
check('query_param array', query_param('arr') === null);
check('query_param array annidato', query_param('nested') === null);
check('query_param assente', query_param('missing') === null);
check('clean_slug con parametro array', clean_slug(query_param('arr')) === null);

// js_json: nessun carattere che possa uscire da un <script>
$encoded = js_json(['name' => '</script><script>alert(1)</script><!-- & \' "']);
check('js_json senza <', !str_contains($encoded, '<'));
check('js_json senza >', !str_contains($encoded, '>'));
check('js_json senza &', !str_contains($encoded, '&'));
check('js_json senza apice', !str_contains($encoded, "'"));
check('js_json reversibile', json_decode($encoded, true)['name'] === '</script><script>alert(1)</script><!-- & \' "');
check('js_json unicode leggibile', str_contains(js_json('Südtiroler'), 'ü'));
check('json_data_block', str_starts_with(json_data_block('page-data', [1]), '<script type="application/json" id="page-data">[1]</script>'));

// safe_url: solo http(s)
check('safe_url https', safe_url('https://www.finanze.gov.it/x') === 'https://www.finanze.gov.it/x');
check('safe_url http', safe_url(' http://example.org ') === 'http://example.org');
check('safe_url javascript', safe_url('javascript:alert(1)') === null);
check('safe_url data', safe_url('data:text/html,<script>') === null);
check('safe_url relativo', safe_url('//evil.example') === null);
check('safe_url null', safe_url(null) === null);

// etag_matches: tollera W/ e il suffisso aggiunto dalla compressione
check('etag uguale', etag_matches('W/"abc"', 'W/"abc"'));
check('etag con -gzip', etag_matches('W/"abc"', 'W/"abc-gzip"'));
check('etag con -br in lista', etag_matches('"abc"', '"zzz", "abc-br"'));
check('etag diverso', !etag_matches('W/"abc"', 'W/"abd"'));
check('etag assente', !etag_matches('W/"abc"', ''));

// asset_url: versione per i file esistenti, percorso invariato per gli altri
check('asset_url con versione', preg_match('#^/assets/css/main\.css\?v=[0-9a-f]{10}$#', asset_url('assets/css/main.css')) === 1);
check('asset_url file assente', asset_url('assets/nope.js') === '/assets/nope.js');

// Le viste non devono contenere script o stili inline: la CSP li bloccherebbe.
foreach (glob(__DIR__ . '/../../app/{views,includes}/*.php', GLOB_BRACE) as $file) {
    $src = (string) file_get_contents($file);
    $name = basename($file);
    if ($name === 'http.php') {
        continue; // solo funzioni PHP, nessun markup
    }
    check("$name: nessun gestore inline", preg_match('/\son[a-z]+\s*=\s*"/i', $src) === 0);
    check("$name: nessuno stile inline", preg_match('/\sstyle\s*=\s*"/i', $src) === 0);
    check("$name: nessuno <script> inline", preg_match('/<script(?![^>]*\b(?:src=|type="application\/(?:ld\+)?json"))[^>]*>/i', $src) === 0);
}

if ($failures > 0) {
    fwrite(STDERR, "$failures test falliti\n");
    exit(1);
}
echo "Test livello HTTP OK\n";
