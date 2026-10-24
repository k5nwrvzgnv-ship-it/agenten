# Status: Agent unterricht (Lias Instanz)

## Zweck
Material auf Zuruf für Lia (docs/lia-architektur.md, Schritt 1): Lia tippt in ihrer Zentrale „Neues Material“,
beschreibt ihren Wunsch und bekommt ein Arbeitsblatt (docx) oder Folien (pptx) in ihrem Stil mit Begleittext.
Woche und Frage sind noch Platzhalter („kommt bald“, ohne Claude).

## Stand (23.10.2026)
- Reihenkontext (23.10., Schritt 1 aus der Auswertung): reihen.toml wird gelesen und jedem Material-Lauf
  mitgegeben. Eingetragen nach Lias Angaben (23.10.): Ethik Klasse 8, Lerngruppe, frühere Reihen aus Kl. 7/8,
  behandelte Philosoph*innen, nächste Reihe Straftheorien (Reihenfrage noch offen). Merksätze fehlen noch.
  Noch kein echter Lauf mit Reihen.
- Lias Material als Nachschlagewerk (23.10., Stufe A): wissen.py legt Textfassungen in data/wissen/text/ an und
  schreibt data/wissen/katalog.md (211 Dateien, 21.760 Zeichen, ca. 6k Tokens; gekürzt 23.10. von 40.400: Ordner
  einmal je Reihe, Anfang 60 Zeichen, Türkisch/Feedback/Bewertung nur als Dateinamen). Jeder Material-Lauf bekommt den Katalog und liest
  höchstens drei passende Beispiele mit Read.
- Echter Lauf mit Reihen und Katalog (23.10., direkt mit material.bearbeiten, Lia bekam nichts):
  „Arbeitsblatt 8. Klasse, Einstieg Reihe Strafe, Vergeltung oder Besserung, Fallbeispiel, 45 min“, Opus:
  2 Läufe, 89 s, 304.176 Tokens, umgerechnet 1,06 USD (erster Lauf ohne Katalog: 0,61 USD). Claude las
  Reihe_Strafe (Lias Planung), AB_1 Strafe (nur Kopf) und AB_1 Helfen als Vorbild. Ergebnis 2 Seiten: BBB-Merksatz,
  Fall Tim, zwei Meinungen, Zuordnungstabelle, Aufgaben mit Satzanfängen und Hilfen, Zusatzaufgabe; kurze Sätze,
  Partnerarbeit, Medienwechsel-Tipp und „Reihenfrage noch offen“ aus dem Reihenkontext übernommen; Belege
  (Kant, von Liszt) im Begleittext. Schwächen: Begleittext zu lang (7 Sätze statt 2–4). Ordner:
  data/arbeit/20261023-195619-unterricht-test02/. Jan und Lia haben das Blatt noch nicht angesehen.
  Mehrkosten real eher 0,30–0,45 USD je Auftrag (mit dem langen Katalog). Katalog danach gekürzt (siehe oben);
  die Wirkung auf die Kosten ist noch nicht in einem echten Lauf gemessen.
- Material läuft (Code fertig, Tests grün, Dienst eingerichtet). Noch kein Auftrag von Lia über Telegram.
- Echter Lauf 22.10. (direkt mit material.bearbeiten, ohne Warteschlange, damit Lia nichts bekam):
  „Arbeitsblatt kategorischer Imperativ, Klasse 10, 45 min“ mit Opus: 2 Claude-Läufe, 90 s, 129.430 Tokens,
  umgerechnet 0,61 USD (Pro-Abo, also nur Kontingent). Beschreibung gleich gültig; in der Kontrolle sah Claude
  den Überlauf auf eine 4. Seite und kürzte, Python baute neu (3 Seiten: Merksatz, Text, Fälle, 5 Aufgaben mit
  Satzanfängen und Hilfen, Tabelle quer). Inhalt fachlich ordentlich, Jan hat die Datei noch nicht angesehen:
  data/arbeit/20261022-231000-unterricht-a1b2c3/.
- Folien sind nur mit Tests geprüft, noch nicht im echten Lauf.
- Angehängte Dateien (22.10.): Lias Zentrale nimmt Dateien und Fotos an, sie kommen im Feld dateien mit.
  Aufbereitung mit echtem LibreOffice geprüft, ein echter Claude-Lauf mit Anhang fehlt noch.

