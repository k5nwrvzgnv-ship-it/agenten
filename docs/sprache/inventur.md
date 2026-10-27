# Inventur: Texte, die an Menschen gehen (Stand 27.10.2026)

Schritt 1 des Auftrags „Sprache der Zentralen“. Grundlage: String-Literale im Code und die echten gesendeten
Texte aus `shared/meldungen/gesendet` (56), `shared/auftraege/erledigt` (13), `lia/instanz/auftraege/erledigt` (1),
dazu die Entwürfe in beiden `freigabe/`. Lias Instanz hat bisher kaum echten Verkehr: ein Ergebnis (Fehler) und
keine gesendete Meldung. Alles, was Lias Agenten bisher schreiben, ging an Jan.

Spalten: **Länge** = sichtbare Zeichen (typisch, bei Agenten echte Spanne). **Schritt** = nennt die Nachricht,
was als Nächstes passiert oder was zu tun ist (ja/nein). **WSTF** = 1. Wiener Sachtextformel (Schulstufe,
niedriger = leichter), nur wo sinnvoll gerechnet. Namen und Mailadressen Dritter sind durch [Name] ersetzt.

## A. Jans Zentrale (shared/telegram, agentkit)

| # | Anlass | Wortlaut (gekürzt) | Fachbegriffe | Länge | Schritt | Quelle |
|---|---|---|---|---|---|---|
| A1 | Auftrag angenommen | „Uni ist dran (lernen), mit 2 Dateien: a.pdf, b.pdf.“ | lernen (Modus), Dateinamen | 15–90 | nein | logik.py:170 |
| A2 | Ergebnis erledigt | „**Uni**“ + Ergebnis des Agenten, darunter 4 Feedback-Knöpfe | (vom Agenten, siehe C) | 50–3800 | – | logik.py:140, vorlagen.py |
| A3 | Ergebnis mit Kern | Kern, ≤ 3 Punkte, „Bitte prüfen: …“, aufklappbare „Belege“ | Belege | 300–3800 | ja | vorlagen.py:64 |
| A4 | Ergebnis fehlgeschlagen | „**Uni** · hat nicht geklappt“ + Grund, sonst „Kein Grund angegeben, Details im Log.“ | Log | 40–500 | nein | logik.py:147 |
| A5 | Entwurf zur Freigabe | „**Uni** · Mail-Entwurf“, Titel, Inhalt, „Details:“ mit `an: ["…"]`, `begruendung: …` | JSON-Listen, Feldnamen (an, cc, begruendung) | 300–3800 | ja (Knöpfe) | logik.py:43 |
| A6 | Klick Freigeben/Ablehnen/Ändern | „Freigegeben. Der Agent führt es jetzt aus.“ / „Abgelehnt.“ / „Was soll geändert werden? Schreib es als nächste Nachricht.“ | Agent | 10–60 | ja | zentrale.py:593 |
| A7 | Freigabe-Fehler | „Nicht möglich: {Fehlertext aus freigabe.py}“ | roher Fehlertext | 20–200 | nein | zentrale.py:609 |
| A8 | Änderungswunsch weiter | „Änderungswunsch an uni weitergegeben mit 1 Datei(en).“ | Agent klein, „Datei(en)“ | 40–70 | nein | zentrale.py:431 |
| A9 | Entwurf ausgeführt | „**Uni**“ „Ausgeführt: Mail: Test …“ + Text des Agenten; „Hat nicht geklappt: …“ + „Fehler: {f}“ | roher Fehlertext | 40–300 | nein | zentrale.py:682 |
| A10 | Ausführung unklar | „Unklar, ob das erledigt wurde: … Begonnen, aber nie fertig gemeldet. Bitte selbst prüfen.“ | – | ~120 | halb (wo prüfen?) | zentrale.py:689 |
| A11 | Weitergabe bleibt liegen | „Uni hat Dokumente einen Auftrag gegeben, aber Dokumente läuft noch nicht. Der Auftrag wartet.“ | „läuft noch nicht“ | ~100 | nein | logik.py:151 |
| A12 | Kontingent leer / frei | „Das Claude-Kontingent ist aufgebraucht. Deine Aufträge warten bis 14:00.“ / „… wieder frei, die Agenten arbeiten weiter.“ | Claude-Kontingent | 60–80 | ja | logik.py:159 |
| A13 | Panel Start | „Agentenzentrale“ „Stufe: normal  \|  5h 6 %  7d 1 %“ „Entwürfe: 0  \|  Aufträge offen: 0“ | Stufe, 5h, 7d | ~90 | nein | zentrale.py:197, logik.py:305 |
| A14 | Panel Agent | „Auftrag an uni / Modus: erledigen / Schreib den Auftrag als nächste Nachricht. Wartende Dateien hängen daran.“ Knopf „Modus wechseln: lernen“ | Modus, erledigen | ~110 | ja | logik.py:317 |
| A15 | Panel Verbrauch | „Stufe: sparen (1 Lauf gleichzeitig, jeder 2. Zeitlauf entfällt, kleineres Modell für Routine)“, „5 Stunden: 6 % (Reset …)“, „- uni: 3 Läufe, 120k Tokens, 4.2 min“ | Stufe, Lauf, Zeitlauf, Modell, Reset, Tokens, min | 250–500 | nein | logik.py:80 |
| A16 | Panel Status, /status | „Offene Entwürfe: 1 / Warten auf Ausführung: 0 / Unklare Ausführungen: 0 / Offene Aufträge: 0 / Sitzungen am PC: 0 / Wartende Dateien: 0“ | Ausführung, Sitzung | ~150 | nein | zentrale.py:186 |
| A17 | Hilfe, /hilfe, unbekannter Befehl | Befehlsliste: „/uni <Auftrag> (erledigen)“, „/unilern …“, „/pc … Sitzung am PC fortsetzen“, „/weiter“, „/verbrauch Auslastung des Claude-Kontingents“ … | Befehle, Sitzung, Modus, Kontingent | ~900 | ja | zentrale.py:95 |
| A18 | Auftrag nicht angelegt | „Auftrag nicht angelegt: {e}“ | roher Fehlertext | 30–200 | nein | zentrale.py:299 |
| A19 | Sitzung | „Zu diesem Auftrag ist keine Sitzung gespeichert. Schick es bitte als neuen Auftrag.“, „Diese Sitzung liegt am PC …“, /pc: „cd ~/agenten/uni && claude --resume <id>“ | Sitzung, Befehl mit ID (gewollt) | 50–200 | ja | zentrale.py:342–376 |
| A20 | Text ohne Befehl | „An welchen Agenten geht das? (Modus: erledigen)“, Knöpfe „uni“, „Verwerfen“; danach „Verworfen.“ / „Text nicht mehr vorhanden, bitte neu senden.“ | Agent, Modus, Name klein | ~45 | ja | zentrale.py:417 |
| A21 | Datei zu groß / nicht geladen | „x.pdf ist größer als 20 MB, das lässt Telegram für Bots nicht zu. Bitte am PC in den Agent-Ordner legen.“ / „… konnte nicht geladen werden ({e}). Bitte noch einmal schicken.“ | Bots, Agent-Ordner, roher Fehler | 80–200 | ja | zentrale.py:497, 507 |
| A22 | Dateien warten | „Unbekannter Befehl in der Bildunterschrift. 2 Datei(en) liegen bereit. Schick jetzt den Auftrag, z. B. /uni …. Die Dateien hängen dann daran. /verwerfen löscht sie.“ | Befehl, „Datei(en)“ | ~160 | ja | zentrale.py:546 |
| A23 | Datei nicht gesendet | „Uni: Datei x.pdf kam nicht durch ({f}).“ | roher Fehlertext, Dateiname | 40–200 | nein | zentrale.py:140 |
| A24 | Knopf alt/doppelt | „Unbekannter Knopf“, „Schon beantwortet“, „Dieser Knopf ist nicht mehr aktuell.“, „Gewählt: Gut“ | – | 10–40 | nein | zentrale.py:603–641 |
| A25 | Feedback-Knöpfe | „Passt“, „Zu lang“, „Falscher Fokus“, „Feedback schreiben“; „Nur hier kürzer“, „Ab jetzt immer kürzer“; Frage „Was hätte im Mittelpunkt stehen sollen? …“; „Danke!“ / „Danke, ich kümmere mich darum.“ / „Feedback nicht angelegt: {e}“ | Fokus | 5–80 | ja | vorlagen.py:24 |
| A26 | Feedback-Zusammenfassung | „**Feedback**“ „Lia zu recherche: „Falscher Fokus: …““ + Satz + „Art: Regel (dauerhaft), nur für recherche“ + „Passiert: „…“ in /tmp/claude-1002/…/recherche/STATUS.md“, Knopf „Stopp“ | Art, Regel (dauerhaft), Agent klein, **Pfad**, Notiz, Nachbesserung | 300–700 | nein | feedback.py:209, 225 |
| A27 | Feedback-Vorschlag | „Nicht automatisch übernommen: Kosten der Nachbesserung unbekannt“ „Vorschlag: neuer Auftrag an den Agenten: …“, Knöpfe Übernehmen/Verwerfen | Nachbesserung, Kosten | 300–800 | ja (Knöpfe) | feedback.py:220 |
| A28 | Antwort auf Stopp | „Gestoppt. Regel entfernt (1 Zeile). Lia weiß Bescheid.“ (echt gesendet 27.10.); „Schon entschieden (Stand: gestoppt).“; „Zeile entfernt, Commit fehlgeschlagen: …“ | Zeile, interner Stand, Commit | 30–250 | nein | feedback/lauf.py:176, 201, 214 |
| A29 | Feedback-Dienst Fehler | „Feedback-Dienst: Fehler bei {id}: {Typ}: {f}“; „Feedback {id} steht in {pfad}, der Commit ist fehlgeschlagen: …“; „… Konnte ich nicht zuordnen ({f}). Bitte selbst ansehen.“ | ID, Exception-Typ, Pfad, Commit | 80–400 | halb | feedback/lauf.py:108, 144, 232 |
| A30 | Ausfall eines Dienstes | „**Störung**“ „Uni-transkript ist ausgefallen: zu wenig Arbeitsspeicher. Ich melde mich dazu frühestens in 6 Stunden wieder.“ | Dienstname mit Bindestrich, Arbeitsspeicher | ~110 | nein | agentkit/ausfall.py:58 |
| A31 | Sicherung fehlgeschlagen | „Sicherung nach GitHub fehlgeschlagen: {git-Ausgabe}“ | GitHub, rohe Ausgabe | 50–300 | nein | sicherung/sicherung.py:59 |

