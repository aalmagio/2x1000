(function () {
  'use strict';
  var groups = window.COMPARE_DATA;
  if (!groups || groups.length === 0) return;

  document.addEventListener('DOMContentLoaded', function () {
    var yearsSet = {};
    groups.forEach(function (g) { g.years.forEach(function (y) { yearsSet[y.declaration_year] = true; }); });
    var years = Object.keys(yearsSet).map(Number).sort(function (a, b) { return a - b; });

    function seriesFor(field) {
      return groups.map(function (g) {
        var byYear = {};
        g.years.forEach(function (y) { byYear[y.declaration_year] = y[field] !== null ? parseFloat(y[field]) : null; });
        return { label: g.party.canonical_name, data: years.map(function (y) { return byYear[y] !== undefined ? byYear[y] : null; }) };
      });
    }

    var eur = function (v) { return '€ ' + Number(v).toLocaleString('it-IT'); };

    Viz.lineChart('chart-compare-choices', years, seriesFor('valid_choices'));
    Viz.lineChart('chart-compare-amount', years, seriesFor('amount'), { yTickFormat: eur });
    Viz.lineChart('chart-compare-avg', years, seriesFor('avg_amount_per_choice'), { yTickFormat: eur });
  });
})();
