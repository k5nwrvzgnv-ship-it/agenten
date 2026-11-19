"""Tests für gruppe_logik.py (Gruppen-Bot Rüdiger), ohne Netz und ohne Telegram."""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))

import gruppe_logik as gl  # noqa: E402

GRUPPE, JAN, HENRI, FREMD, BOT = -100123, 11, 22, 99, 9271126195
ZUGANG = gl.Zugang(GRUPPE, frozenset({JAN, HENRI}), BOT, "nichtsotiefruedigerbot")


def nachricht(text="@nichtsotiefruedigerbot Wie funktioniert die Kamera?", chat=GRUPPE, von=HENRI, **mehr):
    m = {"message_id": 5, "chat": {"id": chat, "type": "supergroup", "title": "Holz"},
         "from": {"id": von, "first_name": "Henri"}, "text": text, **mehr}
    if text and text.startswith("@nichtsotiefruedigerbot"):
        m["entities"] = [{"type": "mention", "offset": 0, "length": 23}]
    return {"update_id": 1, "message": m}


class TestZugang(unittest.TestCase):
    def test_aus_env(self):
        z = gl.zugang_aus_env({"GRUPPE_CHAT_ID": "-100123", "GRUPPE_NUTZER_IDS": "11, 22 33"}, BOT, "@rbot")
        self.assertEqual((z.chat_id, z.nutzer, z.bot_name), (-100123, frozenset({11, 22, 33}), "rbot"))
        leer = gl.zugang_aus_env({}, BOT, "rbot")
        self.assertEqual((leer.chat_id, leer.nutzer), (None, frozenset()))
        with self.assertRaises(gl.LogikFehler):
            gl.zugang_aus_env({"GRUPPE_CHAT_ID": "abc"}, BOT, "rbot")

    def test_erwaehnung_in_der_gruppe(self):
        a = gl.anfrage_aus(nachricht(), ZUGANG)
        self.assertEqual((a.text, a.name, a.nutzer_id, a.antwort_auf), ("Wie funktioniert die Kamera?", "Henri",
                                                                          HENRI, None))

    def test_nur_eine_gruppe_und_bekannte_personen(self):
        self.assertIsNone(gl.anfrage_aus(nachricht(chat=-100999), ZUGANG))
        self.assertIsNone(gl.anfrage_aus(nachricht(von=FREMD), ZUGANG))
        self.assertIsNone(gl.anfrage_aus(nachricht(chat=HENRI), ZUGANG))  # Privatchat
        ohne_gruppe = gl.Zugang(None, frozenset({HENRI}), BOT, "nichtsotiefruedigerbot")
        self.assertIsNone(gl.anfrage_aus(nachricht(), ohne_gruppe))
        bot = nachricht()
        bot["message"]["from"]["is_bot"] = True
        self.assertIsNone(gl.anfrage_aus(bot, ZUGANG))

    def test_ohne_erwaehnung_nichts(self):
        self.assertIsNone(gl.anfrage_aus(nachricht("Wie funktioniert die Kamera?"), ZUGANG))
        # Erwähnung eines anderen Bots zählt nicht
        anders = nachricht("@anderbot Hallo")
        anders["message"]["entities"] = [{"type": "mention", "offset": 0, "length": 9}]
        self.assertIsNone(gl.anfrage_aus(anders, ZUGANG))
        self.assertIsNone(gl.anfrage_aus({"update_id": 2, "edited_message": nachricht()["message"]}, ZUGANG))

    def test_antwort_auf_den_bot(self):
        u = nachricht("Und in Laufrichtung?", reply_to_message={"message_id": 40, "from": {"id": BOT},
                                                               "text": "Es ist eine Zeilenkamera."})
        a = gl.anfrage_aus(u, ZUGANG)
        self.assertEqual((a.antwort_auf, a.zitat), (40, "Es ist eine Zeilenkamera."))
        # Antwort auf Jan ohne Erwähnung: nicht für den Bot
        u = nachricht("Stimmt", reply_to_message={"message_id": 41, "from": {"id": JAN}, "text": "x"})
        self.assertIsNone(gl.anfrage_aus(u, ZUGANG))

    def test_foto_mit_beschriftung_und_zitiertes_foto(self):
        u = nachricht(None, caption="@nichtsotiefruedigerbot Ist das ein Durchfallast?",
                      caption_entities=[{"type": "mention", "offset": 0, "length": 23}],
                      photo=[{"file_id": "klein", "file_size": 100}, {"file_id": "gross", "file_size": 9000}])
        del u["message"]["text"]
        a = gl.anfrage_aus(u, ZUGANG)
        self.assertEqual(a.text, "Ist das ein Durchfallast?")
        self.assertEqual([d["file_id"] for d in a.dateien], ["gross"])
        # Erwähnung als Antwort auf Henris Foto: das Foto gehört dazu
        u = nachricht("@nichtsotiefruedigerbot was ist das?", von=JAN,
                      reply_to_message={"message_id": 7, "from": {"id": HENRI},
                                        "document": {"file_id": "d1", "file_name": "../böse name.pdf"}})
        a = gl.anfrage_aus(u, ZUGANG)
        self.assertEqual(a.dateien[0]["file_id"], "d1")
        self.assertNotIn("/", a.dateien[0]["name"])
        self.assertIsNone(a.antwort_auf)

    def test_nur_erwaehnung_ohne_inhalt(self):
        self.assertIsNone(gl.anfrage_aus(nachricht("@nichtsotiefruedigerbot"), ZUGANG))

    def test_herkunft_fuer_ids(self):
        h = gl.herkunft(nachricht(von=FREMD))
        self.assertEqual((h["chat_id"], h["nutzer_id"], h["chat"]), (GRUPPE, FREMD, "Holz"))
        self.assertIsNone(gl.herkunft({"update_id": 3}))


