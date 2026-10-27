"""Tests des Agenten uni.

Die Logger der Module werden hier vorab ohne Datei eingerichtet: agentkit.log.hole_logger findet dann schon
einen Handler und hängt keinen an logs/<name>.log an. Sonst landen Testzeilen im echten Log.
"""

import logging

for _name in ("uni", "uni-lernen", "uni-transkript"):
    _logger = logging.getLogger(_name)
    _logger.addHandler(logging.NullHandler())
    _logger.propagate = False