## Ablauf (material.py)
1. Prompt = Lias Wunsch + laufende Reihen (reihen.toml) + Anhänge + Katalog (data/wissen/katalog.md) +
   Leitfaden (leitfaden.md) + skills/einzelmaterial/SKILL.md + Abschnitte Allgemein/Arbeitsblatt/Folien aus
   shared/renderer/FORMAT.md (zur Laufzeit gelesen, bleibt aktuell). Claude schreibt mit Write
   data/arbeit/<auftrag>/beschreibung.json.
2. Python baut mit renderer.bauen (Profil profil.toml). Fehler (Datei fehlt, kein JSON, falsche art,
   BeschreibungUngueltig) gehen in derselben Sitzung an Claude zurück, höchstens 3 Korrekturen.
3. Kontrolle: Claude sieht Kontrolltext und Vorschau-PNGs. Ändert Claude die Beschreibung, baut Python neu
   (eine Kontrollrunde, die neue Vorschau sieht Claude nicht mehr).
4. Claudes letzte Antwort ist der Begleittext, die Datei geht über auftraege.abschliessen(..., dateien=).
- Anhänge (Vorlage für genau diesen Auftrag, Jan 22.10.): anhaenge_vorbereiten legt für pdf/docx/pptx neben die
  Datei eine Textfassung (<datei>.txt, agentkit.textfassung, pypdf) und Seitenbilder (<datei>-seiten/, über
  renderer.vorschau, auch für Scans; höchstens 8 je Datei im Prompt). Grund: Claudes Read öffnet PDFs auf dem
  Server nicht (kein poppler). Bilder öffnet Claude direkt, andere Formate versucht Claude mit Read.
- Reihenkontext (reihen.py, reihen.toml): je Reihe [[reihe]] mit klasse (Pflicht), dazu fach, titel,
  reihenfrage (fehlt, solange eine Reihe geplant wird), lerngruppe, notizen, behandelt, merksaetze,
  bisherige_reihen. Alle Reihen gehen in den Startprompt, Claude nimmt die
  passende und nennt sonst seine Annahme im Begleittext. reihen.toml ist im Repo (keine Schülerdaten) und für
  Claude schreibgeschützt (*.toml in claude_lauf.GESCHUETZT). Ist die Datei fehlerhaft, läuft das Material ohne
  Reihen und Jan bekommt eine Meldung. Pflege heute von Hand durch Jan; später ggf. über Lias Zentrale.
- Opus (art="anspruchsvoll"), Zeitbudget 18 min für neue Läufe, Dienst-Timeout 25 min.
- Fehler: Lia bekommt „nicht erstellen, Jan ist informiert“ (ihre Zentrale zeigt bei fehlgeschlagen
  ohnehin ihren eigenen Text), Jan eine Meldung in seiner Zentrale (jan_melden, Jans shared/meldungen).
  Kontingent erschöpft: ebenso, mit Uhrzeit im Ergebnis. Unerwartete Fehler: dasselbe, der Dienst läuft weiter.
- Dateiname aus art und titel (Arbeitsblatt <Titel>.docx), am Wortende auf 60 Zeichen gekürzt.

## Aufbau
- Instanz: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz (Warteschlangen, Regeln, .env dort)
- Code: agent.py (Verteilung nach quelle, Fehler, Meldung an Jan), material.py (Ablauf, ohne Netz testbar),
  reihen.py (Reihenkontext laden und prüfen, Prompt-Abschnitt), wissen.py (Textfassungen, Katalog, Prompt-Abschnitt),
  leitfaden.py (Leitfaden-Entwurf per Claude, freigegebenen Leitfaden laden, Prompt-Abschnitt). leitfaden.md ist
  für Claude noch nicht schreibgeschützt (Bedarf in Haupt-STATUS)
- Wissen: data/wissen/eingang/ (Lias Dateien), text/ (Textfassungen), katalog.md, alles nicht im Repo.
  Nach neuen Dateien von Hand: .venv/bin/python wissen.py (liest nur Neues, entfernt Textfassungen gelöschter
  Quellen; ca. 2 min beim ersten Mal). Neue Dateien vorher auf Schülerdaten prüfen.
