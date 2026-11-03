"""Tests für agentkit.struktur (Strukturplan docs/struktur-pflege-plan.md, Abschnitt 10: Regeln 1–3, 6, 15, 17).

Vorlage: daten/reihen_alt.toml (eingefrorene Kopie der echten reihen.toml) und daten/reihen_neu.toml (dieselben
Daten im neuen Format).
"""

import contextlib
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from agentkit import struktur

DATEN = Path(__file__).parent / "daten"
ALT = (DATEN / "reihen_alt.toml").read_text(encoding="utf-8")
NEU = (DATEN / "reihen_neu.toml").read_text(encoding="utf-8")
GRUPPE = "Geheimer Text zur Gruppe"


def fehler_zu(text: str, lerngruppen: dict | None = None) -> list[str]:
    return struktur.aufloesen(text, lerngruppen or {})[1]


class TestAltesFormat(unittest.TestCase):
    """Bis zur Migration (Bauschritt 3) liest struktur die heutige Datei."""

    def setUp(self):
        self.s = struktur.aus_text(ALT)

    def test_echte_datei_ist_gueltig(self):
        self.assertEqual(fehler_zu(ALT), [])
        self.assertEqual(self.s.format, "alt")
        self.assertEqual(len(self.s.reihen), 14)

    def test_fach_und_klasse_abgeleitet(self):
        self.assertEqual([f["id"] for f in self.s.faecher], ["ethik", "darstellendes-spiel"])
        self.assertEqual([k["id"] for k in self.s.klassen], [
            "ethik-8", "darstellendes-spiel-kurs-12", "darstellendes-spiel-kurs-11-klasse", "ethik-7-2025-26",
            "darstellendes-spiel-kurs-11-2025-26"])
        archiv = self.s.objekt("darstellendes-spiel-kurs-11-2025-26")
        self.assertEqual((archiv["name"], archiv["schuljahr"], len(archiv["reihen"])), ("Kurs 11", "2025/26", 6))

    def test_platzhalter_reihe_und_klasse_kollidieren_nicht(self):
        lage = self.s.ort("darstellendes-spiel-kurs-11")
        self.assertEqual(lage["ebene"], "reihe")
        self.assertEqual(lage["klasse"]["id"], "darstellendes-spiel-kurs-11-klasse")
        self.assertEqual(lage["fach"]["name"], "Darstellendes Spiel")

    def test_reihe_mit_bisherigen_feldern(self):
        r = self.s.reihe("ethik-8-straftheorien")
        self.assertEqual((r["fach"], r["klasse"], r["klasse_id"], r["titel"], r["stand"]),
                         ("Ethik", "8", "ethik-8", "Straftheorien (in Planung)", "laufend"))
        self.assertTrue(r["lerngruppe"].startswith("Platzhalter"))  # im alten Format an der Reihe
        self.assertEqual(r["agenten"], ["examen"])
        self.assertEqual(len(r["bisherige_reihen"]), 6)
        self.assertEqual(self.s.reihe("ethik-7-freundschaft")["schuljahr"], "2025/26")

    def test_stunden_mit_nr_werden_neu_gezaehlt(self):
        text = ALT + '\n[[reihe.stunde]]\nnr = 5\nthema = "Später"\n\n[[reihe.stunde]]\nnr = 2\nthema = "Früher"\n'
        r = struktur.aus_text(text).reihen[-1]
        self.assertEqual([(s["nr"], s["thema"]) for s in r["stunden"]], [(1, "Früher"), (2, "Später")])
        self.assertEqual(r["stunden"][0]["id"], f"{r['id']}-stunde-2")

    def test_reihe_ohne_id_bekommt_abgeleitete(self):
        s = struktur.aus_text('[[reihe]]\nfach = "Ethik"\nklasse = "9"\ntitel = "Würde (neu)"\n')
        self.assertEqual(s.reihen[0]["id"], "ethik-9-wuerde")


