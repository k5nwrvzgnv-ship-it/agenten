"""Mündliche Übungen: Transkript annehmen, Warteschlange, Laufstand, Rubrik, Karten übernehmen. Ohne Netz, ohne Claude.

Gemeinsam für den Web-Dienst (app.py) und den Agenten (auswertung_agent.py).

Ablage je Übung in data/lernen/<modul>/uebungen/<id>/ (nicht im Repo):
  transkript.txt    das Transkript als Text
  stand.json        Laufstand, Titel, Messwerte
  auswertung.json   geprüftes Ergebnis (bewertung.py)
  kartenstand.json  welche Vorschläge Jan schon übernommen hat

Warteschlange in portal/data/: warteschlange/<id>.json startet den Agenten (Pfad-Unit uni-portal-frage.path), geparkt/
hält Aufträge, die bei knappem Kontingent warten, bis Jan sie anstößt. geparkt/ beobachtet systemd nicht: Es startet
nichts von selbst, und eine liegen gebliebene Datei kann den Dienst nicht im Kreis starten.

Karten: Übernehmen hängt nur an karten.json an. Vorhandene Karten, zustand.json und verlauf.jsonl bleiben unberührt.
Fällige Karten kommen nach vorgemerkt.json und erscheinen beim Üben zuerst, ihr FSRS-Stand ändert sich erst, wenn Jan
sie bewertet.
"""

import hashlib
import json
import os
import secrets
from datetime import datetime
from pathlib import Path

import ablage
import lernmodell

ENDUNGEN = (".txt", ".md", ".json")
MAX_BYTES = 512 * 1024
MIN_ZEICHEN = 200
# Das Transkript geht im Prompt mit, und der Prompt ist ein Argument von claude -p. Linux erlaubt je Argument 128 KiB
# (bewertung.MAX_PROMPT_BYTES). 60.000 Zeichen sind etwa 60 Minuten Gespräch.
MAX_ZEICHEN = 60_000
MAX_TITEL = 100
WARTESCHLANGE = "warteschlange"
GEPARKT = "geparkt"
STAENDE = {"wartet": "wartet", "laeuft": "läuft", "fertig": "fertig", "fehlgeschlagen": "fehlgeschlagen"}
ROLLEN = {"agent": "Prüferin", "user": "Prüfling"}
ABGEBROCHEN = "Der Lauf wurde abgebrochen, ohne ein Ergebnis zu schreiben."


class UploadFehler(ValueError):
    """Text für Jan, warum das Transkript nicht angenommen wurde."""


def _json_als_text(text: str) -> str:
    """Bekannte Form {"transcript": [{"role", "message"}]} oder die Liste allein, sonst UploadFehler. Das Exportformat
    von ElevenLabs ist am Web-Export noch ungeprüft; diese Form stammt aus deren API-Dokumentation."""
    try:
        daten = json.loads(text)
    except json.JSONDecodeError:
        raise UploadFehler("Die JSON-Datei ist nicht lesbar. Füge das Transkript als Text ein.") from None
    zuege = daten.get("transcript") if isinstance(daten, dict) else daten
    if not isinstance(zuege, list):
        raise UploadFehler("Diese JSON-Form kenne ich nicht. Füge das Transkript als Text ein.")
    zeilen = []
    for zug in zuege:
        if not isinstance(zug, dict):
            raise UploadFehler("Diese JSON-Form kenne ich nicht. Füge das Transkript als Text ein.")
        nachricht = zug.get("message") or zug.get("text")
        if isinstance(nachricht, str) and nachricht.strip():
            rolle = str(zug.get("role") or zug.get("speaker") or "?")
            zeilen.append(f"{ROLLEN.get(rolle, rolle)}: {nachricht.strip()}")
    return "\n".join(zeilen)


def text_pruefen(text: str) -> str:
    """Eingefügter oder aus einer Datei gelesener Text: bereinigt und in den Grenzen, sonst UploadFehler."""
    if "\x00" in text:
        raise UploadFehler("Die Datei enthält keinen reinen Text.")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(text) < MIN_ZEICHEN:
        raise UploadFehler(f"Das Transkript ist zu kurz (mindestens {MIN_ZEICHEN} Zeichen).")
    if len(text) > MAX_ZEICHEN:
        raise UploadFehler(f"Das Transkript ist zu lang: {len(text)} Zeichen, höchstens {MAX_ZEICHEN}.")
    return text