- Skill: skills/einzelmaterial/SKILL.md (Version 1, Art wählen, Qualitätskriterien). Version steht in material.py.
- Profil: profil.toml (Kopie von shared/renderer/beispiele/profil-lia-stil.toml, Ethik, Frau Pohlmann)
- .venv: Pakete aus requirements.txt (Versionen wie shared/renderer), agentkit und renderer per agentkit.pth
- Dienst: lia-unterricht.service (oneshot, Vorlage systemd/, MemoryMax 1500M), gestartet von Lias Zentrale.
  Nach Änderung: Vorlage nach ~/.config/systemd/user/ kopieren, systemctl --user daemon-reload.
- Laufzeitdaten: data/arbeit/<auftrag>/ (Beschreibung, Datei, Vorschau), Logs: logs/ (beide nicht im Repo)
- Kosten je Auftrag: logs/ (Zeile „fertig: ... USD, Tokens“) und shared/verbrauch/ (instanz lia).

## Entscheidungen (Jan, 22.10.2026)
- Der Agent löst den Platzhalter unterricht ab (Weg material), kein eigener Agent; portal_logik bleibt unverändert.
- Fach Ethik, Lehrkraft Frau Pohlmann. Modell Opus.
- Formate docx und pptx, keine PDF-Ausgabe an Lia (Renderer-Entscheidung).

## Umsetzung der Auswertung (lia/auswertung, 23.10.2026, Rangliste UNGEPRÜFT)
Reihenfolge mit Jan abgestimmt, je Schritt erst nach seinem Okay:
Wissen aus Lias Dokumenten (Jan 23.10., Budget einmalig ca. 10–15 USD Kontingent):
A. Katalog und Nachschlagen: gebaut und im echten Lauf geprüft 23.10. (Claude las drei passende Dateien).
B. Leitfaden „So unterrichtet Lia“ (leitfaden.py): Entwurf erzeugt 23.10. in data/wissen/leitfaden-entwurf.md
   (780 Wörter, 6 Abschnitte, jede Regel mit Quelle) aus 28 Quellen, ein Opus-Lauf: 3,16 USD, 2,73 Mio. Tokens
   (meist Cache-Lesen). Claude meldete: Quellen dünn zu Klasse 8 und zu Methoden, die nicht funktionieren; bei Strafe
   kommt erst Kant, dann von Liszt (Lia 24.10., in reihen.toml). Von Jan freigegeben 23.10., liegt als
   leitfaden.md im Repo und geht in jeden Material-Lauf (nach dem Katalog, vor dem Skill). Noch kein echter Lauf
   damit. Verbraucht für A, B, B2 und C1 bisher ca. 7 USD.
B2. Entwicklungsverlauf (verlauf.py, Jan 23.10., Lia einverstanden): data/wissen/entwicklung.md (nicht im Repo, eine
   Auswertung über Lia, gehört zuerst ihr). Ein Opus-Lauf aus 16 Quellen (6 Entwürfe, 7 Rückmeldungen, Notizen,
   Kriterien): 1,82 USD, 664.918 Tokens. Inhalt: Zeitleiste, 12 Kriterien x 6 Entwürfe (–/o/+ mit Beleg), Kritik
   und was daraus wurde, Richtung je Kriterium, Vermutung (ausdrücklich keine Prognose), Folgen für den Agenten,
   Grenzen. Unsicher: Datum UB 5 (Kopf 18.05.2026, vermutlich Sept. 2026), Kurzentwurf ohne Datum, einige
   Rückmeldungen nur über den Dateinamen zugeordnet. Die Datei selbst geht nicht in die Läufe. Ihre „Folgen für
   den Agenten“ 2–5 hat Jan am 23.10. als Abschnitt 7 in leitfaden.md übernommen; Punkt 1 nicht (nannte noch
   Helfen als laufende Reihe). Belege mit Werk und Stelle gehören in den Begleittext, nicht aufs Blatt
   (Regelvorschlag 3, von Lia freigegeben 24.10.).
