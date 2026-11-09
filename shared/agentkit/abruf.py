"""Webseiten und Dateien laden, nur von Domains aus einer Allowlist (nur Bordmittel, urllib).

Die Allowlist gibt der Aufrufer an, abruf setzt sie durch: Erlaubt ist ein Host, der gleich einer
Domain ist oder auf ".domain" endet ("ia800.us.archive.org" ja, "evilarchive.org" nein).
Nur https. Jede Weiterleitung wird ebenso geprüft (urllib folgt sonst still).
Grenzen: Zeitlimit, Größe (Standard 30 MB), mindestens 2 s Pause je Host zwischen Anfragen
(gilt innerhalb eines Prozesses, Weiterleitungen zählen für den Zielhost mit).
User-Agent ohne persönliche Daten.

Cache im Ordner des Aufrufers: <Schlüssel>.bin (Inhalt) und .json (Meta: url, methode, endgueltige_url,
abgerufen, status, content_type, sha256, groesse, bei Daten auch daten_sha256). Liegt die Anfrage im Cache,
wird nicht neu geladen, außer mit neu=True.

    erg = abruf.laden(url, allowlist=["korpora.org"], cache_dir=Path("data/cache"))
    erg.inhalt (bytes), erg.meta (dict), erg.aus_cache, erg.text() (Zeichensatz aus Content-Type)

POST mit Körper und eigene Header (APIs mit Schlüssel):

    erg = abruf.laden(url, allowlist, cache_dir, methode="POST", daten=json.dumps(abfrage).encode(),
                      header={"Content-Type": "application/json", "X-API-Key": schluessel})

Schlüssel: bei GET ohne Daten sha256 der URL (wie bisher), sonst sha256 aus Methode, URL und Daten.
Header gehen NIE in Schlüssel, Meta, Cache oder Fehlertexte (dort stehen API-Schlüssel). Eine Anfrage, die
sich nur in Headern unterscheidet, trifft also denselben Cache-Eintrag. Weiterleitungen nehmen die Header mit,
aber nur zu Hosts der Allowlist.

HTML als reiner Text (für agentkit.wortlaut.steht_in): html_zu_text(html) bzw. erg.text_ohne_html().
Ohne script, style, template; Titel, og:title, og:description und description stehen oben im Text.

Fehler: AbrufFehler mit Text für Jan (Domain nicht erlaubt, Weiterleitung nach außen, kein https,
HTTP-Fehler, zu groß, Zeitüberschreitung, Netzfehler, unbekannter Zeichensatz, Cache beschädigt).
"""

import codecs
import hashlib
import html.parser
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

    def text_ohne_html(self) -> str:
        return html_zu_text(self.text())


_UNSICHTBAR = {"script", "style", "template", "noscript", "svg"}
_BLOCK = {"p", "div", "br", "li", "ul", "ol", "tr", "td", "th", "table", "h1", "h2", "h3", "h4", "h5", "h6",
          "section", "article", "header", "footer", "nav", "main", "aside", "blockquote", "pre", "dd", "dt",
          "dl", "figure", "figcaption", "hr", "title", "body", "form", "label", "option"}
_META = ("og:title", "og:description", "description")