class TestNeuesFormat(unittest.TestCase):
    def setUp(self):
        self.s = struktur.aus_text(NEU, {"ethik-8": GRUPPE})

    def test_gueltig(self):
        self.assertEqual(fehler_zu(NEU), [])
        self.assertEqual(self.s.format, "neu")
        self.assertEqual(len(self.s.stunden()), 4)

    def test_reihe_aufgeloest(self):
        r = self.s.reihe("ethik-8-straftheorien")
        self.assertEqual((r["fach"], r["fach_id"], r["klasse"], r["klasse_id"], r["schuljahr"], r["stand"]),
                         ("Ethik", "ethik", "8", "ethik-8", "2026/27", "geplant"))
        self.assertEqual(r["lerngruppe"], GRUPPE)
        self.assertEqual(self.s.objekt("ethik-8")["lerngruppe"], GRUPPE)
        self.assertEqual(self.s.objekt("ethik-8")["herkunft"], "ethik-7-2025-26")

    def test_nummer_nur_ueber_sichtbare_stunden(self):
        r = self.s.reihe("ethik-8-straftheorien")
        self.assertEqual([(s["nr"], s["id"]) for s in r["stunden"]], [(1, "s-einstieg"), (2, "s-kant"), (3, "s-liszt")])
        self.assertEqual([(s["nr"], s["id"]) for s in r["ausgeblendete_stunden"]], [(None, "s-alt")])
        self.assertTrue(self.s.objekt("s-alt")["im_archiv"])

    def test_archiv_vererbt_sich_beim_lesen(self):
        self.assertTrue(self.s.objekt("ethik-7-2025-26")["im_archiv"])
        freundschaft = self.s.reihe("ethik-7-freundschaft")
        self.assertTrue(freundschaft["im_archiv"])
        self.assertEqual(freundschaft["archiviert"], "")  # steht nur an der Klasse
        self.assertFalse(self.s.reihe("ethik-8-helfen")["im_archiv"])
        fach = NEU.replace('name = "Ethik"\n', 'name = "Ethik"\narchiviert = "2026-11-03"\n')
        self.assertTrue(struktur.aus_text(fach).objekt("s-kant")["im_archiv"])

    def test_ort(self):
        lage = self.s.ort("s-kant")
        self.assertEqual((lage["ebene"], lage["fach"]["id"], lage["klasse"]["id"], lage["reihe"]["id"]),
                         ("stunde", "ethik", "ethik-8", "ethik-8-straftheorien"))
        self.assertEqual(self.s.ort("ethik")["klasse"], None)
        self.assertEqual(self.s.objekt("ethik")["klassen"], ["ethik-7-2025-26", "ethik-8"])
        self.assertIsNone(self.s.ort("gibt-es-nicht"))

    def test_klasse_ohne_reihe(self):
        self.assertEqual(self.s.objekt("darstellendes-spiel-kurs-11")["reihen"], [])


class TestPruefungsstunde(unittest.TestCase):
    """Examen ist eine Stunde mit Marke „Prüfung“ (Plan Abschnitt 2, F14)."""

    def test_genau_eine(self):
        s = struktur.aus_text(NEU)
        self.assertEqual([r["id"] for r in s.pruefungsreihen()], ["ethik-8-straftheorien"])
        stunde = s.pruefungsstunde("ethik-8-straftheorien")
        self.assertEqual((stunde["id"], stunde["nr"], stunde["thema"]), ("s-kant", 2, "Kant: Vergeltung"))

    def test_keine_oder_zwei_sind_ein_fehler(self):
        keine = struktur.aus_text(NEU.replace('marke = "Prüfung"', 'marke = "UB"'))
        zwei = struktur.aus_text(NEU.replace('marke = "UB"', 'marke = "Prüfung"'))
        for s, anzahl in ((keine, 0), (zwei, 2)):
            with self.subTest(anzahl=anzahl), self.assertRaises(struktur.StrukturFehler) as f:
                s.pruefungsstunde("ethik-8-straftheorien")
            self.assertIn(f"{anzahl} Stunden", str(f.exception))
        self.assertEqual(keine.pruefungsreihen(), [])

    def test_ausgeblendete_zaehlt_nicht(self):
        text = NEU.replace('thema = "Alte Idee, ausgeblendet"', 'thema = "Alte Idee, ausgeblendet"\nmarke = "Prüfung"')
        self.assertEqual(struktur.aus_text(text).pruefungsstunde("ethik-8-straftheorien")["id"], "s-kant")

    def test_archivierte_reihe_ist_keine_pruefungsreihe(self):
        text = NEU.replace('stand = "geplant"', 'stand = "geplant"\narchiviert = "2026-11-03"')
        self.assertEqual(struktur.aus_text(text).pruefungsreihen(), [])

    def test_unbekannte_reihe(self):
        with self.assertRaises(struktur.StrukturFehler):
            struktur.aus_text(NEU).pruefungsstunde("ethik-8")


