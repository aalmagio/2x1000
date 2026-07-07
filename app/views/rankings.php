<?php
declare(strict_types=1);
/** @var int|null $year */
/** @var array $availableYears */
/** @var int $minPrevious */
/** @var array $rankings */
/** @var array $longestPresence */

function ranking_value(array $row, string $col): string
{
    return match ($col) {
        'choices' => fmt_int($row['valid_choices']),
        'amount' => fmt_amount($row['amount']),
        'avg' => fmt_amount($row['avg_amount_per_choice'], 2),
        'growth' => fmt_delta((float) $row['pct_change'], true) . ' (' . fmt_int($row['previous_value']) . ' → ' . fmt_int($row['current_value']) . ')',
        'gap' => fmt_delta((float) $row['amount_vs_choices_share_gap'], true),
        default => '—',
    };
}
?>
<div class="container section">
  <nav class="breadcrumb"><a href="/">Home</a> / <span aria-current="page">Classifiche</span></nav>
  <h1>Classifiche</h1>
  <p class="text-muted">Classifiche annuali dei partiti per scelte, importo, crescita/calo e concentrazione. Le classifiche di variazione percentuale applicano una soglia minima sull'anno precedente per evitare distorsioni su numeri piccoli.</p>

  <form class="filter-bar" method="get" action="/classifiche.php">
    <div class="field">
      <label for="year">Anno di dichiarazione</label>
      <select id="year" name="year" onchange="this.form.submit()">
        <?php foreach ($availableYears as $y): ?>
          <option value="<?= $y ?>" <?= $y === $year ? 'selected' : '' ?>><?= $y ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="field">
      <label for="min_previous">Soglia minima scelte anno precedente</label>
      <input type="number" id="min_previous" name="min_previous" min="0" step="1000" value="<?= h((string) $minPrevious) ?>">
    </div>
    <button class="btn btn-sm" type="submit">Applica</button>
  </form>

  <?php foreach ($rankings as $key => $r): ?>
    <h2><?= h($r['title']) ?> (<?= h((string) $year) ?>)</h2>
    <?php if ($r['rows'] === []): ?>
      <p class="text-muted">Nessun dato disponibile con i filtri correnti.</p>
    <?php else: ?>
    <div class="table-wrap">
      <table class="data-table">
        <caption><?= h($r['title']) ?></caption>
        <thead><tr><th>#</th><th>Partito</th><th>Valore</th></tr></thead>
        <tbody>
        <?php foreach ($r['rows'] as $i => $row): ?>
          <tr>
            <td><span class="badge badge-rank"><?= $i + 1 ?></span></td>
            <td><a href="/partito.php?slug=<?= h($row['slug']) ?>"><?= h($row['canonical_name']) ?></a></td>
            <td><?= ranking_value($row, $r['cols'][0]) ?></td>
          </tr>
        <?php endforeach; ?>
        </tbody>
      </table>
    </div>
    <?php endif; ?>
  <?php endforeach; ?>

  <h2>Presenza storica più lunga</h2>
  <div class="table-wrap">
    <table class="data-table">
      <caption>Partiti con più anni di dati disponibili</caption>
      <thead><tr><th>#</th><th>Partito</th><th>Anni presenti</th><th>Primo anno</th><th>Ultimo anno</th></tr></thead>
      <tbody>
      <?php foreach ($longestPresence as $i => $row): ?>
        <tr>
          <td><span class="badge badge-rank"><?= $i + 1 ?></span></td>
          <td><a href="/partito.php?slug=<?= h($row['slug']) ?>"><?= h($row['canonical_name']) ?></a></td>
          <td><?= fmt_int($row['years_present']) ?></td>
          <td><?= h((string) $row['first_year']) ?></td>
          <td><?= h((string) $row['last_year']) ?></td>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
  </div>
</div>
<script src="/assets/js/rankings.js"></script>
