"""Feedback zu Ergebnissen: Zuordnung, Prüfung, Wirkung, Rücknahme (CLAUDE.md, "Lernen aus Feedback").

Ablauf:
1. Die Zentrale legt einen Auftrag an den Agenten "feedback" an: text = Feedback, quelle "feedback",
   bezug = der Auftrag, dessen Ergebnis gemeint ist. Danach startet sie den Feedback-Dienst
   (feedback.service bzw. <instanz>-feedback.service, Code in shared/feedback/lauf.py).
2. Claude bekommt prompt() und antwortet mit JSON; zuordnung_lesen() prüft es. Arten:
   nachbesserung (neuer Auftrag an denselben Agenten), regel (dauerhaft), notiz (Wunsch an Code oder
   Oberfläche, nur Notiz in einer STATUS.md), keine (Lob, nichts zu tun).
3. entscheiden() wendet CLAUDE.md an: Was nie automatisch geht, wird ein Vorschlag an Jan.
4. Der Dienst setzt die Wirkung um (regeln.zeile_eintragen bzw. neuer Auftrag) und schließt den
   Feedback-Auftrag ab: ergebnis = bestaetigung() für die Person, daten = Fall (siehe fall()).
5. Jan bekommt zusammenfassung() als Meldung in seiner Instanz mit Knopf "Stopp" (bzw. "Übernehmen" /
   "Verwerfen" bei einem Vorschlag). Ein Klick wird ein Auftrag an "feedback" mit Feld meldung; der Dienst
   findet den Fall über den Index in shared/feedback/data/meldungen.json und nimmt ihn zurück.

Hier steht nur Logik ohne Netz, Claude und Git, damit sie testbar bleibt.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

AGENT = "feedback"
QUELLE = "feedback"
ARTEN = ("nachbesserung", "regel", "notiz", "keine")
OBERFLAECHE = "oberflaeche"  # Ziel einer Notiz zur Zentrale (Haupt-STATUS.md)
ALLE = "alle"  # Ziel einer Regel für alle Agenten der Instanz (<instanz>/regeln.md)
REGEL_ABSCHNITT_ALLE = "## Regeln"
REGEL_ABSCHNITT_AGENT = "## Gelernte Regeln"
NOTIZ_ABSCHNITT = "## Wünsche aus Feedback"
MAX_REGEL = 400
MAX_KOSTEN_USD = 1.0  # CLAUDE.md: teurere Nachbesserungen sind ein Vorschlag an Jan (nicht für Lia)
MAX_NACHBESSERUNGEN = 1  # je Ergebnis automatisch (nicht für Lia)
KNOPF_STOPP = "Stopp"
KNOPF_UEBERNEHMEN = "Übernehmen"
KNOPF_VERWERFEN = "Verwerfen"


class FeedbackFehler(Exception):
    pass


def agenten(agenten_dir: Path) -> list[str]:
    """Agenten einer Instanz: Unterordner mit STATUS.md (Jan: uni, dokumente; Lia: unterricht, recherche ...)."""
    return sorted(p.parent.name for p in Path(agenten_dir).glob("*/STATUS.md") if re.fullmatch(r"[a-z]+", p.parent.name))


def kurz(text: str, laenge: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


PROMPT = """Du ordnest Feedback zu einem Ergebnis eines Agenten zu. Du änderst nichts selbst, du antwortest nur mit JSON.

{person} hat dem Agenten „{agent}“ einen Auftrag gegeben und das Ergebnis bekommen. Dazu kam dieses Feedback.

# Auftrag (gekürzt)
{auftrag}

# Ergebnis (gekürzt)
{ergebnis}

# Feedback von {person}
{feedback}
{fassung}
# Regeln, die schon gelten
{regeln}

# Aufgabe
Ordne das Feedback genau einer Art zu:
- "nachbesserung": Es betrifft nur dieses Ergebnis. Schreib in "auftrag", was der Agent am Ergebnis ändern soll, als
  vollständigen Auftrag, den er ohne dieses Gespräch versteht.
- "regel": Es ist eine dauerhafte Vorliebe oder Regel für künftige Ergebnisse. Schreib sie in "regel" als eine Zeile im
  Stil der Regeln oben, allgemein formuliert, ohne Bezug auf dieses eine Ergebnis. "ziel": "{alle}" für alle Agenten
  von {person} oder der Name eines Agenten aus {agenten}, wenn sie nur für ihn gilt.
- "notiz": Es ist ein Wunsch an die Bedienung, die Telegram-Oberfläche oder die Fähigkeiten eines Agenten, den nur
  eine Programmänderung erfüllen kann. Schreib ihn in "notiz" als eine Zeile. "ziel": "{oberflaeche}" für die
  Telegram-Oberfläche, sonst der Agent aus {agenten}.
