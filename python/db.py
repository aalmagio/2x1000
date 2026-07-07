#!/usr/bin/env python3
"""
db.py — Factory centralizzata per la connessione MySQL/MariaDB del progetto
2x1000. Usa le STESSE variabili d'ambiente (stesso file .env) lette da
app/config/database.php, così la pipeline Python scrive nello stesso database
del sito PHP senza bisogno di una configurazione separata:

  DB_HOST       default: localhost
  DB_PORT       default: 3306
  DB_NAME       obbligatorio
  DB_USER       obbligatorio
  DB_PASS       default: ""
  DB_CHARSET    default: utf8mb4

Uso:
    from common import load_dotenv
    from db import get_connection, db_available

    load_dotenv()
    if not db_available():
        logging.warning("DB non configurato, skip.")
    else:
        conn = get_connection()
        with conn:
            ...
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _db_params(override: "dict | None" = None) -> dict:
    """Restituisce il dict di connessione pymysql basato su env vars."""
    cfg = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", ""),
        "password": os.getenv("DB_PASS", ""),
        "database": os.getenv("DB_NAME", ""),
        "charset": os.getenv("DB_CHARSET", "utf8mb4"),
        "autocommit": False,
    }
    if override:
        cfg.update(override)
    return cfg


def db_available(override: "dict | None" = None) -> bool:
    """
    Restituisce True se pymysql è installato e le credenziali minime
    (DB_USER e DB_NAME) sono configurate.
    """
    try:
        import pymysql  # noqa: F401
    except ImportError:
        return False
    cfg = _db_params(override)
    return bool(cfg["user"] and cfg["database"])


def get_connection(override: "dict | None" = None):
    """
    Apre e restituisce una connessione pymysql (autocommit disattivato:
    chi chiama deve fare conn.commit() esplicitamente, o usare "with conn:").

    Solleva ImportError se pymysql non è installato,
    RuntimeError se le credenziali non sono configurate,
    pymysql.Error in caso di errore di connessione.
    """
    try:
        import pymysql
    except ImportError as exc:
        raise ImportError(
            "pymysql non installato. Installa con: pip install pymysql"
        ) from exc

    cfg = _db_params(override)
    if not cfg["user"] or not cfg["database"]:
        raise RuntimeError(
            "Credenziali DB non configurate. "
            "Imposta DB_USER e DB_NAME in .env (nella root del progetto) "
            "o come variabili d'ambiente."
        )

    return pymysql.connect(**cfg)
