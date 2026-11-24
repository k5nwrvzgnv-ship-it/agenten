# Bauplan: Werkbank als Web-App (Labeln, Vergleichen, Trainieren)

Stand 24.11.2026, Vorschlag, nichts entschieden. Auftrag Jan: geschlossene Kette mit einfacher, guter Oberfläche,
Henri und Felix arbeiten mit. Klickbarer Entwurf: unterlagen/werkbank-entwurf/ (index.html, braucht daten.js und die JPGs;
echte Kodytek-Bilder CC BY 4.0, echte Markierung und Vorhersage, nichts wird gespeichert).

## Warum selbst bauen
Ultralytics Platform deckt die Kette ab, aber in fremder Cloud. CVAT frei braucht Docker, Qualitätsansicht und SAM 2/3
laut README nur bezahlt. Label Studio frei sortiert Active Learning nur von Hand. X-AnyLabeling ist lokal. Messung in
mm und Regler für den Maskenstil fanden sich nicht (Suche 24.11., nicht ausprobiert). Für die Fotos vom 27.11.
bleibt X-AnyLabeling der Rückfall.

## Aufteilung
- Server: kleine Python-Web-App, nur Bilder (verkleinert), Labels, Logins, Vergleich. Kein torch. Speicher vorher messen.
- Mac oder Rechenzentrum: Vorlabeln und Training, holt Aufträge ab und lädt Ergebnisse hoch.
- Browser: Umriss bearbeiten, Maße rechnen. Labels als JSON je Bild und Person, Export YOLO-seg.

## Stufen, jede für sich nutzbar
1. Labeln: Vorlabel laden, Punkte ziehen, Rand in mm, glätten, Klasse, zeichnen, rückgängig, speichern je Person.
   Fertig: Henri oder Felix labeln 20 Bilder ohne Hilfe; Maße gleich masken.masse_mm (Test gegen gleiche Umrisse).
2. Vergleichen: Deckung und mm je Paar, Streit zuerst. Fertig: gleiche Zahlen wie auswertung.py.
3. Training: Auftrag, Lauf mit Manifest, neues Modell ersetzt altes nur bei besserer Messlatte auf festen Prüfbalken.
4. Automatik: Bilder nach Unsicherheit des Durchmessers in mm vorlegen, Varianten trainieren. Test bleibt gesperrt.

## Feste Regeln
- Die 20 Vergleichsbilder und der Test-Teil werden ohne Vorlabel und ohne Sicht auf andere gezeichnet.
- Angeschnittene Merkmale bekommen kein Maß.

## Im Entwurf nicht enthalten
Regler für die Schwelle (braucht die Wahrscheinlichkeitskarte des Modells), Klick mit SAM, Anmeldung, Speichern,
Training, Blindmodus, Altholzklassen. Der Entwurf misst den kleinsten Durchmesser als engste Breite des Umrisses,
masken.masse_mm nimmt die Ellipse: vor Stufe 1 festlegen (Normfrage, Henri).

## Offen
Rechenzentrum: GPU, Datenregeln. Erreichbarkeit (werkbank.meldro.de, Schritte als root durch Jan). Pakete und Dienst
erst nach Jans Okay. Lizenz ultralytics AGPL vor Weitergabe prüfen.

## Gestaltung (Jan 24.11.2026)
Schwarz, modern, Stil des Neurolign-Logos (runde Knoten, Verbindungen, Nussbraun). Keine Erklärsätze in der
Oberfläche, nur kurze Beschriftungen. Den von Jan genannten Medium-Artikel konnte Claude nicht lesen (403).
Bilder: Kodytek u. a. 2022, CC BY 4.0, verkleinert; Nennung in der App noch unterbringen.
