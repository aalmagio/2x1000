<?php
declare(strict_types=1);

/**
 * Calcola gli indicatori derivati (quote, ranking, importo medio, concentrazione)
 * a partire dai dati grezzi presenti in `results` (valid_choices, amount) e
 * aggiorna `results` e `annual_totals`. Non modifica total_taxpayers né
 * number_of_parties_admitted in annual_totals, che sono input esterni.
 *
 * Uso: php scripts/calculate_indicators.php
 */

require_once __DIR__ . '/../app/config/database.php';

$pdo = db();

$years = $pdo->query('SELECT DISTINCT declaration_year FROM results ORDER BY declaration_year ASC')->fetchAll(PDO::FETCH_COLUMN);

foreach ($years as $year) {
    $year = (int) $year;

    $stmt = $pdo->prepare('SELECT id, party_id, valid_choices, amount FROM results WHERE declaration_year = :year');
    $stmt->execute(['year' => $year]);
    $rows = $stmt->fetchAll();

    if ($rows === []) {
        continue;
    }

    $totalChoices = array_sum(array_column($rows, 'valid_choices'));
    $totalAmount = array_sum(array_column($rows, 'amount'));

    $totalsStmt = $pdo->prepare('SELECT total_taxpayers FROM annual_totals WHERE declaration_year = :year');
    $totalsStmt->execute(['year' => $year]);
    $totalTaxpayers = $totalsStmt->fetchColumn();
    $totalTaxpayers = $totalTaxpayers !== false ? (float) $totalTaxpayers : null;

    // Ordinamenti per assegnare i ranking (competition ranking semplice, tie-break su id).
    $byChoices = $rows;
    usort($byChoices, fn($a, $b) => $b['valid_choices'] <=> $a['valid_choices'] ?: $a['id'] <=> $b['id']);
    $byAmount = $rows;
    usort($byAmount, fn($a, $b) => $b['amount'] <=> $a['amount'] ?: $a['id'] <=> $b['id']);
    $byAvg = $rows;
    usort($byAvg, function ($a, $b) {
        $avgA = $a['valid_choices'] > 0 ? $a['amount'] / $a['valid_choices'] : -1;
        $avgB = $b['valid_choices'] > 0 ? $b['amount'] / $b['valid_choices'] : -1;
        return $avgB <=> $avgA ?: $a['id'] <=> $b['id'];
    });

    $rankChoices = array_flip(array_column($byChoices, 'id'));
    foreach ($rankChoices as $id => $idx) { $rankChoices[$id] = $idx + 1; }
    $rankAmount = array_flip(array_column($byAmount, 'id'));
    foreach ($rankAmount as $id => $idx) { $rankAmount[$id] = $idx + 1; }
    $rankAvg = array_flip(array_column($byAvg, 'id'));
    foreach ($rankAvg as $id => $idx) { $rankAvg[$id] = $idx + 1; }

    $update = $pdo->prepare(
        'UPDATE results SET
            pct_total_taxpayers = :pct_total_taxpayers,
            pct_valid_choices = :pct_valid_choices,
            pct_amount = :pct_amount,
            avg_amount_per_choice = :avg_amount_per_choice,
            rank_choices = :rank_choices,
            rank_amount = :rank_amount,
            rank_avg_amount = :rank_avg_amount
         WHERE id = :id'
    );

    $pdo->beginTransaction();
    foreach ($rows as $row) {
        $id = (int) $row['id'];
        $choices = (int) $row['valid_choices'];
        $amount = (float) $row['amount'];

        $update->execute([
            'pct_total_taxpayers' => $totalTaxpayers ? round($choices / $totalTaxpayers * 100, 5) : null,
            'pct_valid_choices' => $totalChoices > 0 ? round($choices / $totalChoices * 100, 5) : null,
            'pct_amount' => $totalAmount > 0 ? round($amount / $totalAmount * 100, 5) : null,
            'avg_amount_per_choice' => $choices > 0 ? round($amount / $choices, 2) : null,
            'rank_choices' => $rankChoices[$id],
            'rank_amount' => $rankAmount[$id],
            'rank_avg_amount' => $rankAvg[$id],
            'id' => $id,
        ]);
    }

    // Concentrazione: quota dell'importo totale dei primi 3/5/10 partiti per importo.
    $amountsDesc = array_column($byAmount, 'amount');
    $shareOfTop = function (int $n) use ($amountsDesc, $totalAmount): ?float {
        if ($totalAmount <= 0) return null;
        return round(array_sum(array_slice($amountsDesc, 0, $n)) / $totalAmount * 100, 5);
    };

    $numberWithChoices = count(array_filter($rows, fn($r) => (int) $r['valid_choices'] > 0));

    $upsertTotals = $pdo->prepare(
        'INSERT INTO annual_totals
            (declaration_year, tax_year, total_valid_choices, total_amount, valid_choice_rate, avg_amount_per_choice,
             number_of_parties_with_choices, top_3_amount_share, top_5_amount_share, top_10_amount_share)
         VALUES (:declaration_year, :tax_year, :total_valid_choices, :total_amount, :valid_choice_rate, :avg_amount_per_choice,
             :number_of_parties_with_choices, :top_3_amount_share, :top_5_amount_share, :top_10_amount_share)
         ON DUPLICATE KEY UPDATE
            total_valid_choices = VALUES(total_valid_choices),
            total_amount = VALUES(total_amount),
            valid_choice_rate = VALUES(valid_choice_rate),
            avg_amount_per_choice = VALUES(avg_amount_per_choice),
            number_of_parties_with_choices = VALUES(number_of_parties_with_choices),
            top_3_amount_share = VALUES(top_3_amount_share),
            top_5_amount_share = VALUES(top_5_amount_share),
            top_10_amount_share = VALUES(top_10_amount_share)'
    );
    $upsertTotals->execute([
        'declaration_year' => $year,
        'tax_year' => $year - 1,
        'total_valid_choices' => $totalChoices,
        'total_amount' => $totalAmount,
        'valid_choice_rate' => $totalTaxpayers ? round($totalChoices / $totalTaxpayers * 100, 5) : null,
        'avg_amount_per_choice' => $totalChoices > 0 ? round($totalAmount / $totalChoices, 2) : null,
        'number_of_parties_with_choices' => $numberWithChoices,
        'top_3_amount_share' => $shareOfTop(3),
        'top_5_amount_share' => $shareOfTop(5),
        'top_10_amount_share' => $shareOfTop(10),
    ]);

    $pdo->commit();
    echo "Anno $year: indicatori calcolati per " . count($rows) . " partiti.\n";
}

echo "Completato.\n";
