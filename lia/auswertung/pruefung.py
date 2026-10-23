"""Prüfung durch Lia (Schritt 8): Kodierbogen, Übereinstimmung, Blindvergleich.

1. Kodierbogen: stichprobe() zieht Aufgaben (je Kategorie mindestens eine, nicht zu lang). Lia sieht den
   Chatausschnitt ohne Claudes Einordnung und wählt Kategorie, Ergebnis, Automatisierbarkeit, Korrekturen.
   uebereinstimmung() vergleicht ihre Antworten mit Claudes Einordnung (Anteil gleich, Cohens Kappa).
2. Blindvergleich: paare() stellt je Prüfsatz-Auftrag das alte Ergebnis und das neue von lia/unterricht als
   A und B in zufälliger Reihenfolge nebeneinander, beide als reiner Text. Der Schlüssel bleibt in data/.
   vergleich_auswerten() löst den Schlüssel auf.
formular_html(): eine einzelne HTML-Datei ohne Netz. Lia füllt sie im Browser aus, „Antworten speichern“
lädt eine CSV-Datei (id;feld;wert) herunter, die sie Jan schickt. lies_antworten() liest diese CSV.
Ohne Netz, getestet in tests/test_pruefung.py.
"""

import csv
import html
import io
import json
import random
import re
from collections import Counter

import pruefsatz

ANTWORT_ZEICHEN = 700
MAX_RUNDEN = 12

KATEGORIE_TEXT = {
    "fachklaerung": "Fachfrage klären", "auswahl": "Auswahl (Stücke, Positionen, Beispiele)",
    "planung": "Planung (Reihe, Stunde, UB)", "material": "Material für SuS erstellen",
    "eigener_text": "Eigenen Text prüfen/überarbeiten", "bewertung": "Bewertung, Noten",
    "verwaltung": "Verwaltung, Formulare", "kommunikation": "Nachricht an andere", "sonstiges": "Sonstiges"}
ERGEBNIS_TEXT = {"erreicht": "Ergebnis erreicht", "teilweise": "teilweise", "abgebrochen": "abgebrochen",
                 "unklar": "unklar"}
AUTO_TEXT = {"hoch": "hoch: ein Agent könnte das allein", "mittel": "mittel: mit Rückfragen oder meinem Material",
             "gering": "gering: braucht mein Urteil im Gespräch"}
KORREKTUR_TEXT = {"fachlich": "fachlich falsch", "niveau": "zu schwer für die Klasse", "umfang": "zu lang/zu kurz",
                  "form": "andere Form", "stil": "Ton, Wortwahl", "anwendbarkeit": "im Unterricht nicht brauchbar",
                  "missverstanden": "falsch verstanden", "einseitig": "zu einseitig", "andere": "anderes"}


def stichprobe(aufgaben: list[dict], anzahl: int = 25, seed: int = 8, max_runden: int = MAX_RUNDEN) -> list[dict]:
    """Je Kategorie mindestens eine Aufgabe (falls vorhanden), Rest zufällig. Nur Aufgaben bis max_runden."""
    rnd = random.Random(seed)
    pool = [a for a in aufgaben if a["bis"] - a["von"] + 1 <= max_runden]
    rnd.shuffle(pool)
    gewaehlt, gesehen = [], set()
    for a in pool:
        if a["kategorie"] not in gesehen:
            gewaehlt.append(a)
            gesehen.add(a["kategorie"])
    rest = [a for a in pool if a not in gewaehlt]
    gewaehlt += rest[:max(0, anzahl - len(gewaehlt))]
    return sorted(gewaehlt[:anzahl], key=lambda a: (a["chat"], a["von"]))


