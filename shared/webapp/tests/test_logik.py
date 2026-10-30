import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import logik

JETZT = datetime(2026, 10, 30, 15, 0, tzinfo=ZoneInfo("Europe/Berlin"))


def auftrag(aid, agent="unterricht", status="erledigt", text="Arbeitsblatt Strafe", abgeschlossen="2026-10-30T14:16:49+01:00",
            **felder):
    return {"id": aid, "agent": agent, "text": text, "status": status, "erstellt": "2026-10-30T14:09:44+01:00",
            "abgeschlossen": abgeschlossen, "ergebnis": "", "ergebnis_dateien": [], **felder}


class TestTexte(unittest.TestCase):
    def test_ohne_ids(self):
        self.assertEqual(logik.ohne_ids("Fassung Der nackte Wahnsinn: Runde runde-20261029-140740"),
                         "Fassung Der nackte Wahnsinn")
        self.assertEqual(logik.ohne_ids("Nachbesserung zu „X“ (Auftrag 20261029-150107-theater-0baec0)"),
                         "Nachbesserung zu „X“")
        self.assertEqual(logik.ohne_ids("siehe 20261030-110916-feedback-1c1e7e bitte"), "siehe bitte")

    def test_zeit_text(self):
        self.assertEqual(logik.zeit_text("2026-10-30T14:16:49+01:00", JETZT), "heute 14:16")
        self.assertEqual(logik.zeit_text("2026-10-29T15:01:07+01:00", JETZT), "gestern 15:01")
        self.assertEqual(logik.zeit_text("2026-10-25T00:37:45+02:00", JETZT), "So 25.10.")  # Sommerzeit, nicht 24.10. 23:37
        self.assertEqual(logik.zeit_text(None, JETZT), "")

    def test_dateien_text(self):
        self.assertEqual(logik.dateien_text([]), "")
        self.assertEqual(logik.dateien_text(["a/Fallsuche Strafe.pdf"]), "1 PDF")
        self.assertEqual(logik.dateien_text(["1.docx", "2.docx"]), "2 Word-Dateien")
        self.assertEqual(logik.dateien_text(["m.xlsx", "x.pdf", "y.zip"]), "1 Excel-Datei, 1 PDF, 1 Datei")

    def test_art(self):
        self.assertEqual(logik.art({"agent": "unterricht", "quelle": "portal-material"}), "Material")
        self.assertEqual(logik.art({"agent": "unterricht", "quelle": "portal-frage"}), "Frage")
        self.assertEqual(logik.art({"agent": "theater"}), "Theater")
        self.assertEqual(logik.art({"agent": "neuer-agent"}), "Auftrag")

    def test_titel_nachbesserung_und_feedback_mit_bezug(self):
        alt = auftrag("A", agent="theater", text="Fassung Der nackte Wahnsinn: Runde runde-20261029-140740")
        nb = auftrag("B", agent="theater", bezug="A", text="Nachbesserung zu deinem Ergebnis (Auftrag A)")
        fb = auftrag("C", agent="feedback", bezug="A", text="wieviele minuten?")
        nach_id = {"A": alt}
        self.assertEqual(logik.titel(nb, nach_id), "Antwort auf deine Rückmeldung zu „Fassung Der nackte Wahnsinn“")
        self.assertEqual(logik.titel(fb, nach_id), "Deine Rückmeldung zu „Fassung Der nackte Wahnsinn“")
        self.assertEqual(logik.titel(nb, {}), "Antwort auf deine Rückmeldung")

    def test_titel_erste_zeile_gross(self):
        a = auftrag("A", text="meine formatvorlage darauf anwenden\n\nAngehängte Dateien von Lia: data/eingang/x.pdf")
        self.assertEqual(logik.titel(a, {}), "Meine formatvorlage darauf anwenden")
        self.assertEqual(logik.titel(auftrag("A", text=""), {}), "Material")


