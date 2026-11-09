"""Präsentation und Bericht (arten.py) und was der Arbeitsplatz am Ablauf ändert: Claude ersetzt, Renderer-Prüfung echt."""

import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace

import renderer
from renderer.pruefung import lesen

import agent
import arten
import zusammenfassen as z

from tests.test_zusammenfassen import BEISPIEL, FalscherClaude

HIER = Path(__file__).resolve().parent.parent
DATEN = Path(__file__).resolve().parent / "daten"
FOLIEN = json.loads((DATEN / "praesentation.json").read_text())
BERICHT = json.loads((DATEN / "bericht.json").read_text())
OK = {"erfunden": [], "auftrag": [], "darstellung": []}
KURZ = {"kern": "Fünf Folien zur Holzfeuchte.", "punkte": ["Darrmethode", "Fazit"], "pruefen": "Messwerte ergänzen"}
FORMAT_MD = (HIER.parent / "shared/renderer/FORMAT.md").read_text()


def falsch_bauen(beschreibung, ziel):
    """Prüft echt, baut Platzhalter; der Kontrolltext ist die Beschreibung (enthält die [OFFEN: …])."""
    lesen(beschreibung)
    ziel.write_text("datei")
    vorschau = ziel.parent / f"{ziel.stem}-vorschau"
    vorschau.mkdir(exist_ok=True)
    (vorschau / f"{ziel.stem}.pdf").write_text("pdf")
    bilder = []
    for i in range(1, len(beschreibung.get("folien", [])) + 2):
        bilder.append(vorschau / f"{ziel.stem}-seite-{i:02d}.png")
        bilder[-1].write_text("png")
    return SimpleNamespace(pdf=vorschau / f"{ziel.stem}.pdf", bilder=bilder,
                           kontrolltext=json.dumps(beschreibung, ensure_ascii=False), hinweise=[])


