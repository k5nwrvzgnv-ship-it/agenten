"""Snapshots aller Nachrichtenarten, die schon als reine Funktion vorliegen (docs/sprache/inventur.md, A und B).

Inhalte aus echten Nachrichten (gekürzt). Dateiname: lia_* geht an Lia, jan_* an Jan; test_sprache_snapshots.py
prüft alle Snapshots gegen die Sprachregel. Neu schreiben wie in test_vorlagen.py: SNAPSHOTS_NEU=1.
"""

import os
import re
import unittest

from agentkit import ausfall
from agentkit import feedback as fb
import logik
import portal_logik as p
from tests.test_vorlagen import AID, ERLAUBT, ORDNER, darstellung

ZEIT = {"reset_5h": "Di 19:00", "reset_7d": "Mo 10:00", "zeit": "Di 16:40", "reset_status": "Di 19:00"}


def zeit_text(wert) -> str:
    return wert or "?"


ENTWURF = {
    "id": "20261024-003432-uni-e88e8a", "agent": "uni", "typ": "mail", "fingerabdruck": "x",
    "titel": "Mail: Test Uni-Agent: Mailversand nach Freigabe",
    "inhalt": "An: jkl298@hnee.de\nBetreff: Test Uni-Agent: Mailversand nach Freigabe\n\nHallo Jan,\n\ndas ist der erste "
              "echte Test des Mailversands. Diese Mail wurde erst gesendet, nachdem du sie in Telegram freigegeben "
              "hast.\n\nUni-Agent\n\n(Warum: Echttest des Mailteils, an dich selbst)",
    "daten": {"an": ["jkl298@hnee.de"], "cc": [], "betreff": "Test Uni-Agent: Mailversand nach Freigabe",
              "text": "Hallo Jan,\n\ndas ist der erste echte Test des Mailversands. Diese Mail wurde erst gesendet, "
                      "nachdem du sie in Telegram freigegeben hast.\n\nUni-Agent",
              "begruendung": "Echttest des Mailteils, an dich selbst"},
}
VERLAUF = " ".join(f"<2026{i:02d}11102541.{i}AB@mail.example.org>" if i % 2 else f"<{i}f3c9a@praxis.example.de>"
                   for i in range(1, 15))
ENTWURF_VERLAUF = {
    "id": "20261028-000141-posteingang-483303", "agent": "posteingang", "typ": "mail", "fingerabdruck": "x",
    "titel": "Mail: Re: Anfrage zur Beratung – Absage Termin am 2.11.", "inhalt": "(aus den daten)",
    "daten": {"an": ["m.berger@praxis.example.de"], "cc": [], "betreff": "Re: Anfrage zur Beratung – Absage Termin am 2.11.",
              "text": "Liebe Frau Berger,\n\nleider müssen wir unseren Termin am Montag, 2.11., absagen. Lia ist zu "
                      "dieser Zeit in der Schule gebunden.\n\nWäre im Dezember ein neuer Termin möglich?\n\n"
                      "Liebe Grüße\nLia und Jan",
              "begruendung": "Die Adresse und den Bezug habe ich aus dem Verlauf mit Frau Berger (m14, m11). Der Termin "
                             "steht im Kalender am 2.11. von 15:30 bis 16:30. Den Stil habe ich von m11 übernommen.",
              "in_reply_to": "<14f3c9a@praxis.example.de>", "references": VERLAUF,
              "antwort_auf": "\"Berger, M.\" <m.berger@praxis.example.de>: AW: AW: AW: AW: AW: AW: Anfrage zur Beratung",
              "antwort_auf_von": "\"Berger, M.\" <m.berger@praxis.example.de>",
              "antwort_auf_datum": "2026-08-11T10:25:41+02:00"},
}
ENTWURF_FRAGE = {**ENTWURF_VERLAUF, "daten": {
    **ENTWURF_VERLAUF["daten"], "pruefen": "ob 'eine Woche Vorlauf vereinbart' so stimmt, wie du es gemeint hast."}}
ENTWURF_LANG = {**ENTWURF_VERLAUF, "vorgaenger": "20261027-000000-posteingang-aaaaaa", "daten": {
    **ENTWURF_VERLAUF["daten"], "text": "Liebe Frau Berger,\n\n" + "\n\n".join(
        f"Punkt {i}: Wir haben die Unterlagen für Ihre Beratung durchgesehen und melden uns dazu bald." * 3
        for i in range(1, 31)) + "\n\nLiebe Grüße\nLia und Jan"}}
FREIGABE_KNOEPFE = [[("Freigeben", "f:x"), ("Ändern", "c:x"), ("Ablehnen", "a:x")]]
FEEDBACK_REGEL = {"art": "regel", "ziel": "recherche", "heikel": False,
                  "regel": "Jede Recherche beginnt oben mit einer klaren Empfehlung (z. B. welche Reihenfrage), bevor "
                           "die übrigen Teile folgen.",
                  "zusammenfassung": "Lia will bei jeder Recherche zuerst eine klare Empfehlung ganz oben sehen."}
