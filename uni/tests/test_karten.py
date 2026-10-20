import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import karten


def karte(**f):
    return {"thema": "pilze", "typ": "text", "frage": "Was ist Würfelbruch?", "antwort": "Risse ...",
            "quelle": "IHS S. 90"} | f


class TestKarten(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.basis = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_bilder_schneiden(self):
        seiten = [Image.new("RGB", (100, 200), farbe) for farbe in ("red", "blue")]
        pdf = self.basis / "infokarten.pdf"
        seiten[0].save(pdf, save_all=True, append_images=seiten[1:])
        paare = karten.bilder_schneiden(pdf, self.basis / "bilder", "pilz")
        self.assertEqual([p.name for p, _ in paare], ["pilz-1-frage.jpg", "pilz-2-frage.jpg"])
        frage, ganz = paare[0]
        with Image.open(ganz) as g, Image.open(frage) as f:
            self.assertEqual(g.size, (100, 200))
            self.assertEqual(f.size[1], int(200 * karten.FOTOS_UNTEN) - int(200 * karten.FOTOS_OBEN))

    def test_id_fest_und_je_thema(self):
        self.assertEqual(karten.karte_id(karte()), karten.karte_id(karte(antwort="anders", frage=" Was ist Würfelbruch? ")))
        self.assertNotEqual(karten.karte_id(karte()), karten.karte_id(karte(thema="gk")))
        self.assertNotEqual(karten.karte_id(karte(typ="bild", bild="b/pilz-1-frage.jpg")),
                            karten.karte_id(karte(typ="bild", bild="b/pilz-2-frage.jpg")))

    def test_pruefen(self):
        (self.basis / "b").mkdir()
        (self.basis / "b" / "pilz-1-frage.jpg").write_bytes(b"x")
        (self.basis / "b" / "pilz-1-ganz.jpg").write_bytes(b"x")
        entwurf = [
            karte(),
            karte(typ="bild", bild="b/pilz-1-frage.jpg"),
            karte(typ="bild", bild="b/pilz-1-ganz.jpg"),   # Lösungsbild statt Fragebild
            karte(typ="bild"),                              # ohne Bild
            karte(thema="unbekannt"),
            karte(typ="lückentext"),
            karte(antwort="  "),
            "keine Karte",
        ]
        gueltig, fehler = karten.pruefen(entwurf, {"pilze"}, self.basis)
        self.assertEqual(len(gueltig), 2)
        self.assertEqual(len(fehler), 6)
        self.assertIsNone(gueltig[0]["bild"])
        self.assertEqual(gueltig[1]["bild"], "b/pilz-1-frage.jpg")
        self.assertEqual(karten.pruefen({"karten": []}, {"pilze"}, self.basis), ([], ["Entwurf ist keine Liste"]))

    def test_uebernehmen_behaelt_alte_und_ueberspringt_doppelte(self):
        alt = {"id": "pilze-alt", "thema": "pilze", "frage": "alt"}
        (self.basis / "karten.json").write_text(json.dumps([alt]), encoding="utf-8")
        gueltig, _ = karten.pruefen([karte(), karte(), karte(frage="Zweite?")], {"pilze"}, self.basis)
        self.assertEqual(karten.uebernehmen(self.basis, gueltig), 2)
        self.assertEqual(karten.uebernehmen(self.basis, gueltig), 0)
        ids = [k["id"] for k in json.loads((self.basis / "karten.json").read_text(encoding="utf-8"))]
        self.assertEqual(ids[0], "pilze-alt")
        self.assertEqual(len(ids), 3)


if __name__ == "__main__":
    unittest.main()