C. Beispielsammlung (beispiele.py), Teil 1 erledigt 23.10.: Vorschlag data/wissen/beispiele-vorschlag.md (ein
   Opus-Lauf, 24 Blätter gelesen, 0,86 USD): je Materialtyp 1–2 Musterblätter mit Warum gut / Nachahmen / Schwäche,
   Schwerpunkt Klasse 8 Helfen (AB_4, BBB_AB, AB_5.1/5.2, Sicherungszettel A/B, Erörterung leicht/mittel/schwer,
   Präsentation_5, EH der LEK Lügen). Fehlt ganz: DS, Reihe Strafe, Sprachbildungs-Rubrik, Aufgabe zu Grenzen einer
   Position, EH zur Erörterungs-LEK, Belege auf Blättern. Stellenangaben im Vorschlag sind Claudes eigene Kenntnis,
   ungeprüft. Auswahl durch Lia läuft seit 24.10. (Blatt für Blatt), bisher übernommen: AB_4 (ab_text_position),
   AB_2 (ab_text_position, Muster für den Aufbau: erst Alltagsfall, dann die Regel daraus ableiten),
   BBB_AB mit Lösungen und AB_6_Erörterung (argumentieren),
   AB_5.1/5.2 und AB_3.1 (fallbeispiel; AB_3.2 nicht, Ergebnis nach Singer nicht eindeutig).
   Teil 2: gewählte Blätter ins Renderer-JSON übertragen (Claude, gegen
   das Original geprüft) und als skills/einzelmaterial/beispiele/ ablegen, ca. 0,40–0,60 USD je Blatt.
D. Prüfsatz aus Lias echten Stunden (Reihenplanung + Stundenthema -> Blatt, blind gegen ihr echtes Blatt),
   ca. 0,60 USD je Aufgabe; misst, ob A–C helfen.
1. Reihenkontext: gebaut und gefüllt 23.10. Strafe: erst Kant, dann von Liszt (Lia 24.10.). Merksätze der Reihe Helfen
   eingetragen (24.10.). Offen: Reihenfrage und Merksätze zu Straftheorien (Lia sucht noch, 24.10.).
   Lias Planung Reihe_Strafe.docx enthält Kandidaten („Sollen Gefängnisse Täter:innen bestrafen oder bessern?“,
   Kant vs. von Liszt); erst nach Lias Bestätigung in reihen.toml.
2. Regelvorschläge (lia/auswertung/STATUS.md, „Regelvorschläge“): 23.10. Jan vorgelegt. Eingetragen: 1, 2 (ohne
   „nicht wieder vorschlagen“). Eingetragen 24.10.: 3–10 (Lia). Offen: 11 (Bewertung, gehört nicht zu unterricht). Freigegebene in „Gelernte Regeln“ (gehen über claude_lauf in jeden Lauf). Für Material wichtig: 3, 4, 5, 6, 9, 10; für
   Fragen: 1, 2, 7, 8; 11 (Bewertung) gehört nicht hierher.
3. „Frage stellen“ als Fachfragen mit Belegpflicht (eigener Ablauf und Skill, Reihenkontext mit).
4. Änderungswünsche (offener Punkt 2): Sitzung fortsetzen; Bedarf an Lias Zentrale in die Haupt-STATUS.
5. Profil für Darstellendes Spiel (zweites Profil, Wahl über die Reihe).
Weitere Wünsche von Lia (23.10.), noch nicht umgesetzt:
- Vorgaben ihrer Seminarleitung, was eine gute Reihenfrage ausmacht, und Schulvorgaben (schulinternes
  Curriculum/RLP): Lia schickt sie, sie sollen dem Agenten beigegeben werden (Fragen, Auswahl).
