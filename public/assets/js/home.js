(function () {
  'use strict';
  var d = Site.pageData('page-data');
  if (!d) return;

  Viz.lineChart('chart-home-choices', d.years, [{ label: 'Scelte valide', data: d.choices }]);
  Viz.lineChart('chart-home-amount', d.years, [{ label: 'Importo totale (€)', data: d.amounts }], {
    yTickFormat: function (v) { return '€ ' + Number(v).toLocaleString('it-IT'); },
  });
})();