class TestReineLogik(unittest.TestCase):
    def test_bericht_ok(self):
        self.assertEqual(arten.bericht_pruefen(json.dumps(OK)), [])

    def test_bericht_probleme(self):
        text = "\n".join(arten.bericht_pruefen(json.dumps(
            {"erfunden": ["Messwert 12 %"], "auftrag": ["Zielgruppe nicht beachtet"], "darstellung": "x", "notiz": 1})))
        for teil in ("Unbekannte Felder: notiz", "Dazuerfunden: Messwert 12 %",
                     "Auftrag nicht umgesetzt: Zielgruppe nicht beachtet", "darstellung muss eine Liste sein"):
            self.assertIn(teil, text)
        self.assertIn("Felder fehlen: auftrag, darstellung", arten.bericht_pruefen('{"erfunden": []}')[0])
        self.assertEqual(arten.bericht_pruefen(None), ["kontrolle.json fehlt"])
        self.assertIn("kein gültiges JSON", arten.bericht_pruefen("{")[0])
        self.assertIn("Objekt", arten.bericht_pruefen("[]")[0])

    def test_offene_stellen(self):
        self.assertEqual(z.offene_stellen("a [OFFEN: Zeitraum] b [OFFEN: Betrieb] [OFFEN: Zeitraum] [offen: x]"),
                         ["[OFFEN: Zeitraum]", "[OFFEN: Betrieb]"])
        self.assertEqual(z.offene_stellen("nichts"), [])

    def test_kurz_lesen(self):
        self.assertEqual(z.kurz_lesen(json.dumps(KURZ)), KURZ)
        self.assertEqual(z.kurz_lesen('{"kern": " k "}'), {"kern": "k", "punkte": [], "pruefen": ""})
        for kaputt in (None, "{", "[]", '{"kern": ""}', '{"kern": "k", "punkte": "x"}', '{"kern": "k", "punkte": [1]}',
                       '{"kern": "k", "pruefen": 3}'):
            self.assertIsNone(z.kurz_lesen(kaputt), kaputt)
        self.assertEqual(len(z.kurz_lesen(json.dumps({"kern": "k", "punkte": ["p"] * 20}))["punkte"]), 8)

    def test_umfang(self):
        self.assertEqual(z.umfang_zahl("10 Folien"), 10)
        self.assertEqual(z.umfang_zahl("ca. 5 Seiten"), 5)
        self.assertIsNone(z.umfang_zahl("kurz"))
        self.assertIsNone(z.umfang_zahl(None))
        self.assertIsNone(z.umfang_zahl("0 Seiten"))
        self.assertEqual(z.umfang_abweichung("10 Folien", 8, "Folien"), "")
        self.assertEqual(z.umfang_abweichung("10 Folien", 14, "Folien"), "")
        self.assertEqual(z.umfang_abweichung("10 Folien", 5, "Folien"), "Umfang: gewünscht 10 Folien, es sind 5.")
        self.assertIn("es sind 15", z.umfang_abweichung("10 Folien", 15, "Folien"))
        self.assertEqual(z.umfang_abweichung(None, 3, "Seiten"), "")

    def test_ergebnisdaten(self):
        f = z.Fertig(datei=Path("a/x.pptx"), pdf=Path("a/x.pdf"), titel="Holzfeuchte", seiten=5, kontrollen=1,
                     antwort="\nKurz gesagt: Folien.\nZeile 2", sitzung=None, hinweise=["Schrift ersetzt"],
                     offen=["[OFFEN: Messwerte]"], kurz=KURZ, art="praesentation")
        d = z.ergebnisdaten(f, "10 Folien")
        self.assertEqual(set(d), {"titel", "kern", "punkte", "pruefen"})
        self.assertEqual((d["titel"], d["kern"], d["punkte"]), ("Holzfeuchte", KURZ["kern"], KURZ["punkte"]))
        for teil in ("Messwerte ergänzen", "1 offene Stelle", "gewünscht 10 Folien, es sind 5", "Schrift ersetzt"):
            self.assertIn(teil, d["pruefen"])
        ohne = z.ergebnisdaten(z.Fertig(datei=Path("x.docx"), pdf=Path("x.pdf"), titel="T", seiten=3, kontrollen=1,
                                        antwort="\nKurz gesagt: Bericht.", sitzung=None, art="bericht"))
        self.assertEqual(ohne, {"titel": "T", "kern": "Kurz gesagt: Bericht.", "punkte": [], "pruefen": ""})

    def test_ergebnistext(self):
        f = z.Fertig(datei=Path("x.pptx"), pdf=Path("x.pdf"), titel="Holzfeuchte", seiten=5, kontrollen=2,
                     antwort="Kurzfassung", sitzung=None, offen=["[OFFEN: Messwerte]"], art="praesentation")
        text = z.ergebnistext(f, 0)
        for teil in ("Präsentation „Holzfeuchte“, 5 Folien, pptx und PDF", "2. Runde", "Kurzfassung",
                     "Offen (1): [OFFEN: Messwerte]"):
            self.assertIn(teil, text)

    def test_format_je_art(self):
        folien = z.format_abschnitt(FORMAT_MD, arten.PRAESENTATION.abschnitte)
        self.assertIn("## Folien", folien)
        self.assertNotIn("## Zusammenfassung", folien)
        bericht = z.format_abschnitt(FORMAT_MD, arten.BERICHT.abschnitte)
        for teil in ("## Allgemein", "## Zusammenfassung", "## Bericht"):
            self.assertIn(teil, bericht)
        self.assertNotIn("## Folien", bericht)

    def test_prompts_ohne_reste(self):
        """Grammatik-Marken ersetzt, alle Platzhalter von erstellen bekannt."""
        werte = dict(format="F", herkunft="", text="T", behauptungen="", ordner="o", dateien="", material="m",
                     seiten=1, einheit="Folien", kontrolltext="k", bilder="b", pruefliste="", bericht="B", vorher="",
                     kurz="")
        for art in (arten.PRAESENTATION, arten.BERICHT):
            for prompt in (art.prompt_start, art.prompt_antwort, art.prompt_kontrolle):
                self.assertNotIn("§", prompt)
                prompt.format(**werte)
        self.assertIn("Der Bericht ist gebaut", arten.BERICHT.prompt_kontrolle)
        self.assertIn("den fertigen Bericht", arten.BERICHT.prompt_antwort)
        self.assertIn("[OFFEN:", arten.BERICHT.prompt_start)

    def test_beispiele_und_profile_passen_zum_renderer(self):
        with tempfile.TemporaryDirectory() as tmp:
            for b, endung in ((FOLIEN, ".pptx"), (BERICHT, ".docx")):
                profil = tomllib.loads(agent.PROFILE[b["art"]].read_text())
                e = renderer.bauen(b, Path(tmp) / f"x{endung}", profil=profil, vorschau=False)
                self.assertTrue(e.pfad.is_file())
                self.assertEqual(len(z.offene_stellen(e.kontrolltext)), 1 if b is FOLIEN else 2)

    def test_art_waehlen(self):
        self.assertEqual(agent.art_waehlen({}, {}), (z.ZUSAMMENFASSUNG, False))
        self.assertEqual(agent.art_waehlen({"art": "zusammenfassung"}, {}), (z.ZUSAMMENFASSUNG, True))
        self.assertEqual(agent.art_waehlen({}, {"art": "bericht"}), (arten.BERICHT, True))  # Antwort erbt vom Ursprung
        with self.assertRaises(z.ZusammenfassungFehler) as f:
            agent.art_waehlen({"art": "recherche"}, {})
        self.assertIn("recherche", str(f.exception))