class TestHeute(unittest.TestCase):
    def test_leer(self):
        h = logik.heute([], [], [], JETZT)
        self.assertEqual(h["anzahl_wartet"], 0)
        self.assertEqual(h["wartet_text"], "Gerade wartet nichts auf dich.")
        self.assertEqual((h["wartet"], h["laeuft"], h["fertig"], h["fehlgeschlagen"]), ([], [], [], []))
        self.assertEqual(h["datum"], "Fr 30.10.")

    def test_einteilung(self):
        entwurf = {"id": "E", "agent": "examen", "typ": "entwurf", "titel": "Umfrage vor der Reihe",
                   "erstellt": "2026-10-25T00:37:45+02:00"}
        neu = auftrag("N", ergebnis_dateien=["d/x.docx"])
        alt = auftrag("O", agent="recherche", text="Fallsuche Straftheorien: Dossier",
                      abgeschlossen="2026-10-27T17:54:47+01:00", ergebnis_dateien=["d/F.pdf"])
        kaputt = auftrag("K", status="fehlgeschlagen", abgeschlossen="2026-10-22T23:27:02+02:00",
                         ergebnis="Gerade ist das gemeinsame Kontingent aufgebraucht.")
        fb = auftrag("F", agent="feedback", bezug="O", text="zu lang")
        weg = auftrag("Z", status="zurueckgezogen")
        laeuft = auftrag("L", status="neu", abgeschlossen=None, text="Folien Kant")
        h = logik.heute([laeuft], [neu, alt, kaputt, fb, weg], [entwurf], JETZT, person="Lia")

        self.assertEqual(h["begruessung"], "Hallo Lia.")
        self.assertEqual(h["anzahl_wartet"], 2)
        self.assertEqual(h["wartet_text"], "Sachen warten auf dich.")
        e, n = h["wartet"]
        self.assertEqual((e["titel"], e["unter"], e["marke"], e["hinweis"]),
                         ("Umfrage vor der Reihe", "Entwurf · So 25.10.", "Offen", "Setzt du selbst ein"))
        self.assertEqual((n["titel"], n["unter"], n["marke"], n["hinweis"]),
                         ("Arbeitsblatt Strafe", "Material · heute 14:16", "Neu", "1 Word-Datei"))
        self.assertEqual([x["titel"] for x in h["laeuft"]], ["Folien Kant"])
        self.assertEqual(h["laeuft"][0]["unter"], "Material · seit heute 14:09")
        self.assertEqual([(x["titel"], x["unter"], x["hinweis"]) for x in h["fertig"]],
                         [("Fallsuche Straftheorien: Dossier", "Recherche · Di 27.10.", "1 PDF")])
        self.assertEqual(len(h["fehlgeschlagen"]), 1)
        self.assertEqual(h["fehlgeschlagen"][0]["grund"], "Gerade ist das gemeinsame Kontingent aufgebraucht.")

    def test_keine_ids_und_agentennamen_in_der_ansicht(self):
        a = auftrag("20261030-111155-theater-5d88d5", agent="theater", bezug="20261029-150107-theater-0baec0",
                    text="Nachbesserung zu deinem Ergebnis (Auftrag 20261029-150107-theater-0baec0)")
        b = auftrag("20261029-150107-theater-0baec0", agent="theater",
                    text="Fassung Der nackte Wahnsinn: Runde runde-20261029-140740")
        k = auftrag("20261022-232618-unterricht-67ba47", status="fehlgeschlagen", ergebnis="")
        h = logik.heute([], [a, b, k], [], JETZT)
        alles = repr(h)
        for verboten in ("2026102", "theater-", "unterricht", "feedback", "runde-"):
            self.assertNotIn(verboten, alles)
        self.assertEqual(h["fehlgeschlagen"][0]["grund"], logik.FEHLGESCHLAGEN)

    def test_neu_nur_im_zeitraum(self):
        grenze = (JETZT - timedelta(hours=logik.NEU_STUNDEN)).isoformat()
        frueher = (JETZT - timedelta(hours=logik.NEU_STUNDEN, seconds=1)).isoformat()
        self.assertTrue(logik.ist_neu(auftrag("A", abgeschlossen=grenze), JETZT))
        self.assertFalse(logik.ist_neu(auftrag("A", abgeschlossen=frueher), JETZT))

    def test_fertig_begrenzt(self):
        alt = [auftrag(f"A{i}", abgeschlossen=f"2026-10-{10 + i:02d}T10:00:00+01:00") for i in range(12)]
        h = logik.heute([], alt, [], JETZT)
        self.assertEqual(len(h["fertig"]), logik.FERTIG_ANZAHL)
        self.assertEqual(h["fertig_weitere"], 2)
        self.assertEqual(h["fertig"][0]["unter"], "Material · Mi 21.10.")  # neueste zuerst

    def test_eine_sache(self):
        h = logik.heute([], [auftrag("N")], [], JETZT)
        self.assertEqual(h["wartet_text"], "Sache wartet auf dich.")


if __name__ == "__main__":
    unittest.main()
