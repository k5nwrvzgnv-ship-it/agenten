"""Tests für abrufer.py (ohne Netz): Abfragen prüfen, Anfragen bauen, Antworten prüfen."""

import io
import json
import unittest
import zipfile

import abrufer

SCHLUESSEL = {"GENESIS_TOKEN": "geheim-g", "COMTRADE_KEY": "geheim-c"}


def bauen(**abfrage):
    return abrufer.anfrage_bauen({"beschreibung": "Test", **abfrage}, SCHLUESSEL)


class AnfrageBauen(unittest.TestCase):
    def test_genesis_post_mit_token_im_header_nicht_in_url(self):
        a = bauen(art="genesis", tabelle="42111-0001", von_jahr=2020, bis_jahr=2024)
        self.assertEqual((a.methode, a.url), ("POST", abrufer.GENESIS))
        self.assertEqual(a.header["username"], "geheim-g")
        self.assertIn(b"name=42111-0001", a.daten)
        self.assertIn(b"startyear=2020", a.daten)
        self.assertIn("name=42111-0001", a.quelle_url)
        self.assertNotIn("geheim", a.quelle_url + a.daten.decode())

    def test_genesis_tabellencode_streng(self):
        for falsch in ("42111", "42111-0001&x=1", "../a", 42111):
            with self.assertRaises(abrufer.AbfrageFehler):
                bauen(art="genesis", tabelle=falsch)

    def test_comtrade_eine_zeile_je_abfrage(self):
        a = bauen(art="comtrade", melder=276, partner=0, jahr=2024, hs="847950", richtung="X")
        for teil in ("reporterCode=276", "cmdCode=847950", "partner2Code=0", "customsCode=C00", "motCode=0"):
            self.assertIn(teil, a.url)
        self.assertEqual(a.header, {"Ocp-Apim-Subscription-Key": "geheim-c"})
        self.assertNotIn("geheim", a.url)

    def test_comtrade_falsche_angaben(self):
        with self.assertRaises(abrufer.AbfrageFehler):
            bauen(art="comtrade", melder=276, jahr=2024, hs="8479", richtung="export")
        with self.assertRaises(abrufer.AbfrageFehler):
            bauen(art="comtrade", melder=276, jahr=2024, hs="847", richtung="X")

    def test_schluessel_fehlt(self):
        with self.assertRaisesRegex(abrufer.AbfrageFehler, "COMTRADE_KEY"):
            abrufer.anfrage_bauen({"art": "comtrade", "beschreibung": "x", "melder": 276, "jahr": 2024,
                                   "hs": "8479", "richtung": "M"}, {})

    def test_ted_query_nur_aus_geprueften_teilen(self):
        a = bauen(art="ted", cpv="42997300", von="2025-01-01", land="DEU")
        q = json.loads(a.daten)["query"]
        self.assertEqual(q, "classification-cpv=42997300 AND publication-date>=20250101 AND buyer-country=DEU")
        with self.assertRaises(abrufer.AbfrageFehler):
            bauen(art="ted", cpv="42997300 OR 1", von="2025-01-01")
        with self.assertRaises(abrufer.AbfrageFehler):
            bauen(art="ted", cpv="42997300", von="gestern")

    def test_eurostat_filter_und_jobsuche(self):
        a = bauen(art="eurostat", datensatz="sts_inpr_a", filter={"geo": "DE", "nace_r2": "C16"}, von_jahr=2020)
        self.assertTrue(a.url.startswith(abrufer.EUROSTAT + "sts_inpr_a?"))
        self.assertIn("geo=DE", a.url)
        with self.assertRaises(abrufer.AbfrageFehler):
            bauen(art="eurostat", datensatz="sts_inpr_a", filter={"geo": "DE&x"})
        j = bauen(art="jobsuche", was="Robotik Holz", wo="Bayern")
        self.assertIn("was=Robotik+Holz", j.url)
        self.assertEqual(j.header["X-API-Key"], abrufer.JOBSUCHE_KEY)

    def test_unbekannte_art_und_ohne_beschreibung(self):
        with self.assertRaises(abrufer.AbfrageFehler):
            bauen(art="bundesanzeiger")
        with self.assertRaises(abrufer.AbfrageFehler):
            abrufer.anfrage_bauen({"art": "jobsuche", "was": "Robotik"}, SCHLUESSEL)


