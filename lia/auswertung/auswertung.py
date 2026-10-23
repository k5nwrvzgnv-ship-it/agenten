"""Auswertung von Lias claude.ai-Chats: Welche wiederkehrenden Aufgaben lohnen sich für ihre Agenten?

Werkzeug, das Jan von Hand startet (kein Dienst, kein Timer). Rohdaten nur in data/ (ablage.py).
Aufruf: .venv/bin/python auswertung.py <befehl>
  entpacken <zip>… je ZIP nach data/export/<name>/ entpacken, danach die ZIP-Datei löschen
  struktur         Feldnamen, Typen, Anzahlen des Exports (ohne Inhalte), auch nach data/struktur.txt
  chatliste        Vorschlag, welche Chats Lias sind, nach data/chatliste.tsv (nur Titel)
  filtern <projekt-uuid>…  bestätigte Chats und diese Projekte nach data/lia/, übrige Chats und Projekte löschen
  anonymisieren    data/lia/chats.json aufbereiten, Namen aus data/namen.json ersetzen -> data/lia/anonym.json
  einordnen [n]    Aufgaben einteilen und einordnen lassen (Sonnet), nur die ersten n Pakete -> data/einordnung/
  statistik        Pakete zusammenführen, Kennzahlen je Kategorie und Korrekturen -> data/ergebnis/
  ergebnisse       Rangliste, Beispiele je Typ, Prüfsatz -> data/ergebnis/
  kodierbogen [n]  Bogen für Lia mit n Aufgaben (Standard 25) -> data/pruefung/kodierbogen.html
  kodierung <csv>  Lias Antworten mit Claudes Einordnung vergleichen
  vergleichsbogen <ordner>  Blindvergleich aus <ordner>/P01.txt … (neue Ergebnisse von lia/unterricht)
  vergleich <csv>  Lias Blindvergleich auswerten
Ohne Befehl wird nur data/ angelegt. Plan und weitere Schritte in STATUS.md.
"""

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

import ablage
import anonym
import auswahl
import einordnen
import export
import pruefsatz
import pruefung
import rangliste
import statistik

HIER = ablage.HIER
EXPORT = ablage.DATEN / "export"
LIA = ablage.DATEN / "lia"


def main(argumente: list[str]) -> int:
    ablage.datenordner()
    befehl = argumente[0] if argumente else ""
    if befehl == "entpacken" and len(argumente) >= 2:
        # Der Export kommt als mehrere ZIPs (conversations-000.zip, projects-000.zip, ...), je eins in einen Unterordner
        for zip_pfad in map(Path, argumente[1:]):
            ziel = EXPORT / zip_pfad.stem
            if ziel.exists() and any(ziel.iterdir()):
                print(f"{ziel} ist nicht leer, {zip_pfad.name} übersprungen. Erst prüfen und von Hand leeren.")
                continue
            dateien = export.entpacken(zip_pfad, ziel)
            zip_pfad.unlink()
            print(f"{len(dateien)} Dateien nach {ziel} entpackt, {zip_pfad.name} gelöscht.")
        return 0
    if befehl == "struktur":
        text = export.bericht(EXPORT)
        ablage.schreiben(ablage.DATEN / "struktur.txt", text)
        print(text)
        return 0
    if befehl == "chatliste":
        ziel = ablage.DATEN / "chatliste.tsv"
        if ziel.exists():
            print(f"{ziel} gibt es schon (vielleicht mit Korrekturen). Erst von Hand umbenennen.")
            return 1
        quellen = sorted(EXPORT.rglob("conversations*.json"))  # Aufbau des neuen Exports noch ungeprüft
        if len(quellen) != 1:
            print(f"Erwartet genau eine conversations*.json unter {EXPORT}, gefunden: {len(quellen)}")
            return 1
        gespraeche = json.loads(quellen[0].read_text(encoding="utf-8"))
        tsv = auswahl.chatliste(gespraeche)
        ablage.schreiben(ziel, tsv)
        anzahl = Counter(z.rsplit("\t", 1)[1] for z in tsv.splitlines()[1:])
        print(f"{ziel}: {sum(anzahl.values())} Chats, Vorschlag {dict(anzahl)}. Spalte wer korrigieren.")
        return 0
    if befehl == "anonymisieren":
        namen = json.loads((ablage.DATEN / "namen.json").read_text(encoding="utf-8"))
        ersetzer = anonym.Ersetzer(namen)
        chats = anonym.aufbereiten(json.loads((LIA / "chats.json").read_text(encoding="utf-8")))
        ergebnis = ersetzer.alles(chats)
        ablage.schreiben(LIA / "anonym.json", json.dumps(ergebnis, ensure_ascii=False, indent=1))
        ablage.schreiben(LIA / "zuordnung.json", json.dumps(ersetzer.zuordnung, ensure_ascii=False, indent=1))
        reste = anonym.reste(ergebnis, namen)
        print(f"{len(ergebnis)} Chats nach {LIA / 'anonym.json'}, {sum(ersetzer.treffer.values())} Namen ersetzt.")
        print("Reste aus der Namensliste:", reste or "keine")
        return 1 if reste else 0
    if befehl == "einordnen":
        nur = int(argumente[1]) if len(argumente) > 1 else None
        return einordnen_befehl(nur)
    if befehl == "statistik":
        return statistik_befehl()
    if befehl == "ergebnisse":
        return ergebnisse_befehl()
    if befehl in ("kodierbogen", "kodierung", "vergleichsbogen", "vergleich"):
        return pruefung_befehl(befehl, argumente[1:])
    if befehl == "filtern":
        return filtern_befehl(argumente[1:])
    if befehl:
        print(__doc__)
        return 1
    print(f"Datenordner bereit: {ablage.DATEN} (chmod 700)")
    return 0


