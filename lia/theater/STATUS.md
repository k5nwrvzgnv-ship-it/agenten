# Status: Agent theater (Lias Instanz)

## Zweck
Hilft Lia in ihrem zweiten Fach Theater (Darstellendes Spiel). Erste Aufgabe: aus „Der nackte Wahnsinn“
(Michael Frayn, Noises Off) eine eigene Fassung für ihren DS-Kurs entwickeln. Lia will nicht klassisch kürzen,
sondern Spielanlässe finden, Szenen daraus entwickeln und die lustigen Textstellen behalten.

## Stand (29.10.2026)
- Ordner, STATUS.md und eine leere .venv (Python 3.12, agentkit und renderer per agentkit.pth, keine Pakete).
  Kein Code, keine Tests, kein Dienst, nicht in pruefen.sh.
- Lias Material liegt in data/ (nicht im Repo, Dateien chmod 600):
  - data/eingang/: Originale von Lia (Erste_Gedanken.docx, Figuren.docx, Vom_Text_zur_Szene.pages,
    11._Klasse-25_26.zip, e-245-der-nackte-wahnsinn.pdf).
  - data/entpackt/klasse/k11/: ihre DS-Grundlagen (Status, Kompositionsmethoden, Material, Körper, Stimme/Chor,
    Planung). Den Ordner „Bewertung und Klausuren“ (Noten, Erwartungshorizonte mit Schülernamen) und
    Zwischennoten_11er.docx habe ich aus der entpackten Kopie gelöscht; im Original-Zip sind sie noch.
    Diese Daten gehen nie an Claude.
  - data/entpackt/pages/preview.jpg: „Vom Text zur Szene“ (Schema Stückvorlage -> Genre/Inhalt/Figuren/Ort ->
    Spielsituationen -> Gestaltungselemente -> Requisiten, Szenenfolge, Übergänge). Die .pages-Datei selbst ist
    nicht lesbar, das Vorschaubild reicht.
  - data/text/: Textfassungen aller docx/pdf (agentkit.textfassung), zusammen rund 508.000 Zeichen.
- Das Stück: Ansichtssendung des Deutschen Theaterverlags (E 245, Neufassung 2000), 172 PDF-Seiten, Text mit
  Seitenmarken lesbar (264.000 Zeichen). Erster Akt PDF-Seite 6–76, zweiter 77–132, dritter 133–172.
  Neun Figuren (Dotty, Garry, Brooke, Frederick, Belinda, Selsdon, Lloyd, Poppy, Tim).
- Lias Konzept (Erste_Gedanken.docx, Figuren.docx und ihre Nachricht vom 29.10.):
  - Drei Akte wie im Original: Generalprobe (4. Wand bleibt), Premiere (Publikum einbezogen), Dernière (Chaos).
    Eröffnung 3 Min (Choreo, Rollen werden vorgestellt), je Akt 10 Min, zusammen 35–40 Min.
  - Jede Rolle hat eine klare Eigenheit (Tabelle in Figuren.docx, ohne Frederick). Die SuS treten aus den
    Rollen heraus (Freeze) und sprechen als sie selbst. Am Ende ein Chortext über Scheitern und Angst.
  - Muss bleiben: Akt 1 Lloyd von hinten, Poppy durch die Seitentür, „Und Bitte!“, Ersatz aus dem Publikum für
    Selsdon, Belinda zum Publikum, Kontaktlinsen, Aufdeckmoment, Poppy schließt unter Tränen den Vorhang;
    Akt 2 Blumen- und Whisky-Verwechslung, manche wollen nicht auftreten, Durchsagen, Meditation (Traumreise?),
    vor und hinter der Bühne; Akt 3 Durchsagen unterbrechen Tim, Chaos, Freeze, Chor.
  - Rahmen: 18 SuS, etwa 20 Einheiten à 60 Min plus 2–3 halbe Tage. Die SuS kennen Kompositionsmethoden,
    chorisches Sprechen, Status und bewegte Standbilder.
  - Offen bei Lia: Figurensplitting (nach Ebenen oder nach Text, ab welchem Akt), Schwerpunkt Akt 2
    (Backstage-Zeitlupe, normales Tempo oder Publikumsaktion), eigene Partitur oder Montage aus Originalfragmenten.
  - Lias Unsicherheit: Sie weiß nicht, wie sie kürzen und weitermachen soll. Inhaltlich ist es ihr noch zu lasch.
    Unklar ist auch das Stück im Stück: Sie möchte etwas Kurzes, das sich die SuS selbst ausdenken.

## Rechte
- Die PDF ist eine Ansichtssendung des Deutschen Theaterverlags; laut Vermerk sind Kopien für Einstudierung,
  Aufführung oder Unterricht ohne Vertrag verboten.
