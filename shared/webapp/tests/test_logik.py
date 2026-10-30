import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import logik

JETZT = datetime(2026, 10, 30, 15, 0, tzinfo=ZoneInfo("Europe/Berlin"))


def auftrag(aid, agent="unterricht", status="erledigt", text="Arbeitsblatt Strafe", abgeschlossen="2026-10-30T14:16:49+01:00",
            erstellt="2026-10-30T14:09:44+01:00", **felder):
    return {"id": aid, "agent": agent, "text": text, "status": status, "erstellt": erstellt,
            "abgeschlossen": abgeschlossen, "ergebnis": "", "ergebnis_dateien": [], **felder}


ALT_ID, FB_ID, NB_ID = ("20261029-150107-theater-0baec0", "20261030-110916-feedback-1c1e7e",
                        "20261030-111155-theater-5d88d5")


def theater_kette():
    """Wie in lia/instanz: Fassung, Lias Frage dazu (Feedback), Antwort als Nachbesserung ohne Dateien."""
    alt = auftrag(ALT_ID, agent="theater", text="Fassung Der nackte Wahnsinn: Runde runde-20261029-140740",
                  erstellt="2026-10-29T15:01:07+01:00", abgeschlossen="2026-10-29T15:01:07+01:00",
                  ergebnis_dateien=["d/1 Szenenkarte.docx", "d/2 Ablauf.docx"],
                  daten={"kern": "19 Bausteine für 38 Minuten.", "punkte": ["Szenenkarte"]})
    fb = auftrag(FB_ID, agent="feedback", bezug=ALT_ID, text="wieviele minuten ist das etwa lang?",
                 erstellt="2026-10-30T11:09:16+01:00", abgeschlossen="2026-10-30T11:09:25+01:00",
                 ergebnis="Danke. Das lege ich Jan zur Entscheidung vor.", daten={"nachbesserung": NB_ID})
    nb = auftrag(NB_ID, agent="theater", bezug=ALT_ID, erstellt="2026-10-30T11:11:55+01:00",
                 abgeschlossen="2026-10-30T12:19:06+01:00",
                 text=f"Nachbesserung zu deinem Ergebnis (Auftrag {ALT_ID}):\n\nBeantworte Lias Frage",
                 daten={"kern": "Etwa 38 Min.", "punkte": ["Anfang 3 Min"], "pruefen": "Nicht dazuzählen."})
    return alt, fb, nb


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

    def test_feedback_schleife_ist_eine_zeile(self):
        alt, fb, nb = theater_kette()
        h = logik.heute([], [nb, fb, alt], [], JETZT)
        self.assertEqual([(z["titel"], z["unter"], z["marke"], z["hinweis"], z["link"]) for z in h["wartet"]],
                         [("Fassung Der nackte Wahnsinn", "Theater · heute 12:19", "Neu",
                           "2 Word-Dateien · nach deiner Rückmeldung", f"/ergebnis/{ALT_ID}")])
        self.assertEqual((h["fertig"], h["laeuft"]), ([], []))
        # Nachbesserung läuft: die Kette steht nur unter "Läuft gerade", mit Link auf das bisherige Ergebnis
        laeuft = {**nb, "status": "neu", "abgeschlossen": None}
        h = logik.heute([laeuft], [fb, alt], [], JETZT)
        self.assertEqual((h["wartet"], h["fertig"]), ([], []))
        self.assertEqual([(z["titel"], z["unter"], z["hinweis"], z["link"]) for z in h["laeuft"]],
                         [("Fassung Der nackte Wahnsinn", "Theater · seit heute 11:11", "Arbeitet an deiner Rückmeldung",
                           f"/ergebnis/{ALT_ID}")])
        # Rückmeldung läuft noch (noch keine Nachbesserung): ebenso
        fb_laeuft = {**fb, "status": "neu", "abgeschlossen": None}
        h = logik.heute([fb_laeuft], [alt], [], JETZT)
        self.assertEqual([(z["titel"], z["unter"]) for z in h["laeuft"]],
                         [("Fassung Der nackte Wahnsinn", "Theater · seit heute 11:09")])
        # Älter als NEU_STUNDEN: unter Fertig; letzte Nachbesserung fehlgeschlagen: unter Hat nicht geklappt
        spaeter = JETZT + timedelta(days=3)
        self.assertEqual([z["titel"] for z in logik.heute([], [alt, fb, nb], [], spaeter)["fertig"]],
                         ["Fassung Der nackte Wahnsinn"])
        kaputt = {**nb, "status": "fehlgeschlagen", "ergebnis": "Kontingent aufgebraucht."}
        h = logik.heute([], [alt, fb, kaputt], [], JETZT)
        self.assertEqual((h["wartet"], h["fertig"]), ([], []))
        self.assertEqual([(z["titel"], z["grund"]) for z in h["fehlgeschlagen"]],
                         [("Fassung Der nackte Wahnsinn", "Kontingent aufgebraucht.")])

    def test_eine_sache(self):
        h = logik.heute([], [auftrag("N")], [], JETZT)
        self.assertEqual(h["wartet_text"], "Sache wartet auf dich.")