def datei_lesen(name: str, roh: bytes) -> str:
    """Hochgeladene Datei zu Text. Nur die Endung zählt; der Inhalt muss UTF-8-Text sein und wird nie ausgeführt."""
    endung = Path(name or "").suffix.lower()
    if endung not in ENDUNGEN:
        raise UploadFehler(f"Erlaubt sind nur {', '.join(ENDUNGEN)}.")
    if len(roh) > MAX_BYTES:
        raise UploadFehler(f"Die Datei ist zu groß (höchstens {MAX_BYTES // 1024} KB).")
    try:
        text = roh.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UploadFehler("Die Datei ist kein UTF-8-Text.") from None
    return text_pruefen(_json_als_text(text) if endung == ".json" else text)


def titel_pruefen(titel: str | None) -> str:
    return " ".join((titel or "").split())[:MAX_TITEL]


def neue_id(jetzt: datetime) -> str:
    return f"{jetzt:%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


def _atomar(ziel: Path, daten: dict, tmp_ordner: Path) -> None:
    """Erst in tmp, dann umbenennen: Die Pfad-Unit sieht nie eine halbe Datei."""
    tmp_ordner.mkdir(mode=0o700, parents=True, exist_ok=True)
    ziel.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = tmp_ordner / ziel.name
    tmp.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, ziel)


def einreihen(daten: Path, modul: str, uebung_id: str, erzwingen: bool = False) -> None:
    """Auftrag für den Agenten. erzwingen: Jan will trotz knappem Kontingent starten."""
    _atomar(daten / WARTESCHLANGE / f"{uebung_id}.json", {"id": uebung_id, "modul": modul, "erzwingen": erzwingen},
            daten / "tmp")
    (daten / GEPARKT / f"{uebung_id}.json").unlink(missing_ok=True)


def in_schlange(daten: Path, uebung_id: str) -> bool:
    return (daten / WARTESCHLANGE / f"{uebung_id}.json").exists()


def ist_geparkt(daten: Path, uebung_id: str) -> bool:
    return (daten / GEPARKT / f"{uebung_id}.json").exists()


def parken(daten: Path, auftrag: dict) -> None:
    """Aus der Warteschlange nach geparkt/: bleibt sichtbar, startet aber nichts mehr."""
    _atomar(daten / GEPARKT / f"{auftrag['id']}.json", {"id": auftrag["id"], "modul": auftrag["modul"]}, daten / "tmp")
    (daten / WARTESCHLANGE / f"{auftrag['id']}.json").unlink(missing_ok=True)


def anlegen(modul_ordner: Path, daten: Path, modul: str, text: str, titel: str, jetzt: datetime) -> str:
    """Neue Übung ablegen und einreihen. Gibt die ID zurück."""
    uebung_id = neue_id(jetzt)
    wurzel = modul_ordner / ablage.UEBUNGEN_ORDNER
    wurzel.mkdir(mode=0o700, exist_ok=True)
    ordner = wurzel / uebung_id
    ordner.mkdir(mode=0o700)
    (ordner / ablage.TRANSKRIPT).write_text(text + "\n", encoding="utf-8")
    stand_schreiben(ordner, {"id": uebung_id, "modul": modul, "titel": titel, "stand": "wartet",
                             "grund": "In der Warteschlange.", "angelegt": jetzt.isoformat(timespec="seconds"),
                             "versuche": 0})
    einreihen(daten, modul, uebung_id)
    return uebung_id


def stand_lesen(ordner: Path) -> dict:
    return lernmodell.lies_json(Path(ordner) / ablage.STAND, {})


def stand_schreiben(ordner: Path, stand: dict) -> None:
    lernmodell.schreibe_json(Path(ordner) / ablage.STAND, stand)


def stand_aendern(ordner: Path, **felder) -> dict:
    stand = {**stand_lesen(ordner), **felder}
    stand_schreiben(ordner, stand)
    return stand


