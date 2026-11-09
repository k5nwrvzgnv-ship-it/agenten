"""Netz: liest freie Massagetermine aus der Buchungsschnittstelle von vabali Berlin (Sparkle), nur lesend.

Dieselben Abfragen, die die Buchungsseite vabali.de/berlin/buchung-shop/ im Browser stellt (09.11.2026 geprüft):
getAvailableArtikel (Massagen an einem Tag) und getPossibleAnwendungen (freie Startzeiten einer Massage).
Kein Login, keine Buchung.
"""

import http.cookiejar
import json
import time
import urllib.parse
import urllib.request

BASIS = "https://ecom.vs.sparkleapp.sparkle.plus/ajaxResponder.php?action="
SEITE = "https://www.vabali.de/berlin/buchung-shop/"
PAUSE_SEKUNDEN = 1.0  # zwischen zwei Abfragen, um die Seite nicht zu belasten


class AbfrageFehler(Exception):
    pass


class Abfrage:
    def __init__(self, pause: float = PAUSE_SEKUNDEN):
        self.oeffner = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.pause = pause

    def post(self, aktion: str, daten: dict) -> dict:
        anfrage = urllib.request.Request(
            BASIS + aktion, data=urllib.parse.urlencode(daten).encode(),
            headers={"User-Agent": "Mozilla/5.0 (compatible; Terminpruefer)", "Referer": SEITE,
                     "X-Requested-With": "XMLHttpRequest"})
        try:
            with self.oeffner.open(anfrage, timeout=30) as antwort:
                inhalt = antwort.read()
            ergebnis = json.loads(inhalt)
        except (OSError, ValueError) as f:
            raise AbfrageFehler(f"{aktion}: {f}") from f
        finally:
            time.sleep(self.pause)
        if not isinstance(ergebnis, dict) or ergebnis.get("success") is False:
            raise AbfrageFehler(f"{aktion}: unerwartete Antwort {str(ergebnis)[:200]}")
        return ergebnis

    def artikel(self, datum: str) -> list[dict]:
        ergebnis = self.post("getAvailableArtikel", {"datum": datum})
        if not isinstance(ergebnis.get("artikel"), list):
            raise AbfrageFehler(f"getAvailableArtikel {datum}: kein Feld artikel")
        return ergebnis["artikel"]

    def zeiten(self, datum: str, artikel_id: int) -> dict:
        ergebnis = self.post("getPossibleAnwendungen", {"datum": datum, "Artikel_ID": artikel_id})
        moegliche = ergebnis.get("possibleAnwendungen")
        if isinstance(moegliche, list) and not moegliche:  # PHP schickt leere Zuordnung als []
            return {}
        if not isinstance(moegliche, dict):
            raise AbfrageFehler(f"getPossibleAnwendungen {datum} {artikel_id}: kein Feld possibleAnwendungen")
        return moegliche
