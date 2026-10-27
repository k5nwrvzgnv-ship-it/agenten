"""Gemeinsame Vorlagen für Nachrichten beider Zentralen (reine Logik, ohne Telegram).

Ergebnis: Kernaussage zuerst, dann höchstens PUNKTE_MAX Punkte, eine Zeile "Bitte prüfen", Belege als
ausklappbares Zitat (<blockquote expandable>). Die Daten kommen aus dem Feld daten des Auftrags
(auftraege.abschliessen(..., daten=)): kern, punkte, pruefen, belege. Ohne daten bleibt es der Ergebnistext.
Längenbudget: eine Nachricht höchstens MAX_TEXT Zeichen (Telegram 4096); was nicht passt, wird bei den
Belegen gekürzt ("… und N weitere im Dokument"), höchstens BELEGE_MAX Belege. Text oder Dokument: Hat der Auftrag Dateien und passt der
Text in eine Beschriftung (1024 Zeichen ohne Formatierung), steht er unter der Datei, sonst davor.

Feedback-Knöpfe unter jedem Ergebnis: <vorsatz>fb:<auftrag-id>:<k> (höchstens 64 Bytes), k siehe FB_KNOEPFE.
"Zu lang" fragt nach: nur dieses Ergebnis (lh) oder ab jetzt immer (li). "Falscher Fokus" und "Feedback
schreiben" warten auf die nächste Nachricht. Dazu feedback_text() für den Auftragstext.
"""

import re
from html import escape, unescape

Knoepfe = list[list[tuple[str, str]]]
MAX_TEXT = 3800
PUNKTE_MAX = 3
BELEGE_MAX = 10  # mehr stehen im Dokument
ID = r"\d{8}-\d{6}-[a-z]+-[0-9a-f]{6}"
FB_KNOEPFE = {
    "ok": "Passt",
    "lang": "Zu lang",
    "fokus": "Falscher Fokus",
    "frei": "Feedback schreiben",
    "lh": "Nur hier kürzer",
    "li": "Ab jetzt immer kürzer",
    "zu": "« Zurück",
}
FB_TEXTE = {
    "lh": "Zu lang. Bitte nur dieses Ergebnis kürzen.",
    "li": "Zu lang. Ab jetzt bitte alle Ergebnisse dieser Art kürzer.",
}
FB_FRAGE = {
    "fokus": "Was hätte im Mittelpunkt stehen sollen? Schreib es mir als nächste Nachricht.",
    "frei": "Was soll anders sein? Schreib es mir als nächste Nachricht.",
}
FB_VORSATZ = {"fokus": "Falscher Fokus: ", "frei": ""}
DANKE = "Danke, ich kümmere mich darum."


def esc(text: str) -> str:
    return escape(text or "", False)


def kurz(text: str, laenge: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


# ---------- Ergebnis ----------

def _belege(belege: list[str], platz: int) -> str:
    """Ausklappbares Zitat mit so vielen Belegen, wie in platz Zeichen passen."""
    if not belege or platz < 80:
        return ""
    zeilen, rest = [], platz - len("<blockquote expandable>Belege\n</blockquote>") - 40
    for i, b in enumerate(belege):
        zeile = "• " + esc(kurz(b, 300))
        if i == BELEGE_MAX or len(zeile) + 1 > rest:
            zeilen.append(f"… und {len(belege) - i} weitere im Dokument")
            break
        zeilen.append(zeile)
        rest -= len(zeile) + 1
    return "<blockquote expandable>Belege\n" + "\n".join(zeilen) + "</blockquote>"


def ergebnis_html(kopf: str, auftrag: dict, aufteilen) -> list[str]:
    """Ergebnis als HTML-Nachricht(en). kopf: fertige erste Zeile (HTML). aufteilen: logik.aufteilen."""
    daten = auftrag.get("daten") or {}
    if auftrag.get("status") != "erledigt" or not daten.get("kern"):
        text = (auftrag.get("ergebnis") or "Erledigt.").strip()
        stuecke = aufteilen(text, MAX_TEXT - len(kopf) - 50)
        return [f"{kopf}\n{esc(stuecke[0])}".rstrip(), *(esc(s) for s in stuecke[1:])]
    teile = [kopf.rstrip(), esc(kurz(daten["kern"], 600))]
    punkte = [p for p in daten.get("punkte") or [] if p.strip()][:PUNKTE_MAX]
    if punkte:
        teile.append("\n".join("• " + esc(kurz(p, 300)) for p in punkte))
    if daten.get("pruefen"):
        teile.append("<i>Bitte prüfen: " + esc(kurz(daten["pruefen"], 300)) + "</i>")
    text = "\n\n".join(teile)
    belege = _belege(daten.get("belege") or [], MAX_TEXT - len(text) - 2)
    return [text + ("\n\n" + belege if belege else "")]


def sichtbare_laenge(html: str) -> int:
    """Zeichen ohne Formatierung (so zählt Telegram die 1024 einer Beschriftung)."""
    return len(unescape(re.sub(r"<[^>]+>", "", html)))


# ---------- Feedback-Knöpfe ----------

def fb_daten(vorsatz: str, aid: str, k: str) -> str:
    daten = f"{vorsatz}fb:{aid}:{k}"
    if len(daten.encode()) > 64:
        raise ValueError(f"Knopf-Daten zu lang: {daten}")
    return daten


def feedback_knoepfe(vorsatz: str, aid: str, extra: Knoepfe | None = None) -> Knoepfe:
    """Knöpfe unter einem Ergebnis. extra: weitere Zeile(n), z. B. der Menü-Knopf bei Lia."""
    z1 = [(FB_KNOEPFE[k], fb_daten(vorsatz, aid, k)) for k in ("ok", "lang", "fokus")]
    z2 = [(FB_KNOEPFE["frei"], fb_daten(vorsatz, aid, "frei"))]
    if extra:
        z2 += extra[0]
    return [z1, z2, *(extra or [])[1:]]


def laenge_knoepfe(vorsatz: str, aid: str) -> Knoepfe:
    return [[(FB_KNOEPFE[k], fb_daten(vorsatz, aid, k)) for k in ("lh", "li")],
            [(FB_KNOEPFE["zu"], fb_daten(vorsatz, aid, "zu"))]]


def feedback_auswerten(daten: str, vorsatz: str) -> tuple[str, str] | None:
    """'<vorsatz>fb:<id>:lang' -> (id, 'lang'), sonst None."""
    m = re.fullmatch(re.escape(vorsatz) + rf"fb:({ID}):([a-z]+)", daten or "")
    return (m.group(1), m.group(2)) if m and m.group(2) in FB_KNOEPFE else None


def feedback_text(k: str, eingabe: str = "") -> str:
    """Auftragstext für den Feedback-Dienst: fester Text eines Knopfs oder die freie Eingabe (mit Vorsatz)."""
    if k in FB_TEXTE:
        return FB_TEXTE[k]
    return FB_VORSATZ.get(k, "") + eingabe.strip()


def vermerk(k: str) -> str:
    """Zeile, die nach dem Feedback statt der Knöpfe unter dem Ergebnis steht."""
    return "Danke!" if k == "ok" else DANKE


# ---------- Feedback-Bestätigung und Meldungen ----------

def feedback_bestaetigung(auftrag: dict) -> str:
    """Rückmeldung des Feedback-Dienstes an die Person (HTML)."""
    kopf = f"<b>Zu deinem Feedback</b> „{esc(kurz(auftrag.get('text', ''), 80))}“"
    return f"{kopf}\n{esc(auftrag.get('ergebnis') or 'Ist angekommen.')}"
