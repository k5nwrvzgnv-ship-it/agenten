"""Webseiten und Dateien laden, nur von Domains aus einer Allowlist (nur Bordmittel, urllib).

Die Allowlist gibt der Aufrufer an, abruf setzt sie durch: Erlaubt ist ein Host, der gleich einer
Domain ist oder auf ".domain" endet ("ia800.us.archive.org" ja, "evilarchive.org" nein).
Nur https. Jede Weiterleitung wird ebenso geprüft (urllib folgt sonst still).
Grenzen: Zeitlimit, Größe (Standard 30 MB), mindestens 2 s Pause je Host zwischen Anfragen
(gilt innerhalb eines Prozesses, Weiterleitungen zählen für den Zielhost mit).
User-Agent ohne persönliche Daten.

Cache im Ordner des Aufrufers: <sha256 der URL>.bin (Inhalt) und .json (Meta: url, endgueltige_url,
abgerufen, status, content_type, sha256, groesse). Liegt die URL im Cache, wird nicht neu geladen,
außer mit neu=True.

    erg = abruf.laden(url, allowlist=["korpora.org"], cache_dir=Path("data/cache"))
    erg.inhalt (bytes), erg.meta (dict), erg.aus_cache, erg.text() (Zeichensatz aus Content-Type)

Fehler: AbrufFehler mit Text für Jan (Domain nicht erlaubt, Weiterleitung nach außen, kein https,
HTTP-Fehler, zu groß, Zeitüberschreitung, Netzfehler, unbekannter Zeichensatz, Cache beschädigt).
"""

import codecs
import hashlib
import json
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

USER_AGENT = "agentkit-abruf (privat, nicht kommerziell)"
MAX_BYTES = 30 * 1024 * 1024
ZEITLIMIT = 60
PAUSE = 2.0

# Letzte Anfrage je Host (monotone Zeit). In Tests über _uhr und _schlafen ersetzbar.
_zuletzt: dict[str, float] = {}
_uhr = time.monotonic
_schlafen = time.sleep

# Auch "charset=Charset=ISO-8859-1" (korpora.org) und charset="utf-8"
_CHARSET = re.compile(r'charset\s*=\s*(?:charset\s*=\s*)?["\']?([\w.:-]+)', re.IGNORECASE)


class AbrufFehler(Exception):
    pass


def host_erlaubt(host: str, allowlist) -> bool:
    """True, wenn host eine Domain der Allowlist ist oder auf ".domain" endet."""
    host = (host or "").lower().rstrip(".")
    if not host:
        return False
    for domain in allowlist:
        domain = domain.lower().strip().strip(".")
        if domain and (host == domain or host.endswith("." + domain)):
            return True
    return False


def pruefen(url: str, allowlist) -> str:
    """Prüft Schema und Host, gibt den Host zurück. Sonst AbrufFehler."""
    teile = urlsplit(url)
    if teile.scheme.lower() != "https":
        raise AbrufFehler(f"Nur https erlaubt, nicht {teile.scheme or 'ohne Schema'}: {url}")
    host = (teile.hostname or "").lower()
    if not host_erlaubt(host, allowlist):
        raise AbrufFehler(f"Domain nicht erlaubt: {host or '(keine)'} ({url})")
    return host


def zeichensatz(content_type: str | None) -> str:
    """Zeichensatz aus dem Content-Type, ohne Angabe utf-8. Unbekannt: AbrufFehler."""
    treffer = _CHARSET.search(content_type or "")
    name = treffer.group(1) if treffer else "utf-8"
    try:
        return codecs.lookup(name).name
    except LookupError:
        raise AbrufFehler(f"Unbekannter Zeichensatz {name!r} (Content-Type {content_type!r})") from None


def als_text(inhalt: bytes, content_type: str | None) -> str:
    """Bytes als Text im Zeichensatz des Content-Type. Passt er nicht: AbrufFehler."""
    name = zeichensatz(content_type)
    try:
        return inhalt.decode(name)
    except UnicodeDecodeError as e:
        raise AbrufFehler(f"Inhalt passt nicht zum Zeichensatz {name}: {e}") from None


@dataclass
class Ergebnis:
    inhalt: bytes
    meta: dict
    aus_cache: bool

    def text(self) -> str:
        return als_text(self.inhalt, self.meta.get("content_type"))


