/**
 * Comportamenti comuni a tutte le pagine: menu mobile, invio automatico dei
 * filtri, ricerca nell'elenco partiti, lettura dei blocchi dati JSON.
 * Caricato con "defer": il DOM è già pronto quando viene eseguito.
 */
(function (global) {
  'use strict';

  /** Legge un blocco <script type="application/json" id="..."> generato dal server. */
  function pageData(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  global.Site = { pageData: pageData };

  // Menu mobile
  var toggle = document.querySelector('.nav-toggle');
  var list = document.getElementById('main-nav-list');
  if (toggle && list) {
    toggle.addEventListener('click', function () {
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      list.classList.toggle('open');
    });
  }

  // Select dei filtri: invia il form al cambio valore
  document.querySelectorAll('select[data-autosubmit]').forEach(function (select) {
    select.addEventListener('change', function () {
      if (select.form) select.form.submit();
    });
  });

  // Ricerca nell'elenco partiti
  var search = document.getElementById('party-search');
  if (search) {
    var rows = document.querySelectorAll('#parties-table tbody tr');
    search.addEventListener('input', function () {
      var q = search.value.trim().toLowerCase();
      rows.forEach(function (row) {
        var name = row.querySelector('td').textContent.toLowerCase();
        row.hidden = name.indexOf(q) === -1;
      });
    });
  }
})(window);
