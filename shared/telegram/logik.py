"""Reine Logik der Telegram-Zentrale (ohne Telegram), damit sie testbar ist."""

import json
from pathlib import Path

AGENTEN = ("uni", "dokumente", "posteingang", "einkauf")
MAX_LAENGE = 3800  # Telegram erlaubt 4096 Zeichen pro Nachricht, etwas Puffer


def befehl_auswerten(text: str) -> tuple[str, str, str] | None:
    """'/uni Kapitel 3' -> ('uni', 'erledigen', 'Kapitel 3'), '/unilern ...' -> lernen.

    Gibt None zurück, wenn der Befehl keinem Agenten gehört.
    """
    kopf, _, rest = text.strip().partition(" ")
    befehl = kopf.lstrip("/").split("@", 1)[0].lower()
    modus = "erledigen"
    if befehl.endswith("lern"):
        befehl, modus = befehl[: -len("lern")], "lernen"
    if befehl not in AGENTEN:
        return None
    return befehl, modus, rest.strip()


def entwurf_als_text(entwurf: dict) -> list[str]:
    """Entwurf so darstellen, dass Jan alles sieht, was ausgeführt wird.

    Lange Inhalte werden auf mehrere Nachrichten verteilt (nichts abschneiden,
    denn freigegeben wird genau das, was angezeigt wurde).
    """
    kopf = f"Entwurf von {entwurf['agent']} ({entwurf['typ']})\n{entwurf['titel']}"
    if entwurf.get("vorgaenger"):
        kopf += "\n(überarbeitete Fassung)"
    teile = [kopf, entwurf["inhalt"]]
    if entwurf.get("daten"):
        teile.append("Details:\n" + json.dumps(entwurf["daten"], ensure_ascii=False, indent=2))
    return aufteilen("\n\n".join(teile))


def aufteilen(text: str, max_laenge: int = MAX_LAENGE) -> list[str]:
    stuecke = []
    while len(text) > max_laenge:
        schnitt = text.rfind("\n", 0, max_laenge)
        if schnitt <= 0:
            schnitt = max_laenge
        stuecke.append(text[:schnitt])
        text = text[schnitt:].lstrip("\n")
    stuecke.append(text)
    return stuecke


class Gemeldet:
    """Merkt sich, was Jan schon gezeigt wurde (data/gemeldet.json), damit nichts doppelt kommt.

    angezeigt: Entwurfs-ID -> Fingerabdruck zum Zeitpunkt der Anzeige.
    """

    LISTEN = ("ausgefuehrt", "unklar", "auftraege")

    def __init__(self, pfad: Path):
        self.pfad = pfad
        daten = json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else {}
        self.angezeigt: dict[str, str] = daten.get("angezeigt", {})
        self.listen: dict[str, set[str]] = {n: set(daten.get(n, [])) for n in self.LISTEN}

    def speichern(self) -> None:
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        daten = {"angezeigt": self.angezeigt, **{n: sorted(v) for n, v in self.listen.items()}}
        tmp = self.pfad.with_suffix(".tmp")
        tmp.write_text(json.dumps(daten, indent=2), encoding="utf-8")
        tmp.replace(self.pfad)
