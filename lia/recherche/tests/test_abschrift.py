import unittest

import abschrift

# Echte OCR (Toronto-Scan, ZStW 3, S. 2) und meine Lesung vom Bild. Kalibrierung: STATUS.md.
OCR_S2 = """(Ss  war  bal)er  eitel  Selbfttäufdjung,  roenn  mandje,  rote  £(). 9t
©djüfce  (1874),  bie  Erörterung  jener  fragen  aus  ben  Sefjrbüdjern
bes  ©trafrecfjts  verbannen  gu  bürfen  glaubten.  £>ie  ©efd)icf)te  bes
©trafredjts  fann  nidjt  oerftanben,  bas  geltenbe  9?ed)t  nid)t  gewürbigt,
bie  SRidjtung  feiner  SBeiterbilbung  nid)t  beftimmt  werben,  wenn  bie
Xriebfebern  aller  ©ntwidtung  bes  ©trafredjts  verborgen  bleiben."""
LESUNG = ("Die Geschichte des Strafrechts kann nicht verstanden, das geltende Recht nicht gewürdigt, "
           "die Richtung seiner Weiterbildung nicht bestimmt werden, wenn die Triebfedern aller "
           "Entwicklung des Strafrechts verborgen bleiben.")
ANDERE_SEITE = """Der  (Srforfdjung  b eö  $erbred)cns  als  fojialset^ifdjer ßrf<$einung,  ber  ©träfe  als
gefettfd)aftlid>er  gunftion, rnujj  innerhalb  isnfrev  S9B iffenf diaft  bie  ujr  gebüljrenbe  23e= adjtung
werben.  DaJ3  e$  eine  SMminatantljropotogie,  eine  Kriminalpsychologie  gibt."""


class AehnlichkeitTest(unittest.TestCase):
    def test_richtige_seite_ueber_schwelle(self):
        self.assertGreaterEqual(abschrift.aehnlichkeit(LESUNG, OCR_S2), abschrift.SCHWELLE)

    def test_falsche_seite_unter_schwelle(self):
        self.assertLess(abschrift.aehnlichkeit(LESUNG, ANDERE_SEITE), abschrift.SCHWELLE)

    def test_angleichen_fraktur(self):
        self.assertEqual(abschrift.angleichen("unb ber ©träfe"), abschrift.angleichen("und der Strafe"))
        self.assertEqual(abschrift.angleichen("menfd)lid)er"), abschrift.angleichen("menschlicher"))
        self.assertEqual(abschrift.angleichen("Aus=\nführung"), abschrift.angleichen("Ausführung"))

    def test_ueber_seitengrenze(self):
        vorn, hinten = OCR_S2.split("glaubten.")
        ganz = abschrift.aehnlichkeit_seiten(LESUNG, [vorn + "glaubten. FUSSNOTE und Seitenkopf " * 3, hinten])
        self.assertGreaterEqual(ganz, abschrift.SCHWELLE)
        self.assertEqual(abschrift.aehnlichkeit_seiten(LESUNG, [OCR_S2]), abschrift.aehnlichkeit(LESUNG, OCR_S2))
        self.assertLess(abschrift.aehnlichkeit_seiten(LESUNG, [ANDERE_SEITE, ANDERE_SEITE]), abschrift.SCHWELLE)

    def test_leer(self):
        self.assertEqual(abschrift.aehnlichkeit("", OCR_S2), 0.0)
        self.assertEqual(abschrift.aehnlichkeit("kurz", ""), 0.0)


class VergleichenTest(unittest.TestCase):
    def test_zwei_gleich_ohne_leerraum_unterschied(self):
        text, unterschiede = abschrift.vergleichen(["Die Strafe ist  Schutz.", "Die Strafe ist Schutz."])
        self.assertEqual((text, unterschiede), ("Die Strafe ist  Schutz.", []))

    def test_ungleich_ohne_dritte(self):
        text, unterschiede = abschrift.vergleichen(["Die Strafe ist Schutz.", "Die Strafe ist Rache."])
        self.assertIsNone(text)
        self.assertEqual(unterschiede, ["Schutz. / Rache."])

    def test_dritte_entscheidet(self):
        text, unterschiede = abschrift.vergleichen(["Strafe ist Schutz.", "Strafe ist Rache.", "Strafe ist Schutz."])
        self.assertEqual(text, "Strafe ist Schutz.")
        self.assertTrue(unterschiede)
        self.assertEqual(abschrift.vergleichen(["a b", "a c", "a b"])[0], "a b")
        self.assertEqual(abschrift.vergleichen(["a b", "a c", "a c"])[0], "a c")
        self.assertIsNone(abschrift.vergleichen(["a b", "a c", "a d"])[0])

    def test_unleserlich(self):
        text, unterschiede = abschrift.vergleichen(["Die [?] ist", "Die [?] ist"])
        self.assertIsNone(text)
        self.assertIn("[?]", unterschiede[0])


if __name__ == "__main__":
    unittest.main()
