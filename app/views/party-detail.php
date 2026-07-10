<?php
declare(strict_types=1);
/** @var array $party */
/** @var array $results */
/** @var array $aliases */
/** @var array $codes */
/** @var array $sources */
/** @var array|null $latest */
/** @var array $regionalResults */
?>
<div class="container section">
  <nav class="breadcrumb"><a href="/">Home</a> / <a href="/partiti.php">Partiti</a> / <span aria-current="page"><?= h($party['canonical_name']) ?></span></nav>
  <h1><?= h($party['canonical_name']) ?></h1>
  <?php if (!$party['is_active']): ?><p class="badge">Non più attivo</p><?php endif; ?>
  <p class="text-muted">Anni con dati disponibili: <?= h((string) ($party['first_year'] ?? '—')) ?>–<?= h((string) ($party['last_year'] ?? '—')) ?></p>

  <?php if ($latest): ?>
  <h2>Ultimo anno disponibile: <?= h((string) $latest['declaration_year']) ?></h2>
  <div class="card-grid">
    <div class="card kpi-card"><div class="kpi-label">Scelte valide</div><div class="kpi-value"><?= fmt_int($latest['valid_choices']) ?></div></div>
    <div class="card kpi-card"><div class="kpi-label">Importo</div><div class="kpi-value"><?= fmt_amount($latest['amount']) ?></div></div>
    <div class="card kpi-card"><div class="kpi-label">Importo medio per scelta</div><div class="kpi-value"><?= fmt_amount($latest['avg_amount_per_choice'], 2) ?></div></div>
    <div class="card kpi-card"><div class="kpi-label">Quota scelte</div><div class="kpi-value"><?= fmt_pct($latest['pct_valid_choices']) ?></div></div>
    <div class="card kpi-card"><div class="kpi-label">Quota importo</div><div class="kpi-value"><?= fmt_pct($latest['pct_amount']) ?></div></div>
    <div class="card kpi-card"><div class="kpi-label">Ranking (scelte / importo)</div><div class="kpi-value">#<?= h((string) $latest['rank_choices']) ?> / #<?= h((string) $latest['rank_amount']) ?></div></div>
  </div>
  <?php else: ?>
    <p>Nessun risultato disponibile per questo partito.</p>
  <?php endif; ?>

  <div class="grid-2">
    <div class="chart-card">
      <h3>Serie storica scelte</h3>
      <div class="chart-wrap short"><canvas id="chart-party-choices" role="img" aria-label="Serie storica delle scelte valide"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>Serie storica importo</h3>
      <div class="chart-wrap short"><canvas id="chart-party-amount" role="img" aria-label="Serie storica dell'importo"></canvas></div>
    </div>
  </div>
  <div class="chart-card">
    <h3>Serie storica importo medio per scelta</h3>
    <div class="chart-wrap short"><canvas id="chart-party-avg" role="img" aria-label="Serie storica dell'importo medio per scelta"></canvas></div>
  </div>

  <h2>Tabella annuale completa</h2>
  <div class="table-wrap">
    <table class="data-table">
      <caption>Dati annuali di <?= h($party['canonical_name']) ?></caption>
      <thead>
        <tr>
          <th>Anno</th><th>Scelte</th><th>Quota scelte</th><th>Importo</th><th>Quota importo</th>
          <th>Importo medio</th><th>Rank scelte</th><th>Rank importo</th><th>Var. scelte</th><th>Var. importo</th>
        </tr>
      </thead>
      <tbody>
      <?php foreach (array_reverse($results) as $r): ?>
        <tr>
          <td><?= h((string) $r['declaration_year']) ?></td>
          <td><?= fmt_int($r['valid_choices']) ?></td>
          <td><?= fmt_pct($r['pct_valid_choices']) ?></td>
          <td><?= fmt_amount($r['amount']) ?></td>
          <td><?= fmt_pct($r['pct_amount']) ?></td>
          <td><?= fmt_amount($r['avg_amount_per_choice'], 2) ?></td>
          <td>#<?= h((string) $r['rank_choices']) ?></td>
          <td>#<?= h((string) $r['rank_amount']) ?></td>
          <td><?= $r['choices_delta_pct'] !== null ? fmt_delta((float) $r['choices_delta_pct'], true) : '—' ?></td>
          <td><?= $r['amount_delta_pct'] !== null ? fmt_delta((float) $r['amount_delta_pct'], true) : '—' ?></td>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
  </div>

  <?php if ($regionalResults): ?>
  <h2>Ripartizione regionale delle scelte</h2>
  <p class="text-muted">Numero di scelte valide per regione di residenza del contribuente, per anno di dichiarazione (fonte: Dipartimento delle Finanze). I valori troppo bassi sono oscurati dalla fonte per tutela della riservatezza e sono indicati come "n.d.": le quote percentuali sono calcolate sulla somma delle sole regioni non oscurate e possono quindi non coincidere esattamente con il totale nazionale del partito.</p>
  <div class="filter-bar">
    <div class="field">
      <label for="regional-year-select">Anno di dichiarazione</label>
      <select id="regional-year-select"></select>
    </div>
  </div>
  <div class="chart-card">
    <h3>Scelte valide per regione</h3>
    <div class="chart-wrap tall"><canvas id="chart-party-regional" role="img" aria-label="Scelte valide per regione, anno selezionato"></canvas></div>
  </div>
  <div class="table-wrap">
    <table class="data-table" id="regional-table">
      <caption>Ripartizione regionale, anno selezionato</caption>
      <thead><tr><th>Regione</th><th>Scelte valide</th><th>Quota sulle scelte ripartite</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <?php endif; ?>

  <?php if ($aliases): ?>
  <h2>Denominazioni alternative</h2>
  <ul>
    <?php foreach ($aliases as $a): ?>
      <li><?= h($a['alias_name']) ?> (<?= h((string) $a['year_from']) ?>–<?= h((string) $a['year_to']) ?>)</li>
    <?php endforeach; ?>
  </ul>
  <?php endif; ?>

  <?php if ($sources): ?>
  <h2>Fonti</h2>
  <?php foreach ($sources as $s): ?>
    <div class="box-source">
      <strong><?= h($s['institution']) ?></strong> — <?= h($s['title']) ?>
      <?php if ($s['url']): ?><br><a href="<?= h($s['url']) ?>" target="_blank" rel="noopener"><?= h($s['url']) ?></a><?php endif; ?>
    </div>
  <?php endforeach; ?>
  <?php endif; ?>
