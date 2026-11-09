"""Tests für die EPO-Anbindung (ohne Netz): Suche bauen, Token, Auszug, keine Treffer, Drosselgrenze."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ablauf
import abrufer
import agent
import quellen
from agentkit import abruf

# Gekürzt nach einer echten OPS-Antwort vom 09.11.2026
BIBLIO = """<?xml version="1.0" encoding="UTF-8"?>
<ops:world-patent-data xmlns="http://www.epo.org/exchange" xmlns:ops="http://ops.epo.org">
 <ops:biblio-search total-result-count="192">
  <ops:query syntax="CQL">(ta = timber and cpc = B27) and pd within "2022 2024"</ops:query>
  <ops:search-result><exchange-documents>
   <exchange-document family-id="93947440" country="CN" doc-number="119217474" kind="A">
    <bibliographic-data>
     <publication-reference>
      <document-id document-id-type="docdb"><country>CN</country><doc-number>119217474</doc-number>
       <kind>A</kind><date>20241231</date></document-id>
     </publication-reference>
     <patent-classifications>
      <patent-classification><section>B</section><class>27</class><subclass>B</subclass>
       <main-group>31</main-group><subgroup>006</subgroup></patent-classification>
      <patent-classification><section>B</section><class>27</class><subclass>B</subclass>
       <main-group>31</main-group><subgroup>006</subgroup></patent-classification>
     </patent-classifications>
     <parties><applicants>
      <applicant data-format="epodoc"><applicant-name><name>SICHUAN QINGCHENG MACHINERY CO LTD</name></applicant-name></applicant>
      <applicant data-format="original"><applicant-name><name>四川省青城机械有限公司</name></applicant-name></applicant>
     </applicants></parties>
     <invention-title lang="en">Timber segmentation method based on machine vision</invention-title>
     <invention-title lang="ol">一种基于机器视觉的木料分割方法</invention-title>
    </bibliographic-data>
   </exchange-document>
  </exchange-documents></ops:search-result>
 </ops:biblio-search>
