import json
import os
import tempfile
import time
import unittest
from datetime import timedelta
from pathlib import Path

import agent
import gespraechablage as ga
import gespraechlauf
import kontext
import schnittstelle as sch
from agentkit import claude_lauf, struktur

NEU = ('[[fach]]\nid = "ethik"\nname = "Ethik"\n\n'
       '[[klasse]]\nid = "ethik-8"\nfach = "ethik"\nname = "8"\n\n'
       '[[klasse]]\nid = "ethik-kurs-11"\nfach = "ethik"\nname = "Kurs 11"\n\n'
       '[[reihe]]\nid = "ethik-8-strafe"\nklasse = "ethik-8"\ntitel = "Strafe"\nreihenfrage = "Warum strafen wir?"\n\n'
       '[[reihe.stunde]]\nid = "s-1"\nthema = "Einstieg"\n\n'
       '[[reihe.stunde]]\nid = "s-2"\nthema = "Vergeltung"\n')
REIHE = {"ebene": "reihe", "id": "ethik-8-strafe"}
STUNDE = {"ebene": "stunde", "id": "s-2"}
KLASSE = {"ebene": "klasse", "id": "ethik-kurs-11"}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


class Fake:
    """Ersatz für gespraechlauf.claude_gespraech: merkt sich Aufrufe, liefert Ergebnisse der Reihe nach."""

    def __init__(self, *texte, fehler=None, sitzung="sitz-1"):
        self.texte, self.fehler, self.sitzung, self.aufrufe = list(texte) or ["Antwort."], fehler, sitzung, []

    def __call__(self, prompt, **kw):
        self.aufrufe.append({"prompt": prompt, **kw})
        if self.fehler:
            raise self.fehler
        text = self.texte.pop(0) if len(self.texte) > 1 else self.texte[0]
        sitzung = kw.get("sitzung") if not kw.get("neu", True) else self.sitzung
        return claude_lauf.Ergebnis(text=text, sitzung=sitzung, ok=bool(text))


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        w = Path(self.tmp.name)
        self.instanz, self.daten, self.sitzungen, self.upload = w / "instanz", w / "data", w / "sitz", w / "up"
        for o in (self.instanz, self.sitzungen, self.upload):
            o.mkdir()
        (self.instanz / "reihen.toml").write_text(NEU, encoding="utf-8")
        self.meldungen = []

    def tearDown(self):
        self.tmp.cleanup()

    def hochladen(self, name, inhalt=PNG):
        p = self.upload / name
        p.write_bytes(inhalt)
        return (name, p)

    def abarbeiten(self, fake):
        """Wie der Dienst: alles aus data/fragen/; die Fake-Sitzung legt die Sitzungsdatei an wie claude."""
        def claude(prompt, **kw):
            e = fake(prompt, **kw)
            if e.sitzung:
                (self.sitzungen / f"{e.sitzung}.jsonl").write_text("{}")
            return e
        return agent.fragen_abarbeiten(self.instanz, self.daten, gespraech_kw={
            "claude": claude, "melden": self.meldungen.append, "sitzungen": self.sitzungen,
            "sonder_sitzungen": self.sitzungen, "netz_an": lambda: True})


