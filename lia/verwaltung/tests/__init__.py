"""Tests des Agenten verwaltung.

Der Logger wird vorab ohne Datei eingerichtet, damit Testzeilen nicht in logs/verwaltung.log landen.
Die Module liegen im Agent-Ordner, darum kommt er in sys.path.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_logger = logging.getLogger("verwaltung")
_logger.addHandler(logging.NullHandler())
_logger.propagate = False
logging.getLogger("pypdf").setLevel(logging.ERROR)