class TestRegel1IdBleibt(unittest.TestCase):
    """Regel 1: Die id hängt nicht an Titel, Klasse oder Archiv (beim Lesen; die Operationen kommen in Bauschritt 4)."""

    def test_neues_format(self):
        geaendert = (NEU.replace('titel = "Straftheorien"', 'titel = "Strafe"')
                        .replace('klasse = "ethik-8"\ntitel = "Strafe"', 'klasse = "ethik-7-2025-26"\ntitel = "Strafe"')
                        .replace('stand = "geplant"', 'stand = "laufend"\narchiviert = "2026-11-03"'))
        r = struktur.aus_text(geaendert).reihe("ethik-8-straftheorien")
        self.assertEqual((r["titel"], r["klasse_id"], r["archiviert"]), ("Strafe", "ethik-7-2025-26", "2026-11-03"))
        self.assertEqual([s["id"] for s in r["stunden"]], ["s-einstieg", "s-kant", "s-liszt"])

    def test_altes_format_mit_gespeicherter_id(self):
        geaendert = ALT.replace('titel = "Straftheorien (in Planung)"', 'titel = "Strafe"').replace(
            'klasse = "8"\ntitel = "Strafe"', 'klasse = "9"\ntitel = "Strafe"')
        r = struktur.aus_text(geaendert).reihe("ethik-8-straftheorien")
        self.assertEqual((r["titel"], r["klasse"]), ("Strafe", "9"))

    def test_stunde_verschoben_behaelt_id_und_bekommt_neue_nummer(self):
        kant = '[[reihe.stunde]]\nid = "s-kant"\nthema = "Kant: Vergeltung"\nmarke = "Prüfung"\n\n'
        einstieg = '[[reihe.stunde]]\nid = "s-einstieg"\nthema = "Einstieg: Wozu Gefängnis?"\n\n'
        self.assertIn(kant, NEU)
        text = NEU.replace(kant, "").replace(einstieg, kant + einstieg)
        self.assertEqual(struktur.aus_text(text).objekt("s-kant")["nr"], 1)


class TestRegel2IdEinmalig(unittest.TestCase):
    """Regel 2: eine id gilt über alle Ebenen."""

    def test_doppelt_ueber_ebenen(self):
        for alt, neu in (('id = "s-liszt"', 'id = "ethik-8"'),  # Stunde = Klasse
                         ('id = "ethik-8-helfen"', 'id = "ethik"'),  # Reihe = Fach
                         ('id = "s-alt"', 'id = "s-kant"')):  # zwei Stunden
            with self.subTest(neu=neu):
                fehler = fehler_zu(NEU.replace(alt, neu))
                self.assertTrue(any("doppelt" in f for f in fehler), fehler)

    def test_doppelt_im_alten_format(self):
        text = ALT.replace('id = "ethik-7-freundschaft"', 'id = "ethik-7-tiere-toeten"')
        self.assertTrue(any("doppelt" in f for f in fehler_zu(text)))


class TestRegel3IdGespeichert(unittest.TestCase):
    """Regel 3: Im neuen Format hat jedes Objekt eine gespeicherte id (keine abgeleitete)."""

    def test_alle_objekte_der_vorlage_haben_eine(self):
        s = struktur.aus_text(NEU)
        for o in s.faecher + s.klassen + s.reihen + s.stunden():
            self.assertRegex(o["id"], struktur.ID_MUSTER)
            self.assertIn(f'id = "{o["id"]}"', NEU)

    def test_fehlende_id_je_ebene(self):
        for zeile, wo in (('id = "darstellendes-spiel"\n', "Fach 2"), ('id = "ethik-8"\n', "Klasse 2"),
                          ('id = "ethik-8-helfen"\n', "Reihe 3"), ('id = "s-liszt"\n', "Stunde 4")):
            with self.subTest(wo=wo):
                fehler = fehler_zu(NEU.replace(zeile, "", 1))
                self.assertTrue(any(wo in f and "id fehlt" in f for f in fehler), fehler)

    def test_id_nur_kleinbuchstaben_ziffern_bindestriche(self):
        for falsch in ("Ethik", "ethik_8", "-ethik", "ethik--8", "x" * 81):
            with self.subTest(falsch=falsch):
                self.assertTrue(fehler_zu(NEU.replace('id = "ethik-8-helfen"', f'id = "{falsch}"')))


