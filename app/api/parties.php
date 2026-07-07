<?php
declare(strict_types=1);

require_once __DIR__ . '/_bootstrap.php';

json_response(Party::listWithLatest());
