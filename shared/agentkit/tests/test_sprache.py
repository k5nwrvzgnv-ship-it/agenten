import unittest

from agentkit import sprache as s

# Je Regel ein echtes Beispiel aus docs/sprache/inventur.md (gekürzt)
BEISPIELE = {
    "Agent": (s.LIA, "Dein Agent arbeitet daran."),
    "der Agent": (s.JAN, "Freigegeben. Der Agent führt es jetzt aus."),
    "Agentenname klein": (s.JAN, "Lia zu recherche: passt nicht"),
    "Dienst": (s.LIA, "Der Dienst ist gerade aus."),
    "Auftrag": (s.LIA, "Dein Auftrag ist angekommen."),
    "Kontingent": (s.LIA, "Gerade ist das gemeinsame Kontingent aufgebraucht."),
    "Limit": (s.JAN, "Limit erreicht, alles wartet."),
    "Stufe": (s.JAN, "Stufe: normal"),
    "5h/7d": (s.JAN, "Auslastung 5h 6 %  7d 1 %"),
    "Reset": (s.JAN, "7 Tage: 1 % (Reset Mo 10:00)"),
    "Lauf": (s.JAN, "Kosten 0.01 USD in 1 Läufen."),
    "Tokens": (s.JAN, "uni: 3 Läufe, 120k Tokens"),
    "Nachbesserung": (s.LIA, "Danke. Die Nachbesserung läuft."),
    "Regel (dauerhaft)": (s.JAN, "Art: Regel (dauerhaft), nur für Recherche"),
    "Programmänderung": (s.LIA, "Das braucht eine Programmänderung."),
    "fehlgeschlagen": (s.JAN, "Schritt fehlgeschlagen."),
    "Log": (s.JAN, "Kein Grund angegeben, Details im Log."),
    "Commit": (s.JAN, "Die Änderung ist noch nicht committet."),
    "Version": (s.JAN, "Runde 1 fertig, Version b9090a0."),
    "USD": (s.LIA, "Das hat 2 USD gekostet."),
    "OCR": (s.JAN, "S. 31 Zweckstrafe (2 von 2, OCR 0.85)"),
    "(en)": (s.JAN, "2 Datei(en) liegen bereit."),
    "Bot": (s.JAN, "Das lässt Telegram für Bots nicht zu."),
    "MB": (s.LIA, "Die Datei ist größer als 20 MB."),
    "läuft noch nicht": (s.JAN, "Dokumente läuft noch nicht. Der Auftrag wartet."),
    "Zentrale": (s.LIA, "Zentrale\n\nHallo Lia!"),
    "Sitzung": (s.LIA, "Diese Sitzung liegt am PC."),
    "ID": (s.JAN, "Fallsuche 20261027-115658 abgebrochen"),
    "Hash": (s.JAN, "Stand b49bbb2"),
    "Pfad": (s.JAN, "Datei: /home/agent/agenten/lia/recherche/data/web/x/Recherche"),
    "Dateiname": (s.JAN, "Volles Protokoll: protokolle/20261016.md"),
    "Betrag": (s.JAN, "Kosten 2,10 Euro"),
    "Modellname": (s.JAN, "kleineres Modell (Haiku) für Routine"),
    "Fehlertext": (s.JAN, "TimeoutError: [Errno 110] Connection timed out"),
    "Bezeichner": (s.JAN, "Schritt post_pruefen hat nicht geklappt"),
}

UNVERDAECHTIG = [
    "Hier ist dein Arbeitsblatt.",
    "Der Arbeitsauftrag steht oben, für Jahrgangsstufe 8.",
    "Einstiegsübung CAD/CAM: Abgabe Montag um 22 Uhr.",
    "Im Laufe der Woche ist es auf dem Campus kälter.",
    "Schnell einreichen: https://lms.hnee.de/mod/assign/view.php?id=158900&action=view",
    "Mail von moodle-forum@hnee.de: Überfällig.",
    "Uni ist dran. Ich melde mich mit dem Ergebnis.",
    "Die Rechenzeit ist aufgebraucht. Weiter ab 14 Uhr.",
    "Feedback: Danke, ab jetzt gilt: Fälle zuerst aus der Lebenswelt.",
    "Kant, AA VI, S. 331 „niemals bloß als Mittel“",
]