class TestRegel6AgentInEinerReihe(unittest.TestCase):
    def test_agent_in_zwei_reihen(self):
        neu = NEU.replace('titel = "Helfen"', 'titel = "Helfen"\nagenten = ["theater"]')
        alt = ALT.replace('titel = "Grundlagen Körper"', 'titel = "Grundlagen Körper"\nagenten = ["theater"]')
        for text in (neu, alt):
            fehler = fehler_zu(text)
            self.assertTrue(any("'theater' steht in zwei Reihen" in f for f in fehler), fehler)


class TestRegel15UngueltigWirdErkannt(unittest.TestCase):
    """Regel 15 (Lesehälfte): pruefen erkennt ungültige Dateien, laden liefert dann nichts Halbes."""

    FAELLE = {
        "kein TOML": ("[[reihe]]\nid = ", "kein gültiges TOML"),
        "unbekannter Eintrag": ('[[stunde]]\nid = "x"\n', "unbekannte Einträge"),
        "Tabelle statt Liste": ('[fach]\nid = "x"\n', "als [[fach]] schreiben"),
        "unbekanntes Feld": (NEU.replace('titel = "Helfen"', 'titel = "Helfen"\nfarbe = "rot"'), "unbekannte Felder"),
        "Lerngruppe in reihen.toml": (NEU.replace('name = "8"', 'name = "8"\nlerngruppe = "x"'), "lerngruppen.toml"),
        "Fach an der Reihe": (NEU.replace('titel = "Helfen"', 'titel = "Helfen"\nfach = "Ethik"'), "unbekannte Felder"),
        "Klasse fehlt": (NEU.replace('klasse = "ethik-8"\ntitel = "Helfen"', 'klasse = "ethik-9"\ntitel = "Helfen"'),
                         "Klasse 'ethik-9' gibt es nicht"),
        "Fach fehlt": (NEU.replace('fach = "darstellendes-spiel"\nname = "Kurs 12"', 'fach = "musik"\nname = "Kurs 12"'),
                       "Fach 'musik' gibt es nicht"),
        "Name fehlt": (NEU.replace('name = "Kurs 11"', 'name = " "'), "name fehlt"),
        "Thema fehlt": (NEU.replace('thema = "von Liszt: Prävention"', 'thema = ""'), "thema fehlt"),
        "Stand": (NEU.replace('stand = "geplant"', 'stand = "fertig"'), "stand 'fertig'"),
        "Marke": (NEU.replace('marke = "UB"', 'marke = "Klausur"'), "marke 'Klausur'"),
        "Datum": (NEU.replace('archiviert = "2026-08-01"', 'archiviert = "gestern"'), "als Datum"),
        "Datum ohne Anführungszeichen": (NEU.replace('archiviert = "2026-08-01"', 'archiviert = 2026-08-01'),
                                         "Text in Anführungszeichen"),
        "Liste": (NEU.replace('agenten = ["theater"]', 'agenten = "theater"'), "Liste von Texten"),
        "Herkunft andere Ebene": (NEU.replace('herkunft = "ethik-7-2025-26"', 'herkunft = "ethik-7-freundschaft"'),
                                  "ist keine Klasse"),
        "Stunden als Tabelle": (NEU + '\n[reihe.stunde]\nid = "s-x"\nthema = "x"\n', "als [[reihe.stunde]]"),
        "alt: Stand": (ALT.replace('stand = "abgeschlossen"', 'stand = "fertig"', 1), "stand 'fertig'"),
        "alt: fach fehlt": (ALT.replace('fach = "Ethik"\n', "", 1), "fach fehlt"),
        "alt: nr doppelt": (ALT + '[[reihe.stunde]]\nnr = 1\nthema = "a"\n[[reihe.stunde]]\nnr = 1\nthema = "b"\n',
                            "doppelt"),
        "alt: nr fehlt": (ALT + '[[reihe.stunde]]\nthema = "a"\n', "nr als ganze Zahl"),
    }

    def test_fehler_je_fall(self):
        for name, (text, erwartet) in self.FAELLE.items():
            with self.subTest(name):
                fehler = fehler_zu(text)
                self.assertTrue(any(erwartet in f for f in fehler), fehler)
                with self.assertRaises(struktur.StrukturFehler):
                    struktur.aus_text(text)

    def test_lerngruppe_fuer_unbekannte_klasse(self):
        fehler = fehler_zu(NEU, {"ethik-9": GRUPPE})
        self.assertEqual(fehler, ["lerngruppen.toml: Klasse 'ethik-9' gibt es nicht in reihen.toml"])

    def test_fehlertexte_nennen_die_lerngruppe_nie(self):
        with tempfile.TemporaryDirectory() as tmp:
            instanz = Path(tmp)
            (instanz / "reihen.toml").write_text(NEU.replace('stand = "geplant"', 'stand = "x"'), encoding="utf-8")
            datei = instanz / "lerngruppen.toml"
            datei.write_text(f'"ethik-8" = "{GRUPPE}"\n"ethik-9" = "{GRUPPE}"\n', encoding="utf-8")
            datei.chmod(0o600)
            fehler = struktur.pruefen(instanz)
            self.assertEqual(len(fehler), 2)
            self.assertFalse(any(GRUPPE in f for f in fehler))