def stand_ansicht(stand: dict, daten: Path) -> dict:
    """Was die Seite zeigt. Steht "wartet" oder "läuft" da, aber der Auftrag ist nirgends mehr, ist der Lauf hart
    abgebrochen (Agent schreibt den Endstand vor dem Löschen des Auftrags)."""
    wert, grund = stand.get("stand"), stand.get("grund")
    uebung_id = stand.get("id", "")
    geparkt = ist_geparkt(daten, uebung_id)
    if wert in ("wartet", "laeuft") and not geparkt and not in_schlange(daten, uebung_id):
        wert, grund = "fehlgeschlagen", ABGEBROCHEN
    return {"wert": wert, "text": STAENDE.get(wert, "unbekannt"), "grund": grund, "geparkt": geparkt,
            "laeuft_noch": wert in ("wartet", "laeuft") and not geparkt,
            "neu_startbar": geparkt or wert == "fehlgeschlagen"}


def neu_einreihen(ordner: Path, daten: Path, modul: str, uebung_id: str, jetzt: datetime) -> bool:
    """Geparkte oder fehlgeschlagene Übung auf Jans Knopf neu starten. Sonst nichts tun."""
    stand = stand_lesen(ordner)
    if not stand_ansicht(stand, daten)["neu_startbar"]:
        return False
    stand_aendern(ordner, stand="wartet", grund="In der Warteschlange.", versuche=0,
                  aktualisiert=jetzt.isoformat(timespec="seconds"))
    einreihen(daten, modul, uebung_id, erzwingen=True)
    return True


# --- Rubrik -------------------------------------------------------------------------------------------------------

def rubrik_lesen(modul_ordner: Path) -> dict | None:
    return lernmodell.lies_json(Path(modul_ordner) / ablage.RUBRIK, None)


