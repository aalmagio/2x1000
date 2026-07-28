"""Golden test di parità tra le due implementazioni di slugify().

python/common.py::slugify() e app/includes/helpers.php::slugify() scrivono
entrambe lo slug univoco della stessa tabella `parties`: se divergono anche
per un solo carattere, lo stesso partito importato dai due lati genera due
righe duplicate in anagrafica, in modo del tutto silenzioso. Questo test
esegue entrambe le implementazioni sugli stessi nomi (reali e casi limite)
e pretende output identico.

Richiede il binario `php` nel PATH (in CI è garantito); in locale, se PHP
non è installato, il test di parità viene saltato ma restano i controlli
sull'implementazione Python.
"""

import json
import shutil
import subprocess

import pytest

from common import REPO_ROOT, slugify

# Nomi reali dalle fonti MEF/AdE più casi limite: accenti, maiuscole
# multi-byte, apostrofi, trattini tipografici, spazi multipli, sigle.
GOLDEN_NAMES = [
    "Partito Democratico",
    "Fratelli d'Italia - Alleanza Nazionale",
    "Movimento 5 Stelle",
    "PIÙ EUROPA",
    "Südtiroler Volkspartei",
    "Sudtiroler Volkspartei",
    "Lega Nord per l'Indipendenza della Padania",
    "Lega per Salvini Premier",
    "Sinistra Ecologia Libertà (SEL)",
    "L'Altra Europa con Tsipras",
    "Partito Autonomista Trentino Tirolese – P.A.T.T.",
    "Union Valdôtaine",
    "ÈVIVA",
    "  Nome   con    spazi  multipli  ",
    "Partito, con; punteggiatura: varia!",
    "Çà è già ûn tèst àccentato",
    "UDC - Unione di Centro",
    "NOI CON L'ITALIA",
    "+Europa",
    "Articolo 1 - Movimento Democratico e Progressista",
]


def php_slugify(names: "list[str]") -> "list[str]":
    """Esegue slugify() PHP (helpers.php) sugli stessi nomi, via php -r."""
    script = (
        'require $argv[1];'
        '$names = json_decode(stream_get_contents(STDIN), true);'
        'echo json_encode(array_map("slugify", $names));'
    )
    proc = subprocess.run(
        ["php", "-r", script, str(REPO_ROOT / "app" / "includes" / "helpers.php")],
        input=json.dumps(GOLDEN_NAMES),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"PHP fallito: {proc.stderr}"
    return json.loads(proc.stdout)


@pytest.mark.skipif(shutil.which("php") is None, reason="binario php non disponibile")
def test_python_and_php_slugify_are_identical():
    python_slugs = [slugify(n) for n in GOLDEN_NAMES]
    php_slugs = php_slugify(GOLDEN_NAMES)
    mismatches = [
        {"name": name, "python": py, "php": ph}
        for name, py, ph in zip(GOLDEN_NAMES, python_slugs, php_slugs)
        if py != ph
    ]
    assert mismatches == [], (
        "slugify() Python e PHP divergono — rischio di partiti duplicati "
        f"in anagrafica: {json.dumps(mismatches, ensure_ascii=False, indent=2)}"
    )


# Comportamenti fissati dell'implementazione Python (valgono anche come
# documentazione del contratto che il lato PHP deve rispettare).

@pytest.mark.parametrize("name, expected", [
    ("Partito Democratico", "partito-democratico"),
    ("Südtiroler Volkspartei", "sudtiroler-volkspartei"),
    ("Sudtiroler Volkspartei", "sudtiroler-volkspartei"),  # con/senza umlaut: stesso slug
    ("PIÙ EUROPA", "piu-europa"),
    ("L'Altra Europa con Tsipras", "l-altra-europa-con-tsipras"),
    ("  Nome   con    spazi  multipli  ", "nome-con-spazi-multipli"),
    ("+Europa", "europa"),
])
def test_python_slugify_golden(name, expected):
    assert slugify(name) == expected
