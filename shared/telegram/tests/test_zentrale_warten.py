"""Auftragstext und nachkommende Datei: Telegram schickt sie bei einer Weiterleitung mit Kommentar getrennt."""

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from logik import Eingang, datei_gehoert_zum_auftrag

with (mock.patch("agentkit.config.lade_config", return_value={"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "1"}),
      mock.patch("agentkit.log.hole_logger")):
    import zentrale


class Job:
    def __init__(self, ablauf):
        self.ablauf, self.entfernt = ablauf, False

    def schedule_removal(self):
        self.entfernt = True
        self.ablauf.jobs.remove(self)


class Ablauf(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.jobs, self.auftraege, self.bot = [], [], mock.AsyncMock()
        self.eingang = Eingang(Path(tmp.name))
        self.context = SimpleNamespace(bot=self.bot, chat_data={}, job_queue=SimpleNamespace(run_once=self.run_once))
        for name, neu in (("eingang", self.eingang), ("auftrag_anlegen", self.auftrag_anlegen),
                          ("panel_zeigen", mock.AsyncMock()), ("home", mock.Mock())):
            patcher = mock.patch.object(zentrale, name, neu)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_once(self, rueckruf, wartezeit, chat_id):
        self.assertEqual((rueckruf, wartezeit, chat_id), (zentrale.wartezeit_um, zentrale.AUFTRAG_WARTEN, zentrale.JAN))
        job = Job(self)
        self.jobs.append(job)
        return job

    async def auftrag_anlegen(self, bot, agent, modus, text, bestaetigen=True):
        self.auftraege.append({"agent": agent, "text": text, "bestaetigen": bestaetigen,
                               "dateien": [d.name for d in self.eingang.wartende()]})
        return True

    def uhr_laeuft_ab(self):
        self.assertEqual(len(self.jobs), 1)
        self.jobs.clear()
        asyncio.run(zentrale.wartezeit_um(self.context))

    def text_kommt(self, text="/uni schick das"):
        update = SimpleNamespace(message=SimpleNamespace(text=text, reply_text=mock.AsyncMock()))
        asyncio.run(zentrale.auftrag_befehl(update, self.context))

    def datei_kommt(self, name="a.pdf", caption=None, weitergeleitet=False, antwort=False, gruppe=None, kaputt=False):
        async def laden(pfad):
            if kaputt:
                raise OSError("Netz")
            # Während des Downloads darf der Auftrag nicht loslaufen
            self.assertEqual(self.jobs, [])
            Path(pfad).write_bytes(b"x")

        datei = mock.Mock(file_name=name, file_size=1)
        datei.get_file = mock.AsyncMock(return_value=mock.Mock(download_to_drive=laden))
        m = mock.Mock(document=datei, caption=caption, media_group_id=gruppe, reply_text=mock.AsyncMock(),
                      forward_origin=object() if weitergeleitet else None,
                      reply_to_message=object() if antwort else None)
        with mock.patch.object(zentrale, "beantworteter_auftrag", return_value=None), \
                mock.patch.object(zentrale, "antwort_weitergeben", mock.AsyncMock()) as weiter:
            asyncio.run(zentrale.datei_empfangen(SimpleNamespace(message=m), self.context))
        return m, weiter


class Weiterleitung(Ablauf):
    def test_text_allein_wartet_und_geht_dann_los(self):
        self.text_kommt()
        self.assertEqual(self.auftraege, [])
        self.uhr_laeuft_ab()
        self.assertEqual(self.auftraege, [{"agent": "uni", "text": "schick das", "bestaetigen": True, "dateien": []}])
        self.assertNotIn("wartender_auftrag", self.context.chat_data)

    def test_nachkommende_datei_geht_mit(self):
        self.text_kommt()
        self.datei_kommt(weitergeleitet=True)
        self.assertEqual(self.auftraege, [])
        self.uhr_laeuft_ab()
        self.assertEqual(self.auftraege[0]["dateien"], ["a.pdf"])

    def test_mehrere_dateien_und_album_gehen_mit(self):
        self.text_kommt()
        self.datei_kommt("a.pdf")
        self.datei_kommt("b.pdf", gruppe="g1")
        self.assertNotIn("alben", self.context.chat_data)
        self.uhr_laeuft_ab()
        self.assertEqual(self.auftraege[0]["dateien"], ["a.pdf", "b.pdf"])

    def test_bildunterschrift_des_originals_zaehlt_nicht(self):
        self.text_kommt()
        self.datei_kommt(caption="Vom Absender", weitergeleitet=True)
        self.uhr_laeuft_ab()
        self.assertEqual(self.auftraege[0]["text"], "schick das")
        self.assertEqual(self.auftraege[0]["dateien"], ["a.pdf"])

    def test_datei_nicht_geladen_auftrag_laeuft_trotzdem(self):
        self.text_kommt()
        m, _ = self.datei_kommt(kaputt=True)
        m.reply_text.assert_awaited_once_with(zentrale.DATEI_NICHT_GELADEN)
        self.uhr_laeuft_ab()
        self.assertEqual(self.auftraege[0]["dateien"], [])

    def test_zu_grosse_datei_haelt_die_uhr_nicht_an(self):
        self.text_kommt()
        job = self.jobs[0]
        datei = mock.Mock(file_name="g.pdf", file_size=zentrale.MAX_DATEI_BYTES + 1)
        m = mock.Mock(document=datei, reply_text=mock.AsyncMock())
        asyncio.run(zentrale.datei_empfangen(SimpleNamespace(message=m), self.context))
        self.assertFalse(job.entfernt)

    def test_zweiter_auftrag_schickt_den_ersten_los(self):
        self.text_kommt("/uni eins")
        self.text_kommt("/dokumente zwei")
        self.assertEqual([a["text"] for a in self.auftraege], ["eins"])
        self.uhr_laeuft_ab()
        self.assertEqual([a["text"] for a in self.auftraege], ["eins", "zwei"])

    def test_datei_mit_eigenem_befehl_ist_ein_eigener_auftrag(self):
        self.text_kommt("/uni eins")
        self.datei_kommt(caption="/dokumente zwei")
        self.assertEqual(self.auftraege, [{"agent": "uni", "text": "eins", "bestaetigen": True, "dateien": []},
                                          {"agent": "dokumente", "text": "zwei", "bestaetigen": True,
                                           "dateien": ["a.pdf"]}])
        self.assertEqual(self.jobs, [])

    def test_ohne_wartenden_auftrag_wie_bisher(self):
        self.datei_kommt()
        self.assertEqual(self.auftraege, [])
        self.assertEqual(self.jobs, [])
        self.assertIn("1 Datei liegt bereit", self.bot.send_message.await_args.args[1])

    def test_auftrag_aus_dem_menue(self):
        self.context.chat_data["panel_agent"] = ("uni", "erledigen")
        update = mock.Mock()
        update.message.text = "schick das"
        with mock.patch.object(zentrale, "beantworteter_auftrag", return_value=None), \
                mock.patch.object(zentrale, "beantwortete_meldung", return_value=None):
            asyncio.run(zentrale.text_ohne_befehl(update, self.context))
        self.datei_kommt(weitergeleitet=True)
        self.uhr_laeuft_ab()
        self.assertEqual(self.auftraege, [{"agent": "uni", "text": "schick das", "bestaetigen": False,
                                           "dateien": ["a.pdf"]}])
        zentrale.panel_zeigen.assert_awaited_once()


class Zuordnung(unittest.TestCase):
    def test_regel(self):
        self.assertTrue(datei_gehoert_zum_auftrag(None, False, False))
        self.assertTrue(datei_gehoert_zum_auftrag("  ", False, False))
        self.assertTrue(datei_gehoert_zum_auftrag("Original", True, False))
        self.assertFalse(datei_gehoert_zum_auftrag("/dokumente x", False, False))
        self.assertFalse(datei_gehoert_zum_auftrag(None, False, True))
        self.assertFalse(datei_gehoert_zum_auftrag(None, True, True))


if __name__ == "__main__":
    unittest.main()
