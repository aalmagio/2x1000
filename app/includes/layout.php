<?php
declare(strict_types=1);

/**
 * Renderizza una vista dentro l'header/footer condiviso.
 *
 * @param string $view Percorso assoluto del file vista in app/views/
 * @param array<string,mixed> $data Variabili da rendere disponibili alla vista
 * @param array{charts?:bool,scripts?:list<string>} $assets JavaScript della pagina:
 *        'charts' carica Chart.js e gli helper Viz (solo dove servono: sono
 *        ~200 KB), 'scripts' elenca i file in public/assets/js/ da caricare.
 */
function render_page(
    string $view,
    array $data = [],
    string $pageTitle = '2x1000 Open Data — Partiti politici',
    string $pageDescription = '',
    array $assets = []
): void {
    $pageScripts = ['site.js'];
    if ($assets['charts'] ?? false) {
        $pageScripts[] = 'vendor/chart.umd.min.js';
        $pageScripts[] = 'charts.js';
    }
    foreach ($assets['scripts'] ?? [] as $script) {
        $pageScripts[] = $script;
    }

    extract($data, EXTR_SKIP);
    require __DIR__ . '/header.php';
    require $view;
    require __DIR__ . '/footer.php';
}