def ausschnitt(chat: dict, aufgabe: dict) -> str:
    zeilen = []
    for r in pruefsatz.runden_der_aufgabe(chat, aufgabe):
        dateien = [a["name"] for a in r["anhaenge"]] + r["dateien"]
        zeilen.append(f"Runde {r['nr']} – du: {r['prompt'].strip()}" + (f" [Dateien: {', '.join(dateien)}]" if dateien else ""))
        antwort = " ".join(r["antwort"].split())
        if len(antwort) > ANTWORT_ZEICHEN:
            antwort = antwort[:ANTWORT_ZEICHEN] + " […]"
        zeilen.append(f"Runde {r['nr']} – Claude: {antwort}")
    return "\n\n".join(zeilen)


def kodier_eintraege(chats: dict[str, dict], auswahl: list[dict]) -> list[dict]:
    eintraege = []
    for i, a in enumerate(auswahl, 1):
        eintraege.append({
            "id": f"K{i:02d}", "titel": f"Aufgabe {i} von {len(auswahl)}",
            "abschnitte": [("Chatausschnitt", ausschnitt(chats[a["chat"]], a))],
            "felder": [
                {"name": "kategorie", "frage": "Was für eine Aufgabe war das?", "optionen": KATEGORIE_TEXT},
                {"name": "ergebnis", "frage": "Hattest du am Ende ein Ergebnis, das du verwenden konntest?",
                 "optionen": ERGEBNIS_TEXT},
                {"name": "automatisierbar", "frage": "Hätte ein Agent das für dich erledigen können?",
                 "optionen": AUTO_TEXT},
                {"name": "korrekturen", "frage": "Wie oft musstest du Claude korrigieren oder etwas ändern lassen?",
                 "optionen": {str(n): str(n) for n in range(6)} | {"6+": "6 oder mehr"}},
                {"name": "korrekturarten", "frage": "Warum? (mehrere möglich)", "optionen": KORREKTUR_TEXT,
                 "mehrfach": True},
            ]})
    return eintraege


def formular_html(titel: str, einleitung: str, eintraege: list[dict], dateiname: str) -> str:
    """Eigenständige HTML-Seite mit Formular und CSV-Download (id;feld;wert)."""
    teile = [f"<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' "
             f"content='width=device-width, initial-scale=1'><title>{html.escape(titel)}</title><style>"
             "body{font-family:system-ui,sans-serif;max-width:760px;margin:0 auto;padding:16px;line-height:1.45;"
             "background:#fff;color:#222}section{border-top:2px solid #ccc;padding:12px 0 20px}"
             "pre{white-space:pre-wrap;background:#f5f5f5;padding:12px;border-radius:6px;font-family:inherit}"
             "fieldset{border:0;padding:4px 0}legend{font-weight:600}label{display:block;padding:2px 0}"
             "button{font-size:1.1em;padding:10px 16px;margin:16px 0}</style></head><body>",
             f"<h1>{html.escape(titel)}</h1>", f"<p>{html.escape(einleitung)}</p><form id='f'>"]
    for e in eintraege:
        teile.append(f"<section><h2>{html.escape(e['titel'])}</h2>")
        for ueberschrift, text in e["abschnitte"]:
            teile.append(f"<h3>{html.escape(ueberschrift)}</h3><pre>{html.escape(text)}</pre>")
        for f in e["felder"]:
            typ = "checkbox" if f.get("mehrfach") else "radio"
            teile.append(f"<fieldset><legend>{html.escape(f['frage'])}</legend>")
            for wert, text in f["optionen"].items():
                name = html.escape(f"{e['id']}|{f['name']}", quote=True)
                teile.append(f"<label><input type='{typ}' name='{name}' value='{html.escape(wert, quote=True)}'> "
                             f"{html.escape(text)}</label>")
            teile.append("</fieldset>")
        teile.append(f"<label>Anmerkung (frei): <input type='text' name='{e['id']}|anmerkung' size='60'></label>"
                     "</section>")
    teile.append("</form><button onclick='speichern()'>Antworten speichern</button><script>"
                 "function speichern(){var z=['id;feld;wert'];var f=document.getElementById('f');"
                 "for(var i=0;i<f.elements.length;i++){var e=f.elements[i];if(!e.name)continue;"
                 "if((e.type=='radio'||e.type=='checkbox')&&!e.checked)continue;if(e.type=='text'&&!e.value)continue;"
                 "var t=e.name.split('|');z.push(t[0]+';'+t[1]+';'+e.value.replace(/[;\\n]/g,' '));}"
                 "var b=new Blob([z.join('\\n')],{type:'text/csv'});var a=document.createElement('a');"
                 f"a.href=URL.createObjectURL(b);a.download={json.dumps(dateiname)};a.click();}}"
                 "</script></body></html>")
    return "".join(teile)


