"""Rückmeldungen aus dem Portal, Agent-Teil: Marke nehmen, sichern, Auftrag in der Kette, Endstand zurückschreiben.

Mit der echten Aufträge-Ablage in einem temporären Ordner. Der Web-Teil steht in portal/tests/test_rueckmeldung.py."""

import json
import re
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import agent
import rueckmeldungen
from agentkit import auftraege

JETZT = datetime(2026, 11, 4, 14, 0, tzinfo=timezone.utc)
AGENT = "uni"
PROJEKT = "fehlstellen"
FASSUNG = "Fehlstellen an Holz.pdf"


class Ablage:
    """agentkit.auftraege mit eigenem Ordner, sonst dieselben Aufrufe wie im Agenten."""

    def __init__(self, tmp: Path):
        self.basis, self.agenten_dir = tmp / "auftraege", tmp

    def neue(self, agent_name, dienst=auftraege.ALLE):
        return auftraege.neue(agent_name, basis=self.basis, dienst=dienst)

    def erledigte(self, agent_name):
        return auftraege.erledigte(agent_name, basis=self.basis)

    def erledigter(self, kennung):
        return auftraege.erledigter(kennung, basis=self.basis)

    def neuer_auftrag(self, agent_name, text, **felder):
        return auftraege.neuer_auftrag(agent_name, text, basis=self.basis, agenten_dir=self.agenten_dir, absender="Jan", **felder)

    def abschliessen(self, kennung, ergebnis="ok", status="erledigt", sitzung=None):
        return auftraege.abschliessen(kennung, ergebnis, status, sitzung=sitzung, basis=self.basis, agenten_dir=self.agenten_dir)


