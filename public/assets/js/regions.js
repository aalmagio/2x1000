(function () {
  'use strict';
  var d = window.REGIONS_DATA;
  if (!d || !d.regions || !d.regions.length) return;

  document.addEventListener('DOMContentLoaded', function () {
    var rows = d.regions.slice().sort(function (a, b) {
      return parseInt(b.total_choices, 10) - parseInt(a.total_choices, 10);
    });
    Viz.barChart(
      'chart-regions',
      rows.map(function (r) { return r.region; }),
      rows.map(function (r) { return parseInt(r.total_choices, 10); }),
      { horizontal: true, label: 'Scelte valide' }
    );
  });
})();
