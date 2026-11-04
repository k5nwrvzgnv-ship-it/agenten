import builtins
from datetime import datetime
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import auswertung_agent as agent
import lernmodell
import uebungen
from agentkit import claude_lauf

from tests.hilfe import KOEDER, TRANSKRIPT, agent_ordner

GUT = "bauen die Pilze vor allem die Zellulose ab"
JETZT = datetime(2026, 11, 4, 18, 0)


def gute_antwort(zitat=GUT) -> str:
    return json.dumps({"gesamt": "Geht so.", "punkte": [
        {"id": "r1", "stufe": "teilweise", "begruendung": "Teils.", "zitate": [zitat]},
        {"id": "r2", "stufe": "nicht_geprueft", "begruendung": "Kein Vortrag.", "zitate": []}],
        "luecken": [{"thema": "faeule", "was": "Weißfäule fehlt", "zitat": ""}],
        "karten_neu": [{"thema": "faeule", "frage": "Was baut Weißfäule ab?", "antwort": "Lignin", "quelle": "SHB", "warum": "Lücke"}],
        "karten_faellig": [{"karte": "faeule-1", "warum": "Lücke"}]})


def ergebnis(text=None, ok=True, sitzung="s1", usd=0.2) -> claude_lauf.Ergebnis:
    return claude_lauf.Ergebnis(text=gute_antwort() if text is None else text, sitzung=sitzung, ok=ok, schritte=1, tokens=100, usd=usd, dauer_s=30.0)


