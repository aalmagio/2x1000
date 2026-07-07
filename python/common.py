#!/usr/bin/env python3
"""
common.py — Utilità condivise per la pipeline Python di acquisizione dati
2x1000 (analoga a quella del progetto 5x1000).

Centralizza:
  - load_dotenv()   : carica .env dalla root del progetto (stesso file usato dal sito PHP)
  - load_config()   : carica python/config.yaml
  - get_logger()    : configura logging su file + console
  - ask_yes_no()    : prompt interattivo si/no
  - slugify()       : genera slug canonici (stessa regola di app/includes/helpers.php)
"""

from __future__ import annotations

import datetime
import logging
import os
import re
import sys
from pathlib import Path

# Root del repository (una cartella sopra python/), dove vivono .env, data/, scripts/.
REPO_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(root_dir: "str | Path | None" = None) -> None:
    """
    Carica variabili d'ambiente da <root_dir>/.env (default: REPO_ROOT).

    È lo stesso file .env usato da app/config/database.php: la pipeline Python
    scrive nello stesso database del sito PHP, quindi condivide le credenziali
    DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASS/DB_CHARSET.
    Le variabili già presenti in os.environ non vengono sovrascritte.
    """
    root_dir = Path(root_dir) if root_dir else REPO_ROOT
    env_path = root_dir / ".env"
    if not env_path.is_file():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:]
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def load_config(root_dir: "str | Path | None" = None) -> dict:
    """
    Carica python/config.yaml. Restituisce un dict vuoto se il file non esiste
    o PyYAML non è installato (la pipeline funziona comunque con i default).
    """
    root_dir = Path(root_dir) if root_dir else Path(__file__).resolve().parent
    config_path = root_dir / "config.yaml"
    if not config_path.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        logging.warning(
            "PyYAML non installato: config.yaml ignorato. "
            "Installa con: pip install pyyaml"
        )
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logging.warning(f"Errore nel leggere config.yaml: {e}")
        return {}


def get_logger(module_name: str, root_dir: "str | Path | None" = None) -> "tuple[logging.Logger, str]":
    """
    Configura il root logger (file + console) e restituisce (logger, log_file_path).

    Il file di log viene creato in <root_dir>/python/log/<module_name>_YYYYMMDD_HHMMSS.log.
    Se basicConfig è già stato chiamato (root logger ha handler), non riconfigura
    ma restituisce comunque il logger con il nome indicato.
    """
    base_dir = Path(root_dir) if root_dir else Path(__file__).resolve().parent
    log_dir = base_dir / "log"
    log_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{module_name}_{stamp}.log"

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )
        logging.getLogger(module_name).info(f"Log: {log_file}")

    return logging.getLogger(module_name), str(log_file)


def ask_yes_no(prompt: str, default: str = "s") -> bool:
    """Chiede una conferma si/no. Restituisce True per sì, False per no."""
    suffix = " [S/n]: " if default == "s" else " [s/N]: "
    while True:
        answer = input(prompt + suffix).strip().lower()
        if answer == "":
            return default == "s"
        if answer in ("s", "si", "sì", "y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Rispondi s o n.")


# Stessa tabella di app/includes/helpers.php::slugify(): i due lati (Python e
# PHP) devono restare identici, perché entrambi scrivono lo slug univoco della
# stessa tabella `parties`. Senza normalizzare gli accenti, lo stesso partito
# scritto come "Sudtiroler" in una fonte e "Südtiroler" in un'altra genera due
# slug diversi e quindi due righe duplicate.
_TRANSLITERATION = {
    "à": "a", "á": "a", "â": "a", "ã": "a", "ä": "a", "å": "a",
    "è": "e", "é": "e", "ê": "e", "ë": "e",
    "ì": "i", "í": "i", "î": "i", "ï": "i",
    "ò": "o", "ó": "o", "ô": "o", "õ": "o", "ö": "o",
    "ù": "u", "ú": "u", "û": "u", "ü": "u",
    "ý": "y", "ÿ": "y", "ñ": "n", "ç": "c",
}


def slugify(text: str) -> str:
    """
    Genera uno slug canonico da un nome di partito.
    Stessa regola di app/includes/helpers.php::slugify(), per garantire che
    gli slug generati da Python coincidano con quelli usati dal sito PHP.
    """
    text = text.strip().lower()
    text = "".join(_TRANSLITERATION.get(c, c) for c in text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
