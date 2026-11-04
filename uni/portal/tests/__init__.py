"""Tests des Uni-Portals.

Der Logger von lernen.py (Verträgt-sich-Test) wird vorab ohne Datei eingerichtet, sonst hängt agentkit.log ihn an
das echte logs/uni-lernen.log.
"""

import logging

_logger = logging.getLogger("uni-lernen")
_logger.addHandler(logging.NullHandler())
_logger.propagate = False
