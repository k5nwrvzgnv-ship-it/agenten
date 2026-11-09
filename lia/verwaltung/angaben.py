"""Lias Angaben für die Formulare (rein, ohne Netz und ohne PDF).

Die Angaben stehen in data/angaben.toml (nicht im Repo, chmod 600). Jeder Wert hat einen Pfad wie
"person.nachname". Fehlt ein Wert oder ist er leer, bleibt das Feld im Formular frei und der Pfad
landet in Angaben.fehlend: Die Checkliste nennt Lia dann, was sie noch von Hand ausfüllt.

Formate: Datum als TT.MM.JJJJ, Ja/Nein als true/false. Listen (kinder, taetigkeiten,
oeffentlicher_dienst) als Tabellen-Arrays. Vorlage: angaben.beispiel.toml.
"""

import re
import tomllib
from datetime import date
from pathlib import Path

DATUM = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")

# Für die Liste "noch von Hand": Pfad -> verständlicher Name
NAMEN = {
    "person.anrede": "Anrede",
    "person.nachname": "Nachname",
    "person.vornamen": "Vornamen",
    "person.geburtsdatum": "Geburtsdatum",
    "person.geburtsort": "Geburtsort",
    "person.strasse": "Straße und Hausnummer",
    "person.plz": "PLZ",
    "person.ort": "Wohnort",
    "person.telefon": "Telefon",
    "person.email": "E-Mail",
    "person.deutsch": "Deutsche Staatsangehörigkeit",
    "familie.stand": "Familienstand",
    "familie.seit": "Familienstand seit",
    "familie.partner_name": "Name der Ehegattin/des Ehegatten",
    "familie.partner_geburtsdatum": "Geburtsdatum der Ehegattin/des Ehegatten",
    "familie.partner_oeffentlicher_dienst": "Ehegatte im öffentlichen Dienst (ja/nein)",
    "familie.schwerbehindert": "Schwerbehinderung (ja/nein)",
    "familie.gleichgestellt": "Gleichstellung (ja/nein)",
    "dienst.schule": "Einstellungsbezirk/Schulnummer",
    "dienst.personalnummer": "Personalnummer",
    "dienst.arbeitszeit": "Vollzeit oder Teilzeit",
    "dienst.teilzeit_stunden": "Teilzeit: Wochenstunden",
    "dienst.pflichtstunden": "Teilzeit: Pflichtstunden bei Vollzeit",
    "dienst.volle_lehrbefaehigung": "Volle Lehrbefähigung bei Einstellung (ja/nein)",
    "dienst.vorbereitungsdienst_von": "Vorbereitungsdienst von",
    "dienst.vorbereitungsdienst_bis": "Vorbereitungsdienst bis",
    "dienst.vorbereitungsdienst_bei": "Vorbereitungsdienst bei",
    "dienst.laufbahnpruefung": "Prüfung für die Laufbahn (Lehramt)",
    "dienst.laufbahnpruefung_am": "Datum der Staatsprüfung",
    "dienst.laufbahnpruefung_note": "Note der Staatsprüfung",
    "geld.bank": "Bank",
    "geld.iban": "IBAN",
    "geld.steuer_id": "Steuer-ID",
    "geld.steuerklasse": "Steuerklasse",
    "geld.kirche": "Kirchensteuermerkmal",
    "geld.sv_nummer": "Sozialversicherungsnummer",
    "geld.krankenkasse": "Krankenkasse",
    "geld.firmenticket": "Firmenticket (Deutschlandticket Job, VBB oder keins)",
    "erklaerungen.keine_verurteilungen": "Erklärung Verurteilungen („keine“ ankreuzen)",
    "erklaerungen.keine_verfahren": "Erklärung anhängige Verfahren („keine“ ankreuzen)",
    "erklaerungen.keine_zwangsvollstreckung": "Erklärung Zwangsvollstreckung („keine“ ankreuzen)",
    "erklaerungen.akteneinsicht_hpr": "Akteneinsicht Hauptpersonalrat (ja/nein)",
    "erklaerungen.akteneinsicht_einigungsstelle": "Akteneinsicht Einigungsstelle (ja/nein)",
    "lebenslauf.schule.name": "Schule (Name)",
    "lebenslauf.schule.von": "Schule von",
    "lebenslauf.schule.bis": "Schule bis",
    "lebenslauf.schule.abschluss": "Schulabschluss",
    "lebenslauf.studium.fach": "Studium: Fachrichtung",
    "lebenslauf.studium.von": "Studium von",
    "lebenslauf.studium.bis": "Studium bis",
    "lebenslauf.studium.abschluss": "Studium: Abschlussprüfung",
    "lebenslauf.studium.am": "Studium: Abschluss am",
    "lebenslauf.studium.ergebnis": "Studium: Ergebnis",
    "lebenslauf.studium.hochschule": "Studium: Hochschule",
}