def filtern_befehl(projekt_uuids: list[str]) -> int:
    """Lias Chats und die genannten Projekte nach data/lia/, danach Export-Chats und -Projekte löschen."""
    lia = auswahl.bestaetigte_lia((ablage.DATEN / "chatliste.tsv").read_text(encoding="utf-8"))
    quelle = EXPORT / "conversations-000" / "conversations.json"
    chats = auswahl.filtern(json.loads(quelle.read_text(encoding="utf-8")), lia)
    projekte_dir = EXPORT / "projects-000" / "projects"
    projekte = [projekte_dir / f"{u}.json" for u in projekt_uuids]
    for p in projekte:
        if not p.is_file():
            print(f"Projekt fehlt: {p.name}")
            return 1
    ziel = ablage.datenordner(LIA)
    ablage.schreiben(ziel / "chats.json", json.dumps(chats, ensure_ascii=False))
    ablage.datenordner(ziel / "projekte")
    for p in projekte:
        ablage.schreiben_bytes(ziel / "projekte" / p.name, p.read_bytes())
    if len(json.loads((ziel / "chats.json").read_text(encoding="utf-8"))) != len(lia):
        print("Kontrolle fehlgeschlagen, nichts gelöscht.")
        return 1
    quelle.unlink()
    shutil.rmtree(projekte_dir)
    print(f"{len(chats)} Chats und {len(projekte)} Projekte nach {ziel}. Übrige Chats und Projekte gelöscht.")
    return 0


def einordnen_befehl(nur: int | None) -> int:
    """Pakete nacheinander über claude_lauf (Sonnet, art routine) einordnen. Fertige Pakete werden übersprungen.

    Aufruf mit AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz, damit der Verbrauch bei Lia zählt.
    """
    from agentkit import claude_lauf, log  # erst hier: braucht die Instanz aus der Umgebung

    logger = log.hole_logger(HIER, "auswertung")
    chats = json.loads((LIA / "anonym.json").read_text(encoding="utf-8"))
    schema = (HIER / "schema.md").read_text(encoding="utf-8")
    pakete = einordnen.pakete(chats)
    ziel = ablage.datenordner(ablage.DATEN / "einordnung")
    gesamt_usd = 0.0
    for i, paket in enumerate(pakete[:nur] if nur else pakete, 1):
        datei = ziel / f"paket-{i:02d}.json"
        if datei.exists():
            continue
        try:
            e = claude_lauf.laufen("auswertung", HIER, einordnen.prompt(paket, schema), art="routine",
                                   auftrag_id=f"einordnung-{i:02d}")
            usd, tokens = e.usd, e.tokens
            try:
                aufgaben = einordnen.lesen(e.text)
                fehler = einordnen.pruefen(aufgaben, paket)
            except ValueError as f:
                aufgaben, fehler = [], [str(f)]
            if fehler:
                logger.warning("Paket %s: %d Fehler, eine Nachbesserung", i, len(fehler))
                e = claude_lauf.laufen("auswertung", HIER, "Deine Antwort hat diese Fehler:\n- " + "\n- ".join(fehler)
                                       + "\nAntworte noch einmal mit dem vollständigen, korrigierten JSON-Array.",
                                       art="routine", auftrag_id=f"einordnung-{i:02d}", sitzung_fortsetzen=e.sitzung)
                usd, tokens = usd + e.usd, tokens + e.tokens
                aufgaben = einordnen.lesen(e.text)
                fehler = einordnen.pruefen(aufgaben, paket)
        except claude_lauf.LimitErreicht as f:
            print(f"Paket {i}: {f}. Später erneut aufrufen, fertige Pakete bleiben.")
            return 1
        gesamt_usd += usd
        ergebnis = {"paket": i, "ausschnitte": [{k: t[k] for k in ("chat", "von", "bis", "runden")} for t in paket],
                    "aufgaben": aufgaben, "fehler": fehler, "usd": usd, "tokens": tokens}
        ablage.schreiben(datei, json.dumps(ergebnis, ensure_ascii=False, indent=1))
        logger.info("Paket %s/%s: %d Aufgaben, %d Fehler, %.2f USD, %d Tokens", i, len(pakete), len(aufgaben),
                    len(fehler), usd, tokens)
        print(f"Paket {i}/{len(pakete)}: {len(aufgaben)} Aufgaben, {len(fehler)} Fehler, {usd:.2f} USD")
    print(f"Fertig, {gesamt_usd:.2f} USD in diesem Aufruf.")
    return 0