class TestFreischalten(unittest.TestCase):
    def test_unbekannt_in_der_gruppe(self):
        wer = gl.unbekannt_in_gruppe(nachricht(von=FREMD), ZUGANG)
        self.assertEqual(wer, {"nutzer_id": FREMD, "name": "Henri"})
        self.assertIsNone(gl.unbekannt_in_gruppe(nachricht(von=HENRI), ZUGANG))  # schon frei
        self.assertIsNone(gl.unbekannt_in_gruppe(nachricht(von=FREMD, chat=-100999), ZUGANG))  # andere Gruppe
        self.assertIsNone(gl.unbekannt_in_gruppe(nachricht("ohne Erwähnung", von=FREMD), ZUGANG))
        antwort = nachricht("und?", von=FREMD, reply_to_message={"message_id": 3, "from": {"id": BOT}, "text": "x"})
        self.assertEqual(gl.unbekannt_in_gruppe(antwort, ZUGANG)["nutzer_id"], FREMD)

    def test_mit_nutzern(self):
        z = gl.mit_nutzern(ZUGANG, {"99": "Felix"})
        self.assertIn(FREMD, z.nutzer)
        self.assertIsNotNone(gl.anfrage_aus(nachricht(von=FREMD), z))
        self.assertNotIn(FREMD, ZUGANG.nutzer)  # Zugang selbst bleibt unverändert
        self.assertIn("ID 99", gl.freischalt_meldung("Felix", 99, "Lamellen-Scan"))


class TestStil(unittest.TestCase):
    def test_stilproben_aus_der_gruppe(self):
        verlauf = [{"name": "Henri", "frage": "nimmt die kamera immer ein paar cm auf?", "antwort": "Zeilenkamera"},
                   {"name": "Felix", "frage": "ok", "antwort": "x"},
                   {"name": "Felix", "frage": "nimmt die kamera immer ein paar cm auf?", "antwort": "y"}]
        proben = gl.stilproben(verlauf, "zitat hier", "und wie schnell?")
        self.assertEqual(proben, ["nimmt die kamera immer ein paar cm auf?", "zitat hier", "und wie schnell?"])
        self.assertNotIn("Zeilenkamera", proben)  # Rüdigers eigene Antworten sind kein Vorbild
        self.assertEqual(len(gl.stilproben([{"frage": f"frage {i}"} for i in range(30)])), gl.MAX_STILPROBEN)

    def test_prompt_hat_stil(self):
        a = gl.Anfrage(GRUPPE, 5, HENRI, "Henri", "safe ne zeilenkamera oder?")
        p = gl.prompt_frage(a, [], [], datetime(2026, 11, 19, 12, 0))
        self.assertIn("Stilproben", p)
        self.assertIn("- safe ne zeilenkamera oder?", p)
        self.assertIn("per Du", gl.ROLLE)
        self.assertIn("Keine ungefragten Abstecher", gl.ROLLE)
        self.assertIn("keine internen Ordner", gl.ROLLE.replace("Nenn keine internen Ordner", "keine internen Ordner"))


