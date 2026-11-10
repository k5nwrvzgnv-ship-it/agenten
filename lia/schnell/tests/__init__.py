"""Tests des Agenten schnell.

Der Logger wird hier vorab ohne Datei eingerichtet: agentkit.log.hole_logger findet dann schon einen Handler und
hängt keinen an logs/schnell.log an. Sonst landen Testzeilen im echten Log.
"""

import logging

_logger = logging.getLogger("schnell")
_logger.addHandler(logging.NullHandler())
_logger.propagate = False
