import json
import shutil
import tempfile
import unittest
from pathlib import Path

import agent
import logik
import renderer
import schnittstelle
from agentkit import auftraege, claude_lauf, fassungen

LIA = Path(__file__).resolve().parents[2]
BLATT = {"art": "arbeitsblatt", "titel": "Warum strafen wir?", "bloecke": [
    {"typ": "anweisung", "text": "Lies den Fall."},
    {"typ": "material", "titel": "Fall", "text": "Tom nimmt ein Fahrrad."},
    {"typ": "aufgaben", "aufgaben": [{"text": "Was ist passiert?"}, {"text": "Wie soll Tom bestraft werden?"}]},
]}
LOESCHEN = json.dumps({"aenderungen": [{"loeschen": "bloecke[0]"}], "antwort": "Anweisung entfernt."})
ZU_GROSS = json.dumps({"zu_gross": "Dafür braucht es neue Quellen."})


class Fake:
    """Ersatz für claude_laufen: liefert die Texte der Reihe nach, merkt sich Prompts und Sitzungen."""

    def __init__(self, *texte, fehler=None):
        self.texte, self.fehler, self.aufrufe = list(texte), fehler, []

    def __call__(self, prompt, lauf_id, sitzung=None, lese=None):
        self.aufrufe.append({"prompt": prompt, "lauf": lauf_id, "sitzung": sitzung, "lese": lese})
        if self.fehler:
            raise self.fehler
        return claude_lauf.Ergebnis(text=self.texte.pop(0), sitzung=f"s{len(self.aufrufe)}", ok=True, usd=0.02)


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        w = Path(self.tmp.name)
        self.agenten, self.basis = w / "lia", w / "lia" / "instanz" / "auftraege"
        for a in ("unterricht", "theater", "schnell"):
            (self.agenten / a).mkdir(parents=True)
        shutil.copy(LIA / "unterricht" / "profil.toml", self.agenten / "unterricht")
        self.daten = self.agenten / "schnell" / "data"
        self.weitergaben, self.gestartet, self.meldungen, self.geloescht = [], [], [], []
        # erledigtes Arbeitsblatt von unterricht, mit Beschreibung wie in data/arbeit/<id>/
        self.ergebnis = auftraege.neuer_auftrag("unterricht", "Arbeitsblatt Strafe", basis=self.basis,
                                                agenten_dir=self.agenten)
        arbeit = self.agenten / "unterricht" / "data" / "arbeit" / self.ergebnis
        arbeit.mkdir(parents=True)
        (arbeit / "beschreibung.json").write_text(json.dumps(BLATT), encoding="utf-8")
        renderer.bauen(BLATT, arbeit / "Arbeitsblatt Strafe.docx", vorschau=False)
        auftraege.abschliessen(self.ergebnis, "fertig", dateien=[arbeit / "Arbeitsblatt Strafe.docx"],
                               basis=self.basis, agenten_dir=self.agenten)

    def tearDown(self):
        self.tmp.cleanup()

    def weitergeben(self, von, an, text, aus, **kw):
        self.weitergaben.append({"von": von, "an": an, "text": text, **kw})
        return f"20261110-120000-{an}-abcdef"

    def umgebung(self, fake, cfg=None):
        return agent.Umgebung(laufen=fake, bauen=lambda b, z, profil=None: renderer.bauen(b, z, profil, vorschau=False),
                              weitergeben=self.weitergeben, starten=self.gestartet.append,
                              melden=self.meldungen.append, loeschen=self.geloescht.append, basis=self.basis,
                              agenten_dir=self.agenten, daten=self.daten,
                              cfg=cfg or {"weitergabe": {"schnell": ["unterricht", "theater"]}})

    def wunsch(self, text="Anweisung weg", **kw):
        return {"id": "a" * 12, "art": "aenderung", "zeit": "", "text": text, "bezug": self.ergebnis, "nr": 0,
                "eigene": None, "seite": None, **kw}


