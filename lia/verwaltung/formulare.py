"""Katalog der Formulare für die Verbeamtung in Berlin (SenBJF) und ihre Feldzuordnung (rein).

Quelle ist das Gesamtpaket von berlin.de (88 Seiten, Stand Checkliste 06/2026). Die Einzel-PDFs auf der
Seite sind teils verschlüsselt (pypdf bräuchte dafür cryptography), das Paket nicht. Weil sich im Paket
Feldnamen über Formulare hinweg wiederholen ("Datum", "Name", ein Optionsfeld über zwei Seiten), wird
jedes Formular als eigene PDF aus seinen Seiten gebaut und erst danach zusammengefügt (druck.py).

Die Zuordnung ist von Hand an den Seitenbildern geprüft (09.11.2026). Viele Felder heißen nur
"KontrollkästchenN" oder "undefined_N"; die Kommentare sagen, was dort steht. Ändert berlin.de das
Paket, stimmt PAKET_SHA256 nicht mehr und der Agent füllt nichts (lieber gar nicht als falsch).

Werte: Text als str, Kästchen als Exportwert ("/Ja", "/On", "/0" ...). Leere Texte werden weggelassen.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from angaben import Angaben

PAKET_URL = ("https://www.berlin.de/sen/bjf/service/personalverwaltung/dokumente-beamte/"
             "formularpaket-beamte.pdf")
PAKET_SHA256 = "cb8dcff3454ba6e91addd52f2a8df8e1c673be2a077fe9d82729acb944ff8c36"  # geladen 09.11.2026
SEITEN_PAKET = 88

JA = "/Ja"
AN = "/On"

# Familienstand -> Kästchen im Personalfragebogen (Seite 1)
FAMILIENSTAND = {
    "ledig": "Kontrollkästchen4",
    "verheiratet": "Kontrollkästchen5",
    "lebenspartnerschaft": "Kontrollkästchen6",
    "geschieden": "Kontrollkästchen7",
    "verwitwet": "Kontrollkästchen8",
    "aufgehoben": "Kontrollkästchen9",
    "ueberlebend": "Kontrollkästchen10",
}
FIRMENTICKET = {"deutschlandticket": "/Deutschlandticket_Job", "vbb": "/VBB-Firmenticket"}
KIRCHE = {"keine": "--", "ev": "EV", "rk": "RK"}


@dataclass
class Formular:
    schluessel: str
    nr: int  # Nummer in der Checkliste
    titel: str
    seiten: list[int]  # Seiten im Gesamtpaket, ab 1
    felder: Callable[[Angaben, date], dict] = lambda a, d: {}
    bedingung: Callable[[Angaben], tuple[bool | None, str]] = lambda a: (True, "")
    von_hand: list[str] = field(default_factory=list)  # bleibt immer für Lia


def _ohne_leere(werte: dict) -> dict:
    return {k: v for k, v in werte.items() if v not in ("", None)}


def _ja_nein(wert: bool | None, ja: str, nein: str, an: str = JA) -> dict:
    if wert is None:
        return {}
    return {ja: an} if wert else {nein: an}


# ---------- 1 Personalfragebogen Fin 770 (Paket S. 4-7) ----------

def _personalfragebogen(a: Angaben, stichtag: date) -> dict:
    w = {
        "Name ggf auch Geburtsname": a.nachname_mit_geburtsname(),
        "Vornamen Rufname unterstreichen": a.text("person.vornamen"),
        "Text63": a.datum("person.geburtsdatum"),  # geboren am (Tag Monat Jahr)
        "in": a.text("person.geburtsort"),
        "Anschrift Telefon": ", ".join(x for x in (a.anschrift(), a.text("person.telefon")) if x),
    }
    stand = a.text("familie.stand")
    if stand:
        if stand not in FAMILIENSTAND:
            raise ValueError(f"familie.stand: einer von {', '.join(FAMILIENSTAND)}")
        w[FAMILIENSTAND[stand]] = JA
        if stand in ("verheiratet", "lebenspartnerschaft"):
            w["Datum"] = a.datum("familie.seit")  # "Seit dem" in der mittleren Spalte
        elif stand != "ledig":
            w["geschieden seit"] = a.datum("familie.seit")  # "Seit dem" in der rechten Spalte
    if a.verheiratet() or stand in ("geschieden", "verwitwet", "aufgehoben", "ueberlebend"):
        w["Vorund Zuname ggf Geburtsname der Ehegattin des Ehegatten bzw der eingetragenen Lebenspartnerin "
          "des eingetragenen Lebenspartners ggf derdes früheren"] = a.text("familie.partner_name")
        w["Text62"] = a.datum("familie.partner_geburtsdatum")
        if a.verheiratet():
            w |= _ja_nein(a.ja("familie.partner_oeffentlicher_dienst"), "Kontrollkästchen14", "Kontrollkästchen15")
    for i, kind in enumerate(a.kinder()[:4]):
        w[f"{i + 1}_2"] = str(kind.get("name", ""))
        w[f"Text{16 + i}"] = str(kind.get("geburtsdatum", ""))
    w |= _ja_nein(a.ja("familie.schwerbehindert"), "Kontrollkästchen20", "Kontrollkästchen21")
    w |= _ja_nein(a.ja("familie.gleichgestellt"), "Kontrollkästchen23", "Kontrollkästchen24")
    geb = a.geburtstag()
    if geb is not None and geb >= date(1990, 1, 1):  # Häftlingshilfegesetz: Haft vor 1990, nicht möglich
        w["Kontrollkästchen26"] = JA

    # Seite 2: Schule, Studium
    w |= {
        "Allgemeinbildende Schule": a.text("lebenslauf.schule.name"),
        "vom": a.text("lebenslauf.schule.von"),
        "bis zum": a.text("lebenslauf.schule.bis"),
        "Schulabschluss": a.text("lebenslauf.schule.abschluss"),
        # Fachrichtung: zweite Zeile, in der ersten überdeckt der Text die Beschriftung
        "Fachrichtung12": a.text("lebenslauf.studium.fach"),
        "vom_6": a.text("lebenslauf.studium.von"),
        "bis zum_5": a.text("lebenslauf.studium.bis"),
        "AbschlussprüfungFachrichtung": a.text("lebenslauf.studium.abschluss"),
        "am": a.text("lebenslauf.studium.am"),
        "Ergebnis": a.text("lebenslauf.studium.ergebnis"),
        "Text29": a.text("lebenslauf.studium.hochschule"),  # neben "an (Hochschule, Fachhochschule)"
    }
    if a.text("dienst.laufbahnpruefung_am", merken=False):  # 2. Staatsprüfung bestanden
        w["Kontrollkästchen35"] = JA
        w["Text43"] = a.datum("dienst.laufbahnpruefung_am")

    # Seite 2 unten: besondere Kenntnisse (14a) und Ehrenamt (14b), je bis 3 Zeilen
    kenntnisse = ("Besondere Kenntnisse und Fertigkeiten insbesondere für die auszuübende Tätigkeit14a", 3)
    ehrenamt = ("Ehrenamtliche Tätigkeiten zB Betreuung im Jugendbereich Wahrnehmung karitativer Aufgaben14b", 3)
    for (feld, anzahl), pfad in ((kenntnisse, "lebenslauf.kenntnisse"), (ehrenamt, "lebenslauf.ehrenamt")):
        zeilen = a.daten.get("lebenslauf", {}).get(pfad.split(".")[1], [])
        if not isinstance(zeilen, list) or not all(isinstance(z, str) for z in zeilen):
            raise ValueError(f"{pfad}: Liste von Texten erwartet")
        for i, zeile in enumerate(zeilen[:anzahl]):
            w[feld if i == 0 else f"{feld}_{i + 1}"] = zeile

    # Seite 3: Tätigkeiten außerhalb (15) und im öffentlichen Dienst (16), Vorbereitungsdienst
    for i, t in enumerate(a.liste("lebenslauf.taetigkeiten")[:5]):
        n = i + 1
        w |= {f"BeschäftigungsstelleRow{n}": str(t.get("stelle", "")),
              f"Art der TätigkeitRow{n}": str(t.get("art", "")),
              f"vomRow{n}": str(t.get("von", "")), f"bis zumRow{n}": str(t.get("bis", "")),
              f"Grund des AusscheidensRow{n}": str(t.get("grund", ""))}
    for i, t in enumerate(a.liste("lebenslauf.oeffentlicher_dienst")[:5]):
        s = "" if i == 0 else f"_{i + 1}"
        w |= {f"Beschäftigungsbe hörde16{s}": str(t.get("behoerde", "")),
              "Art des Beschäftigungs verhältnisses als BeamtinBeamter RichterinRichter ArbeitnehmerinArbeit "
              f"nehmer oder zur Berufsausbil dung Beschäftigte Beschäftigter16{s}": str(t.get("art", "")),
              f"Amtsbezeichnung Dienst bezeichnung16{s}": str(t.get("amt", "")),
              f"BesGr VergGr LGr EG16{s}": str(t.get("gruppe", "")),
              f"vom16{s}": str(t.get("von", "")), f"bis zum16{s}": str(t.get("bis", "")),
              f"Grund des Ausscheidens16{s}": str(t.get("grund", ""))}
    w |= {
        "Vorbereitungsdienst": a.text("dienst.vorbereitungsdienst_bei"),
        "vom_9": a.text("dienst.vorbereitungsdienst_von"),
        "bis zum_8": a.text("dienst.vorbereitungsdienst_bis"),
        "Prüfung für die Laufbahn des": a.text("dienst.laufbahnpruefung"),
        "am_2": a.text("dienst.laufbahnpruefung_am", merken=False),
        "Ergebnis_2": a.text("dienst.laufbahnpruefung_note", merken=False),
    }

    # Seite 4: Staatsangehörigkeit
    deutsch = a.ja("person.deutsch")
    if deutsch:
        w["Kontrollkästchen48"] = JA  # Deutsche/r im Sinne des Art. 116 GG: ja
        w["Kontrollkästchen49"] = JA  # besitze die deutsche Staatsangehörigkeit
    elif deutsch is False:
        w["Kontrollkästchen47"] = JA
    return _ohne_leere(w)


# ---------- 4 Einstellungserklärungen ZS P 0.001 (2-fach, S. 15-16 und 17-18) ----------

def _einstellungserklaerung(zwangsvollstreckung_keine: str):
    def felder(a: Angaben, stichtag: date) -> dict:
        w = {"Vorname": a.text("person.vornamen"), "Name": a.text("person.nachname"),
             "Geburtsdatum": a.datum("person.geburtsdatum")}
        if a.ja("erklaerungen.keine_verurteilungen"):
            w["Verurteilungen keine"] = AN
        if a.ja("erklaerungen.keine_verfahren"):
            w["Straf- und Ermittlungsverfahren keine"] = AN
        if a.ja("erklaerungen.keine_zwangsvollstreckung"):
            w["Zwangsvollstreckungsmaßnahmen"] = zwangsvollstreckung_keine  # Optionsfeld "keine"
        return _ohne_leere(w)
    return felder


# ---------- 5 Familienzuschlag Fin 708 (S. 19-23), nur verheiratet oder mit Kindern ----------

FAMILIENSTAND_708 = {"ledig": "Kontrollkästchen61", "verheiratet": "Kontrollkästchen62",
                     "lebenspartnerschaft": "Kontrollkästchen62", "geschieden": "Kontrollkästchen63",
                     "aufgehoben": "Kontrollkästchen63", "verwitwet": "Kontrollkästchen64",
                     "ueberlebend": "Kontrollkästchen64"}


def _familienzuschlag(a: Angaben, stichtag: date) -> dict:
    # Feldnamen täuschen: "Personalnummer" (Kammfeld) steht unter "Dienststelle", "Telefonnummer" unter
    # "Personalnummer". Kinder-Tabelle (Namen, Kindergeld) bleibt für Lia: dort gibt es kein Namensfeld.
    w = {
        "Name/Geburtsname": a.nachname_mit_geburtsname(),
        "Vorname": a.text("person.vornamen"),
        "Geburtsdatum_af_date": a.datum("person.geburtsdatum"),
        "Telefonnummer": a.text("dienst.personalnummer", merken=False),
        "Anschrift": ", ".join(x for x in (a.anschrift(), a.text("person.telefon")) if x),
    }
    stand = a.text("familie.stand", merken=False)
    if stand in FAMILIENSTAND_708:
        w[FAMILIENSTAND_708[stand]] = JA
    if stand and stand != "ledig":
        w["verheirateteingetragene Lebenspartnerschaft"] = a.datum("familie.seit")  # Zeile "seit dem"
    return _ohne_leere(w)


def _familie_bedingung(a: Angaben) -> tuple[bool | None, str]:
    stand = a.text("familie.stand", merken=False)
    if a.verheiratet() or a.kinder():
        return True, ""
    if not stand:
        return None, "Familienstand unbekannt"
    return False, "nur bei Ehe/Lebenspartnerschaft oder Kindern"


# ---------- Absender-Formulare der SenBJF (ZS P ...) ----------

def _absender(a: Angaben) -> dict:
    z = a.zum_absender()
    return {"Absender 1": z[0], "Absender 2": z[1], "Absender 3": z[2]}


def _dienststelle(a: Angaben) -> str:
    return " / ".join(x for x in (a.text("dienst.schule"), a.text("dienst.personalnummer", merken=False)) if x)


def _akteneinsicht(a: Angaben, stichtag: date) -> dict:
    w = _absender(a) | {
        "undefined_4": a.name_voll(),  # Vor- und Nachname (Feldname täuscht)
        "undefined_5": _dienststelle(a),  # Einstellungsbezirk/Dienststelle/ggf. Personalnummer
        "Vorund Nachname": a.datum("person.geburtsdatum"),  # Zeile "Geburtsdatum"
    }
    w |= _ja_nein(a.ja("erklaerungen.akteneinsicht_hpr"), "ja", "nein", AN)
    w |= _ja_nein(a.ja("erklaerungen.akteneinsicht_einigungsstelle"), "ja_2", "nein_2", AN)
    return _ohne_leere(w)


def _erkrankungen(a: Angaben, stichtag: date) -> dict:
    return _ohne_leere(_absender(a) | {
        "undefined_4": a.name_voll(),  # Vor- und Nachname
        "undefined_5": a.text("dienst.schule"),  # Einstellungsbezirk/Dienststelle
        "undefined_6": a.datum("person.geburtsdatum"),
        "undefined_7": a.text("dienst.personalnummer", merken=False),
    })


def _arbeitszeit(a: Angaben, stichtag: date) -> dict:
    w = _absender(a)
    art = a.text("dienst.arbeitszeit")
    if art == "vollzeit":
        w["oder"] = AN  # das Kästchen "Vollzeit" heißt im PDF "oder"
    elif art == "teilzeit":
        w["undefined_4"] = "X"  # Kästchen "Teilzeit" ist ein Textfeld
        w["Teilzeit mit"] = a.text("dienst.teilzeit_stunden")
        w["von"] = a.text("dienst.pflichtstunden")
    elif art:
        raise ValueError("dienst.arbeitszeit: vollzeit oder teilzeit")
    return _ohne_leere(w)


def _hauptstadtzulage(a: Angaben, stichtag: date) -> dict:
    w = {
        "Name Vorname": a.name_komma(),
        "Personalnummer": a.text("dienst.personalnummer", merken=False),
        "BeschäftigungsdienststelleSchulnummerStellenzeichen": a.text("dienst.schule"),
        "Telefon dienstlich oder privat": a.text("person.telefon"),
        "Geburtsdatum": a.datum("person.geburtsdatum"),
        "EMailAdresse dienstlich oder privat": a.text("person.email"),
        "Beschäftigtengruppe": "/Beamte",
    }
    ticket = a.text("geld.firmenticket")
    if ticket in FIRMENTICKET:
        w["Firmenticket"] = "/JA"
        w["Firmenticket_Art"] = FIRMENTICKET[ticket]
    elif ticket == "nein":
        w["Firmenticket"] = "/Nein"
    elif ticket:
        raise ValueError("geld.firmenticket: deutschlandticket, vbb oder nein")
    return _ohne_leere(w)


def _bankverbindung(a: Angaben, stichtag: date) -> dict:
    iban = a.text("geld.iban").replace(" ", "").upper()
    if iban and not iban.startswith("DE"):
        raise ValueError("geld.iban: nur deutsche IBAN (DE ist im Formular vorgedruckt)")
    kirche = a.text("geld.kirche").lower()
    if kirche and kirche not in KIRCHE:
        raise ValueError("geld.kirche: keine, ev oder rk")
    klasse = a.text("geld.steuerklasse")
    if klasse and klasse not in "123456":
        raise ValueError("geld.steuerklasse: 1 bis 6")
    kinder = a.kinder()
    stand_bekannt = bool(a.text("familie.stand", merken=False))
    w = {
        "Anrede": a.text("person.anrede"),
        "Vorname": a.text("person.vornamen"),
        "Nachname": a.text("person.nachname"),
        "Straße + Hausnummer": a.text("person.strasse"),
        "PLZ": a.text("person.plz"),
        "Ort": a.text("person.ort"),
        "Telefonnummer": a.text("person.telefon"),
        "E-Mail-Adresse": a.text("person.email"),
        "Bank": a.text("geld.bank"),
        "IBAN": iban[2:],  # "DE" ist vorgedruckt, Feld hat 20 Stellen
        " Kontoinhaber": a.text("geld.kontoinhaber_abweichend", merken=False),
        "SteuerID 11stellig": a.text("geld.steuer_id").replace(" ", ""),
        "Steuerklasse": klasse,
        "Kirche": KIRCHE.get(kirche, ""),
        # Hauptarbeitgeber (Kästchen links neben dem Wort), außer Lia hat ausdrücklich false angegeben
        "Check Box1": "" if a.ja("geld.hauptarbeitgeber", merken=False) is False else JA,
        "Sozialversicherungsnummer 12stellig": a.text("geld.sv_nummer").replace(" ", ""),
        "Krankenkasse": a.text("geld.krankenkasse"),
    }
    if kinder:
        w |= {"Kinder": "Ja", "Anzahl": str(len(kinder))}
    elif stand_bekannt:  # wer den Familienstand angegeben hat, hat auch Kinder angegeben (leer = keine)
        w["Kinder"] = "Nein"
    return _ohne_leere(w)


def _antrag_verbeamtung(a: Angaben, stichtag: date) -> dict:
    w = _absender(a) | {
        "Text1": a.name_komma(), "Text2": a.text("person.email"), "Text3": a.anschrift(),
        "Text4": a.text("person.telefon"), "Text5": a.datum("person.geburtsdatum"),
        "Text6": a.text("dienst.personalnummer", merken=False), "Text7": a.text("dienst.schule"),
        "Antrag VB": AN,  # Ich beantrage eine Einstellung im Beamtenverhältnis
    }
    w |= _ja_nein(a.ja("dienst.volle_lehrbefaehigung"), "ja", "toggle_3", AN)
    w |= _ja_nein(a.ja("person.deutsch"), "ja_2", "toggle_5", AN)  # deutsch oder EU/EWR/Schweiz
    w |= _ja_nein(a.unter_47(stichtag), "ja_3", "toggle_7", AN)
    return _ohne_leere(w)


def _vl(a: Angaben, stichtag: date) -> dict:
    return _ohne_leere({"Name Vorname": a.name_komma(), "Telefon dienstlich": a.text("person.telefon"),
                        "Beschäftigungsbehörde  1": a.text("dienst.schule"),
                        "Personalnummer": a.text("dienst.personalnummer", merken=False)})


def _riester(a: Angaben, stichtag: date) -> dict:
    return _ohne_leere({"Name  Vorname": a.name_komma(), "Telefon 1": a.text("person.telefon"),
                        "Beschäftigungsbehörde / Versorgungsbehörde": a.text("dienst.schule"),
                        "Personalnummer / Versorgungsnummer": a.text("dienst.personalnummer", merken=False),
                        "Einwilligung": JA if a.ja("geld.riester", merken=False) else ""})


def _wenn(pfad: str, grund_nein: str):
    def bedingung(a: Angaben) -> tuple[bool | None, str]:
        wert = a.ja(pfad, merken=False)
        if wert is None:
            return None, "noch offen"
        return (True, "") if wert else (False, grund_nein)
    return bedingung


def _vor_1972(a: Angaben) -> tuple[bool | None, str]:
    vor = a.vor_1972()
    if vor is None:
        return None, "Geburtsdatum fehlt"
    return (True, "") if vor else (False, "nur bei Geburt vor dem 13.01.1972")


def _kinder_bedingung(a: Angaben) -> tuple[bool | None, str]:
    return (True, "") if a.kinder() else (False, "nur mit Kindern")


UNTERSCHRIFT = "Datum und Unterschrift"

FORMULARE = [
    Formular("fin770", 1, "Personalfragebogen (Fin 770)", [4, 5, 6, 7], _personalfragebogen,
             von_hand=["Lichtbild einkleben (S. 1)", "Rufname unterstreichen",
                       "S. 4 unten: Kästchen zum (erweiterten) Führungszeugnis ankreuzen",
                       "„Berlin, den …“ und Unterschrift (S. 4)"]),
    Formular("fin761", 2, "Zusatzbogen zum Personalfragebogen (Fin 761)", [8, 9], bedingung=_vor_1972,
             von_hand=["alles", UNTERSCHRIFT]),
    Formular("fin762", 3, "Erklärung Nichttätigkeit MfS-AfNS (Fin 762)", [14], bedingung=_vor_1972,
             von_hand=["alles", UNTERSCHRIFT]),
    Formular("zsp0001a", 4, "Einstellungserklärungen ZS P 0.001 (1. Ausfertigung)", [15, 16],
             _einstellungserklaerung("/0"), von_hand=["Datum oben", "Unterschrift (S. 2)"]),
    Formular("zsp0001b", 4, "Einstellungserklärungen ZS P 0.001 (2. Ausfertigung)", [17, 18],
             _einstellungserklaerung("/2"), von_hand=["Datum oben", "Unterschrift (S. 2)"]),
    Formular("fin708", 5, "Erklärung zum Familienzuschlag (Fin 708)", [19, 20, 21, 22, 23], _familienzuschlag,
             bedingung=_familie_bedingung,
             von_hand=["Dienststelle", "Abschnitt II: Kinder (Name, Kindergeld) und folgende Seiten", UNTERSCHRIFT]),
    Formular("zsp1360", 6, "Erklärung zu den Kinderbetreuungszeiten (ZS P 1.360)", [27, 28],
             bedingung=_kinder_bedingung, von_hand=["alles", UNTERSCHRIFT]),
    Formular("zsp0006", 7, "Einverständnis Personalaktenanforderung (ZS P 0.006)", [29],
             lambda a, d: _ohne_leere(_absender(a)),
             bedingung=_wenn("dienst.personalakte_anfordern", "nur wenn eine Personalakte woanders liegt"),
             von_hand=["Angaben zur bisherigen Dienststelle", UNTERSCHRIFT]),
    Formular("zsp0007", 8, "Erklärung Akteneinsicht HPR/Einigungsstelle (ZS P 0.007)", [30], _akteneinsicht,
             von_hand=["Ort, Datum, Unterschrift"]),
    Formular("zsp0029", 9, "Erklärung zu Erkrankungen (ZS P 0.029)", [31, 32, 33], _erkrankungen,
             von_hand=["Ort, Datum, Unterschrift (Inhalt selbst lesen)"]),
    Formular("zsp3999", 10, "Erklärung zur Arbeitszeit (ZS P 3.999)", [34], _arbeitszeit,
             von_hand=["Ort, Datum, Unterschrift"]),
    Formular("zsp2603", 11, "Erklärung zur Hauptstadtzulage (ZS P 2.603)", [35, 36], _hauptstadtzulage,
             von_hand=["Beginn des Zuschusses bzw. Abos (Datum)", UNTERSCHRIFT]),
    Formular("zsp0013a", 12, "Bankverbindung/ELStAM/SV (ZS P 0.013a)", [37], _bankverbindung,
             von_hand=[UNTERSCHRIFT]),
    Formular("zsp0005", 13, "Antrag auf Verbeamtung (ZS P 0.005)", [38, 39], _antrag_verbeamtung,
             von_hand=[UNTERSCHRIFT + " (S. 2)"]),
    Formular("fin586", 14, "Antrag vermögenswirksame Leistungen (Fin 586)", [40, 41], _vl,
             bedingung=_wenn("geld.vl", "nicht gewünscht"),
             von_hand=["Vertragsdaten (Institut, Vertragsnummer, Betrag)", UNTERSCHRIFT]),
    Formular("fin587", 15, "Einwilligung Zulageverfahren Altersvorsorge (Fin 587)", [42, 43], _riester,
             bedingung=_wenn("geld.riester", "nicht gewünscht"),
             von_hand=["Jahr und ggf. Zulagenummer", UNTERSCHRIFT]),
]


def auswahl(a: Angaben) -> list[tuple[Formular, bool | None, str]]:
    """Jedes Formular mit (gilt, Grund). gilt=None: hängt von einer fehlenden Angabe ab, wird mitgedruckt."""
    return [(f, *f.bedingung(a)) for f in FORMULARE]
