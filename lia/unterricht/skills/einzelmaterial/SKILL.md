# Skill einzelmaterial (Version 3)

Du erstellst ein Unterrichtsmaterial für Lia: ein Arbeitsblatt, Folien, eine Arbeitsmappe (Excel), einen
Reihenentwurf oder eine Lernerfolgskontrolle, auf Wunsch mit Varianten. Lia unterrichtet an einer
Schule in Deutschland. Fach und Lehrkraft setzt Python ein, du schreibst nur den Inhalt.

## Art wählen
- Arbeitsblatt (`"art": "arbeitsblatt"`), wenn Lia ein Arbeitsblatt, Aufgaben, Übungen oder Material für
  Einzel- oder Gruppenarbeit möchte.
- Folien (`"art": "folien"`), wenn sie Folien, eine Präsentation oder einen Einstieg für die ganze Klasse möchte.
- Arbeitsmappe (`"art": "arbeitsmappe"`), wenn sie eine Tabelle zum Ausfüllen möchte, in der Excel rechnet:
  Notentabelle, Punkteliste, Übersicht zum Abhaken. Nur leere Vorlagen: keine Namen, Noten oder anderen
  Daten von Schüler*innen in die Beschreibung, auch wenn Lia welche mitschickt (dann im Begleittext sagen, dass
  sie die Werte selbst einträgt). Wie gerechnet wird, steht in den Hinweisen des Blatts, in Lias Worten.
- Reihenentwurf und Lernerfolgskontrolle: Lias Wunsch beginnt mit „Reihenentwurf:“ bzw.
  „Lernerfolgskontrolle:“ (Abschnitte unten). Beide sind Arbeitsblätter (`"art": "arbeitsblatt"`).
- Ist es unklar, mach ein Arbeitsblatt und schreib im Begleittext, dass es auf Wunsch auch Folien gibt.

## Reihenentwurf
Ein Dokument für Lia selbst, nicht für die Klasse. Titel: die Reihenfrage (fehlt sie, dein Vorschlag, als
Vorschlag gekennzeichnet). Inhalt in dieser Reihenfolge:
- Reihenfrage und zwei gegensätzliche Positionen mit je einem Satz, warum sie zur Frage passen (Belege im
  Begleittext).
- Kurz zur Lerngruppe, nur was die Planung betrifft (aus dem Reihenkontext, nichts dazu erfinden).
- Stundenübersicht als Tabelle: Stunde, Thema bzw. Stundenfrage, Ziel, Material, Phase der Reihe. Hat die Reihe
  schon Stunden, übernimm sie mit Nummer und Thema und plane nur die fehlenden. UB und Prüfung kennzeichnen.
- Ablauf wie in Lias Reihen (Leitfaden Abschnitt 1): intuitives Urteil, Position 1, Anwendung, Position 2,
  Anwendung, Transfer, Urteil, LEK.
- Idee für die LEK in einem Satz.
Kein Merksatz-Kasten, keine Aufgaben mit Antwortlinien. Sprache wie in Lias Entwürfen (Paarform).

## Lernerfolgskontrolle
- Die LEK (`beschreibung.json`) stellt die Reihenfrage; AFB II kommt zuerst, dann AFB III. Nicht zu schwer
  (Leitfaden). Punkte je Aufgabe in den Aufgabentext („(4 P.)“), Dauer wie gewünscht, sonst 45 Minuten.
- Dazu immer ein Erwartungshorizont als eigene Datei `beschreibung-erwartungshorizont.json` (Jan 30.10.2026),
  für Lia, nicht zum Austeilen: gleicher Titel, je Aufgabe die erwarteten Inhalte als Liste, Punkte, Hinweise
  zur Bewertung; als Tabelle Aufgabe | Erwartung | Punkte. Keine Namen von Schüler*innen.

## Varianten
Steht im Wunsch eine Zeile „Varianten: …“ oder „Auch als: …“, schreibst du jede Variante aus derselben
Beschreibung als eigene Datei (Namen nennt dir der Abschnitt „Art des Auftrags“). Alle Varianten behandeln
denselben Inhalt mit derselben Reihenfrage, damit alle am selben Thema arbeiten:
- einfach: kürzere Sätze, weniger Text, mehr Hilfen (Satzanfänge, vorgegebene Teile), gleiche Aufgaben.
- hilfekarten: Karten zum Ausschneiden, je Aufgabe eine Karte mit einem gestuften Tipp, nicht der Lösung.
- niveau-1 bis niveau-3: wie die Regel zu drei Niveaus (einfach, mittel, schwer). Unterschieden wird über die
  Hilfen, die Schwierigkeit des Falls oder die Zuteilung der Position; schwer heißt mehr eigenes Denken, nicht
  mehr Arbeit.
Ist das Original schon da (Nachbesserung), bleibt `beschreibung.json` unverändert. Andere Varianten setzt du
sinnvoll um und nennst im Begleittext, wie du sie verstanden hast.

## Qualität
- Sprache passend zur Klassenstufe: kurze Sätze, Fachbegriffe beim ersten Auftreten erklären.
  Fehlt die Klasse, nimm die Mittelstufe (Klasse 8 bis 10) an und sag es im Begleittext.
- Passt zur genannten Dauer. Ohne Angabe: eine Stunde mit 45 Minuten.
- Aufgaben steigen an: erst wiedergeben, dann erklären oder anwenden, zuletzt beurteilen oder Stellung nehmen.
  Operatoren am Satzanfang (Nenne, Erkläre, Wende an, Beurteile).
- Hilfen für schwächere Schülerinnen und Schüler: Satzanfänge oder ein Tipp (`hilfe`) bei schwierigen Aufgaben.
- Material (Texte, Fallbeispiele) schreibst du selbst, anschaulich und aus der Lebenswelt der Klasse.
  Zitate aus Werken nur kurz und mit Quelle. Nichts erfinden, was als Tatsache oder Zitat ausgegeben wird.
- Arbeitsblatt in Lias Aufbau: Merksatz, Anweisung, Material, Aufgaben. Meist reichen ein bis zwei Seiten.
- Folien in Lias Aufbau: Ziel für heute, Einstieg oder Leitfrage, Material, Arbeitsauftrag mit Zeit, Sicherung,
  zum Schluss gern Feedback. Wenig Text pro Folie. Untertitel der Titelfolie: Fach und Klasse,
  z. B. „Ethik · Klasse 10“.
- Gendergerechte Sprache wie bei Lia mit Sternchen (Schüler*innen), sparsam.
- Keine Namen echter Schüler*innen, keine Noten, keine personenbezogenen Daten.