class Aenderung(Basis):
    def test_kleine_aenderung_wird_eigene_fassung(self):
        fake = Fake(LOESCHEN)
        a = agent.bearbeiten(self.wunsch(), self.umgebung(fake))
        self.assertEqual((a["ok"], a["stand"], a["text"], a["usd"]), (True, "fertig", "Anweisung entfernt.", 0.02))
        f = a["fassung"]
        self.assertEqual((f["agent"], f["eigene"], f["name"], f["ursprung"]),
                         ("unterricht", 1, "Arbeitsblatt Strafe.docx", self.ergebnis))
        self.assertTrue((self.agenten / "unterricht" / f["datei"]).is_file())
        stand = fassungen.lesen(self.ergebnis, self.basis)
        self.assertTrue(stand["eigene"][0]["notiz"].startswith("Schnell geändert: Anweisung weg"))
        kopie = self.daten / "fassungen" / self.ergebnis / "eigene-1"
        neu = json.loads((kopie / "beschreibung.json").read_text(encoding="utf-8"))
        self.assertEqual([b["typ"] for b in neu["bloecke"]], ["material", "aufgaben"])
        self.assertTrue((kopie / "Arbeitsblatt Strafe.docx").is_file())
        self.assertIn("Anweisung weg", fake.aufrufe[0]["prompt"])
        self.assertEqual(self.geloescht, ["s1"])
        self.assertEqual(self.weitergaben, [])  # ohne [weitergabe] schnell feedback kein Lernen
        self.assertFalse((self.daten / "arbeit" / ("a" * 12)).exists())

        # zweite Änderung an der schnell geänderten Fassung: baut auf deren Beschreibung auf
        fake2 = Fake(json.dumps({"aenderungen": [{"setzen": "titel", "wert": "Strafe"}], "antwort": "Titel kürzer."}))
        b = agent.bearbeiten(self.wunsch("Titel kürzer", id="b" * 12, eigene=1), self.umgebung(fake2))
        self.assertEqual((b["stand"], b["fassung"]["eigene"]), ("fertig", 2))
        neu2 = json.loads((self.daten / "fassungen" / self.ergebnis / "eigene-2" / "beschreibung.json").read_text())
        self.assertEqual((neu2["titel"], len(neu2["bloecke"])), ("Strafe", 2))

    def test_zu_gross_geht_gruendlich(self):
        a = agent.bearbeiten(self.wunsch("Neue Fälle mit Quellen"), self.umgebung(Fake(ZU_GROSS)))
        self.assertEqual((a["ok"], a["stand"], a["auftrag"]), (True, "gruendlich", "20261110-120000-unterricht-abcdef"))
        w = self.weitergaben[0]
        self.assertEqual((w["an"], w["bezug"], w["nachbesserung"], w["still"], w["dateien"]),
                         ("unterricht", self.ergebnis, True, True, None))
        self.assertIn("Zur Datei „Arbeitsblatt Strafe.docx“: Neue Fälle mit Quellen", w["text"])
        self.assertEqual(self.gestartet, ["unterricht"])
        self.assertEqual(fassungen.lesen(self.ergebnis, self.basis)["eigene"], [])

    def test_zu_gross_an_schnell_geaenderter_fassung_haengt_sie_an(self):
        agent.bearbeiten(self.wunsch(), self.umgebung(Fake(LOESCHEN)))
        agent.bearbeiten(self.wunsch("Neu", id="b" * 12, eigene=1), self.umgebung(Fake(ZU_GROSS)))
        w = self.weitergaben[0]
        self.assertEqual(w["dateien"], [self.daten / "fassungen" / self.ergebnis / "eigene-1" / "Arbeitsblatt Strafe.docx"])
        self.assertIn("schnell geänderte Fassung", w["text"])

    def test_ohne_beschreibung_gleich_gruendlich(self):
        (self.agenten / "unterricht" / "data" / "arbeit" / self.ergebnis / "beschreibung.json").unlink()
        fake = Fake()
        a = agent.bearbeiten(self.wunsch(), self.umgebung(fake))
        self.assertEqual((a["stand"], fake.aufrufe), ("gruendlich", []))

    def test_korrektur_einmal(self):
        falsch = json.dumps({"aenderungen": [{"loeschen": "bloecke[7]"}]})
        fake = Fake(falsch, LOESCHEN)
        a = agent.bearbeiten(self.wunsch(), self.umgebung(fake))
        self.assertEqual(a["stand"], "fertig")
        self.assertEqual(fake.aufrufe[1]["sitzung"], "s1")
        self.assertIn("bloecke[7]", fake.aufrufe[1]["prompt"])
        self.assertEqual(self.geloescht, ["s1", "s2"])

    def test_renderer_lehnt_ab_korrektur_bezieht_sich_auf_geaenderte(self):
        ungueltig = json.dumps({"aenderungen": [{"setzen": "bloecke[0].typ", "wert": "gibtsnicht"}]})
        fake = Fake(ungueltig, json.dumps({"aenderungen": [{"loeschen": "bloecke[0]"}], "antwort": "ok"}))
        a = agent.bearbeiten(self.wunsch(), self.umgebung(fake))
        self.assertEqual(a["stand"], "fertig")
        self.assertIn("nach deinen Änderungen", fake.aufrufe[1]["prompt"])
        self.assertIn("gibtsnicht", fake.aufrufe[1]["prompt"])

    def test_zweimal_ungueltig_geht_gruendlich(self):
        falsch = json.dumps({"aenderungen": [{"loeschen": "bloecke[7]"}]})
        a = agent.bearbeiten(self.wunsch(), self.umgebung(Fake(falsch, falsch)))
        self.assertEqual(a["stand"], "gruendlich")

    def test_art_bleibt(self):
        anders = json.dumps({"beschreibung": {**BLATT, "art": "folien"}})
        a = agent.bearbeiten(self.wunsch(), self.umgebung(Fake(anders, LOESCHEN)))
        self.assertEqual(a["stand"], "fertig")

    def test_lernen_wenn_erlaubt(self):
        cfg = {"weitergabe": {"schnell": ["unterricht", "theater", "feedback"]}}
        agent.bearbeiten(self.wunsch(), self.umgebung(Fake(LOESCHEN), cfg))
        w = self.weitergaben[0]
        self.assertEqual((w["an"], w["bezug"], w["quelle"], w["felder"], w["still"]),
                         ("feedback", self.ergebnis, "feedback", {"feedback_modus": "nur_lernen"}, True))
        self.assertEqual(self.gestartet, ["feedback"])

    def test_unbekannt_und_fehler(self):
        u = self.umgebung(Fake(LOESCHEN))
        for kw in [{"bezug": "20261110-120000-unterricht-000000"}, {"nr": 3}, {"eigene": 4},
                   {"bezug": "20261110-120000-recherche-000000"}]:
            with self.subTest(kw=kw):
                a = agent.bearbeiten(self.wunsch(**kw), u)
                self.assertEqual((a["ok"], a["fehler"]), (False, "ungueltig"))
        a = agent.bearbeiten(self.wunsch(), self.umgebung(Fake(fehler=claude_lauf.LimitErreicht(None))))
        self.assertEqual(a["fehler"], "limit")
        a = agent.bearbeiten(self.wunsch(), self.umgebung(Fake(fehler=claude_lauf.KeinPlatz("voll"))))
        self.assertEqual(a["fehler"], "belegt")
        a = agent.bearbeiten(self.wunsch(), self.umgebung(Fake(fehler=RuntimeError("kaputt"))))
        self.assertEqual(a["fehler"], "technik")
        self.assertTrue(any("kaputt" in m for m in self.meldungen))