- Lias Dokumente aus dem Referendariat (23.10.): Sammelstelle data/wissen/eingang/ (nicht im Repo, nur für agent
  lesbar). Dort bisher: Fachseminar_Ethik_Notizen.pages mit Textfassung (.pages.txt, Sitzungen 09.09.2025 bis
  21.04.2026: Reihenplanung, Problemfragen, Entwürfe, Methoden; aus der Pages-Datei grob entpackt, Tabellen und
  Bilder fehlen) und Kriterien_gute_Unterrichtseinheit.txt (aus Jans Screenshot). Dazu per scp (23.10.):
  Ethik/ (7. Klasse: Reihen Lügen, Gerechtigkeit, Freundschaft + Operatoren, Glück, Tierethik; 8. Klasse:
  Helfen Fremde/Familie, Anfang Reihe Strafe; Operatorentraining Jg. 7; Einzelnes) und UBs+Feedback/
  (Feedbacks der Seminarleitungen, Aristoteles Nikomachische Ethik als PDF mit Text, Entwürfe UE 1–3, UB 4, UB 5
  und Kurzentwurf 7.15 nur als anonymisierte Textfassungen *.anonym.txt; nachgeschärft 23.10., nachdem der
  Leitfaden-Lauf Reste meldete: von der PDF-Umwandlung zerlegte Vornamen (Fa0ma, FaDma, Motomaj, Zenep),
  Seminarleitung und Schule ersetzt). Lehrkräfte und Schulname stehen weiter in Lias Material und Notizen
  (z. B. Folienkopf, LEK-Kopf); Schülerdaten wurden bei der letzten Suche keine mehr gefunden. Aufgeräumt nach Jans Auftrag:
  Schülerdaten gelöscht (Einzelbewertungen, Noten-, Mitarbeits-, Materiallisten, Sitzpläne, Gruppenlisten,
  Original-Entwürfe mit Lerngruppenanalyse), dazu die Zip-Kopie, Vorfassungen, Sperrdateien und PDFs, deren Text zu
  mind. 85 % einer docx/pptx gleichen Namens entspricht (docx/pptx behalten). Stand: 211 lesbare Dateien. Vornamen in
  Fallbeispielen (z. B. Yagmur, Berat) sind geblieben. Noch offen und erst nach Jans Okay: Wie der Agent das
  Wissen nutzt (auswählen, kürzen, in den Prompt oder als Dateien zum Lesen). Schülerdaten gehören nicht hierher.
- Quellen: Lia möchte Dokumente als Quellen hinzufügen. Bei der Wahl zweier gegensätzlicher Positionen soll die
  Quellenlage zählen: als Gelernte Regel eingetragen (23.10.). Offen: wie Lia Quellen dauerhaft ablegt.
6. Optional: Blindvergleich mit lia/auswertung/data/ergebnis/pruefsatz.json (P01–P17, ~10 USD Kontingent).

## Offene Punkte
1. Handtest: Lia tippt „Neues Material“ und schickt einen Wunsch, einmal Arbeitsblatt, einmal Folien.
2. Wünsche nach Änderung („mach Aufgabe 3 leichter“): Lias Zentrale kennt noch keine Antwort auf ein Ergebnis.
   Dann Sitzung fortsetzen (Feld sitzung ist gespeichert) und Beschreibung überarbeiten lassen.
3. Dauerhafte Schulvorlage (dotx/potx nach data/vorlagen/, renderer vorlage=): Die Zentrale nimmt Dateien jetzt an,
   heute gelten sie nur für den einen Auftrag. Erst klären, wie Lia eine Vorlage als dauerhaft kennzeichnet.
4. Handtest Anhang: Lia schickt einen Text oder ein altes Arbeitsblatt mit „Mach daraus ein Arbeitsblatt“.
   Die Datei von 23:15 (22.10.) wurde noch abgelehnt und muss neu geschickt werden.
5. Ausbau des Skills nach Architektur 2.5 (beispiele/, evals/), sobald Lia Ergebnisse abgenommen hat.
6. Woche und Frage: noch Platzhalter. Dateien an einer Frage werden bisher nur bestätigt.

