"""Reihenkontext: Lias laufende Unterrichtsreihen (reihen.toml) für jeden Lauf.

Grund (lia/auswertung, 23.10.2026): Viele Korrekturen in Lias Chats entstanden, weil Claude Reihenfrage, Klasse
oder schon behandelte Positionen nicht kannte. prompt_reihen macht aus den Reihen einen Prompt-Abschnitt.

Die Datei (lia/instanz/reihen.toml, EINE Datei für Web-App und Agenten) liest seit 03.11.2026 nur noch
agentkit.struktur (docs/struktur-pflege-plan.md, Bauschritt 2): Format, Prüfung, altes und neues Format stehen
dort im Kopf. laden gibt die Struktur zurück, ist die Datei kaputt, kommt struktur.StrukturFehler (Text für Jan).
Laufend im Prompt sind die Reihen mit stand geplant oder laufend; abgeschlossene und archivierte stehen nur als
kurze Liste.

Stunden (board-plan.md 3): reihe["stunden"], sichtbare Stunden mit gezählter nr, thema und marke ("UB" oder
"Prüfung"). Sie gehen mit ins Prompt. Welche Reihe gewählt ist, sagt wahl: das Feld ort des Auftrags (id einer
Stunde oder Reihe, über s.ort), sonst das Feld reihe (Web-App). Die gewählte Reihe steht zuerst und als gewählt,
eine Stunde aus ort steht als eigene Zeile darunter. Ohne ort steht die Stunde wie bisher als Zeile
„Stunde n: Thema“ (bzw. „Probe n“) im Auftragstext.
"""

from pathlib import Path

from agentkit import struktur


def laden(instanz: Path) -> struktur.Struktur:
    """Struktur aus <instanz>/reihen.toml über agentkit.struktur. Fehlt die Datei, gibt es keine Reihen."""
    return struktur.laden(instanz)


def wahl(s: struktur.Struktur | None, auftrag: dict) -> tuple[str | None, dict | None]:
    """(id der gewählten Reihe, gewählte Stunde oder None). Feld ort zuerst (Stunde oder Reihe), sonst Feld reihe.
    Zeigt ort auf etwas anderes (Klasse, Fach) oder auf nichts, gilt das Feld reihe."""
    lage = s.ort(auftrag["ort"]) if s is not None and auftrag.get("ort") else None
    if lage and lage["reihe"]:
        return lage["reihe"]["id"], lage["stunde"]
    return auftrag.get("reihe"), None


def laufend(reihe: dict) -> bool:
    """geplant zählt als laufend (Straftheorien ist geplant und genau die Reihe, an der Lia arbeitet)."""
    return reihe.get("stand", "laufend") in ("geplant", "laufend") and not reihe.get("im_archiv")


def ort(reihe: dict, fach: str) -> str:
    """z. B. „Ethik, Klasse 8“ oder „Darstellendes Spiel, Kurs 12“."""
    klasse = str(reihe["klasse"])
    return f"{reihe.get('fach') or fach}, " + (f"Klasse {klasse}" if klasse[:1].isdigit() else klasse)


def stunden_wort(reihe: dict) -> str:
    """„Probe“ für eine Inszenierung (Reihe des Theater-Agenten), sonst „Stunde“ (wie die Web-App)."""
    return "Probe" if "theater" in reihe.get("agenten", []) else "Stunde"


def stunde_zeile(reihe: dict, stunde: dict) -> str:
    """z. B. „Stunde 3: Kant (Prüfung)“; eine ausgeblendete Stunde hat keine Nummer."""
    nr = f" {stunde['nr']}" if stunde.get("nr") else ""
    return f"{stunden_wort(reihe)}{nr}: {stunde['thema']}" + (f" ({stunde['marke']})" if stunde.get("marke") else "")


def prompt_reihen(reihen: list[dict], fach: str, gewaehlt: str | None = None, stunde: dict | None = None) -> str:
    """Abschnitt für den Prompt, leer ohne Reihen. gewaehlt: id der Reihe aus dem Auftrag (wahl), stunde: die
    Stunde aus dem Feld ort, falls es eine Stunde nennt."""
    if not reihen:
        return ""
    bloecke = []
    wahl = next((r for r in reihen if gewaehlt and r.get("id") == gewaehlt), None)
    for r in ([wahl] if wahl else []) + [r for r in reihen if laufend(r) and r is not wahl]:
        kopf = f"### {ort(r, fach)}" + (f": {r['titel']}" if r.get("titel") else "")
        if r is wahl:
            kopf += " (Lia hat den Auftrag dieser Reihe zugeordnet)"
        zeilen = [kopf]
        if r is wahl and stunde:
            zeilen.append(f"- Lia hat den Auftrag zugeordnet: {stunde_zeile(r, stunde)}")
        if r.get("reihenfrage"):
            zeilen.append(f"- Reihenfrage: {r['reihenfrage']}")
        if r.get("lerngruppe"):
            zeilen.append(f"- Lerngruppe: {r['lerngruppe']}")
        if r.get("bisherige_reihen"):
            zeilen.append("- Frühere Reihen der Klasse:\n" + "\n".join(f"  - {x}" for x in r["bisherige_reihen"]))
        if r.get("behandelt"):
            zeilen.append("- Schon behandelt: " + "; ".join(r["behandelt"]))
        if r.get("merksaetze"):
            zeilen.append("- Merksätze der Reihe:\n" + "\n".join(f"  - {m}" for m in r["merksaetze"]))
        if r.get("notizen"):
            zeilen.append(f"- Notizen: {r['notizen']}")
        if r.get("stunden"):
            wort = stunden_wort(r)
            zeilen.append(f"- {wort}n der Reihe:\n" + "\n".join(f"  - {stunde_zeile(r, s)}" for s in r["stunden"]))
        bloecke.append("\n".join(zeilen))
    fertig = [r for r in reihen if not laufend(r) and r is not wahl]
    if fertig:
        bloecke.append("### Abgeschlossene Reihen (nur zur Orientierung, was die Klassen schon kennen)\n" + "\n".join(
            f"- {ort(r, fach)}" + (f" ({r['schuljahr']})" if r.get("schuljahr") else "")
            + (f": {r['titel']}" if r.get("titel") else "") + (f" – {r['reihenfrage']}" if r.get("reihenfrage") else "")
            for r in fertig))
    return ("## Lias laufende Reihen\n"
            "Nimm die Reihe, die zu Klasse und Thema des Wunsches passt. Halte dich an ihre Reihenfrage und ihre "
            "Lerngruppe und baue auf dem auf, was schon behandelt ist; Merksätze der Reihe übernimmst du im "
            "Wortlaut. Frühere Reihen zeigen, was die Klasse schon kennt. Hat Lia den Auftrag einer Reihe zugeordnet, "
            "nimm diese. Nennt ihr Wunsch eine Stunde (z. B. „Stunde 3: …“), passt das Material genau zu dieser "
            "Stunde: Es baut auf den Stunden davor auf und bereitet die danach vor; bei UB oder Prüfung besonders "
            "sorgfältig. Passt keine Reihe oder mehrere, nenne deine Annahme im Begleittext.\n\n"
            + "\n\n".join(bloecke) + "\n\n")


def prompt_auftrag(s: struktur.Struktur | None, fach: str, auftrag: dict) -> str:
    """prompt_reihen für einen Auftrag: alle Reihen der Struktur, gewählt nach wahl. Ohne Struktur leer."""
    if s is None:
        return ""
    gewaehlt, stunde = wahl(s, auftrag)
    return prompt_reihen(s.reihen, fach, gewaehlt, stunde)
