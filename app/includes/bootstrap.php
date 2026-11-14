<?php
declare(strict_types=1);

require_once __DIR__ . '/../config/database.php';
require_once __DIR__ . '/helpers.php';
require_once __DIR__ . '/http.php';
require_once __DIR__ . '/layout.php';
require_once __DIR__ . '/../models/Party.php';
require_once __DIR__ . '/../models/Result.php';
require_once __DIR__ . '/../models/AnnualTotal.php';
require_once __DIR__ . '/../models/Source.php';
require_once __DIR__ . '/../models/RegionalResult.php';

// download.php imposta SKIP_PAGE_HTTP_INIT e chiama http_init('download').
if (PHP_SAPI !== 'cli' && !defined('SKIP_PAGE_HTTP_INIT')) {
    http_init('page');
}
