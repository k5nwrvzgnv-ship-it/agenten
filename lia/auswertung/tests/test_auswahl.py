import unittest

import auswahl


def chat(uuid, name, prompt, datum="2026-05-01T10:00:00Z"):
    return {"uuid": uuid, "name": name, "created_at": datum, "chat_messages": [
        {"sender": "human", "text": prompt}, {"sender": "assistant", "text": "Antwort zu Schule und Python"},
        {"sender": "human", "text": "danke"}]}


class Vorschlag(unittest.TestCase):
    def test_lia(self):
        self.assertEqual(auswahl.vorschlag(chat("1", "Arbeitsblatt Kant", "für Klasse 10")), "Lia")

    def test_jan(self):
        self.assertEqual(auswahl.vorschlag(chat("1", "systemd Dienst", "mein Python-Skript")), "Jan")

    def test_unklar_und_antworten_zaehlen_nicht(self):
        self.assertEqual(auswahl.vorschlag(chat("1", "Rezept Kürbissuppe", "für 4 Personen")), "unklar")

    def test_ohne_titel_und_nachrichten(self):
        self.assertEqual(auswahl.vorschlag({"name": None, "chat_messages": None}), "unklar")


class Chatliste(unittest.TestCase):
    def test_sortiert_ohne_prompts(self):
        tsv = auswahl.chatliste([chat("b", "Elternbrief\tWandertag", "geheimer Inhalt", "2026-06-01"),
                                 chat("a", "", "x", "2026-01-01")])
        zeilen = tsv.splitlines()
        self.assertEqual(zeilen[0].split("\t"), auswahl.SPALTEN)
        self.assertEqual(zeilen[1].split("\t"), ["1", "a", "2026-01-01", "(ohne Titel)", "2", "unklar"])
        self.assertEqual(zeilen[2].split("\t"), ["2", "b", "2026-06-01", "Elternbrief Wandertag", "2", "Lia"])
        self.assertNotIn("geheim", tsv)


class Bestaetigen(unittest.TestCase):
    KOPF = "\t".join(auswahl.SPALTEN)

    def test_nur_lia(self):
        tsv = f"{self.KOPF}\n1\ta\td\tt\t1\tLia\n2\tb\td\tt\t1\tjan\n"
        self.assertEqual(auswahl.bestaetigte_lia(tsv), {"a"})

    def test_unklar_bricht_ab(self):
        tsv = f"{self.KOPF}\n1\ta\td\tt\t1\tLia\n2\tb\td\tt\t1\tunklar\n"
        with self.assertRaisesRegex(ValueError, "Nr.*2"):
            auswahl.bestaetigte_lia(tsv)

    def test_falscher_kopf(self):
        with self.assertRaises(ValueError):
            auswahl.bestaetigte_lia("nr\twer\n")
