"""Feedback-Dienst: arbeitet die Aufträge an den Agenten "feedback" ab (CLAUDE.md, "Lernen aus Feedback").

Zwei Arten von Aufträgen (Logik in agentkit.feedback):
- Feedback zu einem Ergebnis (quelle "feedback", bezug = Ergebnis-Auftrag): Claude ordnet zu, Python prüft,
  übernimmt (Regel/Notiz eintragen und committen, Nachbesserung als Auftrag) oder macht einen Vorschlag.
  Jan bekommt eine Meldung mit Knopf, die Person die Bestätigung als Ergebnis dieses Auftrags.
- Jans Klick auf diese Meldung (Feld meldung, nur in Jans Instanz): Stopp/Rückgängig nimmt zurück,
  Übernehmen/Verwerfen entscheidet einen Vorschlag. Der Fall kann in einer anderen Instanz liegen (Lia),
  der Index data/meldungen.json sagt, wo.

Dienste: feedback.service (Jans Instanz) und lia-feedback.service (AGENTKIT_INSTANZ=lia/instanz), Vorlagen in
systemd/. Die Zentralen starten sie nach jedem neuen Auftrag an "feedback".
Daten: data/<instanz>/ (Arbeitsordner für claude -p), data/meldungen.json (Index), logs/feedback.log.

Start: [AGENTKIT_INSTANZ=...] .venv/bin/python lauf.py
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agentkit import auftraege, claude_lauf, config, log, meldungen, regeln, verbrauch
from agentkit import feedback as fb

HIER = Path(__file__).resolve().parent
REPO = HIER.parent.parent
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
JAN = config.KONTINGENT_DIR  # Jans shared-Ordner: dort landen die Meldungen an Jan
INDEX = fb.Index(HIER / "data" / "meldungen.json")
logger = log.hole_logger(HIER, "feedback")
STOPP = (fb.KNOPF_STOPP, "Rückgängig")
STAND_TEXT = {"uebernommen": "übernommen", "gestoppt": "gestoppt", "verworfen": "verworfen"}


@dataclass(frozen=True)
class Ort:
    """Eine Instanz: Warteschlangen in instanz/, Agenten daneben."""
    instanz: Path

    @property
    def auftraege(self) -> Path:
        return self.instanz / "auftraege"

    @property
    def agenten_dir(self) -> Path:
        return self.instanz.parent

    @property
    def ist_jan(self) -> bool:
        return self.instanz == JAN

    def dienst(self, agent: str) -> str:
        return agent if self.ist_jan else f"{self.instanz.parent.name}-{agent}"

    def person(self) -> str:
        return config.person(self.instanz)


HIERHER = Ort(config.SHARED_DIR)


# ---------- Handeln (dünn) ----------

def commit(pfad: Path, nachricht: str) -> str | None:
    """Committet genau diese Datei (der Hook prüft das ganze Repo). Gibt bei Fehler den Grund zurück."""
    pfad = Path(pfad)
    if not pfad.is_relative_to(REPO):
        return None  # außerhalb des Repos (z. B. Nachweis-Instanz): nichts zu committen
    # Der Hook prüft das Repo mit pruefen.sh: ohne AGENTKIT_INSTANZ, sonst liefen die Tests in Lias Instanz
    umgebung = {k: v for k, v in os.environ.items() if k != "AGENTKIT_INSTANZ"}
    p = subprocess.run(["git", "-C", str(REPO), "commit", "-q", "-m", nachricht + "\n\n(Feedback-Dienst)", "--", str(pfad)],
                       capture_output=True, text=True, timeout=600, env=umgebung)
    if p.returncode == 0:
        logger.info("Commit %s: %s", pfad.relative_to(REPO), nachricht)
        return None
    grund = (p.stdout + p.stderr).strip().splitlines()[-5:]
    logger.error("Commit von %s fehlgeschlagen: %s", pfad, " | ".join(grund))
    return " ".join(grund)


def starten(dienst: str) -> None:
    p = subprocess.run(["systemctl", "--user", "start", "--no-block", f"{dienst}.service"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        logger.error("Start von %s.service fehlgeschlagen: %s", dienst, p.stderr.strip())


def jan_melden(text: str, knoepfe: list[list[str]] | None = None) -> str:
    return meldungen.melden(fb.AGENT, text, knoepfe=knoepfe, dienst=fb.AGENT if knoepfe else None,
                            basis=JAN / "meldungen", agenten_dir=JAN.parent)


def person_melden(ort: Ort, text: str) -> None:
    """Nachricht an die Person der Instanz. Jan erfährt es schon über das Ergebnis seines Klicks."""
    if not ort.ist_jan:
        meldungen.melden(fb.AGENT, text, basis=ort.instanz / "meldungen", agenten_dir=ort.agenten_dir)


# ---------- Feedback zu einem Ergebnis ----------

def anwenden(ort: Ort, fid: str, z: dict, ziel: tuple[Path, str] | None, alt: dict) -> tuple[str | None, str | None]:
    """Übernimmt die Zuordnung. Gibt (geschriebene Zeile, ID der Nachbesserung) zurück."""
    if z["art"] in ("regel", "notiz"):
        text = z["regel"] if z["art"] == "regel" else fb.notiz_text(z, ort.person(), alt["agent"])
        zeile = regeln.zeile_eintragen(ziel[0], ziel[1], text, fid)
        logger.info("Feedback %s: %s eingetragen in %s", fid, z["art"], ziel[0])
        if grund := commit(ziel[0], f"Feedback {fid}: {'Regel' if z['art'] == 'regel' else 'Notiz'} übernommen"):
            logger.error("Feedback %s: Commit von %s fehlgeschlagen: %s", fid, ziel[0], grund)
            jan_melden("Ein Feedback gilt jetzt, ist aber nicht gesichert. Einzelheiten am PC.")
        return zeile, None
    if z["art"] == "nachbesserung":
        nb = auftraege.neuer_auftrag(alt["agent"], fb.nachbesserung_text(z, alt), quelle=alt.get("quelle") or "telegram",
                                     modus=alt.get("modus") or "erledigen", bezug=alt["id"], sitzung=alt.get("sitzung"),
                                     basis=ort.auftraege, agenten_dir=ort.agenten_dir)
        logger.info("Feedback %s: Nachbesserung %s an %s", fid, nb, alt["agent"])
        starten(ort.dienst(alt["agent"]))
        return None, nb
    return None, None


def nachbesserungen_bisher(ort: Ort, bezug: str) -> int:
    return sum(1 for a in auftraege.erledigte(fb.AGENT, basis=ort.auftraege)
               if (a.get("daten") or {}).get("bezug") == bezug and (a.get("daten") or {}).get("nachbesserung")
               and a["daten"].get("stand") == "uebernommen")


def feedback_bearbeiten(ort: Ort, a: dict, laufen=claude_lauf.laufen) -> None:
    fid = a["id"]
    try:
        alt = auftraege.erledigter(a.get("bezug") or "", basis=ort.auftraege)
    except auftraege.AuftragFehler:
        logger.warning("Feedback %s: Ergebnis %s nicht gefunden", fid, a.get("bezug"))
        auftraege.abschliessen(fid, "Zu welchem Ergebnis das gehört, finde ich nicht mehr. Schreib es bitte noch einmal.",
                               "fehlgeschlagen", basis=ort.auftraege)
        return
    agent, person = alt["agent"], ort.person()
    agenten_liste = fb.agenten(ort.agenten_dir)
    e = laufen(fb.AGENT, HIER / "data" / (config.INSTANZ_NAME or "jan"),
               fb.prompt(person, agent, alt, a["text"], regeln.regeln_als_text(ort.agenten_dir / agent), agenten_liste),
               art="routine", auftrag_id=fid)
    try:
        z = fb.zuordnung_lesen(e.text if e.ok else "", agenten_liste)
    except fb.FeedbackFehler as f:
        logger.error("Feedback %s nicht zugeordnet: %s (Antwort: %s)", fid, f, fb.kurz(e.text, 300))
        jan_melden(f"Feedback von {person} zu {fb.agent_name(agent)}: „{fb.kurz(a['text'], 300)}“\n"
                   "Damit wusste ich nichts anzufangen. Sieh es dir bitte selbst an.")
        auftraege.abschliessen(fid, "Danke, ist angekommen. Jan schaut es sich an.", basis=ort.auftraege)
        return
    lage = fb.Lage(nachbesserungen_bisher(ort, alt["id"]), verbrauch.kosten(alt["id"]),
                   (UNIT_DIR / f"{ort.dienst(agent)}.service").exists(), grenzen=ort.ist_jan)
    ok, grund = fb.entscheiden(z, lage)
    ziel = fb.ziel_datei(z, ort.instanz, ort.agenten_dir, REPO)
    zeile, nb = anwenden(ort, fid, z, ziel, alt) if ok else (None, None)
    fall = fb.fall(fid, alt["id"], agent, a["text"], z, ok, grund, ziel, zeile, nb, ort.instanz)
    text, knoepfe = fb.zusammenfassung(person, agent, a["text"], z, ok, grund)
    if ok and z["art"] == "keine":
        knoepfe = []  # nichts zurückzunehmen
    elif ort.ist_jan and ok:
        knoepfe = [["Rückgängig"]]
    mid = jan_melden(text, knoepfe)
    if knoepfe:
        INDEX.merken(mid, ort.instanz, fid)
    fall["meldung"] = mid
    auftraege.abschliessen(fid, fb.bestaetigung(z, ok), daten=fall, basis=ort.auftraege)
    logger.info("Feedback %s: %s, %s, Ziel %s, Kosten %s, Meldung %s", fid, z["art"],
                "übernommen" if ok else f"Vorschlag ({grund})", ziel[0] if ziel else "-", lage.kosten_usd, mid)


# ---------- Jans Klick ----------

def stoppen(ort: Ort, fall: dict) -> tuple[str, str]:
    """Nimmt einen übernommenen Fall zurück. Gibt (Text für Jan, Text für die Person) zurück."""
    art, fid = fall["zuordnung"]["art"], fall["feedback_id"]
    if art in ("regel", "notiz"):
        n = regeln.zeilen_entfernen(Path(fall["datei"]), fid)
        fuer_person = "Das gilt also nicht mehr." if art == "regel" else "Der Wunsch ist nicht mehr notiert."
        if not n:
            return "Es stand schon nicht mehr drin.", fuer_person
        if grund := commit(Path(fall["datei"]), f"Feedback {fid}: zurückgenommen (Jans Stopp)"):
            logger.error("Feedback %s: Commit der Rücknahme fehlgeschlagen: %s", fid, grund)
            return "Es ist gestrichen, aber nicht gesichert. Einzelheiten am PC.", fuer_person
        return "Es ist wieder gestrichen.", fuer_person
    if art == "nachbesserung":
        try:
            auftraege.abschliessen(fall["nachbesserung"], "Von Jan gestoppt.", "zurueckgezogen", basis=ort.auftraege)
            return "Die überarbeitete Fassung kommt nicht.", "Die neue Fassung kommt also nicht."
        except auftraege.AuftragFehler:
            return "Die überarbeitete Fassung war schon fertig und ist zugestellt.", "Die neue Fassung bleibt, wie sie ist."
    return "Es war nichts übernommen.", "Es ändert sich nichts."


def knopf_bearbeiten(a: dict) -> None:
    """Jans Klick auf eine Feedback-Meldung (läuft in Jans Instanz)."""
    eintrag = INDEX.finden(a.get("meldung") or "")
    if eintrag is None:
        logger.warning("Klick %s: kein Feedback-Fall zur Meldung %s", a["id"], a.get("meldung"))
        auftraege.abschliessen(a["id"], "Zu dieser Meldung finde ich nichts mehr. Einzelheiten am PC.", "fehlgeschlagen")
        return
    ort, fid = Ort(Path(eintrag["instanz"])), eintrag["feedback_id"]
    fall = auftraege.erledigter(fid, basis=ort.auftraege)["daten"]
    aktion = a["text"].strip()
    if a.get("quelle") != "knopf":
        antwort = "Bitte einen der Knöpfe unter der Meldung nutzen."
    elif aktion in STOPP and fall["stand"] == "uebernommen":
        fuer_jan, fuer_person = stoppen(ort, fall)
        fall["stand"] = "gestoppt"
        person_melden(ort, fb.stopp_text(fall, fuer_person))
        antwort = f"Gestoppt. {fuer_jan}" + ("" if ort.ist_jan else f" {ort.person()} weiß Bescheid.")
    elif aktion == fb.KNOPF_UEBERNEHMEN and fall["stand"] == "vorschlag":
        alt = auftraege.erledigter(fall["bezug"], basis=ort.auftraege)
        ziel = (Path(fall["datei"]), fall["abschnitt"]) if fall["datei"] else None
        fall["zeile"], fall["nachbesserung"] = anwenden(ort, fid, fall["zuordnung"], ziel, alt)
        fall["stand"] = "uebernommen"
        person_melden(ort, fb.entscheidung_text(fall, True))
        antwort = "Übernommen." + ("" if ort.ist_jan else f" {ort.person()} weiß Bescheid.")
    elif aktion == fb.KNOPF_VERWERFEN and fall["stand"] == "vorschlag":
        fall["stand"] = "verworfen"
        person_melden(ort, fb.entscheidung_text(fall, False))
        antwort = "Verworfen." + ("" if ort.ist_jan else f" {ort.person()} weiß Bescheid.")
    else:
        antwort = f"Das ist schon entschieden: {STAND_TEXT.get(fall['stand'], fall['stand'])}."
    auftraege.daten_setzen(fid, fall, basis=ort.auftraege)
    logger.info("Klick %r auf Feedback %s: %s", aktion, fid, antwort)
    auftraege.abschliessen(a["id"], antwort)


def main() -> None:
    for a in auftraege.neue(fb.AGENT):
        try:
            if a.get("meldung"):
                knopf_bearbeiten(a)
            else:
                feedback_bearbeiten(HIERHER, a)
        except (claude_lauf.LimitErreicht, claude_lauf.KeinPlatz, claude_lauf.LaeuftSchon) as f:
            logger.warning("Feedback %s wartet: %s", a["id"], f)  # bleibt in neu/, nächster Start
            break
        except Exception:
            logger.exception("Feedback %s: unerwarteter Fehler", a["id"])
            jan_melden("Ein Feedback hat nicht geklappt. Einzelheiten am PC.")
            try:
                auftraege.abschliessen(a["id"], "Das hat leider nicht geklappt. Jan weiß Bescheid.", "fehlgeschlagen")
            except auftraege.AuftragFehler:
                pass  # schon abgeschlossen, der Fehler kam danach


if __name__ == "__main__":
    main()