class AntwortPruefen(unittest.TestCase):
    def test_genesis_zip_wird_zu_csv(self):
        puffer = io.BytesIO()
        with zipfile.ZipFile(puffer, "w") as z:
            z.writestr("42111-0001_de_flat.csv", "a;b\n1;2\n")
        roh, endung = abrufer.antwort_pruefen("genesis", puffer.getvalue(), "application/zip")
        self.assertEqual((roh, endung), (b"a;b\n1;2\n", "csv"))

    def test_genesis_fehler_als_json(self):
        antwort = json.dumps({"Status": {"Code": 104, "Content": "Es gibt keine Objekte"}}).encode()
        with self.assertRaisesRegex(abrufer.AbfrageFehler, "keine Objekte"):
            abrufer.antwort_pruefen("genesis", antwort, "application/json")

    def test_leere_daten_sind_fehler(self):
        with self.assertRaises(abrufer.AbfrageFehler):
            abrufer.antwort_pruefen("comtrade", b'{"count": 0, "data": []}', "application/json")
        with self.assertRaises(abrufer.AbfrageFehler):
            abrufer.antwort_pruefen("eurostat", b'{"value": {}}', "application/json")
        with self.assertRaises(abrufer.AbfrageFehler):
            abrufer.antwort_pruefen("ted", b"<html>", "text/html")

    def test_gueltige_json_antwort(self):
        roh = b'{"totalNoticeCount": 722, "notices": []}'
        self.assertEqual(abrufer.antwort_pruefen("ted", roh, "application/json"), (roh, "json"))

    def test_abfragen_lesen_begrenzt(self):
        liste, fehler = abrufer.abfragen_lesen({"abfragen": [{}] * 20})
        self.assertEqual(len(liste), abrufer.MAX_ABFRAGEN)
        self.assertTrue(fehler)
        self.assertEqual(abrufer.abfragen_lesen([])[0], [])



def fakt(wert, ende, start=None, form="10-K", filed="2026-01-31", fp="FY"):
    e = {"end": ende, "val": wert, "form": form, "filed": filed, "fp": fp}
    if start:
        e["start"] = start
    return e


SEC_ANTWORT = {"cik": 1045810, "entityName": "NVIDIA CORP", "facts": {
    "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [fakt(24.3e9, "2026-08-01", form="10-Q"),
                                                                        fakt(24.4e9, "2026-10-01", form="10-Q")]}}},
    "us-gaap": {
        "Revenues": {"units": {"USD": [fakt(60.9e9, "2025-01-26", "2024-01-29")]}},
        "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
            fakt(130.5e9, "2026-01-25", "2025-01-27"),
            fakt(35.1e9, "2025-10-26", "2025-07-28", form="10-Q", fp="Q3"),   # Quartal: nicht
            fakt(129.0e9, "2026-01-25", "2025-01-27", filed="2025-03-01"),    # älter eingereicht: nicht
            fakt(30.0e9, "2025-12-31", "2025-10-01")]}},                      # nur 3 Monate: nicht
        "StockholdersEquity": {"units": {"USD": [fakt(79.3e9, "2026-01-25")]}},
    }}}


class SecUndKurs(unittest.TestCase):
    def test_sec_anfrage(self):
        a = bauen(art="sec", cik=1045810)
        self.assertEqual(a.url, "https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json")
        self.assertEqual(a.allowlist, ["data.sec.gov"])
        self.assertIn("User-Agent", a.header)
        with self.assertRaises(abrufer.AbfrageFehler):
            bauen(art="sec", cik="1045810/../x")

    def test_kurs_anfrage(self):
        self.assertIn("/chart/6954.T?range=5y", bauen(art="kurs", symbol="6954.T").url)
        for falsch in ("nvda", "NV DA", "A/B", ""):
            with self.assertRaises(abrufer.AbfrageFehler):
                bauen(art="kurs", symbol=falsch)

    def test_sec_auszug_jahreswerte(self):
        roh, endung = abrufer.antwort_pruefen("sec", json.dumps(SEC_ANTWORT).encode(), "application/json")
        d = json.loads(roh)
        self.assertEqual(endung, "json")
        umsatz = d["kennzahlen"]["umsatz"]
        self.assertEqual(umsatz["einheit"], "USD")
        self.assertEqual([j["wert"] for j in umsatz["jahre"]], [130.5e9, 60.9e9])  # beide Konzepte, neuestes zuerst
        self.assertEqual(d["kennzahlen"]["eigenkapital"]["jahre"][0]["wert"], 79.3e9)  # Bestandsgröße ohne start
        self.assertEqual(d["kennzahlen"]["ausstehende_aktien"]["wert"], 24.4e9)

    def test_sec_ohne_daten(self):
        with self.assertRaises(abrufer.AbfrageFehler):
            abrufer.antwort_pruefen("sec", b'{"facts": {"us-gaap": {}}}', "application/json")
        with self.assertRaises(abrufer.AbfrageFehler):
            abrufer.antwort_pruefen("sec", b'{"error": "x"}', "application/json")

    def test_kurs_auszug(self):
        antwort = {"chart": {"result": [{"meta": {"symbol": "NVDA", "currency": "USD", "regularMarketPrice": 191.2,
                                                  "regularMarketTime": 1794236676},
                                         "timestamp": [1762000000, 1764600000],
                                         "indicators": {"quote": [{"close": [180.123456, None]}]}}]}}
        d = json.loads(abrufer.antwort_pruefen("kurs", json.dumps(antwort).encode(), "application/json")[0])
        self.assertEqual((d["kurs_aktuell"], d["waehrung"], d["stand"]), (191.2, "USD", "2026-11-09"))
        self.assertEqual(d["monatsschluss"], [{"monat": "2025-11", "schluss": 180.1235}])

    def test_kurs_unbekanntes_symbol(self):
        antwort = b'{"chart": {"result": null, "error": {"description": "No data found"}}}'
        with self.assertRaisesRegex(abrufer.AbfrageFehler, "No data"):
            abrufer.antwort_pruefen("kurs", antwort, "application/json")


if __name__ == "__main__":
    unittest.main()
