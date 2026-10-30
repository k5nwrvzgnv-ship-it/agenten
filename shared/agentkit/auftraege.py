"""Auftrags-Warteschlange: shared/auftraege/neu/ und erledigt/.

Die Telegram-Zentrale legt hier Jans Aufträge und Korrekturen ab und startet
danach den Dienst des Agenten. Der Agent holt seine Aufträge, bearbeitet sie
und schließt sie ab. Stürzt er vorher ab, bleibt der Auftrag in neu/ und wird
beim nächsten Lauf wieder geholt.

Modus (gilt für alle Agenten, Standard ist "erledigen"):
- erledigen: Der Agent arbeitet allein und liefert danach ein verständliches
  Protokoll (was er getan hat, Quellen, Unsicherheiten, wie Jan es prüfen kann).
- lernen: Der Agent geht den Auftrag Schritt für Schritt gemeinsam mit Jan
  durch (erklären, Fragen stellen, Rückmeldung geben), per Telegram oder im
  Claude-Code-Chat am PC.

Gespräch: Ein abgeschlossener Auftrag trägt die Claude-Sitzung seines Laufs
(Feld sitzung). Antwortet Jan in Telegram auf die Meldung, legt die Zentrale
einen neuen Auftrag mit bezug=<alter Auftrag> und derselben sitzung an, und der
Agent setzt diese Sitzung fort statt neu anzufangen.

Dateien: Schickt Jan Dateien mit, verschiebt neuer_auftrag(..., dateien=) sie nach
<agent>/data/eingang/<auftrag-id>/ (dort darf Claude lesen, nicht im Repo). Die Pfade
stehen im Feld dateien und zusätzlich am Ende des Auftragstexts, damit jeder Agent
sie ohne eigenen Code im Prompt hat.
Umgekehrt gibt abschliessen(..., dateien=) Ergebnisdateien aus dem Agent-Ordner mit,
die Zentrale schickt sie Jan nach dem Ergebnistext.

Weitergabe: Ein Agent gibt einem anderen einen Auftrag mit weitergeben(von, an, ...).
Erlaubt ist nur, was in [weitergabe] in einstellungen.toml steht. Dateien werden kopiert
(der Absender behält seine), der Auftrag trägt von=<Absender> und aus_auftrag=<Auftrag,
aus dem die Weitergabe kommt>. Ein weitergegebener Auftrag darf nicht weitergegeben werden,
damit sich Agenten nicht im Kreis beauftragen. Die Zentrale meldet Jan jede Weitergabe und
startet den Empfänger; das Ergebnis geht wie jedes an Jan.

Rückfragen per Meldung (siehe meldungen): Klick oder Antwort auf eine Meldung wird ein
Auftrag mit meldung=<Meldungs-ID> und dienst=<Dienst der Meldung>. Jeder Dienst holt
nur seine Aufträge: neue(agent, dienst=None) die ohne Dienst (<agent>.service),
neue(agent, dienst="uni-lernen") nur die für uni-lernen. Ohne Angabe kommen alle.

Zurückziehen (Jan 30.10.2026): zurueckziehen(id) schließt einen offenen Auftrag mit Status zurueckgezogen ab, auch
während der Agent daran arbeitet. claude_lauf bricht einen laufenden Lauf dazu ab (Zurueckgezogen), und ein
späteres abschliessen() des Agenten ändert nichts mehr und wirft nicht.
"""

import re
import shutil
from pathlib import Path

from . import _ablage, einstellungen, ereignis
from ._ablage import AblageFehler as AuftragFehler  # noqa: F401
from .config import SHARED_DIR, person

BASIS = SHARED_DIR / "auftraege"
AGENTEN_DIR = SHARED_DIR.parent
EINGANG = Path("data") / "eingang"
ABSCHLUESSE = ("erledigt", "fehlgeschlagen", "zurueckgezogen")  # zurueckgezogen: Jans Stopp, wird nicht gemeldet
MODI = ("erledigen", "lernen")
REIHE_MUSTER = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
ALLE = "*"  # neue(..., dienst=ALLE): Aufträge aller Dienste


