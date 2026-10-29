import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import fassung
import runde
import stueck
from tests.test_stueck import TEXT

runde.logger.disabled = True  # Tests sollen nicht ins echte logs/ schreiben
HIER = Path(__file__).resolve().parents[1]
OPTION = {"titel": "T", "beschreibung": "B", "vorteile": "V", "nachteile": "N"}


def aufbauen(tmp: Path) -> runde.Pfade:
    """Agent-Ordner im Kleinen: theater.toml (echt, Textfassung umgebogen), Lias Texte, Nachricht."""
    texte = tmp / "data" / "text"
    texte.mkdir(parents=True)
    (texte / "eingang__stueck.pdf.txt").write_text(TEXT, encoding="utf-8")
    (texte / "eingang__Erste_Gedanken.docx.txt").write_text("Kontaktlinsen drin lassen!", encoding="utf-8")
    (texte / "eingang__Figuren.docx.txt").write_text("Lloyd | Regisseur", encoding="utf-8")
    seiten = "".join(f"--- Seite {p}\nBuchseite {p - 2} Übung\n" for p in range(1, 400))
    (texte / "eingang__Praxis_Schultheater.pdf.txt").write_text(seiten, encoding="utf-8")
    toml = (HIER / "theater.toml").read_text(encoding="utf-8")
    # nur die Textfassung des Stücks umbiegen (die des Buchs steht weiter unten und bleibt)
    toml = re.sub(r'textfassung = ".*"', 'textfassung = "data/text/eingang__stueck.pdf.txt"', toml, count=1)
    for name in re.findall(r'^  "([^"]+)",', toml, re.M):
        (texte / f"k11__{name}.txt").write_text(f"Inhalt {name}", encoding="utf-8")
    (tmp / "theater.toml").write_text(toml, encoding="utf-8")
    (tmp / "data" / "vorgaben").mkdir()
    (tmp / "data" / "vorgaben" / "nachricht.md").write_text("mir ist es zu lasch", encoding="utf-8")
    shutil.copy(HIER / "profil.toml", tmp / "profil.toml")
    return runde.Pfade(hier=tmp, vorgaben=tmp / "theater.toml", nachricht=tmp / "data" / "vorgaben" / "nachricht.md",
                       texte=texte, profil=tmp / "profil.toml")


def antworten(einheiten: list[stueck.Einheit], muss_ids: list[str]) -> dict:
    g = stueck.akt_grenzen(einheiten)
    anlaesse = []
    for akt in (1, 2, 3):
        von, bis = g[akt]
        for i, (v, b) in enumerate(((von, von), (von + 1, von + 1), (von + 2, bis)), 1):
            anlaesse.append({"id": f"A{akt}-{i:02d}", "akt": akt, "von": v, "bis": b, "titel": "T", "figuren": ["TIM"],
                             "worum": "W", "komik": "K", "muss": [], "lustige_stellen": []})
    karte = {"anlaesse": anlaesse,
             "nicht_gefunden": [{"muss": m, "grund": "eigene Idee"} for m in muss_ids if not m.startswith("M0")]}
    teile = {0: [], 1: [], 2: [], 3: []}
    for m in muss_ids:
        teile[int(m[1])].append(m)
    bausteine = [{"id": f"B{t}", "teil": t, "titel": "T", "minuten": [5, 10, 10, 12][t], "art": "neu",
                  "spielidee": "S", "neuer_text": "neu", "muss": teile[t]} for t in teile]
    bausteine[1].update(art="gemischt", stellen=[{"von": g[1][0] + 1, "bis": g[1][0] + 2}])
    ablauf = {"bausteine": bausteine,
              "varianten": [{"frage": f, "optionen": [OPTION, OPTION], "empfehlung": 1} for f in fassung.FRAGEN],
              "zuspitzung": [{"titel": "Z", "vorschlag": "V"}] * 3}
    aufgabe = {"art": "arbeitsblatt", "titel": "Szenenaufgabe: Unser Stück im Stück",
               "bloecke": [{"typ": "anweisung", "text": "Erfindet ein Mini-Stück!"}]}
    return {"szenenkarte.json": karte, "ablauf.json": ablauf, "stueck_im_stueck.json": aufgabe}