class TestErgebnis(unittest.TestCase):
    def test_kern_punkte_pruefen_und_dateien(self):
        a = auftrag("A", agent="theater", text="Fassung Der nackte Wahnsinn: Runde runde-20261029-140740",
                    ergebnis="langer Telegram-Text", ergebnis_dateien=["d/1 Szenenkarte.docx", "d/2 Ablauf.docx"],
                    daten={"kern": "19 Bausteine.", "punkte": ["Szenenkarte", "Ablauf"], "pruefen": "Frederick?",
                           "knoepfe": "nur_antwort"})
        e = logik.ergebnis([a], {"A": [(True, True, 17), (True, False, 0)]}, JETZT)
        self.assertEqual((e["titel"], e["unter"]), ("Fassung Der nackte Wahnsinn", "Theater · heute 14:16"))
        self.assertEqual((e["kern"], e["punkte"], e["pruefen"]), ("19 Bausteine.", ["Szenenkarte", "Ablauf"],
                                                                  "Frederick?"))
        self.assertEqual(e["bloecke"], [])  # mit Kern kein zweites Mal der ganze Text
        self.assertFalse(e["fehlgeschlagen"])
        d1, d2 = e["dateien"]
        self.assertEqual((d1["nr"], d1["name"], d1["seiten"], d1["auftrag"]), (0, "1 Szenenkarte", 17, "A"))
        self.assertEqual((e["dateien_aus"], e["laeuft"]), ("", ""))
        self.assertEqual([(x["name"], x["von"], x["aktuell"]) for x in e["verlauf"]],
                         [("Fassung 1", "vom Assistenten", True)])  # Fassungen auch ohne Schleife
        self.assertEqual(d1["knoepfe"], [{"text": "PDF", "lang": "PDF zum Drucken", "pfad": "/pdf"},
                                         {"text": "Word", "lang": "In Word öffnen", "pfad": ""}])
        self.assertEqual(d2["knoepfe"], [{"text": "Word", "lang": "In Word öffnen", "pfad": ""}])
        self.assertEqual((e["art_zeile"], e["marke"], e["aktuell_ref"], e["aktuell_final"]),
                         ("Theater · 2 Word-Dateien", "Neu · wartet", "A", False))

    def test_ohne_daten_ganzer_text_in_bloecken(self):
        a = auftrag("A", ergebnis="Erster Absatz.\n\nZweiter.\n- eins\n- zwei\nDanach (Auftrag 20261030-140944-unterricht-93e29e)")
        e = logik.ergebnis([a], {}, JETZT)
        self.assertEqual(e["bloecke"], [{"absatz": "Erster Absatz."}, {"absatz": "Zweiter."},
                                        {"punkte": ["eins", "zwei"]}, {"absatz": "Danach"}])
        self.assertEqual((e["kern"], e["punkte"], e["dateien"]), ("", [], []))

    def test_titel_in_der_ansicht_lang(self):
        a = auftrag("A", text="x" * 150)
        self.assertEqual(logik.ergebnis([a], {}, JETZT)["titel"], "X" + "x" * 149)

    def test_fehlgeschlagen_zeigt_grund_ohne_dateien(self):
        a = auftrag("K", status="fehlgeschlagen", ergebnis="Kontingent aufgebraucht.",
                    ergebnis_dateien=["d/x.docx"], daten={"kern": "alt"})
        e = logik.ergebnis([a], {}, JETZT)
        self.assertTrue(e["fehlgeschlagen"])
        self.assertEqual(e["grund"], "Kontingent aufgebraucht.")
        self.assertEqual((e["kern"], e["dateien"]), ("", []))
        leer = auftrag("K", status="fehlgeschlagen", ergebnis="")
        self.assertEqual(logik.ergebnis([leer], {}, JETZT)["grund"], logik.FEHLGESCHLAGEN)

    def test_feedback_schleife_ein_auftrag_mit_verlauf(self):
        alt, fb, nb = theater_kette()
        alle = [nb, alt, fb]
        e = logik.ergebnis(logik.kette_von(NB_ID, alle), {ALT_ID: [(True, True, 3), (True, False, 0)]}, JETZT)
        self.assertEqual(e["titel"], "Fassung Der nackte Wahnsinn")
        self.assertEqual(e["unter"], "Theater · heute 12:19")  # Zeit der neuesten Fassung
        # Oben die Antwort, die Dateien aus der ersten Fassung (die Antwort hat keine)
        self.assertEqual((e["kern"], e["punkte"], e["pruefen"]), ("Etwa 38 Min.", ["Anfang 3 Min"], "Nicht dazuzählen."))
        self.assertEqual([(d["auftrag"], d["name"]) for d in e["dateien"]],
                         [(ALT_ID, "1 Szenenkarte"), (ALT_ID, "2 Ablauf")])
        self.assertEqual(e["dateien_aus"], "Fassung 1")
        v = e["verlauf"]
        self.assertEqual([(x["art"], x["name"], x["zeit"]) for x in v],
                         [("fassung", "Fassung 1", "gestern 15:01"), ("rueckmeldung", "Deine Rückmeldung", "heute 11:09"),
                          ("fassung", "Antwort", "heute 12:19")])
        self.assertEqual((v[0]["aktuell"], v[2]["aktuell"]), (False, True))
        self.assertEqual(v[0]["kern"], "19 Bausteine für 38 Minuten.")
        self.assertEqual(len(v[0]["dateien"]), 2)
        self.assertEqual((v[1]["zitat"], v[1]["notiz"]), ("wieviele minuten ist das etwa lang?", ""))
        # Jede ID der Kette ergibt dieselbe Kette mit demselben Kopf
        for aid in (ALT_ID, FB_ID, NB_ID):
            self.assertEqual(logik.kopf(logik.kette_von(aid, alle))["id"], ALT_ID)
        self.assertEqual(logik.kette_von("gibt-es-nicht", alle), [])
        # Sichtbare Texte ohne IDs und Agentennamen (nur "id"/"auftrag" für Links dürfen IDs tragen)
        def ohne_links(x):
            if isinstance(x, dict):
                return {k: ohne_links(w) for k, w in x.items() if k not in ("id", "auftrag", "ref", "aktuell_ref")}
            return [ohne_links(w) for w in x] if isinstance(x, list) else x
        sichtbar = repr(ohne_links(e))
        for verboten in ("2026102", "theater", "feedback", "runde-"):
            self.assertNotIn(verboten, sichtbar)

    def test_verlauf_laufend_und_fehlgeschlagen(self):
        alt, fb, nb = theater_kette()
        laeuft = {**nb, "status": "neu", "abgeschlossen": None}
        e = logik.ergebnis([alt, fb, laeuft], {}, JETZT)
        self.assertEqual(e["laeuft"], "Arbeitet gerade an deiner Rückmeldung (seit heute 11:11).")
        self.assertEqual(e["kern"], "19 Bausteine für 38 Minuten.")  # oben noch die erste Fassung
        self.assertEqual(e["dateien_aus"], "")
        self.assertEqual((e["verlauf"][2]["notiz"], e["verlauf"][2]["zeit"]), ("Läuft gerade.", "seit heute 11:11"))
        kaputt = {**nb, "status": "fehlgeschlagen", "ergebnis": "Kontingent aufgebraucht."}
        e = logik.ergebnis([alt, fb, kaputt], {}, JETZT)
        self.assertFalse(e["fehlgeschlagen"])
        self.assertEqual(e["zuletzt_fehlgeschlagen"], "Kontingent aufgebraucht.")
        self.assertEqual(e["verlauf"][2]["notiz"], "Hat nicht geklappt: Kontingent aufgebraucht.")
        # Rückmeldung ohne Nachbesserung (z. B. als Regel übernommen): die Antwort des Feedback-Agenten
        nur_fb = {**fb, "daten": {}, "ergebnis": "Danke, merke ich mir."}
        self.assertEqual(logik.ergebnis([alt, nur_fb], {}, JETZT)["verlauf"][1]["notiz"], "Danke, merke ich mir.")

    def test_zweite_nachbesserung_mit_dateien_ist_fassung_2(self):
        alt, fb, nb = theater_kette()
        fb2 = auftrag("FB2", agent="feedback", bezug=NB_ID, text="kürzer bitte", erstellt="2026-10-30T13:00:00+01:00")
        nb2 = auftrag("NB2", agent="theater", bezug=NB_ID, text="Nachbesserung", abgeschlossen="2026-10-30T14:00:00+01:00",
                      ergebnis_dateien=["d/3 Spielfassung.docx"], daten={"kern": "Gekürzt."})
        alle = [alt, fb, nb, fb2, nb2]
        self.assertEqual({logik.kopf(logik.kette_von(x, alle))["id"] for x in ("FB2", "NB2")}, {ALT_ID})
        e = logik.ergebnis(logik.kette_von("NB2", alle), {"NB2": [(True, True, 1)]}, JETZT)
        self.assertEqual([x["name"] for x in e["verlauf"]],
                         ["Fassung 1", "Deine Rückmeldung", "Antwort", "Deine Rückmeldung", "Fassung 2"])
        self.assertEqual((e["kern"], e["dateien_aus"], e["dateien"][0]["auftrag"]), ("Gekürzt.", "", "NB2"))

    def test_bezug_im_kreis_bricht_ab(self):
        a = auftrag("A", bezug="B")
        b = auftrag("B", bezug="A", abgeschlossen="2026-10-30T15:00:00+01:00")
        self.assertEqual(sorted(x["id"] for k in logik.ketten([a, b]) for x in k), ["A", "B"])  # endet, nichts doppelt

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
        self.assertEqual(d[0]["knoepfe"], [{"text": "PDF", "lang": "PDF zum Drucken", "pfad": ""}])  # nicht doppelt
        self.assertEqual([k["text"] for k in d[1]["knoepfe"]], ["PDF", "Excel"])
        self.assertEqual([k["text"] for k in d[2]["knoepfe"]], ["PowerPoint"])

    def test_fassung_namen(self):
        alt, fb, nb = theater_kette()
        self.assertEqual(logik.fassung_namen([alt, fb, nb]), {ALT_ID: "Fassung 1", NB_ID: "Antwort"})
        nb_datei = {**nb, "ergebnis_dateien": ["d/neu.docx"]}
        self.assertEqual(logik.fassung_namen([alt, fb, nb_datei])[NB_ID], "Fassung 2")

    def test_betrachter(self):
        alt, fb, nb = theater_kette()
        nb = {**nb, "ergebnis_dateien": ["d/neu.docx"]}
        datei = {"nr": 1, "name": "Ablauf", "seiten": 3,
                 "knoepfe": [{"text": "PDF", "pfad": "/pdf"}, {"text": "Word", "pfad": ""}]}
        b = logik.betrachter([alt, fb, nb], NB_ID, datei, None)  # ohne ?seite= die erste Seite
        basis = f"/ergebnis/{NB_ID}/datei/1"
        self.assertEqual((b["titel"], b["unter"], b["seite"], b["bild"], b["vorher"], b["nachher"]),
                         ("Ablauf", "Fassung 2 · Seite 1 von 3", 1, basis + "/seite/1", "", basis + "/ansehen?seite=2"))
        self.assertEqual((b["ergebnis_titel"], b["ergebnis_link"]), ("Fassung Der nackte Wahnsinn", f"/ergebnis/{ALT_ID}"))
        self.assertEqual([k["link"] for k in b["knoepfe"]], [basis + "/pdf", basis])
        b = logik.betrachter([alt, fb, nb], NB_ID, datei, "2")
        self.assertEqual((b["vorher"], b["nachher"]), (basis + "/ansehen?seite=1", basis + "/ansehen?seite=3"))
        self.assertEqual([s["aktiv"] for s in b["seiten"]], [False, True, False])
        b = logik.betrachter([alt, fb, nb], NB_ID, datei, " 3 ")
        self.assertEqual((b["nachher"], b["seite"]), ("", 3))
        for falsch in ("0", "4", "-1", "x", "", "1.5", "٢", "00002000000"):
            self.assertIsNone(logik.betrachter([alt, fb, nb], NB_ID, datei, falsch), falsch)
        self.assertIsNone(logik.betrachter([alt], ALT_ID, {**datei, "seiten": 0}, "1"))  # keine Seitenbilder
        # nur eine Fassung: keine Fassung im Untertitel
        self.assertEqual(logik.betrachter([alt], ALT_ID, datei, "1")["unter"], "Seite 1 von 3")

    def test_seiten_text(self):
        self.assertEqual((logik.seiten_text(1), logik.seiten_text(4)), ("1 Seite", "4 Seiten"))