def neuer_auftrag(
    agent: str,
    text: str,
    quelle: str = "telegram",
    modus: str = "erledigen",
    bezug: str | None = None,
    sitzung: str | None = None,
    dateien: list[Path] | None = None,
    meldung: str | None = None,
    dienst: str | None = None,
    basis: Path | None = None,
    agenten_dir: Path | None = None,
    absender: str | None = None,
    reihe: str | None = None,
    kopieren: bool = False,
) -> str:
    """Legt einen Auftrag an und gibt seine ID zurück.

    bezug: ID eines Entwurfs (Korrektur) oder Auftrags (Antwort darauf).
    sitzung: Claude-Sitzung, die der Agent fortsetzen soll.
    dateien: werden in den Agent-Ordner verschoben (siehe oben).
    meldung, dienst: Antwort auf eine Meldung (siehe oben).
    absender: Name im Satz über angehängte Dateien; Standard config.person() der eigenen Instanz. Für Programme,
    die mit basis= für eine andere Instanz anlegen (Web-App für Lia).
    reihe: Kennung einer Unterrichtsreihe (Web-App für Lia, Kleinbuchstaben, Ziffern, Bindestriche). Das Feld
    steht nur im Auftrag, wenn es gesetzt ist.
    kopieren: dateien kopieren statt verschieben (z. B. Lias eigene Fassung, die in agentkit.fassungen bleibt).
    """
    if modus not in MODI:
        raise AuftragFehler(f"Unbekannter Modus: {modus!r}")
    if bezug is not None:
        _ablage.pruefe_id(bezug)
    if meldung is not None:
        _ablage.pruefe_id(meldung)
    _ablage.pruefe_dienst(agent, dienst)
    if reihe is not None and not REIHE_MUSTER.fullmatch(reihe):
        raise AuftragFehler(f"Ungültige Reihe: {reihe!r}")
    felder = {"quelle": quelle, "modus": modus, "bezug": bezug, "sitzung": sitzung, "meldung": meldung,
              "dienst": dienst, **({"reihe": reihe} if reihe is not None else {})}
    return _anlegen(agent, text, felder, dateien or [], shutil.copy2 if kopieren else shutil.move,
                    absender or person(), basis, agenten_dir)


def weitergeben(
    von: str,
    an: str,
    text: str,
    aus_auftrag: str | None,
    dateien: list[Path] | None = None,
    cfg: dict | None = None,
    basis: Path | None = None,
    agenten_dir: Path | None = None,
) -> str:
    """Auftrag von Agent von an Agent an, gibt seine ID zurück.

    aus_auftrag: Auftrag, den von gerade bearbeitet (None bei Läufen ohne Auftrag, z. B. Timer).
    dateien: im Ordner von (absolut oder relativ dazu), werden in den Ordner von an kopiert.
    """
    _ablage.pruefe_agent(von)
    _ablage.pruefe_agent(an)
    if not einstellungen.weitergabe_erlaubt(einstellungen.lade() if cfg is None else cfg, von, an):
        raise AuftragFehler(f"Weitergabe {von} -> {an} ist nicht erlaubt (einstellungen.toml, [weitergabe])")
    basis = basis or BASIS
    if aus_auftrag is not None:
        herkunft = _finden(aus_auftrag, basis)
        if herkunft.get("von"):
            raise AuftragFehler(f"{aus_auftrag} kam von {herkunft['von']}, weitergegebene Aufträge "
                                "werden nicht weitergegeben")
    agenten_dir = agenten_dir or AGENTEN_DIR
    quellen = [agenten_dir / von / p for p in _ablage.anhaenge_pruefen(agenten_dir / von, dateien or [])]
    felder = {"quelle": f"agent:{von}", "modus": "erledigen", "bezug": None, "sitzung": None, "meldung": None,
              "dienst": None, "von": von, "aus_auftrag": aus_auftrag}
    return _anlegen(an, text, felder, quellen, shutil.copy2, von, basis, agenten_dir)


