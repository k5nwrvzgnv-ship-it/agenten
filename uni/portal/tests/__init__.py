"""Tests des Uni-Portals.

Die Logger von lernen.py (Verträgt-sich-Test) und auswertung_agent.py werden vorab ohne Datei eingerichtet, sonst
hängt agentkit.log sie an die echten Logdateien.
"""

import logging

for _name in ("uni-lernen", "uni-portal-frage"):
    _logger = logging.getLogger(_name)
    _logger.addHandler(logging.NullHandler())
    _logger.propagate = False
