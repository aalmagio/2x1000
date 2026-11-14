(function () {
  'use strict';
  var d = Site.pageData('page-data');
  if (!d || !d.results) return;

  document.addEventListener('DOMContentLoaded', function () {
    var results = d.results;
    var years = results.map(function (r) { return parseInt(r.declaration_year, 10); });
    Viz.lineChart('chart-party-choices', years, [{ label: 'Scelte valide', data: results.map(function (r) { return parseInt(r.valid_choices, 10); }) }]);
    Viz.lineChart('chart-party-amount', years, [{ label: 'Importo (€)', data: results.map(function (r) { return parseFloat(r.amount); }) }], {
      yTickFormat: function (v) { return '€ ' + Number(v).toLocaleString('it-IT'); },
    });
    Viz.lineChart('chart-party-avg', years, [{ label: 'Importo medio per scelta (€)', data: results.map(function (r) { return r.avg_amount_per_choice !== null ? parseFloat(r.avg_amount_per_choice) : null; }) }], {
      yTickFormat: function (v) { return '€ ' + Number(v).toLocaleString('it-IT'); },
    });

    var regionalRows = d.regionalResults;
    var regionalSelect = document.getElementById('regional-year-select');
    if (regionalRows && regionalRows.length && regionalSelect) {
      var regionalByYear = {};
      regionalRows.forEach(function (r) {
        var y = parseInt(r.declaration_year, 10);
        (regionalByYear[y] = regionalByYear[y] || []).push(r);
      });
      var regionalYears = Object.keys(regionalByYear).map(Number).sort(function (a, b) { return b - a; });
      regionalYears.forEach(function (y) {
        var opt = document.createElement('option');
        opt.value = String(y);
        opt.textContent = String(y);
        regionalSelect.appendChild(opt);
      });

      var regionalChart = null;
      var renderRegional = function (year) {
        var rows = (regionalByYear[year] || []).slice().sort(function (a, b) {
          var av = a.valid_choices !== null ? parseInt(a.valid_choices, 10) : -1;
          var bv = b.valid_choices !== null ? parseInt(b.valid_choices, 10) : -1;
          return bv - av;
        });
        var total = rows.reduce(function (sum, r) {
          return sum + (r.valid_choices !== null ? parseInt(r.valid_choices, 10) : 0);
        }, 0);

        var labels = rows.map(function (r) { return r.region; });
        var data = rows.map(function (r) { return r.valid_choices !== null ? parseInt(r.valid_choices, 10) : null; });

        if (regionalChart) { regionalChart.destroy(); }
        regionalChart = Viz.barChart('chart-party-regional', labels, data, { horizontal: true, label: 'Scelte valide' });

        var tbody = document.querySelector('#regional-table tbody');
        tbody.innerHTML = '';
        rows.forEach(function (r) {
          var tr = document.createElement('tr');
          var tdRegion = document.createElement('td');
          tdRegion.textContent = r.region;
          var tdChoices = document.createElement('td');
          tdChoices.textContent = r.is_suppressed ? 'n.d.' : Number(r.valid_choices).toLocaleString('it-IT');
          var tdShare = document.createElement('td');
          tdShare.textContent = (r.is_suppressed || !total) ? '—' : (r.valid_choices / total * 100).toLocaleString('it-IT', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
          tr.appendChild(tdRegion);
          tr.appendChild(tdChoices);
          tr.appendChild(tdShare);
          tbody.appendChild(tr);
        });
      };

      regionalSelect.addEventListener('change', function () {
        renderRegional(parseInt(regionalSelect.value, 10));
      });
      renderRegional(regionalYears[0]);
    }
  });
})();