class Fall(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.uni = agent_ordner(self.tmp)
        self.modul = self.uni / "data" / "lernen" / "holzschutz"
        self.daten = self.tmp / "portal-data"
        self.id = uebungen.anlegen(self.modul, self.daten, "holzschutz", TRANSKRIPT, "T", JETZT)
        self.ordner = self.modul / "uebungen" / self.id
        self.gemeldet, self.geloescht, self.prompts, self.schlaf = [], [], [], []

    def lauf(self, *antworten, stufe=("normal", None), **kw):
        """abarbeiten mit vorbereiteten Antworten. Eine Ausnahme als Antwort wird geworfen."""
        reihe = list(antworten)

        def fragen(prompt, uebung_id, sitzung=None):
            self.prompts.append((prompt, sitzung))
            antwort = reihe.pop(0)
            if isinstance(antwort, Exception):
                raise antwort
            return antwort

        kw.setdefault("schlafen", self.schlaf.append)
        kw.setdefault("regeltext", lambda: "- Regel von Jan")
        return agent.abarbeiten(self.uni, self.daten, stufe=lambda: stufe, fragen=fragen, melden=self.gemeldet.append,
                                loeschen=self.geloescht.append, **kw)

    def stand(self):
        return uebungen.stand_ansicht(uebungen.stand_lesen(self.ordner), self.daten)

    def auswertung(self):
        return lernmodell.lies_json(self.ordner / "auswertung.json", None)

    def schlange_leer(self):
        self.assertEqual(list((self.daten / "warteschlange").glob("*")), [])


class Ablauf(Fall):
    def test_gut_durch(self):
        self.assertEqual(self.lauf(ergebnis()), 1)
        self.assertEqual(self.stand()["wert"], "fertig")
        a = self.auswertung()
        self.assertEqual(a["punkte"][0]["stufe"], "teilweise")
        self.assertEqual(a["rubrik_summe"], uebungen.rubrik_summe(uebungen.rubrik_lesen(self.modul)))
        self.assertFalse(a["rubrik_bestaetigt_beim_lauf"])  # läuft trotzdem
        s = uebungen.stand_lesen(self.ordner)
        self.assertEqual((s["usd"], s["laeufe"], s["schritte"], s["dauer_s"]), (0.2, 1, 1, 30.0))
        self.assertEqual(self.geloescht, ["s1"])
        self.assertEqual(self.gemeldet, [])
        self.schlange_leer()

    def test_karten_und_lernstand_bleiben_unberuehrt(self):
        karten = (self.modul / "karten.json").read_text(encoding="utf-8")
        self.lauf(ergebnis())
        self.assertEqual((self.modul / "karten.json").read_text(encoding="utf-8"), karten)
        self.assertFalse((self.modul / "zustand.json").exists())
        self.assertFalse((self.modul / "verlauf.jsonl").exists())
        self.assertFalse((self.modul / "vorgemerkt.json").exists())

    def test_prompt_enthaelt_transkript_und_regeln_aber_keine_koeder(self):
        self.lauf(ergebnis())
        prompt = self.prompts[0][0]
        self.assertIn(GUT.split()[0], prompt)
        self.assertIn("- Regel von Jan", prompt)
        self.assertNotIn(KOEDER, prompt)

    def test_liest_nur_die_ablage(self):
        echt, gesehen = builtins.open, set()

        def merken(datei, *a, **k):
            if isinstance(datei, (str, os.PathLike)) and Path(datei).resolve().is_relative_to(self.uni.resolve()):
                gesehen.add(Path(datei).resolve())
            return echt(datei, *a, **k)

        with mock.patch.object(builtins, "open", merken), mock.patch.object(io, "open", merken):
            self.lauf(ergebnis())
        wurzel = self.modul.resolve()
        self.assertTrue(gesehen)
        erlaubt = {wurzel / n for n in ("rubrik.json", "pruefungsplan.json", "karten.json")}
        erlaubt |= {self.ordner.resolve() / n for n in ("transkript.txt", "stand.json", "stand.json.tmp", "auswertung.json", "auswertung.json.tmp")}
        self.assertLessEqual(gesehen, erlaubt)

    def test_nachbesserung_in_derselben_sitzung(self):
        falsch = ergebnis(gute_antwort("Das hat Jan nie so gesagt, wirklich nicht"))
        self.lauf(falsch, ergebnis(sitzung="s1", usd=0.1))
        self.assertEqual(self.prompts[1][1], "s1")
        self.assertIn("nicht wörtlich", self.prompts[1][0])
        self.assertEqual(self.auswertung()["punkte"][0]["stufe"], "teilweise")
        s = uebungen.stand_lesen(self.ordner)
        self.assertEqual(s["laeufe"], 2)
        self.assertAlmostEqual(s["usd"], 0.3)
        self.assertTrue(s["nachbesserung"])

    def test_bleibt_das_zitat_falsch_steht_unbelegt_auf_der_seite(self):
        falsch = gute_antwort("Das hat Jan nie so gesagt, wirklich nicht")
        self.lauf(ergebnis(falsch), ergebnis(falsch))
        a = self.auswertung()
        self.assertEqual(a["punkte"][0]["stufe"], "unbelegt")
        self.assertTrue(a["verworfen"])
        self.assertEqual(self.stand()["wert"], "fertig")
        self.assertEqual(len(self.prompts), 2)  # genau eine Nachbesserung

    def test_zweimal_kein_json_ist_fehlgeschlagen_mit_grund(self):
        self.lauf(ergebnis("kein json"), ergebnis("immer noch nicht"))
        stand = self.stand()
        self.assertEqual(stand["wert"], "fehlgeschlagen")
        self.assertIn("unbrauchbar", stand["grund"])
        self.assertTrue(stand["neu_startbar"])
        self.assertIsNone(self.auswertung())
        self.assertEqual(self.geloescht, ["s1", "s1"])
        self.schlange_leer()

    def test_nachbesserung_faellt_aus_die_erste_antwort_bleibt(self):
        falsch = gute_antwort("Das hat Jan nie so gesagt, wirklich nicht")
        self.lauf(ergebnis(falsch), claude_lauf.LimitErreicht(None))
        self.assertEqual(self.stand()["wert"], "fertig")
        self.assertEqual(self.auswertung()["punkte"][0]["stufe"], "unbelegt")


class Fehler(Fall):
    def test_kontingent_erschoepft_wird_geparkt(self):
        self.assertEqual(self.lauf(claude_lauf.LimitErreicht(1893456000.0)), 1)
        stand = self.stand()
        self.assertEqual((stand["wert"], stand["geparkt"], stand["neu_startbar"]), ("wartet", True, True))
        self.assertIn("Kontingent aufgebraucht", stand["grund"])
        self.assertEqual(self.gemeldet, [])
        self.schlange_leer()

    def test_knappes_kontingent_startet_keinen_lauf(self):
        for wert in ("limit", "nur_auftraege"):
            uebungen.einreihen(self.daten, "holzschutz", self.id)
            self.lauf(stufe=(wert, 1893456000.0))
            self.assertEqual(self.prompts, [], wert)
            self.assertEqual(self.stand()["wert"], "wartet")
            self.assertTrue(self.stand()["geparkt"])
            self.schlange_leer()

    def test_jan_startet_trotz_knappem_kontingent(self):
        uebungen.parken(self.daten, {"id": self.id, "modul": "holzschutz"})
        uebungen.stand_aendern(self.ordner, stand="wartet")
        uebungen.neu_einreihen(self.ordner, self.daten, "holzschutz", self.id, JETZT)
        self.lauf(ergebnis(), stufe=("nur_auftraege", None))
        self.assertEqual(self.stand()["wert"], "fertig")

    def test_aber_nicht_wenn_es_aufgebraucht_ist(self):
        uebungen.einreihen(self.daten, "holzschutz", self.id, erzwingen=True)
        self.lauf(stufe=("limit", None))
        self.assertEqual(self.prompts, [])
        self.assertTrue(self.stand()["geparkt"])

    def test_platz_belegt_zeigt_wartet_und_versucht_neu(self):
        staende = []

        def schlafen(_):
            staende.append(uebungen.stand_lesen(self.ordner)["stand"])

        self.lauf(claude_lauf.KeinPlatz("voll"), claude_lauf.LaeuftSchon("läuft"), ergebnis(), schlafen=schlafen)
        self.assertEqual(staende, ["wartet", "wartet"])
        self.assertEqual(self.stand()["wert"], "fertig")

    def test_platz_lange_belegt_wird_geparkt(self):
        self.lauf(claude_lauf.KeinPlatz("voll"), warten_s=0)
        stand = self.stand()
        self.assertEqual((stand["wert"], stand["geparkt"]), ("wartet", True))
        self.assertIn("belegt", stand["grund"])
        self.schlange_leer()

    def test_zeitueberschreitung(self):
        self.lauf(claude_lauf.Zeitueberschreitung("zu lang"))
        self.assertEqual(self.stand()["wert"], "fehlgeschlagen")
        self.assertIn("länger als", self.stand()["grund"])

    def test_technischer_fehler_meldet_ohne_inhalt(self):
        self.lauf(RuntimeError(TRANSKRIPT))
        self.assertEqual(self.stand()["wert"], "fehlgeschlagen")
        self.assertEqual(len(self.gemeldet), 1)
        self.assertNotIn("Braunfäule", self.gemeldet[0])
        self.assertNotIn("Braunfäule", self.stand()["grund"])

    def test_claude_ohne_brauchbare_antwort(self):
        self.lauf(ergebnis("", ok=False))
        self.assertEqual(self.stand()["wert"], "fehlgeschlagen")
        self.assertEqual(len(self.gemeldet), 1)

    def test_rubrik_fehlt(self):
        (self.modul / "rubrik.json").unlink()
        self.lauf()
        self.assertIn("keine Rubrik", self.stand()["grund"])

    def test_zu_grosser_prompt_startet_keinen_lauf(self):
        (self.ordner / "transkript.txt").write_text("ä" * 70_000, encoding="utf-8")
        self.lauf()
        self.assertEqual(self.prompts, [])
        self.assertIn("zu lang", self.stand()["grund"])

    def test_zu_viele_abgebrochene_starts(self):
        uebungen.stand_aendern(self.ordner, versuche=agent.MAX_VERSUCHE)
        self.lauf()
        self.assertEqual(self.prompts, [])
        self.assertEqual(self.stand()["wert"], "fehlgeschlagen")

    def test_ungueltige_auftraege_verschwinden(self):
        schlange = self.daten / "warteschlange"
        (schlange / "kaputt.json").write_text("{kaputt")
        (schlange / "20261104-100000-abcdef.json").write_text(json.dumps({"id": "20261104-100000-abcdef", "modul": "mails"}))
        (schlange / "20261104-100001-abcdef.json").write_text(json.dumps({"id": "../../mails", "modul": "holzschutz"}))
        (schlange / "20261104-100002-abcdef.json").write_text(json.dumps({"id": "20261104-100002-abcdef", "modul": "holzschutz"}))
        self.lauf(ergebnis())
        self.schlange_leer()
        self.assertEqual(len(self.prompts), 1)

    def test_kommt_waehrend_des_laufs_ein_auftrag_dazu(self):
        zweite = []

        def fragen(prompt, uebung_id, sitzung=None):
            zweite.append(uebung_id)
            if len(zweite) == 1:
                uebungen.anlegen(self.modul, self.daten, "holzschutz", TRANSKRIPT, "Z", datetime(2030, 1, 1))
            return ergebnis()

        agent.abarbeiten(self.uni, self.daten, stufe=lambda: ("normal", None), fragen=fragen, melden=self.gemeldet.append,
                         loeschen=self.geloescht.append, regeltext=lambda: "")
        self.assertEqual(len(zweite), 2)
        self.schlange_leer()


class Einstellungen(unittest.TestCase):
    def test_ohne_werkzeuge_und_ohne_warten(self):
        cfg = {"werkzeuge": {"standard": ["Read", "Write", "Edit"]}, "lauf": {"max_schritte": 30, "max_minuten": 15, "warten_minuten": 30}}
        neu = agent.lauf_einstellungen(cfg)
        self.assertEqual(neu["werkzeuge"][agent.AGENT], [""])
        self.assertEqual(neu["lauf"]["warten_minuten"], 0)
        self.assertEqual(cfg["lauf"]["max_schritte"], 30)  # Original bleibt

    def test_befehl_hat_keine_werkzeuge_und_keinen_fremden_ordner(self):
        cfg = {"werkzeuge": {"standard": ["Read", "Write", "Edit"]}, "lauf": {"max_schritte": 30, "max_minuten": 15, "warten_minuten": 30}}
        befehl = claude_lauf.befehl(agent.AGENT, agent.HIER, "p", "opus", agent.lauf_einstellungen(cfg))
        start = befehl.index("--tools")
        self.assertEqual(befehl[start + 1], "")
        self.assertNotIn("Bash", " ".join(befehl[start:start + 2]))
        self.assertNotIn("Write", befehl[start + 1])

    def test_name_passt_zu_meldungen(self):
        from agentkit import _ablage
        _ablage.pruefe_agent(agent.AGENT)

    def test_regeln_von_uni_stehen_im_prompt_bereit(self):
        text = agent._regeln_von_uni()
        self.assertIn("KI-Richtlinie", text)
        self.assertIn("Prüfungstermine", text)

    def test_eigene_sperre(self):
        self.assertEqual(agent.HIER.name, "portal")
        self.assertNotEqual(agent.HIER / "data" / "lauf.lock", agent.UNI / "data" / "lauf.lock")


if __name__ == "__main__":
    unittest.main()