## B. Lias Zentrale (shared/telegram/portal*.py, agentkit.feedback, lia/unterricht)

| # | Anlass | Wortlaut (gekürzt) | Fachbegriffe | Länge | Schritt | WSTF | Quelle |
|---|---|---|---|---|---|---|---|
| B1 | Panel Start | „Zentrale“ „Hallo Lia!“ „Unterwegs: 0  \|  Fertig: 3“ „Material erstelle ich schon. Wochenüberblick und Antworten auf Fragen kommen bald.“ | „Zentrale“ | ~140 | nein | – | portal_logik.py:94 |
| B2 | Anleitung Material / Frage | „Schreib mir einfach, was du brauchst: Fach, Klasse, Thema, Dauer. Zum Beispiel: …“ / „Schreib mir deine Frage als nächste Nachricht.“ | – | 45–130 | ja | 6,9 | portal_logik.py:40 |
| B3 | Bestätigen | „Neues Material / {Text} / Mit 1 Datei. / So abschicken?“ ✓ Abschicken ✕ Abbrechen | – | ~60+Text | ja | – | portal_logik.py:116 |
| B4 | Text ohne Menü | „Was soll ich damit tun? „…““ Knöpfe „Als Materialwunsch“, „Als Frage“, „✕ Verwerfen“ | – | ~40+Text | ja | – | portal_logik.py:125 |
| B5 | Dateien warten | „1 Datei liegt bereit. Schreib mir jetzt, was ich damit machen soll, z. B. „Mach daraus ein Arbeitsblatt für Klasse 8“.“ | – | ~110 | ja | – | portal_logik.py:131 |
| B6 | Abgeschickt | „Ist unterwegs: „…“ (mit 1 Datei) Ich melde mich mit der Antwort.“ | – | ~80 | ja | – | portal.py:117 |
| B7 | Meine Anfragen | „• Neues Material: Arbeitsblatt kategorischer Imp… – unterwegs“ | – | 50–400 | nein | – | portal_logik.py:147 |
| B8 | Hilfe | „So funktioniert's / Neues Material: … / Meine Woche: … / … Antworten kommen als eigene Nachricht mit einem Knopf zurück ins Menü.“ | Menü | ~640 | ja | – | portal_logik.py:54 |
| B9 | Ergebnis | „Zu deiner Anfrage „…“:“ + Ergebnis (Kern, Punkte, „Bitte prüfen“, Belege) + Passt / Zu lang / Falscher Fokus / Feedback schreiben / ☰ Menü | Belege, Fokus | 60–3800 | ja | 3,7 (Kern) | portal_logik.py:231 |
| B10 | Ergebnis Fehler (echt 22.10.) | „Gerade ist das gemeinsame Kontingent aufgebraucht. Bitte schick den Wunsch ab 23.10. 00:00 noch einmal.“ | Kontingent, 00:00 | ~100 | ja | 7,0 | lia/unterricht/agent.py:33 |
| B11 | Fehler allgemein | „Das hat leider nicht geklappt. Sag Jan bitte Bescheid.“ (Jan bekommt in diesem Fall keine Meldung) / lia/unterricht: „… Jan ist informiert.“ | – | ~55 | ja, aber widersprüchlich | 0,9 | portal_logik.py:65 |
| B12 | Datei-Probleme | „Die Datei ist größer als 20 MB, das lässt Telegram nicht zu. Schick sie Jan bitte anders.“, „Eine Datei konnte ich leider nicht schicken. Sag Jan bitte Bescheid.“ | MB | 60–90 | ja | – | portal.py:194, portal_logik.py:227 |
| B13 | Sonstiges | „Sprachnachrichten kann ich noch nicht annehmen. Schreib mir bitte als Text.“, „Dieser Knopf ist nicht mehr aktuell.“, „Abgebrochen.“ | – | 10–80 | teils | – | portal.py:245–295 |
| B14 | Platzhalter (Woche, Frage) | „Der Wochenüberblick kommt bald. Dein Wunsch ist notiert.“, „Ist angekommen. Diese Funktion kommt bald.“ | Funktion | ~55 | ja | – | lia/unterricht/agent.py:27 |
| B15 | Feedback-Frage | „Feedback / Was hätte im Mittelpunkt stehen sollen? Schreib es mir als nächste Nachricht.“ | – | ~90 | ja | – | portal_logik.py:163 |
| B16 | Feedback-Bestätigung | „**Zu deinem Feedback** „Falscher Fokus: …““ + „Danke, übernommen. Ab jetzt gilt: {Regel}“ / „Danke. Die Nachbesserung läuft, das neue Ergebnis kommt hierher.“ / „Danke, für später notiert. Das braucht eine Programmänderung, Jan baut es bei Gelegenheit ein.“ / „Danke. Das lege ich Jan zur Entscheidung vor …“ | Nachbesserung, Programmänderung, Vorsatz „Falscher Fokus:“ im Zitat | 80–500 | ja | 2,0–4,9 | vorlagen.py:136, feedback.py:196 |
| B17 | Feedback Fehler | „Zu welchem Ergebnis das gehört, finde ich nicht mehr. Schreib es bitte noch einmal.“, „Danke, ist angekommen. Jan schaut es sich an.“ | – | ~80 | ja | – | feedback/lauf.py:132, 145 |
| B18 | Jan stoppt / entscheidet | „Jan hat dein Feedback „…“ zurückgenommen: Die Regel ist wieder gestrichen.“ / „Jan hat dein Feedback „…“ übernommen. Danke, übernommen. Ab jetzt gilt: …“ (doppeltes „übernommen“) | Regel | 80–300 | nein | – | feedback.py:240–248 |