class Claude:
    """Schreibt die Antwortdatei, deren Pfad im Prompt steht. `kaputt`: diese Dateien beim ersten Mal fehlerhaft."""

    def __init__(self, hier: Path, kaputt=(), usd=0.5):
        self.hier, self.kaputt, self.usd, self.prompts = hier, set(kaputt), usd, []

    def __call__(self, prompt, sitzung=None):
        self.prompts.append((prompt, sitzung))
        pfad = Path(re.search(r"(data/runde-[^ \n]+?\.json)", prompt).group(1))
        ordner = self.hier / pfad.parent
        einheiten = stueck.aus_dicts(json.loads((ordner / "einheiten.json").read_text(encoding="utf-8")))
        import tomllib
        muss = [m["id"] for m in tomllib.loads((self.hier / "theater.toml").read_text(encoding="utf-8"))["muss"]]
        daten = antworten(einheiten, muss)[pfad.name]
        if pfad.name in self.kaputt:
            self.kaputt.discard(pfad.name)
            daten = {"kaputt": True}
        (self.hier / pfad).write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
        return SimpleNamespace(usd=self.usd, tokens=1, dauer_s=1, ok=True, sitzung="s1")


def renderer_attrappe(gebaut):
    def bauen(b, ziel, profil=None):
        from renderer import pruefen
        fehler = pruefen(b)
        if fehler:
            raise ValueError("; ".join(fehler))
        gebaut.append((ziel.name, profil["fach"]))
        ziel.write_bytes(b"docx")
        return SimpleNamespace(hinweise=[])
    return bauen


