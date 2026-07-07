<?php
declare(strict_types=1);
/** @var array|null $latest */
/** @var int|null $latestYear */
/** @var array $totals */
?>
<section class="hero">
  <div class="container">
    <p class="badge">Osservatorio ASSIF sul 5, 2 e 8 per mille</p>
    <h1>2x1000 Open Data — Partiti politici</h1>
    <p class="lead">
      Questa piattaforma raccoglie, normalizza e rende consultabili i dati ufficiali sulla destinazione
      volontaria del 2 per mille IRPEF ai partiti politici. Il 2x1000 non misura il consenso elettorale:
      racconta una forma specifica di partecipazione fiscale.
    </p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="/dashboard.php">Vai alla dashboard</a>
      <a class="btn" href="/open-data.php">Scarica i dati</a>
      <a class="btn" href="/metodo.php">Leggi il metodo</a>
    </div>
  </div>
</section>

<?php if ($latest): ?>
<section class="section">
  <div class="container">
    <h2>Dati <?= h((string) $latestYear) ?> <span class="badge">ultimo anno disponibile</span></h2>
    <div class="card-grid">
      <div class="card kpi-card">
        <div class="kpi-label">Scelte valide</div>
        <div class="kpi-value"><?= fmt_int($latest['total_valid_choices']) ?></div>
      </div>
      <div class="card kpi-card">
        <div class="kpi-label">Importo totale</div>
        <div class="kpi-value"><?= fmt_amount($latest['total_amount']) ?></div>
      </div>
      <div class="card kpi-card">
        <div class="kpi-label">Importo medio per scelta</div>
        <div class="kpi-value"><?= fmt_amount($latest['avg_amount_per_choice'], 2) ?></div>
      </div>
      <div class="card kpi-card">
        <div class="kpi-label">Partiti con scelte</div>
        <div class="kpi-value"><?= fmt_int($latest['number_of_parties_with_choices']) ?></div>
      </div>
    </div>
  </div>
</section>
<?php endif; ?>

<section class="section section-alt">
  <div class="container">
    <h2>Andamento storico</h2>
    <div class="grid-2">
      <div class="chart-card">
        <h3>Scelte valide nel tempo</h3>
        <div class="chart-wrap"><canvas id="chart-home-choices" role="img" aria-label="Andamento delle scelte valide totali negli anni"></canvas></div>
      </div>
      <div class="chart-card">
        <h3>Importo totale nel tempo</h3>
        <div class="chart-wrap"><canvas id="chart-home-amount" role="img" aria-label="Andamento dell'importo totale negli anni"></canvas></div>
      </div>
    </div>
    <details>
      <summary>Mostra dati in tabella</summary>
      <div class="table-wrap">
        <table class="data-table">
          <caption>Totali annuali 2x1000 ai partiti politici</caption>
          <thead><tr><th>Anno dichiarazione</th><th>Scelte valide</th><th>Importo totale</th></tr></thead>
          <tbody>
          <?php foreach ($totals as $t): ?>
            <tr>
              <td><?= h((string) $t['declaration_year']) ?></td>
              <td><?= fmt_int($t['total_valid_choices']) ?></td>
              <td><?= fmt_amount($t['total_amount']) ?></td>
            </tr>
          <?php endforeach; ?>
          </tbody>
        </table>
      </div>
    </details>
  </div>
</section>

<section class="section">
  <div class="container">
    <h2>Esplora i dati</h2>
    <div class="grid-3">
      <a class="card" href="/dashboard.php"><h3>Dashboard</h3><p class="text-muted">KPI annuali, top 10 partiti, concentrazione dell'importo.</p></a>
      <a class="card" href="/classifiche.php"><h3>Classifiche</h3><p class="text-muted">Più scelti, più finanziati, maggiore crescita e calo.</p></a>
      <a class="card" href="/partiti.php"><h3>Partiti</h3><p class="text-muted">Elenco completo con schede dedicate per ciascun partito.</p></a>
      <a class="card" href="/confronta.php"><h3>Confronta</h3><p class="text-muted">Metti a confronto fino a 5 partiti nel tempo.</p></a>
      <a class="card" href="/open-data.php"><h3>Open data</h3><p class="text-muted">Scarica i dataset completi in CSV e JSON.</p></a>
      <a class="card" href="/metodo.php"><h3>Metodo</h3><p class="text-muted">Cosa misura (e cosa non misura) il 2x1000.</p></a>
    </div>
  </div>
</section>

<script>
document.addEventListener('DOMContentLoaded', function () {
  var years = <?= json_encode(array_map(fn($t) => (int) $t['declaration_year'], $totals)) ?>;
  var choices = <?= json_encode(array_map(fn($t) => (int) $t['total_valid_choices'], $totals)) ?>;
  var amounts = <?= json_encode(array_map(fn($t) => (float) $t['total_amount'], $totals)) ?>;
  Viz.lineChart('chart-home-choices', years, [{ label: 'Scelte valide', data: choices }]);
  Viz.lineChart('chart-home-amount', years, [{ label: 'Importo totale (€)', data: amounts }], {
    yTickFormat: function (v) { return '€ ' + Number(v).toLocaleString('it-IT'); },
  });
});
</script>
