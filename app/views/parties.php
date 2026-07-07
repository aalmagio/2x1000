<?php
declare(strict_types=1);
/** @var array $rows */
?>
<div class="container section">
  <nav class="breadcrumb"><a href="/">Home</a> / <span aria-current="page">Partiti</span></nav>
  <h1>Partiti</h1>
  <p class="text-muted">Elenco dei partiti politici con dati sul 2x1000, ordinati alfabeticamente. Usa la ricerca per filtrare.</p>

  <div class="field" style="max-width:320px">
    <label for="party-search">Cerca partito</label>
    <input type="search" id="party-search" placeholder="Digita un nome...">
  </div>

  <div class="table-wrap">
    <table class="data-table" id="parties-table">
      <caption>Elenco partiti e ultimo dato disponibile</caption>
      <thead>
        <tr>
          <th>Partito</th>
          <th>Anni presenza</th>
          <th>Ultimo anno</th>
          <th>Scelte ultimo anno</th>
          <th>Importo ultimo anno</th>
          <th>Importo medio ultimo anno</th>
          <th>Var. scelte vs anno prec.</th>
        </tr>
      </thead>
      <tbody>
      <?php foreach ($rows as $r): ?>
        <tr>
          <td data-label="partito"><a href="/partito.php?slug=<?= h($r['slug']) ?>"><?= h($r['canonical_name']) ?></a></td>
          <td><?= fmt_int($r['years_present']) ?></td>
          <td><?= h((string) ($r['declaration_year'] ?? '—')) ?></td>
          <td><?= fmt_int($r['valid_choices'] ?? null) ?></td>
          <td><?= fmt_amount($r['amount'] ?? null) ?></td>
          <td><?= fmt_amount($r['avg_amount_per_choice'] ?? null, 2) ?></td>
          <td class="<?= isset($r['choices_delta_pct']) && $r['choices_delta_pct'] < 0 ? 'kpi-delta negative' : 'kpi-delta positive' ?>">
            <?= isset($r['choices_delta_pct']) ? fmt_delta((float) $r['choices_delta_pct'], true) : '—' ?>
          </td>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
  </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function () {
  var input = document.getElementById('party-search');
  var rows = document.querySelectorAll('#parties-table tbody tr');
  input.addEventListener('input', function () {
    var q = input.value.trim().toLowerCase();
    rows.forEach(function (row) {
      var name = row.querySelector('td').textContent.toLowerCase();
      row.style.display = name.indexOf(q) !== -1 ? '' : 'none';
    });
  });
});
</script>