class TestDateien(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.instanz = Path(self.tmp.name) / "lia" / "instanz"
        self.instanz.mkdir(parents=True)
        self.datei = self.instanz / "reihen.toml"
        shutil.copy(DATEN / "reihen_neu.toml", self.datei)

    def tearDown(self):
        self.tmp.cleanup()

    def lerngruppen(self, text: str, rechte: int = 0o600):
        pfad = self.instanz / "lerngruppen.toml"
        pfad.write_text(text, encoding="utf-8")
        pfad.chmod(rechte)

    def test_regel17_lesen_aendert_nichts(self):
        vorher, zeit = self.datei.read_bytes(), self.datei.stat().st_mtime_ns
        eins, zwei = struktur.laden(self.instanz), struktur.laden(self.instanz)
        self.assertEqual(self.datei.read_bytes(), vorher)
        self.assertEqual(self.datei.stat().st_mtime_ns, zeit)
        self.assertEqual(eins, zwei)
        self.assertEqual(sorted(p.name for p in self.instanz.iterdir()), ["reihen.toml"])  # legt nichts an

    def test_lerngruppen_aus_eigener_datei(self):
        self.lerngruppen(f'"ethik-8" = """{GRUPPE}"""\n')
        s = struktur.laden(self.instanz)
        self.assertEqual(s.reihe("ethik-8-straftheorien")["lerngruppe"], GRUPPE)
        self.assertEqual(s.reihe("darstellendes-spiel-kurs-12-der-nackte-wahnsinn")["lerngruppe"], "")

    def test_lerngruppen_nur_mit_rechten_600(self):
        self.lerngruppen(f'"ethik-8" = "{GRUPPE}"\n', 0o644)
        fehler = struktur.pruefen(self.instanz)
        self.assertTrue(any("chmod 600" in f for f in fehler), fehler)
        with self.assertRaises(struktur.StrukturFehler):
            struktur.laden(self.instanz)

    def test_lerngruppen_kaputt(self):
        self.lerngruppen('"ethik-8" = 8\n')
        self.assertTrue(struktur.pruefen(self.instanz))

    def test_ohne_datei_leer(self):
        self.datei.unlink()
        s = struktur.laden(self.instanz)
        self.assertEqual((s.faecher, s.klassen, s.reihen), ([], [], []))

    def test_kommandozeile(self):
        with contextlib.redirect_stdout(io.StringIO()) as aus:
            self.assertEqual(struktur.main([str(self.instanz)]), 0)
        self.assertIn("Format neu", aus.getvalue())
        self.datei.write_text(NEU.replace('stand = "geplant"', 'stand = "x"'), encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()) as fehler:
            self.assertEqual(struktur.main([str(self.instanz)]), 1)
        self.assertIn("stand 'x'", fehler.getvalue())


class TestHaengtDran(unittest.TestCase):
    """Quellen aus Abschnitt 3.1 (Regel 8 mit den Lösch-Operationen folgt in Bauschritt 4)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self.tmp.name)
        self.instanz = self.wurzel / "lia" / "instanz"
        self.instanz.mkdir(parents=True)
        (self.instanz / "reihen.toml").write_text(NEU, encoding="utf-8")
        self.webapp = self.wurzel / "webapp-data"

    def tearDown(self):
        self.tmp.cleanup()

    def json_ablegen(self, ordner: str, name: str, daten: dict):
        pfad = self.instanz / ordner / f"{name}.json"
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps(daten), encoding="utf-8")

    def haken(self, kennung: str) -> dict[str, str]:
        s = struktur.laden(self.instanz)
        return {h["quelle"]: h["text"] for h in s.haengt_dran(kennung, webapp_daten=self.webapp)}

    def test_nichts_dran(self):
        self.assertEqual(self.haken("ethik-8-helfen"), {})
        self.assertEqual(self.haken("darstellendes-spiel-kurs-11"), {})
        self.assertEqual(self.haken("s-liszt"), {})

    def test_ebenen_darunter(self):
        self.assertEqual(self.haken("ethik"), {"darunter": "2 Klassen"})
        self.assertEqual(self.haken("ethik-7-2025-26"), {"darunter": "1 Reihe"})
        self.assertEqual(self.haken("ethik-8-straftheorien")["darunter"], "4 Stunden")  # auch ausgeblendete

    def test_auftraege_mit_reihe_oder_ort(self):
        self.json_ablegen("auftraege/neu", "a", {"agent": "unterricht", "reihe": "ethik-8-helfen"})
        self.json_ablegen("auftraege/erledigt", "b", {"agent": "unterricht", "ort": "ethik-8-helfen"})
        self.json_ablegen("auftraege/erledigt", "c", {"agent": "unterricht", "reihe": "ethik-7-freundschaft"})
        self.json_ablegen("auftraege/neu", "d", {"agent": "unterricht", "ort": "s-liszt"})
        self.assertEqual(self.haken("ethik-8-helfen"), {"auftraege": "2 Aufträge"})
        self.assertEqual(self.haken("s-liszt"), {"auftraege": "1 Auftrag"})

    def test_entwuerfe(self):
        self.json_ablegen("freigabe/offen", "e", {"agent": "examen", "ort": "ethik-8-helfen"})
        self.assertEqual(self.haken("ethik-8-helfen"), {"entwuerfe": "1 Entwurf"})

    def test_agenten(self):
        self.assertEqual(self.haken("darstellendes-spiel-kurs-12-der-nackte-wahnsinn"), {"agenten": "Agenten: theater"})

    def test_webapp_zustand(self):
        schluessel = hashlib.sha256(str(self.instanz.resolve()).encode()).hexdigest()[:12]
        (self.webapp / "zustand").mkdir(parents=True)
        (self.webapp / "zustand" / f"{schluessel}.json").write_text(json.dumps({
            "stunden": {"ethik-8-helfen": [{"thema": "x"}]},
            "stunde_von": {"u1": {"reihe": "ethik-8-helfen", "nr": 1}, "u2": {"stunde": "s-liszt"}},
            "reihe_von": {"u3": "ethik-8-helfen"}}), encoding="utf-8")
        self.assertEqual(self.haken("ethik-8-helfen"), {"webapp": "3 Zuordnungen in der Web-App"})
        self.assertEqual(self.haken("s-liszt"), {"webapp": "1 Zuordnung in der Web-App"})

    def test_chat_verlauf(self):
        pfad = self.wurzel / "lia" / "chat" / "data" / "verlauf.jsonl"
        pfad.parent.mkdir(parents=True)
        pfad.write_text(json.dumps({"reihe": "ethik-8-helfen"}) + "\nkaputt\n" + json.dumps({"reihe": None}) + "\n",
                        encoding="utf-8")
        self.assertEqual(self.haken("ethik-8-helfen"), {"chat": "1 Eintrag im Chat-Verlauf"})

    def test_verweise(self):
        self.assertEqual(self.haken("s-kant"), {"verweise": "Prüfungsstunde (lia/examen)"})
        (self.wurzel / "lia" / "recherche").mkdir()
        (self.wurzel / "lia" / "recherche" / "agent.py").write_text('REIHE = "ethik-8-helfen"\n', encoding="utf-8")
        (self.wurzel / "lia" / "unterricht").mkdir()
        os.symlink("../instanz/reihen.toml", self.wurzel / "lia" / "unterricht" / "reihen.toml")
        self.assertEqual(self.haken("ethik-8-helfen"), {"verweise": "Verweis in lia/recherche/agent.py"})

    def test_unbekannte_id(self):
        with self.assertRaises(struktur.StrukturFehler):
            struktur.laden(self.instanz).haengt_dran("gibt-es-nicht")


if __name__ == "__main__":
    unittest.main()