class TestAblauf(unittest.TestCase):
    def setUp(self):
        self.agent_dir = Path(tempfile.mkdtemp())
        self.ordner = self.agent_dir / "data/ausgang/a1"
        self.ordner.mkdir(parents=True)

    def lauf(self, schritte, art=arten.PRAESENTATION, sitzung=None, mit_kurz=True, dateien=None):
        self.claude = FalscherClaude(self.ordner, schritte)
        auftrag = {"id": "a1", "text": "Art: Präsentation\nThema: Holzfeuchte\nUmfang: 5 Folien", "art": art.kennung,
                   "dateien": dateien if dateien is not None else ["data/eingang/a1/notizen.docx"]}
        return z.erstellen(auftrag, self.ordner, self.agent_dir, self.claude, falsch_bauen, "FORMAT", None, sitzung,
                           art=art, mit_kurz=mit_kurz)

    def test_praesentation_gerade_durch(self):
        f = self.lauf([{"beschreibung.json": FOLIEN}, {"kontrolle.json": OK, "kurz.json": KURZ, "antwort": "Kurz"}])
        self.assertEqual(f.datei.name, "holzfeuchte-messen.pptx")
        self.assertTrue(f.pdf.is_file())
        self.assertEqual((f.seiten, f.kontrollen, f.kurz, f.art), (5, 1, KURZ, "praesentation"))
        self.assertEqual(f.offen, ["[OFFEN: Messwerte der Gruppe fehlen im Material]"])
        start, kontrolle = (p for p, _ in self.claude.prompts)
        self.assertIn("Präsentation", start)
        self.assertIn("Material: data/eingang/a1/notizen.docx", start)
        self.assertIn("Umfang: 5 Folien", start)
        self.assertIn("(5 Folien)", kontrolle)
        self.assertIn("data/ausgang/a1/kurz.json", kontrolle)

    def test_ohne_material(self):
        self.lauf([{"beschreibung.json": FOLIEN}, {"kontrolle.json": OK}], dateien=[])
        self.assertIn("Material: keine Dateien", self.claude.prompts[0][0])

    def test_kurz_fehlt_oder_kaputt(self):
        f = self.lauf([{"beschreibung.json": FOLIEN}, {"kontrolle.json": OK, "kurz.json": "{"}])
        self.assertIsNone(f.kurz)

    def test_ohne_kurz_wird_nicht_gefragt(self):
        f = self.lauf([{"beschreibung.json": FOLIEN}, {"kontrolle.json": OK, "kurz.json": KURZ}], mit_kurz=False)
        self.assertIsNone(f.kurz)
        self.assertNotIn("kurz.json", self.claude.prompts[1][0])

    def test_erfundenes_baut_neu(self):
        f = self.lauf([{"beschreibung.json": FOLIEN},
                       {"kontrolle.json": {**OK, "erfunden": ["Messwert 12 %"]},
                        "beschreibung.json": {**FOLIEN, "untertitel": "neu"}},
                       {"kontrolle.json": OK}])
        self.assertEqual(f.kontrollen, 2)
        self.assertIn("Dazuerfunden: Messwert 12 %", self.claude.prompts[2][0])

    def test_falsche_renderer_art_geht_an_claude(self):
        f = self.lauf([{"beschreibung.json": BEISPIEL}, {"beschreibung.json": FOLIEN}, {"kontrolle.json": OK}])
        self.assertIn('"art": "folien"', self.claude.prompts[1][0])
        self.assertEqual(f.datei.suffix, ".pptx")

    def test_zu_wenig_material(self):
        with self.assertRaises(z.ZusammenfassungFehler) as f:
            self.lauf([{"antwort": "ZU_WENIG_MATERIAL: Nur ein Thema, keine Stichpunkte."}], dateien=[])
        self.assertEqual(str(f.exception), "Zu wenig Material für eine Präsentation: Nur ein Thema, keine Stichpunkte.")

    def test_bericht_gerade_durch(self):
        f = self.lauf([{"beschreibung.json": BERICHT}, {"kontrolle.json": OK, "kurz.json": KURZ}], art=arten.BERICHT)
        self.assertEqual(f.datei.name, "praktikum-im-saegewerk.docx")
        self.assertEqual(len(f.offen), 2)
        self.assertIn("Der Bericht ist gebaut (1 Seiten)", self.claude.prompts[1][0])

    def test_antwort_mit_datei(self):
        self.claude = FalscherClaude(self.ordner, [{"beschreibung.json": BERICHT}, {"kontrolle.json": OK}])
        z.erstellen({"id": "a2", "text": "Zeitraum war Mai bis Juli", "dateien": ["data/eingang/a2/kommentiert.docx"]},
                    self.ordner, self.agent_dir, self.claude, falsch_bauen, "F", None, "alt", art=arten.BERICHT)
        prompt, sitzung = self.claude.prompts[0]
        self.assertEqual(sitzung, "alt")
        self.assertIn("den fertigen Bericht", prompt)
        self.assertIn("data/eingang/a2/kommentiert.docx", prompt)


if __name__ == "__main__":
    unittest.main()
