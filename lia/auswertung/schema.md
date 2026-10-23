# Kategorienschema für Lias Aufgaben (Schritt 6)

Abgeleitet am 23.10.2026 aus einer Stichprobe von 9 Chats (zusammen etwa 230 Runden): Aristoteles,
Anwesenheit/Mitarbeit, Teilzeitantrag, Stücke für DS, Statusspiel, Bewerbung, Dramen-Zusammenfassungen,
Gedicht-Remix, Strafe/Kant. Der Text unten geht wörtlich in den Prompt für die Einordnung.

## Was eine Aufgabe ist
Eine Aufgabe ist ein Ziel, das Lia mit Claude erreichen will, zum Beispiel „Merksatz und AB-Text zu
Aristoteles“ oder „Teilzeitantrag ausfüllen“. Eine Aufgabe umfasst eine oder mehrere aufeinanderfolgende
Runden. Nachfragen, Änderungswünsche und Korrekturen am selben Ergebnis gehören zur selben Aufgabe.
Eine neue Aufgabe beginnt, wenn Lia ein anderes Ergebnis will (anderes Material, andere Frage, anderes
Dokument). Eine kurze Zwischenfrage ohne eigenes Ergebnis („ist Dotty alt?“) gehört zur laufenden Aufgabe.
Runden ohne Inhalt (leer, nur Dank) gehören zur Aufgabe davor.

## Kategorien (genau eine je Aufgabe)
- `fachklaerung`: Fachliche Frage klären oder recherchieren: Was sagt ein Philosoph, worum geht es in
  einem Stück, wo steht etwas, wird das heute noch vertreten. Ergebnis ist Wissen für Lia, kein Material.
- `auswahl`: Vorschläge zur Auswahl sammeln und abwägen: Stücke, Romane, Filme, Positionen, Beispiele,
  Fälle, die sich für eine Klasse oder Reihe eignen.
- `planung`: Didaktische Planung: Reihenfrage, Stundenaufbau, Phasen, Anwendung und Transfer, Kriterien,
  Eignung für die Lerngruppe, Unterrichtsbesuch vorbereiten.
- `material`: Material für Schülerinnen und Schüler erstellen: Text für ein Arbeitsblatt, Merksatz,
  Fallbeispiel, Aufgaben, Erwartungshorizont, Zusammenfassungen und Themenlisten für die Klasse,
  Szenen und Spielanweisungen, Gedichte und Textcollagen aus Schülertexten.
- `eigener_text`: Einen Text von Lia prüfen oder überarbeiten: Unterrichtsentwurf, Reflexion, Abschnitt
  für den UB, „kann ich das so nehmen?“, kürzen, umformulieren, Zitierweise, Rechtschreibung.
- `bewertung`: Leistung erfassen und bewerten: Mitarbeit und Fehlzeiten auswerten, Noten berechnen,
  Notenskalen, Schülertexte korrigieren und bewerten.
- `verwaltung`: Dienstliches und Formulare: Anträge ausfüllen, Bewerbung und Unterlagen, Mails von
  Behörden oder Schulleitung verstehen, Gehalt, Stunden, Fristen, Examen organisieren.
- `kommunikation`: Eine Nachricht an andere schreiben: Mail an Kolleginnen, Seminarleitung, Eltern,
  Schulleitung, Einladung, Antwort.
- `sonstiges`: Alles andere.

## Felder je Aufgabe
- `von`, `bis`: erste und letzte Runde (Nummern aus R1, R2 …).
- `kategorie`: eine aus der Liste oben.
- `titel`: kurze Beschreibung in Lias Worten, höchstens 10 Wörter.
- `fach`: `ethik`, `ds` (Darstellendes Spiel/Theater), `keins` oder `unklar`.
- `klasse`: Jahrgang als Zahl, wenn genannt, sonst null.
- `eingaben`: Liste aus `freitext`, `eigener_text` (Lia fügt einen eigenen Text ein), `bild` (Foto,
  Screenshot), `dokument` (PDF, docx, epub), `mail`, `tabelle`.
- `ausgabe`: was Lia am Ende haben will, kurz (z. B. „AB-Text“, „Liste mit Stücken“, „ausgefülltes Formular“).
- `ergebnis`: `erreicht` (Lia ist zufrieden oder macht mit dem Ergebnis weiter), `teilweise`,
  `abgebrochen` (Lia gibt auf oder wechselt ohne Ergebnis), `unklar`.
- `runde_ergebnis`: Runde, in der das verwendbare Ergebnis vorlag, sonst null.
- `korrekturen`: Liste der Stellen, an denen Lia ein Ergebnis von Claude zurückweist oder ändern lässt,
  weil es nicht passt. Eine bloße Anschlussfrage ist keine Korrektur. Je Korrektur:
  `runde`, `art` und `zitat` (Lias Worte, höchstens 15 Wörter). Arten:
  - `fachlich`: inhaltlich falsch oder nicht belegt („das steht so nicht bei Aristoteles“)
  - `niveau`: zu schwer, zu eloquent, nicht für die Klasse („bitte nicht so eloquent“)
  - `umfang`: zu lang, zu kurz, kürzen, ausführlicher
  - `form`: andere Form, Gliederung, Fließtext statt Liste, Kommas statt Punkte
  - `stil`: Ton, Wortwahl, Gendern („nicht so männlich“)
  - `anwendbarkeit`: im Unterricht nicht brauchbar („der Merksatz muss anwendbar sein“)
  - `missverstanden`: Claude hat den Auftrag falsch verstanden
  - `einseitig`: zu wenig Auswahl, zu sehr in eine Richtung
  - `andere`
- `belastung`: true, wenn Lia Zeitdruck, Frust oder Erschöpfung äußert („ich bin so verzweifelt“).
- `automatisierbar`: `hoch` (ein Agent könnte das Ergebnis mit den Angaben aus dem Chat allein liefern),
  `mittel` (geht mit Rückfragen oder Lias Material), `gering` (braucht Lias Urteil im Gespräch).
- `begruendung`: ein Satz zu `automatisierbar`.