class Runde(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.pfade = aufbauen(self.tmp)

    def test_ganze_runde_mit_nachbesserung(self):
        claude, gebaut = Claude(self.tmp, kaputt={"ablauf.json"}), []
        z = runde.runde(self.pfade, laufen=claude, renderer_bauen=renderer_attrappe(gebaut))
        self.assertEqual(len(claude.prompts), 4)  # Karte, Ablauf, Nachbesserung, Aufgabe
        self.assertEqual([s for _, s in claude.prompts], [None, "s1", "s1", None])  # Aufgabe in neuer Sitzung
        self.assertIn("Fehler gefunden", claude.prompts[2][0])
        self.assertIn("B1 (Teil 1, 10 Min, gemischt): T. S", claude.prompts[3][0])  # Ablauf als Kurzfassung
        self.assertNotIn("stueck-teil-1.txt", claude.prompts[3][0])
        self.assertEqual([g[0] for g in gebaut], list(runde.DOKUMENTE))
        self.assertEqual({g[1] for g in gebaut}, {"Darstellendes Spiel"})
        self.assertAlmostEqual(z["usd"], 2.0)
        self.assertEqual(z["minuten"], 37)
        self.assertEqual(z["behalten"], 2)
        ordner = Path(z["ordner"]).parent
        self.assertTrue((ordner / "spielfassung.txt").exists())
        vorgaben = (ordner / "kontext" / "vorgaben.md").read_text(encoding="utf-8")
        self.assertIn("mir ist es zu lasch", vorgaben)
        self.assertIn("M1-6", vorgaben)
        grundlagen = (ordner / "kontext" / "grundlagen.md").read_text(encoding="utf-8")
        self.assertIn("## Szenenaufgabe_CvO.docx", grundlagen)
        self.assertIn("Noch nicht an Lia geschickt", runde.melden_text(z))

    def test_prompt_nennt_nur_dateien_im_agent_ordner(self):
        claude = Claude(self.tmp)
        runde.runde(self.pfade, laufen=claude, renderer_bauen=renderer_attrappe([]))
        erster = claude.prompts[0][0]
        self.assertIn("data/runde-", erster)
        self.assertNotIn(str(self.tmp), erster)
        self.assertIn("data/vorgaben/vom_text_zur_szene.jpg", erster)
        self.assertRegex(erster, r"data/runde-[^/]+/kontext/buch-teil-1\.md")
        self.assertIn("buch-teil-1.md", claude.prompts[2][0])  # auch die Szenenaufgabe bekommt das Buch
        ordner = next((self.tmp / "data").glob("runde-*"))
        buch1 = (ordner / "kontext" / "buch-teil-1.md").read_text(encoding="utf-8")
        self.assertIn("--- Buch S. 123\nBuchseite 123 Übung", buch1)

    def test_buch_fehlt(self):
        (self.pfade.texte / "eingang__Praxis_Schultheater.pdf.txt").unlink()
        with self.assertRaisesRegex(runde.RundenFehler, "Textfassung des Buchs fehlt"):
            runde.runde(self.pfade, laufen=Claude(self.tmp), renderer_bauen=renderer_attrappe([]))

    def test_zweimal_fehlerhaft_bricht_ab(self):
        claude = Claude(self.tmp, kaputt={"szenenkarte.json"})
        alt = claude.__call__

        def immer_kaputt(prompt, sitzung=None):
            claude.kaputt.add("szenenkarte.json")
            return alt(prompt, sitzung)
        with self.assertRaisesRegex(runde.RundenFehler, "Szenenkarte nach Nachbesserung noch fehlerhaft"):
            runde.runde(self.pfade, laufen=immer_kaputt, renderer_bauen=renderer_attrappe([]))

    def test_fortsetzen_uebernimmt_gepruefte_antworten(self):
        erste = Claude(self.tmp, usd=3.0)
        with self.assertRaisesRegex(runde.RundenFehler, "Kostengrenze"):
            runde.runde(self.pfade, laufen=erste, renderer_bauen=renderer_attrappe([]))
        ordner = next((self.tmp / "data").glob("runde-*")).name
        (self.tmp / "data" / ordner / "ablauf.json").write_text("{}", encoding="utf-8")  # fehlerhaft: läuft neu
        zweite, gebaut = Claude(self.tmp), []
        z = runde.runde(self.pfade, laufen=zweite, renderer_bauen=renderer_attrappe(gebaut), fortsetzen=ordner)
        laeufe = [re.search(r"data/runde-[^ \n]+?/(\w+)\.json", p).group(1) for p, _ in zweite.prompts]
        self.assertEqual(laeufe, ["ablauf", "stueck_im_stueck"])  # Szenenkarte übernommen
        self.assertEqual(z["usd"], 1.0)
        self.assertEqual(len(gebaut), 4)

    def test_fortsetzen_unbekannter_ordner(self):
        with self.assertRaisesRegex(runde.RundenFehler, "keine angefangene Runde"):
            runde.runde(self.pfade, laufen=Claude(self.tmp), fortsetzen="runde-gibt-es-nicht")

    def test_main_mit_ordner_setzt_fort(self):
        aufrufe, alt = [], runde.runde
        runde.runde = lambda **kw: aufrufe.append(kw) or (_ for _ in ()).throw(RuntimeError("halt"))
        try:
            runde.main(["runde-x"], melden=lambda t: None)
        finally:
            runde.runde = alt
        self.assertEqual(aufrufe, [{"fortsetzen": "runde-x"}])

    def test_kostengrenze(self):
        with self.assertRaisesRegex(runde.RundenFehler, "Kostengrenze 5.00 USD"):
            runde.runde(self.pfade, laufen=Claude(self.tmp, usd=3.0), renderer_bauen=renderer_attrappe([]))

    def test_kontextdatei_fehlt(self):
        next(self.pfade.texte.glob("*Szenenaufgabe_CvO*")).unlink()
        with self.assertRaisesRegex(runde.RundenFehler, "0 Textfassungen mit „Szenenaufgabe_CvO.docx“"):
            runde.runde(self.pfade, laufen=Claude(self.tmp), renderer_bauen=renderer_attrappe([]))

    def test_main_meldet_abbruch(self):
        gemeldet = []
        alt = runde.runde
        runde.runde = lambda: (_ for _ in ()).throw(RuntimeError("kaputt"))
        try:
            self.assertEqual(runde.main([], melden=gemeldet.append), 1)
        finally:
            runde.runde = alt
        self.assertEqual(gemeldet, ["Runde abgebrochen: kaputt"])

    def test_lesbarer_name(self):
        self.assertEqual(runde.lesbarer_name("Spielmo╠êglichkeiten_Status.docx"), "Spielmöglichkeiten_Status.docx")
        self.assertEqual(runde.lesbarer_name("AB_1.docx"), "AB_1.docx")


if __name__ == "__main__":
    unittest.main()