class Ablage(Basis):
    def test_anlegen_liste_umbenennen_umhaengen_loeschen(self):
        a = sch.gespraech_anlegen("Strafe", REIHE, ordner=self.daten)
        b = sch.gespraech_anlegen("", None, ordner=self.daten)
        self.assertEqual([g["id"] for g in sch.gespraeche(REIHE, self.daten)], [a])
        self.assertEqual([g["id"] for g in sch.gespraeche(sch.OHNE_ORT, self.daten)], [b])
        self.assertEqual({g["id"] for g in sch.gespraeche(ordner=self.daten)}, {a, b})
        self.assertEqual({g["id"]: g["name"] for g in sch.gespraeche(ordner=self.daten)}[b], "Neues Gespräch")
        sch.umbenennen(a, "  Strafe   und Schuld ", self.daten)
        sch.umhaengen(a, KLASSE, self.daten)
        g = sch.gespraech(a, self.daten)
        self.assertEqual((g["name"], g["ort"], g["laeuft"]), ("Strafe und Schuld", KLASSE, False))
        self.assertNotIn("sitzung", g)
        self.assertEqual(oct(ga.datei(a, self.daten).stat().st_mode & 0o777), "0o600")
        self.assertTrue(sch.loeschen(a, self.daten))
        self.assertFalse(sch.loeschen(a, self.daten))
        self.assertIsNone(sch.gespraech(a, self.daten))
        with self.assertRaises(sch.GespraechFehler):
            sch.umbenennen(a, "x", self.daten)

    def test_ort_und_name_pruefen(self):
        for ort in ({"ebene": "fach", "id": "ethik"}, {"ebene": "reihe"}, {"ebene": "reihe", "id": "../x"},
                    {"ebene": "reihe", "id": "a", "chip": "x"}, "reihe"):
            with self.assertRaises(sch.GespraechFehler):
                sch.gespraech_anlegen("x", ort, ordner=self.daten)
        with self.assertRaises(sch.GespraechFehler):
            sch.gespraech_anlegen("x" * 81, None, ordner=self.daten)
        self.assertIsNone(sch.gespraech("../../etc", self.daten))

    def test_name_aus_erster_nachricht(self):
        g = sch.gespraech_anlegen("", REIHE, ordner=self.daten)
        sch.nachricht(g, "## Wie leite ich eine Diskussion über Strafe in einer achten Klasse an?\nMehr", ordner=self.daten)
        name = sch.gespraech(g, self.daten)["name"]
        self.assertTrue(name.startswith("Wie leite ich eine Diskussion") and name.endswith("…"), name)
        self.assertLessEqual(len(name), 52)

    def test_nachricht_grenzen(self):
        g = sch.gespraech_anlegen("x", None, ordner=self.daten)
        with self.assertRaises(sch.GespraechFehler):
            sch.nachricht(g, "  ", ordner=self.daten)
        with self.assertRaises(sch.GespraechFehler):
            sch.nachricht(g, "x" * 60_001, ordner=self.daten)
        with self.assertRaises(sch.GespraechFehler) as f:
            sch.nachricht(g, "Foto", [self.hochladen("bild.HEIC")], ordner=self.daten)
        self.assertIn("HEIC", str(f.exception))
        with self.assertRaises(sch.GespraechFehler):
            sch.nachricht(g, "Fotos", [self.hochladen(f"b{i}.jpg") for i in range(6)], ordner=self.daten)
        with self.assertRaises(sch.GespraechFehler):
            sch.nachricht(g, "Excel", [self.hochladen("t.xlsx")], ordner=self.daten)
        with self.assertRaises(sch.GespraechFehler):
            sch.nachricht("0" * 12, "x", ordner=self.daten)
        # bei Fehlern bleibt alles liegen, nichts in der Warteschlange
        self.assertTrue((self.upload / "b0.jpg").exists())
        self.assertFalse((self.daten / "fragen").exists() and any((self.daten / "fragen").iterdir()))
        nid = sch.nachricht(g, "x" * 60_000, [self.hochladen(f"b{i}.png") for i in range(5)], ordner=self.daten)
        self.assertTrue((ga.dateien_ordner(g, self.daten) / nid / "b4.png").exists())
        self.assertFalse((self.upload / "b4.png").exists())
        with self.assertRaises(sch.GespraechFehler) as f:  # eine Nachricht nach der anderen
            sch.nachricht(g, "Noch was", ordner=self.daten)
        self.assertIn("antwortet noch", str(f.exception))
        self.assertTrue(sch.gespraech(g, self.daten)["laeuft"])

    def test_sonderlauf_braucht_inhalt(self):
        g = sch.gespraech_anlegen("x", None, ordner=self.daten)
        with self.assertRaises(sch.GespraechFehler):
            sch.bisher(g, self.daten)


