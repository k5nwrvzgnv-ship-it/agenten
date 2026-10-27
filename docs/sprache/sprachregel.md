# Sprachregel der Zentralen (von Jan angenommen 27.10.2026)

Gilt für jede Nachricht, die Lias oder Jans Zentrale schickt, auch für Ergebnisse und Meldungen der Agenten.
Telegram ist die Oberfläche: Was dort steht, muss ohne Technikwissen verständlich sein. Technik steht im Log.

## Für beide
- **Duzen**, freundlich, sachlich. Keine Ausrufe, kein Lob für sich selbst, keine Emojis.
- **Das Wichtigste zuerst:** Die erste Zeile sagt, was fertig ist oder was passiert ist. Erklärungen danach.
- **Fehler und Warten** immer in zwei Teilen: (1) was passiert ist, in Alltagsworten; (2) was jetzt passiert oder
  was du tun kannst, mit Zeit, wenn es eine gibt. „Jan weiß Bescheid“ nur, wenn Jan wirklich eine Meldung bekommt.
- **Zahlen:** Uhrzeit „14 Uhr“, „Mitternacht“; Datum relativ („morgen“, „Donnerstag, 29.10.“). Einzahl und Mehrzahl
  ausschreiben („1 Datei“, „2 Dateien“, nie „Datei(en)“).
- **Formatierung:** Fett nur für die erste Zeile (Absender oder Thema). Höchstens 3 Aufzählungspunkte. Lange Teile
  (Belege, Listen) aufklappbar. Deutsche Anführungszeichen „…“.

## Lia (Laiin)
- **Wer spricht:** eine Stimme, „ich“. Keine Agentennamen, keine Systemteile. Jan heißt „Jan“.
- **Länge:** Satz höchstens 15 Wörter. Nachricht höchstens 600 Zeichen ohne aufklappbaren Teil.
- **Ton:** einfach, aber nicht flapsig und nicht im Telegrammstil (ihre Kritik: „weniger eloquent“, „nicht so
  abgehackt“). Schulwörter (Arbeitsblatt, Reihe, Merksatz, Beleg, Feedback) sind erlaubt, Technikwörter nicht.
- **Lesbarkeit:** 1. Wiener Sachtextformel höchstens 6 (Schulstufe).

## Jan (Betreiber, aber ohne Technik im Alltag)
- **Wer spricht:** Absender fett in der ersten Zeile: der Agent mit großem Namen („Uni“, „Recherche (Lia)“) oder
  „Zentrale“ für alles vom System (Rechenzeit, Störung, Feedback). Der Absender spricht als „ich“.
- **Länge:** Satz höchstens 20 Wörter. Nachricht höchstens 800 Zeichen ohne aufklappbaren Teil.
- **Ausnahmen:** der Befehl unter /pc (zum Kopieren) und die Zahlen unter Verbrauch.
- **Lesbarkeit:** 1. Wiener Sachtextformel höchstens 8.

## Glossar: nie sagen, stattdessen sagen
| Nie | Stattdessen | Für |
|---|---|---|
| Agent, Agent unterricht, Dienst | „ich“ | Lia |
| uni, recherche (klein), „der Agent“ | „Uni“, „Recherche“ | Jan |
| Auftrag | „Anfrage“, „Wunsch“ | Lia |
| (Claude-)Kontingent, Limit, Stufe, 5h/7d, Reset | „Rechenzeit ist aufgebraucht, weiter ab 14 Uhr“ | beide |
| Lauf, Läufe, Zeitlauf, Tokens, Modell, Sonnet/Opus/Haiku | weglassen; Verbrauch: „Uni hat heute 3-mal gearbeitet“ | beide |
| Nachbesserung | „überarbeitete Fassung“ | beide |
| Regel (dauerhaft), Notiz, Art | „Ab jetzt gilt: …“ / „Wunsch für später notiert“ | beide |
| Programmänderung, Code, Oberfläche | „Das kann ich noch nicht. Jan baut es ein.“ | Lia |
| fehlgeschlagen, Fehler, Exception, Timeout, Login failed | „hat nicht geklappt“ + Grund in Worten („Moodle war nicht erreichbar“) | beide |
| Log, Pfad, Dateiname mit Endung, Ordner | Lia: nichts; Jan: „Einzelheiten am PC“ bzw. was es ist („die PDF“) | beide |
| ID, Commit, Version, Hash, --weiter, .service | weglassen | beide |
| USD, Kosten | Lia: nie; Jan: nur unter Verbrauch | beide |
| OCR, Schwelle, bestanden/durchgefallen, Kontrollrunde, Behauptungsliste | „geprüft“, „31 von 49 Aussagen haben einen Beleg“ | beide |
| Datei(en), Bot, MB | „1 Datei“ / „2 Dateien“, „zu groß für Telegram“ | beide |
| läuft noch nicht (Dienst) | „ist noch nicht eingerichtet“ | Jan |
| Zentrale, Panel | „Menü“ | Lia |

## Prüfung
agentkit.sprache: Jargon-Prüfer (Glossar, soweit als Muster eindeutig, dazu IDs, Pfade, Dateinamen, Beträge,
Modellnamen, rohe Fehlertexte, Bezeichner) und 1. WSTF. Gemessen wird Fließtext nach Entfernen von URLs, Pfaden, Zahlen
und Zitaten der Person („…“); Beschriftungen (bis 4 Wörter ohne Satzzeichen, z. B. „Neues Material“) zählen nur für die
Satzlänge; unter 10 Wörtern gilt nur die Satzlänge. Läuft über alle Snapshots (pruefen.sh) und zur Laufzeit über jede
ausgehende Nachricht (nur Warnung ins Log, ohne Inhalt).

## Entschieden (Jan 27.10.2026)
1. Grenzwerte wie oben: WSTF Lia 6 / Jan 8, Satz 15 / 20 Wörter, 600 / 800 Zeichen.
2. „Rechenzeit“ statt „Kontingent“, auch für Jan.
3. Absender „Zentrale“ für Systemnachrichten an Jan.
4. Lias Fehlertexte bleiben „Sag Jan bitte Bescheid“, wo Jan keine Meldung bekommt; keine neue Meldung.
5. Modus-Wörter: „Uni macht es allein“ / „Wir machen es zusammen“ statt „erledigen / lernen“.
