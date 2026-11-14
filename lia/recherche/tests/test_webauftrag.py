import json
import re
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import agent
import webauftrag
from agentkit import claude_lauf
from tests.test_webpruefung import DOMAINS, REGISTER, beleg, seitentext

CFG = {"webfetch": {"recherche": DOMAINS}}
GUT = {"abschnitte": [{"titel": "B) Fälle", "aussagen": [
    {"text": "Ein Mann stahl drei Fahrräder.", "belege": [beleg("https://taz.de/fall", "stahl drei Fahrräder")]},
    {"text": "Liszt: Gelegenheitsverbrecher.", "belege": [{"register": "liszt:41"}]}]}],
    "luecken": ["Kein Video gefunden."], "rueckfragen": []}
FALSCH = {"abschnitte": [{"titel": "B) Fälle", "aussagen": [
    {"text": "Ein Mann stahl drei Fahrräder.", "belege": [beleg("https://taz.de/fall", "stahl drei Räder")]}]}]}


class Claude:
    """Ersetzt claude_lauf. Recherche/Nachbesserung: nächste Antwort aus antworten. Prüflauf: Urteile aus
    traegt (id -> (wert, fehlt)), sonst "ja"; traegt_kaputt schreibt beim ersten Prüflauf Unsinn."""

    def __init__(self, hier, antworten, usd=0.5, ok=True, traegt=None, traegt_kaputt=False):
        self.hier, self.antworten, self.usd, self.ok, self.prompts = hier, list(antworten), usd, ok, []
        self.traegt, self.traegt_kaputt = traegt or {}, traegt_kaputt

    def __call__(self, prompt, sitzung=None, art="anspruchsvoll"):
        self.prompts.append((prompt, sitzung, art))
        pfad = re.search(r"NUR in die Datei (\S+?),|neu nach (\S+?),|VOLLSTÄNDIGE Datei (\S+) neu", prompt)
        pfad = next(g for g in pfad.groups() if g)
        if "Prüfe für jede Aussage" in prompt or "jede id genau einmal" in prompt:
            if self.traegt_kaputt:
                self.traegt_kaputt = False
                teil = prompt.split("AUSSAGEN (JSON):")[-1].split("Schreibe NUR")[0]
                self.ids = list(dict.fromkeys(re.findall(r'"id": "(a\d+-\d+)"', teil)))
                (self.hier / pfad).write_text('{"urteile": [{"id": "zz", "traegt": "vielleicht"}]}')
            else:
                teil = prompt.split("AUSSAGEN (JSON):")[-1].split("Schreibe NUR")[0]
                ids = list(dict.fromkeys(re.findall(r'"id": "(a\d+-\d+)"', teil))) or self.ids
                self.ids = ids
                urteile = [{"id": i, "traegt": self.traegt.get(i, ("ja", ""))[0], "fehlt": self.traegt.get(i, ("ja", ""))[1]}
                           for i in ids]
                (self.hier / pfad).write_text(json.dumps({"urteile": urteile}), encoding="utf-8")
        else:
            antwort = self.antworten.pop(0)
            if antwort is not None:
                (self.hier / pfad).write_text(json.dumps(antwort), encoding="utf-8")
        return claude_lauf.Ergebnis(text="fertig", sitzung="s1", ok=self.ok, usd=self.usd)


class Basis(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.hier)
        (self.hier / "data").mkdir()
        (self.hier / "data/register.json").write_text(json.dumps(
            {"quellen": [dict(REGISTER["liszt"], id="liszt")]}), encoding="utf-8")
        self.auftrag = self.hier / "auftrag.txt"
        self.auftrag.write_text("AUFGABE\nFinde reale Fälle.", encoding="utf-8")
        self.meldungen, self.gebaut = [], []

    def ausfuehren(self, antworten, anhang=(), **mehr):
        self.claude = Claude(self.hier, antworten, **mehr)
        return webauftrag.ausfuehren(self.auftrag, hier=self.hier, laufen=self.claude, seitentext=seitentext,
                                     renderer_bauen=lambda b, ziel: self.gebaut.append((b, ziel)),
                                     melden=self.meldungen.append, cfg=CFG, anhang=list(anhang),
                                     als_text=lambda p: "TEXT", anhang_wurzel=self.hier)