class TestMaterial(unittest.TestCase):
    """Material-Ansicht wie Board "Desktop": Fassungen samt eigener Fassungen, final, Rückmeldung."""

    def test_eigene_fassung_zeitlich_eingereiht(self):
        alt, fb, nb = theater_kette()
        nb = {**nb, "ergebnis_dateien": ["d/neu.docx"]}
        eigene = [{"name": "Spielfassung.docx", "zeit": "2026-10-30T10:00:00+01:00", "notiz": "mit deinen Kommentaren"}]
        self.assertEqual(logik.fassung_namen([alt, fb, nb], eigene),
                         {ALT_ID: "Fassung 1", "eigene-1": "Fassung 2", NB_ID: "Fassung 3"})
        v = logik.verlauf([alt, fb, nb], nb, {}, JETZT, eigene, "eigene-1")
        self.assertEqual([(x["art"], x["name"]) for x in v],
                         [("fassung", "Fassung 1"), ("eigene", "Fassung 2"), ("rueckmeldung", "Deine Rückmeldung"),
                          ("fassung", "Fassung 3")])
        self.assertEqual((v[1]["von"], v[1]["beschreibung"], v[1]["datei"], v[1]["final"], v[1]["finalbar"]),
                         ("von dir", "mit deinen Kommentaren", {"name": "Spielfassung", "nr": 1, "knopf": "Word"},
                          True, True))
        self.assertEqual((v[0]["von"], v[0]["beschreibung"], v[0]["final"]),
                         ("vom Assistenten", "19 Bausteine für 38 Minuten.", False))

    def test_final_und_marke(self):
        alt, fb, nb = theater_kette()
        e = logik.ergebnis([alt, fb, nb], {}, JETZT, final_ref=ALT_ID)
        # Die Antwort ohne Dateien ist keine Fassung zum Markieren; der Knopf gilt für Fassung 1 mit den Dateien
        self.assertEqual((e["marke"], e["final_name"], e["aktuell_ref"], e["aktuell_final"]),
                         ("Final", "Fassung 1", ALT_ID, True))
        self.assertFalse(logik.final_erlaubt(NB_ID, e["verlauf"]))
        self.assertTrue(logik.final_erlaubt(ALT_ID, e["verlauf"]))
        self.assertFalse(logik.final_erlaubt("eigene-1", e["verlauf"]))
        e = logik.ergebnis([alt, fb, nb], {}, JETZT, final_ref=NB_ID)  # ungültig gespeichert: nicht final
        self.assertEqual((e["marke"], e["aktuell_final"]), ("Neu · wartet", False))
        laeuft = {**nb, "status": "neu", "abgeschlossen": None}
        self.assertEqual(logik.ergebnis([alt, fb, laeuft], {}, JETZT)["marke"], "Läuft")
        alt_alt = {**alt, "abgeschlossen": "2026-10-20T10:00:00+02:00"}
        self.assertEqual(logik.ergebnis([alt_alt], {}, JETZT)["marke"], "")

    def test_final_setzen_und_eigene_dazu(self):
        z = {"final": {}, "eigene": {}}
        z1 = logik.final_setzen(z, "K", "A", True, "t1")
        self.assertEqual(z1["final"], {"K": {"fassung": "A", "zeit": "t1"}})
        self.assertEqual(z["final"], {})  # nichts verändert
        self.assertEqual(logik.final_setzen(z1, "K", "B", True, "t2")["final"]["K"]["fassung"], "B")  # nur eine
        self.assertEqual(logik.final_setzen(z1, "K", "B", False, "t2")["final"], z1["final"])  # andere bleibt
        self.assertEqual(logik.final_setzen(z1, "K", "A", False, "t2")["final"], {})
        z2, n = logik.eigene_dazu(z1, "K", {"name": "a.docx"})
        z3, n3 = logik.eigene_dazu(z2, "K", {"name": "b.pdf"})
        self.assertEqual((n, n3, len(z2["eigene"]["K"]), len(z3["eigene"]["K"])), (1, 2, 1, 2))

    def test_heute_final_wartet_nicht(self):
        a = auftrag("A", abgeschlossen="2026-10-30T14:00:00+01:00")
        self.assertEqual(logik.heute([], [a], [], JETZT)["anzahl_wartet"], 1)
        h = logik.heute([], [a], [], JETZT, finale={"A"})
        self.assertEqual((h["anzahl_wartet"], [z["marke"] for z in h["fertig"]]), (0, ["Final"]))

    def test_rueckmeldung_und_dateien_pruefen(self):
        self.assertEqual(logik.rueckmeldung_pruefen("  kürzer  ", None), ("kürzer", []))
        self.assertEqual(logik.rueckmeldung_pruefen(" ", None)[1], ["Schreib kurz, was anders werden soll."])
        self.assertEqual(len(logik.rueckmeldung_pruefen("x" * 5001, None)[1]), 1)
        self.assertEqual(logik.rueckmeldung_pruefen("x", ("Foto.JPG", 10))[1], [])
        self.assertIn("geht nicht", logik.rueckmeldung_pruefen("x", ("a.exe", 10))[1][0])
        self.assertIn("zu groß", logik.datei_pruefen("a.docx", 21 * 1024 * 1024, logik.EIGENE_ENDUNGEN)[0])
        self.assertEqual(logik.datei_pruefen("a.png", 1, logik.EIGENE_ENDUNGEN),
                         ["Diese Datei geht nicht. Möglich sind: Excel, PDF, PowerPoint, Word."])
        self.assertEqual(logik.rueckmeldung_text("kürzer"), "kürzer")
        self.assertEqual(logik.rueckmeldung_text("kürzer", "Blatt.docx", "Fassung 2"),
                         "kürzer\n\nDazu gibt es eine Datei mit Kommentaren (Blatt.docx, Fassung 2). Sie liegt bisher "
                         "nur in der Web-App.")


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