def rubrik_summe(rubrik: dict) -> str:
    """Prüfsumme der Punkte: Ändert sich eine Rubrik nach der Bestätigung, gilt sie wieder als unbestätigt."""
    inhalt = json.dumps(rubrik.get("punkte", []), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(inhalt.encode()).hexdigest()


def rubrik_bestaetigt(rubrik: dict | None) -> bool:
    return bool(rubrik) and (rubrik.get("bestaetigt") or {}).get("summe") == rubrik_summe(rubrik)


def rubrik_bestaetigen(modul_ordner: Path, jetzt: datetime) -> bool:
    rubrik = rubrik_lesen(modul_ordner)
    if not rubrik:
        return False
    rubrik["bestaetigt"] = {"zeit": jetzt.isoformat(timespec="seconds"), "summe": rubrik_summe(rubrik)}
    lernmodell.schreibe_json(Path(modul_ordner) / ablage.RUBRIK, rubrik)
    return True


def rubrik_hinweis(auswertung: dict | None, rubrik: dict | None) -> str | None:
    """Hinweis auf der Ergebnisseite; None, wenn die Auswertung auf der bestätigten Rubrik beruht."""
    if not auswertung:
        return None if rubrik_bestaetigt(rubrik) else "Rubrik noch nicht bestätigt"
    if rubrik and auswertung.get("rubrik_summe") != rubrik_summe(rubrik):
        return "Mit einer früheren Fassung der Rubrik ausgewertet"
    return None if rubrik_bestaetigt(rubrik) else "Rubrik noch nicht bestätigt"


# --- Karten -------------------------------------------------------------------------------------------------------

def karte_id(thema: str, frage: str, bild: str | None = None) -> str:
    """Wie karten.karte_id: fest aus Thema, Frage und Bild."""
    schluessel = frage.strip() + "|" + (bild or "")
    return f"{thema}-{hashlib.sha1(schluessel.encode()).hexdigest()[:8]}"


def kartenstand_lesen(ordner: Path) -> dict:
    return {"neu": {}, "faellig": {}, **lernmodell.lies_json(Path(ordner) / ablage.KARTENSTAND, {})}


def vorgemerkt_lesen(modul_ordner: Path) -> list[str]:
    return lernmodell.lies_json(Path(modul_ordner) / ablage.VORGEMERKT, [])


def vormerkung_entfernen(modul_ordner: Path, karte: str) -> None:
    liste = vorgemerkt_lesen(modul_ordner)
    if karte in liste:
        lernmodell.schreibe_json(Path(modul_ordner) / ablage.VORGEMERKT, [k for k in liste if k != karte])


def uebernehmen(modul_ordner: Path, ordner: Path, auswertung: dict, art: str, nummern: list[int] | None,
                jetzt: datetime) -> int:
    """Vorschläge auf Jans Bestätigung übernehmen. art "neu" oder "faellig", nummern None = alle offenen. Gibt die Zahl
    der übernommenen zurück. Ein Absturz mittendrin schadet nicht: Doppelte erkennt die Karten-ID."""
    feld = {"neu": "karten_neu", "faellig": "karten_faellig"}.get(art)
    if feld is None:
        return 0
    vorschlaege = auswertung.get(feld, [])
    stand = kartenstand_lesen(ordner)
    offen = [n for n in range(len(vorschlaege)) if str(n) not in stand[art]]
    gewaehlt = offen if nummern is None else [n for n in nummern if n in offen]
    if not gewaehlt:
        return 0
    zeit = jetzt.isoformat(timespec="seconds")
    if art == "neu":
        pfad = Path(modul_ordner) / "karten.json"
        alle = lernmodell.lies_json(pfad, [])
        ids = {k["id"] for k in alle}
        neu = []
        for n in gewaehlt:
            v = vorschlaege[n]
            kennung = karte_id(v["thema"], v["frage"])
            if kennung not in ids:
                ids.add(kennung)
                neu.append({"id": kennung, "thema": v["thema"], "typ": "text", "frage": v["frage"],
                            "antwort": v["antwort"], "quelle": v["quelle"], "bild": None,
                            "herkunft": f"uebung {auswertung.get('id', '')}"})
            stand["neu"][str(n)] = {"zeit": zeit, "karte": kennung}
        if neu:
            lernmodell.schreibe_json(pfad, alle + neu)
    else:
        liste = vorgemerkt_lesen(modul_ordner)
        for n in gewaehlt:
            kennung = vorschlaege[n]["karte"]
            if kennung not in liste:
                liste.append(kennung)
            stand["faellig"][str(n)] = {"zeit": zeit, "karte": kennung}
        lernmodell.schreibe_json(Path(modul_ordner) / ablage.VORGEMERKT, liste)
    lernmodell.schreibe_json(Path(ordner) / ablage.KARTENSTAND, stand)
    return len(gewaehlt)


def ergebnis_ansicht(auswertung: dict, kartenstand: dict, plan: dict, karten: dict) -> dict:
    """Ergebnisseite: Lücken nach Thema, wichtigste zuerst, Vorschläge mit ihrem Stand."""
    themen = {t["id"]: t for t in plan.get("themen", [])}
    gruppen: dict[str, list] = {}
    for luecke in auswertung.get("luecken", []):
        gruppen.setdefault(luecke["thema"], []).append(luecke)
    luecken = [{"titel": themen.get(i, {}).get("titel", i), "score": themen.get(i, {}).get("score", 0), "eintraege": e}
               for i, e in gruppen.items()]
    neu = [{**v, "nr": n, "titel": themen.get(v["thema"], {}).get("titel", v["thema"]),
            "uebernommen": str(n) in kartenstand["neu"]} for n, v in enumerate(auswertung.get("karten_neu", []))]
    faellig = [{**v, "nr": n, "frage": karten.get(v["karte"], {}).get("frage", v["karte"]),
                "vorhanden": v["karte"] in karten, "uebernommen": str(n) in kartenstand["faellig"]}
               for n, v in enumerate(auswertung.get("karten_faellig", []))]
    return {"luecken": sorted(luecken, key=lambda z: -z["score"]), "neu": neu, "faellig": faellig,
            "neu_offen": sum(1 for v in neu if not v["uebernommen"]),
            "faellig_offen": sum(1 for v in faellig if not v["uebernommen"] and v["vorhanden"])}
