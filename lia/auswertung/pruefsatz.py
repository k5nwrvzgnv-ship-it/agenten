"""Beispiele und Prüfsatz aus echten, anonymisierten Aufträgen (Schritt 7).

Prüfsatz-Eintrag: Lias Auftrag (ihr Prompt in der ersten Runde der Aufgabe, dazu frühere Prompts derselben
Aufgabe nicht, denn der Agent bekommt auch nur einen Auftrag), Kriterien aus ihren Korrekturen,
und ihr altes Ergebnis (Claudes Antwort in der Runde, in der das Ergebnis vorlag) für den Blindvergleich.
Auswahl: nur erreichte Aufgaben mit eigenständigem Auftrag (am Chatanfang mindestens MIN_ZEICHEN, mitten im
Chat mindestens MIN_ZEICHEN_MITTE), je Typ die mit den meisten Korrekturen zuerst. Dazu als Kontext Lias
letzte KONTEXT Prompts davor (gekürzt), damit der Auftrag für einen Agenten vollständig formuliert werden kann.
Ohne Netz, getestet in tests/test_pruefsatz.py.
"""

import rangliste
import verlauf

MIN_ZEICHEN = 40
MIN_ZEICHEN_MITTE = 150
KONTEXT = 3


def runden_der_aufgabe(chat: dict, aufgabe: dict) -> list[dict]:
    return [r for r in verlauf.runden(chat) if aufgabe["von"] <= r["nr"] <= aufgabe["bis"]]


def eintrag(chat: dict, aufgabe: dict) -> dict | None:
    runden = runden_der_aufgabe(chat, aufgabe)
    if not runden or aufgabe["ergebnis"] != "erreicht" or not isinstance(aufgabe.get("runde_ergebnis"), int):
        return None
    auftrag = runden[0]["prompt"].strip()
    if len(auftrag) < (MIN_ZEICHEN if aufgabe["von"] == 1 else MIN_ZEICHEN_MITTE):
        return None
    davor = [r for r in verlauf.runden(chat) if r["nr"] < aufgabe["von"]][-KONTEXT:]
    alt = next((r["antwort"] for r in runden if r["nr"] == aufgabe["runde_ergebnis"]), "")
    return {"typ": rangliste.typ(aufgabe), "kategorie": aufgabe["kategorie"], "titel": aufgabe["titel"],
            "fach": aufgabe["fach"], "klasse": aufgabe["klasse"], "chat": aufgabe["chat"],
            "runden": f"{aufgabe['von']}-{aufgabe['bis']}", "auftrag": auftrag,
            "anhaenge": [a["name"] for a in runden[0]["anhaenge"]] + runden[0]["dateien"],
            "kontext": [" ".join(r["prompt"].split())[:300] for r in davor],
            "kriterien": [f"{k['art']}: {k.get('zitat', '')}" for k in aufgabe["korrekturen"]],
            "altes_ergebnis": alt}


def auswaehlen(chats: dict[str, dict], aufgaben: list[dict], je_typ: dict[str, int]) -> list[dict]:
    """chats: nach den ersten 8 Zeichen der uuid. je_typ: wie viele Einträge je Aufgabentyp."""
    kandidaten: dict[str, list[dict]] = {}
    for a in sorted(aufgaben, key=lambda a: (-len(a["korrekturen"]), a["chat"], a["von"])):
        t = rangliste.typ(a)
        if t not in je_typ or a["chat"] not in chats:
            continue
        e = eintrag(chats[a["chat"]], a)
        if e:
            kandidaten.setdefault(t, []).append(e)
    aus = []
    for t, anzahl in je_typ.items():
        aus += kandidaten.get(t, [])[:anzahl]
    for i, e in enumerate(aus, 1):
        e["id"] = f"P{i:02d}"
    return aus
