"""Rende importabili i moduli della pipeline (extract, common, ...) dai test,
senza richiedere un'installazione come package: aggiunge python/ al path."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
