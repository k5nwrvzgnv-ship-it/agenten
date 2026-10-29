# Status: Agent theater (Lias Instanz)

## Zweck
Hilft Lia in ihrem zweiten Fach Theater (Darstellendes Spiel). Erste Aufgabe: ein Stück für ihre Gruppe
kürzen (Jan 29.10.2026). Später ggf. weitere Theateraufgaben aus lia/auswertung (Stücke zusammenfassen,
Szenen und Chortexte, Bewertungsbögen), aber erst nach Absprache.

## Stand (29.10.2026)
- Ordner eingerichtet: nur diese STATUS.md und eine leere .venv (Python 3.12, agentkit per agentkit.pth,
  keine Pakete). Kein Code, keine Tests, kein Dienst, nicht in pruefen.sh (kommt mit den ersten Tests).
- Das Stück liegt noch nicht vor, Lias Vorgaben fehlen (siehe Offene Punkte).

## Vorschlag Aufbau (noch nicht entschieden, erst nach Lias Angaben)
- Grundsatz wie in lia/recherche: Der Agent erfindet keinen Text. Python zerlegt das Stück in Szenen und
  Repliken mit fester Nummer. Claude schlägt Striche nur als Nummern vor (mit kurzer Begründung je Strich),
  Python baut daraus die gekürzte Fassung wörtlich aus dem Original.
- Python rechnet nach jedem Vorschlag nach: Wörter bzw. geschätzte Spieldauer vorher/nachher, Textanteil je
  Rolle, welche Rollen ganz wegfallen, ob jede Szene noch einen Auftritt/Abgang hat, der zum Rest passt.
- Ergebnis für Lia: Strichfassung (gestrichene Stellen sichtbar durchgestrichen oder grau) und saubere
  Spielfassung, als docx/PDF über shared/renderer, dazu eine Liste der Striche mit Begründung.
- Lia prüft und gibt Feedback über ihre Zentrale; Änderungswünsche als neue Runde auf derselben Fassung.
- Einstieg vermutlich von Hand gestartet (wie lia/examen), Dienst erst, wenn Lia den Weg über ihre
  Zentrale nutzen will.
- Pakete: pypdf und die Renderer-Pakete (Versionen wie shared/renderer/requirements.txt), sobald klar ist,
  in welchem Format das Stück vorliegt. Vorher Jans Okay.

## Aufbau
- Instanz: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz
- .venv: lia/theater/.venv, agentkit und renderer per agentkit.pth
- Laufzeitdaten: lia/theater/data/ (Stücktext, Fassungen), Logs: lia/theater/logs/ (beide nicht im Repo)

## Entscheidungen
- 29.10.2026: eigener Ordner lia/theater statt Teil von lia/unterricht (Jan: zweites Fach, eigener Agent).

## Offene Punkte
1. Fragen an Lia (über Jan):
   - Welches Stück (Titel, Autor, Ausgabe/Übersetzung)? In welcher Form liegt es vor (PDF, Word, Scan,
     Buch)? Bitte die Datei schicken.
   - Ziel: wie lang soll die Fassung werden (Spieldauer in Minuten oder Seitenzahl)?
   - Gruppe: wie viele Spieler*innen, Klasse/Kurs, sollen alle etwa gleich viel Text haben? Dürfen Rollen
     zusammengelegt, geteilt oder chorisch gesprochen werden? (Nur Zahlen, keine Namen von Schüler*innen.)
   - Was muss bleiben (Szenen, Figuren, Lieblingsstellen), was darf sicher raus?
   - Nur streichen, oder auch Übergänge umformulieren, Sprache vereinfachen, Erzähler-/Chortext ergänzen?
   - Rechte: Kommt das Stück von einem Bühnenverlag? Dann klärt Lia mit dem Verlag, ob die Kürzung für die
     Schulaufführung erlaubt ist; der Agent kann das nicht prüfen.
   - Termin: bis wann braucht sie die Fassung, wann ist die Aufführung?
2. Danach Plan mit Jan abstimmen (Ablauf, Pakete, Kostengrenze je Lauf), dann Code mit Tests und Eintrag in
   pruefen.sh.

## Gelernte Regeln
- (noch keine)
