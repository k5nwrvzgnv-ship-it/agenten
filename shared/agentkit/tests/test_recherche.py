import json
import tempfile
import unittest
from pathlib import Path

from agentkit import recherche
from agentkit.recherche import RechercheFehler

OK = {"status": "bestanden", "grund": ""}
DURCH = {"status": "durchgefallen", "grund": "Zitat nicht auf der Seite"}


def lauf1():
    """Wie ein Webauftrag von Lia: zwei Fälle, eine Einschätzung, ein Registerbeleg."""
    return {
        "fragen": [{"id": "F1", "frage": "Welche milden Jugendtaten gab es?"}],
        "quellen": [{"url": "https://www.presseportal.de/blaulicht/1/", "titel": "Freibad Ladenburg"}],
        "aussagen": [
            {"frage": "F1", "art": "fall", "text": "Jugendliche brachen nachts ins Freibad Ladenburg ein.",
             "belege": [{"url": "https://www.presseportal.de/blaulicht/1", "zitat": "brachen ein", "pruefung": OK}],
             "traegt": {"urteil": "ja", "fehlt": ""}, "fall": {"alter": "14-16"}},
            {"frage": "F1", "art": "fall", "text": "Graffiti in Hagen.",
             "belege": [{"url": "https://hagen.example/graffiti", "zitat": "Graffiti", "pruefung": OK}]},
            {"frage": None, "art": "einschaetzung", "text": "Der Ausgang ist meist nicht bekannt.", "belege": []},
            {"frage": None, "art": "tatsache", "text": "Kant: niemals bloß als Mittel.",
             "belege": [{"register": "kant-mds-strafrecht", "zitat": "niemals bloß als Mittel", "seite": 331,
                         "pruefung": OK}], "traegt": {"urteil": "ja", "fehlt": ""}},
        ],
        "luecken": ["Kein Fall aus Berlin."],
        "rueckfragen": ["Auch 18-Jährige?"],
    }


def basis_mit_lauf():
    b = recherche.neu("lia-milde-jugendtaten", "Milde Jugendtaten", "lia", "recherche", fach="Ethik")
    recherche.einarbeiten(b, {"art": "suche", "usd": 2.63, "modell": "opus"}, lauf1())
    return b


class NeuUndPruefen(unittest.TestCase):
    def test_neu_ist_gueltig(self):
        b = recherche.neu("p-1", "Titel", "jan", "uni")
        self.assertEqual(recherche.pruefen(b), [])
        self.assertEqual(b["fragen"], [])

    def test_neu_ungueltig(self):
        with self.assertRaises(RechercheFehler):
            recherche.neu("Mit Leerzeichen", "Titel", "jan", "uni")
        with self.assertRaises(RechercheFehler):
            recherche.neu("p-1", "Titel", "felix", "uni")

    def test_pruefen_findet_kaputte_verweise(self):
        b = basis_mit_lauf()
        b["aussagen"][0]["frage"] = "F9"
        b["aussagen"][1]["belege"][0]["quelle"] = "Q99"
        b["aussagen"][2]["status"] = "toll"
        b["quellen"][1]["id"] = "Q1"
        fehler = "\n".join(recherche.pruefen(b))
        for teil in ("F9", "Q99", "toll", "doppelt"):
            self.assertIn(teil, fehler)

    def test_pruefen_kein_objekt(self):
        self.assertTrue(recherche.pruefen([]))