FEEDBACK_TEXT = "Falscher Fokus: Mir fehlt oben eine klare Empfehlung, welche Reihenfrage ich nehmen soll."


class NachrichtenTest(unittest.TestCase):
    def snapshot(self, name: str, stuecke, knoepfe=None):
        stuecke = [stuecke] if isinstance(stuecke, str) else stuecke
        for s in stuecke:
            self.assertEqual(re.sub(r"<[^>]*>", "", ERLAUBT.sub("", s)), ERLAUBT.sub("", s), "nur erlaubtes HTML")
        ist = darstellung(stuecke, knoepfe)
        datei = ORDNER / f"{name}.txt"
        if os.environ.get("SNAPSHOTS_NEU") or not datei.exists():
            datei.write_text(ist, encoding="utf-8")
        self.assertEqual(ist, datei.read_text(encoding="utf-8"), f"Snapshot {name} weicht ab")

    # ---------- Jan ----------

    def test_jan_auftrag(self):
        self.snapshot("jan_bestaetigung", logik.bestaetigung("uni", "lernen", ["Transkript_20-10-26.pdf"]))
        a = {"id": AID, "agent": "dokumente", "status": "fehlgeschlagen", "text": "Zusammenfassung"}
        self.snapshot("jan_fehler_ohne_grund", logik.auftrag_nachricht(a))
        self.snapshot("jan_fehler_mit_grund", logik.auftrag_nachricht(
            {**a, "ergebnis": "Fehler im Agenten (RenderFehler): Vorlage fehlt\nDetails: dokumente/logs/dokumente.log"}))

    def test_jan_entwurf(self):
        self.snapshot("jan_entwurf_mail", logik.entwurf_als_text(ENTWURF), FREIGABE_KNOEPFE)
        self.snapshot("jan_entwurf_mail_verlauf", logik.entwurf_als_text(ENTWURF_VERLAUF), FREIGABE_KNOEPFE)
        self.snapshot("jan_entwurf_mail_frage", logik.entwurf_als_text(ENTWURF_FRAGE), FREIGABE_KNOEPFE)
        lang = logik.entwurf_als_text(ENTWURF_LANG)
        self.assertGreater(len(lang), 1)
        self.assertTrue(all(len(s) <= logik.MAX_LAENGE for s in lang))
        self.snapshot("jan_entwurf_mail_lang", lang, FREIGABE_KNOEPFE)

    def test_jan_hinweise(self):
        a = {"id": AID, "agent": "dokumente", "von": "uni"}
        self.snapshot("jan_weitergabe", logik.weitergabe_text(a, False))
        self.snapshot("jan_rechenzeit_leer", logik.stufe_text("normal", "limit", ZEIT, zeit_text))
        self.snapshot("jan_rechenzeit_frei", logik.stufe_text("limit", "normal", ZEIT, zeit_text))
        self.snapshot("jan_stoerung", ausfall.KOPF + ausfall.text("uni-transkript.service", "oom-kill"))

    def test_jan_menue(self):
        stand = {"5h": 0.06, "7d": 0.01, **ZEIT}
        self.snapshot("jan_menue", *logik.ansicht_home(logik.home_zeilen(stand, "normal", 1, 0, 2), ["uni", "dokumente"], 1))
        self.snapshot("jan_menue_sparen", *logik.ansicht_home(logik.home_zeilen(stand, "sparen", 0, 1, 0), ["uni"], 0))
        self.snapshot("jan_menue_agent", *logik.ansicht_agent("uni", "erledigen"))
        self.snapshot("jan_menue_entwuerfe", *logik.ansicht_entwuerfe([ENTWURF]))
        heute = {"uni": {"laeufe": 3, "tokens": 120_000, "minuten": 4.2, "fehler": 0},
                 "lia/recherche": {"laeufe": 1, "tokens": 48_000, "minuten": 1.5, "fehler": 1}}
        self.snapshot("jan_menue_verbrauch", *logik.ansicht_text("Verbrauch", logik.verbrauch_text(
            stand, "sparen", heute, zeit_text)))

    def test_jan_hilfe_und_status(self):
        self.snapshot("jan_hilfe", logik.hilfe_text(logik.AGENTEN))
        self.snapshot("jan_status", logik.status_text({"offen": 1, "ausfuehrung": 0, "unklar": 0, "auftraege": 2,
                                                       "am_pc": 0, "dateien": 1}))

    def test_jan_antworten(self):
        self.snapshot("jan_hinweise", [
            logik.freigabe_antwort("freigegeben", "uni"), logik.freigabe_antwort("abgelehnt", "uni"),
            logik.freigabe_antwort("aendern", "uni"),
            logik.freigabe_fehler("20261027-112951-uni-e7a60a: Entwurf weicht von der Anzeige ab, nicht freigegeben"),
            logik.freigabe_fehler("20261027-112951-uni-e7a60a ist nicht (mehr) offen"), logik.freigabe_fehler("?"),
            logik.aenderung_weiter("uni", 1), logik.dateien_warten(2, "/uni Fasse das zusammen", True),
            logik.dateien_verworfen(2), logik.dateien_verworfen(0), logik.NICHT_ANGELEGT, logik.DATEI_ZU_GROSS,
            logik.DATEI_NICHT_GELADEN, logik.TEXT_WEG, logik.KNOPF_ALT, logik.AN_WEN])
        self.snapshot("jan_unklar", logik.mit_absender("uni", logik.unklar_text(
            "Mail: AW: Anfrage Betreuung Forschungsprojekt")))
        self.snapshot("jan_datei_fehlt", logik.mit_absender("dokumente", logik.datei_nicht_gesendet(
            "data/ausgabe/x/Zusammenfassung_Gebrauchsklassen.pdf")))

    def test_jan_feedback(self):
        text, knoepfe = fb.zusammenfassung("Lia", "recherche", FEEDBACK_TEXT, FEEDBACK_REGEL, True, "")
        self.snapshot("jan_feedback_regel", logik.mit_absender("feedback", text),
                      logik.meldung_knoepfe({"id": AID, "knoepfe": knoepfe}))
        nb = {"art": "nachbesserung", "ziel": "", "auftrag": "Setz die Empfehlung ganz nach oben.", "heikel": False,
              "zusammenfassung": "Lia will die Empfehlung in diesem Ergebnis oben sehen."}
        text, knoepfe = fb.zusammenfassung("Lia", "recherche", FEEDBACK_TEXT, nb, False,
                                           fb.entscheiden(nb, fb.Lage(dienst_da=True))[1])
        self.snapshot("jan_feedback_vorschlag", logik.mit_absender("feedback", text),
                      logik.meldung_knoepfe({"id": AID, "knoepfe": knoepfe}))

    # ---------- Lia ----------

    def test_lia_menue(self):
        self.snapshot("lia_menue", *p.ansicht_home(1, 3, p.hinweis_dateien(1)))
        self.snapshot("lia_menue_material", *p.ansicht_anleitung("material"))
        self.snapshot("lia_menue_frage", *p.ansicht_anleitung("frage"))
        self.snapshot("lia_menue_bestaetigen", *p.ansicht_bestaetigen(
            {"art": "material", "text": "Arbeitsblatt kategorischer Imperativ, Klasse 10, 45 min"}, 1))
        self.snapshot("lia_menue_einordnen", *p.ansicht_einordnen("Kannst du mir einen Fall zu Strafe für Klasse 8 machen?"))
        self.snapshot("lia_menue_dateien", *p.ansicht_dateien(2))
        auftraege = [{"id": "20261022-232618-unterricht-67ba47", "text": "meine formatvorlage darauf anwenden",
                      "status": "fehlgeschlagen", "quelle": "portal-material"},
                     {"id": "20261027-160000-unterricht-aaaaaa", "text": "Fallsuche Strafe Klasse 8",
                      "status": "neu", "quelle": "portal-frage"}]
        self.snapshot("lia_menue_anfragen", *p.ansicht_anfragen(auftraege))
        self.snapshot("lia_menue_hilfe", *p.ansicht_hilfe())
        self.snapshot("lia_menue_feedback", *p.ansicht_feedback("fokus"))

    def test_lia_hinweise(self):
        self.snapshot("lia_hinweise", [p.unterwegs("Arbeitsblatt kategorischer Imperativ, Klasse 10, 45 min", 1),
                                       p.verworfen(2), p.ZU_GROSS, p.NICHT_GELADEN, p.SPRACHNACHRICHT, p.KNOPF_ALT,
                                       p.ABGEBROCHEN, p.FEHLGESCHLAGEN])

    def test_lia_ergebnis_und_dateien(self):
        a = {"id": AID, "agent": "unterricht", "status": "fehlgeschlagen", "text": "meine formatvorlage darauf anwenden"}
        self.snapshot("lia_fehler_ohne_grund", p.ergebnis_nachricht(a), p.ergebnis_knoepfe(a))
        self.snapshot("lia_dateien_ok", p.dateien_text(2, True))
        self.snapshot("lia_dateien_fehler", p.dateien_text(2, False))

    def test_lia_feedback(self):
        for name, z, uebernommen in (
                ("vorschlag", FEEDBACK_REGEL, False),
                ("nachbesserung", {"art": "nachbesserung"}, True),
                ("notiz", {"art": "notiz"}, True)):
            a = {"id": "20261027-161900-feedback-abcdef", "agent": "feedback", "status": "erledigt",
                 "text": FEEDBACK_TEXT, "ergebnis": fb.bestaetigung(z, uebernommen)}
            self.snapshot(f"lia_feedback_{name}", p.ergebnis_nachricht(a), p.ergebnis_knoepfe(a))
        fall = {"feedback": FEEDBACK_TEXT, "zuordnung": FEEDBACK_REGEL}
        self.snapshot("lia_feedback_gestoppt", fb.stopp_text(fall, "Das gilt also nicht mehr."))
        self.snapshot("lia_feedback_entschieden_ja", fb.entscheidung_text(fall, True))
        self.snapshot("lia_feedback_entschieden_nein", fb.entscheidung_text(fall, False))


if __name__ == "__main__":
    unittest.main()
