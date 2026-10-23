"""Chats in Runden zerlegen und kompakt für Claude darstellen (Schritt 6, Vorbereitung).

Eine Runde = ein Prompt von Lia und Claudes Antwort darauf. Ein Chat ist ein Baum (parent_message_uuid):
Bearbeitet Lia einen Prompt, entsteht ein Geschwister-Ast. Ausgewertet wird der Hauptpfad zum zuletzt
geschriebenen Blatt; verworfene Äste zählen als Bearbeitung an der Runde, an der sie abzweigen.
Die Einteilung in Aufgaben (mehrere Runden zum selben Ziel) macht später Claude, Python liefert die Runden.
kompakt: Lias Prompts vollständig, Claudes Antworten gekürzt, Anhänge nur mit Namen und Länge.
Ohne Netz, getestet in tests/test_verlauf.py.
"""

from collections import defaultdict

ZEICHEN_JE_TOKEN = 3.5  # grobe Schätzung für deutschen Text, ohne Zählung durch die API


def hauptpfad(nachrichten: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Nachrichten auf dem Pfad zum jüngsten Blatt und je Nachricht die Zahl verworfener Geschwister."""
    kinder = defaultdict(list)
    ids = {n["uuid"] for n in nachrichten}
    for n in nachrichten:
        kinder[n["vorgaenger"]].append(n)
    blaetter = [n for n in nachrichten if not kinder.get(n["uuid"])]
    if not blaetter:
        return [], {}
    nach_id = {n["uuid"]: n for n in nachrichten}
    pfad = []
    n = max(blaetter, key=lambda n: n.get("zeit") or "")
    while n is not None:
        pfad.append(n)
        n = nach_id.get(n["vorgaenger"]) if n["vorgaenger"] in ids else None
    pfad.reverse()
    verworfen = {n["uuid"]: len(kinder[n["vorgaenger"]]) - 1 for n in pfad if len(kinder[n["vorgaenger"]]) > 1}
    return pfad, verworfen


def runden(chat: dict) -> list[dict]:
    pfad, verworfen = hauptpfad(chat["nachrichten"])
    aus = []
    for n in pfad:
        if n["absender"] == "lia":
            aus.append({"nr": len(aus) + 1, "prompt": n["text"], "antwort": "", "anhaenge": n["anhaenge"],
                        "dateien": n["dateien"], "bearbeitet": verworfen.get(n["uuid"], 0)})
        elif aus:
            aus[-1]["antwort"] += ("\n" if aus[-1]["antwort"] else "") + n["text"]
    return aus


def _kurz(text: str, zeichen: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= zeichen else text[:zeichen] + f" […{len(text) - zeichen} Zeichen gekürzt]"


def kompakt(chat: dict, antwort_zeichen: int = 300, von: int = 1, bis: int | None = None) -> str:
    """Text eines Chats (oder der Runden von..bis) für den Prompt."""
    zeilen = [f"### Chat {chat['uuid'][:8]}: {chat['titel']} ({chat['datum']})"]
    for r in runden(chat)[von - 1:bis]:
        extra = []
        if r["bearbeitet"]:
            extra.append(f"Prompt {r['bearbeitet']}x neu geschrieben")
        extra += [f"Anhang {a['name']} ({len(a['text'])} Zeichen)" for a in r["anhaenge"]]
        extra += [f"Datei {d}" for d in r["dateien"]]
        zeilen.append(f"R{r['nr']} LIA: {r['prompt'].strip()}" + (f" [{'; '.join(extra)}]" if extra else ""))
        zeilen.append(f"R{r['nr']} CLAUDE: {_kurz(r['antwort'], antwort_zeichen)}")
    return "\n".join(zeilen)


def tokens_geschaetzt(text: str) -> int:
    return round(len(text) / ZEICHEN_JE_TOKEN)