class Aufbau(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.hier = self.tmp / AGENT
        self.ablage = Ablage(self.tmp)
        self.meldungen = []
        self.kommentare = lambda pfad: [{"kommentar": "kürzen"}]
        self.start = self.ablage.neuer_auftrag(AGENT, "Exposé: Fehlstellen", sitzung=None)
        self.ablage.abschliessen(self.start, sitzung="s1")
        self.ende = self.ablage.neuer_auftrag(AGENT, "Antwort", bezug=self.start, sitzung="s1")
        self.ablage.abschliessen(self.ende, sitzung="s2")
        self.expose = self.hier / "data" / "expose" / self.start
        (self.expose / "fassung").mkdir(parents=True)
        (self.expose / "expose.json").write_text('{"titel": "alt"}')
        (self.expose / "fassung" / FASSUNG).write_bytes(b"%PDF-alt")
        (self.expose / "fassung" / "Fehlstellen an Holz.docx").write_bytes(b"DOCX-alt")
        (self.expose / "fassung" / "notiz.txt").write_text("gehört nicht zur Sicherung")

    def anlegen(self, text="Bitte kürzen, und zwar deutlich.", endung=None, roh=b"", kette=None, wann=JETZT) -> str:
        return rueckmeldungen.anlegen(self.hier, PROJEKT, kette or self.start, text, endung, roh, wann)

    def wo(self, kennung: str) -> Path:
        return rueckmeldungen.ordner(self.hier, PROJEKT, kennung)

    def stand(self, kennung: str) -> dict:
        return rueckmeldungen.stand_lesen(self.wo(kennung))

    def marken(self) -> list[str]:
        ordner = rueckmeldungen.schlange(self.hier)
        return sorted(p.stem for p in ordner.glob("*.json")) if ordner.is_dir() else []

    def schritt(self, abarbeiten=lambda: None) -> None:
        rueckmeldungen.abarbeiten(self.hier, AGENT, self.ablage, abarbeiten, self.kommentare, self.meldungen.append, lambda: JETZT)


class Kette(unittest.TestCase):
    ERLEDIGT = [{"id": "1", "bezug": None, "sitzung": "s1", "status": "fehlgeschlagen"},
                {"id": "2", "bezug": "1", "sitzung": "s2", "status": "erledigt"},
                {"id": "3", "bezug": "2", "sitzung": None, "status": "fehlgeschlagen"},
                {"id": "4", "bezug": "2", "sitzung": "s4", "status": "zurueckgezogen"},
                {"id": "9", "bezug": None, "sitzung": "fremd", "status": "erledigt"}]

    def test_neuester_mit_sitzung_der_kette(self):
        self.assertEqual(rueckmeldungen.kettenende(self.ERLEDIGT, "1")["id"], "2")

    def test_keine_kette(self):
        self.assertIsNone(rueckmeldungen.kettenende(self.ERLEDIGT, "x"))

    def test_kreis_haengt_nicht(self):
        self.assertIsNone(rueckmeldungen.kettenende([{"id": "a", "bezug": "b", "sitzung": "s"}, {"id": "b", "bezug": "a", "sitzung": "s"}], "x"))

    def test_kette_offen(self):
        self.assertTrue(rueckmeldungen.kette_offen([{"id": "5", "bezug": "2"}], self.ERLEDIGT, "1"))
        self.assertFalse(rueckmeldungen.kette_offen([{"id": "5", "bezug": "9"}], self.ERLEDIGT, "1"))
        self.assertFalse(rueckmeldungen.kette_offen([], self.ERLEDIGT, "1"))


class Uebergabe(Aufbau):
    def test_text_wird_auftrag_in_der_kette(self):
        kennung = self.anlegen()
        self.schritt()
        self.assertEqual(self.marken(), [])
        a, = self.ablage.neue(AGENT, dienst=None)
        self.assertEqual((a["quelle"], a["bezug"], a["sitzung"], a["modus"], a["dateien"]), ("portal", self.ende, "s2", "erledigen", []))
        self.assertIn("Bitte kürzen, und zwar deutlich.", a["text"])
        self.assertNotIn("angehängten Datei", a["text"])
        stand = self.stand(kennung)
        self.assertEqual((stand["stand"], stand["auftrag"]), ("laeuft", a["id"]))

    def test_sicherung_vor_dem_auftrag(self):
        kennung = self.anlegen()
        gesehen = []

        def neuer(*args, **felder):
            gesehen.append(sorted(p.name for p in (self.wo(kennung) / "vorher").iterdir()))
            return Ablage.neuer_auftrag(self.ablage, *args, **felder)

        with mock.patch.object(self.ablage, "neuer_auftrag", neuer):
            self.schritt()
        self.assertEqual(gesehen, [["Fehlstellen an Holz.docx", FASSUNG, "expose.json"]])
        vorher = self.wo(kennung) / "vorher"
        self.assertEqual((vorher / FASSUNG).read_bytes(), b"%PDF-alt")
        self.assertEqual((vorher / "expose.json").read_text(), '{"titel": "alt"}')
        self.assertEqual(vorher.stat().st_mode & 0o777, 0o700)
        for datei in vorher.iterdir():
            self.assertEqual(datei.stat().st_mode & 0o777, 0o600, datei.name)
        self.assertEqual((self.expose / "expose.json").read_text(), '{"titel": "alt"}')  # das Original bleibt

    def test_datei_wird_kopiert(self):
        kennung = self.anlegen("", ".pdf", b"%PDF-mit-kommentaren")
        self.schritt()
        a, = self.ablage.neue(AGENT, dienst=None)
        self.assertEqual(a["dateien"], [f"data/eingang/{a['id']}/kommentare.pdf"])
        self.assertEqual((self.hier / a["dateien"][0]).read_bytes(), b"%PDF-mit-kommentaren")
        self.assertTrue((self.wo(kennung) / "kommentare.pdf").is_file())
        self.assertIn("angehängten Datei", a["text"])
        self.assertIsNone(self.stand(kennung)["hinweis"])

    def test_datei_ohne_kommentare_und_ohne_text_kostet_nichts(self):
        self.kommentare = lambda pfad: []
        kennung = self.anlegen("", ".pdf", b"%PDF-")
        self.schritt()
        self.assertEqual(self.ablage.neue(AGENT, dienst=None), [])
        stand = self.stand(kennung)
        self.assertEqual(stand["stand"], "fehlgeschlagen")
        self.assertIn("keine Kommentare", stand["grund"])
        self.assertFalse((self.wo(kennung) / "vorher").exists())
        self.assertEqual(self.marken(), [])
        self.assertEqual(len(self.meldungen), 1)

    def test_datei_ohne_kommentare_mit_text_laeuft_mit_hinweis(self):
        self.kommentare = lambda pfad: []
        kennung = self.anlegen("Bitte Abschnitt 2 kürzen.", ".docx", b"PK\x03\x04")
        self.schritt()
        self.assertEqual(len(self.ablage.neue(AGENT, dienst=None)), 1)
        self.assertIn("keine lesbaren Kommentare", self.stand(kennung)["hinweis"])

    def test_kaputte_datei(self):
        def kaputt(pfad):
            raise ValueError("zerstört")

        self.kommentare = kaputt
        ohne_text = self.anlegen("", ".pdf", b"%PDF-")
        self.schritt()
        self.assertEqual(self.ablage.neue(AGENT, dienst=None), [])
        self.assertIn("nicht lesbar: zerstört", self.stand(ohne_text)["grund"])
        mit_text = self.anlegen("Bitte Abschnitt 2 kürzen.", ".pdf", b"%PDF-")
        self.schritt()
        self.assertEqual(len(self.ablage.neue(AGENT, dienst=None)), 1)
        self.assertEqual(self.stand(mit_text)["stand"], "laeuft")

    def test_ohne_fassung_kein_auftrag(self):
        (self.expose / "expose.json").unlink()
        kennung = self.anlegen()
        self.schritt()
        self.assertEqual(self.ablage.neue(AGENT, dienst=None), [])
        self.assertIn("noch keine Fassung", self.stand(kennung)["grund"])

    def test_kette_ohne_sitzung(self):
        kennung = self.anlegen(kette="20200101-000000-uni-abcdef")
        self.schritt()
        self.assertEqual(self.ablage.neue(AGENT, dienst=None), [])
        self.assertIn("keinen Auftrag mit Sitzung", self.stand(kennung)["grund"])

    def test_absturz_beim_anlegen_gibt_keinen_zweiten_lauf(self):
        kennung = self.anlegen()
        with mock.patch.object(self.ablage, "neuer_auftrag", side_effect=OSError("Platte voll")):
            self.schritt()
        self.assertEqual(self.marken(), [])
        self.assertEqual(self.stand(kennung)["stand"], "fehlgeschlagen")
        self.assertIn("Platte voll", self.meldungen[0])
        self.schritt()
        self.assertEqual(self.ablage.neue(AGENT, dienst=None), [])

    def test_ungueltige_marke_wird_gemeldet_und_entfernt(self):
        kennung = self.anlegen()
        pfad = rueckmeldungen.schlange(self.hier) / f"{kennung}.json"
        for inhalt in ("kein json", json.dumps({"id": kennung, "projekt": "../..", "kette": self.start}),
                       json.dumps({"id": "anders", "projekt": PROJEKT, "kette": self.start}), json.dumps({"id": kennung, "projekt": PROJEKT, "kette": "../x"})):
            pfad.write_text(inhalt)
            self.meldungen.clear()
            self.schritt()
            self.assertEqual(self.marken(), [], inhalt)
            self.assertEqual(len(self.meldungen), 1, inhalt)
            self.assertEqual(self.ablage.neue(AGENT, dienst=None), [], inhalt)

    def test_zurueckgenommene_wird_nicht_uebergeben(self):
        kennung = self.anlegen()
        self.assertTrue(rueckmeldungen.zuruecknehmen(self.hier, self.wo(kennung), kennung, JETZT))
        self.schritt()
        self.assertEqual(self.ablage.neue(AGENT, dienst=None), [])
        self.assertEqual(self.stand(kennung)["stand"], "zurueckgezogen")
        self.assertFalse(rueckmeldungen.zuruecknehmen(self.hier, self.wo(kennung), kennung, JETZT))

    def test_ohne_warteschlange_passiert_nichts(self):
        self.schritt()
        self.assertEqual(self.ablage.neue(AGENT, dienst=None), [])

    def test_offener_auftrag_der_kette_laesst_warten(self):
        offen = self.ablage.neuer_auftrag(AGENT, "Antwort per Telegram", bezug=self.ende, sitzung="s2")
        kennung = self.anlegen()
        self.schritt()
        self.assertEqual(self.marken(), [kennung])
        self.assertEqual([a["id"] for a in self.ablage.neue(AGENT, dienst=None)], [offen])
        self.assertEqual(self.stand(kennung)["stand"], "wartet")


class Endstand(Aufbau):
    def _laufend(self) -> tuple[str, str]:
        kennung = self.anlegen()
        self.schritt()
        return kennung, self.stand(kennung)["auftrag"]

    def test_bleibt_laufend_solange_offen(self):
        kennung, _ = self._laufend()
        self.schritt()
        self.assertEqual(self.stand(kennung)["stand"], "laeuft")

    def test_endstaende(self):
        for status, sitzung, erwartet, grund in (("erledigt", "s3", "fertig", None), ("fehlgeschlagen", None, "fehlgeschlagen", "Fehler"),
                                                 ("zurueckgezogen", None, "zurueckgezogen", "gestoppt")):
            kennung, auftrag = self._laufend()
            self.ablage.abschliessen(auftrag, f"Text {status}", status, sitzung=sitzung)
            self.schritt()
            stand = self.stand(kennung)
            self.assertEqual((stand["stand"], stand["ergebnis"]), (erwartet, f"Text {status}"))
            if grund:
                self.assertIn(grund, stand["grund"])
            else:
                self.assertIsNone(stand["grund"])

    def test_verschwundener_auftrag_steht_nicht_ewig_auf_laeuft(self):
        kennung, auftrag = self._laufend()
        (self.ablage.basis / "neu" / f"{auftrag}.json").unlink()
        self.schritt()
        stand = self.stand(kennung)
        self.assertEqual(stand["stand"], "fehlgeschlagen")
        self.assertIn(auftrag, stand["grund"])

    def test_ergebnis_steht_schon_nach_dem_lauf_im_stand(self):
        kennung = self.anlegen()

        def lauf():
            for a in self.ablage.neue(AGENT, dienst=None):
                self.ablage.abschliessen(a["id"], "Neue Fassung", sitzung="s3")

        self.schritt(lauf)
        self.assertEqual((self.stand(kennung)["stand"], self.stand(kennung)["ergebnis"]), ("fertig", "Neue Fassung"))


class NurEineJeProjekt(Aufbau):
    def _zwei(self) -> tuple[str, str]:
        return self.anlegen("Erste Rückmeldung bitte.", wann=JETZT), self.anlegen("Zweite Rückmeldung bitte.", wann=JETZT.replace(minute=5))

    def test_zweite_wartet_wenn_die_erste_liegen_bleibt(self):
        """Kontingent knapp: Der erste Auftrag bleibt offen, die zweite Marke bleibt liegen."""
        erste, zweite = self._zwei()
        self.schritt()
        self.assertEqual(self.marken(), [zweite])
        self.assertEqual(self.stand(zweite)["stand"], "wartet")
        self.assertEqual(self.stand(erste)["stand"], "laeuft")
        self.assertEqual(len(self.ablage.neue(AGENT, dienst=None)), 1)
        self.schritt()  # auch ein späterer Lauf übergibt sie nicht
        self.assertEqual(self.marken(), [zweite])

    def test_nacheinander_in_einem_lauf_und_die_zweite_baut_auf_der_ersten_auf(self):
        erste, zweite = self._zwei()
        reihenfolge = []

        def lauf():
            for a in self.ablage.neue(AGENT, dienst=None):
                reihenfolge.append((a["id"], a["bezug"], a["sitzung"]))
                self.ablage.abschliessen(a["id"], "fertig", sitzung=f"neu-{len(reihenfolge)}")

        self.schritt(lauf)
        self.assertEqual(self.marken(), [])
        self.assertEqual(reihenfolge[0][1:], (self.ende, "s2"))
        self.assertEqual(reihenfolge[1][1:], (reihenfolge[0][0], "neu-1"))
        self.assertEqual((self.stand(erste)["stand"], self.stand(zweite)["stand"]), ("fertig", "fertig"))


class ImAgenten(Aufbau):
    def test_auftrag_landet_im_expose_zweig(self):
        """Der fertige Auftrag läuft durch den echten auftrag_bearbeiten, die Kommentare stehen im Text, start ist die Wurzel."""
        kennung = self.anlegen("Bitte Abschnitt 2 kürzen.", ".pdf", b"%PDF-")
        self.schritt()
        a, = self.ablage.neue(AGENT, dienst=None)
        with mock.patch.object(auftraege, "BASIS", self.ablage.basis), mock.patch.object(agent, "HIER", self.hier), \
                mock.patch.object(agent.kurse, "textfassung") as textfassung, \
                mock.patch.object(agent.kurse, "kommentare_block", return_value="Kommentare in kommentare.pdf: kürzen") as block, \
                mock.patch.object(agent, "expose_auftrag") as bearbeiten:
            self.assertTrue(agent.auftrag_bearbeiten(a))
        textfassung.assert_called_once()
        block.assert_called_once()
        auftrag, start = bearbeiten.call_args.args
        self.assertEqual(start["id"], self.start)
        self.assertEqual(auftrag["sitzung"], "s2")
        self.assertIn("Kommentare in kommentare.pdf: kürzen", auftrag["text"])
        self.assertEqual(self.stand(kennung)["auftrag"], auftrag["id"])

    def test_schritt_folgt_beiden_auftragslaeufen(self):
        code = Path(agent.__file__).read_text(encoding="utf-8")
        schritte = re.search(r"for schritt in \((.*?)\):", code, re.S).group(1).replace("\n", " ")
        namen = [n.strip() for n in schritte.split(",")]
        for i, name in enumerate(namen):
            if name == "auftraege_abarbeiten":
                self.assertEqual(namen[i + 1], "rueckmeldungen_abarbeiten")
        self.assertEqual(namen.count("rueckmeldungen_abarbeiten"), 2)

    def test_agent_gibt_die_echte_ablage_mit(self):
        with mock.patch.object(agent.rueckmeldungen, "abarbeiten") as schritt:
            agent.rueckmeldungen_abarbeiten()
        args = schritt.call_args.args
        self.assertEqual(args[:4], (agent.HIER, agent.AGENT, agent.auftraege, agent.auftraege_abarbeiten))
        self.assertIs(args[4], agent.kurse.kommentare)
        self.assertIs(args[5], agent.melden)

    def test_echte_ablage_kann_was_das_modul_braucht(self):
        for name in ("neue", "erledigte", "erledigter", "neuer_auftrag"):
            self.assertTrue(callable(getattr(auftraege, name)), name)


class Einrichtung(unittest.TestCase):
    def test_pfad_unit_ohne_startschleife(self):
        text = (Path(agent.__file__).parent / "portal" / "systemd" / "uni-portal-rueckmeldung.path").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^PathChanged=/home/agent/agenten/uni/data/projekte/warteschlange$")
        self.assertRegex(text, r"(?m)^Unit=uni\.service$")
        self.assertRegex(text, r"(?m)^MakeDirectory=yes$")
        self.assertNotRegex(text, r"(?m)^DirectoryNotEmpty")


if __name__ == "__main__":
    unittest.main()
