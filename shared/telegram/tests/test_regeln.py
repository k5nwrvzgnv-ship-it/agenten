"""Kürze-Regeln für Jans Nachrichten (docs/befund-ux.md, Abschnitt 3) und der Signal-Filter (logik.signal_html).

Geprüft wird jede Nachricht in tests/snapshots/jan_*.txt mit logik.regelverstoesse: sichtbarer Teil kurz, höchstens
drei Punkte, höchstens eine Handlung, keine Füllwörter. Entwürfe zur Freigabe sind ausgenommen (freigegeben wird genau
der gezeigte Text, er wird nicht gekürzt).
"""

import re
import unittest
from html import unescape

import logik
import vorlagen as v
from tests.test_sprache_snapshots import ORDNER, zerlegen

AUSGENOMMEN = ("jan_entwurf_",)


def ohne_html(html: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", html))


class RegelnSnapshotTest(unittest.TestCase):
    def test_alle_nachrichten_an_jan(self):
        dateien = [d for d in sorted(ORDNER.glob("jan_*.txt")) if not d.stem.startswith(AUSGENOMMEN)]
        self.assertGreater(len(dateien), 20)
        verstoesse = {}
        for d in dateien:
            nachrichten, knoepfe = zerlegen(d.read_text(encoding="utf-8"))
            # Knöpfe hängen an der letzten Nachricht; jan_hinweise sind lauter einzelne Antworten
            for i, n in enumerate(nachrichten):
                gefunden = logik.regelverstoesse(n, knoepfe if i == len(nachrichten) - 1 else None)
                if gefunden:
                    verstoesse[f"{d.stem}[{i}]"] = gefunden
        self.assertEqual(verstoesse, {})

    def test_keine_feedback_knoepfe_bei_jan(self):
        for d in ORDNER.glob("jan_*.txt"):
            self.assertNotIn(":fb:", d.read_text(encoding="utf-8").replace("[", " "), d.stem)
            self.assertNotRegex(d.read_text(encoding="utf-8"), r"\] fb:", d.stem)

    def test_hilfe_und_menue_ohne_alte_funktionen(self):
        texte = [logik.hilfe_text(logik.AGENTEN), *[t for t, _ in (logik.ansicht_agent("uni", "erledigen"),
                                                                    logik.ansicht_home([], ["uni"], 2))]]
        knoepfe = [b for _, k in (logik.ansicht_agent("uni", "erledigen"), logik.ansicht_home([], ["uni"], 2))
                   for z in k for b, _ in z]
        for wort in ("/pc", "/weiter", "/verwerfen", "lern", "Modus"):
            for t in texte + knoepfe:
                self.assertNotIn(wort, t)
        for alt in ("Status", "Verbrauch", "Hilfe", "↻ Aktualisieren"):
            self.assertNotIn(alt, knoepfe)


class RegelPruefungTest(unittest.TestCase):
    def test_erkennt_verstoesse(self):
        self.assertEqual(logik.regelverstoesse("Uni ist dran."), [])
        self.assertIn("fuellwort: bitte", logik.regelverstoesse("Schick es bitte noch einmal."))
        self.assertIn("fuellwort: leider", logik.regelverstoesse("Das ging leider nicht."))
        self.assertIn("fuellwort: kommt hierher", logik.regelverstoesse("Uni ist dran. Das Ergebnis kommt hierher."))
        self.assertIn("handlungen: 2", logik.regelverstoesse("Schick den Auftrag. Sieh am PC nach."))
        self.assertIn("handlungen: 2", logik.regelverstoesse("Tipp einen an.", ["Uni", "Dokumente"]))
        self.assertEqual(logik.regelverstoesse("Was soll Uni tun?", ["« Zurück"]), [])
        self.assertIn("punkte: 4", logik.regelverstoesse("Kopf\n• a\n• b\n• c\n• d"))
        self.assertIn("laenge: 901 sichtbare Zeichen", logik.regelverstoesse("x" * 901))

    def test_zugeklappter_teil_zaehlt_nicht(self):
        html = "<b>Uni</b>\nKopf\n• a\n<blockquote expandable>• b\n• c\n• d\n" + "x" * 3000 + "</blockquote>"
        self.assertEqual(logik.regelverstoesse(html), [])
        self.assertEqual(logik.sichtbarer_teil(html), "Uni\nKopf\n• a")


class SignalFilterTest(unittest.TestCase):
    def test_rauschen_raus(self):
        (n,) = logik.mit_absender("posteingang", "[post] Wichtige Mails (3 geprüft, 1 vorgefiltert):\nPayPal: Beleg")
        self.assertEqual(n, "<b>Posteingang</b>\nWichtige Mails:\nPayPal: Beleg")
        (n,) = logik.mit_absender("uni", "Wichtige Uni-Mails (8 neue geprüft):\n- **Was es ist:** Folien")
        self.assertEqual(n, "<b>Uni</b>\nWichtige Uni-Mails:\n• Was es ist: Folien")
        (n,) = logik.mit_absender("lia/recherche", "Lia, Agent recherche: Fertig.\nDatei: /home/agent/x/y z.docx")
        self.assertEqual(n, "<b>Recherche (Lia)</b>\nFertig.")
        (n,) = logik.mit_absender("dokumente", "Fehler im Agenten (RenderFehler): Vorlage fehlt\n"
                                               "Details: dokumente/logs/dokumente.log", "hat nicht geklappt")
        self.assertEqual(n, "<b>Dokumente</b> · hat nicht geklappt\nVorlage fehlt")

    def test_inhalt_bleibt(self):
        """Zahlen in Klammern, die kein Zähler sind, und relative Angaben bleiben stehen."""
        (n,) = logik.mit_absender("uni", "Aufgabe fällig (09.11. 23:59): BTLx (2 Seiten)\nKurs: Fertigung 1")
        self.assertIn("(09.11. 23:59)", n)
        self.assertIn("(2 Seiten)", n)
        self.assertIn("https://moodle.example.org/a/b", logik.mit_absender("uni", "Kopf\nhttps://moodle.example.org/a/b")[0])

    def test_hoechstens_drei_punkte_rest_zugeklappt(self):
        text = "Normen:\n" + "\n".join(f"- Norm {i}" for i in range(1, 8))
        (n,) = logik.mit_absender("uni", text)
        sichtbar, _, zu = n.partition("<blockquote expandable>")
        self.assertEqual(sichtbar.count("• "), 3)
        self.assertEqual(zu.count("• "), 4)
        self.assertTrue(n.endswith("</blockquote>"))

    def test_lange_kopfzeile_erster_satz(self):
        (n,) = logik.mit_absender("uni", "Fertig: 20 von 39 belegt. " + "Belege: 27 bestanden, 0 durchgefallen. " * 5)
        self.assertEqual(logik.sichtbarer_teil(n), "Uni\nFertig: 20 von 39 belegt.")
        self.assertIn("Belege: 27 bestanden", n)

    def test_nichts_geht_verloren_und_laengen(self):
        zeilen = [f"Zeile {i} <&> " + "wort " * 60 for i in range(60)]
        stuecke = logik.mit_absender("holzbalkenscan", "Lauf fertig\n" + "\n".join(zeilen))
        self.assertGreater(len(stuecke), 1)
        alles = "\n".join(ohne_html(s) for s in stuecke)
        for z in zeilen:
            self.assertIn(z.strip(), alles)
        for s in stuecke:
            self.assertLessEqual(v.sichtbare_laenge(s), 4096)
            self.assertEqual(s.count("<blockquote expandable>"), s.count("</blockquote>"))
        self.assertEqual(logik.regelverstoesse(stuecke[0]), [])

    def test_kurz_bleibt_beschriftung(self):
        stuecke = logik.mit_absender("uni", "Zusammenfassung fertig.\n" + "\n".join(f"- Punkt {i}" for i in range(6)))
        self.assertTrue(logik.passt_als_beschriftung(stuecke))

    def test_leerer_text(self):
        self.assertEqual(logik.mit_absender("uni", ""), ["<b>Uni</b>"])


class SchalterTest(unittest.TestCase):
    A = {"id": "20261025-211917-uni-7ad7f7", "agent": "uni", "status": "erledigt", "ergebnis": "x"}

    def test_feedback_knoepfe_nur_mit_schalter(self):
        self.assertIsNone(logik.ergebnis_knoepfe(self.A))
        alt = logik.FEEDBACK_KNOEPFE
        try:
            logik.FEEDBACK_KNOEPFE = True
            self.assertEqual(logik.ergebnis_knoepfe(self.A)[0][0][0], "Passt")
            self.assertIsNone(logik.ergebnis_knoepfe({**self.A, "status": "fehlgeschlagen"}))
            self.assertIsNone(logik.ergebnis_knoepfe({**self.A, "agent": "feedback"}))
            self.assertIsNone(logik.ergebnis_knoepfe({**self.A, "daten": {"knoepfe": v.NUR_ANTWORT}}))
        finally:
            logik.FEEDBACK_KNOEPFE = alt

    def test_lernmodus_still_weiter_angenommen(self):
        self.assertEqual(logik.befehl_auswerten("/unilern Kapitel 4"), ("uni", "lernen", "Kapitel 4"))


if __name__ == "__main__":
    unittest.main()
