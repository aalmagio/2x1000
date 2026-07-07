(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    var minPrevious = document.getElementById('min_previous');
    if (!minPrevious) return;
    var timer = null;
    minPrevious.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(function () { minPrevious.form.submit(); }, 700);
    });
  });
})();
