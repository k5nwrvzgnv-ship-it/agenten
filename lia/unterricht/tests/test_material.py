import functools
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

import material
import renderer
from agentkit.claude_lauf import Ergebnis

PROFIL = tomllib.loads((Path(__file__).resolve().parent.parent / "profil.toml").read_text(encoding="utf-8"))
BAUEN = functools.partial(renderer.bauen, vorschau=False)  # Vorschau prüft der Renderer selbst (dauert 5 s)

BLATT = {"art": "arbeitsblatt", "titel": "Der kategorische Imperativ", "nummer": "1", "bloecke": [
    {"typ": "merksatz", "text": "Handle nur nach derjenigen Maxime, durch die du zugleich wollen kannst, "
                                "dass sie ein allgemeines Gesetz werde."},
    {"typ": "aufgaben", "aufgaben": [{"text": "Erkläre den Merksatz.", "antwort": {"art": "linien", "anzahl": 3}}]},
]}
FOLIEN = {"art": "folien", "titel": "Kant für Einsteiger", "untertitel": "Ethik · Klasse 10", "folien": [
    {"titel": "Ziel für heute", "inhalt": [{"typ": "zentriert", "absaetze": ["Wir lernen Kants Pflichtethik."]}]},
]}

MAPPE = {"art": "arbeitsmappe", "titel": "Notenübersicht", "blaetter": [{
    "name": "Noten", "titel": "Notenübersicht", "zeilen": 30, "hinweise": ["Endnote = 2/3 Schnitt + 1/3 LEK."],
    "spalten": [{"id": "nr", "kopf": "Nr.", "art": "nummer"}, {"id": "name", "kopf": "Name", "art": "text"},
                {"id": "n1", "kopf": "Note 1", "art": "zahl", "ganz": True, "min": 0, "max": 15},
                {"id": "n2", "kopf": "Note 2", "art": "zahl", "ganz": True, "min": 0, "max": 15},
                {"id": "schnitt", "kopf": "Durchschnitt", "art": "rechnung", "formel": "mittelwert(n1:n2)"},
                {"id": "lek", "kopf": "LEK", "art": "zahl", "ganz": True, "min": 0, "max": 15},
                {"id": "end", "kopf": "Endnote", "art": "rechnung", "formel": "wenn_leer(2/3 * schnitt + 1/3 * lek, schnitt)"}],
}]}


class FalscherClaude:
    """Spielt Claude: jeder Schritt schreibt (oder nicht) die Beschreibung und antwortet mit einem Text."""

    def __init__(self, ordner: Path, schritte: list):
        self.pfad = ordner / "beschreibung.json"
        self.schritte = list(schritte)
        self.prompts, self.sitzungen = [], []

    def __call__(self, prompt, sitzung=None):
        self.prompts.append(prompt)
        self.sitzungen.append(sitzung)
        inhalt, text = self.schritte.pop(0)
        if isinstance(inhalt, dict) and all(k.startswith("beschreibung") and k.endswith(".json") for k in inhalt):
            for name, b in inhalt.items():  # mehrere Dateien in einem Schritt
                (self.pfad.parent / name).write_text(json.dumps(b), encoding="utf-8")
        elif inhalt is not None:
            self.pfad.write_text(inhalt if isinstance(inhalt, str) else json.dumps(inhalt), encoding="utf-8")
        return Ergebnis(text=text, sitzung="s1", ok=True, usd=0.5, tokens=1000)


class MaterialTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.auftrag = {"id": "20261022-120000-unterricht-abcdef", "text": "Arbeitsblatt kategorischer Imperativ, Kl. 10"}
        self.ordner = self.hier / "data" / "arbeit" / self.auftrag["id"]

    def bearbeiten(self, schritte):
        claude = FalscherClaude(self.ordner, schritte)
        return material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN), claude

    def test_format_nur_passende_abschnitte(self):
        text = material.format_abschnitte(material.FORMAT_DATEI.read_text(encoding="utf-8"))
        self.assertIn("## Arbeitsblatt", text)
        self.assertIn("## Folien", text)
        self.assertIn("## Allgemein", text)
        self.assertNotIn("## Zusammenfassung", text)
        with self.assertRaises(ValueError):
            material.format_abschnitte("# Format\n## Allgemein\nx")

    def test_dateiname(self):
        self.assertEqual(material.dateiname({"art": "arbeitsblatt", "titel": "Muss ich helfen? Ja/Nein!"}),
                         "Arbeitsblatt Muss ich helfen JaNein.docx")
        self.assertEqual(material.dateiname(FOLIEN), "Folien Kant für Einsteiger.pptx")
        self.assertTrue(material.dateiname({"art": "folien", "titel": "x" * 300}).endswith("x.pptx"))
        lang = "Kann ich wollen, dass alle so handeln wie ich? – Kants kategorischer Imperativ"
        self.assertEqual(material.dateiname({"art": "arbeitsblatt", "titel": lang}),
                         "Arbeitsblatt Kann ich wollen dass alle so handeln wie ich Kants.docx")

    def test_gelingt_beim_ersten_mal(self):
        f, claude = self.bearbeiten([(BLATT, "Entwurf"), (None, "Ein Blatt mit Merksatz und einer Aufgabe.")])
        self.assertEqual(f.datei, self.ordner / "Arbeitsblatt Der kategorische Imperativ.docx")
        self.assertTrue(f.datei.is_file())
        self.assertEqual(f.begleittext, "Ein Blatt mit Merksatz und einer Aufgabe.")
        self.assertEqual((f.laeufe, f.usd, f.tokens, f.sitzung), (2, 1.0, 2000, "s1"))
        self.assertIn("kategorischer Imperativ, Kl. 10", claude.prompts[0])
        self.assertIn("Ethik", claude.prompts[0])
        self.assertIn("data/arbeit/20261022-120000-unterricht-abcdef/beschreibung.json", claude.prompts[0])
        self.assertIn("Skill einzelmaterial", claude.prompts[0])
        self.assertIn("Kontrolltext", claude.prompts[1])
        self.assertNotIn("laufende Reihen", claude.prompts[0])
        self.assertNotIn("früheren Reihen", claude.prompts[0])
        self.assertNotIn("So unterrichtet Lia", claude.prompts[0])
        self.assertIn("Handle nur nach derjenigen Maxime", claude.prompts[1])
        self.assertEqual(claude.sitzungen, [None, "s1"])

    def test_reihen_im_startprompt(self):
        claude = FalscherClaude(self.ordner, [(BLATT, "Entwurf"), (None, "Fertig.")])
        reihe = {"klasse": 10, "reihenfrage": "Was soll ich tun?", "behandelt": ["Kant"]}
        material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN, reihen=[reihe])
        start = claude.prompts[0]
        self.assertIn("## Lias laufende Reihen", start)
        self.assertIn("### Ethik, Klasse 10\n- Reihenfrage: Was soll ich tun?\n- Schon behandelt: Kant", start)
        self.assertLess(start.index("kategorischer Imperativ, Kl. 10"), start.index("## Lias laufende Reihen"))
        self.assertLess(start.index("## Lias laufende Reihen"), start.index("Skill einzelmaterial"))
        self.assertNotIn("laufende Reihen", claude.prompts[1])

    def test_gewaehlte_reihe_zuerst(self):
        claude = FalscherClaude(self.ordner, [(BLATT, "Entwurf"), (None, "Fertig.")])
        andere = {"id": "a", "fach": "Ethik", "klasse": 8, "titel": "Strafe"}
        gewaehlt = {"id": "b", "fach": "Ethik", "klasse": 10, "titel": "Pflicht",
                    "stunden": [{"nr": 1, "thema": "Kant", "marke": "UB"}]}
        material.bearbeiten({**self.auftrag, "reihe": "b"}, self.hier, PROFIL, laufen=claude, bauen=BAUEN,
                            reihen=[andere, gewaehlt])
        start = claude.prompts[0]
        self.assertLess(start.index("Klasse 10: Pflicht (Lia hat den Auftrag"), start.index("Klasse 8: Strafe"))
        self.assertIn("- Stunden der Reihe:\n  - Stunde 1: Kant (UB)", start)

    def test_katalog_im_startprompt(self):
        claude = FalscherClaude(self.ordner, [(BLATT, "Entwurf"), (None, "Fertig.")])
        material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN,
                            reihen=[{"klasse": 10, "reihenfrage": "Was soll ich tun?"}],
                            katalog="### Ethik 7: Lügen\n- data/wissen/text/AB_6_Kant.docx.txt | Arbeitsblatt | Kant\n")
        start = claude.prompts[0]
        self.assertIn("## Lias Material aus früheren Reihen", start)
        self.assertIn("- data/wissen/text/AB_6_Kant.docx.txt | Arbeitsblatt | Kant", start)
        self.assertLess(start.index("## Lias laufende Reihen"), start.index("## Lias Material aus früheren Reihen"))
        self.assertLess(start.index("## Lias Material aus früheren Reihen"), start.index("Skill einzelmaterial"))

    def test_leitfaden_im_startprompt(self):
        claude = FalscherClaude(self.ordner, [(BLATT, "Entwurf"), (None, "Fertig.")])
        material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN,
                            katalog="### Ethik 7\n- a.txt | Arbeitsblatt | x\n",
                            leitfaden="# So unterrichtet Lia\n\n## 3. Arbeitsblätter\n- Kein Lückentext (Feedback_1.UB)\n")
        start = claude.prompts[0]
        self.assertIn("## So unterrichtet Lia (Leitfaden, von Jan freigegeben)", start)
        self.assertIn("### 3. Arbeitsblätter\n- Kein Lückentext", start)
        self.assertLess(start.index("## Lias Material aus früheren Reihen"), start.index("## So unterrichtet Lia"))
        self.assertLess(start.index("## So unterrichtet Lia"), start.index("Skill einzelmaterial"))
        self.assertNotIn("So unterrichtet Lia", claude.prompts[1])

    def test_arbeitsmappe(self):
        f, claude = self.bearbeiten([(MAPPE, "Entwurf"), (None, "Deine Notentabelle.")])
        self.assertEqual(f.datei, self.ordner / "Arbeitsmappe Notenübersicht.xlsx")
        self.assertTrue(f.datei.is_file())
        self.assertIn("## Arbeitsmappe", claude.prompts[0])
        self.assertIn("arbeitsmappe", material.SKILL_DATEI.read_text(encoding="utf-8"))
        self.assertIn("\nProbe ", claude.prompts[1])
        self.assertIn("Prüfe die Probe-Zeilen", claude.prompts[1])
        self.assertNotIn("Prüfe die Probe-Zeilen", material.prompt_kontrolle("x", "Merksatz", [], []))

    def test_fehler_gehen_an_claude_zurueck(self):
        falsch = dict(BLATT, farbe="rot")
        f, claude = self.bearbeiten([(falsch, "a"), (BLATT, "b"), (None, "fertig")])
        self.assertIn("farbe", claude.prompts[1])
        self.assertIn("Korrigiere", claude.prompts[1])
        self.assertEqual(f.laeufe, 3)
        self.assertEqual(f.begleittext, "fertig")

    def test_fehlende_datei_kaputtes_json_falsche_art(self):
        f, claude = self.bearbeiten([(None, "a"), ("{kaputt", "b"), ({"art": "zusammenfassung"}, "c"),
                                     (FOLIEN, "d"), (None, "Folien fertig")])
        self.assertIn("fehlt", claude.prompts[1])
        self.assertIn("kein gültiges JSON", claude.prompts[2])
        self.assertIn("art", claude.prompts[3])
        self.assertEqual(f.datei.suffix, ".pptx")

    def test_gibt_nach_max_korrekturen_auf(self):
        with self.assertRaises(material.MaterialFehler):
            self.bearbeiten([("{", "x")] * (material.MAX_KORREKTUREN + 1))

    def test_kontrolle_ueberarbeitet(self):
        besser = dict(BLATT, titel="Kants kategorischer Imperativ")
        f, claude = self.bearbeiten([(BLATT, "a"), (besser, "Überarbeitet.")])
        self.assertEqual(f.datei.name, "Arbeitsblatt Kants kategorischer Imperativ.docx")
        self.assertEqual(f.begleittext, "Überarbeitet.")
        self.assertEqual(f.laeufe, 2)

    def nachbesserung(self, schritte, sitzung="alt", ok=True):
        """Altes Ergebnis anlegen, dann eine Nachbesserung dazu bearbeiten."""
        alt = self.hier / "data" / "arbeit" / "alt-auftrag"
        alt.mkdir(parents=True, exist_ok=True)
        (alt / "beschreibung.json").write_text(json.dumps(BLATT), encoding="utf-8")
        self.auftrag.update(bezug="alt-auftrag", sitzung=sitzung,
                            text="Nachbesserung zu deinem Ergebnis: Aufgabe 1 leichter")
        claude = FalscherClaude(self.ordner, schritte)
        if not ok:  # erster Lauf (Fortsetzen) scheitert
            echt = claude.__call__
            def laufen(prompt, sitzung=None):
                e = echt(prompt, sitzung)
                return Ergebnis(text="Sitzung nicht gefunden", sitzung=None, ok=False) if len(claude.prompts) == 1 else e
            return material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=laufen, bauen=BAUEN), claude
        return material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN), claude

    def test_nachbesserung_setzt_sitzung_fort(self):
        leichter = dict(BLATT, titel="Kant leicht")
        f, claude = self.nachbesserung([(leichter, "Aufgabe 1 hat jetzt Satzanfänge."), (None, "Leichter gemacht.")])
        self.assertEqual(claude.sitzungen, ["alt", "s1"])
        self.assertIn("Aufgabe 1 leichter", claude.prompts[0])
        self.assertIn("data/arbeit/20261022-120000-unterricht-abcdef/beschreibung.json", claude.prompts[0])
        self.assertNotIn("Skill einzelmaterial", claude.prompts[0])  # kennt Claude aus der Sitzung
        self.assertIn("Kontrolltext", claude.prompts[1])
        self.assertEqual(f.datei.name, "Arbeitsblatt Kant leicht.docx")
        self.assertEqual(f.begleittext, "Leichter gemacht.")
        # das alte Ergebnis bleibt, wie es war
        self.assertEqual(json.loads((self.hier / "data/arbeit/alt-auftrag/beschreibung.json").read_text()), BLATT)

    def test_nachbesserung_ohne_aenderung_nur_antwort(self):
        f, claude = self.nachbesserung([(None, "Aufgabe 1 ist schon die leichteste.")])
        self.assertIsNone(f.datei)
        self.assertEqual((f.begleittext, f.laeufe), ("Aufgabe 1 ist schon die leichteste.", 1))
        self.assertIn("Nachbesserung ohne Änderung, nur Antwort", f.hinweise)
        self.assertTrue((self.ordner / "beschreibung.json").is_file())  # Grundlage für die nächste Nachbesserung

    def test_nachbesserung_ohne_sitzung_neuer_lauf(self):
        f, claude = self.nachbesserung([(dict(BLATT, titel="Neu"), "a"), (None, "Fertig.")], sitzung=None)
        self.assertEqual(claude.sitzungen, [None, "s1"])
        self.assertIn("Skill einzelmaterial", claude.prompts[0])
        self.assertIn("## Lias bisheriges Material", claude.prompts[0])
        self.assertEqual(f.datei.name, "Arbeitsblatt Neu.docx")

    def test_nachbesserung_fortsetzen_scheitert(self):
        f, claude = self.nachbesserung([("{kaputt", "x"), (dict(BLATT, titel="Neu"), "a"), (None, "Fertig.")], ok=False)
        self.assertEqual(claude.sitzungen, ["alt", None, "s1"])
        self.assertIn("## Lias bisheriges Material", claude.prompts[1])
        self.assertEqual(f.laeufe, 3)
        self.assertTrue(any("nicht fortgesetzt" in h for h in f.hinweise))
        self.assertEqual(f.datei.name, "Arbeitsblatt Neu.docx")

    # Mehrere Dateien in einem Lauf (board-plan.md 4 und 5)
    def test_prompt_wunsch_art(self):
        self.assertEqual(material.prompt_wunsch_art("Arbeitsblatt Kant"), "")
        self.assertIn("Reihenentwurf", material.prompt_wunsch_art("Reihenentwurf: Straftheorien, Klasse 8"))
        lek = material.prompt_wunsch_art("Lernerfolgskontrolle: Straftheorien")
        self.assertIn("beschreibung-erwartungshorizont.json", lek)
        v = material.prompt_wunsch_art("Arbeitsblatt Kant\nVarianten: einfach, Level und Comic-Fassung")
        self.assertIn("beschreibung-einfach.json, beschreibung-niveau-1.json, beschreibung-niveau-2.json, "
                      "beschreibung-niveau-3.json, beschreibung-comic-fassung.json.", v)
        self.assertIn("beschreibung-hilfekarten.json", material.prompt_wunsch_art("Auch als: mit Hilfekarten"))

    def test_dateiname_mit_zusatz(self):
        self.assertEqual(material.dateiname(BLATT, "niveau-1"), "Arbeitsblatt Der kategorische Imperativ (Niveau 1).docx")

    def test_lek_mit_erwartungshorizont(self):
        self.auftrag["text"] = "Lernerfolgskontrolle: Kant, Klasse 10"
        eh = dict(BLATT, titel="Der kategorische Imperativ")
        f, claude = self.bearbeiten([({"beschreibung.json": BLATT, "beschreibung-erwartungshorizont.json": eh},
                                      "Entwurf"), (None, "LEK und Erwartungshorizont.")])
        self.assertEqual([d.name for d in f.dateien], ["Arbeitsblatt Der kategorische Imperativ.docx",
                                                       "Arbeitsblatt Der kategorische Imperativ (Erwartungshorizont).docx"])
        self.assertTrue(all(d.is_file() for d in f.dateien))
        self.assertEqual(f.datei, f.dateien[0])
        self.assertIn("## Art des Auftrags", claude.prompts[0])
        self.assertIn("=== Arbeitsblatt Der kategorische Imperativ (Erwartungshorizont).docx ===", claude.prompts[1])

    def test_fehler_in_zusatzdatei(self):
        kaputt = dict(BLATT, bloecke=[{"typ": "gibtsnicht"}])
        f, claude = self.bearbeiten([({"beschreibung.json": BLATT, "beschreibung-einfach.json": kaputt}, "a"),
                                     ({"beschreibung-einfach.json": BLATT}, "b"), (None, "Fertig.")])
        self.assertIn("beschreibung-einfach.json: ", claude.prompts[1])
        self.assertNotIn("beschreibung.json: ", claude.prompts[1])
        self.assertEqual(len(f.dateien), 2)

    def test_zu_viele_dateien(self):
        viele = {f"beschreibung-v{i}.json": dict(BLATT, titel=f"V{i}") for i in range(material.MAX_DATEIEN)}
        f, _ = self.bearbeiten([({"beschreibung.json": BLATT, **viele}, "a"), (None, "Fertig.")])
        self.assertEqual(len(f.dateien), material.MAX_DATEIEN)
        self.assertTrue(any(h.startswith("nicht gebaut: ") for h in f.hinweise))

    def test_varianten_zu_fertigem_material(self):
        varianten = {f"beschreibung-niveau-{i}.json": dict(BLATT, titel=f"Kant {i}") for i in (1, 2, 3)}
        f, claude = self.nachbesserung([(varianten, "Drei Niveaus."), (None, "Drei Niveaus dazu.")])
        self.assertIn("beschreibung-<name>.json", claude.prompts[0])
        self.assertEqual(len(f.dateien), 4)
        self.assertEqual(f.dateien[0].name, "Arbeitsblatt Der kategorische Imperativ.docx")
        self.assertEqual(f.dateien[1].name, "Arbeitsblatt Kant 1 (Niveau 1).docx")

    def test_nachbesserung_kopiert_zusatzdateien(self):
        alt = self.hier / "data" / "arbeit" / "alt-auftrag"
        alt.mkdir(parents=True)
        (alt / "beschreibung-erwartungshorizont.json").write_text(json.dumps(BLATT), encoding="utf-8")
        f, claude = self.nachbesserung([(None, "Passt schon.")])
        self.assertEqual(f.dateien, [])
        self.assertTrue((self.ordner / "beschreibung-erwartungshorizont.json").is_file())

    def test_nachbesserung_mit_eigener_fassung(self):
        eingang = self.hier / "data" / "eingang" / "nb"
        eingang.mkdir(parents=True)
        (eingang / "foto.jpg").write_bytes(b"x")
        self.auftrag["dateien"] = ["data/eingang/nb/foto.jpg"]
        f, claude = self.nachbesserung([(dict(BLATT, titel="Lias Fassung"), "a"), (None, "Fertig.")])
        self.assertEqual(claude.sitzungen[0], "alt")
        self.assertIn("## Angehängte Dateien von Lia", claude.prompts[0])
        self.assertIn("Lias eigene Fassung", claude.prompts[0])
        self.assertIn("data/eingang/nb/foto.jpg", claude.prompts[0])

    def test_nachbesserung_ohne_altes_material(self):
        self.auftrag["bezug"] = "gibt-es-nicht"
        with self.assertRaises(material.MaterialFehler):
            self.bearbeiten([])

    def test_lauf_fehlgeschlagen(self):
        def laufen(prompt, sitzung=None):
            return Ergebnis(text="kaputt", sitzung=None, ok=False)
        with self.assertRaises(material.MaterialFehler):
            material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=laufen, bauen=BAUEN)

    def test_zeitbudget(self):
        uhr = iter([0, material.ZEIT_BUDGET_S + 1])
        claude = FalscherClaude(self.ordner, [("{", "a"), (BLATT, "b")])
        with self.assertRaises(material.MaterialFehler):
            material.bearbeiten(self.auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN, uhr=lambda: next(uhr))
        self.assertEqual(len(claude.prompts), 1)

    def test_kontrolle_ohne_vorschau(self):
        text = material.prompt_kontrolle("b.json", "Inhalt", [], ["Keine Vorschau: soffice fehlt"])
        self.assertIn("soffice fehlt", text)
        self.assertNotIn("Öffne jedes", text)
        text = material.prompt_kontrolle("b.json", "Inhalt", ["data/x-vorschau/seite-1.png"], [])
        self.assertIn("- data/x-vorschau/seite-1.png", text)


