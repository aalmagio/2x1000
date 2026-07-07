<?php
declare(strict_types=1);

/**
 * Renderizza una vista dentro l'header/footer condiviso.
 *
 * @param string $view Percorso assoluto del file vista in app/views/
 * @param array<string,mixed> $data Variabili da rendere disponibili alla vista
 */
function render_page(string $view, array $data = [], string $pageTitle = '2x1000 Open Data — Partiti politici', string $pageDescription = ''): void
{
    extract($data, EXTR_SKIP);
    require __DIR__ . '/header.php';
    require $view;
    require __DIR__ . '/footer.php';
}
