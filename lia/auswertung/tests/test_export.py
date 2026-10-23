import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

import export


def zip_bauen(pfad: Path, dateien: dict[str, str]) -> Path:
    with zipfile.ZipFile(pfad, "w") as z:
        for name, inhalt in dateien.items():
            z.writestr(name, inhalt)
    return pfad


class Entpacken(unittest.TestCase):
    def test_entpackt_mit_rechten(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            z = zip_bauen(t / "e.zip", {"conversations.json": "[]", "unter/users.json": "{}"})
            dateien = export.entpacken(z, t / "data" / "export")
            self.assertEqual(len(dateien), 2)
            for d in dateien:
                self.assertEqual(stat.S_IMODE(d.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE((t / "data" / "export" / "unter").stat().st_mode), 0o700)
            self.assertEqual((t / "data" / "export" / "unter" / "users.json").read_text(), "{}")

    def test_lehnt_pfad_nach_oben_ab_und_schreibt_nichts(self):
        for boese in ["../x.json", "/etc/x", "a/../../x", "a\\..\\x"]:
            with self.subTest(boese), tempfile.TemporaryDirectory() as t:
                t = Path(t)
                z = zip_bauen(t / "e.zip", {"gut.json": "[]", boese: "x"})
                with self.assertRaises(export.ExportFehler):
                    export.entpacken(z, t / "ziel")
                self.assertFalse((t / "ziel").exists())

    def test_lehnt_symlink_ab(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            with zipfile.ZipFile(t / "e.zip", "w") as z:
                info = zipfile.ZipInfo("link")
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, "/etc/passwd")
            with self.assertRaises(export.ExportFehler):
                export.entpacken(t / "e.zip", t / "ziel")


GESPRAECHE = [
    {"uuid": "g1", "name": "Arbeitsblatt Kant", "chat_messages": [
        {"uuid": "m1", "sender": "human", "text": "geheim", "parent_message_uuid": "root"},
        {"uuid": "m2", "sender": "assistant", "text": "a", "parent_message_uuid": "m1"},
        {"uuid": "m3", "sender": "assistant", "text": "b", "parent_message_uuid": "m1"},
        {"uuid": "m4", "sender": "human", "text": "c", "parent_message_uuid": "m3"},
        {"uuid": "m5", "sender": "human", "text": "d", "parent_message_uuid": "m3"},
    ]},
    {"uuid": "g2", "name": None, "chat_messages": []},
]


class Struktur(unittest.TestCase):
    def test_pfade_und_typen_ohne_inhalt(self):
        s = export.struktur(GESPRAECHE)
        self.assertEqual(s["."]["liste"], 1)
        self.assertEqual(s["[].name"]["text"], 1)
        self.assertEqual(s["[].name"]["null"], 1)
        self.assertEqual(s["[].chat_messages[].sender"]["text"], 5)
        self.assertNotIn("geheim", repr(s))

    def test_verzweigungen(self):
        v = export.verzweigungen(GESPRAECHE)
        self.assertEqual(v["nachrichten_mit_vorgaenger"], 5)
        self.assertEqual(v["stellen_nach_absender"], {"assistant": 1, "human": 1})

    def test_verzweigungen_ohne_feld(self):
        v = export.verzweigungen([{"chat_messages": [{"sender": "human"}]}])
        self.assertEqual(v, {"nachrichten_mit_vorgaenger": 0, "stellen_nach_absender": {}})

    def test_bericht_ohne_inhalte(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / "conversations.json").write_text(json.dumps(GESPRAECHE), encoding="utf-8")
            (t / "kaputt.json").write_text("{", encoding="utf-8")
            (t / "bild.png").write_bytes(b"123")
            b = export.bericht(t)
            self.assertIn("## conversations.json: 2 Einträge", b)
            self.assertIn("Verzweigungen:", b)
            self.assertIn("## kaputt.json: nicht lesbar", b)
            self.assertIn("## bild.png: keine JSON-Datei, 3 Bytes", b)
            self.assertNotIn("geheim", b)
            self.assertNotIn("Arbeitsblatt Kant", b)
