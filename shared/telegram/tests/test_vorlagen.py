"""Snapshot-Tests der gerenderten Nachrichten (tests/snapshots/*.txt).

Ändert sich eine Vorlage absichtlich: SNAPSHOTS_NEU=1 setzen, Tests laufen lassen, Diff ansehen, committen.
"""

import os
import re
import unittest
from pathlib import Path

from agentkit import feedback as fb
import logik
import portal_logik as p
import vorlagen as v

ORDNER = Path(__file__).parent / "snapshots"
AID = "20261025-211917-recherche-7ad7f7"
ERLAUBT = re.compile(r"</?(b|i)>|<blockquote expandable>|</blockquote>")

RECHERCHE = {
    "id": AID, "agent": "recherche", "status": "erledigt", "quelle": "portal-frage",
    "text": "Vorschläge für eine Reihe Strafe, Ethik Klasse 8",
    "ergebnis": "Recherche fertig, Dokument anbei.",
    "daten": {
        "kern": "Für Klasse 8 trägt die Gegenüberstellung Kant gegen von Liszt am besten, über einen echten "
                "Diebstahlsfall mit zwei Tätern. 31 von 49 Aussagen sind belegt.",
        "punkte": ["4 Reihenfragen, vorläufig bewertet", "3 reale Fälle mit Quelle", "Liszts drei Tätertypen geprüft",
                   "dieser vierte Punkt fällt weg"],
        "pruefen": "15 Aussagen sind nur teilweise belegt, im Dokument markiert.",
        "belege": [f"Beleg {i}: Kant, AA VI, S. 331 „niemals bloß als Mittel“ <und> & mehr" for i in range(1, 41)],
    },
}


def knoepfe_text(knoepfe) -> str:
    return "\n".join("  ".join(f"[{t}] {d}" for t, d in zeile) for zeile in knoepfe)


def darstellung(stuecke: list[str], knoepfe=None) -> str:
    teile = ["\n--- nächste Nachricht ---\n".join(stuecke)]
    if knoepfe:
        teile.append("--- Knöpfe ---\n" + knoepfe_text(knoepfe))
    return "\n".join(teile) + "\n"


class SnapshotTest(unittest.TestCase):
    def pruefen(self, name: str, stuecke: list[str], knoepfe=None):
        for s in stuecke:
            self.assertLessEqual(len(s), 4096)
            self.assertEqual(re.sub(r"<[^>]*>", "", ERLAUBT.sub("", s)), ERLAUBT.sub("", s), "nur erlaubtes HTML")
        for zeile in knoepfe or []:
            for _, daten in zeile:
                self.assertLessEqual(len(daten.encode()), 64)
        ist = darstellung(stuecke, knoepfe)
        datei = ORDNER / f"{name}.txt"
        if os.environ.get("SNAPSHOTS_NEU") or not datei.exists():
            datei.write_text(ist, encoding="utf-8")
        self.assertEqual(ist, datei.read_text(encoding="utf-8"), f"Snapshot {name} weicht ab")

    def test_lia_recherche_mit_kern_und_belegen(self):
        stuecke = p.ergebnis_nachricht(RECHERCHE)
        self.assertEqual(len(stuecke), 1)
        self.assertIn("weitere im Dokument", stuecke[0])
        self.assertNotIn("vierte Punkt", stuecke[0])
        self.pruefen("lia_recherche", stuecke, p.ergebnis_knoepfe(RECHERCHE))

    def test_lia_einfach_und_lang(self):
        a = {"id": AID, "agent": "unterricht", "status": "erledigt", "text": "Arbeitsblatt Kant", "ergebnis": "Hier ist dein Arbeitsblatt."}
        self.pruefen("lia_einfach", p.ergebnis_nachricht(a), p.ergebnis_knoepfe(a))
        lang = p.ergebnis_nachricht({**a, "ergebnis": "\n".join(f"Zeile {i} " + "x" * 80 for i in range(100))})
        self.assertGreater(len(lang), 1)

    def test_lia_fehler(self):
        a = {"id": AID, "agent": "unterricht", "status": "fehlgeschlagen", "text": "Arbeitsblatt Kant",
             "ergebnis": "Gerade ist das gemeinsame Kontingent aufgebraucht. Bitte schick den Wunsch ab 14:00 noch einmal."}
        self.pruefen("lia_fehler", p.ergebnis_nachricht(a), p.ergebnis_knoepfe(a))

    def test_lia_feedback_bestaetigung(self):
        a = {"id": "20261027-120000-feedback-abcdef", "agent": "feedback", "status": "erledigt",
             "text": "Falscher Fokus: mehr Fälle aus der Lebenswelt", "ergebnis": fb.bestaetigung(
                 {"art": "regel", "regel": "Fälle zuerst aus der Lebenswelt der Lerngruppe."}, True)}
        self.pruefen("lia_feedback_bestaetigung", p.ergebnis_nachricht(a), p.ergebnis_knoepfe(a))

    def test_knoepfe_zu_lang(self):
        self.pruefen("knoepfe_zu_lang", [""], v.laenge_knoepfe(p.VORSATZ, AID))

    def test_jan_ergebnis_mit_kern(self):
        a = {**RECHERCHE, "agent": "uni"}
        self.pruefen("jan_ergebnis_kern", logik.auftrag_nachricht(a), v.feedback_knoepfe("", AID))

    def test_jan_feedback_zusammenfassung(self):
        z = {"art": "regel", "ziel": "alle", "regel": "Ergebnisse beginnen mit einer Empfehlung in einem Satz.",
             "zusammenfassung": "Lia will die Empfehlung zuerst sehen."}
        text, knoepfe = fb.zusammenfassung("Lia", "recherche", "Ich will zuerst wissen, was du empfiehlst", z, True, "",
                                           "„Ergebnisse beginnen mit einer Empfehlung in einem Satz.“ in lia/instanz/regeln.md")
        self.pruefen("jan_feedback_zusammenfassung", logik.mit_absender("feedback", text),
                     logik.meldung_knoepfe({"id": "20261027-120001-feedback-abcdef", "knoepfe": knoepfe}))


class VorlagenTest(unittest.TestCase):
    def test_feedback_auswerten(self):
        self.assertEqual(v.feedback_auswerten(f"p:fb:{AID}:lang", "p:"), (AID, "lang"))
        self.assertEqual(v.feedback_auswerten(f"fb:{AID}:li", ""), (AID, "li"))
        for falsch in (f"p:fb:{AID}:boese", "fb:../x:ok", f"fb:{AID}:ok", "p:menue"):
            self.assertIsNone(v.feedback_auswerten(falsch, "p:"), falsch)
        self.assertIsNone(v.feedback_auswerten(f"p:fb:{AID}:ok", ""))

    def test_feedback_text(self):
        self.assertEqual(v.feedback_text("fokus", " mehr Fälle "), "Falscher Fokus: mehr Fälle")
        self.assertEqual(v.feedback_text("frei", "passt nicht"), "passt nicht")
        self.assertIn("nur dieses Ergebnis", v.feedback_text("lh"))
        self.assertIn("Ab jetzt", v.feedback_text("li"))

    def test_zu_lange_knopfdaten(self):
        with self.assertRaises(ValueError):
            v.fb_daten("p:", "x" * 60, "ok")

    def test_beschriftung_zaehlt_ohne_html(self):
        self.assertEqual(v.sichtbare_laenge("<b>a</b>&amp;"), 2)


if __name__ == "__main__":
    unittest.main()
