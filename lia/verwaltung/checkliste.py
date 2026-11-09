"""Lias persönliche Checkliste zum Termin (rein, Text).

Folgt der Checkliste ZS P 0.004a (06/2026) der SenBJF: Formulare 1-15 (was beiliegt, was entfällt,
was Lia noch von Hand macht), Merkblätter 16-22 (nur lesen), persönliche Unterlagen 23-38.
"""

from angaben import NAMEN, Angaben
from formulare import Formular

TERMIN = ("Termin: Dienstag, 10.11.2026, 14:00 Uhr, Senatsverwaltung für Bildung, Jugend und Familie, "
          "Flottenstraße 28-42, 13407 Berlin. Beim Pförtner anmelden, Personalausweis oder Reisepass dabei.")

MERKBLAETTER = [
    "16. Verschwiegenheitspflicht (Fin 759)",
    "17. Annahmeverbot von Belohnungen und Geschenken (Fin 760)",
    "18. Familienzuschlag (Fin 710)",
    "19. Vermögenswirksame Leistungen (Fin 586a)",
    "20. Zusätzliche private Altersvorsorge (Riester)",
    "21. Hauptstadtzulage und Firmenticket (ZS P 2.603a)",
    "22. Freiwillig gesetzlich Versicherte bei Unfall (ZS P 1.801)",
]


def _unterlagen(a: Angaben) -> list[str]:
    stand = a.text("familie.stand", merken=False)
    z = [
        "23. Personalausweis oder Reisepass (nur vorzeigen, keine Kopie)",
        "24. Masernschutz: Impfpass mit zwei Masernimpfungen (Original und Kopie) oder ärztliche Bescheinigung",
        "25. Lebenslauf, aktuell und eigenhändig unterschrieben",
    ]
    if stand in ("verheiratet", "lebenspartnerschaft"):
        z.append("26. Eheurkunde bzw. Nachweis der Lebenspartnerschaft")
    if stand in ("geschieden", "aufgehoben"):
        z.append("27. Scheidungsurteil mit Rechtskraftvermerk bzw. Aufhebung der Lebenspartnerschaft")
    if stand in ("verwitwet", "ueberlebend"):
        z.append("28. Sterbeurkunde")
    if a.kinder():
        z.append("29. Geburtsurkunden aller Kinder")
    if a.ja("familie.schwerbehindert", merken=False) or a.ja("familie.gleichgestellt", merken=False):
        z.append("30. Schwerbehindertenausweis bzw. Gleichstellungsbescheid")
    if not stand:
        z.append("26.-30. nur falls zutreffend: Ehe-, Scheidungs-, Sterbeurkunde, Geburtsurkunden der Kinder, "
                 "Schwerbehindertenausweis")
    z += [
        "31. Zeugnis über den Schulabschluss (auch wenn ein Hochschulabschluss vorliegt)",
        "32. Zeugnis und Urkunde über den Hochschulabschluss",
        "33. vorläufige Bescheinigung über die Staatsprüfung, sobald bestanden "
        "(laut Mail auch per Mail an die Einstellungsstelle schicken)",
        "34. Zeugnis und Urkunde über eine Berufsausbildung (falls vorhanden)",
        "35. Nachweis über Wehr- oder Zivildienst (falls vorhanden)",
        "36. Arbeitsverträge und Zeugnisse über bisherige Tätigkeiten",
        "37. Mitgliedsbescheinigung der Krankenkasse (nur freiwillig gesetzlich oder privat versichert)",
    ]
    return z


def erstellen(a: Angaben, auswahl: list[tuple[Formular, bool | None, str]], seiten: dict[str, tuple[int, int]],
              druckdatei: str) -> str:
    """auswahl aus formulare.auswahl, seiten: schluessel -> (erste, letzte Seite in der Druck-PDF)."""
    z = ["Verbeamtung: Checkliste für Lia", "", TERMIN, "",
         f"DRUCKEN: {druckdatei}, einseitig (NICHT doppelseitig). Reihenfolge so lassen.",
         "Die Felder sind ausfüllbar: Fehlendes geht auch am Rechner, sonst mit Kuli.", "",
         "FORMULARE (ausgefüllt und unterschrieben mitbringen)"]
    for f, gilt, grund in auswahl:
        if gilt is False:
            z.append(f"{f.nr:>2}. {f.titel}: entfällt ({grund})")
            continue
        von, bis = seiten[f.schluessel]
        ort = f"S. {von}" if von == bis else f"S. {von}-{bis}"
        zeile = f"{f.nr:>2}. {f.titel}: liegt bei ({ort})"
        if gilt is None:
            zeile += f", bitte prüfen, ob nötig ({grund})"
        z.append(zeile)
        if f.von_hand:
            z.append("    von Hand: " + "; ".join(f.von_hand))
    z += ["", "Personalfragebogen Ziffer 15/16: Zeiten ab Schulende lückenlos (auch Studium, Nebenjobs, "
              "Arbeitslosigkeit). Mehr als fünf Zeilen: Beiblatt.", ""]
    if a.fehlend:
        z.append("FEHLENDE ANGABEN (in den Formularen frei gelassen, bitte selbst eintragen)")
        z += [f"- {NAMEN.get(p, p)}" for p in a.fehlend]
        z.append("")
    z += ["MERKBLÄTTER (nicht drucken, nur lesen; im Gesamtpaket auf berlin.de)"]
    z += [f"- {m}" for m in MERKBLAETTER]
    z += ["", "PERSÖNLICHE UNTERLAGEN (in dieser Reihenfolge)",
          "Urkunden und Zeugnisse im Original oder als beglaubigte Kopie. Ohne Beglaubigung: einfache Kopie "
          "UND Original mitbringen."]
    z += [f"- {u}" for u in _unterlagen(a)]
    z += ["", "SCHON ERLEDIGT / KOMMT VON SELBST",
          "- Erweitertes Führungszeugnis: liegt laut Mail schon vor.",
          "- Amtsärztliche Untersuchung (ZMGA): Termin kommt per Post, pünktlich hingehen.",
          "- Terminbestätigung an einstellungsstelle@senbjf.berlin.de: macht Lia selbst, falls noch nicht geschehen."]
    return "\n".join(z) + "\n"