</div>

<script>
  window.PARTY_DATA = <?= json_encode(['results' => $results, 'regionalResults' => $regionalResults]) ?>;
</script>
<script>
document.addEventListener('DOMContentLoaded', function () {
  var results = window.PARTY_DATA.results;
  var years = results.map(function (r) { return parseInt(r.declaration_year, 10); });
  Viz.lineChart('chart-party-choices', years, [{ label: 'Scelte valide', data: results.map(function (r) { return parseInt(r.valid_choices, 10); }) }]);
  Viz.lineChart('chart-party-amount', years, [{ label: 'Importo (€)', data: results.map(function (r) { return parseFloat(r.amount); }) }], {
    yTickFormat: function (v) { return '€ ' + Number(v).toLocaleString('it-IT'); },
  });
  Viz.lineChart('chart-party-avg', years, [{ label: 'Importo medio per scelta (€)', data: results.map(function (r) { return r.avg_amount_per_choice !== null ? parseFloat(r.avg_amount_per_choice) : null; }) }], {
    yTickFormat: function (v) { return '€ ' + Number(v).toLocaleString('it-IT'); },
  });

  var regionalRows = window.PARTY_DATA.regionalResults;
  var regionalSelect = document.getElementById('regional-year-select');
  if (regionalRows && regionalRows.length && regionalSelect) {
    var regionalByYear = {};
    regionalRows.forEach(function (r) {
      var y = parseInt(r.declaration_year, 10);
      (regionalByYear[y] = regionalByYear[y] || []).push(r);
    });
    var regionalYears = Object.keys(regionalByYear).map(Number).sort(function (a, b) { return b - a; });
    regionalYears.forEach(function (y) {
      var opt = document.createElement('option');
      opt.value = String(y);
      opt.textContent = String(y);
      regionalSelect.appendChild(opt);
    });

    var regionalChart = null;
    var renderRegional = function (year) {
      var rows = (regionalByYear[year] || []).slice().sort(function (a, b) {
        var av = a.valid_choices !== null ? parseInt(a.valid_choices, 10) : -1;
        var bv = b.valid_choices !== null ? parseInt(b.valid_choices, 10) : -1;
        return bv - av;
      });
      var total = rows.reduce(function (sum, r) {
        return sum + (r.valid_choices !== null ? parseInt(r.valid_choices, 10) : 0);
      }, 0);

      var labels = rows.map(function (r) { return r.region; });
      var data = rows.map(function (r) { return r.valid_choices !== null ? parseInt(r.valid_choices, 10) : null; });

      if (regionalChart) { regionalChart.destroy(); }
      regionalChart = Viz.barChart('chart-party-regional', labels, data, { horizontal: true, label: 'Scelte valide' });

      var tbody = document.querySelector('#regional-table tbody');
      tbody.innerHTML = '';
      rows.forEach(function (r) {
        var tr = document.createElement('tr');
        var tdRegion = document.createElement('td');
        tdRegion.textContent = r.region;
        var tdChoices = document.createElement('td');
        tdChoices.textContent = r.is_suppressed ? 'n.d.' : Number(r.valid_choices).toLocaleString('it-IT');
        var tdShare = document.createElement('td');
        tdShare.textContent = (r.is_suppressed || !total) ? '—' : (r.valid_choices / total * 100).toLocaleString('it-IT', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
        tr.appendChild(tdRegion);
        tr.appendChild(tdChoices);
        tr.appendChild(tdShare);
        tbody.appendChild(tr);
      });
    };

    regionalSelect.addEventListener('change', function () {
      renderRegional(parseInt(regionalSelect.value, 10));
    });
    renderRegional(regionalYears[0]);
  }
});
</script>