def statistik_befehl() -> int:
    """Pakete zusammenführen, Kennzahlen je Kategorie und Korrekturen nach data/ergebnis/."""
    aufgaben, grenzen, offen = [], {}, []
    for datei in sorted((ablage.DATEN / "einordnung").glob("paket-*.json")):
        p = json.loads(datei.read_text(encoding="utf-8"))
        if p["fehler"]:
            offen.append(datei.name)
        aufgaben += p["aufgaben"]
        for t in p["ausschnitte"]:
            if t["bis"] < t["runden"]:
                grenzen.setdefault(t["chat"], set()).add(t["bis"])
    aufgaben = einordnen.zusammenfuehren(aufgaben, grenzen)
    ziel = ablage.datenordner(ablage.DATEN / "ergebnis")
    kennzahlen = statistik.je_kategorie(aufgaben)
    for name, inhalt in (("aufgaben", aufgaben), ("kategorien", kennzahlen),
                         ("korrekturen", statistik.korrekturen(aufgaben))):
        ablage.schreiben(ziel / f"{name}.json", json.dumps(inhalt, ensure_ascii=False, indent=1))
    print(f"{len(aufgaben)} Aufgaben, Pakete mit Fehlern: {offen or 'keine'}")
    for kat, k in kennzahlen.items():
        print(f"{kat:14} {k['aufgaben']:3} Aufgaben, {k['runden_summe']:4} Runden, Median {k['runden_median']}, "
              f"{k['korrekturen_summe']:3} Korrekturen, auto {k['automatisierbar']}")
    return 1 if offen else 0


PRUEFSATZ_JE_TYP = {"ab_text_position": 4, "argumentieren_ueben": 3, "fallbeispiel": 3, "ab_bausteine": 3,
                    "zusammenfassung_stueck": 2, "theater_material": 2, "philosophie_und_quellen": 3,
                    "bewertungsbogen_und_noten": 2}


def ergebnisse_befehl() -> int:
    """Rangliste, Beispiele je Top-Typ und Prüfsatz nach data/ergebnis/ (alles anonymisiert)."""
    ziel = ablage.DATEN / "ergebnis"
    aufgaben = json.loads((ziel / "aufgaben.json").read_text(encoding="utf-8"))
    chats = {c["uuid"][:8]: c for c in json.loads((LIA / "anonym.json").read_text(encoding="utf-8"))}
    liste = rangliste.rangliste(aufgaben)
    ablage.schreiben(ziel / "rangliste.json", json.dumps(liste, ensure_ascii=False, indent=1))
    zeilen = ["# Beispiele je Aufgabentyp (anonymisiert)", ""]
    for z in liste[:10]:
        zeilen += [f"## {z['typ']} ({z['kategorie']}): {z['aufgaben']} Aufgaben, Wert {z['wert']}", ""]
        beispiele = sorted((a for a in aufgaben if rangliste.typ(a) == z["typ"]), key=lambda a: -len(a["korrekturen"]))
        for a in beispiele[:2]:
            runden = pruefsatz.runden_der_aufgabe(chats[a["chat"]], a)
            zeilen += [f"### {a['titel']} (Runden {a['von']}-{a['bis']}, {a['ergebnis']}, {a['automatisierbar']})",
                       "", "Auftrag: " + " ".join(runden[0]["prompt"].split())[:500] if runden else "", ""]
            zeilen += [f"- R{k['runde']} {k['art']}: {k.get('zitat', '')}" for k in a["korrekturen"]] + [""]
    ablage.schreiben(ziel / "beispiele.md", "\n".join(zeilen))
    satz = pruefsatz.auswaehlen(chats, aufgaben, PRUEFSATZ_JE_TYP)
    ablage.schreiben(ziel / "pruefsatz.json", json.dumps(satz, ensure_ascii=False, indent=1))
    print(f"Rangliste ({len(liste)} Typen), Beispiele, Prüfsatz ({len(satz)} Aufträge) in {ziel}")
    return 0


