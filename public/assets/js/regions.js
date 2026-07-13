(function () {
  'use strict';
  var d = window.REGIONS_DATA;
  if (!d || !d.regions || !d.regions.length) return;

  function esc(text) {
    var el = document.createElement('span');
    el.textContent = String(text);
    return el.innerHTML;
  }

  function fmt(n) {
    return Number(n).toLocaleString('it-IT');
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Grafico a barre (tutte le righe, comprese quelle non mappabili
    // come "Non residenti")
    var rows = d.regions.slice().sort(function (a, b) {
      return parseInt(b.total_choices, 10) - parseInt(a.total_choices, 10);
    });
    Viz.barChart(
      'chart-regions',
      rows.map(function (r) { return r.region; }),
      rows.map(function (r) { return parseInt(r.total_choices, 10); }),
      { horizontal: true, label: 'Scelte valide' }
    );

    // ------------------------------------------------------------------
    // Mappa coropletica: aggrega le righe per map_code (le due Province
    // Autonome confluiscono sul Trentino-Alto Adige, '04') e colora i
    // path dell'SVG inline (app/includes/italy-map.php).
    // ------------------------------------------------------------------
    var byMapCode = {};
    var hasMapData = false;
    d.regions.forEach(function (r) {
      if (!r.map_code) return; // non mappabile ("Non residenti") o DB non migrato
      hasMapData = true;
      var e = byMapCode[r.map_code] = byMapCode[r.map_code] || { total: 0, suppressed: 0, rows: [] };
      e.total += parseInt(r.total_choices, 10) || 0;
      e.suppressed += parseInt(r.suppressed_count, 10) || 0;
      e.rows.push(r);
    });

    var card = document.getElementById('map-card');
    if (!card || !hasMapData) return; // resta nascosta: barre e tabella sono il fallback
    card.hidden = false;

    var max = 0;
    Object.keys(byMapCode).forEach(function (k) { max = Math.max(max, byMapCode[k].total); });

    // Scala sequenziale dal tenue al rosso scuro di marca, in radice
    // quadrata: i valori regionali sono molto sbilanciati (Lombardia >>
    // Molise) e una scala lineare renderebbe quasi bianche tutte le
    // regioni piccole.
    function fillColor(value) {
      var t = max > 0 ? Math.sqrt(value / max) : 0;
      var from = [255, 227, 227]; // --color-primary-light
      var to = [163, 0, 0];       // --color-primary-dark
      var c = from.map(function (f, i) { return Math.round(f + (to[i] - f) * t); });
      return 'rgb(' + c.join(',') + ')';
    }

    var tooltip = document.getElementById('map-tooltip');

    function showTooltip(html, ev) {
      if (!tooltip) return;
      tooltip.innerHTML = html;
      tooltip.style.display = 'block';
      var x = ev.clientX + 14;
      var y = ev.clientY + 14;
      // non far uscire il tooltip dal viewport
      var rect = tooltip.getBoundingClientRect();
      if (x + rect.width > window.innerWidth - 8) x = ev.clientX - rect.width - 14;
      if (y + rect.height > window.innerHeight - 8) y = ev.clientY - rect.height - 14;
      tooltip.style.left = x + 'px';
      tooltip.style.top = y + 'px';
    }

    function hideTooltip() {
      if (tooltip) tooltip.style.display = 'none';
    }

    document.querySelectorAll('#italy-map .map-region').forEach(function (path) {
      var code = path.getAttribute('data-istat');
      var name = path.getAttribute('data-name');
      var entry = byMapCode[code];
      if (!entry) {
        path.setAttribute('aria-label', name + ': dato non disponibile');
        return;
      }

      path.style.fill = fillColor(entry.total);
      path.classList.add('has-data');
      path.setAttribute('aria-label', name + ': ' + fmt(entry.total) + ' scelte valide');

      var html = '<strong>' + esc(name) + '</strong>';
      if (entry.rows.length === 1) {
        html += '<br>' + fmt(entry.total) + ' scelte valide';
      } else {
        entry.rows.forEach(function (r) {
          html += '<br>' + esc(r.region) + ': ' + fmt(r.total_choices);
        });
        html += '<br>Totale: ' + fmt(entry.total) + ' scelte valide';
      }
      if (entry.suppressed > 0) {
        html += '<br><em>' + fmt(entry.suppressed) + ' dati oscurati per riservatezza</em>';
      }

      path.addEventListener('mousemove', function (ev) { showTooltip(html, ev); });
      path.addEventListener('mouseleave', hideTooltip);

      // Click → classifica regionale, solo quando la regione della mappa
      // corrisponde a una singola riga di fonte (per il Trentino-Alto
      // Adige le classifiche restano raggiungibili dalla tabella, una per
      // Provincia Autonoma).
      if (entry.rows.length === 1) {
        var href = '/classifiche.php?year=' + encodeURIComponent(d.year) +
                   '&region=' + encodeURIComponent(entry.rows[0].region);
        path.setAttribute('tabindex', '0');
        path.setAttribute('role', 'link');
        path.addEventListener('click', function () { window.location.href = href; });
        path.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') {
            ev.preventDefault();
            window.location.href = href;
          }
        });
      }
    });

    var legend = document.getElementById('map-legend');
    if (legend && max > 0) {
      legend.innerHTML =
        '<span>0</span>' +
        '<span class="map-legend-bar" aria-hidden="true"></span>' +
        '<span>' + fmt(max) + ' scelte</span>';
    }
  });
})();