## C. Texte der Agenten an Jan (echt gesendet)

| # | Agent, Anlass | Wortlaut (Auszug) | Fachbegriffe | Länge | Schritt | WSTF |
|---|---|---|---|---|---|---|
| C1 | uni, Mails (10x) | „Wichtige Uni-Mails (3 neue geprüft): - Moodle (moodle-forum@hnee.de): Überfällig: … Schnell einreichen: https://lms.hnee.de/…“ | Mailadresse, URL | 150–1200 | meist ja | 4,8–11,5 |
| C2 | uni, Fristen (5x) | „Aufgabe Nachfrist endet morgen (17.10. 12:49): … Kurs: … https://…“; „Achtung: Teamabgabe, aber du bist in keiner Gruppe. Erst eintragen (Belegung in uebersicht.md).“ | URL, **Dateiname** | 100–250 | ja | 2,7–8,2 |
| C3 | uni, neues Material (8x) | „Neues Material in Bauklimatik: - 05 Projektbearbeitung/Dämmwerk-Datei (Import Cascados)/251020-Beispiel-Datenimport-neu.zip“; „(Keine Einordnung: Claude war gerade nicht verfügbar.)“ | **Pfade, Dateinamen**, Claude | 80–900 | nein | 9,8–15,7 |
| C4 | uni, Transkript (4x) | „Aufzeichnung transkribiert: Fertigung im Holzbau 1 (BBHbf01) 26_27/10 Video-Aufzeichnungen/….mp4 Text: ….mp4.txt“ | **Pfade, Dateinamen** | ~200 | nein | 10,4–12,3 |
| C5 | uni, Normen (2x) | „Normen aufbereitet (29 neu): - DIN 276 (2018-12), 56 Seiten: bauphysik_lca/DIN 276_2018-12-00_DE_2873248.pdf …“ | **Pfade, Dateinamen** | 90–3000 | nein | 1,1 (täuscht) |
| C6 | uni, Schritt-Fehler (2x) | „Schritt post_pruefen fehlgeschlagen: TimeoutError: [Errno 110] Connection timed out / Weitere Fehler dieses Schritts heute nur im Log: uni/logs/uni.log“ | **Funktionsname, Exception, Englisch, Pfad** | ~130 | nein | 3,4–6,3 |
| C7 | uni, Ergebnisse (9x) | „… Volles Protokoll: protokolle/20261016-124856-uni-38fdf6.md“, „kurse.py schreibt jetzt …“, „nicht committet, weil ich in diesem Auftrag kein Bash hatte“, „wenn du uni.service von Hand startest“, „Sie liegt nur auf dem Server: data/termine/20261027-…/“ | **ID, Pfad, Dateiname, Dienst, Bash, committet** | 400–1600 | meist ja | 4,1–7,8 |
| C8 | uni, Tests (27.10.) | „Guten Tag“, „T“, ganze Mail mit Kopfzeilen | – | 1–900 | nein | – |
| C9 | dokumente, Ergebnis | „Zusammenfassung „…“, 3 Seiten. Kontrolle (2. Runde): alle 10 Behauptungen der Liste enthalten, nichts dazuerfunden. … Offene Fragen: keine.“; Fehler: „Fehler im Agenten ({Typ}): … Details: dokumente/logs/dokumente.log“ | Kontrollrunde, Behauptungsliste, Pfad | 300–700 | ja | 9,5 |
| C10 | recherche für Lia (17x) | „Lia, Agent recherche: Quellenregister. stgb-46: Gemeinfreiheit frei …“; „… (2 von 2, OCR 0.85) …, 0.60 USD“; „Webauftrag fertig: 31 von 49 Aussagen belegt … Belege: 51 bestanden, 0 durchgefallen … (erste Prüfung: 51/1/0) … Kosten 0.01 USD in 1 Läufen. Datei: /home/agent/…/Recherche.docx“; „Fallsuche 20261027-115658 abgebrochen … Fortsetzen mit --weiter /home/agent/…“ | **IDs, USD, OCR, Pfade, Befehl, Fenster-Namen (social_media)** | 150–1400 | selten | 4,4–12,2 |
| C11 | examen für Lia | „Lia, Agent examen: Runde 1 fertig (2.47 USD, Version b9090a0). Bericht: /home/agent/…/bericht.md“ | **USD, Commit-Hash, Pfad** | ~300 | nein | 3,8 |
| C12 | unterricht für Lia | „Lia, Agent unterricht: Materialwunsch von Lia nicht bearbeitet: Kontingent erschöpft, wieder frei ab 23.10. 00:00“ | Kontingent | ~110 | nein | 9,3 |
| C13 | uni, Mail-Entwurf (Freigabe) | Titel „Mail: AW: …“, Inhalt mit An/Cc/Betreff, „(Warum: …)“, Details mit u-Nummern | – | 600–900 | ja (Knöpfe) | 4,4 |