class AngabenFehler(ValueError):
    """Angaben-Datei fehlt, ist kaputt oder hat ein falsches Format."""


def laden(pfad: Path) -> "Angaben":
    if not pfad.exists():
        raise AngabenFehler(f"{pfad} fehlt (Vorlage: angaben.beispiel.toml)")
    if pfad.stat().st_mode & 0o077:
        raise AngabenFehler(f"{pfad} muss chmod 600 haben (persönliche Daten)")
    try:
        daten = tomllib.loads(pfad.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise AngabenFehler(f"{pfad}: {e}") from e
    return Angaben(daten)


class Angaben:
    """Lesender Zugriff mit Buchführung, was fehlt."""

    def __init__(self, daten: dict):
        self.daten = daten
        self.fehlend: list[str] = []

    def _roh(self, pfad: str):
        wert = self.daten
        for teil in pfad.split("."):
            if not isinstance(wert, dict) or teil not in wert:
                return None
            wert = wert[teil]
        return wert

    def _fehlt(self, pfad: str) -> None:
        if pfad not in self.fehlend:
            self.fehlend.append(pfad)

    def text(self, pfad: str, merken: bool = True) -> str:
        """Wert als Text, "" wenn er fehlt (dann in fehlend, außer merken=False)."""
        wert = self._roh(pfad)
        if wert is None or (isinstance(wert, str) and not wert.strip()):
            if merken:
                self._fehlt(pfad)
            return ""
        if isinstance(wert, bool):
            raise AngabenFehler(f"{pfad}: Text erwartet, nicht ja/nein")
        return str(wert).strip()

    def ja(self, pfad: str, merken: bool = True) -> bool | None:
        """True/False, None wenn unbekannt (dann in fehlend)."""
        wert = self._roh(pfad)
        if wert is None:
            if merken:
                self._fehlt(pfad)
            return None
        if not isinstance(wert, bool):
            raise AngabenFehler(f"{pfad}: true oder false erwartet")
        return wert

    def datum(self, pfad: str, merken: bool = True) -> str:
        wert = self.text(pfad, merken)
        if wert and not DATUM.fullmatch(wert):
            raise AngabenFehler(f"{pfad}: Datum als TT.MM.JJJJ erwartet")
        return wert

    def liste(self, pfad: str) -> list[dict]:
        wert = self._roh(pfad)
        if wert is None:
            return []
        if not isinstance(wert, list) or not all(isinstance(x, dict) for x in wert):
            raise AngabenFehler(f"{pfad}: Liste von Tabellen erwartet")
        return wert

    # ---------- abgeleitete Werte ----------

    def name_voll(self) -> str:
        """'Lia Laura Pohlmann' (ohne Geburtsname)."""
        return " ".join(x for x in (self.text("person.vornamen"), self.text("person.nachname")) if x)

    def name_komma(self) -> str:
        """'Pohlmann, Lia Laura'."""
        teile = [x for x in (self.text("person.nachname"), self.text("person.vornamen")) if x]
        return ", ".join(teile)

    def nachname_mit_geburtsname(self) -> str:
        name = self.text("person.nachname")
        geb = self.text("person.geburtsname", merken=False)
        return f"{name}, geb. {geb}" if name and geb else name

    def plz_ort(self) -> str:
        return " ".join(x for x in (self.text("person.plz"), self.text("person.ort")) if x)

    def anschrift(self) -> str:
        return ", ".join(x for x in (self.text("person.strasse"), self.plz_ort()) if x)

    def geburtstag(self) -> date | None:
        wert = self.datum("person.geburtsdatum")
        if not wert:
            return None
        t, m, j = (int(x) for x in DATUM.fullmatch(wert).groups())
        return date(j, m, t)

    def unter_47(self, stichtag: date) -> bool | None:
        """Hat das 47. Lebensjahr am Stichtag noch nicht vollendet."""
        geb = self.geburtstag()
        if geb is None:
            return None
        try:
            tag47 = geb.replace(year=geb.year + 47)
        except ValueError:  # 29. Februar
            tag47 = date(geb.year + 47, 3, 1)
        return stichtag < tag47

    def vor_1972(self) -> bool | None:
        """Vor dem 13.01.1972 geboren (Zusatzbogen Fin 761 und Erklärung MfS)."""
        geb = self.geburtstag()
        return None if geb is None else geb < date(1972, 1, 13)

    def verheiratet(self) -> bool:
        return self.text("familie.stand", merken=False) in ("verheiratet", "lebenspartnerschaft")

    def kinder(self) -> list[dict]:
        return self.liste("familie.kinder")

    def zum_absender(self) -> list[str]:
        """Drei Absenderzeilen: Name, Straße, PLZ Ort."""
        return [self.name_voll(), self.text("person.strasse"), self.plz_ort()]
