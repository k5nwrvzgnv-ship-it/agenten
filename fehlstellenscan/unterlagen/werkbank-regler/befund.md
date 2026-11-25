# Werkbank mit Bedienfeld (25.11.2026)

Aufbau auf werkbank-skill-pur (dort bleibt der Test unverändert). Jan: in vielem besser, Optik zum Spielen gewünscht, so wenige Knöpfe wie nötig.
Bedienfeld (regler.js): Werte in sechs Gruppen, sechs Vorlagen, „Werte kopieren“ liefert Text zum Schicken.
Weg: Tasten, Bild vor/zurück, Zoomknöpfe, Plus/Minus an Reglern, Einzelpunkt, doppeltes „Beide lassen“ (Hauptknopf macht es).
Vier davon (Zoom, Plus/Minus, Einzelpunkt, Bild vor/zurück) lassen sich unter „Zusätzliche Knöpfe“ einschalten. Ohne „Einzelpunkt“ geht ein Punkt nur durch Ziehen (Bedienhilfe).
Nur wenn nutzbar: Rückgängig, Wiederholen, Ganzes Bild, Speichern. „Bild hinzufügen“ steht in der Bilderleiste.
Geprüft: jeder Wert an 1440 und 390 (je Bereich beide Enden), Überlauf, axe je Vorlage und bei Extremfarben, Hauptweg. Kombinationen nicht alle.
Einzeldatei: `python3 bauen.py <ziel>`, nicht ins Repo.
Regel Jan 25.11.2026: Was sich als Symbol zeigen lässt, ist auf Knöpfen Symbol statt Text (z. B. Löschen = Mülleimer). Name bleibt als Hinweis und für Vorleseprogramme. Gegen die Regel nav-label-icon des Skills, Jan geht vor. Schalter „Knöpfe“ zeigt Text wieder.