class Einarbeiten(unittest.TestCase):
    def test_erster_lauf(self):
        b = basis_mit_lauf()
        self.assertEqual(recherche.pruefen(b), [])
        self.assertEqual([q["id"] for q in b["quellen"]], ["Q1", "Q2", "Q3"])
        # Adresse mit / am Ende ist dieselbe Quelle
        self.assertEqual(b["aussagen"][0]["belege"][0]["quelle"], "Q1")
        self.assertEqual(b["quellen"][2]["register"], "kant-mds-strafrecht")
        self.assertEqual([a["status"] for a in b["aussagen"]], ["gesichert", "teilweise", "einschaetzung", "gesichert"])
        self.assertEqual(b["aussagen"][0]["fall"], {"alter": "14-16"})
        lauf = b["laeufe"][0]
        self.assertEqual((lauf["nr"], lauf["usd"]), (1, 2.63))
        self.assertEqual(lauf["neu"]["aussagen"], ["A1", "A2", "A3", "A4"])
        self.assertEqual(b["luecken"], [{"text": "Kein Fall aus Berlin.", "lauf": 1}])

    def test_zweiter_lauf_ohne_doppelte(self):
        b = basis_mit_lauf()
        zwei = lauf1()
        zwei["fragen"].append({"id": "F2", "frage": "Gibt es Fälle aus Berlin?"})
        zwei["aussagen"][1]["belege"][0]["zitat"] = "Graffiti an der Schule"  # neuer Beleg zur alten Aussage
        zwei["aussagen"].append({"frage": "F2", "art": "fall", "text": "Ladendiebstahl in Neukölln.",
                                 "belege": [{"url": "https://www.berlin.de/polizei/1", "zitat": "x", "pruefung": OK}]})
        eintrag = recherche.einarbeiten(b, {"art": "ausweiten", "usd": 1.5}, zwei)
        self.assertEqual(recherche.pruefen(b), [])
        self.assertEqual(eintrag["neu"], {"fragen": ["F2"], "quellen": ["Q4"], "aussagen": ["A5"]})
        self.assertEqual(eintrag["geaendert"], ["A2"])
        self.assertEqual(eintrag["doppelt"], 4)
        self.assertEqual(b["aussagen"][4]["frage"], "F2")
        self.assertEqual(len(b["aussagen"][1]["belege"]), 2)
        self.assertEqual(b["aussagen"][1]["geaendert_in"], [2])
        self.assertEqual(len(b["luecken"]), 1)
        self.assertEqual(recherche.zahlen(b)["usd"], 4.13)

    def test_gleicher_text_andere_quelle_ist_neue_aussage(self):
        b = basis_mit_lauf()
        e = {"aussagen": [{"art": "fall", "text": "Graffiti in Hagen.",
                           "belege": [{"url": "https://anders.example/", "zitat": "y", "pruefung": OK}]}]}
        eintrag = recherche.einarbeiten(b, {"art": "suche"}, e)
        self.assertEqual(eintrag["neu"]["aussagen"], ["A5"])

    def test_neuere_pruefung_und_urteil_gelten(self):
        b = basis_mit_lauf()
        e = {"aussagen": [{"art": "fall", "text": "Graffiti in Hagen.",
                           "belege": [{"url": "https://hagen.example/graffiti", "zitat": "Graffiti", "pruefung": DURCH}],
                           "traegt": {"urteil": "nein", "fehlt": "Ort"}}]}
        recherche.einarbeiten(b, {"art": "nachpruefen"}, e)
        a = b["aussagen"][1]
        self.assertEqual(a["belege"][0]["pruefung"], DURCH)
        self.assertEqual(a["status"], "unbelegt")
        self.assertEqual(a["traegt"]["urteil"], "nein")

    def test_ungueltiger_eingang_aendert_nichts(self):
        b = basis_mit_lauf()
        vorher = json.dumps(b, sort_keys=True)
        schlecht = [
            ({"art": "irgendwas"}, {}),
            ({"art": "suche"}, {"aussagen": [{"art": "fall", "text": "x", "frage": "F7", "belege": []}]}),
            ({"art": "suche"}, {"aussagen": [{"art": "fall", "text": "x", "belege": [{"zitat": "z", "pruefung": OK}]}]}),
            ({"art": "suche"}, {"aussagen": [{"art": "fall", "text": "x", "belege": [{"url": "u", "zitat": "z"}]}]}),
            ({"art": "suche"}, {"aussagen": [{"art": "witz", "text": "x"}]}),
            ({"art": "suche"}, {"fragen": [{"id": "F1", "frage": "a"}, {"id": "F1", "frage": "b"}]}),
        ]
        for lauf, e in schlecht:
            with self.assertRaises(RechercheFehler, msg=str(e)):
                recherche.einarbeiten(b, lauf, e)
        self.assertEqual(json.dumps(b, sort_keys=True), vorher)