- Jan 29.10.2026: Lia hat alles mit dem Verlag geklärt (Bearbeitung und Ausgabe des Textes). Der Agent darf
  deshalb Stücktext ausgeben, auch Strich- und Spielfassungen. Den Vertrag selbst habe ich nicht gesehen.
- Originaltext tippt Claude nicht ab: Claude wählt Stellen über Nummern aus, Python übernimmt sie wörtlich aus
  der Textfassung. Neue Texte (Chortext, Einstieg, Heraustreten) sind als neu gekennzeichnet.

## Plan (Vorschlag an Jan 29.10.2026, noch nicht freigegeben)
Zur Einordnung: Das Original hat rund 165 Seiten Text und dauert etwa 2,5 Stunden. Lia hat je Akt 10 Minuten,
davon geht ein Teil an eigene Szenen (Publikum, Freeze, Chor). Das ist eher eine Montage aus wenigen
Originalfragmenten als eine Kürzung. Das ist meine Einschätzung, keine gemessene Zahl; der Agent soll sie im
ersten Lauf mit Seitenzahlen und geschätzter Dauer belegen.

1. Szenenkarte (ein Lauf, Opus): Python zerlegt die Textfassung in Repliken und Regieanweisungen mit fester
   Nummer und PDF-Seite. Claude baut je Akt eine Liste der Spielanlässe: Nummern von–bis, Figuren, worum es
   geht, warum es komisch ist, ob es zu Lias Muss-Liste gehört. Python prüft die Nummern und schätzt die
   Spieldauer aus der Wortzahl. Ergebnis als docx/PDF in Lias Stil (renderer, Profil wie lia/unterricht).
2. Ablaufvorschlag und Spielfassung (zweiter Lauf, gleiche Sitzung): Bausteine für 35–40 Minuten: welche
   Originalfragmente (als Nummern), wo eigene Szenen, Publikumsmomente, Freeze und Chor liegen. Python baut
   daraus die Spielfassung: Originaltext wörtlich, neue Texte markiert, dazu eine Strichübersicht je Akt.
   Python rechnet die Zeiten zusammen und prüft, dass jede Muss-Stelle genau einmal vorkommt. Zu Lias offenen Fragen je zwei
   Varianten mit Vor- und Nachteil (Figurensplitting: 18 SuS auf 9 Figuren ergibt genau 2 je Figur;
   Schwerpunkt Akt 2). Gegen „zu lasch“: Vorschläge, die an ihr Thema Scheitern und Angst und an das anknüpfen,
   was die SuS können (ihre ABs aus data/text als Kontext, ohne Bewertungsdaten).
3. Stück im Stück: eine Szenenaufgabe im Stil ihrer Szenenaufgaben, mit der die SuS ein Mini-Stück von etwa
   3–4 Minuten selbst erfinden. Vorgaben so, dass die Pannen der drei Akte darin möglich sind (Türen, ein
   Requisit, das verwechselt wird, Auftritte, ein Satz, der immer wieder kommt).
4. Übergabe: erst Jan zur Vorschau, dann an Lia (wie lia/recherche). Ihr Feedback läuft über ihre Zentrale
   (lia-feedback), daraus wird die nächste Runde.
- Gestartet von Hand (wie lia/examen), kein Dienst.
- Pakete: pypdf und die Renderer-Pakete in den Versionen von lia/examen. Braucht Jans Okay.
- Kostengrenze: Vorschlag 5 USD je Lauf, danach Abbruch mit Meldung an Jan.
- Tests für Zerlegung in Repliken, Nummernprüfung, Zeitrechnung, Muss-Liste und den Bau der Spielfassung;
  Eintrag in pruefen.sh.

## Aufbau
- Instanz: AGENTKIT_INSTANZ=/home/agent/agenten/lia/instanz
- .venv: lia/theater/.venv, agentkit und renderer per agentkit.pth
- Laufzeitdaten: lia/theater/data/, Logs: lia/theater/logs/ (beide nicht im Repo)

## Entscheidungen
- 29.10.2026: eigener Ordner lia/theater statt Teil von lia/unterricht (Jan: zweites Fach, eigener Agent).
- 29.10.2026: Bewertungsdaten aus Lias Zip werden nicht verwendet (Schülerdaten).

## Offene Punkte
1. Jan: Plan, Pakete und Kostengrenze freigeben.
2. Fragen an Lia (über Jan):
   - Frederick (Philip/Scheich) fehlt in Figuren.docx. Fällt die Figur weg, oder ist sie nur vergessen?
   - Termin der Aufführung und bis wann sie den Ablaufvorschlag braucht.
   - PDF nennt „Kurs DS 12. Klasse“, das Material heißt „11. Klasse 25/26“: gleiche Gruppe, jetzt in Klasse 12?

## Gelernte Regeln
- (noch keine)