class _Weiterleitung(urllib.request.HTTPRedirectHandler):
    """Prüft jedes Weiterleitungsziel gegen die Allowlist."""

    def __init__(self, allowlist):
        self.allowlist = list(allowlist)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            pruefen(newurl, self.allowlist)
        except AbrufFehler as e:
            raise AbrufFehler(f"Weiterleitung von {req.full_url} abgelehnt. {e}") from None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def opener(allowlist, *handler):
    """urllib-Opener mit geprüften Weiterleitungen. handler: zusätzliche Handler (Tests)."""
    return urllib.request.build_opener(_Weiterleitung(allowlist), *handler)


def _warten(host: str):
    letzte = _zuletzt.get(host)
    if letzte is not None:
        rest = PAUSE - (_uhr() - letzte)
        if rest > 0:
            _schlafen(rest)
    _zuletzt[host] = _uhr()


def _schluessel(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _aus_cache(cache_dir: Path, url: str) -> Ergebnis | None:
    name = _schluessel(url)
    datei, meta_datei = cache_dir / f"{name}.bin", cache_dir / f"{name}.json"
    if not (datei.exists() and meta_datei.exists()):
        return None
    meta = json.loads(meta_datei.read_text(encoding="utf-8"))
    inhalt = datei.read_bytes()
    if hashlib.sha256(inhalt).hexdigest() != meta.get("sha256") or meta.get("url") != url:
        raise AbrufFehler(f"Cache beschädigt für {url} ({datei}). Mit neu=True neu laden.")
    return Ergebnis(inhalt, meta, True)


def _speichern(cache_dir: Path, url: str, inhalt: bytes, meta: dict):
    cache_dir.mkdir(parents=True, exist_ok=True)
    name = _schluessel(url)
    for endung, daten in ((".bin", inhalt), (".json", json.dumps(meta, ensure_ascii=False, indent=1).encode())):
        tmp = cache_dir / f".{name}{endung}.tmp"
        tmp.write_bytes(daten)
        tmp.replace(cache_dir / f"{name}{endung}")


def laden(url: str, allowlist, cache_dir: Path, neu: bool = False, zeitlimit: float = ZEITLIMIT,
          max_bytes: int = MAX_BYTES, _opener=None) -> Ergebnis:
    """Lädt url (nur https, nur Allowlist) oder nimmt sie aus dem Cache. Fehler: AbrufFehler."""
    host = pruefen(url, allowlist)
    cache_dir = Path(cache_dir)
    if not neu:
        treffer = _aus_cache(cache_dir, url)
        if treffer:
            return treffer

    _warten(host)
    anfrage = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with (_opener or opener(allowlist)).open(anfrage, timeout=zeitlimit) as antwort:
            endgueltig = antwort.geturl()
            pruefen(endgueltig, allowlist)  # doppelt hält besser
            _zuletzt[urlsplit(endgueltig).hostname.lower()] = _uhr()
            laenge = antwort.headers.get("Content-Length")
            if laenge and laenge.isdigit() and int(laenge) > max_bytes:
                raise AbrufFehler(f"Zu groß: {int(laenge)} Bytes, erlaubt {max_bytes} ({url})")
            inhalt = antwort.read(max_bytes + 1)
            if len(inhalt) > max_bytes:
                raise AbrufFehler(f"Zu groß: mehr als {max_bytes} Bytes ({url})")
            status = getattr(antwort, "status", None) or antwort.getcode()
            content_type = antwort.headers.get("Content-Type")
    except urllib.error.HTTPError as e:
        raise AbrufFehler(f"HTTP-Fehler {e.code} ({e.reason}) bei {url}") from None
    except urllib.error.URLError as e:
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            raise AbrufFehler(f"Zeitüberschreitung nach {zeitlimit} s bei {url}") from None
        raise AbrufFehler(f"Netzfehler bei {url}: {e.reason}") from None
    except (TimeoutError, socket.timeout):
        raise AbrufFehler(f"Zeitüberschreitung nach {zeitlimit} s bei {url}") from None
    except OSError as e:
        raise AbrufFehler(f"Netzfehler bei {url}: {e}") from None

    meta = {
        "url": url,
        "endgueltige_url": endgueltig,
        "abgerufen": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "content_type": content_type,
        "sha256": hashlib.sha256(inhalt).hexdigest(),
        "groesse": len(inhalt),
    }
    _speichern(cache_dir, url, inhalt, meta)
    return Ergebnis(inhalt, meta, False)
