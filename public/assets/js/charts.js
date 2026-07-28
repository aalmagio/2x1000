/**
 * Helper di rendering per Chart.js, con palette categoriale validata
 * (ordine fisso, mai ciclato arbitrariamente) e stile istituzionale sobrio.
 */
(function (global) {
  'use strict';

  // Il sito è dichiaratamente solo-chiaro (main.css: color-scheme: light,
  // nessun tema scuro): i grafici usano sempre la palette chiara. Seguire
  // prefers-color-scheme qui — come accadeva in passato — produceva assi ed
  // etichette grigio chiaro su pagina bianca per gli utenti con il sistema
  // operativo in tema scuro.
  var PALETTE = ['#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834'];

  function seriesColor(index) {
    return PALETTE[index % PALETTE.length];
  }

  function chromeColor() {
    return '#52514e';
  }

  function gridColor() {
    return '#e1e0d9';
  }

  Chart.defaults.font.family = 'inherit';
  Chart.defaults.color = chromeColor();
  Chart.defaults.borderColor = gridColor();

  /** Grafico a linee multi-serie nel tempo (una linea per partito o per metrica). */
  function lineChart(canvasId, labels, series, opts) {
    opts = opts || {};
    var el = document.getElementById(canvasId);
    if (!el) return null;
    var datasets = series.map(function (s, i) {
      var color = s.color || seriesColor(i);
      return {
        label: s.label,
        data: s.data,
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        tension: 0.15,
        spanGaps: true,
      };
    });
    return new Chart(el, {
      type: 'line',
      data: { labels: labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: datasets.length > 1, labels: { boxWidth: 12 } },
          tooltip: {
            callbacks: opts.tooltipCallbacks || {},
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { callback: opts.yTickFormat || undefined },
            grid: { color: gridColor() },
          },
          x: { grid: { display: false } },
        },
      },
    });
  }

  /** Grafico a barre orizzontali o verticali (classifiche, top10). */
  function barChart(canvasId, labels, data, opts) {
    opts = opts || {};
    var el = document.getElementById(canvasId);
    if (!el) return null;
    return new Chart(el, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: opts.label || '',
          data: data,
          backgroundColor: opts.colors || seriesColor(0),
          borderRadius: 4,
          maxBarThickness: 34,
        }],
      },
      options: {
        indexAxis: opts.horizontal ? 'y' : 'x',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: opts.tooltipCallbacks || {} },
        },
        scales: opts.horizontal
          ? {
              x: { beginAtZero: true, ticks: { callback: opts.valueTickFormat }, grid: { color: gridColor() } },
              y: { grid: { display: false } },
            }
          : {
              x: { grid: { display: false } },
              y: { beginAtZero: true, ticks: { callback: opts.valueTickFormat }, grid: { color: gridColor() } },
            },
      },
    });
  }

  /** Scatter: una bolla per partito, x = scelte, y = importo. */
  function scatterChart(canvasId, points, opts) {
    opts = opts || {};
    var el = document.getElementById(canvasId);
    if (!el) return null;
    return new Chart(el, {
      type: 'scatter',
      data: {
        datasets: [{
          label: opts.label || 'Partiti',
          data: points,
          backgroundColor: seriesColor(0),
          pointRadius: 6,
          pointHoverRadius: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var p = ctx.raw;
                return (p.label || '') + ': ' + (opts.xLabel || 'x') + ' ' + p.x.toLocaleString('it-IT') + ' · ' + (opts.yLabel || 'y') + ' € ' + p.y.toLocaleString('it-IT');
              },
            },
          },
        },
        scales: {
          x: { title: { display: true, text: opts.xLabel || '' }, grid: { color: gridColor() } },
          y: { title: { display: true, text: opts.yLabel || '' }, grid: { color: gridColor() } },
        },
      },
    });
  }

  global.Viz = {
    lineChart: lineChart,
    barChart: barChart,
    scatterChart: scatterChart,
    seriesColor: seriesColor,
  };

  document.addEventListener('DOMContentLoaded', function () {
    var toggle = document.querySelector('.nav-toggle');
    var list = document.getElementById('main-nav-list');
    if (toggle && list) {
      toggle.addEventListener('click', function () {
        var expanded = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', String(!expanded));
        list.classList.toggle('open');
      });
    }
  });
})(window);