class Ablauf(Basis):
    def test_drei_nachrichten_mit_foto_und_fortsetzen(self):
        g = sch.gespraech_anlegen("", STUNDE, ordner=self.daten)
        n1 = sch.nachricht(g, "Was ist Vergeltung?", ordner=self.daten)
        fake = Fake("Erste.", "Zweite.", "Dritte.")
        self.assertEqual(self.abarbeiten(fake), 1)
        a = sch.antwort_holen(n1, self.daten)
        self.assertEqual((a["ok"], a["text"], a["art"], a["gespraech"]), (True, "Erste.", "nachricht", g))
        self.assertEqual(a["chip"], "Ethik › 8 › Strafe › Stunde 2")
        p1 = fake.aufrufe[0]
        self.assertTrue(p1["neu"])
        self.assertIn("baustein <art>", p1["prompt"])
        self.assertIn("Reihenfrage: Warum strafen wir?", p1["prompt"])
        self.assertIn("Gerade offen: Stunde 2: Vergeltung", p1["prompt"])
        self.assertEqual(p1["fotos"], 0)
        # zweite mit Foto: Sitzung fortgesetzt, ohne Grundtext, Foto als Pfad im Gesprächsordner
        n2 = sch.nachricht(g, "Was hältst du davon?", [self.hochladen("tafel.jpg")], ordner=self.daten)
        self.abarbeiten(fake)
        p2 = fake.aufrufe[1]
        self.assertEqual((p2["neu"], p2["sitzung"], p2["fotos"]), (False, "sitz-1", 1))
        self.assertNotIn("baustein <art>", p2["prompt"])
        self.assertNotIn("Reihenfrage", p2["prompt"])
        foto = ga.dateien_ordner(g, self.daten) / n2 / "tafel.jpg"
        self.assertIn(str(foto), p2["prompt"])
        self.assertEqual(p2["lese_ordner"], ga.dateien_ordner(g, self.daten))
        # dritte nach Umhängen: neuer Ort geht mit
        sch.umhaengen(g, KLASSE, self.daten)
        sch.nachricht(g, "Und für Kurs 11?", ordner=self.daten, gruendlich=True)
        self.abarbeiten(fake)
        p3 = fake.aufrufe[2]
        self.assertIn("jetzt an einem anderen Ort", p3["prompt"])
        self.assertIn("Kurs 11", p3["prompt"])
        self.assertTrue(p3["gruendlich"])
        voll = sch.gespraech(g, self.daten)
        self.assertEqual([(e["rolle"], e["text"]) for e in voll["eintraege"]],
                         [("lia", "Was ist Vergeltung?"), ("claude", "Erste."), ("lia", "Was hältst du davon?"),
                          ("claude", "Zweite."), ("lia", "Und für Kurs 11?"), ("claude", "Dritte.")])
        self.assertEqual(voll["eintraege"][2]["fotos"], ["tafel.jpg"])
        self.assertFalse(voll["laeuft"])
        self.assertTrue(sch.gespraeche(ordner=self.daten)[0]["neu"])
        sch.gesehen(g, self.daten)
        self.assertFalse(sch.gespraeche(ordner=self.daten)[0]["neu"])
        self.assertFalse(any((self.daten / "fragen").iterdir()))

    def test_verlorene_sitzung_geht_mit_verlauf_neu(self):
        g = sch.gespraech_anlegen("x", None, ordner=self.daten)
        sch.nachricht(g, "Erste Frage", ordner=self.daten)
        fake = Fake("Eins.", "Zwei.", sitzung="sitz-a")
        self.abarbeiten(fake)
        (self.sitzungen / "sitz-a.jsonl").unlink()
        sch.nachricht(g, "Zweite Frage", ordner=self.daten)
        self.abarbeiten(fake)
        p = fake.aufrufe[1]
        self.assertTrue(p["neu"])
        self.assertIn("Bisheriger Verlauf", p["prompt"])
        self.assertIn("Lia: Erste Frage", p["prompt"])
        self.assertIn("Claude: Eins.", p["prompt"])
        self.assertIn("keinen Ort", p["prompt"])

    def test_fortsetzen_ohne_antwort_versucht_neu(self):
        g = sch.gespraech_anlegen("x", None, ordner=self.daten)
        sch.nachricht(g, "Erste", ordner=self.daten)
        self.abarbeiten(Fake("Eins."))
        sch.nachricht(g, "Zweite", ordner=self.daten)
        fake = Fake("", "Zwei.", sitzung="sitz-2")
        self.abarbeiten(fake)
        self.assertEqual([a["neu"] for a in fake.aufrufe], [False, True])
        self.assertEqual(json.loads(ga.datei(g, self.daten).read_text())["sitzung"], "sitz-2")

    def test_fehler_landen_als_satz_und_nicht_im_verlauf(self):
        g = sch.gespraech_anlegen("x", None, ordner=self.daten)
        nid = sch.nachricht(g, "Frage", ordner=self.daten)
        self.abarbeiten(Fake(fehler=claude_lauf.LimitErreicht(None)))
        a = sch.antwort_holen(nid, self.daten)
        self.assertEqual((a["ok"], a["fehler"]), (False, "limit"))
        self.assertIn("Rechenzeit", a["text"])
        voll = sch.gespraech(g, self.daten)
        self.assertEqual([(e["rolle"], e["stand"]) for e in voll["eintraege"]], [("lia", "fehler")])
        self.assertFalse(voll["laeuft"])
        nid = sch.nachricht(g, "Nochmal", ordner=self.daten)  # danach geht die nächste
        self.abarbeiten(Fake(fehler=RuntimeError("kaputt")))
        self.assertEqual(sch.antwort_holen(nid, self.daten)["fehler"], "technik")
        self.assertTrue(any("kaputt" in m for m in self.meldungen))

    def test_geloescht_waehrend_warten(self):
        g = sch.gespraech_anlegen("x", None, ordner=self.daten)
        nid = sch.nachricht(g, "Frage", ordner=self.daten)
        sch.loeschen(g, self.daten)
        fake = Fake()
        self.abarbeiten(fake)
        self.assertEqual(fake.aufrufe, [])
        self.assertEqual(sch.antwort_holen(nid, self.daten)["fehler"], "ungueltig")

    def test_sonderlaeufe_nicht_im_verlauf(self):
        g = sch.gespraech_anlegen("x", REIHE, ordner=self.daten)
        sch.nachricht(g, "Ideen für einen Einstieg?", ordner=self.daten)
        self.abarbeiten(Fake("Ein Fallbeispiel."))
        fake = Fake("### Entschieden\n- Fall", "Ich möchte ein Arbeitsblatt …", sitzung="sonder")
        b = sch.bisher(g, self.daten)
        self.assertEqual(self.abarbeiten(fake), 1)
        a = sch.auftrag_ordnen(g, self.daten)
        self.assertEqual(self.abarbeiten(fake), 1)
        self.assertEqual(sch.antwort_holen(b, self.daten)["art"], "bisher")
        self.assertEqual(sch.antwort_holen(a, self.daten)["text"], "Ich möchte ein Arbeitsblatt …")
        self.assertTrue(all(x["sonder"] and x.get("fotos", 0) == 0 for x in fake.aufrufe))
        self.assertIn("Lia: Ideen für einen Einstieg?", fake.aufrufe[0]["prompt"])
        self.assertIn("### Entschieden", fake.aufrufe[0]["prompt"])
        self.assertIn("Ich-Form", fake.aufrufe[1]["prompt"])
        self.assertEqual(len(sch.gespraech(g, self.daten)["eintraege"]), 2)
        self.assertFalse((self.sitzungen / "sonder.jsonl").exists())  # Sitzung des Sonderlaufs gleich weg
        self.assertTrue((self.sitzungen / "sitz-1.jsonl").exists())

    def test_ablage_der_ebenen_einmal_mitgeben(self):
        for oid, name in (("ethik-8", "plan.png"), ("ethik-8-strafe", "notiz.pdf"), ("s-2", "skizze.jpg"),
                          ("s-1", "fremd.png")):
            (self.instanz / "ablage" / oid).mkdir(parents=True)
            (self.instanz / "ablage" / oid / name).write_bytes(PNG)
        g = sch.gespraech_anlegen("x", STUNDE, ordner=self.daten)
        sch.nachricht(g, "Schau dir das an", ordner=self.daten)
        fake = Fake()
        self.abarbeiten(fake)
        p = fake.aufrufe[0]
        self.assertEqual(p["fotos"], 2)
        kopie = ga.dateien_ordner(g, self.daten) / "ablage" / "s-2" / "skizze.jpg"
        self.assertTrue(kopie.exists())
        self.assertIn(str(kopie), p["prompt"])
        self.assertIn("--- Abgelegt: notiz.pdf", p["prompt"])  # kaputtes PDF: Satz statt Text
        self.assertIn("ließ sich nicht lesen", p["prompt"])
        self.assertNotIn("fremd.png", p["prompt"])
        sch.nachricht(g, "Weiter", ordner=self.daten)
        self.abarbeiten(fake)
        self.assertNotIn("Abgelegt", fake.aufrufe[1]["prompt"])
        self.assertEqual(fake.aufrufe[1]["fotos"], 0)
        neu = self.instanz / "ablage" / "ethik-8-strafe" / "neu.png"
        neu.write_bytes(PNG)
        sch.nachricht(g, "Und das?", ordner=self.daten)
        self.abarbeiten(fake)
        self.assertIn("Neu am Ort abgelegt", fake.aufrufe[2]["prompt"])
        self.assertIn("neu.png", fake.aufrufe[2]["prompt"])
        self.assertNotIn("skizze.jpg", fake.aufrufe[2]["prompt"])

    def test_prompt_bleibt_unter_128_kb(self):
        g = sch.gespraech_anlegen("x", None, ordner=self.daten)
        sch.nachricht(g, "ä" * 60_000, ordner=self.daten)
        self.abarbeiten(Fake())
        (self.sitzungen / "sitz-1.jsonl").unlink()  # Verlauf muss dann als Text mit
        sch.nachricht(g, "ö" * 50_000, ordner=self.daten)
        fake = Fake()
        self.abarbeiten(fake)
        self.assertLessEqual(len(fake.aufrufe[0]["prompt"].encode()), gespraechlauf.PROMPT_BYTES + 1000)
        self.assertIn("ö" * 50_000, fake.aufrufe[0]["prompt"])

    def test_aufraeumen_nach_30_tagen(self):
        alt_, frisch = (sch.gespraech_anlegen(n, None, ordner=self.daten) for n in ("alt", "frisch"))
        for gid, sitz in ((alt_, "s-alt"), (frisch, "s-frisch")):
            with ga.sperre(self.daten):
                g = ga.lesen(gid, self.daten)
                g["sitzung"] = sitz
                if gid == alt_:
                    g["zuletzt"] = (ga.jetzt() - timedelta(days=31)).isoformat()
                ga.schreiben(g, self.daten)
            (self.sitzungen / f"{sitz}.jsonl").write_text("{}")
        (ga.dateien_ordner(alt_, self.daten) / "x").mkdir(parents=True)
        lose = self.sitzungen / "lose.jsonl"
        lose.write_text("{}")
        os.utime(lose, (time.time() - 7200,) * 2)
        os.utime(self.sitzungen / "s-alt.jsonl", (time.time() - 7200,) * 2)
        jung = self.sitzungen / "laeuft-gerade.jsonl"
        jung.write_text("{}")
        agent.aufraeumen(self.daten, self.sitzungen, self.sitzungen)
        self.assertIsNone(sch.gespraech(alt_, self.daten))
        self.assertFalse(ga.dateien_ordner(alt_, self.daten).exists())
        self.assertIsNotNone(sch.gespraech(frisch, self.daten))
        self.assertEqual(sorted(p.name for p in self.sitzungen.iterdir()), ["laeuft-gerade.jsonl", "s-frisch.jsonl"])

    def test_alte_frage_laeuft_weiter(self):
        fid = sch.frage_stellen("Alte Spalte?", None, ordner=self.daten)
        geloescht = []

        def fragen(prompt, gruendlich, frage_id, netz=False):
            return claude_lauf.Ergebnis(text="Alt.", sitzung="x", ok=True)
        agent.fragen_abarbeiten(self.instanz, self.daten, fragen=fragen, melden=self.meldungen.append,
                                loeschen=geloescht.append)
        self.assertEqual(sch.antwort_holen(fid, self.daten)["text"], "Alt.")


