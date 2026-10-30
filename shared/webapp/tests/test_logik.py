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
        # Zeilen verlinken auf die Einzelansichten, laufende Aufträge (noch) nicht
        self.assertEqual((e["link"], n["link"]), ("/entwurf/E", "/ergebnis/N"))
        self.assertEqual(h["fertig"][0]["link"], "/ergebnis/O")
        self.assertEqual(h["fehlgeschlagen"][0]["link"], "/ergebnis/K")
        self.assertEqual(h["laeuft"][0]["link"], "")

    def test_keine_ids_und_agentennamen_in_der_ansicht(self):
        a = auftrag("20261030-111155-theater-5d88d5", agent="theater", bezug="20261029-150107-theater-0baec0",
                    text="Nachbesserung zu deinem Ergebnis (Auftrag 20261029-150107-theater-0baec0)")
        b = auftrag("20261029-150107-theater-0baec0", agent="theater",
                    text="Fassung Der nackte Wahnsinn: Runde runde-20261029-140740")
        k = auftrag("20261022-232618-unterricht-67ba47", status="fehlgeschlagen", ergebnis="")
        h = logik.heute([], [a, b, k], [], JETZT)
        # IDs nur in Links, nie im sichtbaren Text
        alles = repr([{k: v for k, v in z.items() if k != "link"} for z in [*h["wartet"], *h["fehlgeschlagen"]]])
        self.assertTrue(all(z["link"].startswith("/ergebnis/2026") for z in [*h["wartet"], *h["fehlgeschlagen"]]))
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