## Gelernte Regeln
- 23.10.2026: Bei der Wahl zweier gegensätzlicher Positionen zählt die Quellenlage: Es muss Texte dazu geben, möglichst digital verfügbar, kostengünstig und nicht zu nischig. (Anlass: Lias Wunsch, von Jan freigegeben)
- 23.10.2026: Was einem Philosophen zugeschrieben wird, braucht einen Beleg (Werk, Stelle). Eigene didaktische Vereinfachung als solche kennzeichnen. Nichts erfinden, Unsicherheit sagen. (Anlass: Auswertung von Lias Chats, Regelvorschlag 1, fachlich: 52 Korrekturen; von Jan freigegeben)
- 23.10.2026: Vor jeder Antwort Reihenfrage, Klasse und gewählte Positionen der laufenden Reihe beachten, nicht stillschweigend wechseln. (Anlass: Auswertung, Regelvorschlag 2 ohne „behandelte Positionen nicht wieder vorschlagen“, missverstanden: 43, einseitig: 14; von Jan freigegeben)
- 24.10.2026: Texte für Schülerinnen und Schüler: Fließtext in ganzen Sätzen, ohne Zwischenüberschriften und ohne Stellenangaben. Belege (Werk, Stelle) gehören in den Begleittext für Lia. BBB: je Teil genau ein vollständiger Satz. (Anlass: Auswertung, Regelvorschlag 3, form: 48; von Lia freigegeben, über Jan)
- 24.10.2026: Sprache in der 8. Klasse (lernschwach, mehrsprachig), nur dort: kurze Sätze, keine Redewendungen, abstrakte Wörter (schulden, Pflicht, zustehen, Kosten tragen) vermeiden oder erklären, nichts voraussetzen, was nicht behandelt wurde, nicht eloquent. Ausnahme Sprachbildung: zwei bis drei etwas schwierigere Wörter je Text sind gewollt. (Anlass: Auswertung, Regelvorschlag 4, niveau: 26; von Lia freigegeben mit Ergänzung, über Jan)
- 24.10.2026: Ein Merksatz muss zuerst fachlich korrekt sein: Er darf für die Lerngruppe vereinfacht sein, aber die Position nicht verfälschen (Beleg im Begleittext). Außerdem muss er sich auf einen Fall anwenden lassen und ihn eindeutig entscheiden. Vor dem Abschicken beides an einem Beispielfall prüfen; den Testfall mit kurzer Begründung in den Begleittext schreiben. (Anlass: Auswertung, Regelvorschlag 5, anwendbarkeit: 30; von Lia freigegeben mit Ergänzung, über Jan)
- 24.10.2026: Fallbeispiele (vorerst für alle Klassen): alltagsnah, logisch stimmig, eindeutige Entscheidung (entweder/oder), keine Tötung, kein Femizid, keine Gewalt, die man rechtfertigen müsste; Strafen realistisch. (Anlass: Auswertung, Regelvorschlag 6; von Lia freigegeben, über Jan)
- 24.10.2026: Zwei Positionen für eine Reihe müssen sich klar widersprechen; nah beieinander liegende Positionen benennen. (Anlass: Auswertung, Regelvorschlag 7, fachlich; von Lia freigegeben, über Jan)
- 24.10.2026: Auswahllisten (Philosoph*innen, Stücke, Filme, Themen) breit streuen, nicht nur eine Richtung oder nur Klassiker. (Anlass: Auswertung, Regelvorschlag 8, einseitig; von Lia freigegeben, über Jan)
- 24.10.2026: Lieber kurz, auf Wunsch länger. Ein Arbeitsblatt passt auf eine Seite, wenn nicht anders gesagt. (Anlass: Auswertung, Regelvorschlag 9, umfang: 31; von Lia freigegeben, über Jan)
- 24.10.2026: Geschlechtergerecht schreiben, nicht männlich geprägt. In Entwürfen (Unterrichtsentwürfe, die Lia abgibt) die Paarform „Schülerinnen und Schüler“, sonst mit Sternchen (Schüler*innen). Texte, die Lia selbst abgibt, in ihrem Ton, ohne Umgangssprache und nicht geschwollen. (Anlass: Auswertung, Regelvorschlag 10, stil: 18; von Lia freigegeben mit Ergänzung, über Jan)
- 24.10.2026: Musterblätter sind Anregung für ihren Materialtyp, keine Vorlage für jedes Blatt. Form und Aufgaben richten sich nach der Phase der Reihe (z. B. Einstieg, Erarbeitung, Anwendung, Urteil). Passt kein Muster zur Phase, wird das Blatt frei gestaltet, nach den übrigen Regeln. (Anlass: Lia bei der Auswahl der Beispielsammlung; von Lia freigegeben, über Jan)