class TestGrenzen(unittest.TestCase):
    def test_tageslimit(self):
        jetzt = datetime(2026, 11, 19, 12, 0)
        alt = [(jetzt - timedelta(hours=25)).isoformat()] * 50
        frisch = [(jetzt - timedelta(hours=1)).isoformat()] * 3
        self.assertTrue(gl.noch_erlaubt(alt + frisch, jetzt, 4))
        self.assertFalse(gl.noch_erlaubt(frisch + frisch[:1], jetzt, 4))
        self.assertTrue(gl.noch_erlaubt(["kaputt"], jetzt, 1))

    def test_lese_ordner_nie_andere_agenten(self):
        wurzel = HIER.parent
        karte = gl.lese_ordner_karte(HIER, wurzel)
        for pfad in karte:
            teile = pfad.relative_to(wurzel).parts
            self.assertIn(teile[0], ("fehlstellenscan", "holzbalkenscan"))
            self.assertNotIn(teile[0], gl.NIE_LESEN)
            self.assertNotEqual(pfad, HIER)  # nie der ganze Agent-Ordner (claude_lauf lehnt das ab)
            self.assertNotEqual(pfad, HIER / "data")  # data/gruppe/mails hält Mails aus Jans Postfach
            self.assertFalse(str(pfad.relative_to(HIER)).startswith("data/gruppe/mails")
                             if pfad.is_relative_to(HIER) else False)


