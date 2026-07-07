(function () {
  'use strict';
  var d = window.DASHBOARD_DATA;
  if (!d) return;

  document.addEventListener('DOMContentLoaded', function () {
    var years = d.totals.map(function (t) { return parseInt(t.declaration_year, 10); });
    var eur = function (v) { return '€ ' + Number(v).toLocaleString('it-IT'); };

    Viz.lineChart('chart-choices', years, [{ label: 'Scelte valide', data: d.totals.map(function (t) { return parseInt(t.total_valid_choices, 10); }) }]);
    Viz.lineChart('chart-amount', years, [{ label: 'Importo totale (€)', data: d.totals.map(function (t) { return parseFloat(t.total_amount); }) }], { yTickFormat: eur });
    Viz.lineChart('chart-avg', years, [{ label: 'Importo medio per scelta (€)', data: d.totals.map(function (t) { return t.avg_amount_per_choice !== null ? parseFloat(t.avg_amount_per_choice) : null; }) }], { yTickFormat: eur });

    Viz.barChart('chart-top-choices', d.topChoices.map(function (r) { return r.canonical_name; }), d.topChoices.map(function (r) { return parseInt(r.valid_choices, 10); }), { horizontal: true, label: 'Scelte valide' });
    Viz.barChart('chart-top-amount', d.topAmount.map(function (r) { return r.canonical_name; }), d.topAmount.map(function (r) { return parseFloat(r.amount); }), { horizontal: true, label: 'Importo (€)', valueTickFormat: eur });

    Viz.scatterChart('chart-scatter', d.yearResults.map(function (r) {
      return { x: parseInt(r.valid_choices, 10), y: parseFloat(r.amount), label: r.canonical_name };
    }), { xLabel: 'Scelte valide', yLabel: 'Importo (€)' });

    if (d.currentTotal) {
      Viz.barChart('chart-concentration', ['Top 3', 'Top 5', 'Top 10'], [
        parseFloat(d.currentTotal.top_3_amount_share) || 0,
        parseFloat(d.currentTotal.top_5_amount_share) || 0,
        parseFloat(d.currentTotal.top_10_amount_share) || 0,
      ], { label: 'Quota importo (%)', valueTickFormat: function (v) { return v + '%'; } });
    }
  });
})();