class WebauftragTest(Basis):

    def test_alles_bestanden_ohne_nachbesserung(self):
        ordner = self.ausfuehren([GUT])
        self.assertEqual(len(self.claude.prompts), 2)  # Recherche und Prüflauf
        self.assertEqual(self.claude.prompts[1][1:], (None, "routine"))  # neue Sitzung, günstig
        prompt = self.claude.prompts[0][0]
        self.assertIn("Finde reale Fälle.", prompt)
        self.assertIn("liszt:41", prompt)
        self.assertIn("taz.de, youtube.com", prompt)
        self.assertEqual((self.hier / "data/web").resolve(), ordner.parent.resolve())
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["zahlen"]["belegt"], 2)
        self.assertEqual(self.gebaut[0][1], ordner / "Recherche.docx")
        self.assertIn("2 von 2 Aussagen belegt", self.meldungen[-1])
        self.assertIn("Kosten 1.00 USD in 2 Läufen", self.meldungen[-1])
        self.assertIn("2 ja, 0 teilweise, 0 nein", self.meldungen[-1])

    def test_nachbesserung_in_derselben_sitzung(self):
        ordner = self.ausfuehren([FALSCH, GUT])
        self.assertEqual(len(self.claude.prompts), 3)
        self.assertEqual(self.claude.prompts[1][1], "s1")
        self.assertIn("stahl drei Räder", self.claude.prompts[1][0])
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["erste_pruefung"]["durchgefallen"], 1)
        self.assertEqual(d["zahlen"]["durchgefallen"], 0)
        self.assertTrue((ordner / "ergebnis_1.json").exists())
        self.assertIn("erste Prüfung: 0/1/0", self.meldungen[-1])

    def test_nach_nachbesserung_noch_falsch_bleibt_unbelegt(self):
        ordner = self.ausfuehren([FALSCH, FALSCH])
        self.assertEqual(len(self.claude.prompts), 2)  # nur eine Nachbesserung, kein Prüflauf (nichts belegt)
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual((d["zahlen"]["belegt"], d["zahlen"]["unbelegt"]), (0, 1))
        self.assertIn("Nicht belegt", json.dumps(self.gebaut[0][0], ensure_ascii=False))

    def test_keine_datei_bricht_ab_und_meldet(self):
        with self.assertRaises(webauftrag.webpruefung.WebFehler):
            self.ausfuehren([None])
        self.assertIn("abgebrochen", self.meldungen[-1])

    def test_kostengrenze(self):
        kosten = agent.Kosten(grenze=0.4)
        self.claude = Claude(self.hier, [FALSCH, GUT])
        with self.assertRaises(agent.KostenGrenze):
            webauftrag.ausfuehren(self.auftrag, hier=self.hier, laufen=self.claude, seitentext=seitentext,
                                  renderer_bauen=lambda b, z: None, melden=self.meldungen.append, cfg=CFG,
                                  kosten=kosten)
        self.assertEqual(len(self.claude.prompts), 1)
        self.assertIn("Kostengrenze", self.meldungen[-1])

    def test_lauf_nicht_ok_aber_datei_da(self):
        self.ausfuehren([GUT], ok=False)  # z. B. max_turns erreicht, Datei schon geschrieben
        self.assertIn("2 von 2 Aussagen belegt", self.meldungen[-1])

    def test_traegt_nein_und_teilweise(self):
        ordner = self.ausfuehren([GUT], traegt={"a0-0": ("nein", "Fahrräder: es waren Roller")})
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["traegt_zahlen"], {"ja": 1, "teilweise": 0, "nein": 1, "nicht_geprueft": 0})
        self.assertEqual(d["zahlen"]["belegt"], 1)  # nein -> unbelegt; Liszt-Aussage ist Register, "ja"
        b = json.dumps(self.gebaut[-1][0], ensure_ascii=False)
        self.assertIn("Zitat trägt die Aussage nicht: Fahrräder: es waren Roller", b)
        self.ausfuehren([GUT], traegt={"a0-0": ("teilweise", "Anzahl drei")})
        b = json.dumps(self.gebaut[-1][0], ensure_ascii=False)
        self.assertIn("Ein Mann stahl drei Fahrräder. [1] *", b)
        self.assertIn("„Ein Mann stahl drei Fahrräder.“: Anzahl drei", b)
        self.assertIn("Zu prüfen", b)
        self.assertNotIn("Detail nicht belegt", b)

    def test_traegt_kaputt_eine_nachbesserung(self):
        ordner = self.ausfuehren([GUT], traegt_kaputt=True)
        self.assertEqual([p[2] for p in self.claude.prompts], ["anspruchsvoll", "routine", "routine"])
        self.assertEqual(json.loads((ordner / "geprueft.json").read_text())["traegt_zahlen"]["ja"], 2)

    def test_anhaenge(self):
        erlaubt = self.hier / "vorbild.md"
        erlaubt.write_text("Vorbild", encoding="utf-8")
        (self.hier / "x.docx").write_bytes(b"docx")
        self.auftrag.write_text(f"AUFGABE\nANHANG: {erlaubt}\nANHANG: /etc/passwd\n", encoding="utf-8")
        ordner = self.ausfuehren([GUT], anhang=[str(self.hier / "x.docx"), str(self.hier / ".env")])
        self.assertEqual(sorted(p.name for p in (ordner / "anhaenge").iterdir()), ["vorbild.md", "x.docx", "x.docx.txt"])
        prompt = self.claude.prompts[0][0]
        self.assertIn(f"data/web/{ordner.name}/anhaenge/vorbild.md", prompt)
        self.assertIn("anhaenge/x.docx.txt", prompt)
        self.assertIn("Abgelehnte Anhänge: /etc/passwd: nicht unter", self.meldungen[-1])
        self.assertIn(".env", self.meldungen[-1])

    def test_nur_traegt_auf_fertigen_auftrag(self):
        ordner = self.ausfuehren([GUT])
        d = json.loads((ordner / "geprueft.json").read_text())
        for k in ("traegt_zahlen",):
            d.pop(k)
        (ordner / "geprueft.json").write_text(json.dumps(d))
        claude = Claude(self.hier, [], traegt={"a0-0": ("teilweise", "Ort")})
        webauftrag.nur_traegt(ordner, hier=self.hier, laufen=claude, melden=self.meldungen.append,
                              renderer_bauen=lambda b, z: self.gebaut.append((b, z)))
        self.assertEqual(len(claude.prompts), 1)
        self.assertTrue((ordner / "geprueft_vor_traegt.json").exists())
        self.assertIn("1 ja, 1 teilweise", self.meldungen[-1])
        with self.assertRaises(webauftrag.webpruefung.WebFehler):
            webauftrag.nur_traegt(ordner, hier=self.hier, laufen=claude, melden=self.meldungen.append,
                                  renderer_bauen=lambda b, z: None)

    def test_zwei_auftraege_in_derselben_sekunde(self):
        a, b = self.ausfuehren([GUT]), self.ausfuehren([GUT])
        self.assertNotEqual(a, b)

    def test_id(self):
        self.assertEqual(webauftrag.auftrag_id(Path("Lias Auftrag 1.txt"), datetime(2026, 10, 25, 9, 5, 1)),
                         "20261025-090501-lias-auftrag-1")


