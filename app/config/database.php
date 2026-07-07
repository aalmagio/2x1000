<?php
declare(strict_types=1);

/**
 * Carica .env (se presente) e restituisce una connessione PDO condivisa.
 */

function env_load(string $path): void
{
    if (!is_file($path)) {
        return;
    }
    foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) {
            continue;
        }
        [$key, $value] = array_map('trim', explode('=', $line, 2));
        $value = trim($value, "\"'");
        if (getenv($key) === false) {
            putenv("$key=$value");
        }
        $_ENV[$key] = $_ENV[$key] ?? $value;
    }
}

env_load(__DIR__ . '/../../.env');

function env(string $key, ?string $default = null): ?string
{
    $value = getenv($key);
    return $value !== false ? $value : ($_ENV[$key] ?? $default);
}

function db(): PDO
{
    static $pdo = null;
    if ($pdo !== null) {
        return $pdo;
    }

    $host = env('DB_HOST', 'localhost');
    $port = env('DB_PORT', '3306');
    $name = env('DB_NAME', '2x1000');
    $charset = env('DB_CHARSET', 'utf8mb4');
    $user = env('DB_USER', 'root');
    $pass = env('DB_PASS', '');

    $dsn = "mysql:host=$host;port=$port;dbname=$name;charset=$charset";

    try {
        $pdo = new PDO($dsn, $user, $pass, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
    } catch (PDOException $e) {
        http_response_code(500);
        if (str_starts_with($_SERVER['SCRIPT_NAME'] ?? '', '/api/')) {
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode(['error' => 'Database non disponibile']);
        } else {
            echo 'Database non disponibile. Verifica la configurazione in .env.';
        }
        exit;
    }

    return $pdo;
}
