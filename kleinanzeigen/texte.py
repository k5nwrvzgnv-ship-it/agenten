"""Texte für Telegram (HTML) und Zeitregeln, ohne Netz."""

import html
from datetime import datetime

from eingabe import details_text
from seite import Anzeige

HILFE = (
    "Schreib, was du suchst, oder schick ein <b>Foto</b> (gern mit Text dazu).\n"
    "Danach frage ich nach Preisgrenze und Ort, z. B. <code>80 € 30 km 34128</code> "
    "oder <code>80 €</code> für ganz Deutschland.\n"
    "Neue gute Angebote kommen sofort mit Link, schreiben musst du den Verkäufern selbst.\n\n"
    "/suchen – deine Suchen (pausieren, löschen)\n/hilfe – diese Hilfe"
)


def e(text) -> str:
    return html.escape(str(text), quote=False)


def suche_text(s: dict) -> str:
    begriffe = ", ".join(f"„{b}“" for b in s["begriffe"])
    zustand = {"aktiv": "läuft", "pause": "pausiert", "entwurf": "wartet auf Preis und Ort"}.get(s["status"], s["status"])
    return (f"<b>#{s['id']} {e(s['titel'])}</b> ({zustand})\n"
            f"{e(details_text(s['max_preis'], s['umkreis_km'], s['plz']))}\nSuchbegriffe: {e(begriffe)}")


def treffer_text(a: Anzeige, bewertung: dict | None, suche_titel: str, markt: float | None = None) -> str:
    """Eine Meldung je Treffer. bewertung None = Notmeldung ohne Claude (Tagesgrenze)."""
    zeilen = [f"<b>{e(a.titel)}</b>", f"<b>{e(a.preis_text or 'ohne Preis')}</b>"
              + (" (gewerblich)" if a.gewerblich else "")]
    wert = (bewertung or {}).get("marktwert") or markt
    if wert and a.preis is not None:
        zeilen[-1] += f" · üblich ca. {wert:g} €"
    zeilen.append(f"{e(a.plz)} {e(a.ort)} · {e(a.datum)}" + (" · Versand" if a.versand else ""))
    if bewertung:
        zeilen.append(f"{bewertung['punkte']}/100 – {e(bewertung['grund'])}")
    else:
        zeilen.append("Ohne Bewertung (Tagesgrenze erreicht), Preis klar unter dem Median dieser Suche.")
    zeilen.append(f"Suche: {e(suche_titel)}")
    zeilen.append(f'<a href="{e(a.link)}">Zur Anzeige</a>')
    return "\n".join(zeilen)


def ist_nacht(jetzt: datetime, von: int, bis: int) -> bool:
    """Nachtruhe von..bis Uhr (z. B. 1..6). von == bis: keine Nachtruhe."""
    if von == bis:
        return False
    h = jetzt.hour
    return von <= h < bis if von < bis else (h >= von or h < bis)


def tag(jetzt: datetime) -> str:
    return jetzt.strftime("%Y-%m-%d")