class TestText(unittest.TestCase):
    def test_teilen(self):
        text = ("Absatz eins. " * 30 + "\n\n") * 5
        stuecke = gl.teilen(text, 500)
        self.assertTrue(all(len(s) <= 500 for s in stuecke))
        self.assertEqual("".join(stuecke).replace(" ", "").replace("\n", ""),
                         text.replace(" ", "").replace("\n", ""))
        self.assertEqual(gl.teilen("x" * 1200, 500), ["x" * 500, "x" * 500, "x" * 200])
        self.assertEqual(gl.teilen(""), ["(leer)"])

    def test_ohne_markdown(self):
        self.assertEqual(gl.ohne_markdown("## Kamera\n**Zeilenkamera** mit `66 kHz`"),
                         "Kamera\nZeilenkamera mit 66 kHz")

    def test_mailauftrag_erkennen(self):
        self.assertEqual(gl.mailauftrag_aus('{"mail_auftrag": "Jan an Böhme:  Termin  Dienstag"}'),
                         "Jan an Böhme: Termin Dienstag")
        self.assertEqual(gl.mailauftrag_aus('```json\n{"mail_auftrag": "x an y"}\n```'), "x an y")
        for kein in ("Die Kamera ist eine Zeilenkamera.", '{"mail_auftrag": ""}', '{"anderes": 1}', "{kaputt}",
                     'Text {"mail_auftrag": "x"}'):
            self.assertIsNone(gl.mailauftrag_aus(kein), kein)

    def test_prompt_und_verlauf(self):
        a = gl.Anfrage(GRUPPE, 5, HENRI, "Henri", "Und die Belichtung?", zitat="Zeilenkamera")
        verlauf = [{"zeit": "2026-11-19T10:00:00", "name": "Henri", "frage": "Kamera?", "antwort": "Zeile"}]
        p = gl.prompt_frage(a, verlauf, ["/x/foto.jpg"], datetime(2026, 11, 19, 12, 0))
        for teil in ("Henri: Kamera?", "Rüdiger: Zeile", "«Zeilenkamera»", "/x/foto.jpg", "«Und die Belichtung?»"):
            self.assertIn(teil, p)
        self.assertIn("(noch kein Verlauf)", gl.verlauf_text([]))
        self.assertIn("mail_auftrag", gl.ROLLE)
        self.assertIn("{ordner}", gl.ROLLE)
        gl.ROLLE.format(ordner="x")  # keine offenen Klammern

    def test_mail_text_und_titel(self):
        t = gl.mail_text("an Prof. Böhme wegen Termin", "Henri", [])
        self.assertIn("als Jan", t)
        self.assertIn("Henri", t)
        self.assertEqual(gl.entwurf_titel({"betreff": "Termin"}, "Henri"), "Mail aus der Projektgruppe (Henri): Termin")

    def test_entwurf_wie_in_der_zentrale(self):
        from telegram import logik as tl
        e = {"id": "20261119-140000-fehlstellenscan-abc123", "agent": "fehlstellenscan", "typ": "mail", "titel": "x",
             "inhalt": "x", "daten": {"an": ["boehme@hnee.de"], "cc": [], "betreff": "Termin",
                                      "text": "Hallo, passt Dienstag?", "begruendung": "b", "pruefen": "Uhrzeit"}}
        teile = gl.entwurf_fuer_gruppe(e)
        self.assertEqual(teile[0], tl.entwurf_als_text(e)[0] + "\n\n<i>" + gl.ENTWURF_HINWEIS + "</i>")
        self.assertIn("Hallo, passt Dienstag?", teile[0])

    def test_knoepfe_und_knopf_lesen(self):
        fid = "20261119-140000-fehlstellenscan-abc123"
        k = gl.entwurf_knoepfe(fid)["inline_keyboard"][0]
        self.assertEqual([b["text"] for b in k], [gl.FREIGEBEN, gl.ABLEHNEN])
        self.assertEqual(gl.knopf_lesen(k[0]["callback_data"]), ("freigegeben", fid))
        self.assertEqual(gl.knopf_lesen(k[1]["callback_data"]), ("abgelehnt", fid))
        self.assertTrue(all(len(b["callback_data"].encode()) <= 64 for b in k))  # Telegram-Grenze
        for falsch in ("", "f:", "x:" + fid, "f:../etwas", "c:" + fid):
            self.assertIsNone(gl.knopf_lesen(falsch))

    def test_freigeben_nur_jan_in_der_gruppe(self):
        z = gl.Zugang(-100, frozenset({1, 2}), 99, "rbot")
        klick = lambda von, chat=-100: {"from": {"id": von}, "message": {"chat": {"id": chat}}}  # noqa: E731
        self.assertTrue(gl.freigabe_erlaubt(klick(1), z, 1))
        self.assertFalse(gl.freigabe_erlaubt(klick(2), z, 1))          # freigeschaltet, aber nicht Jan
        self.assertFalse(gl.freigabe_erlaubt(klick(1, chat=555), z, 1))  # anderer Chat
        self.assertFalse(gl.freigabe_erlaubt(klick(1), z, None))         # ohne GRUPPE_JAN_ID niemand

    def test_entwurf_zu_antwort(self):
        entwuerfe = {"A": {"nachrichten": [10, 11]}, "B": {"nachrichten": [20]}}
        self.assertEqual(gl.entwurf_zu(entwuerfe, 11), "A")
        self.assertEqual(gl.entwurf_zu(entwuerfe, 20), "B")
        self.assertIsNone(gl.entwurf_zu(entwuerfe, 30))
        self.assertIsNone(gl.entwurf_zu(entwuerfe, None))
        self.assertIn("Henri", gl.aenderung_kommentar("Henri", "lieber Mittwoch"))

    def test_ergebnis_text(self):
        d = {"an": ["boehme@hnee.de"], "betreff": "Termin"}
        self.assertIn("ist raus", gl.ergebnis_text({"daten": d, "ausgefuehrt": "x", "erfolgreich": True}))
        self.assertIn("ging nicht raus", gl.ergebnis_text({"daten": d, "ausgefuehrt": "x", "erfolgreich": False}))
        self.assertIn("nicht freigegeben", gl.ergebnis_text({"daten": d, "status": "abgelehnt"}))
        self.assertIn("abgelaufen", gl.ergebnis_text({"daten": d, "status": "abgelaufen"}))
        self.assertIn("überarbeiten", gl.ergebnis_text({"daten": d, "status": "aendern"}))
        self.assertIsNone(gl.ergebnis_text({"daten": d, "status": "freigegeben"}))  # wartet auf Ausführung
        self.assertIsNone(gl.ergebnis_text({"daten": d, "status": "offen"}))


class TestGeruestGruppe(unittest.TestCase):
    def test_kein_bash_und_kein_torch(self):
        quelle = (HIER / "gruppe.py").read_text()
        for verboten in ("import torch", "import ultralytics", "subprocess", '"Bash"'):
            self.assertNotIn(verboten, quelle)
        self.assertIn("ohne_projekt=True", quelle)  # nie im Repo, also ohne CLAUDE.md
        self.assertIn("werkzeuge=[]", quelle)  # Mail-Läufe ohne Netz


if __name__ == "__main__":
    unittest.main()
