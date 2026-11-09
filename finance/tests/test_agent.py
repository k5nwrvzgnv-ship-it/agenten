"""Tests für agent.py mit agentkit (ohne Netz): Abfragen ausführen und ablegen."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ablauf
import abrufer
import agent
import quellen
from agentkit import abruf


class FalschesLaden:
    def __init__(self, inhalt=b"", content_type="application/json", fehler=None):
        self.inhalt, self.content_type, self.fehler, self.aufrufe = inhalt, content_type, fehler, []

    def __call__(self, url, **kw):
        self.aufrufe.append((url, kw))
        if self.fehler:
            raise abruf.AbrufFehler(self.fehler)
        return abruf.Ergebnis(self.inhalt, {"content_type": self.content_type}, aus_cache=False)


class TestAbrufen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.quellen = Path(self.tmp.name)
        patch = mock.patch.multiple(agent, QUELLEN=self.quellen, cfg={"COMTRADE_KEY": "geheim"}, logger=mock.DEFAULT)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_abfrage_wird_abgelegt_ohne_schluessel(self):
        roh = json.dumps({"count": 1, "data": [{"primaryValue": 123456789.0}]}).encode()
        laden = FalschesLaden(roh)
        qid = agent.abrufen({"art": "comtrade", "melder": 276, "jahr": 2024, "hs": "847950", "richtung": "X",
                             "beschreibung": "Export Industrieroboter"}, _laden=laden)
        self.assertTrue(quellen.ist_id(qid))
        meta = quellen.meta(self.quellen, qid)
        self.assertEqual(meta["art"], "comtrade")
        url, kw = laden.aufrufe[0]
        self.assertEqual(kw["header"], {"Ocp-Apim-Subscription-Key": "geheim"})
        self.assertTrue(kw["neu"])
        self.assertNotIn("geheim", json.dumps(meta) + url)

    def test_fehler_werden_zu_texten_fuer_claude(self):
        abfrage = {"art": "jobsuche", "was": "Robotik", "beschreibung": "Stellen"}
        with self.assertRaisesRegex(ablauf.WebFehler, "HTTP 500"):
            agent.abrufen(abfrage, _laden=FalschesLaden(fehler="HTTP 500"))
        with self.assertRaises(abrufer.AbfrageFehler):
            agent.abrufen(abfrage, _laden=FalschesLaden(b'{"x": 1}'))
        with self.assertRaisesRegex(abrufer.AbfrageFehler, "COMTRADE_KEY"):
            with mock.patch.object(agent, "cfg", {}):
                agent.abrufen({"art": "comtrade", "melder": 276, "jahr": 2024, "hs": "8479", "richtung": "M",
                               "beschreibung": "x"}, _laden=FalschesLaden())


if __name__ == "__main__":
    unittest.main()
