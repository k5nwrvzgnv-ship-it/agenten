import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from agentkit import ereignis


def ts(text: str) -> float:
    return datetime.fromisoformat(text).timestamp()


class TestEreignis(unittest.TestCase):
    def setUp(self):
        self.ordner = Path(tempfile.mkdtemp()) / "ereignisse"

    def schreib(self, typ, zeit="2026-10-28T10:00:00", **kw):
        return ereignis.schreiben(typ, "uni", ordner=self.ordner, jetzt=ts(zeit), **kw)

    def test_schreiben_und_lesen(self):
        a = self.schreib("lauf.gestartet", lauf="l1", daten={"modell": "sonnet"})
        b = self.schreib("lauf.beendet", lauf="l1", daten={"ok": True, "tokens": 5})
        self.assertEqual(a, "2026-10-28:0")
        alle = ereignis.lesen(ordner=self.ordner, heute=date(2026, 10, 28))
        self.assertEqual([e["id"] for e in alle], [a, b])
        self.assertEqual(alle[0]["daten"], {"modell": "sonnet"})
        self.assertEqual((alle[1]["agent"], alle[1]["lauf"], alle[1]["auftrag"]), ("uni", "l1", None))

    def test_seit_setzt_genau_dahinter_fort_auch_ueber_tage(self):
        a = self.schreib("x1")
        self.schreib("x2")
        self.schreib("x3", zeit="2026-10-29T08:00:00")
        typen = [e["typ"] for e in ereignis.lesen(seit=a, ordner=self.ordner)]
        self.assertEqual(typen, ["x2", "x3"])
        letzte = ereignis.lesen(ordner=self.ordner, heute=date(2026, 10, 29))[-1]["id"]
        self.assertEqual(ereignis.lesen(seit=letzte, ordner=self.ordner), [])

    def test_tage_begrenzen_den_rueckblick(self):
        self.schreib("alt", zeit="2026-10-20T10:00:00")
        self.schreib("neu")
        typen = [e["typ"] for e in ereignis.lesen(tage=2, ordner=self.ordner, heute=date(2026, 10, 28))]
        self.assertEqual(typen, ["neu"])

    def test_texte_werden_gekuerzt(self):
        self.schreib("x", daten={"grund": "a" * 500, "liste": ["b" * 300]})
        d = ereignis.lesen(ordner=self.ordner, heute=date(2026, 10, 28))[0]["daten"]
        self.assertEqual(len(d["grund"]), ereignis.MAX_TEXT)
        self.assertEqual(len(d["liste"][0]), ereignis.MAX_TEXT)

    def test_kaputte_und_halbe_zeilen_werden_uebersprungen(self):
        self.schreib("x1")
        datei = self.ordner / "2026-10-28.jsonl"
        with open(datei, "a") as f:
            f.write("kein json\n")
        self.schreib("x2")
        with open(datei, "a") as f:
            f.write('{"typ": "halb"')
        typen = [e["typ"] for e in ereignis.lesen(ordner=self.ordner, heute=date(2026, 10, 28))]
        self.assertEqual(typen, ["x1", "x2"])

    def test_fehler_beim_schreiben_wirft_nicht(self):
        datei = Path(tempfile.mkdtemp()) / "datei"
        datei.write_text("")
        with self.assertLogs("agentkit.ereignis", "WARNING"):
            self.assertIsNone(ereignis.schreiben("x", "uni", ordner=datei / "unter"))

    def test_unsinnige_id(self):
        with self.assertRaises(ValueError):
            ereignis.lesen(seit="gestern:0", ordner=self.ordner)

    def test_ohne_ordner_leer(self):
        self.assertEqual(ereignis.lesen(ordner=self.ordner), [])
        self.assertEqual(ereignis.aufraeumen(ordner=self.ordner), [])

    def test_aufraeumen(self):
        self.schreib("alt", zeit="2026-09-20T10:00:00")
        self.schreib("neu")
        weg = ereignis.aufraeumen(tage=30, ordner=self.ordner, heute=date(2026, 10, 28))
        self.assertEqual(weg, ["2026-09-20.jsonl"])
        self.assertEqual(sorted(p.name for p in self.ordner.iterdir()), ["2026-10-28.jsonl"])

    def test_instanz_wird_mitgeschrieben(self):
        with mock.patch.object(ereignis.config, "INSTANZ_NAME", "lia"):
            self.schreib("x")
        self.assertEqual(ereignis.lesen(ordner=self.ordner, heute=date(2026, 10, 28))[0]["instanz"], "lia")


if __name__ == "__main__":
    unittest.main()
