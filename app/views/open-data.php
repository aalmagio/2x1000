<?php
declare(strict_types=1);
/** @var array $files */
/** @var string|null $generatedAt */
?>
<div class="container section">
  <nav class="breadcrumb"><a href="/">Home</a> / <span aria-current="page">Open data</span></nav>
  <h1>Open data</h1>
  <p class="text-muted">
    Tutti i dati pubblicati su questa piattaforma sono scaricabili in formato CSV e JSON, con licenza aperta.
    <?php if ($generatedAt): ?>Ultimo aggiornamento dataset: <strong><?= h($generatedAt) ?></strong>.<?php endif; ?>
  </p>
  <p class="text-muted">
    I CSV usano il punto e virgola (<code>;</code>) come separatore di campo e i numeri in formato italiano
    (virgola per i decimali, punto per le migliaia: es. <code>1.234,56</code>) — si aprono correttamente in Excel
    in italiano con un doppio click. I JSON riportano invece i numeri in formato standard (punto decimale, senza
    separatore delle migliaia), pensati per essere letti da codice.
  </p>

  <h2>Download</h2>
  <?php if ($files === []): ?>
    <p>Dataset non ancora generati. Eseguire <code>php scripts/export_open_data.php</code>.</p>
  <?php else: ?>
    <ul class="download-list">
      <?php foreach ($files as $f): ?>
        <li>
          <span><?= h($f['label']) ?> <span class="badge"><?= strtoupper(h($f['ext'])) ?></span></span>
          <a class="btn btn-sm" href="/download.php?file=<?= h($f['file']) ?>" download>Scarica</a>
        </li>
      <?php endforeach; ?>
    </ul>
  <?php endif; ?>

  <h2>Dizionario dati</h2>
  <div class="table-wrap">
    <table class="data-table">
      <caption>Principali campi dei dataset</caption>
      <thead><tr><th>Campo</th><th>Significato</th></tr></thead>
      <tbody>
        <tr><td>declaration_year</td><td>Anno in cui viene presentata la dichiarazione dei redditi</td></tr>
        <tr><td>tax_year</td><td>Anno d'imposta a cui si riferisce il reddito dichiarato (di norma declaration_year − 1)</td></tr>
        <tr><td>valid_choices</td><td>Numero di scelte valide espresse a favore del partito</td></tr>
        <tr><td>amount</td><td>Importo in euro assegnato al partito</td></tr>
        <tr><td>pct_valid_choices / pct_amount</td><td>Quota percentuale sul totale delle scelte valide / dell'importo</td></tr>
        <tr><td>avg_amount_per_choice</td><td>Importo medio per scelta: indicatore aggregato, non un reddito medio</td></tr>
        <tr><td>rank_choices / rank_amount / rank_avg_amount</td><td>Posizione in classifica per l'anno, rispettivamente per scelte, importo, importo medio</td></tr>
        <tr><td>region</td><td>Regione di residenza del contribuente, come riportata dalla fonte (dataset ripartizione regionale)</td></tr>
        <tr><td>region_istat_code</td><td>Codice ISTAT a 2 cifre della regione (vuoto per le righe non territoriali, es. "Non residenti", e per le Province Autonome di Trento e Bolzano, pubblicate separatamente dalla fonte)</td></tr>
        <tr><td>is_suppressed</td><td>1 se il dato di quella regione/partito/anno è oscurato dalla fonte per tutela della riservatezza (valid_choices resta vuoto in quel caso, non 0)</td></tr>
      </tbody>
    </table>
  </div>

  <h2>Licenza e riuso</h2>
  <div class="box-method">
    <p>I dataset sono pubblicati con licenza <strong>Creative Commons Attribuzione 4.0 (CC BY 4.0)</strong>.
    È consentito il riuso, anche commerciale, citando la fonte: "Osservatorio ASSIF sul 5, 2 e 8 per mille — 2x1000 Open Data".</p>
    <p>I dati derivano da fonti ufficiali (Ministero dell'Economia e delle Finanze, Agenzia delle Entrate); si veda la pagina <a href="/fonti.php">Fonti</a> per i dettagli.</p>
  </div>

  <h2>Fonti ufficiali</h2>
  <p><a href="/fonti.php">Consulta l'elenco completo delle fonti »</a></p>
</div>
