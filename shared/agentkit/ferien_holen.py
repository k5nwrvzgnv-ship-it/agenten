"""Ferien und Feiertage aller 16 Bundesländer einmal je Schuljahr holen und in ferien.json schreiben (F20, Jans
Okay 03.11.2026). Von Hand starten, kein Timer, kein Dienst:

    cd ~/agenten/shared && python3 -m agentkit.ferien_holen [2027/28]

Ohne Angabe das laufende Schuljahr. Geholt wird der 01.01. des ersten bis 31.12. des zweiten Jahres, danach liegt
ferien.json im Repo (git diff zeigt, was sich geändert hat; committen wie jede Änderung).

Quelle: OpenHolidays API (https://www.openholidaysapi.org), kostenlos, ohne Schlüssel, Abfragen höchstens drei
Jahre. Daten unter Open Database License (ODbL 1.0, https://opendatacommons.org/licenses/odbl/1-0/): Quelle nennen;
wer eine abgeleitete Datenbank veröffentlicht, gibt sie unter derselben Lizenz weiter. Sie stammen laut Projekt aus
der Ferienregelung der KMK, den Ferienordnungen der Länder und den Feiertagsgesetzen. Drei Anfragen je Lauf
(Schulferien, Feiertage, Schularten), über agentkit.abruf (nur https, nur diese Domain).

Rückfall von Hand (F20 a): Einträge im gleichen Format in ferien.json ergänzen und den Zeitraum unter "abgedeckt"
mit "quelle": "von Hand (KMK)" eintragen. Ein späterer Abruf ersetzt im abgerufenen Zeitraum alles.

Umwandlung (rein, getestet in umwandeln und einfuegen):
- Nur Einträge, die für das ganze Land gelten, zählen in agentkit.termine. Ausnahmen (z. B. Sommerferien der Inseln
  in SH) und örtliche Feiertage (z. B. Friedensfest Augsburg) bekommen "nur" mit dem Hinweis bzw. dem Gebiet.
- Ferien nur für eine Schulart (MV: allgemeinbildende und berufliche Schulen) bekommen "schulart".
"""

import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from . import abruf, termine

API = "https://openholidaysapi.org"
ALLOWLIST = ["openholidaysapi.org"]
QUELLE = ("OpenHolidays API (https://www.openholidaysapi.org), Daten unter ODbL 1.0 "
          "(https://opendatacommons.org/licenses/odbl/1-0/)")
HINWEIS = ("Ferien und Feiertage je Bundesland für agentkit.termine. Holen: python3 -m agentkit.ferien_holen "
           "[2027/28]. Von Hand ergänzen: gleiches Format, Zeitraum unter abgedeckt mit quelle \"von Hand (KMK)\". "
           "Einträge mit nur gelten nicht im ganzen Land und zählen nicht, schulart nur für diese Schulart.")


def _name(eintrag: dict) -> str:
    namen = eintrag.get("name") or []
    for n in namen:
        if n.get("language") == "DE":
            return n["text"]
    return namen[0]["text"] if namen else ""


def _gebiete(eintrag: dict) -> list[tuple[str, str]]:
    """(Land, Gebiet) je Eintrag; Gebiet ist leer, wenn das ganze Land gemeint ist (z. B. DE-BY-AU -> ("BY",
    "DE-BY-AU"))."""
    if eintrag.get("nationwide"):
        return [(land, "") for land in termine.BUNDESLAENDER]
    paare = []
    for s in eintrag.get("subdivisions") or []:
        teile = s.get("code", "").split("-")
        if len(teile) >= 2 and teile[0] == "DE" and teile[1] in termine.BUNDESLAENDER:
            paare.append((teile[1], s["code"] if len(teile) > 2 else ""))
    return paare


def umwandeln(schulferien: list, feiertage: list, schularten: list) -> dict[str, dict]:
    """Antworten der API -> {Land: {"ferien": [...], "feiertage": [...]}} für alle 16 Länder, sortiert."""
    arten = {g["code"]: _name(g) for g in schularten}
    laender = {land: {"ferien": [], "feiertage": []} for land in termine.BUNDESLAENDER}
    for art, liste in (("ferien", schulferien), ("feiertage", feiertage)):
        for x in liste:
            nur_halb = "halber Tag" if x.get("temporalScope", "FullDay") != "FullDay" else ""
            kommentar = _name({"name": x.get("comment") or []})
            ausnahme = kommentar or ("Ausnahme" if "Exception" in (x.get("tags") or []) else "")
            gruppen = [arten.get(g["code"], g["code"]) for g in x.get("groups") or []]
            for land, gebiet in _gebiete(x):
                e = {"name": _name(x)}
                if art == "ferien":
                    e.update(von=x["startDate"], bis=x["endDate"])
                else:
                    e["datum"] = x["startDate"]
                nur = ", ".join(t for t in (ausnahme, gebiet, nur_halb) if t)
                if nur:
                    e["nur"] = nur
                if not gruppen:
                    laender[land][art].append(e)
                for g in gruppen:
                    laender[land][art].append({**e, "schulart": g})
    for eintrag in laender.values():
        for art, schluessel in (("ferien", "von"), ("feiertage", "datum")):
            eintrag[art] = sorted({json.dumps(e, sort_keys=True): e for e in eintrag[art]}.values(),
                                  key=lambda e: (e[schluessel], e["name"], e.get("schulart", ""), e.get("nur", "")))
    return laender


