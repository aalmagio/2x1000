<?php
declare(strict_types=1);
/** @var array $allParties */
/** @var array $selectedSlugs */
/** @var array $comparison */
?>
<div class="container section">
  <nav class="breadcrumb"><a href="/">Home</a> / <span aria-current="page">Confronta</span></nav>
  <h1>Confronta partiti</h1>
  <p class="text-muted">Seleziona fino a 5 partiti per confrontare scelte, importi, importo medio, quote e ranking nel tempo.</p>

  <form method="get" action="/confronta.php">
    <fieldset class="compare-picker" aria-label="Selezione partiti da confrontare (massimo 5)">
      <legend class="sr-only">Seleziona fino a 5 partiti</legend>
      <?php foreach ($allParties as $p): ?>
        <label>
          <input type="checkbox" name="parties[]" value="<?= h($p['slug']) ?>" <?= in_array($p['slug'], $selectedSlugs, true) ? 'checked' : '' ?>>
          <?= h($p['canonical_name']) ?>
        </label>
      <?php endforeach; ?>
    </fieldset>
    <button class="btn btn-primary" type="submit">Confronta</button>
  </form>

  <?php if ($comparison === []): ?>
    <p class="text-muted">Seleziona almeno un partito per iniziare il confronto.</p>
  <?php else: ?>
    <div class="grid-2">
      <div class="chart-card">
        <h3>Scelte valide nel tempo</h3>
        <div class="chart-wrap"><canvas id="chart-compare-choices" role="img" aria-label="Confronto scelte valide nel tempo"></canvas></div>
      </div>
      <div class="chart-card">
        <h3>Importo nel tempo</h3>
        <div class="chart-wrap"><canvas id="chart-compare-amount" role="img" aria-label="Confronto importo nel tempo"></canvas></div>
      </div>
    </div>
    <div class="chart-card">
      <h3>Importo medio per scelta nel tempo</h3>
      <div class="chart-wrap"><canvas id="chart-compare-avg" role="img" aria-label="Confronto importo medio per scelta nel tempo"></canvas></div>
    </div>

    <h2>Tabella comparativa</h2>
    <div class="table-wrap">
      <table class="data-table">
        <caption>Confronto annuale tra i partiti selezionati</caption>
        <thead><tr><th>Partito</th><th>Anno</th><th>Scelte</th><th>Quota scelte</th><th>Importo</th><th>Quota importo</th><th>Importo medio</th><th>Rank scelte</th><th>Rank importo</th></tr></thead>
        <tbody>
        <?php foreach ($comparison as $group): foreach ($group['years'] as $y): ?>
          <tr>
            <td><a href="/partito.php?slug=<?= h($group['party']['slug']) ?>"><?= h($group['party']['canonical_name']) ?></a></td>
            <td><?= h((string) $y['declaration_year']) ?></td>
            <td><?= fmt_int($y['valid_choices']) ?></td>
            <td><?= fmt_pct($y['pct_valid_choices']) ?></td>
            <td><?= fmt_amount($y['amount']) ?></td>
            <td><?= fmt_pct($y['pct_amount']) ?></td>
            <td><?= fmt_amount($y['avg_amount_per_choice'], 2) ?></td>
            <td>#<?= h((string) $y['rank_choices']) ?></td>
            <td>#<?= h((string) $y['rank_amount']) ?></td>
          </tr>
        <?php endforeach; endforeach; ?>
        </tbody>
      </table>
    </div>
  <?php endif; ?>
</div>

<script>
  window.COMPARE_DATA = <?= json_encode($comparison) ?>;
</script>
<script src="/assets/js/compare.js"></script>