def lies_antworten(text: str) -> dict[str, dict[str, list[str]]]:
    """CSV aus dem Formular: {id: {feld: [werte]}}."""
    aus: dict[str, dict[str, list[str]]] = {}
    for zeile in csv.DictReader(io.StringIO(text.strip()), delimiter=";"):
        aus.setdefault(zeile["id"], {}).setdefault(zeile["feld"], []).append(zeile["wert"])
    return aus


def kappa(paare: list[tuple[str, str]]) -> float | None:
    """Cohens Kappa für zwei Kodierer. None, wenn nicht berechenbar."""
    if not paare:
        return None
    n = len(paare)
    beobachtet = sum(a == b for a, b in paare) / n
    links, rechts = Counter(a for a, _ in paare), Counter(b for _, b in paare)
    erwartet = sum(links[k] * rechts[k] for k in links) / (n * n)
    return None if erwartet == 1 else round((beobachtet - erwartet) / (1 - erwartet), 2)


def _korrektur_stufe(n: int) -> str:
    return "6+" if n >= 6 else str(n)


def uebereinstimmung(auswahl: list[dict], antworten: dict[str, dict[str, list[str]]]) -> dict:
    """auswahl in der Reihenfolge des Bogens (K01 = auswahl[0])."""
    felder = {"kategorie": [], "ergebnis": [], "automatisierbar": [], "korrekturen": []}
    korrektur_nah, arten = [], []
    for i, a in enumerate(auswahl, 1):
        lia = antworten.get(f"K{i:02d}", {})
        for feld in ("kategorie", "ergebnis", "automatisierbar"):
            if lia.get(feld):
                felder[feld].append((a[feld], lia[feld][0]))
        if lia.get("korrekturen"):
            claude_n = len(a["korrekturen"])
            felder["korrekturen"].append((_korrektur_stufe(claude_n), lia["korrekturen"][0]))
            lia_n = 6 if lia["korrekturen"][0] == "6+" else int(lia["korrekturen"][0])
            korrektur_nah.append(abs(claude_n - lia_n) <= 1)
        c_arten, l_arten = {k["art"] for k in a["korrekturen"]}, set(lia.get("korrekturarten", []))
        if c_arten or l_arten:
            arten.append(len(c_arten & l_arten) / len(c_arten | l_arten))
    aus = {feld: {"n": len(p), "gleich": round(sum(x == y for x, y in p) / len(p), 2) if p else None,
                  "kappa": kappa(p)} for feld, p in felder.items()}
    aus["korrekturen"]["hoechstens_1_daneben"] = round(sum(korrektur_nah) / len(korrektur_nah), 2) if korrektur_nah else None
    aus["korrekturarten_jaccard"] = round(sum(arten) / len(arten), 2) if arten else None
    aus["unterschiede_kategorie"] = [f"K{i:02d}: Claude {a['kategorie']}, Lia {antworten[f'K{i:02d}']['kategorie'][0]}"
                                     for i, a in enumerate(auswahl, 1)
                                     if antworten.get(f"K{i:02d}", {}).get("kategorie")
                                     and antworten[f"K{i:02d}"]["kategorie"][0] != a["kategorie"]]
    return aus