def einfuegen(alt: dict, neu: dict[str, dict], von: str, bis: str, abgerufen: str, quelle: str = QUELLE) -> dict:
    """Neuen Abruf für [von, bis] in den Inhalt von ferien.json einfügen: Einträge, die den Zeitraum berühren, werden
    ersetzt, alles andere bleibt. Gibt den neuen Inhalt zurück, ändert alt nicht."""
    def beruehrt(e):
        a, b = (e["datum"], e["datum"]) if "datum" in e else (e["von"], e["bis"])
        return a <= bis and b >= von

    laender = {land: {k: [dict(e) for e in v] for k, v in eintrag.items()}
               for land, eintrag in (alt.get("laender") or {}).items()}
    for land, eintrag in neu.items():
        ziel = laender.setdefault(land, {})
        for art, schluessel in (("ferien", "von"), ("feiertage", "datum")):
            behalten = [e for e in ziel.get(art, []) if not beruehrt(e)]
            ziel[art] = sorted(behalten + eintrag[art], key=lambda e: (e[schluessel], e["name"]))
        ziel["abgedeckt"] = sorted([a for a in ziel.get("abgedeckt", []) if not (von <= a["von"] and a["bis"] <= bis)]
                                   + [{"von": von, "bis": bis, "quelle": quelle, "abgerufen": abgerufen}],
                                   key=lambda a: a["von"])
        laender[land] = {k: ziel[k] for k in ("abgedeckt", "ferien", "feiertage")}
    return {"hinweis": HINWEIS, "quelle": QUELLE, "laender": dict(sorted(laender.items()))}


def als_text(daten: dict) -> str:
    """JSON mit einem Eintrag je Zeile (lesbare Diffs)."""
    zeilen = ["{", f' "hinweis": {json.dumps(daten["hinweis"], ensure_ascii=False)},',
              f' "quelle": {json.dumps(daten["quelle"], ensure_ascii=False)},', ' "laender": {']
    laender = list(daten["laender"].items())
    for i, (land, eintrag) in enumerate(laender):
        zeilen.append(f'  "{land}": {{')
        arten = list(eintrag.items())
        for j, (art, liste) in enumerate(arten):
            zeilen.append(f'   "{art}": [')
            zeilen += [f"    {json.dumps(e, ensure_ascii=False)}" + ("," if k < len(liste) - 1 else "")
                       for k, e in enumerate(liste)]
            zeilen.append("   ]" + ("," if j < len(arten) - 1 else ""))
        zeilen.append("  }" + ("," if i < len(laender) - 1 else ""))
    return "\n".join(zeilen + [" }", "}"]) + "\n"


def zeitraum(schuljahr: str | None, heute: date) -> tuple[str, str, str]:
    """(Schuljahr, von, bis): 01.01. des ersten bis 31.12. des zweiten Jahres. Ohne Angabe: ab August das
    beginnende Schuljahr, sonst das laufende."""
    if schuljahr is None:
        jahr = heute.year if heute.month >= 8 else heute.year - 1
        schuljahr = f"{jahr}/{(jahr + 1) % 100:02d}"
    teile = schuljahr.split("/")
    if len(teile) != 2 or not teile[0].isdigit() or len(teile[0]) != 4 or teile[1] != f"{(int(teile[0]) + 1) % 100:02d}":
        raise termine.TermineFehler(f"Schuljahr {schuljahr!r} wie \"2026/27\" schreiben")
    jahr = int(teile[0])
    return schuljahr, f"{jahr}-01-01", f"{jahr + 1}-12-31"


def _holen(pfad: str, parameter: dict, cache: Path) -> list:
    url = f"{API}/{pfad}?{urlencode(parameter)}"
    erg = abruf.laden(url, ALLOWLIST, cache, neu=True)
    try:
        daten = json.loads(erg.inhalt.decode("utf-8"))
    except ValueError as e:
        raise abruf.AbrufFehler(f"Antwort von {url} ist kein JSON: {e}") from None
    if not isinstance(daten, list):
        raise abruf.AbrufFehler(f"Antwort von {url} ist keine Liste")
    return daten


def main(argumente: list[str], datei: Path = termine.FERIEN_DATEI) -> int:
    try:
        schuljahr, von, bis = zeitraum(argumente[0] if argumente else None, date.today())
    except termine.TermineFehler as e:
        print(e, file=sys.stderr)
        return 2
    basis = {"countryIsoCode": "DE", "languageIsoCode": "DE"}
    with tempfile.TemporaryDirectory() as cache:
        try:
            ferien = _holen("SchoolHolidays", {**basis, "validFrom": von, "validTo": bis}, Path(cache))
            feiertage = _holen("PublicHolidays", {**basis, "validFrom": von, "validTo": bis}, Path(cache))
            arten = _holen("Groups", basis, Path(cache))
        except abruf.AbrufFehler as e:
            print(f"Abruf fehlgeschlagen, {datei.name} bleibt unverändert: {e}", file=sys.stderr)
            return 1
    alt = json.loads(datei.read_text(encoding="utf-8")) if datei.exists() else {}
    neu = einfuegen(alt, umwandeln(ferien, feiertage, arten), von, bis, date.today().isoformat())
    fehler = termine.ferien_pruefen(neu)
    if fehler:
        print("Ergebnis ungültig, nichts geschrieben:\n" + "\n".join(fehler), file=sys.stderr)
        return 1
    tmp = datei.with_name(f".{datei.name}.tmp")
    tmp.write_text(als_text(neu), encoding="utf-8")
    tmp.replace(datei)
    print(f"{datei} geschrieben: Schuljahr {schuljahr} ({von} bis {bis}), {len(ferien)} Ferieneinträge, "
          f"{len(feiertage)} Feiertage. Bitte mit git diff prüfen und committen.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
