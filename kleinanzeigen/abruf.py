"""Abrufe bei Kleinanzeigen (dünn): Suchseite und Orts-ID. Nur lesend, ohne Konto.

Zwischen zwei Abrufen liegen mindestens PAUSE_S Sekunden (plus Zufall), damit wir nicht auffallen.
"""

import asyncio
import random
import time

import httpx

from seite import BASIS, ort_id_lesen

PAUSE_S = 3.0
KOPF = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/130.0 Safari/537.36"),
    "Accept-Language": "de-DE,de;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}


class AbrufFehler(Exception):
    pass


class Abruf:
    def __init__(self):
        self._client = httpx.AsyncClient(headers=KOPF, timeout=20, follow_redirects=True)
        self._sperre = asyncio.Lock()
        self._zuletzt = 0.0

    async def _holen(self, url: str, **params) -> httpx.Response:
        async with self._sperre:
            warten = self._zuletzt + PAUSE_S + random.uniform(0, 2) - time.monotonic()
            if warten > 0:
                await asyncio.sleep(warten)
            try:
                antwort = await self._client.get(url, params=params or None)
            except httpx.HTTPError as f:
                raise AbrufFehler(f"{type(f).__name__}: {f}") from f
            finally:
                self._zuletzt = time.monotonic()
        if antwort.status_code != 200:
            raise AbrufFehler(f"HTTP {antwort.status_code} bei {url}")
        return antwort

    async def seite(self, url: str) -> str:
        return (await self._holen(url)).text

    async def ort_id(self, plz: str) -> int | None:
        antwort = await self._holen(f"{BASIS}/s-ort-empfehlungen.json", query=plz)
        try:
            return ort_id_lesen(antwort.json(), plz)
        except ValueError as f:
            raise AbrufFehler(f"Ortssuche lieferte kein JSON: {f}") from f

    async def schliessen(self) -> None:
        await self._client.aclose()
