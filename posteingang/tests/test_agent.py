import json
from datetime import date
from types import SimpleNamespace
import tempfile
import unittest
from pathlib import Path

from agentkit import claude_lauf
from agentkit.claude_lauf import Ergebnis

import agent


def mail(uid, **kopf):
    return {"uid": uid, "von": f"x{uid}@example.de", "datum": "", "betreff": f"B{uid}", "text": "t",
            "anhaenge": [], "kopf": kopf}


class TestPostPruefen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.offen = Path(self.tmp.name) / "mails_offen.json"
        self.gemeldet, self.prompts = [], []

    def tearDown(self):
        self.tmp.cleanup()

    def pruefen(self, neue, antwort="KEINE", ok=True, fehler=None, gesperrt=()):
        def laufen(name, hier, prompt, **kw):
            self.prompts.append((prompt, kw))
            if fehler:
                raise fehler
            return Ergebnis(antwort, None, ok)
        agent.post_pruefen(holen=lambda: neue, laufen=laufen, melden=self.gemeldet.append,
                           gesperrt=lambda: list(gesperrt), offen_datei=self.offen)

    def test_keine_mails_nichts_tun(self):
        self.pruefen([])
        self.assertEqual(self.prompts, [])
        self.assertFalse(self.offen.exists())

    def test_wichtige_mail_gemeldet(self):
        self.pruefen([mail(1), mail(2, **{"list-unsubscribe": "<x>"})], antwort="- Persönlich | x1: B1. Antworten")
        self.assertEqual(len(self.prompts), 1)
        prompt, kw = self.prompts[0]
        self.assertIn("uid 1", prompt)
        self.assertNotIn("uid 2", prompt)
        self.assertEqual(kw, {"art": "routine", "zeitgesteuert": True})
        self.assertEqual(self.gemeldet, ["[post] Wichtige Mails (1 geprüft, 1 vorgefiltert):\n- Persönlich | x1: B1. Antworten"])
        self.assertFalse(self.offen.exists())

    def test_keine_nichts_melden(self):
        self.pruefen([mail(1)])
        self.assertEqual(self.gemeldet, [])
        self.assertFalse(self.offen.exists())

    def test_alle_vorgefiltert_ohne_claude(self):
        self.pruefen([mail(1, precedence="bulk"), mail(2)], gesperrt=["x2@example.de"])
        self.assertEqual(self.prompts, [])
        self.assertEqual(self.gemeldet, [])
        self.assertFalse(self.offen.exists())

    def test_warten_mails_bleiben_offen(self):
        self.pruefen([mail(1)], fehler=claude_lauf.LimitErreicht(None))
        self.assertEqual([m["uid"] for m in json.loads(self.offen.read_text())], [1])
        # nächster Lauf nimmt die offenen und die neuen
        self.prompts.clear()
        self.pruefen([mail(2)], antwort="- Termin | x2: B2")
        self.assertIn("uid 1", self.prompts[0][0])
        self.assertIn("uid 2", self.prompts[0][0])
        self.assertIn("2 geprüft", self.gemeldet[0])
        self.assertFalse(self.offen.exists())

    def test_fehlgeschlagener_lauf_wirft_und_behaelt(self):
        with self.assertRaises(claude_lauf.LaufFehler):
            self.pruefen([mail(1)], antwort="kaputt", ok=False)
        self.assertTrue(self.offen.exists())
        self.assertEqual(self.gemeldet, [])


class TestSchrittFehler(unittest.TestCase):
    def test_einmal_am_tag(self):
        with tempfile.TemporaryDirectory() as d:
            datei, gemeldet = Path(d) / "f.json", []
            f = RuntimeError("weg")
            self.assertTrue(agent.schritt_fehler_melden("post_pruefen", f, "2026-10-27", datei, gemeldet.append))
            self.assertFalse(agent.schritt_fehler_melden("post_pruefen", f, "2026-10-27", datei, gemeldet.append))
            self.assertTrue(agent.schritt_fehler_melden("post_pruefen", f, "2026-10-28", datei, gemeldet.append))
            self.assertEqual(len(gemeldet), 2)
            self.assertIn("RuntimeError: weg", gemeldet[0])