def normalisieren(text: str) -> str:
    """Gleiche Optik für alt und neu: Markdown-Zeichen und Reste aus claude.ai entfernen, damit nichts verrät,
    welche Fassung welche ist."""
    text = re.sub(r"```\s*This block is not supported on your current device yet\.\s*```", "", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"\*\*|__|`", "", text)
    text = re.sub(r"(?<!\w)\*(?!\s)|(?<!\s)\*(?!\w)", "", text)
    text = re.sub(r"^\s*[-*•]\s+", "- ", text, flags=re.M)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def paare(satz: list[dict], neu: dict[str, str], seed: int = 8) -> tuple[list[dict], dict[str, str]]:
    """Für jeden Prüfsatz-Eintrag mit neuem Ergebnis: Eintrag für den Bogen und Schlüssel {id: 'alt'|'neu' für A}."""
    rnd = random.Random(seed)
    eintraege, schluessel = [], {}
    for e in satz:
        if e["id"] not in neu:
            continue
        a_ist_alt = rnd.random() < 0.5
        alt, ne = normalisieren(e["altes_ergebnis"]), normalisieren(neu[e["id"]])
        texte = (alt, ne) if a_ist_alt else (ne, alt)
        schluessel[e["id"]] = "alt" if a_ist_alt else "neu"
        kriterien = {f"k{j}": k for j, k in enumerate(e["kriterien"], 1)}
        felder = [{"name": "besser", "frage": "Welche Fassung ist besser für deinen Unterricht?",
                   "optionen": {"A": "A", "B": "B", "gleich": "gleich gut"}}]
        for seite in ("A", "B"):
            felder.append({"name": f"nutzbar_{seite}", "frage": f"Würdest du Fassung {seite} so verwenden?",
                           "optionen": {"ja": "ja, so", "aenderung": "mit kleinen Änderungen", "nein": "nein"}})
        if kriterien:
            for seite in ("A", "B"):
                felder.append({"name": f"kriterien_{seite}", "mehrfach": True, "optionen": kriterien,
                               "frage": f"Welche deiner früheren Wünsche erfüllt Fassung {seite}? (mehrere möglich)"})
        eintraege.append({"id": e["id"], "titel": f"{e['id']}: {e['titel']}", "abschnitte": [
            ("Dein Auftrag", e["auftrag"] + ("\n\nVorher im Chat: " + " / ".join(e["kontext"]) if e["kontext"] else "")),
            ("Fassung A", texte[0]), ("Fassung B", texte[1])], "felder": felder})
    return eintraege, schluessel


def vergleich_auswerten(antworten: dict[str, dict[str, list[str]]], schluessel: dict[str, str],
                        satz: list[dict]) -> dict:
    """Ergebnis aus Sicht von neu (lia/unterricht) gegen alt."""
    besser, nutzbar = Counter(), {"neu": Counter(), "alt": Counter()}
    kriterien = {"neu": [0, 0], "alt": [0, 0]}  # erfüllt, möglich
    anzahl_kriterien = {e["id"]: len(e["kriterien"]) for e in satz}
    for pid, a_ist in schluessel.items():
        lia = antworten.get(pid, {})
        if not lia:
            continue  # nicht bewertet: zählt auch bei den Kriterien nicht mit
        seite = {"A": a_ist, "B": "neu" if a_ist == "alt" else "alt"}
        if lia.get("besser"):
            besser[seite.get(lia["besser"][0], "gleich")] += 1
        for s in ("A", "B"):
            if lia.get(f"nutzbar_{s}"):
                nutzbar[seite[s]][lia[f"nutzbar_{s}"][0]] += 1
            if anzahl_kriterien.get(pid):
                kriterien[seite[s]][0] += len(lia.get(f"kriterien_{s}", []))
                kriterien[seite[s]][1] += anzahl_kriterien[pid]
    return {"bewertet": sum(besser.values()), "besser": dict(besser),
            "nutzbar": {k: dict(v) for k, v in nutzbar.items()},
            "kriterien_erfuellt": {k: round(v[0] / v[1], 2) if v[1] else None for k, v in kriterien.items()}}