KERN = dict(GUT, kern="Fünf Gruppen von Auslösern helfen dir. Entscheide, ob drei reichen.",
            punkte=["Wissen, Wort, Ding, Person, Panne", "Übungen mit Karten", "Seitenzahlen fehlen", "zu viel"])
THEATER = dict(KERN, abschnitte=[{"titel": "A) Status", "aussagen": [GUT["abschnitte"][0]["aussagen"][0]]}])
MEHR = {"kern": "Jetzt gründlicher.", "punkte": ["Mehr Quellen"], "abschnitte": GUT["abschnitte"] + [
    {"titel": "C) Mehr", "aussagen": [{"text": "Noch ein Fall.", "belege": [beleg("https://taz.de/fall", "Der Mann")]}]}],
    "luecken": [], "rueckfragen": []}


class KopfTest(unittest.TestCase):
    def test_standard(self):
        self.assertEqual(webauftrag.kopf_lesen("AUFGABE\nFACH: Theater"),
                         {"fach": "Ethik", "titel": "", "aufwand": "normal"})

    def test_kopfzeilen_oben(self):
        k = webauftrag.kopf_lesen("\nFACH: Darstellendes Spiel\nTITEL: Auslöser: Statuswechsel\nAUFWAND: groß\n\nAUFGABE")
        self.assertEqual(k, {"fach": "Darstellendes Spiel", "titel": "Auslöser: Statuswechsel", "aufwand": "gross"})
        self.assertFalse(webauftrag.mit_register(k))
        self.assertTrue(webauftrag.mit_register({"fach": " ethik "}))
        self.assertEqual(webauftrag.dateiname(k), "Auslöser Statuswechsel.docx")
        self.assertEqual(webauftrag.dateiname({"titel": " / "}), "Recherche.docx")
        self.assertEqual(webauftrag.dokument_titel({"titel": ""}, datetime(2026, 11, 14)), "Recherche vom 14.11.2026")

    def test_unbekannter_aufwand(self):
        with self.assertRaises(webauftrag.webpruefung.WebFehler):
            webauftrag.kopf_lesen("AUFWAND: riesig")