KODIER_EINLEITUNG = ("Hier stehen Ausschnitte aus deinen Chats mit Claude, Namen sind ersetzt. Lies jeden Ausschnitt "
                     "und beantworte die Fragen so, wie du die Aufgabe selbst siehst. Es gibt kein Richtig oder Falsch. "
                     "Am Ende auf „Antworten speichern“ tippen und die Datei an Jan schicken.")
VERGLEICH_EINLEITUNG = ("Zu jedem deiner früheren Aufträge gibt es zwei Fassungen, A und B. Eine ist dein damaliges "
                        "Ergebnis, die andere hat dein Agent neu erstellt. Welche welche ist, verrät der Bogen nicht. "
                        "Bewerte sie so, als würdest du sie morgen im Unterricht einsetzen. Am Ende „Antworten "
                        "speichern“ und die Datei an Jan schicken.")


def pruefung_befehl(befehl: str, argumente: list[str]) -> int:
    """Schritt 8: Kodierbogen und Blindvergleich erzeugen und auswerten (alles in data/pruefung/)."""
    ziel = ablage.datenordner(ablage.DATEN / "pruefung")
    ergebnis = ablage.DATEN / "ergebnis"
    if befehl == "kodierbogen":
        aufgaben = json.loads((ergebnis / "aufgaben.json").read_text(encoding="utf-8"))
        chats = {c["uuid"][:8]: c for c in json.loads((LIA / "anonym.json").read_text(encoding="utf-8"))}
        auswahl = pruefung.stichprobe(aufgaben, anzahl=int(argumente[0]) if argumente else 25)
        ablage.schreiben(ziel / "kodier_stichprobe.json", json.dumps(auswahl, ensure_ascii=False, indent=1))
        bogen = pruefung.formular_html("Deine Aufgaben einordnen", KODIER_EINLEITUNG,
                                       pruefung.kodier_eintraege(chats, auswahl), "kodierung-lia.csv")
        ablage.schreiben(ziel / "kodierbogen.html", bogen)
        print(f"{ziel / 'kodierbogen.html'}: {len(auswahl)} Aufgaben, Kategorien "
              f"{dict(Counter(a['kategorie'] for a in auswahl))}")
        return 0
    if befehl == "kodierung" and argumente:
        auswahl = json.loads((ziel / "kodier_stichprobe.json").read_text(encoding="utf-8"))
        antworten = pruefung.lies_antworten(Path(argumente[0]).read_text(encoding="utf-8"))
        u = pruefung.uebereinstimmung(auswahl, antworten)
        ablage.schreiben(ziel / "uebereinstimmung.json", json.dumps(u, ensure_ascii=False, indent=1))
        print(json.dumps(u, ensure_ascii=False, indent=1))
        return 0
    if befehl == "vergleichsbogen" and argumente:
        satz = json.loads((ergebnis / "pruefsatz.json").read_text(encoding="utf-8"))
        neu = {p.stem: p.read_text(encoding="utf-8") for p in Path(argumente[0]).glob("P*.txt")}
        eintraege, schluessel = pruefung.paare(satz, neu)
        ablage.schreiben(ziel / "vergleich_schluessel.json", json.dumps(schluessel, indent=1))
        ablage.schreiben(ziel / "vergleichsbogen.html", pruefung.formular_html(
            "Alt oder neu?", VERGLEICH_EINLEITUNG, eintraege, "vergleich-lia.csv"))
        print(f"{ziel / 'vergleichsbogen.html'}: {len(eintraege)} Paare, fehlend: "
              f"{[e['id'] for e in satz if e['id'] not in neu]}")
        return 0
    if befehl == "vergleich" and argumente:
        satz = json.loads((ergebnis / "pruefsatz.json").read_text(encoding="utf-8"))
        schluessel = json.loads((ziel / "vergleich_schluessel.json").read_text(encoding="utf-8"))
        antworten = pruefung.lies_antworten(Path(argumente[0]).read_text(encoding="utf-8"))
        v = pruefung.vergleich_auswerten(antworten, schluessel, satz)
        ablage.schreiben(ziel / "vergleich.json", json.dumps(v, ensure_ascii=False, indent=1))
        print(json.dumps(v, ensure_ascii=False, indent=1))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
