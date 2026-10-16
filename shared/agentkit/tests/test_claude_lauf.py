import copy
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from agentkit import claude_lauf, einstellungen, verbrauch

CFG = einstellungen.lade()

# Nachgebautes claude: schreibt seine Argumente in args.json und gibt stream-json aus.
FAKE = """#!/usr/bin/env python3
import json, os, sys, time
json.dump(sys.argv[1:], open("args.json", "w"))
modus = os.environ.get("FAKE_MODUS", "ok")
if modus == "langsam":
    time.sleep(5)
status = "rejected" if modus == "limit" else "allowed"
print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": status, "resetsAt": 4102444800,
    "unifiedWindows": {"five_hour": {"utilization": 0.2, "resetsAt": 4102444800},
                       "seven_day": {"utilization": 0.4, "resetsAt": 4102444800}}}}))
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "Fertig",
    "session_id": "sitzung-1", "num_turns": 3, "duration_ms": 1500, "total_cost_usd": 0.05,
    "usage": {"input_tokens": 10, "output_tokens": 20, "cache_creation_input_tokens": 100,
              "cache_read_input_tokens": 1000}, "permission_denials": []}))
"""


class TestClaudeLauf(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fake = self.tmp / "claude"
        self.fake.write_text(FAKE)
        self.fake.chmod(0o755)
        self.agent_dir = self.tmp / "uni"
        self.agent_dir.mkdir()
        (self.agent_dir / "STATUS.md").write_text("## Gelernte Regeln\n- 16.10.2026: Quellen mit Seite\n")
        self.protokoll = self.tmp / "v" / "laeufe.jsonl"
        self.slots = self.tmp / "plaetze"
        p = mock.patch.object(claude_lauf, "CLAUDE_BIN", str(self.fake))
        p.start()
        self.addCleanup(p.stop)
        os.environ.pop("FAKE_MODUS", None)

    def lauf(self, cfg=CFG, **kw):
        return claude_lauf.laufen("uni", self.agent_dir, "Prüfe Fristen", cfg=cfg,
                                  slot_dir=self.slots, protokoll=self.protokoll, **kw)

    def args(self):
        return json.loads((self.agent_dir / "args.json").read_text())

    def test_normaler_lauf(self):
        e = self.lauf(auftrag_id="a1")
        self.assertTrue(e.ok)
        self.assertEqual((e.text, e.sitzung, e.schritte, e.tokens), ("Fertig", "sitzung-1", 3, 1130))
        a = self.args()
        tools = a[a.index("--tools") + 1: a.index("--strict-mcp-config")]
        self.assertEqual(tools, einstellungen.werkzeuge(CFG, "uni"))
        self.assertNotIn("Bash", tools)
        self.assertEqual(a[a.index("--model") + 1], "sonnet")
        self.assertEqual(a[a.index("--permission-mode") + 1], "acceptEdits")
        self.assertIn("Read(**/.env)", a[a.index("--settings") + 1])
        system = a[a.index("--append-system-prompt") + 1]
        self.assertIn("nie selbst nach außen", system)
        self.assertIn("Quellen mit Seite", system)
        eintrag = json.loads(self.protokoll.read_text().splitlines()[-1])
        self.assertEqual((eintrag["agent"], eintrag["auftrag"], eintrag["tokens"]), ("uni", "a1", 1130))
        self.assertEqual(eintrag["auslastung"]["7d"], 0.4)

    def test_lernsitzung_und_fortsetzen(self):
        self.lauf(art="anspruchsvoll", lernsitzung=True)
        a = self.args()
        self.assertEqual(a[a.index("--model") + 1], "opus")
        self.assertIn("--session-id", a)
        self.lauf(sitzung_fortsetzen="abc")
        a = self.args()
        self.assertEqual(a[a.index("--resume") + 1], "abc")
        self.assertNotIn("--session-id", a)

    def test_limit_erreicht(self):
        os.environ["FAKE_MODUS"] = "limit"
        with self.assertRaises(claude_lauf.LimitErreicht):
            self.lauf()
        os.environ.pop("FAKE_MODUS")
        # danach wird gar nicht erst gestartet
        (self.agent_dir / "args.json").unlink()
        with self.assertRaises(claude_lauf.LimitErreicht):
            self.lauf()
        self.assertFalse((self.agent_dir / "args.json").exists())

    def test_stufen(self):
        verbrauch.protokollieren({"auslastung": {"status": "allowed", "5h": 0.6, "7d": 0.1,
                                                 "reset_5h": time.time() + 999, "reset_7d": time.time() + 999}},
                                 self.protokoll)
        os.environ["FAKE_MODUS"] = "ok"
        # Fake meldet danach 0.2/0.4 -> wieder normal; hier zählt der Stand VOR dem Lauf
        self.lauf()
        self.assertEqual(self.args()[self.args().index("--model") + 1], "haiku")
        verbrauch.protokollieren({"auslastung": {"status": "allowed", "5h": 0.85, "7d": 0.1,
                                                 "reset_5h": time.time() + 999, "reset_7d": time.time() + 999}},
                                 self.protokoll)
        with self.assertRaises(claude_lauf.Pausiert):
            self.lauf(zeitgesteuert=True)
        self.lauf()  # Jans Aufträge laufen weiter

    def test_zeitlimit(self):
        os.environ["FAKE_MODUS"] = "langsam"
        cfg = copy.deepcopy(CFG)
        cfg["lauf"]["max_minuten"] = 0.02
        with self.assertRaises(claude_lauf.Zeitueberschreitung):
            self.lauf(cfg=cfg)
        self.assertFalse(json.loads(self.protokoll.read_text().splitlines()[-1])["ok"])

    def test_sperren(self):
        with claude_lauf._sperre(self.agent_dir / "data" / "lauf.lock", RuntimeError()):
            with self.assertRaises(claude_lauf.LaeuftSchon):
                self.lauf()
        cfg = copy.deepcopy(CFG)
        cfg["lauf"]["warten_minuten"] = 0
        with claude_lauf._platz(2, 0, self.slots):
            with claude_lauf._platz(2, 0, self.slots):
                with self.assertRaises(claude_lauf.KeinPlatz):
                    self.lauf(cfg=cfg)
            self.lauf(cfg=cfg)  # ein Platz wieder frei


if __name__ == "__main__":
    unittest.main()