class SeitenTextTest(unittest.TestCase):
    def test_pdf_und_html(self):
        self.assertEqual(webauftrag.seiten_text(b"%PDF-1.4 ...", None, lambda b: "--- Seite 1\nStatus"),
                         "--- Seite 1\nStatus")
        self.assertEqual(webauftrag.seiten_text(b"x", "application/pdf", lambda b: "T"), "T")
        with self.assertRaises(webauftrag.abruf.AbrufFehler):
            webauftrag.seiten_text(b"%PDF-1.4", None, lambda b: "")
        self.assertIn("Hallo", webauftrag.seiten_text(b"<p>Hallo</p>", "text/html; charset=utf-8", None))


class GrosserAuftragTest(Basis):
    """Kopfzeilen, Vertiefungsrunden, Kern und --an-lia (Jan 14.11.2026)."""

    def test_normal_ohne_vertiefung_mit_register(self):
        self.ausfuehren([KERN])
        prompt = self.claude.prompts[0][0]
        self.assertIn("höchstens etwa 20 Werkzeugaufrufe", prompt)
        self.assertIn("liszt:41", prompt)
        self.assertIn('"kern"', prompt)

    def test_anderes_fach_ohne_register(self):
        self.auftrag.write_text("FACH: Darstellendes Spiel\nTITEL: Statuswechsel\nAUFGABE\nX", encoding="utf-8")
        ordner = self.ausfuehren([THEATER])
        prompt = self.claude.prompts[0][0]
        self.assertNotIn("liszt:41", prompt)
        self.assertNotIn("register", prompt)
        self.assertEqual(self.gebaut[0][1], ordner / "Statuswechsel.docx")
        self.assertEqual(self.gebaut[0][0]["titel"], "Statuswechsel")
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual((d["kopf"]["fach"], d["datei"]), ("Darstellendes Spiel", "Statuswechsel.docx"))
        self.assertEqual(d["punkte"], KERN["punkte"][:3])
        b = self.gebaut[0][0]["bloecke"]
        self.assertEqual((b[0]["typ"], b[0]["titel"]), ("merksatz", "Auf einen Blick"))
        self.assertIn("Fünf Gruppen", b[0]["text"])

    def test_gross_mit_vertiefungsrunden(self):
        self.auftrag.write_text("AUFWAND: gross\nAUFGABE\nX", encoding="utf-8")
        ordner = self.ausfuehren([FALSCH, KERN, MEHR, MEHR])
        arten = [p[0].split("\n")[0][:25] for p in self.claude.prompts]
        self.assertIn("großer, wichtiger Auftrag", self.claude.prompts[0][0])
        self.assertTrue(all(p[0].startswith("Vertiefungsrunde") for p in self.claude.prompts[1:4]), arten)
        self.assertEqual([p[1] for p in self.claude.prompts[1:4]], ["s1", "s1", "s1"])  # dieselbe Sitzung
        self.assertIn("stahl drei Räder", self.claude.prompts[1][0])  # durchgefallener Beleg wird genannt
        self.assertEqual(len(self.claude.prompts), 5)  # Recherche, 3 Vertiefungen, Prüflauf
        self.assertTrue((ordner / "ergebnis_runde0.json").exists())
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["zahlen"]["aussagen"], 3)
        self.assertEqual(d["kern"], "Jetzt gründlicher.")

    def test_gross_vertiefung_endet_an_der_reserve(self):
        self.auftrag.write_text("AUFWAND: gross\nAUFGABE\nX", encoding="utf-8")
        self.ausfuehren([KERN, MEHR, MEHR, MEHR], usd=9.0)  # 9 + 9 = 18 >= 0,7 * 25
        self.assertEqual(len(self.claude.prompts), 3)  # Recherche, 1 Vertiefung, Prüflauf

    def test_gross_kaputte_vertiefung_nimmt_stand_davor(self):
        self.auftrag.write_text("AUFWAND: gross\nAUFGABE\nX", encoding="utf-8")
        claude = Claude(self.hier, [KERN])
        alt = claude.__call__

        def kaputt(prompt, sitzung=None, art="anspruchsvoll"):
            if prompt.startswith("Vertiefungsrunde"):
                pfad = re.search(r"VOLLSTÄNDIGE Datei (\S+) neu", prompt).group(1)
                (self.hier / pfad).write_text("{kaputt")
                claude.prompts.append((prompt, sitzung, art))
                return claude_lauf.Ergebnis(text="x", sitzung="s1", ok=True, usd=0.5)
            return alt(prompt, sitzung, art)
        ordner = webauftrag.ausfuehren(self.auftrag, hier=self.hier, laufen=kaputt, seitentext=seitentext,
                                       renderer_bauen=lambda b, z: None, melden=self.meldungen.append, cfg=CFG)
        d = json.loads((ordner / "geprueft.json").read_text())
        self.assertEqual(d["zahlen"]["belegt"], 2)
        self.assertEqual(sum(p[0].startswith("Vertiefungsrunde") for p in claude.prompts), 1)

    def test_an_lia(self):
        self.auftrag.write_text("FACH: Darstellendes Spiel\nTITEL: Statuswechsel\nAUFGABE\nX", encoding="utf-8")
        ordner = self.ausfuehren([THEATER])
        (ordner / "Statuswechsel.docx").write_text("docx")
        lia = self.hier.parent / f"{self.hier.name}-lia"
        self.addCleanup(shutil.rmtree, lia, True)
        basis, agenten = lia / "instanz/auftraege", lia
        (agenten / "recherche").mkdir(parents=True)
        ziel = agenten / "recherche" / "data" / "web" / ordner.name
        shutil.copytree(ordner, ziel)

        def pdf(docx):
            (docx.with_suffix(".pdf")).write_text("pdf")
            return docx.with_suffix(".pdf")
        aid = webauftrag.an_lia(ziel, pdf_bauen=pdf, basis=basis, agenten_dir=agenten)
        a = webauftrag.auftraege.erledigter(aid, basis=basis)
        self.assertEqual((a["agent"], a["status"]), ("recherche", "erledigt"))
        self.assertEqual(a["ergebnis_dateien"], [f"data/web/{ordner.name}/Statuswechsel.pdf"])
        self.assertIn("Fünf Gruppen", a["daten"]["kern"])
        self.assertEqual(a["daten"]["knoepfe"], "nur_antwort")
        self.assertEqual(len(a["daten"]["punkte"]), 3)
        with self.assertRaises(webauftrag.webpruefung.WebFehler):
            webauftrag.an_lia(ziel, pdf_bauen=pdf, basis=basis, agenten_dir=agenten)  # nur einmal

    def test_an_lia_nur_in_lias_instanz(self):
        self.assertEqual(webauftrag.main(["webauftrag.py", "--an-lia", str(self.hier)]), 2)

    def test_an_lia_ohne_kern_oder_zu_lang(self):
        with self.assertRaises(webauftrag.webpruefung.WebFehler):
            webauftrag.nachricht_an_lia({"kern": "", "punkte": []})
        lang = " ".join(["Wort"] * 25) + "."
        with self.assertRaises(webauftrag.webpruefung.WebFehler):
            webauftrag.nachricht_an_lia({"kern": lang, "punkte": []})


class AdresseTest(unittest.TestCase):
    def test_umlaute_werden_kodiert(self):
        self.assertEqual(webauftrag.adresse("https://de.wikipedia.org/wiki/Antonio_Rüdiger"),
                         "https://de.wikipedia.org/wiki/Antonio_R%C3%BCdiger")
        self.assertEqual(webauftrag.adresse("https://taz.de/a?b=Fußball&c=1#x"), "https://taz.de/a?b=Fu%C3%9Fball&c=1")

    def test_schon_kodiert_bleibt(self):
        url = "https://de.wikipedia.org/wiki/Rassismus_im_Fu%C3%9Fball"
        self.assertEqual(webauftrag.adresse(url), url)


if __name__ == "__main__":
    unittest.main()