class TestErgebnis(unittest.TestCase):
    def test_kern_punkte_pruefen_und_dateien(self):
        a = auftrag("A", agent="theater", text="Fassung Der nackte Wahnsinn: Runde runde-20261029-140740",
                    ergebnis="langer Telegram-Text", ergebnis_dateien=["d/1 Szenenkarte.docx", "d/2 Ablauf.docx"],
                    daten={"kern": "19 Bausteine.", "punkte": ["Szenenkarte", "Ablauf"], "pruefen": "Frederick?",
                           "knoepfe": "nur_antwort"})
        e = logik.ergebnis(a, [a], [(True, True, 17), (True, False, 0)], JETZT)
        self.assertEqual((e["titel"], e["unter"]), ("Fassung Der nackte Wahnsinn", "Theater · heute 14:16"))
        self.assertEqual((e["kern"], e["punkte"], e["pruefen"]), ("19 Bausteine.", ["Szenenkarte", "Ablauf"],
                                                                  "Frederick?"))
        self.assertEqual(e["bloecke"], [])  # mit Kern kein zweites Mal der ganze Text
        self.assertFalse(e["fehlgeschlagen"])
        d1, d2 = e["dateien"]
        self.assertEqual((d1["nr"], d1["name"], d1["seiten"]), (0, "1 Szenenkarte", 17))
        self.assertEqual(d1["knoepfe"], [{"text": "PDF", "pfad": "/pdf"}, {"text": "Word", "pfad": ""}])
        self.assertEqual(d2["knoepfe"], [{"text": "Word", "pfad": ""}])

    def test_ohne_daten_ganzer_text_in_bloecken(self):
        a = auftrag("A", ergebnis="Erster Absatz.\n\nZweiter.\n- eins\n- zwei\nDanach (Auftrag 20261030-140944-unterricht-93e29e)")
        e = logik.ergebnis(a, [a], [], JETZT)
        self.assertEqual(e["bloecke"], [{"absatz": "Erster Absatz."}, {"absatz": "Zweiter."},
                                        {"punkte": ["eins", "zwei"]}, {"absatz": "Danach"}])
        self.assertEqual((e["kern"], e["punkte"], e["dateien"]), ("", [], []))

    def test_titel_in_der_ansicht_lang(self):
        a = auftrag("A", text="x" * 150)
        self.assertEqual(logik.ergebnis(a, [a], [], JETZT)["titel"], "X" + "x" * 149)

    def test_fehlgeschlagen_zeigt_grund_ohne_dateien(self):
        a = auftrag("K", status="fehlgeschlagen", ergebnis="Kontingent aufgebraucht.",
                    ergebnis_dateien=["d/x.docx"], daten={"kern": "alt"})
        e = logik.ergebnis(a, [a], [], JETZT)
        self.assertTrue(e["fehlgeschlagen"])
        self.assertEqual(e["grund"], "Kontingent aufgebraucht.")
        self.assertEqual((e["kern"], e["dateien"]), ("", []))
        leer = auftrag("K", status="fehlgeschlagen", ergebnis="")
        self.assertEqual(logik.ergebnis(leer, [leer], [], JETZT)["grund"], logik.FEHLGESCHLAGEN)

    def test_nachbesserung_verweist_auf_ursprung_und_rueckmeldung(self):
        alt_id, nb_id = "20261029-150107-theater-0baec0", "20261030-111155-theater-5d88d5"
        alt = auftrag(alt_id, agent="theater", text="Fassung Der nackte Wahnsinn: Runde runde-20261029-140740")
        nb = auftrag(nb_id, agent="theater", bezug=alt_id, abgeschlossen="2026-10-30T12:19:06+01:00",
                     text=f"Nachbesserung zu deinem Ergebnis (Auftrag {alt_id}):\n\nBeantworte Lias Frage")
        fb = auftrag("20261030-110916-feedback-1c1e7e", agent="feedback", bezug=alt_id,
                     text="wieviele minuten ist das etwa lang?", daten={"nachbesserung": nb_id})
        alle = [alt, nb, fb]
        e = logik.ergebnis(nb, alle, [], JETZT)
        self.assertEqual(e["titel"], "Antwort auf deine Rückmeldung zu „Fassung Der nackte Wahnsinn“")
        self.assertEqual(e["bezug"], {"titel": "Fassung Der nackte Wahnsinn", "link": f"/ergebnis/{alt_id}"})
        self.assertEqual(e["rueckmeldung"], "wieviele minuten ist das etwa lang?")
        self.assertEqual(e["antworten"], [])
        # Das ursprüngliche Ergebnis zeigt die Antwort, aber nicht die Feedback-Bestätigung
        u = logik.ergebnis(alt, alle, [], JETZT)
        self.assertEqual(u["antworten"], [{"titel": "Antwort auf deine Rückmeldung zu „Fassung Der nackte Wahnsinn“",
                                           "unter": "heute 12:19", "link": f"/ergebnis/{nb_id}"}])
        self.assertEqual((u["bezug"], u["rueckmeldung"]), (None, ""))
        # Sichtbare Texte ohne IDs und Agentennamen (Links dürfen IDs tragen)
        for ansicht in (e, u):
            sichtbar = repr({k: v for k, v in ansicht.items() if k not in ("bezug", "antworten")}
                            ) + repr([x["titel"] for x in ansicht["antworten"]])
            for verboten in ("2026102", "theater", "feedback", "runde-"):
                self.assertNotIn(verboten, sichtbar)

    def test_zeigbar(self):
        self.assertTrue(logik.zeigbar(auftrag("A")))
        self.assertTrue(logik.zeigbar(auftrag("A", status="fehlgeschlagen")))
        self.assertFalse(logik.zeigbar(auftrag("A", agent="feedback")))
        self.assertFalse(logik.zeigbar(auftrag("A", status="zurueckgezogen")))
        self.assertFalse(logik.zeigbar(auftrag("A", status="neu")))

    def test_dateien_ansicht(self):
        d = logik.dateien_ansicht(["a/F.pdf", "a/weg.docx", "a/M.xlsx", "a/D.pptx"],
                                  [(True, True, 2), (False, True, 3), (True, True, 1), (True, False, 0)])
        self.assertEqual([x["nr"] for x in d], [0, 2, 3])  # fehlende Datei fehlt, Nummern bleiben
        self.assertEqual(d[0]["knoepfe"], [{"text": "PDF", "pfad": ""}])  # PDF nicht doppelt
        self.assertEqual([k["text"] for k in d[1]["knoepfe"]], ["PDF", "Excel"])
        self.assertEqual([k["text"] for k in d[2]["knoepfe"]], ["PowerPoint"])


class TestEntwurf(unittest.TestCase):
    def test_ganzer_text_und_nur_bekannte_details(self):
        inhalt = "Kurze Umfrage\n\n1. Frage\n   [ ] in der Schule   [ ] zu Hause\n" + "lang " * 200
        e = logik.entwurf({"id": "20261025-003745-examen-0c44bf", "agent": "examen", "typ": "entwurf",
                           "titel": "Examensreihe Strafe: anonyme Umfrage", "inhalt": inhalt,
                           "daten": {"einsatz": "Lia selbst, auf Papier", "datei": "lia/examen/impuls.md"},
                           "erstellt": "2026-10-25T00:37:45+02:00"}, JETZT)
        self.assertEqual(e["inhalt"], inhalt.strip("\n"))  # keine Kürzung, Einrückung bleibt
        self.assertEqual(e["details"], [("Einsatz", "Lia selbst, auf Papier")])
        self.assertEqual((e["titel"], e["unter"], e["hinweis"]),
                         ("Examensreihe Strafe: anonyme Umfrage", "Entwurf · So 25.10.", "Setzt du selbst ein"))
        self.assertNotIn("examen", repr(e))

    def test_anderer_typ(self):
        e = logik.entwurf({"typ": "mail", "titel": "Mail", "inhalt": "Text"}, JETZT)
        self.assertEqual((e["hinweis"], e["details"]), ("Wartet auf deine Entscheidung", []))


if __name__ == "__main__":
    unittest.main()