class Dokument(Basis):
    def test_schnelles_dokument(self):
        b = {"art": "arbeitsblatt", "titel": "Checkliste Wandertag", "bloecke": [
            {"typ": "anweisung", "text": "Hake ab, was du dabei hast."}]}
        fake = Fake(json.dumps({"beschreibung": b, "antwort": "Eine Checkliste."}))
        quelle = Path(self.tmp.name) / "upload.jpg"
        quelle.write_bytes(b"\xff\xd8\xff")
        wid = schnittstelle.dokument("Checkliste Wandertag", dateien=[("Foto.jpg", quelle)], ordner=self.daten)
        w = agent.wunsch_lesen(self.daten / "wuensche" / f"{wid}.json")
        a = agent.bearbeiten(w, self.umgebung(fake))
        self.assertEqual((a["ok"], a["stand"]), (True, "fertig"))
        self.assertTrue(a["text"].endswith(logik.HINWEIS))
        e = auftraege.erledigter(a["auftrag"], self.basis)
        self.assertEqual((e["status"], e["quelle"], e["daten"]["pruefen"]), ("erledigt", "schnell-dokument",
                                                                             logik.HINWEIS))
        datei = self.agenten / "schnell" / e["ergebnis_dateien"][0]
        self.assertEqual(datei.name, "Arbeitsblatt Checkliste Wandertag.docx")
        self.assertEqual(logik.beschreibung_finden(datei), datei.with_suffix(".json"))
        self.assertEqual(fake.aufrufe[0]["lauf"], a["auftrag"])
        foto = self.agenten / "schnell" / e["dateien"][0]
        self.assertEqual(fake.aufrufe[0]["lese"], [foto.parent])
        self.assertIn(str(foto), fake.aufrufe[0]["prompt"])

        # danach kleine Änderung am schnellen Dokument: eigene Fassung in der Kette von schnell
        fake2 = Fake(json.dumps({"aenderungen": [{"setzen": "titel", "wert": "Wandertag"}], "antwort": "ok"}))
        c = agent.bearbeiten({**self.wunsch(), "bezug": a["auftrag"]}, self.umgebung(fake2))
        self.assertEqual((c["stand"], c["fassung"]["agent"], c["fassung"]["eigene"]), ("fertig", "schnell", 1))
        # zu groß an einem schnellen Dokument: kein gründlicher Agent, Hinweis an Lia
        d = agent.bearbeiten({**self.wunsch(), "bezug": a["auftrag"]}, self.umgebung(Fake(ZU_GROSS)))
        self.assertEqual((d["stand"], self.weitergaben), ("zu_gross", []))
        self.assertIn("unter „Neu“", d["text"])

    def test_falsche_art_und_fehlschlag(self):
        b = {"art": "zusammenfassung", "titel": "X", "bloecke": []}
        a = agent.bearbeiten({"id": "c" * 12, "art": "dokument", "text": "X", "ort": None, "dateien": []},
                             self.umgebung(Fake(json.dumps({"beschreibung": b}), json.dumps({"beschreibung": b}))))
        self.assertEqual((a["ok"], a["fehler"]), (False, "technik"))
        self.assertEqual(auftraege.erledigte("schnell", self.basis)[0]["status"], "fehlgeschlagen")