- "keine": Lob oder nichts zu tun.
Wenn es sowohl dieses Ergebnis als auch künftige betrifft, wähle "regel".

Setze "heikel": true, wenn das Feedback etwas berührt, das nie automatisch übernommen wird: Handeln nach außen
(Mails, Nachrichten, Abgaben, Käufe), Limits oder die Freigabe von Entwürfen; Schülerdaten oder Datenschutz; das
Löschen oder Ändern einer Regel, die schon gilt. Begründe kurz in "heikel_grund".
Widerspricht die neue Regel einer Regel oben, schreib die betroffene Regel in "widerspricht", sonst "".

Antworte nur mit diesem JSON, ohne weiteren Text:
{{"art": "...", "ziel": "...", "auftrag": "...", "regel": "...", "notiz": "...", "heikel": false,
"heikel_grund": "", "widerspricht": "", "zusammenfassung": "ein Satz für Jan: was {person} will"}}
Leere Felder als "". Schreib deutsch, kurz und klar.
"""


MAX_KOMMENTARE = 4000


def fassung_abschnitt(person: str, eigene: dict | None, kommentare: list[dict]) -> str:
    """Abschnitt im Prompt, wenn die Person eine eigene Fassung (Datei) mitgeschickt hat (agentkit.fassungen)."""
    if not eigene:
        return ""
    zeilen = [f"\n# Eigene Fassung von {person}",
              f"{person} hat dazu eine eigene Fassung hochgeladen ({eigene['name']}). Eine Nachbesserung baut auf ihr auf."]
    if eigene.get("notiz"):
        zeilen.append(f"Notiz: {eigene['notiz']}")
    if kommentare:
        zeilen.append("Kommentare darin (Stelle -> Kommentar), sie betreffen meist nur dieses Ergebnis:")
        zeilen += [f"- „{kurz(k['stelle'], 150)}“ -> {kurz(k['kommentar'], 400)}" if k["stelle"]
                   else f"- {kurz(k['kommentar'], 400)}" for k in kommentare]
    return kurz_zeilen("\n".join(zeilen), MAX_KOMMENTARE) + "\n"


def kurz_zeilen(text: str, laenge: int) -> str:
    """Wie kurz(), aber Zeilen bleiben erhalten."""
    return text if len(text) <= laenge else text[: laenge - 1] + "…"


def prompt(person: str, agent: str, auftrag: dict, feedback_text: str, regeln_text: str, agenten_liste: list[str],
           fassung: str = "") -> str:
    """fassung: fassung_abschnitt(), wenn eine eigene Fassung mitkam."""
    return PROMPT.format(
        person=person, agent=agent, auftrag=kurz(auftrag.get("text", ""), 1500),
        ergebnis=kurz(auftrag.get("ergebnis", ""), 3000) or "(kein Text, nur Dateien)",
        feedback=feedback_text.strip() or "(kein Text, nur die Datei unten)", fassung=fassung,
        regeln=regeln_text.strip() or "(keine)",
        alle=ALLE, oberflaeche=OBERFLAECHE, agenten=", ".join(agenten_liste) or "(keine)",
    )


def zuordnung_lesen(antwort: str, agenten_liste: list[str]) -> dict:
    """Claudes Antwort prüfen. Gibt die bereinigte Zuordnung zurück, sonst FeedbackFehler."""
    treffer = re.search(r"\{.*\}", antwort or "", re.DOTALL)
    if not treffer:
        raise FeedbackFehler("Keine JSON-Antwort")
    try:
        roh = json.loads(treffer.group(0))
    except json.JSONDecodeError as e:
        raise FeedbackFehler(f"JSON kaputt: {e}") from None
    if not isinstance(roh, dict):
        raise FeedbackFehler("JSON ist kein Objekt")
    z = {k: str(roh.get(k) or "").strip() for k in
         ("art", "ziel", "auftrag", "regel", "notiz", "heikel_grund", "widerspricht", "zusammenfassung")}
    z["heikel"] = roh.get("heikel") is True
    if z["art"] not in ARTEN:
        raise FeedbackFehler(f"Unbekannte Art: {z['art']!r}")
    if z["art"] == "nachbesserung" and not z["auftrag"]:
        raise FeedbackFehler("Nachbesserung ohne Auftrag")
    for feld, erlaubt in (("regel", [ALLE, *agenten_liste]), ("notiz", [OBERFLAECHE, *agenten_liste])):
        if z["art"] != feld:
            continue
        if not z[feld] or "\n" in z[feld] or len(z[feld]) > MAX_REGEL:
            raise FeedbackFehler(f"{feld} muss eine Zeile mit höchstens {MAX_REGEL} Zeichen sein")
        if z["ziel"] not in erlaubt:
            raise FeedbackFehler(f"Unbekanntes Ziel {z['ziel']!r} für {feld}")
    return z


@dataclass
class Lage:
    """Was entscheiden() über die Umgebung wissen muss (der Dienst ermittelt es)."""
    nachbesserungen_bisher: int = 0  # übernommene Nachbesserungen zum selben Ergebnis
    kosten_usd: float | None = None  # Kosten des ursprünglichen Laufs, None = unbekannt
    dienst_da: bool = False  # Agent hat einen Dienst, der den neuen Auftrag abholt
    grenzen: bool = True  # Kosten- und Anzahlgrenze für Nachbesserungen (Jan 30.10.: für Lia keine)


def entscheiden(z: dict, lage: Lage) -> tuple[bool, str]:
    """(übernehmen, Grund für einen Vorschlag an Jan). CLAUDE.md: was nie automatisch geht."""
    if z["heikel"]:
        return False, z["heikel_grund"] or "es berührt etwas, das ich nie von selbst übernehme"
    if z["art"] == "regel" and z["widerspricht"]:
        return False, f"es widerspricht dem, was schon gilt: „{kurz(z['widerspricht'], 200)}“"
    if z["art"] == "nachbesserung":
        if lage.grenzen and lage.nachbesserungen_bisher >= MAX_NACHBESSERUNGEN:
            return False, "zu diesem Ergebnis gab es schon eine überarbeitete Fassung"
        if lage.grenzen and lage.kosten_usd is None:
            return False, "ich weiß nicht, wie viel Rechenzeit das braucht"
        if lage.grenzen and lage.kosten_usd > MAX_KOSTEN_USD:
            return False, "das braucht mehr Rechenzeit, als ich allein freigeben darf"
        if not lage.dienst_da:
            return False, "der Agent ist noch nicht eingerichtet"
    return True, ""


def ziel_datei(z: dict, instanz_dir: Path, agenten_dir: Path, repo: Path) -> tuple[Path, str] | None:
    """Datei und Abschnitt für Regel oder Notiz, None bei Nachbesserung und keine."""
    if z["art"] == "regel":
        if z["ziel"] == ALLE:
            return Path(instanz_dir) / "regeln.md", REGEL_ABSCHNITT_ALLE
        return Path(agenten_dir) / z["ziel"] / "STATUS.md", REGEL_ABSCHNITT_AGENT
    if z["art"] == "notiz":
        if z["ziel"] == OBERFLAECHE:
            return Path(repo) / "STATUS.md", NOTIZ_ABSCHNITT
        return Path(agenten_dir) / z["ziel"] / "STATUS.md", NOTIZ_ABSCHNITT
    return None


def notiz_text(z: dict, person: str, agent: str) -> str:
    return f"{person} zu {agent}: {z['notiz']}"


def nachbesserung_text(z: dict, auftrag: dict, eigene: dict | None = None, person: str = "Lia") -> str:
    """eigene: Eintrag der eigenen Fassung (agentkit.fassungen), die als Datei am Auftrag hängt."""
    text = (f"Nachbesserung zu deinem Ergebnis für den Auftrag „{kurz(auftrag.get('text', ''), 200)}“ "
            f"(Auftrag {auftrag['id']}):\n\n{z['auftrag']}")
    if eigene:
        text += (f"\n\nGrundlage ist {person}s eigene Fassung {eigene['name']} (angehängt), nicht dein letztes "
                 f"Ergebnis. Übernimm ihre Änderungen, setze ihre Kommentare um und entferne die Kommentare.")
    return text


def agent_name(agent: str) -> str:
    """'recherche' -> 'Recherche' (Sprachregel: Agenten groß)."""
    return agent[:1].upper() + agent[1:]


def ziel_name(z: dict, person: str) -> str:
    """Für wen eine Regel oder Notiz gilt, in Worten."""
    if z["ziel"] == ALLE:
        return f"alles von {person}"
    if z["ziel"] == OBERFLAECHE:
        return "die Zentrale"
    return agent_name(z["ziel"])


def wirkung_fuer_person(z: dict) -> str:
    """Was das Feedback bewirkt, in Lias bzw. Jans Worten (ohne Dank)."""
    if z["art"] == "regel":
        return f"Ab jetzt gilt: „{z['regel']}“"
    if z["art"] == "nachbesserung":
        return "Ich mache das Ergebnis jetzt noch einmal. Es kommt dann hierher."
    if z["art"] == "notiz":
        return "Ich habe es notiert. Das kann ich noch nicht. Jan baut es ein."
    return ""


def bestaetigung(z: dict, uebernommen: bool) -> str:
    """Rückmeldung an die Person, die das Feedback gegeben hat."""
    if not uebernommen:
        return "Danke. Das lege ich Jan zur Entscheidung vor. Ich sage dir dann Bescheid."
    if z["art"] == "keine":
        return "Danke, ist angekommen."
    return f"Danke. {wirkung_fuer_person(z)}"


def wirkung_text(z: dict, person: str, agent: str) -> str:
    """Was passiert ist (bzw. bei einem Vorschlag passieren würde), für Jan. Wo es steht, steht im Log."""
    if z["art"] == "regel":
        return f"Ab jetzt gilt für {ziel_name(z, person)}: „{z['regel']}“"
    if z["art"] == "notiz":
        return f"Wunsch für später notiert, für {ziel_name(z, person)}: „{z['notiz']}“"
    if z["art"] == "nachbesserung":
        return f"{agent_name(agent)} schickt eine überarbeitete Fassung: „{kurz(z['auftrag'], 300)}“"
    return "Nichts zu tun."


def zusammenfassung(person: str, agent: str, feedback_text: str, z: dict, uebernommen: bool,
                    grund: str) -> tuple[str, list[list[str]]]:
    """Meldung an Jan (Text, Knöpfe): wer, was, was passiert ist bzw. was ich vorschlage."""
    zeilen = [f"Feedback von {person} zu {agent_name(agent)}: „{kurz(feedback_text, 300)}“"]
    if uebernommen:
        zeilen.append(wirkung_text(z, person, agent))
        return "\n".join(zeilen), [[KNOPF_STOPP]]
    if z.get("zusammenfassung"):
        zeilen.append(z["zusammenfassung"])
    zeilen.append(f"Mein Vorschlag: {wirkung_text(z, person, agent)}")
    zeilen.append(f"Das übernehme ich nicht von selbst, denn {grund}.")
    return "\n".join(zeilen), [[KNOPF_UEBERNEHMEN, KNOPF_VERWERFEN]]


def stopp_text(fall: dict, ergebnis: str) -> str:
    """Kurze Nachricht an die Person nach Jans Stopp."""
    return f"Jan nimmt dein Feedback „{kurz(fall.get('feedback', ''), 120)}“ zurück. {ergebnis}"


def entscheidung_text(fall: dict, uebernommen: bool) -> str:
    """Nachricht an die Person, nachdem Jan über einen Vorschlag entschieden hat."""
    zitat = f"„{kurz(fall.get('feedback', ''), 120)}“"
    if uebernommen:
        return f"Jan hat dein Feedback {zitat} angenommen. {wirkung_fuer_person(fall['zuordnung'])}".strip()
    return f"Jan hat dein Feedback {zitat} angesehen. Es bleibt alles, wie es ist."


def fall(feedback_id: str, bezug: str, agent: str, feedback_text: str, z: dict, uebernommen: bool, grund: str,
         ziel: tuple[Path, str] | None, zeile: str | None, nachbesserung_id: str | None, instanz_dir: Path) -> dict:
    """Alles, was zur Rücknahme nötig ist (Feld daten des Feedback-Auftrags)."""
    return {
        "feedback_id": feedback_id, "bezug": bezug, "agent": agent, "feedback": feedback_text,
        "zuordnung": z, "uebernommen": uebernommen, "grund": grund,
        "datei": str(ziel[0]) if ziel else None, "abschnitt": ziel[1] if ziel else None, "zeile": zeile,
        "nachbesserung": nachbesserung_id, "instanz": str(instanz_dir), "stand": "uebernommen" if uebernommen else "vorschlag",
    }


class Index:
    """Meldungs-ID -> (Instanz, Feedback-ID), damit Jans Klick den Fall findet (JSON-Datei, eine für alle Instanzen)."""

    MAX = 1000

    def __init__(self, pfad: Path):
        self.pfad = Path(pfad)

    def lesen(self) -> dict:
        return json.loads(self.pfad.read_text(encoding="utf-8")) if self.pfad.exists() else {}

    def merken(self, meldung_id: str, instanz_dir: Path, feedback_id: str) -> None:
        daten = self.lesen()
        daten[meldung_id] = {"instanz": str(instanz_dir), "feedback_id": feedback_id}
        for alt in sorted(daten)[: -self.MAX]:  # IDs beginnen mit Datum
            del daten[alt]
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.pfad.with_suffix(".tmp")
        tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.pfad)

    def finden(self, meldung_id: str) -> dict | None:
        return self.lesen().get(meldung_id)
