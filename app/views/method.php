<?php declare(strict_types=1); ?>
<div class="container section">
  <nav class="breadcrumb"><a href="/">Home</a> / <span aria-current="page">Metodo</span></nav>
  <h1>Metodo</h1>

  <div class="box-method">
    <p><strong>Il 2x1000 ai partiti politici non misura il consenso elettorale, il numero di iscritti o le donazioni private.
    Misura la destinazione volontaria di una quota dell'IRPEF espressa dai contribuenti in dichiarazione dei redditi.</strong></p>
  </div>

  <h2>Cosa misura il 2x1000</h2>
  <p>Il 2 per mille IRPEF è una scelta facoltativa che il contribuente può esprimere in dichiarazione dei redditi,
  destinando il 2‰ della propria imposta a un partito politico ammesso al beneficio secondo la normativa vigente
  (legge 21/2016 e successive modifiche). La scelta è espressa anche da chi non deve versare imposta, e non comporta
  alcun costo aggiuntivo per il contribuente.</p>

  <h2>Cosa non misura il 2x1000</h2>
  <ul>
    <li>Non è un sondaggio né un'elezione: non misura il consenso elettorale di un partito.</li>
    <li>Non misura il numero di iscritti o militanti di un partito.</li>
    <li>Non equivale a una donazione privata: è una destinazione di gettito fiscale già dovuto, non una spesa aggiuntiva.</li>
    <li>L'importo medio per scelta non rappresenta il reddito medio di chi effettua la scelta: è un indicatore aggregato
    che dipende dalla distribuzione dei redditi di chi ha scelto quel partito, non un dato individuale.</li>
  </ul>

  <h2>Anno di dichiarazione, anno d'imposta, anno di pubblicazione</h2>
  <div class="table-wrap">
    <table class="data-table">
      <caption>Le tre dimensioni temporali del dato</caption>
      <thead><tr><th>Dimensione</th><th>Significato</th></tr></thead>
      <tbody>
        <tr><td>Anno d'imposta (tax_year)</td><td>L'anno a cui si riferisce il reddito dichiarato (es. redditi 2023)</td></tr>
        <tr><td>Anno di dichiarazione (declaration_year)</td><td>L'anno in cui viene presentata la dichiarazione relativa a quel reddito (di norma l'anno successivo, es. dichiarazione 2024 per redditi 2023)</td></tr>
        <tr><td>Anno di pubblicazione</td><td>L'anno in cui il Ministero dell'Economia e delle Finanze pubblica i risultati definitivi, generalmente con uno o più anni di ritardo rispetto alla dichiarazione</td></tr>
      </tbody>
    </table>
  </div>
  <p>Questa piattaforma indicizza i dati per <em>anno di dichiarazione</em>, riportando sempre anche l'anno d'imposta corrispondente.</p>

  <h2>Fonti utilizzate</h2>
  <ul>
    <li>Ministero dell'Economia e delle Finanze (MEF) — Dipartimento delle Finanze: risultati annuali del 2x1000 ai partiti politici.</li>
    <li>Agenzia delle Entrate: elenco dei partiti ammessi e codici da indicare in dichiarazione per ciascun anno.</li>
    <li>Comunicati MEF: fonti di contesto e validazione incrociata dei dati.</li>
  </ul>
  <p>L'elenco puntuale delle fonti effettivamente utilizzate è in <a href="/fonti.php">Fonti</a>.</p>

  <h2>Normalizzazioni applicate</h2>
  <ul>
    <li>Unificazione delle denominazioni dei partiti nel tempo tramite un'anagrafica di alias (cambi di nome, sigle, fusioni), per consentire confronti storici corretti.</li>
    <li>Uniformità dei formati numerici (separatori decimali, valute) tra le fonti originarie, spesso eterogenee.</li>
    <li>Associazione esplicita di ogni dato alla fonte e alla data di download, per garantire tracciabilità e riproducibilità.</li>
  </ul>

  <h2>Calcolo degli indicatori</h2>
  <p>Gli indicatori derivati (quote percentuali, ranking, importo medio per scelta, variazioni anno su anno, concentrazione
  dell'importo nei primi 3/5/10 partiti) sono calcolati automaticamente a partire dai dati grezzi (scelte valide e importo)
  tramite lo script <code>scripts/calculate_indicators.php</code>, così da garantire coerenza e riproducibilità dei calcoli
  su tutta la serie storica. Il codice sorgente di questi calcoli è pubblico nel repository del progetto.</p>

  <h2>Limiti interpretativi</h2>
  <ul>
    <li>I dati riflettono le scelte dei contribuenti che presentano dichiarazione dei redditi (o modello 730/Redditi con
    riquadro compilato): non rappresentano l'intera popolazione elettorale.</li>
    <li>Le variazioni anno su anno possono riflettere cambiamenti normativi (es. nuove ammissioni, esclusioni,
    variazioni di soglia) oltre che variazioni nelle scelte dei contribuenti.</li>
    <li>Il confronto tra partiti con denominazioni cambiate nel tempo richiede cautela: si veda l'anagrafica alias
    per la storia di ciascun soggetto.</li>
    <li>Le classifiche di crescita/calo percentuale applicano una soglia minima sul valore dell'anno precedente,
    configurabile, per evitare che variazioni percentuali enormi su numeri piccoli distorcano la lettura.</li>
  </ul>
</div>
