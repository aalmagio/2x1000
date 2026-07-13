<?php
declare(strict_types=1);

/** Escape sicuro per output HTML. */
function h(?string $value): string
{
    return htmlspecialchars($value ?? '', ENT_QUOTES, 'UTF-8');
}

/** Formatta un numero intero con separatore delle migliaia italiano. */
function fmt_int(int|float|string|null $value): string
{
    if ($value === null) {
        return '—';
    }
    return number_format((float) $value, 0, ',', '.');
}

/** Formatta un importo in euro. */
function fmt_amount(int|float|string|null $value, int $decimals = 0): string
{
    if ($value === null) {
        return '—';
    }
    return '€ ' . number_format((float) $value, $decimals, ',', '.');
}

/** Formatta una percentuale. */
function fmt_pct(int|float|string|null $value, int $decimals = 1): string
{
    if ($value === null) {
        return '—';
    }
    return number_format((float) $value, $decimals, ',', '.') . '%';
}

/** Formatta una variazione con segno esplicito. */
function fmt_delta(int|float|string|null $value, bool $isPct = false, int $decimals = 1): string
{
    if ($value === null) {
        return '—';
    }
    $sign = $value > 0 ? '+' : '';
    return $sign . number_format((float) $value, $isPct ? $decimals : 0, ',', '.') . ($isPct ? '%' : '');
}

/** Valida e restituisce uno slug sicuro (solo lettere, numeri, trattini). */
function clean_slug(?string $value): ?string
{
    if ($value === null) {
        return null;
    }
    $value = strtolower(trim($value));
    return preg_match('/^[a-z0-9\-]{1,120}$/', $value) ? $value : null;
}

/** Valida e restituisce un anno numerico plausibile. */
function clean_year(mixed $value): ?int
{
    if ($value === null || $value === '') {
        return null;
    }
    if (!is_numeric($value)) {
        return null;
    }
    $year = (int) $value;
    return ($year >= 2000 && $year <= 2100) ? $year : null;
}

/** Valida un intero positivo generico (es. limit, id). */
function clean_int(mixed $value, int $min = 0, int $max = 1000000): ?int
{
    if ($value === null || $value === '' || !is_numeric($value)) {
        return null;
    }
    $int = (int) $value;
    return ($int >= $min && $int <= $max) ? $int : null;
}

/**
 * Restituisce lo slug generato da un nome (per import/normalizzazione).
 *
 * La tabella di trascrizione deve restare identica a quella in
 * python/common.py::slugify(): entrambi i lati scrivono lo slug univoco
 * della stessa tabella `parties`, quindi devono produrre risultati identici
 * per lo stesso input (es. "Südtiroler" e "Sudtiroler" → stesso slug).
 * Usa mb_strtolower (non strtolower) perché le lettere accentate maiuscole
 * sono multi-byte in UTF-8 e strtolower() non le riconosce.
 */
function slugify(string $text): string
{
    static $transliteration = [
        'à' => 'a', 'á' => 'a', 'â' => 'a', 'ã' => 'a', 'ä' => 'a', 'å' => 'a',
        'è' => 'e', 'é' => 'e', 'ê' => 'e', 'ë' => 'e',
        'ì' => 'i', 'í' => 'i', 'î' => 'i', 'ï' => 'i',
        'ò' => 'o', 'ó' => 'o', 'ô' => 'o', 'õ' => 'o', 'ö' => 'o',
        'ù' => 'u', 'ú' => 'u', 'û' => 'u', 'ü' => 'u',
        'ý' => 'y', 'ÿ' => 'y', 'ñ' => 'n', 'ç' => 'c',
    ];
    $text = mb_strtolower(trim($text), 'UTF-8');
    $text = strtr($text, $transliteration);
    $text = preg_replace('/[^a-z0-9]+/', '-', $text) ?? $text;
    return trim($text, '-');
}

/** Genera un URL assoluto al progetto (usa APP_URL se configurato). */
function base_url(string $path = ''): string
{
    $base = rtrim(env('APP_URL', ''), '/');
    return $base . '/' . ltrim($path, '/');
}

function current_path(): string
{
    return parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
}

/**
 * URL canonico della pagina corrente (assoluto, basato su APP_URL).
 * I parametri di filtro volatili (anno, regione, soglie) sono esclusi di
 * proposito: il canonico punta alla vista di default della pagina. L'unico
 * parametro che identifica un contenuto distinto è lo slug del partito.
 */
function canonical_url(): string
{
    $query = '';
    $slug = clean_slug($_GET['slug'] ?? null);
    if ($slug !== null) {
        $query = '?slug=' . rawurlencode($slug);
    }
    return base_url(current_path() . $query);
}