## D. Lia: Wortschatz und Beschwerden über Form und Länge (lia/auswertung, nur gelesen)

Quelle: 1.108 Nachrichten von Lia in 27 Chats (anonymisiert), 284 Korrekturen (von Claude eingeordnet, ungeprüft).
Die Beschwerden betreffen Claudes Antworten in claude.ai, nicht Telegram, zeigen aber, was sie stört.

- **Ihre eigenen Nachrichten:** Median 11 Wörter, 80 % unter 23 Wörtern. Klein geschrieben, umgangssprachlich
  („vllt“ 65x, „idk“, „mh“, „ne“). Fachkürzel aus der Schule wie selbstverständlich: AB (31), UB (24), BBB (38), SuS.
  Fachbegriffe aus Ethik und Didaktik (Reihenfrage, Merksatz, Position) sind ihr Alltag, Technikwörter kommen fast
  nicht vor (Datei 2x, PDF 1x, „word blatt“). „Feedback“ benutzt sie selbst („das Feedback zum letzten UB“).
- **Form (48 Korrekturen):** Fließtext statt Unterteilungen, ganze Sätze, „in einem Satz am Anfang kurz zusammenfassen
  und dann verständlich in Stichpunkten“, „ohne Zitate“, „du musst nicht verweisen auf die stellen!!!“, „ohne zum beispiel“.
