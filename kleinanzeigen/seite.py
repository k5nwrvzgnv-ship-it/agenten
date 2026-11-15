"""Suchseite von Kleinanzeigen auslesen (ohne Netz).

Die Seite enthält die Anzeigen als Daten einer Astro-Komponente (ImpressionTracker): Attribut props,
HTML-maskiertes JSON im Astro-Format. Darin ist jeder Wert ein Paar [typ, wert]: typ 0 = einfacher Wert
oder Objekt, typ 1 = Liste. Werbeanzeigen (sponsoredAd) werden übersprungen.
"""

import html
import json
import re
from dataclasses import dataclass, field

BASIS = "https://www.kleinanzeigen.de"


class SeitenFehler(Exception):
    """Die Seite hat nicht das erwartete Format (Kleinanzeigen hat etwas geändert oder blockt)."""


@dataclass
class Anzeige:
    id: int
    titel: str
    beschreibung: str
    link: str
    preis_text: str
    preis: float | None
    vb: bool
    plz: str
    ort: str
    datum: str
    top: bool
    gewerblich: bool
    bild: str | None = None
    versand: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def neu(self) -> bool:
        """Heute oder gestern eingestellt (Top-Anzeigen sind oft Wochen alt)."""
        return self.datum.startswith(("Heute", "Gestern"))


def astro_wert(w):
    """Astro-Serialisierung [typ, wert] rekursiv in normales Python umwandeln."""
    if isinstance(w, list) and len(w) == 2 and isinstance(w[0], int):
        typ, inhalt = w
        if typ == 1 and isinstance(inhalt, list):
            return [astro_wert(x) for x in inhalt]
        return astro_wert(inhalt)
    if isinstance(w, list) and len(w) == 1 and isinstance(w[0], int):
        return None  # leerer Wert, z. B. [0]
    if isinstance(w, dict):
        return {k: astro_wert(v) for k, v in w.items()}
    return w


def preis_lesen(text: str) -> tuple[float | None, bool]:
    """'1.200 € VB' -> (1200.0, True), 'Zu verschenken' -> (0.0, False), 'VB' -> (None, True)."""
    t = (text or "").strip()
    vb = bool(re.search(r"\bVB\b", t))
    if "verschenken" in t.lower():
        return 0.0, False
    m = re.search(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?\s*€", t)
    if not m:
        return None, vb
    ganz = m.group(1).replace(".", "")
    return float(f"{ganz}.{m.group(2) or 0}"), vb


_PROPS = re.compile(r"<astro-island\b[^>]*?\bprops=\"([^\"]*)\"", re.S)


def anzeigen_lesen(seite: str) -> list[Anzeige]:
    """Alle normalen Anzeigen der Suchseite. SeitenFehler, wenn die Anzeigenliste fehlt."""
    for m in _PROPS.finditer(seite):
        roh = m.group(1)
        if "resultAds" not in roh:
            continue
        try:
            daten = astro_wert(json.loads(html.unescape(roh)))
        except json.JSONDecodeError as f:
            raise SeitenFehler(f"Anzeigenliste ist kein JSON: {f}") from f
        return [a for a in (_anzeige(e) for e in daten.get("resultAds") or []) if a]
    if "Keine Ergebnisse" in seite or "keine Anzeigen" in seite.lower():
        return []
    raise SeitenFehler("Keine Anzeigenliste auf der Seite (Format geändert oder gesperrt?)")


def _anzeige(eintrag) -> Anzeige | None:
    if not isinstance(eintrag, dict):
        return None
    a = eintrag.get("organicAdPreview")
    if not isinstance(a, dict) or not a.get("id") or not a.get("seoLink"):
        return None
    preis, vb = preis_lesen(a.get("price") or "")
    bilder = a.get("imageList") or []
    bild = bilder[0].get("xLargeUrl") if bilder and isinstance(bilder[0], dict) else None
    return Anzeige(
        id=int(a["id"]),
        titel=(a.get("title") or "").strip(),
        beschreibung=(a.get("description") or "").strip(),
        link=BASIS + a["seoLink"],
        preis_text=(a.get("price") or "").strip(),
        preis=preis,
        vb=vb,
        plz=str(a.get("locationName") or ""),
        ort=(a.get("parentLocationName") or "").strip(),
        datum=(a.get("sortingDate") or "").strip(),
        top=bool(a.get("topAd")),
        gewerblich=(a.get("posterType") or "PRIVATE") != "PRIVATE",
        bild=bild,
        versand=bool(a.get("shippingAvailableValue")),
    )


def _slug(text: str) -> str:
    """Suchbegriff für die URL: klein, Umlaute ausgeschrieben, Bindestriche statt Leerzeichen."""
    t = text.lower().strip()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t or "alles"


def such_url(begriff: str, max_preis: float | None = None, ort_id: int | None = None,
             plz: str | None = None, umkreis_km: int | None = None) -> str:
    """URL der Suchseite. Mit Ort: /s-<plz>/<begriff>/k0l<ort_id>r<km>; Preis: /s-preis::<max>/..."""
    teile = []
    if ort_id and plz:
        teile.append(plz)
    if max_preis is not None:
        teile.append(f"preis::{int(max_preis)}")
    pfad = "/s-" + "/".join(teile + [_slug(begriff)]) if teile else f"/s-{_slug(begriff)}"
    code = "k0"
    if ort_id and plz:
        code += f"l{ort_id}"
        if umkreis_km:
            code += f"r{int(umkreis_km)}"
    return f"{BASIS}{pfad}/{code}"


def ort_id_lesen(antwort: dict, plz: str) -> int | None:
    """Antwort von /s-ort-empfehlungen.json?query=<plz> -> Orts-ID ({"_4927": "34128 Kassel"} -> 4927)."""
    for schluessel, name in antwort.items():
        if schluessel in ("_0", "0"):
            continue  # "Deutschland"
        if str(name).startswith(plz):
            try:
                return int(schluessel.lstrip("_"))
            except ValueError:
                continue
    return None
