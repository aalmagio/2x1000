<?php
declare(strict_types=1);
/** @var int $year */
/** @var array $availableYears */
/** @var array|null $currentTotal */
/** @var array $totals */
/** @var array $topChoices */
/** @var array $topAmount */
/** @var array $yearResults */
?>
<div class="container section">
  <nav class="breadcrumb"><a href="/">Home</a> / <span aria-current="page">Dashboard</span></nav>
  <h1>Dashboard</h1>
  <p class="text-muted">Panoramica annuale delle scelte e degli importi del 2x1000 ai partiti politici.</p>

  <form class="filter-bar" method="get" action="/dashboard.php">
    <div class="field">
      <label for="year">Anno di dichiarazione</label>
      <select id="year" name="year" onchange="this.form.submit()">
        <?php foreach ($availableYears as $y): ?>
          <option value="<?= $y ?>" <?= $y === $year ? 'selected' : '' ?>><?= $y ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <noscript><button class="btn btn-sm" type="submit">Applica</button></noscript>
  </form>

  <?php if ($currentTotal): ?>
  <div class="card-grid">
    <div class="card kpi-card">
      <div class="kpi-label">Scelte valide</div>
      <div class="kpi-value"><?= fmt_int($currentTotal['total_valid_choices']) ?></div>
    </div>
    <div class="card kpi-card">
      <div class="kpi-label">Importo totale</div>
      <div class="kpi-value"><?= fmt_amount($currentTotal['total_amount']) ?></div>
    </div>
    <div class="card kpi-card">
      <div class="kpi-label">Importo medio per scelta</div>
      <div class="kpi-value"><?= fmt_amount($currentTotal['avg_amount_per_choice'], 2) ?></div>
    </div>
    <div class="card kpi-card">
      <div class="kpi-label">Tasso di scelta</div>
      <div class="kpi-value"><?= fmt_pct($currentTotal['valid_choice_rate'], 2) ?></div>
    </div>
    <div class="card kpi-card">
      <div class="kpi-label">Partiti con scelte</div>
      <div class="kpi-value"><?= fmt_int($currentTotal['number_of_parties_with_choices']) ?></div>
    </div>
    <div class="card kpi-card">
      <div class="kpi-label">Partiti ammessi</div>
      <div class="kpi-value"><?= fmt_int($currentTotal['number_of_parties_admitted']) ?></div>
    </div>
  </div>
  <?php else: ?>
    <p>Nessun dato disponibile per l'anno selezionato.</p>
  <?php endif; ?>

  <div class="grid-2">
    <div class="chart-card">
      <h3>Scelte valide nel tempo</h3>
      <div class="chart-wrap"><canvas id="chart-choices" role="img" aria-label="Scelte valide totali per anno"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>Importo totale nel tempo</h3>
      <div class="chart-wrap"><canvas id="chart-amount" role="img" aria-label="Importo totale per anno"></canvas></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="chart-card">
      <h3>Top 10 partiti per scelte (<?= $year ?>)</h3>
      <div class="chart-wrap"><canvas id="chart-top-choices" role="img" aria-label="Primi 10 partiti per numero di scelte"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>Top 10 partiti per importo (<?= $year ?>)</h3>
      <div class="chart-wrap"><canvas id="chart-top-amount" role="img" aria-label="Primi 10 partiti per importo"></canvas></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="chart-card">
      <h3>Scelte vs importo per partito (<?= $year ?>)</h3>
      <p class="text-muted">Ogni punto è un partito: in alto a destra i partiti con più scelte e più importo.</p>
      <div class="chart-wrap"><canvas id="chart-scatter" role="img" aria-label="Diagramma a dispersione scelte contro importo per partito"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>Importo medio per scelta nel tempo</h3>
      <p class="text-muted">Indicatore aggregato: non rappresenta il reddito medio dei sostenitori.</p>
      <div class="chart-wrap"><canvas id="chart-avg" role="img" aria-label="Importo medio per scelta per anno"></canvas></div>
    </div>
  </div>

  <div class="chart-card">
    <h3>Concentrazione dell'importo (<?= $year ?>)</h3>
    <p class="text-muted">Quota dell'importo totale raccolta dai primi 3, 5 e 10 partiti.</p>
    <div class="chart-wrap short"><canvas id="chart-concentration" role="img" aria-label="Quota di importo dei primi 3, 5 e 10 partiti"></canvas></div>
  </div>
</div>

<script>
  window.DASHBOARD_DATA = {
    year: <?= json_encode($year) ?>,
    totals: <?= json_encode($totals) ?>,
    topChoices: <?= json_encode($topChoices) ?>,
    topAmount: <?= json_encode($topAmount) ?>,
    yearResults: <?= json_encode($yearResults) ?>,
    currentTotal: <?= json_encode($currentTotal) ?>
  };
</script>
<script src="/assets/js/dashboard.js"></script>