class TestNeuerAuftrag(unittest.TestCase):
    def test_dateiname_bereinigen(self):
        self.assertEqual(logik.dateiname_bereinigen("3 Spielfassung_feedback.docx"), "3 Spielfassung_feedback.docx")
        self.assertEqual(logik.dateiname_bereinigen("../../.env"), "env")
        self.assertEqual(logik.dateiname_bereinigen("C:\\Users\\lia\\Foto.JPG"), "Foto.jpg")
        self.assertEqual(logik.dateiname_bereinigen(".versteckt.pdf"), "versteckt.pdf")
        self.assertEqual(logik.dateiname_bereinigen('a<b>\x00c?.pdf'), "a_b__c_.pdf")
        self.assertEqual(logik.dateiname_bereinigen(""), "datei")
        self.assertEqual(logik.dateiname_bereinigen(".pdf"), "pdf")
        lang = logik.dateiname_bereinigen("x" * 300 + ".docx")
        self.assertEqual((len(lang), lang[-5:]), (100, ".docx"))

    def test_pruefen(self):
        self.assertEqual(logik.neuer_auftrag_pruefen("  Arbeitsblatt Kant\r\n45 Min  ", []),
                         ("Arbeitsblatt Kant\n45 Min", []))
        self.assertEqual(logik.neuer_auftrag_pruefen("", [])[1], ["Schreib bitte kurz, was du brauchst."])
        self.assertEqual(len(logik.neuer_auftrag_pruefen("x" * (logik.NEU_TEXT_MAX + 1), [])[1]), 1)
        mb = 1024 * 1024
        _, fehler = logik.neuer_auftrag_pruefen("Vorlage", [("a.docx", mb), ("b.PNG", 2 * mb), ("c.exe", 10),
                                                            ("d.pdf", 21 * mb), ("e.pdf", 0)])
        self.assertEqual(len(fehler), 3)
        self.assertIn("„c.exe“", fehler[0])
        self.assertIn("größer als 20 MB", fehler[1])
        self.assertIn("leer", fehler[2])
        self.assertEqual(len(logik.neuer_auftrag_pruefen("x", [("a.pdf", 1)] * 11)[1]), 1)

    def test_herkunft(self):
        self.assertTrue(logik.herkunft_passt("http://localhost:8792", "localhost:8792", "same-origin"))
        self.assertTrue(logik.herkunft_passt("https://lia.meldro.de", "lia.meldro.de", None))
        self.assertFalse(logik.herkunft_passt("https://boese.example", "localhost:8792", "cross-site"))
        self.assertFalse(logik.herkunft_passt("https://boese.example", "localhost:8792", None))
        self.assertFalse(logik.herkunft_passt("http://localhost:8792", "localhost:8792", "same-site"))
        self.assertFalse(logik.herkunft_passt(None, "localhost:8792", None))
        self.assertFalse(logik.herkunft_passt("null", "localhost:8792", None))

    def test_token(self):
        geheim = b"g" * 32
        t = logik.formular_token(geheim)
        self.assertTrue(logik.token_passt(geheim, t))
        self.assertFalse(logik.token_passt(b"h" * 32, t))
        self.assertFalse(logik.token_passt(geheim, ""))
        self.assertFalse(logik.token_passt(geheim, None))