class AnhaengeTest(unittest.TestCase):
    def setUp(self):
        self.hier = Path(tempfile.mkdtemp())
        self.eingang = self.hier / "data" / "eingang" / "a1"
        self.eingang.mkdir(parents=True)
        self.vorschau_aufrufe = []

    def vorschau(self, quelle, ordner, anzahl=2):
        self.vorschau_aufrufe.append(quelle.name)
        ordner.mkdir(parents=True, exist_ok=True)
        return [ordner / f"seite-{i:02d}.png" for i in range(1, anzahl + 1)]

    def datei(self, name, inhalt=b"x") -> str:
        (self.eingang / name).write_bytes(inhalt)
        return f"data/eingang/a1/{name}"

    def test_bild_und_unbekanntes(self):
        zeilen = material.anhaenge_vorbereiten(self.hier, [self.datei("foto.jpg"), self.datei("alt.odt")],
                                               self.vorschau)
        self.assertEqual(zeilen, ["- data/eingang/a1/foto.jpg: Bild, mit Read öffnen",
                                  "- data/eingang/a1/alt.odt: Format ohne Aufbereitung, versuche Read"])
        self.assertEqual(self.vorschau_aufrufe, [])

    def test_docx_mit_textfassung_und_hoechstens_8_bildern(self):
        import docx
        d = docx.Document()
        d.add_paragraph("Der Ring des Gyges")
        d.save(self.eingang / "text.docx")
        zeilen = material.anhaenge_vorbereiten(self.hier, ["data/eingang/a1/text.docx"],
                                               lambda q, o: self.vorschau(q, o, anzahl=10))
        txt = self.eingang / "text.docx.txt"
        self.assertIn("Ring des Gyges", txt.read_text(encoding="utf-8"))
        self.assertIn("  Textfassung: data/eingang/a1/text.docx.txt", zeilen)
        bilder = [z for z in zeilen if "Seitenbilder" in z][0]
        self.assertIn("nur die ersten 8 von 10", bilder)
        self.assertIn("data/eingang/a1/text.docx-seiten/seite-08.png", bilder)
        self.assertNotIn("seite-09", bilder)

    def test_word_kommentare(self):
        import docx
        docx.Document().save(self.eingang / "eigene.docx")
        kommentare = [{"stelle": "Aufgabe 2", "kommentar": "zu schwer", "autor": "Lia"},
                      {"stelle": "", "kommentar": "Bild fehlt", "autor": "Lia"}]
        with mock.patch.object(material.textfassung, "word_kommentare", return_value=kommentare):
            zeilen = material.anhaenge_vorbereiten(self.hier, ["data/eingang/a1/eigene.docx"], self.vorschau)
        self.assertIn("  Kommentare in der Datei (kommentierte Stelle: Kommentar):", zeilen)
        self.assertIn("    - „Aufgabe 2“: zu schwer", zeilen)
        self.assertIn("    - Bild fehlt", zeilen)
        with mock.patch.object(material.textfassung, "word_kommentare", side_effect=ValueError("kaputt")):
            zeilen = material.anhaenge_vorbereiten(self.hier, ["data/eingang/a1/eigene.docx"], self.vorschau)
        self.assertIn("  Kommentare nicht lesbar (kaputt)", zeilen)

    def test_scan_ohne_text(self):
        import io

        import pypdf
        w = pypdf.PdfWriter()
        w.add_blank_page(595, 842)
        puffer = io.BytesIO()
        w.write(puffer)
        rel = self.datei("scan.pdf", puffer.getvalue())
        zeilen = material.anhaenge_vorbereiten(self.hier, [rel], self.vorschau)
        self.assertTrue(any("vermutlich ein Scan" in z for z in zeilen))
        self.assertTrue(any("Seitenbilder: data/eingang/a1/scan.pdf-seiten/seite-01.png" in z for z in zeilen))
        self.assertFalse((self.eingang / "scan.pdf.txt").exists())

    def test_kaputte_pdf_und_vorschau_fehler(self):
        def kaputt(quelle, ordner):
            raise renderer.vorschau.VorschauFehler("PDF lässt sich nicht öffnen")
        zeilen = material.anhaenge_vorbereiten(self.hier, [self.datei("kaputt.pdf", b"kein pdf")], kaputt)
        self.assertTrue(any("Text nicht lesbar" in z for z in zeilen))
        self.assertTrue(any("Keine Seitenbilder (PDF lässt sich nicht öffnen)" in z for z in zeilen))

    def test_prompt(self):
        self.assertEqual(material.prompt_anhaenge([]), "")
        self.assertIn("Angehängte Dateien von Lia", material.prompt_anhaenge(["- a.jpg: Bild"]))

    def test_bearbeiten_mit_anhang(self):
        auftrag = {"id": "20261022-120000-unterricht-abcdef", "text": "Mach daraus ein Arbeitsblatt",
                   "dateien": [self.datei("foto.jpg")]}
        claude = FalscherClaude(self.hier / "data" / "arbeit" / auftrag["id"], [(BLATT, "a"), (None, "b")])
        material.bearbeiten(auftrag, self.hier, PROFIL, laufen=claude, bauen=BAUEN, vorschau=self.vorschau)
        self.assertIn("- data/eingang/a1/foto.jpg: Bild, mit Read öffnen", claude.prompts[0])
        self.assertIn("Angehängte Dateien von Lia", claude.prompts[0])


if __name__ == "__main__":
    unittest.main()