if __name__ == "__main__":
    unittest.main()


class MailFehler(Exception):
    pass


def falsches_mail_modul():
    """Ersatz für agentkit.mail (Bedarf Nr. 19b), nur was agent.py braucht."""
    def pruefen(roh, original=None):
        if not roh.get("an"):
            raise MailFehler("an: mindestens ein Empfänger nötig")
        daten = {"an": roh["an"], "cc": [], "betreff": roh["betreff"], "text": roh["text"]}
        if original:
            daten.update(in_reply_to=original["message_id"], antwort_auf=original["betreff"])
        return daten
    return SimpleNamespace(pruefen=pruefen, anzeige=lambda d: f"An: {d['an']}\n{d['text']}", MailFehler=MailFehler)


SUCHE = '{"personen": ["Oppenheimer"], "stichworte": ["Paarberatung"], "tage_zurueck": 365, "kalender_tage": 14}'
ENTWURF = ('{"entwurf": {"an": ["o@praxis.de"], "betreff": "Re: Termin", "text": "Liebe Frau Oppenheimer, ...", '
           '"antwort_auf": "m1", "begruendung": "Adresse aus m1"}}')


class TestMailAuftrag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ablage = Path(self.tmp.name) / "auftraege"
        self.entwuerfe = Path(self.tmp.name) / "entwuerfe.json"
        self.alt_mail, agent.mail = agent.mail, falsches_mail_modul()
        self.alt_cfg, agent._cfg = agent._cfg, lambda: {}
        self.fertig, self.freigabe, self.prompts = [], [], []

    def tearDown(self):
        agent.mail, agent._cfg = self.alt_mail, self.alt_cfg
        self.tmp.cleanup()

    def laufen(self, *antworten, fehler=None):
        antworten = list(antworten)

        def lauf(name, hier, prompt, **kw):
            self.prompts.append((prompt, kw))
            if fehler:
                raise fehler
            return Ergebnis(antworten.pop(0), "s1", True)
        return lauf

    def einreichen(self, antwort, kontext, auftrag_id, vorgaenger=None):
        def neuer_entwurf(agent_name, **kw):
            self.freigabe.append(kw)
            return f"F{len(self.freigabe)}"
        return agent.entwurf_einreichen(antwort, kontext, auftrag_id, vorgaenger=vorgaenger,
                                        neuer_entwurf=neuer_entwurf, entwuerfe=self.entwuerfe)

    def auftrag(self, a, *antworten, suchen=None):
        treffer = [{"uid": 3, "ordner": "INBOX", "von": "Oppenheimer <o@praxis.de>", "datum": "2026-10-01",
                    "betreff": "Termin", "message_id": "<m3@praxis>", "wortlaut": "Bis nächste Woche"}]
        return agent.mail_auftrag(a, laufen=self.laufen(*antworten),
                                  suchen=suchen or (lambda ordner, **kw: treffer if ordner == "INBOX" else []),
                                  termine=lambda von, bis: [], heute=date(2026, 10, 27), ablage=self.ablage,
                                  einreichen=self.einreichen, fertig=lambda a, t, ok, s=None: self.fertig.append((t, ok)))

    def test_entwurf_in_freigabe(self):
        self.assertTrue(self.auftrag({"id": "A1", "text": "Termin absagen"}, SUCHE, ENTWURF))
        self.assertEqual(self.fertig, [("Entwurf an o@praxis.de liegt zur Freigabe.", True)])
        f = self.freigabe[0]
        self.assertEqual((f["typ"], f["titel"]), ("mail", "Mail: Re: Termin"))
        self.assertEqual(f["daten"]["in_reply_to"], "<m3@praxis>")
        self.assertEqual([kw["art"] for _, kw in self.prompts], ["routine", "anspruchsvoll"])
        self.assertIn("--- m1\nOrdner: INBOX\nVon: Oppenheimer <o@praxis.de>", self.prompts[1][0])
        self.assertTrue((self.ablage / "A1" / "kontext.json").exists())
        self.assertEqual(json.loads(self.entwuerfe.read_text()), {"F1": "A1"})

    def test_rueckfrage_und_nachtrag(self):
        self.auftrag({"id": "A1", "text": "Termin absagen"}, SUCHE, '{"rueckfrage": "Welche Adresse?"}')
        self.assertTrue(self.fertig[0][0].startswith("Welche Adresse?"))
        self.assertEqual(self.freigabe, [])
        self.auftrag({"id": "A2", "text": "o@praxis.de", "bezug": "A1"}, SUCHE, ENTWURF)
        self.assertIn("Termin absagen\n\nNachtrag von Jan: o@praxis.de", self.prompts[2][0])
        self.assertEqual(len(self.freigabe), 1)

    def test_ungueltiger_entwurf_wird_gemeldet(self):
        self.auftrag({"id": "A1", "text": "x"}, SUCHE, '{"entwurf": {"an": [], "betreff": "b", "text": "t"}}')
        self.assertEqual(self.fertig, [("Kein Entwurf möglich: an: mindestens ein Empfänger nötig", False)])
        self.assertEqual(self.freigabe, [])

    def test_claude_wartet(self):
        lauf = self.laufen(fehler=claude_lauf.LimitErreicht(None))
        self.assertFalse(agent.mail_auftrag({"id": "A1", "text": "x"}, laufen=lauf, suchen=None, termine=None,
                                            ablage=self.ablage, fertig=lambda *x: self.fertig.append(x)))
        self.assertEqual(self.fertig, [])

    def test_aendern_mit_gespeichertem_kontext(self):
        self.auftrag({"id": "A1", "text": "Termin absagen"}, SUCHE, ENTWURF)
        alt = {"id": "F1", "typ": "mail", "daten": {**self.freigabe[0]["daten"]}}
        neu = '{"entwurf": {"an": ["o@praxis.de"], "betreff": "Termin", "text": "Kürzer", "antwort_auf": null}}'
        agent.aenderung({"id": "A2", "text": "kürzer", "bezug": "F1", "quelle": "telegram-aendern"},
                        laufen=self.laufen(neu), heute=date(2026, 10, 27), ablage=self.ablage,
                        entwuerfe=self.entwuerfe, holen=lambda eid: alt if eid == "F1" else None,
                        einreichen=self.einreichen, fertig=lambda a, t, ok, s=None: self.fertig.append((t, ok)))
        f = self.freigabe[1]
        self.assertEqual(f["vorgaenger"], "F1")
        self.assertEqual(f["daten"]["in_reply_to"], "<m3@praxis>")  # Bezug der alten Mail bleibt
        self.assertIn("kürzer", self.prompts[-1][0])
        self.assertEqual(json.loads(self.entwuerfe.read_text()), {"F1": "A1", "F2": "A1"})

    def test_aendern_ohne_kontext(self):
        agent.aenderung({"id": "A2", "text": "kürzer", "bezug": "F9"}, laufen=None, ablage=self.ablage,
                        entwuerfe=self.entwuerfe, holen=lambda eid: None,
                        fertig=lambda a, t, ok, s=None: self.fertig.append((t, ok)))
        self.assertFalse(self.fertig[0][1])

    def test_ohne_bausteine_abgelehnt(self):
        agent.mail = None
        gesendet = []
        alt, agent._fertig = agent._fertig, lambda a, t, ok, s=None: gesendet.append((t, ok))
        try:
            self.assertTrue(agent.auftrag_bearbeiten({"id": "A1", "text": "x"}))
        finally:
            agent._fertig = alt
        self.assertIn("agentkit.mail", gesendet[0][0])
        self.assertFalse(gesendet[0][1])