if __name__ == "__main__":
    unittest.main()


ETHIK = {"fach": "Ethik", "klasse": "8", "titel": "Straftheorien (in Planung)", "reihenfrage": "",
         "behandelt": ["Kant", "Bentham"], "agenten": ["examen"]}
THEATER = {"fach": "Darstellendes Spiel", "klasse": "Kurs 12", "titel": "Der nackte Wahnsinn", "agenten": ["theater"]}


def reihen(*eintraege):
    ergebnis, fehler = logik.reihen_aus(list(eintraege or (ETHIK, THEATER)))
    assert not fehler, fehler
    return ergebnis


class TestReihen(unittest.TestCase):
    def test_kennung(self):
        self.assertEqual(logik.kennung("Ethik", "8", "Straftheorien (in Planung)"), "ethik-8-straftheorien")
        self.assertEqual(logik.kennung("Darstellendes Spiel", "Kurs 12", "Der nackte Wahnsinn"),
                         "darstellendes-spiel-kurs-12-der-nackte-wahnsinn")
        self.assertEqual(logik.kennung("Ethik", "7", "Glückliches Leben: Wie?"), "ethik-7-glueckliches-leben-wie")

    def test_reihen_aus(self):
        ethik, theater = reihen()
        self.assertEqual((ethik["id"], ethik["gruppe"], ethik["gruppe_id"], ethik["laufend"]),
                         ("ethik-8-straftheorien", "Klasse 8", "ethik-8", True))
        self.assertEqual((theater["gruppe"], theater["fach_id"]), ("Kurs 12", "darstellendes-spiel"))

    def test_reihen_aus_fehler(self):
        faelle = [({"klasse": "8"}, "fach fehlt"), ({"fach": "Ethik"}, "klasse fehlt"),
                  ({**ETHIK, "farbe": "rot"}, "farbe"), ({**ETHIK, "behandelt": "Kant"}, "behandelt"),
                  ({**ETHIK, "id": "Ethik 8"}, "id"), ({**ETHIK, "stand": "fertig"}, "stand"), ("x", "kein Block")]
        for eintrag, text in faelle:
            with self.subTest(eintrag=eintrag):
                gut, fehler = logik.reihen_aus([eintrag])
                self.assertEqual(gut, [])
                self.assertIn(text, fehler[0])
        gut, fehler = logik.reihen_aus([ETHIK, ETHIK])
        self.assertEqual((len(gut), "doppelt" in fehler[0]), (1, True))
        self.assertEqual(logik.reihen_aus([{"klasse": "8"}], "Ethik")[0][0]["fach"], "Ethik")

    def test_reihe_von(self):
        r = reihen()
        self.assertEqual(logik.reihe_von({"agent": "theater"}, r)["fach"], "Darstellendes Spiel")
        self.assertEqual(logik.reihe_von({"agent": "examen"}, r)["fach"], "Ethik")
        self.assertIsNone(logik.reihe_von({"agent": "unterricht"}, r))  # nichts geraten
        self.assertEqual(logik.reihe_von({"agent": "unterricht", "reihe": "ethik-8-straftheorien"}, r)["klasse"], "8")
        self.assertIsNone(logik.reihe_von({"agent": "theater", "reihe": "gibt-es-nicht"}, r))
        zweimal = reihen(ETHIK, {**ETHIK, "titel": "Helfen"})  # examen in zwei Reihen: nicht sicher
        self.assertIsNone(logik.reihe_von({"agent": "examen"}, zweimal))

    def test_auswahl_und_pruefen(self):
        r = reihen(ETHIK, THEATER, {**ETHIK, "titel": "Helfen", "stand": "abgeschlossen"})
        self.assertEqual(logik.reihen_auswahl(r), [
            {"id": "ethik-8-straftheorien", "text": "Straftheorien (in Planung) (Ethik, Klasse 8)"},
            {"id": "darstellendes-spiel-kurs-12-der-nackte-wahnsinn",
             "text": "Der nackte Wahnsinn (Darstellendes Spiel, Kurs 12)"}])
        self.assertEqual(logik.reihe_pruefen("", r), (None, []))
        self.assertEqual(logik.reihe_pruefen("ethik-8-straftheorien", r), ("ethik-8-straftheorien", []))
        self.assertEqual(logik.reihe_pruefen("ethik-8-helfen", r)[0], None)  # abgeschlossen
        self.assertTrue(logik.reihe_pruefen("../x", r)[1])

    def test_heute_mit_ort(self):
        alt, fb, nb = theater_kette()
        material = auftrag("20261030-123903-unterricht-ef0a90", text="Notentabelle",
                           abgeschlossen="2026-10-27T12:00:00+01:00")
        entwurf = {"id": "20261025-003745-examen-0c44bf", "agent": "examen", "typ": "entwurf",
                   "titel": "Umfrage", "erstellt": "2026-10-25T00:37:45+02:00"}
        h = logik.heute([], [alt, fb, nb, material], [entwurf], JETZT, reihen=reihen())
        self.assertEqual([z["reihe"] for z in h["wartet"]],
                         ["Ethik › Klasse 8 › Straftheorien (in Planung)", "Darstellendes Spiel › Kurs 12 › Der nackte Wahnsinn"])
        self.assertEqual((h["fertig"][0]["titel"], h["fertig"][0]["reihe"]), ("Notentabelle", ""))
        self.assertNotIn("chips", h)

    def test_heute_ohne_reihen_wie_bisher(self):
        h = logik.heute([], [auftrag("20261030-123903-unterricht-ef0a90")], [], JETZT)
        self.assertEqual(h["wartet"][0]["reihe"], "")

    def test_reihe_ansicht(self):
        alt, fb, nb = theater_kette()
        material = auftrag("20261030-123903-unterricht-ef0a90", text="Notentabelle")
        mit_reihe = auftrag("20261030-140000-unterricht-aaaaaa", text="Arbeitsblatt Kant", status="neu",
                            abgeschlossen=None, reihe="ethik-8-straftheorien")
        entwurf = {"id": "20261025-003745-examen-0c44bf", "agent": "examen", "typ": "entwurf", "titel": "Umfrage",
                   "erstellt": "2026-10-25T00:37:45+02:00"}
        r = reihen()
        alle = [alt, fb, nb, material, mit_reihe]
        ethik = logik.reihe_ansicht(r[0], r, alle, JETZT, [entwurf])
        self.assertEqual((ethik["titel"], ethik["unter"], ethik["behandelt"]),
                         ("Straftheorien (in Planung)", "Ethik · Klasse 8", "Kant; Bentham"))
        self.assertEqual([(z["titel"], z["marke"]) for z in ethik["zeilen"]],
                         [("Umfrage", "Offen"), ("Arbeitsblatt Kant", "Läuft")])
        self.assertEqual(ethik["zeilen"][1]["link"], "")  # läuft noch, keine Ergebnis-Ansicht
        theater = logik.reihe_ansicht(r[1], r, alle, JETZT, [entwurf])
        self.assertEqual(len(theater["zeilen"]), 1)  # Kette mit Rückmeldung ist eine Zeile
        self.assertEqual(theater["zeilen"][0]["link"], f"/ergebnis/{ALT_ID}")
        self.assertEqual([z["titel"] for z in logik.zeilen_je_reihe(r, alle, JETZT)["ohne"]], ["Notentabelle"])
        self.assertEqual(logik.zeilen_je_reihe(r, alle, JETZT, finale={ALT_ID})[r[1]["id"]][0]["marke"], "Final")
        fertig = reihen({**ETHIK, "stand": "abgeschlossen"})[0]
        self.assertEqual(logik.reihe_ansicht(fertig, [fertig], [], JETZT)["unter"], "Ethik · Klasse 8 · abgeschlossen")

    def test_material_marke(self):
        alt, fb, nb = theater_kette()
        self.assertEqual(logik.material_marke([alt, fb, nb], JETZT), "Fassung 1 · neu")  # Antwort zählt nicht
        eigene = [{"name": "Blatt.docx", "zeit": "2026-10-30T13:00:00+01:00"}]
        self.assertEqual(logik.material_marke([alt, fb, nb], JETZT, eigene=eigene), "Fassung 2 · neu")
        spaeter = JETZT + timedelta(days=3)
        self.assertEqual(logik.material_marke([alt], spaeter), "Fassung 1")
        self.assertEqual(logik.material_marke([alt], spaeter, {ALT_ID}), "Final")
        self.assertEqual(logik.material_marke([alt, {**nb, "status": "neu"}], JETZT, {ALT_ID}), "Läuft")
        self.assertEqual(logik.material_marke([alt, {**nb, "status": "fehlgeschlagen"}], JETZT), "Hat nicht geklappt")

    def test_baum(self):
        r = reihen(ETHIK, THEATER, {**ETHIK, "titel": "Helfen", "stand": "abgeschlossen"})
        b = logik.baum(r, 2, "heute")
        self.assertEqual([(e["art"], e["text"], e.get("link", ""), e.get("tiefe")) for e in b], [
            ("eintrag", "Heute", "/", 0), ("fach", "Ethik", "", None), ("gruppe", "Klasse 8", "/klasse/ethik-8", 0),
            ("eintrag", "Straftheorien (in Planung)", "/reihe/ethik-8-straftheorien", 1),
            ("eintrag", "Helfen (abgeschlossen)", "/reihe/ethik-8-helfen", 1),
            ("fach", "Darstellendes Spiel", "", None), ("gruppe", "Kurs 12", "/klasse/darstellendes-spiel-kurs-12", 0),
            ("eintrag", "Der nackte Wahnsinn", "/reihe/darstellendes-spiel-kurs-12-der-nackte-wahnsinn", 1)])
        self.assertEqual((b[0]["zahl"], b[0]["aktiv"], b[3]["aktiv"]), (2, True, False))
        b = logik.baum(r, 0, "ethik-8-straftheorien")
        self.assertEqual((b[0]["zahl"], b[0]["aktiv"], b[3]["aktiv"]), ("", False, True))
        self.assertEqual(logik.baum([], 1), [{"art": "eintrag", "text": "Heute", "link": "/", "tiefe": 0,
                                              "zahl": 1, "aktiv": False}])

    def test_klasse_ansicht(self):
        r = reihen(ETHIK, THEATER, {**ETHIK, "titel": "Helfen", "stand": "abgeschlossen", "reihenfrage": "Wem helfen?"})
        e = logik.klasse_ansicht("ethik-8", r, {"ethik-8-helfen": [{}, {}], "ethik-8-straftheorien": [{}]})
        self.assertEqual((e["titel"], e["unter"]), ("Klasse 8", "Ethik"))
        self.assertEqual([(z["titel"], z["hinweis"], z["marke"], z["link"]) for z in e["zeilen"]], [
            ("Straftheorien (in Planung)", "1 Sache", "", "/reihe/ethik-8-straftheorien"),
            ("Helfen", "2 Sachen", "Abgeschlossen", "/reihe/ethik-8-helfen")])
        self.assertEqual(e["zeilen"][1]["unter"], "Wem helfen?")
        self.assertIsNone(logik.klasse_ansicht("ethik-9", r, {}))
        self.assertEqual(logik.krumen_klasse(r[0]), {"teile": [{"text": "Ethik", "link": ""}], "hier": "Klasse 8"})
        b = logik.baum(r, 0, logik.klasse_aktiv("ethik-8"))
        self.assertEqual([e["text"] for e in b if e.get("aktiv")], ["Klasse 8"])

    def test_krumen(self):
        ethik = reihen()[0]
        self.assertEqual(logik.krumen(), {"teile": [], "hier": "Heute"})
        self.assertEqual(logik.krumen("Neuer Auftrag"),
                         {"teile": [{"text": "Heute", "link": "/"}], "hier": "Neuer Auftrag"})
        self.assertEqual(logik.krumen(reihe=ethik), {"teile": [{"text": "Ethik", "link": ""},
                                                               {"text": "Klasse 8", "link": "/klasse/ethik-8"}],
                                                     "hier": "Straftheorien (in Planung)"})
        k = logik.krumen("Umfrage", ethik)
        self.assertEqual(([x["text"] for x in k["teile"]], k["teile"][2]["link"], k["hier"]),
                         (["Ethik", "Klasse 8", "Straftheorien (in Planung)"], "/reihe/ethik-8-straftheorien",
                          "Umfrage"))
        k = logik.krumen("Ablauf", ethik, {"text": "Umfrage", "link": "/ergebnis/x"})
        self.assertEqual(([x["text"] for x in k["teile"]], k["teile"][3]["link"], k["hier"]),
                         (["Ethik", "Klasse 8", "Straftheorien (in Planung)", "Umfrage"], "/ergebnis/x", "Ablauf"))
        k = logik.krumen("Ablauf", None, {"text": "Umfrage " * 20, "link": "/ergebnis/x"})
        self.assertEqual([x["link"] for x in k["teile"]], ["/", "/ergebnis/x"])
        self.assertLessEqual(len(k["teile"][1]["text"]), logik.KRUME_LANG)