- **Umfang (31):** „kürzer“, „bitte nochmal etwas kürzen“, „jetzt bitte schmälern und nur das wichtigste“, „je 1 Satz“,
  aber auch „ein ticken länger ist ok“, „etwas ausführlicher. etwas!“. Richtung klar: kurz, auf Wunsch mehr.
- **Stil (18):** „weniger eloquent“, „nicht so geschwollen“, „Umgangssprache vermeiden“, „so, als hätte ich das geschrieben“,
  „der zweite Satz ist so abgehackt“. Also: einfach, aber nicht flapsig und nicht im Telegrammstil.
- **Unverständnis:** „hä und was ist dieses p? was trägt man da ein“, „was heißt unbedarft“, „was bedeutet das
  „gebührende“?“, „ich bin schon wieder verwirrt“ (6x „verwirrt“). Unbekannte Kürzel und Fremdwörter lösen Rückfragen aus.

## Befunde

1. **Lias Agenten schreiben an Jan, nicht an Lia** (C10–C12): Präfix „Lia, Agent recherche:“, voll mit IDs, Pfaden, USD,
   OCR-Werten. Das ist der Teil mit dem meisten Jargon und läuft über Jans Zentrale.
2. **Pfade und Dateinamen** sind der häufigste Fachbegriff in echten Nachrichten an Jan (C2–C7, C9–C11, A26).
3. **Rohe Fehlertexte** (`{e}`, `{f}`, Exception-Namen) an 9 Stellen in Jans Zentrale (A7, A9, A18, A21, A23, A25, A28,
   A29, A31) und bei uni (C6). Keine davon sagt, was jetzt passiert.
4. **Kein durchgehender Sprecher:** Bei Lia spricht „ich“, aber „Zu deiner Anfrage“ klingt nach Amt. Bei Jan steht der
   Agent fett darüber, die Zentrale redet von „der Agent“, Agentennamen mal groß („Uni“), mal klein („uni“, „recherche“).
5. **Widerspruch bei Lia:** „Sag Jan bitte Bescheid“ (B11, B12), obwohl Jan teils schon eine Meldung bekommt, und umgekehrt
   „Jan ist informiert“ nur in lia/unterricht. Ein Text darf nur sagen „Jan weiß Bescheid“, wenn es stimmt.
6. **Lesbarkeit allein misst Jargon schlecht:** Die Normenliste (C5) bekommt WSTF 1,1 („sehr leicht“), weil Pfade in kurze
   Stücke zerfallen. Lesbarkeitsmaß und Jargon-Prüfer gehören zusammen, Pfade und URLs vor der Messung entfernen.
7. **Wenig echtes Material für Lia:** Für die Handy-Bilder (Schritt 5) nehme ich die echten Ergebnisse von recherche
   (Webauftrag, Fallsuche) und dem Feedback-Nachweis, dargestellt in Lias Vorlage, wie heute in den Snapshots.
