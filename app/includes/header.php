<?php
/** @var string $pageTitle */
/** @var string $pageDescription */
declare(strict_types=1);

$navItems = [
    '/' => 'Home',
    '/dashboard.php' => 'Dashboard',
    '/partiti.php' => 'Partiti',
    '/classifiche.php' => 'Classifiche',
    '/confronta.php' => 'Confronta',
    '/open-data.php' => 'Open data',
    '/metodo.php' => 'Metodo',
    '/fonti.php' => 'Fonti',
];
$currentPath = current_path();
?>
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= h($pageTitle ?? '2x1000 Open Data — Partiti politici') ?></title>
<meta name="description" content="<?= h($pageDescription ?? 'Dati ufficiali sulla destinazione del 2 per mille IRPEF ai partiti politici, a cura dell\'Osservatorio ASSIF sul 5, 2 e 8 per mille.') ?>">
<link rel="stylesheet" href="/assets/css/main.css">
<script src="/assets/js/vendor/chart.umd.min.js"></script>
</head>
<body>
<a class="skip-link" href="#main-content">Vai al contenuto principale</a>
<header class="site-header">
  <div class="container header-inner">
    <a class="brand" href="/">
      <span class="brand-mark">2×1000</span>
      <span class="brand-sub">Open Data · Partiti politici</span>
    </a>
    <nav class="main-nav" aria-label="Navigazione principale">
      <button class="nav-toggle" aria-expanded="false" aria-controls="main-nav-list">Menu</button>
      <ul id="main-nav-list">
        <?php foreach ($navItems as $href => $label): ?>
          <li>
            <a href="<?= h($href) ?>" <?= ($currentPath === $href || ($href !== '/' && str_starts_with($currentPath, $href))) ? 'class="active" aria-current="page"' : '' ?>><?= h($label) ?></a>
          </li>
        <?php endforeach; ?>
      </ul>
    </nav>
  </div>
  <div class="observatory-strip">
    <div class="container">Osservatorio ASSIF sul 5, 2 e 8 per mille</div>
  </div>
</header>
<main id="main-content">