class Warteschlange(Basis):
    def test_abarbeiten(self):
        wid = schnittstelle.aendern(self.ergebnis, "Anweisung weg", ordner=self.daten)
        (self.daten / "wuensche" / ("f" * 12 + ".json")).write_text("{kaputt")
        self.assertEqual(agent.abarbeiten(self.umgebung(Fake(LOESCHEN))), 1)
        self.assertEqual(schnittstelle.antwort_holen(wid, self.daten)["stand"], "fertig")
        self.assertEqual(schnittstelle.antwort_holen("f" * 12, self.daten)["fehler"], "ungueltig")
        self.assertFalse(schnittstelle.wartet(wid, self.daten))

    def test_aufraeumen(self):
        alt = self.daten / "antworten" / "x.json"
        alt.parent.mkdir(parents=True)
        alt.write_text("{}")
        (self.daten / "arbeit" / "y").mkdir(parents=True)
        self.assertEqual(agent.aufraeumen(self.daten, jetzt=alt.stat().st_mtime + 31 * 86400), 2)


class Einstellungen(unittest.TestCase):
    def test_ohne_werkzeuge(self):
        cfg = {"werkzeuge": {"standard": ["Read"]}, "lauf": {"max_schritte": 30, "max_minuten": 15,
                                                            "warten_minuten": 30}}
        c = agent.lauf_einstellungen(cfg)
        self.assertEqual((c["werkzeuge"]["schnell"], c["lauf"]["max_schritte"], c["lauf"]["warten_minuten"]),
                         ([""], 3, 1))
        self.assertEqual(cfg["lauf"]["max_schritte"], 30)
        self.assertEqual(agent.lauf_einstellungen(cfg, fotos=True)["lauf"]["max_schritte"], 8)


if __name__ == "__main__":
    unittest.main()
