"""Datensätze bauen und prüfen (reine Logik ohne Netz, getestet). Noch leer.

Geplant:
- Annotationen der Quelle (zuerst Kodytek et al., Zenodo 10.5281/zenodo.4694695) ins YOLO-Format umwandeln:
  je Bild eine .txt mit "klasse x_mitte y_mitte breite hoehe", Werte relativ zur Bildgröße (0..1).
  Vorher das Box-Format der Quelle an echten Bildern prüfen: Das Paper beschreibt Reihenfolge der Ecken und
  „durch 100 geteilt“ widersprüchlich.
- Prüfen: Box im Bild, Breite und Höhe > 0, Klasse bekannt, zu jedem Bild eine Annotation (leer = ohne Fehler).
- Aufteilen in train/val/test, fest gesetzter Zufall, je Klasse möglichst gleich verteilt (Klassen sehr ungleich).
- Ziel: data/datensaetze/<name>-<version>/ mit data.yaml und Zählung je Klasse und Teil.
"""
