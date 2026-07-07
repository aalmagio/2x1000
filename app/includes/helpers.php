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

/** Restituisce lo slug generato da un nome (per import/normalizzazione). */
function slugify(string $text): string
{
    $text = strtolower(trim($text));
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