class _Textleser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.teile, self.meta, self.titel = [], {}, []
        self.verborgen = 0
        self.im_titel = False

    def handle_starttag(self, tag, attrs):
        if tag in _UNSICHTBAR:
            self.verborgen += 1
        elif tag == "title":
            self.im_titel = True
        elif tag == "meta":
            a = {k.lower(): (v or "") for k, v in attrs}
            name = (a.get("property") or a.get("name") or "").lower()
            if name in _META and a.get("content", "").strip():
                self.meta.setdefault(name, a["content"].strip())
        if tag in _BLOCK:
            self.teile.append("\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag in _UNSICHTBAR:
            self.verborgen -= 1

    def handle_endtag(self, tag):
        if tag in _UNSICHTBAR:
            self.verborgen = max(0, self.verborgen - 1)
        elif tag == "title":
            self.im_titel = False
        if tag in _BLOCK:
            self.teile.append("\n")

    def handle_data(self, data):
        if self.verborgen:
            return
        if self.im_titel:
            self.titel.append(data)
        else:
            self.teile.append(data)


def html_zu_text(quelltext: str) -> str:
    """HTML als reiner Text: ohne Tags, script und style, Zeichen-Entities aufgelöst, eine Zeile je Block.

    Oben stehen Titel, og:title, og:description und description (bei YouTube steht sonst kaum etwas im HTML).
    """
    leser = _Textleser()
    leser.feed(quelltext)
    leser.close()
    kopf = [" ".join("".join(leser.titel).split())] + [leser.meta.get(n, "") for n in _META]
    zeilen = [" ".join(z.split()) for z in "".join(leser.teile).splitlines()]
    gesehen, ergebnis = set(), []
    for z in kopf:  # gleiche Angaben (Titel = og:title) nur einmal
        if z and z not in gesehen:
            gesehen.add(z)
            ergebnis.append(z)
    return "\n".join(ergebnis + [z for z in zeilen if z])


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


METHODEN = ("GET", "POST")


def _schluessel(url: str, methode: str = "GET", daten: bytes | None = None) -> str:
    """GET ohne Daten: sha256 der URL (alte Cache-Einträge bleiben gültig). Sonst aus Methode, URL und Daten.

    Header gehören absichtlich nicht dazu: dort stehen API-Schlüssel."""
    if methode == "GET" and daten is None:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()
    h = hashlib.sha256()
    for teil in (methode.encode(), url.encode("utf-8"), b"" if daten is None else daten):
        h.update(len(teil).to_bytes(8, "big"))  # Längen davor: keine Verwechslung an den Grenzen
        h.update(teil)
    return h.hexdigest()


def _daten_sha256(daten: bytes | None) -> str | None:
    return None if daten is None else hashlib.sha256(daten).hexdigest()


def _aus_cache(cache_dir: Path, url: str, methode: str = "GET", daten: bytes | None = None) -> Ergebnis | None:
    name = _schluessel(url, methode, daten)
    datei, meta_datei = cache_dir / f"{name}.bin", cache_dir / f"{name}.json"
    if not (datei.exists() and meta_datei.exists()):
        return None
    meta = json.loads(meta_datei.read_text(encoding="utf-8"))
    inhalt = datei.read_bytes()
    if (hashlib.sha256(inhalt).hexdigest() != meta.get("sha256") or meta.get("url") != url
            or meta.get("methode", "GET") != methode or meta.get("daten_sha256") != _daten_sha256(daten)):
        raise AbrufFehler(f"Cache beschädigt für {methode} {url} ({datei}). Mit neu=True neu laden.")
    return Ergebnis(inhalt, meta, True)


def _speichern(cache_dir: Path, name: str, inhalt: bytes, meta: dict):
    cache_dir.mkdir(parents=True, exist_ok=True)
    for endung, daten in ((".bin", inhalt), (".json", json.dumps(meta, ensure_ascii=False, indent=1).encode())):
        tmp = cache_dir / f".{name}{endung}.tmp"
        tmp.write_bytes(daten)
        tmp.replace(cache_dir / f"{name}{endung}")


def _header_pruefen(header) -> dict:
    """Eigene Header als dict str -> str. Der Wert wird in Fehlertexten nie genannt (API-Schlüssel)."""
    if header is None:
        return {}
    if not isinstance(header, dict):
        raise AbrufFehler("header muss ein dict sein")
    for name, wert in header.items():
        if not isinstance(name, str) or not name.strip() or any(z in name for z in "\r\n:"):
            raise AbrufFehler(f"Ungültiger Header-Name {name!r}")
        if not isinstance(wert, str) or "\r" in wert or "\n" in wert:
            raise AbrufFehler(f"Ungültiger Wert für Header {name!r} (muss Text ohne Zeilenumbruch sein)")
    return dict(header)


def laden(url: str, allowlist, cache_dir: Path, neu: bool = False, zeitlimit: float = ZEITLIMIT,
          max_bytes: int = MAX_BYTES, _opener=None, *, methode: str = "GET", daten: bytes | None = None,
          header: dict | None = None) -> Ergebnis:
    """Lädt url (nur https, nur Allowlist) oder nimmt sie aus dem Cache.

    methode: "GET" oder "POST". daten: Körper als bytes (nur bei POST). header: eigene Header, z. B. API-Schlüssel;
    sie gehen nicht in Cache, Meta oder Fehlertexte. Ein eigener User-Agent ersetzt den Standard.
    Fehler: AbrufFehler."""
    methode = (methode or "").upper()
    if methode not in METHODEN:
        raise AbrufFehler(f"Methode {methode!r} nicht unterstützt (erlaubt: {', '.join(METHODEN)})")
    if daten is not None and not isinstance(daten, (bytes, bytearray)):
        raise AbrufFehler("daten müssen bytes sein (z. B. json.dumps(...).encode())")
    if methode == "GET" and daten is not None:
        raise AbrufFehler("GET mit daten nicht möglich, dafür methode=\"POST\"")
    daten = None if daten is None else bytes(daten)
    eigene = _header_pruefen(header)
    host = pruefen(url, allowlist)
    cache_dir = Path(cache_dir)
    name = _schluessel(url, methode, daten)
    if not neu:
        treffer = _aus_cache(cache_dir, url, methode, daten)
        if treffer:
            return treffer

    _warten(host)
    kopf = {"User-Agent": USER_AGENT}
    for k, v in eigene.items():  # gleiche Namen ohne Rücksicht auf Groß-/Kleinschreibung ersetzen
        for alt in [a for a in kopf if a.lower() == k.lower()]:
            del kopf[alt]
        kopf[k] = v
    anfrage = urllib.request.Request(url, data=daten, headers=kopf, method=methode)
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
        "methode": methode,
        "endgueltige_url": endgueltig,
        "abgerufen": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "content_type": content_type,
        "sha256": hashlib.sha256(inhalt).hexdigest(),
        "groesse": len(inhalt),
    }
    if daten is not None:
        meta["daten_sha256"] = _daten_sha256(daten)
    _speichern(cache_dir, name, inhalt, meta)
    return Ergebnis(inhalt, meta, False)