class JargonTest(unittest.TestCase):
    def test_jede_regel_hat_ein_beispiel_und_trifft(self):
        self.assertEqual(set(BEISPIELE), {r.wort for r in s.REGELN})
        for wort, (fuer, text) in BEISPIELE.items():
            self.assertIn(wort, [t.wort for t in s.jargon(text, fuer)], text)

    def test_alltagssaetze_ohne_treffer(self):
        for text in UNVERDAECHTIG:
            for fuer in (s.LIA, s.JAN):
                self.assertEqual(s.jargon(text, fuer), [], f"{fuer}: {text}")

    def test_manche_woerter_nur_fuer_lia_tabu(self):
        self.assertEqual(s.jargon("Dein Auftrag ist angekommen, die Sitzung liegt am PC.", s.JAN), [])
        self.assertEqual({t.wort for t in s.jargon("Dein Auftrag ist angekommen.", s.LIA)}, {"Auftrag"})

    def test_ausnahmen_und_html(self):
        self.assertEqual(s.jargon("Heute: 0,23 USD", s.JAN, ausnahmen=("betrag", "glossar")), [])
        self.assertEqual(s.jargon("<b>Uni</b>\nFertig &amp; geprüft.", s.JAN), [])
        self.assertTrue(s.jargon("<b>Uni</b> &lt;uni.service&gt;", s.JAN))


class LesbarkeitTest(unittest.TestCase):
    def test_silben(self):
        self.assertEqual(s.silben("Haus"), 1)
        self.assertEqual(s.silben("Schule"), 2)
        self.assertEqual(s.silben("Arbeitsblatt"), 3)

    def test_kurzer_text_ohne_formel(self):
        m = s.lesbarkeit("Uni ist dran.")
        self.assertIsNone(m.wstf)
        self.assertEqual((m.laengster_satz, m.woerter), (3, 3))

    def test_einfach_leichter_als_amtsdeutsch(self):
        einfach = s.lesbarkeit("Das hat nicht geklappt. Jan weiß Bescheid. Du musst nichts tun. Ich melde mich später.")
        schwer = s.lesbarkeit("Die Gegenüberstellung unterschiedlicher Straftheorien ermöglicht eine differenzierte "
                              "Auseinandersetzung mit gesellschaftlichen Normvorstellungen.")
        self.assertLess(einfach.wstf, 3)
        self.assertGreater(schwer.wstf, 10)
        self.assertEqual(schwer.laengster_satz, 11)

    def test_messung_ohne_technik_und_aufklappbares(self):
        m = s.lesbarkeit("Kurz.\n\n<blockquote expandable>Belege\n• " + "sehr langer Beleg " * 50 + "</blockquote>")
        self.assertEqual(m.zeichen, 5)
        self.assertEqual(s.lesbarkeit("Siehe https://example.org/a/b und data/termine/x.ics heute.").woerter, 3)
        self.assertEqual(s.lesbarkeit("Abgabe z. B. am 19.10. um 22:00 Uhr.").laengster_satz, 4)

    def test_zitate_und_beschriftungen_zaehlen_nicht(self):
        einfach = "Das hat nicht geklappt. Jan weiß Bescheid. Du musst nichts tun."
        mit = s.lesbarkeit("Neues Material\nZu „Arbeitsblatt kategorischer Imperativ Klassenstufe zehn“:\n" + einfach)
        self.assertEqual(mit.wstf, s.lesbarkeit("Zu:\n" + einfach).wstf)
        self.assertTrue(s.ist_fliesstext("Fach, Klasse, Thema, Dauer, Ort"))
        self.assertFalse(s.ist_fliesstext("Meine Anfragen"))
        self.assertEqual(s.lesbarkeit("Zu „eins zwei drei vier fünf sechs sieben acht neun“: Danke.").laengster_satz, 2)


class PruefenTest(unittest.TestCase):
    def test_grenzen_je_person(self):
        satz = "Ich habe dir heute ein neues Arbeitsblatt zum Thema Strafe für deine achte Klasse mit drei Aufgaben gemacht."
        self.assertIn("satz: 18 Wörter, höchstens 15", s.pruefen(satz, s.LIA))
        self.assertEqual(s.pruefen(satz, s.JAN), [])
        lang = "Das ist gut. " * 70
        self.assertTrue(any(b.startswith("laenge:") for b in s.pruefen(lang, s.JAN)))
        self.assertEqual(s.pruefen(lang, s.JAN, ausnahmen=("laenge",)), [])

    def test_log_ohne_inhalt(self):
        befunde = s.pruefen("Fehler in /home/agent/geheim/lia.txt", s.JAN)
        log = s.log_text(befunde)
        self.assertIn("pfad: Pfad", log)
        self.assertNotIn("geheim", log)
        self.assertNotIn("lia.txt", log)


if __name__ == "__main__":
    unittest.main()
