"""PDF: Formulare aus dem Gesamtpaket schneiden, füllen und zu einer Druckdatei zusammenfügen (pypdf).

Jedes Formular wird zuerst eine eigene PDF (seine Seiten aus dem Paket), damit gleiche Feldnamen
verschiedener Formulare sich nicht gegenseitig überschreiben. Danach bekommen alle Felder einen
Vorsatz (<schluessel>.), erst dann wird zusammengefügt. Die Felder bleiben ausfüllbar: Lia kann
Fehlendes auch am Rechner eintragen, bevor sie druckt.
"""

import hashlib
import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject


class DruckFehler(RuntimeError):
    """Paket passt nicht (Prüfsumme, Seitenzahl) oder ein Feld der Zuordnung fehlt im PDF."""


def pruefsumme(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def paket_oeffnen(pfad: Path, sha256: str, seiten: int) -> PdfReader:
    if pruefsumme(pfad) != sha256:
        raise DruckFehler("Das Formularpaket von berlin.de hat sich geändert. Zuordnung neu prüfen "
                          "(formulare.py), sonst landen Angaben in falschen Feldern.")
    leser = PdfReader(pfad)
    if len(leser.pages) != seiten:
        raise DruckFehler(f"Paket hat {len(leser.pages)} statt {seiten} Seiten")
    return leser


def _widgets(seite):
    for a in seite.get("/Annots") or []:
        a = a.get_object()
        if a.get("/Subtype") == "/Widget":
            yield a


def _feld(widget):
    """Das Feld (mit /T) zu einem Widget: das Widget selbst oder sein Elternobjekt."""
    return widget if widget.get("/T") is not None else widget["/Parent"].get_object()


def feldnamen(writer: PdfWriter) -> set[str]:
    return {str(_feld(w)["/T"]) for s in writer.pages for w in _widgets(s)}


def formular_bauen(paket: PdfReader, seiten: list[int], werte: dict, vorsatz: str) -> bytes:
    """Seiten (ab 1) aus dem Paket, mit werte gefüllt, Felder mit Vorsatz. Gibt die PDF als Bytes zurück."""
    w = PdfWriter()
    w.append(paket, pages=[s - 1 for s in seiten])
    unbekannt = set(werte) - feldnamen(w)
    if unbekannt:
        raise DruckFehler(f"{vorsatz}: Felder nicht im PDF: {', '.join(sorted(unbekannt))}")
    if werte:
        w.set_need_appearances_writer(True)
        for seite in w.pages:
            namen = {str(_feld(x)["/T"]) for x in _widgets(seite)}
            hier = {k: v for k, v in werte.items() if k in namen}
            if hier:
                w.update_page_form_field_values(seite, hier, auto_regenerate=False)
    umbenannt = set()
    for seite in w.pages:
        for x in _widgets(seite):
            f = _feld(x)
            if id(f) in umbenannt:
                continue
            # oberstes Feld finden (bei Kindern mit eigenem /T bleibt der Pfad erhalten)
            while f.get("/Parent") is not None and f["/Parent"].get_object().get("/T") is not None:
                f = f["/Parent"].get_object()
            if not str(f["/T"]).startswith(vorsatz + "."):
                f[NameObject("/T")] = TextStringObject(f"{vorsatz}.{f['/T']}")
            umbenannt.add(id(f))
    puffer = io.BytesIO()
    w.write(puffer)
    return puffer.getvalue()


def zusammenfuegen(teile: list[bytes]) -> bytes:
    gesamt = PdfWriter()
    for teil in teile:
        gesamt.append(PdfReader(io.BytesIO(teil)))
    gesamt.set_need_appearances_writer(True)
    puffer = io.BytesIO()
    gesamt.write(puffer)
    return puffer.getvalue()


def feldwerte(pdf: bytes) -> dict[str, str]:
    """Gefüllte Felder einer fertigen PDF (für Tests und die Kontrolle)."""
    felder = PdfReader(io.BytesIO(pdf)).get_fields() or {}
    return {k: str(v.get("/V")) for k, v in felder.items() if v.get("/V") not in (None, "", "/Off")}