</ops:world-patent-data>""".encode()

SCHLUESSEL = {"EPO_OPS_KEY": "key-geheim", "EPO_OPS_SECRET": "secret-geheim", "EPO_TOKEN": "tok-geheim"}


class Suche(unittest.TestCase):
    def test_cql_aus_geprueften_teilen(self):
        q = abrufer.epo_cql({"begriffe": "timber drying", "anmelder": "Weinig", "cpc": "B27B31/006",
                             "land": "EP", "von_jahr": 2020, "bis_jahr": 2024})
        self.assertEqual(q, 'ta="timber drying" and pa="Weinig" and cpc="B27B31/006" and pn=EP '
                            'and pd within "2020 2024"')

    def test_ausbruch_und_falsche_angaben(self):
        for falsch in ({"begriffe": 'wood" or ta="x'}, {"cpc": "B27B or 1"}, {"cpc": "Z99"},
                       {"begriffe": "wood", "land": "DEU"}, {"land": "EP"}, {},
                       {"begriffe": "wood", "von_jahr": 2024, "bis_jahr": 2020}):
            with self.assertRaises(abrufer.AbfrageFehler, msg=falsch):
                abrufer.epo_cql(falsch)

    def test_anfrage_mit_token_nur_im_header(self):
        a = abrufer.anfrage_bauen({"art": "epo", "beschreibung": "x", "cpc": "B27B"}, SCHLUESSEL)
        self.assertTrue(a.url.startswith(abrufer.EPO_SUCHE))
        self.assertIn("Range=1-25", a.url)
        self.assertEqual(a.header["Authorization"], "Bearer tok-geheim")
        self.assertNotIn("geheim", a.url + a.quelle_url)

    def test_ohne_token(self):
        with self.assertRaisesRegex(abrufer.AbfrageFehler, "EPO_TOKEN"):
            abrufer.anfrage_bauen({"art": "epo", "beschreibung": "x", "cpc": "B27B"}, {})

    def test_token_anfrage_und_antwort(self):
        a = abrufer.epo_token_anfrage(SCHLUESSEL)
        self.assertEqual((a.methode, a.url), ("POST", abrufer.EPO_TOKEN_URL))
        self.assertTrue(a.header["Authorization"].startswith("Basic "))
        self.assertEqual(abrufer.epo_token_lesen(b'{"access_token": "t1", "status": "approved"}'), "t1")
        with self.assertRaises(abrufer.AbfrageFehler):
            abrufer.epo_token_lesen(b'{"status": "revoked"}')
        with self.assertRaisesRegex(abrufer.AbfrageFehler, "EPO_OPS_SECRET"):
            abrufer.epo_token_anfrage({"EPO_OPS_KEY": "k"})


class Auszug(unittest.TestCase):
    def test_auszug(self):
        roh, endung = abrufer.antwort_pruefen("epo", BIBLIO, "application/xml")
        d = json.loads(roh)
        self.assertEqual((endung, d["treffer_gesamt"]), ("json", 192))
        v = d["veroeffentlichungen"][0]
        self.assertEqual(v["nummer"], "CN119217474A")
        self.assertEqual(v["veroeffentlicht"], "2024-12-31")
        self.assertEqual(v["titel"], "Timber segmentation method based on machine vision")
        self.assertEqual(v["anmelder"], ["SICHUAN QINGCHENG MACHINERY CO LTD"])
        self.assertEqual(v["cpc"], ["B27B31/006"])

    def test_keine_daten(self):
        for falsch in (b"<html>", b'<a xmlns:ops="http://ops.epo.org"/>', b"{}"):
            with self.assertRaises(abrufer.AbfrageFehler):
                abrufer.antwort_pruefen("epo", falsch, "application/xml")

    def test_drosselgrenze(self):
        liste, fehler = abrufer.abfragen_lesen({"abfragen": [{"art": "epo"}] * 6 + [{"art": "ted"}]})
        self.assertEqual([a["art"] for a in liste], ["epo"] * abrufer.MAX_EPO + ["ted"])
        self.assertTrue(any("EPO" in f for f in fehler))


class Laden:
    """Erst Token, dann Suche (oder Fehler bei der Suche)."""

    def __init__(self, suche=BIBLIO, fehler=None):
        self.suche, self.fehler, self.aufrufe = suche, fehler, []

    def __call__(self, url, **kw):
        self.aufrufe.append((url, kw))
        if url == abrufer.EPO_TOKEN_URL:
            return abruf.Ergebnis(b'{"access_token": "tok-geheim", "status": "approved"}',
                                  {"content_type": "application/json"}, aus_cache=False)
        if self.fehler:
            raise abruf.AbrufFehler(self.fehler)
        return abruf.Ergebnis(self.suche, {"content_type": "application/xml"}, aus_cache=False)


class Agent(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.quellen = Path(self.tmp.name) / "quellen"
        self.cache = Path(self.tmp.name) / "cache"
        patch = mock.patch.multiple(agent, QUELLEN=self.quellen, CACHE=self.cache, logger=mock.DEFAULT,
                                    cfg={"EPO_OPS_KEY": "key-geheim", "EPO_OPS_SECRET": "secret-geheim"},
                                    _epo={"token": None, "bis": 0.0})
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def abfrage(self, **kw):
        return {"art": "epo", "begriffe": "timber", "cpc": "B27", "beschreibung": "Patente Holz", **kw}

    def test_abgelegt_ohne_geheimnisse_token_nicht_im_cache(self):
        laden = Laden()
        qid = agent.abrufen(self.abfrage(), _laden=laden)
        token_kw = laden.aufrufe[0][1]
        self.assertNotEqual(Path(token_kw["cache_dir"]), self.cache)
        self.assertFalse(Path(token_kw["cache_dir"]).exists())  # Wegwerf-Cache ist weg
        self.assertEqual(laden.aufrufe[1][1]["header"]["Authorization"], "Bearer tok-geheim")
        meta = quellen.meta(self.quellen, qid)
        self.assertEqual(meta["art"], "epo")
        alles = "".join(p.read_text(errors="ignore") for p in self.quellen.rglob("*") if p.is_file())
        self.assertNotIn("geheim", alles)
        self.assertIn("192", alles)

    def test_token_wird_wiederverwendet(self):
        laden = Laden()
        agent.abrufen(self.abfrage(), _laden=laden)
        agent.abrufen(self.abfrage(von_jahr=2020), _laden=laden)
        self.assertEqual([u for u, _ in laden.aufrufe].count(abrufer.EPO_TOKEN_URL), 1)

    def test_keine_treffer_ist_beleg(self):
        qid = agent.abrufen(self.abfrage(), _laden=Laden(fehler="HTTP-Fehler 404 (Not Found) bei https://..."))
        self.assertTrue(quellen.ist_id(qid))

    def test_andere_fehler_gehen_an_claude(self):
        with self.assertRaisesRegex(ablauf.WebFehler, "403"):
            agent.abrufen(self.abfrage(), _laden=Laden(fehler="HTTP-Fehler 403 (Forbidden) bei https://..."))

    def test_falsche_abfrage_holt_keinen_token(self):
        laden = Laden()
        with self.assertRaises(abrufer.AbfrageFehler):
            agent.abrufen({"art": "epo", "beschreibung": "x"}, _laden=laden)
        self.assertEqual(laden.aufrufe, [])


if __name__ == "__main__":
    unittest.main()