def _anlegen(agent: str, text: str, felder: dict, dateien: list[Path], ablegen, absender: str,
             basis: Path | None, agenten_dir: Path | None) -> str:
    basis = basis or BASIS
    eintrag_id = _ablage.neue_id(agent)
    anhaenge = _dateien_ablegen((agenten_dir or AGENTEN_DIR) / agent, eintrag_id, dateien, ablegen)
    if anhaenge:
        text += f"\n\nAngehängte Dateien von {absender} (im Agent-Ordner):\n" + "\n".join(f"- {p}" for p in anhaenge)
    eintrag = {
        "id": eintrag_id,
        "agent": agent,
        "text": text,
        "von": None,
        "aus_auftrag": None,
        **felder,
        "dateien": anhaenge,
        "erstellt": _ablage.jetzt(),
        "status": "neu",
        "abgeschlossen": None,
        "ergebnis": "",
    }
    _ablage.schreibe(_ablage.ordner(basis, "neu") / f"{eintrag_id}.json", eintrag)
    ereignis.schreiben("auftrag.angelegt", agent, auftrag=eintrag_id, ordner=ereignis.ordner_zu(basis), daten={
        "quelle": eintrag.get("quelle"), "modus": eintrag.get("modus"), "von": eintrag.get("von"),
        "bezug": eintrag.get("bezug"), "dienst": eintrag.get("dienst"), "dateien": len(anhaenge)})
    return eintrag_id


def _finden(eintrag_id: str, basis: Path) -> dict:
    """Offener oder abgeschlossener Auftrag per ID."""
    _ablage.pruefe_id(eintrag_id)
    for name in ("neu", "erledigt"):
        pfad = _ablage.ordner(basis, name) / f"{eintrag_id}.json"
        if pfad.exists():
            return _ablage.lies(pfad)
    raise AuftragFehler(f"Auftrag {eintrag_id} nicht gefunden")


def _dateien_ablegen(agent_dir: Path, eintrag_id: str, dateien: list[Path], ablegen=shutil.move) -> list[str]:
    """Verschiebt (oder kopiert, ablegen=shutil.copy2) die Dateien nach <agent>/data/eingang/<id>/.

    Gibt Pfade relativ zum Agent-Ordner zurück."""
    if not dateien:
        return []
    if not agent_dir.is_dir():
        raise AuftragFehler(f"Agent-Ordner fehlt: {agent_dir}")
    ziel = agent_dir / EINGANG / eintrag_id
    ziel.mkdir(parents=True)
    pfade = []
    for quelle in map(Path, dateien):
        pfad, n = ziel / quelle.name, 2
        while pfad.exists():  # gleicher Name zweimal: nichts überschreiben
            pfad, n = ziel / f"{quelle.stem}-{n}{quelle.suffix}", n + 1
        ablegen(quelle, pfad)
        pfade.append(str(pfad.relative_to(agent_dir)))
    return pfade


def neue(agent: str | None = None, basis: Path | None = None, dienst: str | None = ALLE) -> list[dict]:
    """Offene Aufträge, älteste zuerst. dienst: siehe oben."""
    eintraege = _ablage.liste(_ablage.ordner(basis or BASIS, "neu"), agent)
    if dienst == ALLE:
        return eintraege
    return [a for a in eintraege if a.get("dienst") == dienst]


def erledigte(agent: str | None = None, basis: Path | None = None) -> list[dict]:
    return _ablage.liste(_ablage.ordner(basis or BASIS, "erledigt"), agent)


def erledigter(eintrag_id: str, basis: Path | None = None) -> dict:
    """Ein abgeschlossener Auftrag per ID (z. B. der, auf den Jan antwortet)."""
    _ablage.pruefe_id(eintrag_id)
    pfad = _ablage.ordner(basis or BASIS, "erledigt") / f"{eintrag_id}.json"
    if not pfad.exists():
        raise AuftragFehler(f"{eintrag_id} ist nicht abgeschlossen")
    return _ablage.lies(pfad)