class Kontext(unittest.TestCase):
    def setUp(self):
        self.s = struktur.aus_text(NEU)

    def test_ebenen(self):
        chip, text = kontext.ort_kontext(KLASSE, self.s)
        self.assertEqual(chip, "Ethik › Kurs 11")
        self.assertIn("Reihen: noch keine", text)
        chip, text = kontext.ort_kontext({"ebene": "klasse", "id": "ethik-8"}, self.s)
        self.assertIn("Strafe (laufend): Warum strafen wir?", text)
        chip, text = kontext.ort_kontext(REIHE, self.s)
        self.assertEqual(chip, "Ethik › 8 › Strafe")
        self.assertIn("Stunden: 1. Einstieg; 2. Vergeltung", text)
        self.assertNotIn("Gerade offen", text)
        self.assertIn("nicht mehr", kontext.ort_kontext({"ebene": "reihe", "id": "s-1"}, self.s)[1])
        self.assertIn("nicht mehr", kontext.ort_kontext(REIHE, None)[1])
        self.assertEqual(kontext.ort_kontext(None, self.s), ("", ""))

    def test_ablage_ids(self):
        self.assertEqual(kontext.ablage_ids(STUNDE, self.s), ["ethik", "ethik-8", "ethik-8-strafe", "s-2"])
        self.assertEqual(kontext.ablage_ids(KLASSE, self.s), ["ethik", "ethik-kurs-11"])
        self.assertEqual(kontext.ablage_ids(None, self.s), [])

    def test_verlauf_kuerzt_von_vorn(self):
        e = [{"rolle": "lia", "text": "a" * 100}, {"rolle": "claude", "text": "b" * 100},
             {"rolle": "lia", "text": "c", "stand": "fehler"}]
        text = kontext.verlauf_text(e, grenze=150)
        self.assertTrue(text.startswith("[Die ältesten"))
        self.assertNotIn("a" * 100, text)
        self.assertNotIn("Lia: c", kontext.verlauf_text(e))

    def test_werkzeughinweis(self):
        p = kontext.gespraech_prompt("x", erste=False, gruendlich=False, netz=False, vorher_netz=True)
        self.assertIn("keine Websuche", p)
        p = kontext.gespraech_prompt("x", erste=False, gruendlich=False, netz=True)
        self.assertIn("Quellen:", p)

    def test_einstellungen(self):
        cfg = {"werkzeuge": {}, "lauf": {}, "webfetch": {"recherche": ["kmk.org"]}}
        c = gespraechlauf.lauf_einstellungen(False, False, 0, cfg)
        self.assertEqual(c["werkzeuge"]["chat"], [""])
        c = gespraechlauf.lauf_einstellungen(True, True, 2, cfg)
        self.assertEqual(c["werkzeuge"]["chat"], ["WebSearch", "WebFetch", "Read"])
        self.assertEqual((c["lauf"]["max_schritte"], c["lauf"]["max_minuten"]), (13, 10))
        c = gespraechlauf.lauf_einstellungen(False, True, 2, cfg, sonder=True)
        self.assertEqual(c["werkzeuge"]["chat"], [""])


if __name__ == "__main__":
    unittest.main()
