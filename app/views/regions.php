<?php
declare(strict_types=1);
/** @var int|null $year */
/** @var array $availableYears */
/** @var array $regions */
?>
<div class="container section">
  <nav class="breadcrumb"><a href="/">Home</a> / <span aria-current="page">Regioni</span></nav>
  <h1>Ripartizione regionale delle scelte</h1>
  <p class="text-muted">Numero di scelte valide per regione di residenza del contribuente, sommate su tutti i partiti, per anno di dichiarazione (fonte: Dipartimento delle Finanze). I valori troppo bassi sono oscurati dalla fonte per tutela della riservatezza: i totali per regione includono solo i valori non oscurati, quindi possono essere leggermente inferiori al dato reale.</p>

  <form class="filter-bar" method="get" action="/regioni.php">
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

  <?php if ($regions === []): ?>
    <p>Nessun dato disponibile per l'anno selezionato.</p>
  <?php else: ?>
  <div class="chart-card" id="map-card" hidden>
    <h3>Mappa delle scelte per regione (<?= h((string) $year) ?>)</h3>
    <p class="text-muted">
      Intensità di colore proporzionale al numero di scelte valide (scala in radice quadrata,
      per mantenere leggibili le regioni piccole). Le due Province Autonome di Trento e Bolzano
      sono sommate sul Trentino-Alto Adige; i contribuenti non residenti non sono rappresentabili
      sulla mappa ma compaiono nella tabella. Clicca una regione per la classifica completa.
    </p>
    <div class="map-wrap">
      <?php require __DIR__ . '/../includes/italy-map.php'; ?>
      <div class="map-legend" id="map-legend"></div>
    </div>
    <p class="text-muted map-credits">Confini regionali: ISTAT, via openpolis/geojson-italy (CC-BY 4.0).</p>
  </div>
  <div class="map-tooltip" id="map-tooltip" role="status" aria-live="polite"></div>

  <div class="chart-card">
    <h3>Scelte valide per regione (<?= h((string) $year) ?>)</h3>
    <div class="chart-wrap tall"><canvas id="chart-regions" role="img" aria-label="Scelte valide totali per regione"></canvas></div>
  </div>

  <div class="table-wrap">
    <table class="data-table">
      <caption>Ripartizione regionale, <?= h((string) $year) ?></caption>
      <thead>
        <tr><th>Regione</th><th>Scelte valide</th><th>Partito più scelto</th><th>Dati oscurati</th><th></th></tr>
      </thead>
      <tbody>
      <?php foreach ($regions as $r): ?>
        <tr>
          <td><?= h($r['region']) ?></td>
          <td><?= fmt_int($r['total_choices']) ?></td>
          <td>
            <?php if ($r['top_party']): ?>
              <a href="/partito.php?slug=<?= h($r['top_party']['slug']) ?>"><?= h($r['top_party']['canonical_name']) ?></a>
            <?php else: ?>—<?php endif; ?>
          </td>
          <td><?= (int) $r['suppressed_count'] > 0 ? fmt_int($r['suppressed_count']) : '—' ?></td>
          <td><a href="/classifiche.php?year=<?= h((string) $year) ?>&amp;region=<?= h(rawurlencode($r['region'])) ?>">Classifica completa »</a></td>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
  </div>
  <?php endif; ?>
</div>

<script>
  window.REGIONS_DATA = <?= json_encode(['regions' => $regions, 'year' => $year]) ?>;
</script>
<script src="/assets/js/regions.js"></script>