def zurueckgezogen(eintrag_id: str, basis: Path | None = None) -> bool:
    """Wurde der Auftrag zurückgezogen? (claude_lauf fragt das während eines Laufs.)"""
    _ablage.pruefe_id(eintrag_id)
    pfad = _ablage.ordner(basis or BASIS, "erledigt") / f"{eintrag_id}.json"
    try:
        return _ablage.lies(pfad).get("status") == "zurueckgezogen"
    except (FileNotFoundError, ValueError):
        return False


def zurueckziehen(eintrag_id: str, grund: str = "", basis: Path | None = None) -> dict:
    """Offenen Auftrag (neu oder laufend) zurückziehen, z. B. auf Lias Wunsch in der Web-App. Ein laufender
    claude-Lauf dazu endet binnen weniger Sekunden. Schon erledigt oder fehlgeschlagen: AuftragFehler;
    zweimal zurückziehen schadet nicht."""
    return abschliessen(eintrag_id, grund, "zurueckgezogen", basis=basis)


def daten_setzen(eintrag_id: str, daten: dict, basis: Path | None = None) -> dict:
    """Feld daten eines abgeschlossenen Auftrags ersetzen (z. B. Stand eines Feedback-Falls nach Jans Stopp)."""
    eintrag = erledigter(eintrag_id, basis)
    eintrag["daten"] = daten
    _ablage.schreibe(_ablage.ordner(basis or BASIS, "erledigt") / f"{eintrag_id}.json", eintrag)
    return eintrag


def abschliessen(
    eintrag_id: str,
    ergebnis: str = "",
    status: str = "erledigt",
    sitzung: str | None = None,
    dateien: list[Path] | None = None,
    basis: Path | None = None,
    agenten_dir: Path | None = None,
    daten: dict | None = None,
) -> dict:
    """Verschiebt den Auftrag nach erledigt/ (status siehe ABSCHLUESSE).

    sitzung: Claude-Sitzung des Laufs, damit Jan per Antwort darin weitermachen kann.
    dateien: Ergebnisdateien im Agent-Ordner (absolut oder relativ dazu), gehen an Jan.
    daten: strukturierter Teil des Ergebnisses für die Vorlagen der Zentralen (Feld daten), z. B.
    {"kern": "1-2 Sätze", "punkte": [...], "pruefen": "...", "belege": [...]}, siehe shared/telegram/vorlagen.py.
    "knoepfe": "nur_antwort" wählt die Feedback-Knöpfe unter diesem Ergebnis ab (Antwort genügt).
    Feedback speichert hier seine Zuordnung.
    Wurde der Auftrag inzwischen zurückgezogen, bleibt er so und wird unverändert zurückgegeben.
    """
    if status not in ABSCHLUESSE:
        raise AuftragFehler(f"Unbekannter Abschluss: {status!r}")
    _ablage.pruefe_id(eintrag_id)
    agent = eintrag_id.split("-")[2]  # vor dem Verschieben prüfen, sonst bliebe der Auftrag halb abgeschlossen
    ergebnis_dateien = _ablage.anhaenge_pruefen((agenten_dir or AGENTEN_DIR) / agent, dateien or [])
    eigene_basis, basis = basis, basis or BASIS
    try:
        eintrag = _ablage.abschliessen(
            _ablage.ordner(basis, "neu"),
            _ablage.ordner(basis, "erledigt"),
            eintrag_id,
            {"status": status, "abgeschlossen": _ablage.jetzt(), "ergebnis": ergebnis, "sitzung": sitzung,
             "ergebnis_dateien": ergebnis_dateien, **({"daten": daten} if daten is not None else {})},
        )
    except AuftragFehler:
        if zurueckgezogen(eintrag_id, basis):  # Agent kommt nach dem Zurückziehen: nichts ändern, nicht abstürzen
            return erledigter(eintrag_id, basis)
        raise
    ereignis.schreiben("auftrag.abgeschlossen", agent, auftrag=eintrag_id, ordner=ereignis.ordner_zu(eigene_basis),
                       daten={"status": status, "dateien": len(ergebnis_dateien)})
    return eintrag
