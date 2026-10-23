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
  schreibt data/wissen/katalog.md (211 Dateien, ca. 11k Tokens). Jeder Material-Lauf bekommt den Katalog und liest
  höchstens drei passende Beispiele mit Read.
- Echter Lauf mit Reihen und Katalog (23.10., direkt mit material.bearbeiten, Lia bekam nichts):
  „Arbeitsblatt 8. Klasse, Einstieg Reihe Strafe, Vergeltung oder Besserung, Fallbeispiel, 45 min“, Opus:
  2 Läufe, 89 s, 304.176 Tokens, umgerechnet 1,06 USD (erster Lauf ohne Katalog: 0,61 USD). Claude las
  Reihe_Strafe (Lias Planung), AB_1 Strafe (nur Kopf) und AB_1 Helfen als Vorbild. Ergebnis 2 Seiten: BBB-Merksatz,
  Fall Tim, zwei Meinungen, Zuordnungstabelle, Aufgaben mit Satzanfängen und Hilfen, Zusatzaufgabe; kurze Sätze,
  Partnerarbeit, Medienwechsel-Tipp und „Reihenfrage noch offen“ aus dem Reihenkontext übernommen; Belege
  (Kant, von Liszt) im Begleittext. Schwächen: Begleittext zu lang (7 Sätze statt 2–4). Ordner:
  data/arbeit/20261023-195619-unterricht-test02/. Jan und Lia haben das Blatt noch nicht angesehen.
  Mehrkosten real eher 0,30–0,45 USD je Auftrag. Hebel, falls zu teuer: Katalog kürzen (Varianten Türkisch,
  Feedback und Bewertung nur bei Bedarf, kürzerer Anfang).
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
1. Prompt = Lias Wunsch + laufende Reihen (reihen.toml) + Anhänge + Katalog (data/wissen/katalog.md) + skills/einzelmaterial/SKILL.md + Abschnitte Allgemein/Arbeitsblatt/Folien aus
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
  reihen.py (Reihenkontext laden und prüfen, Prompt-Abschnitt), wissen.py (Textfassungen, Katalog, Prompt-Abschnitt)
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
B. Leitfaden „So unterrichtet Lia“ aus Seminarnotizen, Kriterien, Entwürfen und Reihenplanungen (ein Opus-Lauf,
   ca. 1–2 USD), Jan liest gegen, dann in jeden Lauf.
C. Feste Beispielsammlung je Materialtyp im Skill (Architektur 2.5 beispiele/), Lia oder Jan wählt mit aus.
D. Prüfsatz aus Lias echten Stunden (Reihenplanung + Stundenthema -> Blatt, blind gegen ihr echtes Blatt),
   ca. 0,60 USD je Aufgabe; misst, ob A–C helfen.
1. Reihenkontext: gebaut und gefüllt 23.10. Offen: Merksätze und die Reihenfrage zu Straftheorien von Lia.
   Lias Planung Reihe_Strafe.docx enthält Kandidaten („Sollen Gefängnisse Täter:innen bestrafen oder bessern?“,
   Kant vs. von Liszt); erst nach Lias Bestätigung in reihen.toml.
2. Regelvorschläge (lia/auswertung/STATUS.md, „Regelvorschläge“): 23.10. Jan vorgelegt. Eingetragen: 1, 2 (ohne
   „nicht wieder vorschlagen“). Pausiert (Jan 23.10.): 3–11 werden nachgeholt, wenn Lia Zeit hat
   (3 und 4 vorgelegt ohne Wahl, 5–8 vorgelegt ohne Antwort, 9–11 noch nicht vorgelegt). Freigegebene in „Gelernte Regeln“ (gehen über claude_lauf in jeden Lauf). Für Material wichtig: 3, 4, 5, 6, 9, 10; für
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
  und Kurzentwurf 7.15 nur als anonymisierte Textfassungen *.anonym.txt). Aufgeräumt nach Jans Auftrag:
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
