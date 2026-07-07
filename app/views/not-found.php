<?php
declare(strict_types=1);
/** @var string $message */
?>
<div class="container section">
  <h1>Pagina non trovata</h1>
  <p><?= h($message ?? 'La risorsa richiesta non è stata trovata.') ?></p>
  <p><a class="btn" href="/">Torna alla home</a></p>
</div>
