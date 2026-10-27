import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentkit import ausfall


class TestAusfall(unittest.TestCase):
    def setUp(self):
        self.stand = Path(tempfile.mkdtemp()) / "ausfall" / "stand.json"
        self.env = {"TELEGRAM_BOT_TOKEN": "123:geheim", "TELEGRAM_CHAT_ID": "42"}
        befehl = mock.patch.object(ausfall, "_befehl", side_effect=lambda *a: "oom-kill" if a[0] == "systemctl"
                                   else "Zeile 1\nFehler mit 123:geheim")
        befehl.start()
        self.addCleanup(befehl.stop)

    def test_agent_aus_unit(self):
        self.assertEqual(ausfall.agent_aus_unit("uni-transkript.service"), "uni")
        self.assertEqual(ausfall.agent_aus_unit("uni.service"), "uni")
        self.assertEqual(ausfall.agent_aus_unit("agentenzentrale.service"), "agentenzentrale")
        self.assertEqual(ausfall.agent_aus_unit("Komisch_1.service"), "ausfall")

    def test_text_in_worten(self):
        self.assertEqual(ausfall.text("uni-transkript.service", "oom-kill"),
                         "Uni (transkript) ist ausgefallen: zu wenig Arbeitsspeicher.\n"
                         "Bitte sieh am PC nach. Zu diesem Teil melde ich mich frühestens in 6 Stunden wieder.")
        self.assertIn("ausgefallen: aus unbekanntem Grund.", ausfall.text("uni.service", "komisch"))
        self.assertIn("ausgefallen: aus unbekanntem Grund.", ausfall.text("uni.service", ""))

    def test_senden_und_sperre(self):
        gesendet = []
        senden = lambda token, chat, text: gesendet.append((token, chat, text))  # noqa: E731
        self.assertEqual(ausfall.melden("uni.service", 1000.0, self.stand, senden, self.env), "telegram")
        token, chat, text = gesendet[0]
        self.assertEqual((token, chat), ("123:geheim", "42"))
        self.assertTrue(text.startswith("<b>Zentrale</b> · Störung\nUni ist ausgefallen: zu wenig Arbeitsspeicher."))
        self.assertNotIn("geheim", text)  # keine Journal-Zeilen mehr
        # innerhalb der Sperre nichts, andere Unit schon, nach der Sperre wieder
        self.assertEqual(ausfall.melden("uni.service", 1000.0 + 3600, self.stand, senden, self.env), "gesperrt")
        self.assertEqual(ausfall.melden("uni-lernen.service", 1000.0 + 3600, self.stand, senden, self.env),
                         "telegram")
        self.assertEqual(ausfall.melden("uni.service", 1000.0 + ausfall.SPERRE_S, self.stand, senden, self.env),
                         "telegram")
        self.assertEqual(len(gesendet), 3)

    def test_ersatzweg_warteschlange(self):
        def kaputt(*_):
            raise OSError("kein Netz")
        with mock.patch.object(ausfall.meldungen, "melden") as melden:
            self.assertEqual(ausfall.melden("uni-transkript.service", 1000.0, self.stand, kaputt, self.env),
                             "warteschlange")
        agent, text = melden.call_args.args
        self.assertEqual(agent, "uni")
        self.assertIn("Uni (transkript) ist ausgefallen", text)
        self.assertNotIn("<b>", text)  # die Zentrale setzt den Absender selbst
        self.assertEqual(ausfall.melden("uni-transkript.service", 1001.0, self.stand, kaputt, self.env), "gesperrt")

    def test_kaputter_stand(self):
        self.stand.parent.mkdir(parents=True)
        self.stand.write_text("{kaputt")
        self.assertEqual(ausfall.melden("uni.service", 1000.0, self.stand, lambda *a: None, self.env), "telegram")
