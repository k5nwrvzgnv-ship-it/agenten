import asyncio
import logging
import unittest

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import sprachpruefung as sp
from agentkit import sprache


class SprachpruefungTest(unittest.TestCase):
    def test_befunde_aus_text_und_knoepfen(self):
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("uni", callback_data="z:uni")]])
        b = sp.befunde("sendMessage", {"text": "Details im Log.", "reply_markup": markup}, sprache.JAN)
        self.assertIn("glossar: Log (stattdessen Lia: nichts, Jan: „Einzelheiten am PC“)", b)
        self.assertTrue(any(x.startswith("knopf glossar: Agentenname klein") for x in b))
        self.assertEqual(sp.befunde("getUpdates", {"offset": 1}, sprache.JAN), [])
        self.assertTrue(sp.befunde("sendDocument", {"caption": "Kontingent leer"}, sprache.LIA))
        knoepfe = {"inline_keyboard": [[{"text": "Passt", "callback_data": "x"}]]}
        self.assertEqual(sp.beschriftungen(knoepfe), ["Passt"])

    def test_absender(self):
        self.assertEqual(sp.absender("<b>Uni</b>\nFertig."), "Uni")
        self.assertEqual(sp.absender("Hallo Lia!"), "-")

    def test_warnt_ohne_inhalt_und_sendet_trotzdem(self):
        gesendet = []

        async def senden(endpunkt, daten):
            gesendet.append(endpunkt)
            return True

        async def lauf(text):
            pruefung = sp.Sprachpruefung(sprache.LIA, logging.getLogger("test_sprache"))
            return await pruefung.process_request(senden, ("sendMessage", {"text": text}), {}, "sendMessage",
                                                  {"text": text}, None)

        with self.assertLogs("test_sprache", "WARNING") as log:
            self.assertTrue(asyncio.run(lauf("Geheim: das Kontingent ist leer.")))
        self.assertEqual(gesendet, ["sendMessage"])
        self.assertIn("glossar: Kontingent", log.output[0])
        self.assertNotIn("Geheim", log.output[0])

    def test_ausnahmen_gelten_nur_im_block(self):
        daten = {"text": "cd ~/agenten/uni && claude --resume 1c039156-f7b0"}
        self.assertTrue(sp.befunde("sendMessage", daten, sprache.JAN))
        with sp.ausnahmen("pfad", "bezeichner", "id", "glossar"):
            self.assertEqual(sp.befunde("sendMessage", daten, sprache.JAN, sp._AUSNAHMEN.get()), [])
        self.assertEqual(sp._AUSNAHMEN.get(), ())

    def test_fehler_der_pruefung_haelt_nichts_auf(self):
        async def senden(*_):
            return "ok"

        pruefung = sp.Sprachpruefung(sprache.JAN, logging.getLogger("test_sprache"))
        with self.assertLogs("test_sprache", "ERROR"):
            ergebnis = asyncio.run(pruefung.process_request(senden, (), {}, "sendMessage", {"text": 42}, None))
        self.assertEqual(ergebnis, "ok")


if __name__ == "__main__":
    unittest.main()