class Entscheidungen(unittest.TestCase):
    def test_sperre_macht_unbelegt_und_ist_rueckgaengig(self):
        b = basis_mit_lauf()
        nr = recherche.entscheiden(b, "jan", "sperren", "Q1", "nur Pressemeldung")
        self.assertTrue(b["quellen"][0]["gesperrt"])
        self.assertEqual(b["aussagen"][0]["status"], "unbelegt")
        recherche.zuruecknehmen(b, nr)
        self.assertFalse(b["quellen"][0]["gesperrt"])
        self.assertEqual(b["aussagen"][0]["status"], "gesichert")
        self.assertIsNotNone(b["entscheidungen"][0]["zurueckgenommen"])
        with self.assertRaises(RechercheFehler):
            recherche.zuruecknehmen(b, nr)

    def test_verwerfen_und_uebernehmen(self):
        b = basis_mit_lauf()
        recherche.entscheiden(b, "lia", "verwerfen", "A1", "zu hart")
        self.assertEqual((b["aussagen"][0]["status"], b["aussagen"][0]["sichtung"]), ("verworfen", "verworfen"))
        self.assertFalse(recherche.gilt_als_uebernommen(b["aussagen"][0]))
        # die spätere Entscheidung gilt
        recherche.entscheiden(b, "lia", "uebernehmen", "A1")
        self.assertEqual(b["aussagen"][0]["status"], "gesichert")
        self.assertTrue(recherche.gilt_als_uebernommen(b["aussagen"][0]))
        self.assertEqual(recherche.pruefen(b), [])

    def test_gesichertes_gilt_als_uebernommen(self):
        b = basis_mit_lauf()
        self.assertEqual([recherche.gilt_als_uebernommen(a) for a in b["aussagen"]], [True, False, False, True])

    def test_falsches_ziel(self):
        b = basis_mit_lauf()
        for wer, was, ziel in (("jan", "sperren", "A1"), ("jan", "verwerfen", "Q1"), ("felix", "verwerfen", "A1"),
                               ("jan", "loeschen", "A1"), ("jan", "verwerfen", "A99")):
            with self.assertRaises(RechercheFehler):
                recherche.entscheiden(b, wer, was, ziel)

    def test_neuer_lauf_behaelt_entscheidungen(self):
        b = basis_mit_lauf()
        recherche.entscheiden(b, "jan", "sperren", "Q2")
        recherche.einarbeiten(b, {"art": "suche"}, lauf1())
        self.assertEqual(b["aussagen"][1]["status"], "unbelegt")


class BestandUndKosten(unittest.TestCase):
    def test_bestand_text(self):
        b = basis_mit_lauf()
        recherche.entscheiden(b, "lia", "verwerfen", "A2")
        recherche.entscheiden(b, "jan", "sperren", "Q1")
        t = recherche.bestand_text(b)
        self.assertIn("F1: Welche milden Jugendtaten gab es?", t)
        self.assertIn("Register kant-mds-strafrecht", t)
        self.assertIn("A4 [gesichert] Kant", t)
        self.assertIn("Nicht wieder vorschlagen:", t)
        self.assertIn("verworfen: Graffiti in Hagen.", t)
        self.assertIn("gesperrte Quelle: https://www.presseportal.de/blaulicht/1/", t)
        self.assertIn("Kein Fall aus Berlin.", t)
        self.assertNotIn("A2 [", t)
        self.assertNotIn("brachen ein", t)  # keine Zitate

    def test_bestand_leer(self):
        t = recherche.bestand_text(recherche.neu("p", "T", "jan", "uni"))
        self.assertIn("(keine)", t)

    def test_kosten(self):
        self.assertTrue(recherche.kosten_schaetzen("webauftrag", "suche", "normal")["gemessen"])
        self.assertEqual(recherche.kosten_schaetzen("webauftrag", "ausweiten", "gross")["von"], 21.53)
        self.assertEqual(recherche.kosten_schaetzen("uni", "frage")["bis"], 0.5)
        self.assertIsNone(recherche.kosten_schaetzen("uni", "suche", "riesig"))
        self.assertIsNone(recherche.kosten_schaetzen("uni", "suche", "kurz")["von"])


class Datei(unittest.TestCase):
    def test_speichern_laden_bearbeiten(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "projekte" / "p" / recherche.WISSEN
            recherche.speichern(pfad, basis_mit_lauf())
            with recherche.bearbeiten(pfad) as b:
                recherche.entscheiden(b, "jan", "verwerfen", "A1")
            self.assertEqual(recherche.laden(pfad)["aussagen"][0]["status"], "verworfen")

    def test_fehler_im_block_aendert_nichts(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / recherche.WISSEN
            recherche.speichern(pfad, basis_mit_lauf())
            vorher = pfad.read_text()
            with self.assertRaises(RuntimeError):
                with recherche.bearbeiten(pfad) as b:
                    recherche.entscheiden(b, "jan", "verwerfen", "A1")
                    raise RuntimeError("Abbruch")
            self.assertEqual(pfad.read_text(), vorher)

    def test_ungueltig_wird_nicht_geschrieben(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / recherche.WISSEN
            b = basis_mit_lauf()
            b["fuer"] = "niemand"
            with self.assertRaises(RechercheFehler):
                recherche.speichern(pfad, b)
            self.assertFalse(pfad.exists())


if __name__ == "__main__":
    unittest.main()
