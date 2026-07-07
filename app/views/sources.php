<?php
declare(strict_types=1);
/** @var array $sources */
?>
<div class="container section">
  <nav class="breadcrumb"><a href="/">Home</a> / <span aria-current="page">Fonti</span></nav>
  <h1>Fonti</h1>
  <p class="text-muted">Elenco delle fonti ufficiali utilizzate per popolare la piattaforma.</p>

  <?php if ($sources === []): ?>
    <p>Nessuna fonte registrata.</p>
  <?php else: ?>
    <?php foreach ($sources as $s): ?>
      <div class="box-source">
        <h3 class="mt-0"><?= h($s['title']) ?></h3>
        <p><strong>Istituzione:</strong> <?= h($s['institution']) ?><br>
        <strong>Tipo:</strong> <?= h($s['source_type']) ?><br>
        <?php if ($s['url']): ?><strong>URL:</strong> <a href="<?= h($s['url']) ?>" target="_blank" rel="noopener"><?= h($s['url']) ?></a><br><?php endif; ?>
        <?php if ($s['publication_date']): ?><strong>Data pubblicazione:</strong> <?= h($s['publication_date']) ?><br><?php endif; ?>
        <?php if ($s['download_date']): ?><strong>Data download:</strong> <?= h($s['download_date']) ?><br><?php endif; ?>
        <?php if ($s['checksum']): ?><strong>Checksum:</strong> <code><?= h($s['checksum']) ?></code><br><?php endif; ?>
        <?php if ($s['notes']): ?><strong>Note:</strong> <?= h($s['notes']) ?><?php endif; ?>
        </p>
      </div>
    <?php endforeach; ?>
  <?php endif; ?>
</div>
