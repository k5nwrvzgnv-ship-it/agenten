import unittest

import anonym

NAMEN = [
    {"name": "Lia Laura Musterfrau", "art": "lehrkraft"},
    {"name": "Musterfrau", "gleich_wie": "Lia Laura Musterfrau"},
    {"name": "Lia", "gleich_wie": "Lia Laura Musterfrau", "nur_gross": True},
    {"name": "Yasmin", "art": "schueler"},
    {"name": "Noor Aldeen", "art": "schueler"},
    {"name": "Noor", "gleich_wie": "Noor Aldeen"},
    {"name": "Said", "art": "schueler", "nur_gross": True},
    {"name": "Frau Beispiel", "art": "person"},
    {"name": "Beispiel-Gymnasium", "art": "schule"},
]


class Ersetzen(unittest.TestCase):
    def setUp(self):
        self.e = anonym.Ersetzer(NAMEN)

    def test_platzhalter(self):
        self.assertEqual(self.e.zuordnung["Yasmin"], "[Schüler 1]")
        self.assertEqual(self.e.zuordnung["Noor"], "[Schüler 2]")
        self.assertEqual(self.e.zuordnung["Said"], "[Schüler 3]")
        self.assertEqual(self.e.zuordnung["Beispiel-Gymnasium"], "[Schule A]")
        self.assertEqual(self.e.zuordnung["Lia"], "[Lehrkraft]")

    def test_namen_klein_genitiv_und_laengster_zuerst(self):
        self.assertEqual(self.e.text("yasmin und Noor Aldeen, Yasmins Bruder"),
                         "[Schüler 1] und [Schüler 2], [Schüler 1]s Bruder")
        self.assertEqual(self.e.text("Lia Laura Musterfrau schreibt"), "[Lehrkraft] schreibt")

    def test_nur_gross_und_wortgrenzen(self):
        self.assertEqual(self.e.text("He said: Said fehlt."), "He said: [Schüler 3] fehlt.")
        self.assertEqual(self.e.text("Liane und Liaison, Yasminblüte"), "Liane und Liaison, Yasminblüte")
        self.assertEqual(self.e.text("lia"), "lia")

    def test_grossbuchstaben_und_unterstrich(self):
        self.assertEqual(self.e.text("NOOR ALDEEN und YASMIN"), "[Schüler 2] und [Schüler 1]")
        self.assertEqual(self.e.text("Bewertung_NOOR_ALDEEN.docx, Bewertung_Yasmin.docx"),
                         "Bewertung_[Schüler 2].docx, Bewertung_[Schüler 1].docx")
        self.assertEqual(self.e.text("LIA"), "LIA")

    def test_bindestrich_ist_grenze(self):
        self.assertEqual(self.e.text("yasmin-Text, Anti-Yasmin"), "[Schüler 1]-Text, Anti-[Schüler 1]")

    def test_schule_mit_bindestrich(self):
        self.assertEqual(self.e.text("am Beispiel-Gymnasium"), "am [Schule A]")

    def test_muster(self):
        t = self.e.text("Mail an a.b-c@gmx.de, Tel. 030 90227 6208, Akazienstraße 23, 10823 Berlin, "
                        "Personalnummer 4175359, ISBN 9780573113123, BSN 02K02, Jahr 2026, 11.2")
        self.assertEqual(t, "Mail an [E-Mail], Tel. [Telefon], [Adresse], [PLZ Ort], "
                            "Personalnummer [Nummer], ISBN 9780573113123, BSN [Schulnummer], Jahr 2026, 11.2")
        self.assertEqual(self.e.text("Flottenstr. 28"), "[Adresse]")

    def test_treffer_gezaehlt(self):
        self.e.text("Yasmin, yasmin, Noor")
        self.assertEqual(self.e.treffer, {"Yasmin": 2, "Noor": 1})

    def test_alles_laesst_ids(self):
        d = {"uuid": "Yasmin-1", "titel": "Yasmin", "nachrichten": [{"text": "Yasmin", "zeit": "x"}]}
        self.assertEqual(self.e.alles(d), {"uuid": "Yasmin-1", "titel": "[Schüler 1]",
                                           "nachrichten": [{"text": "[Schüler 1]", "zeit": "x"}]})

    def test_gleich_wie_unbekannt(self):
        with self.assertRaises(ValueError):
            anonym.Ersetzer([{"name": "X", "gleich_wie": "Y"}])

    def test_reste(self):
        chats = [{"titel": "yasmin", "nachrichten": [{"text": "He said hi"}]}]
        self.assertEqual(anonym.reste(chats, NAMEN), {"Yasmin": 1})


class Aufbereiten(unittest.TestCase):
    def test_nur_benoetigtes(self):
        chats = [{"uuid": "c", "name": "T", "created_at": "2026-09-01T10:00:00Z", "summary": "S",
                  "chat_messages": [
                      {"uuid": "m1", "parent_message_uuid": "0", "sender": "human", "created_at": "z",
                       "text": "", "content": [{"type": "text", "text": "Frage"}, {"type": "tool_result"}],
                       "attachments": [{"file_name": "a.txt", "extracted_content": "Inhalt"}],
                       "files": [{"file_name": "b.docx", "file_uuid": "u"}]}]}]
        a = anonym.aufbereiten(chats)
        self.assertEqual(a, [{"uuid": "c", "titel": "T", "datum": "2026-09-01", "zusammenfassung": "S",
                              "nachrichten": [{"uuid": "m1", "vorgaenger": "0", "absender": "lia", "zeit": "z",
                                               "text": "Frage", "anhaenge": [{"name": "a.txt", "text": "Inhalt"}],
                                               "dateien": ["b.docx"]}]}])
