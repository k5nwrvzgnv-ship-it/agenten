"""Verfall offener Entwürfe in der Zentrale (Untersuchung 11/2026, B5): Prüfrunde und später Klick.

Das ist der Weg, über den Mails nach außen gehen: Ein abgelaufener Entwurf darf durch keinen alten Knopf mehr
freigegeben werden, und Jan erfährt genau einmal davon.
"""

import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from agentkit import auftraege, freigabe, meldungen
from logik import Gemeldet

with (mock.patch("agentkit.config.lade_config", return_value={"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "1"}),
      mock.patch("agentkit.log.hole_logger")):
    import zentrale


class Verfall(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.bot = mock.AsyncMock()
        self.context = SimpleNamespace(bot=self.bot, chat_data={})
        self.gemeldet = Gemeldet(self.tmp / "gemeldet.json")
        self.starts = mock.AsyncMock()
        for ziel, name, neu in ((freigabe, "BASIS", self.tmp / "freigabe"), (auftraege, "BASIS", self.tmp / "auftraege"),
                                (meldungen, "BASIS", self.tmp / "meldungen"), (freigabe, "_ereignis", mock.Mock()),
                                (zentrale, "gemeldet", self.gemeldet), (zentrale, "agent_starten", self.starts),
                                (zentrale, "aktuelle_stufe", lambda: (None, "normal"))):
            patcher = mock.patch.object(ziel, name, neu)
            patcher.start()
            self.addCleanup(patcher.stop)

    def entwurf(self, tage_alt: float, titel="Mail an Prof") -> str:
        eid = freigabe.neuer_entwurf("uni", titel, "Hallo", typ="mail", daten={"an": "p@example.org"})
        pfad = self.tmp / "freigabe" / "offen" / f"{eid}.json"
        daten = json.loads(pfad.read_text())
        daten["erstellt"] = (datetime.now().astimezone() - timedelta(days=tage_alt)).isoformat(timespec="seconds")
        pfad.write_text(json.dumps(daten))
        return eid

    def runde(self, uhr=10):
        echt = datetime

        class Uhr(datetime):
            @classmethod
            def now(cls, tz=None):
                return echt.now(tz).replace(hour=uhr)
        with mock.patch.object(zentrale, "datetime", Uhr):
            asyncio.run(zentrale.pruefen(self.context))

    def texte(self) -> list[str]:
        return [c.args[1] for c in self.bot.send_message.call_args_list]

    def klick(self, daten: str):
        q = mock.AsyncMock()
        q.data = daten
        update = SimpleNamespace(callback_query=q, effective_chat=SimpleNamespace(id=zentrale.JAN))
        asyncio.run(zentrale.knopf(update, self.context))
        return q

    def test_alter_entwurf_laeuft_ab_und_wird_einmal_gemeldet(self):
        alt = self.entwurf(8, "Mail: alte Rückfrage")
        self.gemeldet.angezeigt[alt] = "abc"  # war schon gezeigt
        self.runde()
        self.assertEqual(freigabe.offene(), [])
        texte = self.texte()
        self.assertEqual(len(texte), 1)
        self.assertIn("abgelaufen", texte[0])
        self.assertIn("Mail: alte Rückfrage", texte[0])
        self.assertNotIn("Hallo", texte[0])  # kein Inhalt, nur der Titel
        self.assertNotIn(alt, self.gemeldet.angezeigt)
        self.runde()
        self.assertEqual(len(self.texte()), 1)  # nicht noch einmal
        self.starts.assert_not_called()

    def test_spaeter_klick_gibt_nichts_frei(self):
        alt = self.entwurf(8)
        gesehen = freigabe.offene()[0]["fingerabdruck"]
        self.gemeldet.angezeigt[alt] = gesehen  # der alte Knopf mit passendem Fingerabdruck
        self.runde()
        q = self.klick(f"f:{alt}")
        self.assertIn("abgelaufen", q.message.reply_text.call_args.args[0])
        self.assertEqual(freigabe.zur_ausfuehrung(), [])
        self.assertEqual(freigabe.erledigte()[0]["status"], "abgelaufen")
        self.starts.assert_not_called()  # kein Agent wird gestartet

    def test_frischer_entwurf_wird_gezeigt_und_laesst_sich_freigeben(self):
        eid = self.entwurf(0)
        self.runde()
        self.assertEqual(freigabe.abgelaufene(), [])
        self.assertIn(eid, self.gemeldet.angezeigt)
        self.klick(f"f:{eid}")
        self.assertEqual([e["id"] for e in freigabe.zur_ausfuehrung()], [eid])
        self.starts.assert_awaited_once_with("uni")

    def test_meldung_kommt_nach_netzfehler_nach(self):
        self.entwurf(8)
        self.bot.send_message.side_effect = RuntimeError("Netz weg")
        with self.assertRaises(RuntimeError):
            self.runde()
        self.assertEqual(len(freigabe.abgelaufene()), 1)  # abgelaufen ist er trotzdem
        self.bot.send_message.side_effect = None
        self.runde()
        self.assertIn("abgelaufen", self.texte()[-1])

    def test_erinnerung_einmal_am_tag_mit_knopf(self):
        self.entwurf(3)  # die Test-Uhr verstellt nur die Stunde, darum unten 2 oder 3 Tage
        self.runde(uhr=3)
        self.assertEqual(len(self.texte()), 1)  # nur der Entwurf selbst, nachts keine Erinnerung
        self.runde(uhr=10)
        texte = self.texte()
        self.assertEqual(len(texte), 2)
        self.assertRegex(texte[1], "wartet seit [23] Tagen auf deine Entscheidung")
        knopf = self.bot.send_message.call_args.kwargs["reply_markup"].inline_keyboard[0][0]
        self.assertEqual(knopf.callback_data, "u:entwuerfe")
        self.runde(uhr=15)
        self.assertEqual(len(self.texte()), 2)
        self.assertEqual(Gemeldet(self.tmp / "gemeldet.json").erinnert, datetime.now().date().isoformat())

    def test_entwurf_aus_dem_menue_einzeln_zeigen(self):
        eid, anderer = self.entwurf(1, "Mail: eins"), self.entwurf(1, "Mail: zwei")
        with mock.patch.object(zentrale, "panel_zeigen", mock.AsyncMock()), mock.patch.object(zentrale, "home", mock.Mock()):
            self.klick(f"u:e:{eid}")
        self.assertIn(eid, self.gemeldet.angezeigt)
        self.assertNotIn(anderer, self.gemeldet.angezeigt)
        self.assertEqual(len(self.texte()), 1)
        self.assertIn("Mail: eins", self.texte()[0])


if __name__ == "__main__":
    unittest.main()
