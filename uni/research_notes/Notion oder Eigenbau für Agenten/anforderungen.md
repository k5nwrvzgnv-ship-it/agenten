# Anforderungen an eine Arbeitsoberfläche für Jans Agenten-System (nur aus dem Repo, Stand 04.11.2026)

Kennzeichnung: **[B]** belegt, **[W]** von Jan gewünscht, noch nicht praktisch vorgekommen, **[V]** vermutet. Quellen sind Pfade relativ zu `/home/agent/agenten`, mit Zeile. "Gemessen" heißt: von mir am 04.11. per `wc`, `grep`, `git log`, `systemctl` erhoben. Keine Inhalte aus Mails, Schülerdaten oder `.env`. Kein Werkzeug wurde geprüft; die Zuordnung "Standardfunktion" ist nur aus Repo-Notizen und eigener Einordnung.

## 1. Kernaufgaben und Wünsche (belegt, gewünscht, vermutet)

### Takeaway
Belegt ist vor allem das Arbeiten am Dokument: lesen, kommentieren, neue Fassung prüfen, Lücken schließen. Die Ebenen mit freien Reitern und die gemeinsame Arbeit sind Jans klarster Wunsch, aber noch nie praktisch vorgekommen. Lernen über die Oberfläche ist Wunsch, die Nutzung ist bisher null.

### Cited Findings

**Kernaufgaben (Jan: "stimmen")** — [portal-oberflaeche.md:26-35, 84](uni/portal-oberflaeche.md). Grundlage ist klein: eine Kette, ein Projekt, drei Tage, vor dem Portal entstanden — [ebd.:18-19](uni/portal-oberflaeche.md).

| Nr. | Aufgabe | Einstufung |
|---|---|---|
| 1 | Aktuelle Fassung lesen, kommentieren, neue Fassung prüfen ("der agent schreibt und wir kommentieren") | [B], häufigste |
| 2 | Offene Stellen abarbeiten, Fehlendes nachliefern | [B] |
| 3 | Der Recherche kurz und sparsam nachfragen | [B], zwei Fälle |
| 4 | Von der Aussage im Text zur Quelle | [B] Bedarf am Text, [V] Weg über Belege |
| 5 | Verstehen und erklären, wie die Recherche zustande kam | [B] |
| 6 | Ergebnis an Gruppe oder Betreuung weitergeben | [B] |
| 7 | Stand mit Kontaktpersonen sehen, Interviews vorbereiten | [W] |
| 8 | Für die Prüfung üben, Karten und mündlich | [W] |
| 9 | Neue Recherche starten, vorab Überblick über den Ablauf | [W] |
| 10 | Gemeinsam kapitelweise arbeiten, jede Person mit Zugang | [W] |

**Jans Ebenen-Idee [W], nah an seinen Worten:** Oberste Ebene Kurs; darin frei benennbare, nachträglich umorganisierbare Reiter (Themenfindung, Exposé, Versuche, Interviews, Software, Hardware, Schriftlicher Teil); darunter weitere Ebenen, etwa Kapitel. "Auf den Ebenen kann man immer Dokumente oder Aufträge anlegen", jeder Auftrag und jedes Dokument hat einen Ort, "alle Fassungen gehören zu dem einen Dokument" — [portal-oberflaeche.md:117-122](uni/portal-oberflaeche.md). "Flexibilität" heißt: Reiter je Strukturebene hinzufügen oder entfernen, nicht Filter und Suche — [ebd.:89-92](uni/portal-oberflaeche.md).

**Weitere Aussagen von Jan**
- Portal heute: "furchtbar", zu viel Information, keine Hierarchie — [uni/STATUS.md:437](uni/STATUS.md).
- "wir sollten nicht das rad neu erfinden", "keine lust das rad neu zuerfinden" — [portal-oberflaeche.md:131, 238](uni/portal-oberflaeche.md).
- Kommentieren an der Textstelle im Browser: "erstmal zu kompliziert, lieber das mit dokumetnen und kommentaren optimieren und wirklich gut machen" — [ebd.:239](uni/portal-oberflaeche.md). Web-Editor: nein, Word bleibt — [webapp-plan.md:154, 230](uni/webapp-plan.md).
- Abnahme nach Jans Eindruck, keine Messung, kein Abbruchkriterium — [webapp-plan.md:255, 270](uni/webapp-plan.md).
- Überblick, "was die anderen gemacht haben" [W] — [portal-oberflaeche.md:124-125](uni/portal-oberflaeche.md).
- Zugriff vom Mac, ohne Tunnel, eigene Subdomain, HTTPS, Passwort — [webapp-plan.md:267](uni/webapp-plan.md). Handy-Oberfläche: nicht gebaut — [ebd.:235](uni/webapp-plan.md).
- Schriftverkehr im Portal, als Auszug; Schreiben und Freigeben bleibt in Telegram — [ebd.:268, 233](uni/webapp-plan.md).
- Jan will mehr lernen und das Portal dafür nutzen — [ebd.:263](uni/webapp-plan.md).

**Was Telegram nicht trägt [B]:** 27 Uni-Aufträge in 19 Tagen. Mail, Frage und Termin passen laut Plan in Telegram. Das Exposé verursacht 77 % der Kosten (71,42 von 92,71 USD Gegenwert, 5 Aufträge) und hat Telegram gesprengt; PDF-Kommentare wurden im Chat abgeschrieben, Rückmeldung zum Lauf fehlte ("hallo?") — [webapp-plan.md:36-53](uni/webapp-plan.md).

**Lias Anforderungen, von Jan vorgegeben (30.10.):** meist am PC; Gerüst Fach, Klasse, Reihe, Stunde; auf jeder Ebene Aufträge, die über Verbesserungen zu einem finalen Material werden; fester Chat für schnelle Fragen; Vorlagen verschiedener Art — [docs/webapp-aufbau.md:9-11](docs/webapp-aufbau.md). Lias echter Feedbackweg ist die in Word kommentierte und wieder hochgeladene Fassung — [ebd.:38-40](docs/webapp-aufbau.md). Lias Test: Aufbau gefällt, Ebene Stunde gewünscht; Zahlen wurden nicht erhoben — [ebd.:292-294](docs/webapp-aufbau.md). Lia arbeitet mit Word, Pages/Keynote und einer Schulplattform — [ebd.:59-62](docs/webapp-aufbau.md).

**Laufender Entscheid:** Notion-Test, Plan freigegeben, nichts gebaut: Datenbank "Aufträge", Knopf "Starten", Brücke per Timer alle 2 Minuten, nur Jans Konto, nur unkritische Recherchen, kein Exposé, nichts aus Lias Instanz, ohne Felix und Henri, ohne Kommentare an den Agenten — [STATUS.md:126-141](STATUS.md). Portal-Schritt 4 (Ebenen) pausiert bis zu Jans Urteil; Prüfungsseite und Lernen sind nicht betroffen — [portal-oberflaeche.md:6](uni/portal-oberflaeche.md).

### Inferences
- [V] Jan misst an zwei Dingen: Hierarchie und Ort. Fehlende Funktionen stehen in seinen Aussagen weniger im Vordergrund als die Unübersichtlichkeit.
- [V] Der belegte Hauptbedarf (Aufgaben 1 bis 6) liegt fast nur im Forschungsprojekt, also einem einzigen Arbeitsstrang. Alles darüber hinaus ist eine Erwartung für die Zukunft.

### Gaps
- Ob das Portal im Alltag genutzt wird, ist offen: Das Log taugt kaum, weil Tests und Jan nicht zu trennen sind — [portal-oberflaeche.md:20-22](uni/portal-oberflaeche.md).
- Jans Urteil zum Notion-Test liegt nicht vor; nichts gebaut — [STATUS.md:126](STATUS.md).

## 2. Was Lias Web-App und das Uni-Portal heute können, was besonders ist, Aufwand

### Takeaway
Zwei eigene Apps in sechs Tagen: Lias App rund 10.600 Zeilen mit 67 Routen und 82 Commits, das Portal rund 5.200 Zeilen mit 19 Routen und 7 Commits an einem Tag. Das Portal kann mehr, als genutzt wird. Karten wurden laut Dateien nie bewertet, die Übungsauswertung ist nicht eingerichtet.

### Cited Findings

**Größe, gemessen (Zeilen, ohne Bibliotheken)**

| | Lias Web-App `shared/webapp` | Uni-Portal `uni/portal` |
|---|---:|---:|
| Python ohne Tests | 4.744 | 1.843 |
| Tests (Zeilen) | 3.681 | 1.968 |
| Testfunktionen (`def test_`) | 204 | 186 |
| Vorlagen (Dateien / Zeilen) | 30 / 1.556 | 11 / 726 |
| CSS und eigenes JS | 630 | 642 (Kopie plus eigene Regeln, [uni/STATUS.md:366](uni/STATUS.md)) |
| **Summe Zeilen** | **rund 10.600** | **rund 5.200** |
| Routen (GET / POST) | 67 (29 / 38) | 19 (12 / 7) |
| Commits | 82 | 7 |
| Zeitraum | 30.10. bis 04.11. (41 am ersten Tag) | nur 04.11. |
| Git hinzugefügt / entfernt | +18.285 / -2.201 | +6.078 / -735 |

Dazu, gemessen: `agentkit/struktur.py` 699, `strukturpflege.py` 1.350, `fassungen.py` 261, `lia/chat` 544 (10 Commits), `uni/rueckmeldungen.py` 332, `uni/schriftverkehr.py` 90, `uni/lernmodell.py` 151. Planungsdokumente: `docs/webapp-plan.md` 526, `docs/webapp-aufbau.md` 312, `docs/struktur-pflege-plan.md` 646 (10 Commits), `uni/portal-oberflaeche.md` 371 (10 Commits), `uni/webapp-plan.md` 279 (6 Commits). Das Gesamt-Repo hat 578 Commits.

Routenverteilung Web-App, gemessen: klasse 16, ergebnis 13, reihe 11, fach 7; 41 von 67 sind Schulstruktur — deckt sich mit [webapp-plan.md:79-83](uni/webapp-plan.md). `shared/webapp` kann deshalb nicht einfach zweimal betrieben werden: Bindungen an Lia in Instanz, Dienstnamen und Agent-Ordner — [ebd.:97-101](uni/webapp-plan.md).

**Lias Web-App, Stand** — [shared/webapp/STATUS.md](shared/webapp/STATUS.md)
- Drei Spalten, Baum, Brotkrumen, "+ Neu hier" am Ort — Zeilen 17-27. "Heute" als Eingang quer über alle Orte, jede Zeile nennt ihren Ort — 22, 55, 63.
- Auftrag mit Feedback-Schleife ist ein Auftrag mit Verlauf (`logik.ketten`) — 65-69.
- Fassungen: Liste, final markieren (rückgängig), eigene Fassung hochladen, Rückmeldung als Text oder Datei, auch je Datei und Seite. Agenten sehen final und eigene Fassung — 80-102, 257.
- Seitenbetrachter, Varianten, Galerie, Formatvorlagen hochladen — 40-54, 123-128, 266-269, 285-290.
- Struktur pflegen mit Stundenplan, Ferien, Terminen, Ausfall mit Nachrücken, Rückgängig; schreibt nur über `agentkit.strukturpflege` — 181-210. Noch nicht abgenommen; im Browser ist nur Klasse und Reihe anlegen belegt — 181, 369.
- Chat "Fragen" mit Ortskontext, Netzsuche, Dateien, "Daraus Auftrag machen", etwa 0,03 USD je Frage — 270-284. Widerspruch im Dokument: Zeile 18 nennt die Spalte "Platzhalter", Zeile 347 den Dienst mit `WEBAPP_CHAT=an`.
- Fehlt: Konten (ein Passwort über Caddy, Passkeys später), Anmerkung an einer Stelle — 349, 359, 390, 395.
- Doppelklick-Schutz, Herkunftsprüfung, Token, strenge Kopfzeilen — 75, 103-114.
- Freigaben: keine Knöpfe. Entwurf "Setze ich selbst ein" liegt nur in der App, Jans Freigabe bleibt unberührt, Ändern geht über Jan — 136, 259-261.

**Uni-Portal, Stand** — [uni/STATUS.md:358-472](uni/STATUS.md), [uni/portal/app.py:1-30](uni/portal/app.py)
- Karten und FSRS: Bibliothek `fsrs` 6.3.2, dünne Schicht `lernmodell.py`; vier Knöpfe, große Bildkarten, Lernstand gemeinsam mit Telegram-Lernen, kein Claude-Lauf, Karte 6 bis 19 ms — Zeilen 362-363, 372-379. Pro Tag bis 8 neue — 374.
- Nutzung: `zustand.json` und `verlauf.jsonl` existieren am 04.11. nicht, also keine bewertete Karte (gemessen). Übungsordner: 0 (gemessen).
- Sprachübung: Die Stimme läuft bei ElevenLabs, das Portal verlinkt nur und nimmt das Transkript an — [webapp-plan.md:172](uni/webapp-plan.md), [uni/STATUS.md:384-388](uni/STATUS.md). Auswertung durch eigenen Agenten ohne Werkzeuge, gegen eine zu bestätigende Rubrik; jedes Zitat muss wörtlich im Transkript stehen; Kartenvorschläge per Klick — 389-410. Etwa 0,32 bis 0,82 USD je Lauf im Probelauf mit Kurztranskript — 414-415. Streuung bis 2 von 10 Stufen, "eine Einschätzung, keine Messung" — 417-418.
- Nicht betriebsbereit: `uni-portal-frage.path` ist inaktiv (gemessen), Einrichtung offen — [uni/STATUS.md:583-586](uni/STATUS.md). Rubrik war am 04.11. nicht bestätigt — 404.
- Recherche-Ansicht: nur lesend, Aussagen je Frage mit Statusfilter, Belegen, Quellen, Lücken, Literatursuche — 422-425. Standardansicht 16.635 Wörter, 163 Aussagen unter 24 Fragen, keine Suche, keine Verknüpfung Exposé zu Beleg, kein Nachfrageformular — [portal-oberflaeche.md:45-65](uni/portal-oberflaeche.md).
- Fassungen: Portal zeigt nur die aktuelle; kein Vergleich; Sicherung `vorher/` nur für den Agenten, Zurückholen von Hand — [portal-oberflaeche.md:70](uni/portal-oberflaeche.md), [uni/STATUS.md:452, 460-461](uni/STATUS.md). `agentkit.fassungen` nutzt der Uni-Agent nicht — [webapp-plan.md:145](uni/webapp-plan.md).
- Rückmeldung zum Exposé: Text oder kommentierte PDF/docx wird zum Auftrag in der Kette; Marke in Warteschlange, Pfad-Unit aktiv (gemessen). Echter Lauf 2:20 min, 10,38 USD wegen `--resume`; die Seite nennt "etwa 1 USD" — [uni/STATUS.md:448-471](uni/STATUS.md), [portal-oberflaeche.md:262](uni/portal-oberflaeche.md).
- Aufträge: Das Portal legt allgemein keine an und kennt keinen freien Auftrag; nur Rückmeldung und Übungsauswertung lösen Läufe aus — [uni/portal/app.py:9-27](uni/portal/app.py). "Aufträge an einem Ort" ist nur Jans Wunsch und Lias Muster — [portal-oberflaeche.md:97, 121, 216](uni/portal-oberflaeche.md).
- Freigaben: keine. Mails schreiben und freigeben bleibt in Telegram — [webapp-plan.md:199, 233, 268](uni/webapp-plan.md).
- Schriftverkehr: schmaler Auszug nur für eingetragene Kontakte, kein Postfachzugang — [uni/STATUS.md:426-431](uni/STATUS.md).
- Schutz: Web-Dienst lädt `uni/.env` nicht, Positivliste, kein Weg nach außen, belegt per Test — 369-371.
- Betrieb: Speicherspitze 83 MB, Grenze 200 MB — 468. Lia: 52 MB, Grenze 300 MB (gemessen). Aussehen laut Status nicht selbst geprüft, Screenshots von Jan ausgewertet — 381, [portal-oberflaeche.md:103-108, 140-144](uni/portal-oberflaeche.md). Erreichbarkeit widersprüchlich: "von außen noch nicht erreichbar" [uni/STATUS.md:361, 580](uni/STATUS.md) gegen "von außen ohne Passwort 401" (435); vermutlich ist 361 veraltet [V].

**Mängel, die Jan nach einem Tag Portal sah [B]:** Reiter, Ansicht und Status als drei Reihen, halbe Breite leer, Formular vor dem Text, technischer Hinweis offen auf der Seite, Rückmeldungen nur mit Uhrzeit benannt — [portal-oberflaeche.md:103-108, 140-144](uni/portal-oberflaeche.md). Betriebsrisiko des Eigenbaus: Vorlagen wirken sofort live, die Web-App antwortete am 04.11. rund 14 Minuten mit 500, `pruefen.sh` merkt das nicht — [shared/webapp/STATUS.md:322-324](shared/webapp/STATUS.md).

### Inferences
- [V] Der messbare Anteil liegt bei rund 15.800 Zeilen in den zwei Apps, plus Bausteinen in agentkit. Das Portal ist kleiner, weil es das Schulmodell nicht hat und bewusst nicht von Lias Code abhängt.
- [V] Das Portal hat bislang weniger geliefert, als die Zeilen vermuten lassen: Die Lern-Funktion ist gebaut, aber unbenutzt, die Hauptaufgabe von Jan ist mit "furchtbar" bewertet.
- [V] Git-Zahlen sind nur ein grobes Maß: viele Commits, oft Status-Zeilen, und die Summen enthalten Kopien (CSS, Schrift, htmx).

### Gaps
- **Aufwand in Stunden und Geld für den Bau ist im Repo nicht erfasst.** `laeufe.jsonl` zählt Agentenläufe, keine Entwicklungs-Chats. Der Plan schätzte "2-4 Chat-Sitzungen" für den Durchstich — [webapp-plan.md:110](uni/webapp-plan.md); tatsächliche Sitzungszahl nicht geprüft.
- Künftiger Pflegeaufwand ist nicht beziffert. Bekannt: Kopien laufen auseinander, die Trennung von Lias App kostet doppelte Sicherheitskorrekturen — [webapp-plan.md:108](uni/webapp-plan.md).
- Schätzungen für das noch nicht Gebaute: Personen und Überblick "mittel", Recherche-Start "mittel bis groß", Nachfrage "mittel" — [portal-oberflaeche.md:291, 316, 335](uni/portal-oberflaeche.md), alle [V]. Die Ebenen selbst haben keine Aufwandsangabe.

## 3. Harte Regeln, die jede Lösung einhalten muss

### Takeaway
Die Regeln treffen nicht die Anzeige, sondern das Handeln, die Daten und den Betrieb: Python handelt nach außen nur mit Freigabe, keine Schülerdaten in fremde Dienste ohne Klärung, Betrieb klein und isoliert. Für Jans Projektgruppe gibt es zudem Entscheidungen, die vom gewohnten Muster abweichen.

### Cited Findings

Alle aus [CLAUDE.md](CLAUDE.md), wenn nicht anders genannt.
- **Freigabe:** Nach außen nur nach Jans Freigabe des konkreten Entwurfs über `shared/freigabe/`, danach genau einmal ausführen und melden. Käufe zusätzlich nur bis `KAUF_LIMIT_EURO`.
- **Notion berührt das:** Der Test braucht eine befristete Ausnahme in CLAUDE.md, weil Ergebnisse ohne Einzelfreigabe in Jans eigenen Workspace gehen (Jans Okay 04.11.) — [STATUS.md:140](STATUS.md). In der aktuellen CLAUDE.md steht sie noch nicht (gelesen).
- **Architektur:** "Claude denkt, Python handelt". Claude nur über `agentkit.claude_lauf`, ohne Bash, Schreibschutz auf Code und Regeln. Warteschlangen sind Ordner mit JSON-Dateien. Telegram ist einziger Kontakt zu Jan, laut Architekturabschnitt.
- **Zugangsdaten:** nur `.env` mit chmod 600, nie im Repo. Jeder Agent eigene Zugangsdaten.
- **Isolation:** eigener Ordner, eigene `.venv`, eigener systemd-User-Dienst oder -Timer. Keine dauerhaft laufende Browser-Automation.
- **Tabus:** kcalbot und Vinted-Bot nicht anfassen, Ausnahmen eng begrenzt. Caddy-Änderungen betreffen denselben Dienst, über den kcal erreichbar ist, darum Jans Entscheidung und als root — [docs/webapp-plan.md:121](docs/webapp-plan.md).
- **Server:** Ubuntu, 4 Kerne, 7,8 GB, kein Swap, User `agent` ohne sudo. Gemessen: 7.941 MB gesamt, 1.553 MB verfügbar zum Messzeitpunkt (am Vormittag etwa 4.070 MB, [webapp-plan.md:130](uni/webapp-plan.md)). Jeder `claude`-Prozess etwa 280 MB — ebd. `pruefen.sh` nur mit Sperre, sonst Speichermangel (Projektgedächtnis).
- **Docker:** nicht vorhanden, `docker` und `podman` nicht im Pfad (gemessen); auch [docs/webapp-plan.md:496](docs/webapp-plan.md). Browser startet auf dem Server nicht, Bibliotheken fehlen, Installation braucht root — [ebd.:441](docs/webapp-plan.md).
- **Root:** Jan hat Root und macht Caddy und DNS selbst — [webapp-plan.md:202, 272](uni/webapp-plan.md). "Kein sudo" gilt für Agenten-Chats, nicht für Jan.
- **Pakete:** nur nach Jans Okay. Bordmittel bevorzugt.
- **Claude-Plätze:** 2 parallele Läufe, Sparstufe 1, über alle Agenten und Lia — [shared/einstellungen.toml:24-27](shared/einstellungen.toml), [webapp-plan.md:118](uni/webapp-plan.md). Das 7-Tage-Kontingent ist gemeinsam — [portal-oberflaeche.md:267](uni/portal-oberflaeche.md).
- **Feedback:** Lias Feedback wird ohne Freigabe übernommen, Jan hat Stopp-Knopf. Lias Aufträge und Nachbesserungen laufen ohne Jans Okay, egal wie oft und wie teuer.
- **Schülerdaten:** Vorschlag an Jan, nie automatisch. Verantwortlichkeit und Drittlandübermittlung sind laut Plan zu klären; K1 (Schule, Datenschutz) ist offen, Jan hat "Weg 2" trotzdem entschieden — [docs/webapp-plan.md:40-62](docs/webapp-plan.md), [shared/webapp/STATUS.md:389](shared/webapp/STATUS.md). Fester Hinweis "keine Namen", Bewertung und Noten gesperrt — [docs/webapp-plan.md:84-87](docs/webapp-plan.md). Namen nicht in Wissensbasis, Profil, Regeln — [docs/lia-architektur.md:134](docs/lia-architektur.md). Lerngruppe mit festem Hinweis — [docs/struktur-pflege-plan.md:387-388](docs/struktur-pflege-plan.md).
- **Uni-Daten:** Mails und `data/mailauftraege` nie im Portal, Normen und Skripte keine öffentlichen Links — [webapp-plan.md:194-195](uni/webapp-plan.md). Web-Dienst lädt keine Zugangsdaten — [ebd.:193](uni/webapp-plan.md).
- **Fertig heißt:** `./pruefen.sh` ALLES GRÜN, Commit nur mit `commit.sh`, neue Logik hat Tests.

### Inferences
- [V] Jede fremde Lösung müsste an `agentkit.auftraege` andocken und Python als einzigen handelnden Teil behalten. Das ist genau die Notion-Brücke im Testplan — [STATUS.md:134](STATUS.md).
- [V] Der Notion-Test schließt Lias Instanz aus, eine Entscheidung zu ihren Daten in einem fremden Werkzeug gibt es nicht. Ergebnisse des Tests gelten also zunächst nur für Jans Seite.

### Gaps
- Ob Claude-Konto oder fremder Dienst für Uni-Inhalte zulässig sind: Jan hat das eingeordnet, "kein Thema mehr" — [webapp-plan.md:266](uni/webapp-plan.md). Für Normen und Skripte in einem fremden Werkzeug steht nichts im Repo.
- Für Lias Daten in einem SaaS gibt es keine Entscheidung, nur die offene Klärung K1 — [docs/webapp-plan.md:155](docs/webapp-plan.md).

## 4. Was einzigartig ist, was Nachbau von Standard ist

### Takeaway
Die Zuordnung ist überwiegend Einordnung [V], gestützt auf die Vorbilder im Repo. Struktur, Reiter, Rechte und Aktivität sind Standard. Einzigartig ist die Kopplung an die Agenten: Auftrag am Ort, Fassungskette, Kosten und Warteschlange, Lernzustand, Beleg-Prüfung.

### Cited Findings

**Vollständige Anforderungsliste mit Einordnung.** Sp. "Wer": S = Standardfunktion eines Dokumentwerkzeugs zu erwarten [V], E = nur mit eigenem Code [V], B = fremdes Werkzeug plus eigene Brücke [V]. Vorbild-Belege stammen aus Dokumentation, nicht aus Benutzung, abgerufen über automatische Zusammenfassung — [portal-oberflaeche.md:148-151](uni/portal-oberflaeche.md).

| Anforderung | Status | Wer | Beleg |
|---|---|---|---|
| Baum, beliebig tiefe Ebenen, frei benennen, verschieben | [W] | S | Jan [portal-oberflaeche.md:117-122](uni/portal-oberflaeche.md); Notion-Doku ebd.:161; Umbenennen dort "nicht belegt" ebd.:167 |
| Reiter je Ebene anlegen, entfernen | [W] | S | ebd.:89-92 |
| Papierkorb, Wiederherstellen | [V] | S | ebd.:162 |
| Brotkrumen, "wo bin ich" | [B] bei Lia | S | [shared/webapp/STATUS.md:25-27](shared/webapp/STATUS.md) |
| Kommentare am Dokument, erledigen, Filter | [B]/[W] | S | [portal-oberflaeche.md:163, 188](uni/portal-oberflaeche.md), aber Markieren im Text nicht vorgesehen ebd.:239-240 |
| Datei mit Fassungen, Stapel, "alle Fassungen" | [W] | S bei Datei-Modell | Basecamp ebd.:175 |
| Benannte Fassungen, Vergleich | [W] | S teilweise | Overleaf, Confluence ebd.:186-198; Notions Automatik "passt schlecht" ebd.:166 |
| Überblick, wer was gemacht hat | [W] | S | ebd.:165, 174 |
| Drei Konten, alle dürfen alles | [W] | S | ebd.:124, 236, 271-281 |
| Suche | offen | S | im Plan nur "bei belegtem Bedarf" [webapp-plan.md:234](uni/webapp-plan.md) |
| PDF und Word herunterladen, weitergeben | [B] | S | [portal-oberflaeche.md:344](uni/portal-oberflaeche.md) |
| Zugriff vom Mac mit HTTPS | [B] | S | [webapp-plan.md:267](uni/webapp-plan.md) |
| Auftrag an einem Ort anlegen, Agent starten | [W] | B | "nichts Direktes" in den Werkzeugen [portal-oberflaeche.md:216](uni/portal-oberflaeche.md); Brücke [STATUS.md:131-135](STATUS.md) |
| Ergebnis und Dateien zurück an den Ort | [W] | B | [STATUS.md:135-136](STATUS.md), mit Grenzen 2.000 Zeichen, 100 Blöcke, 5 MB im Free-Tarif |
| Kommentare als Auftrag an den Agenten, in die Kette | [B] | B oder E | Portal gebaut [uni/STATUS.md:448-456](uni/STATUS.md); im Notion-Test ausdrücklich nicht [STATUS.md:141](STATUS.md) |
| Fassung als Datei mit Herkunft, final, eigene Fassung, für Agenten lesbar | [B] bei Lia | E | [shared/webapp/STATUS.md:86-94](shared/webapp/STATUS.md), `agentkit/fassungen.py` |
| JSON ist führend, Word abgeleitet; Wechsel bei eigener Word-Fassung | Vorschlag | E | [webapp-plan.md:150-153](uni/webapp-plan.md) |
| Recherche: Aussage, Status, Beleg; von Aussage zur Quelle | [B] Daten, [W] Weg | E | [portal-oberflaeche.md:56, 205-208](uni/portal-oberflaeche.md), `geprueft.json`; NotebookLM nur Muster |
| Recherche in zwei Stufen starten, Eckpunkte vorab | [W] | E | ebd.:303-309 |
| Nachfrage zweistufig, immer neue Sitzung, Kosten | [W] | E | ebd.:322-335 |
| Seite "So kam das zustande" aus `stand.json`, `geprueft.json` | Vorschlag | E | ebd.:343, 347 |
| Karten mit FSRS, Bildkarten, gemeinsamer Stand mit Telegram | [W], gebaut | E (Bibliothek) | [uni/STATUS.md:362-376](uni/STATUS.md) |
| Probeprüfung auswerten: Transkript, Rubrik, wörtliche Zitatprüfung, Kartenvorschläge | [W], gebaut | E | ebd.:384-418 |
| Thema mit Score, Liste "fehlt", Modul und Prüfungsleistung getrennt | gebaut | E | [webapp-plan.md:71, 221](uni/webapp-plan.md) |
| Laufstand, Warten, Parken nach Kontingent, Kosten zeigen | [B] | E | [uni/STATUS.md:397-400](uni/STATUS.md); Rückmeldung fehlt als belegtes Problem [webapp-plan.md:50](uni/webapp-plan.md) |
| Schriftverkehr-Auszug | [W], gebaut | E | [uni/STATUS.md:426-431](uni/STATUS.md) |
| Lias Schulmodell: Stundenplan, Ferien, Nachrücken, Reihe kopieren, Schuljahreswechsel | [B] | E | [shared/webapp/STATUS.md:191-207](shared/webapp/STATUS.md), `strukturpflege.py` 1.350 Zeilen |
| Varianten, Vorlagengalerie mit Agent, Formatvorlage für den Renderer | [B] | E | ebd.:49-54, 266, 285 |
| Regeln aus Feedback sehen, Stopp | [B] | E | ebd.:45-48; CLAUDE.md |
| Freigabe nach außen | [B] | E, bleibt Telegram | CLAUDE.md, [webapp-plan.md:233](uni/webapp-plan.md) |

**Selbst Nachgebautes, das klar Standard ist [V]:** Baum und Brotkrumen (`logik.baum`, `logik.krumen`), Reiter im Portal, Fassungsliste, Rückgängig und Papierkorb-Ähnliches, Ziehen von Stunden (`ziehen.js`), Passwort über Caddy. Geplant, nicht gebaut: Rechte/Name je Handlung, Aktivitäts-Zeitleiste, Fassungsvergleich — [portal-oberflaeche.md:281, 229-231](uni/portal-oberflaeche.md).

**Einzigartig für Jan [V]:** Rechercheergebnis mit Status je Aussage und wörtlichem Zitatabgleich ([webapp-plan.md:250](uni/webapp-plan.md)), Kostenwissen je Lauf und Sitzungswahl (`--resume` 10,38 USD gegen neue Sitzung, [portal-oberflaeche.md:329](uni/portal-oberflaeche.md)), Karten mit FSRS und Prüfungsauswertung mit Rubrik, Trennung Modul und Prüfungsleistung.

**Einzigartig für Lia [V]:** Fach, Klasse, Reihe, Stunde mit Terminen und Ferien, Varianten eines Blatts, Reihenkontext im Auftrag ("Lia trägt den Kontext der Reihe heute von Hand von Chat zu Chat", [docs/webapp-aufbau.md:45-47](docs/webapp-aufbau.md)), Regeln R1 bis R11 ([ebd.:69-81](docs/webapp-aufbau.md)), Chat mit Ortskontext, Schuljahreswechsel.

**Gegenprobe:** Die Muster sind im Repo teils bestätigt, teils begrenzt: Basecamp eher flach, Overleaf setzt beim Wiederherstellen Kommentare zurück, Confluence-Baum nur alt belegt — [portal-oberflaeche.md:179, 189, 199](uni/portal-oberflaeche.md).

### Inferences
- [V] Teilung nach Schichten: Struktur, Reiter, Rechte, Aktivität sind Dokumentwerkzeug-Schicht. Auftragsstart, Fassungskette, Kosten, Lernen, Belege sind Agenten-Schicht. Jans Ebenen-Idee verlangt, dass beide am selben Ort zusammenkommen; das ist die eigentliche Schwierigkeit.
- [V] Die stärkste Reibung ist bei "alle Fassungen gehören zu dem einen Dokument": Der Agent erzeugt Dateien aus JSON, ein Dokumentwerkzeug erzeugt eigene Seitenversionen. Das Repo nennt das als Unpassendes bei Notion — [portal-oberflaeche.md:166](uni/portal-oberflaeche.md).
- [V] Lias Schulmodell und das Lernen sind vermutlich nicht sinnvoll in einem Standardwerkzeug abbildbar; das Repo hat dazu aber keinen Test.

### Gaps
- Kein Werkzeug wurde benutzt; "Standard" ist Annahme. Der Notion-Test soll das klären, ist aber nicht gebaut und klammert Kommentare und die Gruppe aus — [STATUS.md:126, 141](STATUS.md).
- Ob Jan bereit ist, Lernen getrennt von Projektarbeit zu führen, steht nirgends. Portal-Pause gilt nur für Ebenen — [portal-oberflaeche.md:6](uni/portal-oberflaeche.md).
- Für Aufgaben 5 und 7 wurden nur Muster aus Dritt- und Hilfeseiten notiert, Interviewvorbereitung ohne Vorbild — [ebd.:343-345](uni/portal-oberflaeche.md).

## 5. Felix und Henri: Zugang

### Takeaway
Es gibt keine eigene Aussage von Felix oder Henri im Repo, nur Jans Wiedergabe. Jans Wunsch: voller Zugang zum Projekt, ohne Sperren, Überblick über die Arbeit der anderen, so einfach wie möglich. Gebaut ist nichts.

### Cited Findings
- Jan: "beide sollen alles bearbeiten können innerhalb des wissenschaftlichen projektes, wir arbeiten alle an allem und brauchen auch überblick was die anderen gemacht haben" — [portal-oberflaeche.md:124-125](uni/portal-oberflaeche.md).
- "beide" sind Felix und Henri, bestätigt. "holzschutz oder ander müssen nicht gesperrt bleiben, soeinfahch wie möglich erstmal" — [ebd.:236](uni/portal-oberflaeche.md).
- Entscheidungen Jan 04.11. ("erstmal okay"): alle drei dürfen Recherchen starten, ohne Freigabe; jeder darf bezahlte Läufe auslösen; Lernstand "so lassen", also gemeinsam; Normenzitate und Kartenbilder in Ordnung — [ebd.:351-360](uni/portal-oberflaeche.md).
- Bezahlung offen: "schlussendlich muss ich gucken dass ich geld von den anderen bekomme bzw. vielleicht hat jeder seinen eigenen pro acount" — [ebd.:357](uni/portal-oberflaeche.md). Heute alles auf Jans Konto, ohne Name je Handlung nicht zuzuordnen — [ebd.:368](uni/portal-oberflaeche.md).
- Technik heute: nur Konto `jan`, keine Personen. Vorschlag: drei Caddy-Konten mit Namensweitergabe, kein geteiltes Passwort, kein Abmelden, kein Magic Link, kein Rechte-System — [ebd.:273-286](uni/portal-oberflaeche.md). Nichts gebaut — [ebd.:244](uni/portal-oberflaeche.md).
- Folgen von "keine Sperren" aus dem Code: Üben durch Felix ändert Jans Lernstand; schon Öffnen von "Üben" speichert; alle sähen 3 Mails einer dritten Person, Transkripte und Lernstand; jeder kann Claude-Läufe auf Jans Konto starten; Rückmeldungen und Fassungen tragen keinen Namen — [ebd.:254-264](uni/portal-oberflaeche.md).
- Offene Rückfrage: Laut Empfängerfeld ging eine der Betreuer-Mails nur an Jan; ein cc-Feld gibt es in der Datei nicht. Jan sagte allgemein "die stehen im cc" — [ebd.:359-367](uni/portal-oberflaeche.md).
- Bisherige Praxis: Beide arbeiten über Kommentare in der Datei (Kette: 17 Kommentare, Felix 12, Henri 5) und Fragen über Jan (Henris Kamera-Frage), Ergebnisse gingen als PDF-Blatt — [uni/STATUS.md:591, 602-607](uni/STATUS.md), [portal-oberflaeche.md:30, 33](uni/portal-oberflaeche.md). Autor eines Kommentars geht in der Kette verloren: Der Agent nannte falsch nur Henri — [uni/STATUS.md:593-594](uni/STATUS.md).
- Überholt: "Felix und Henri bekommen keinen Zugang. Ihre Beiträge kommen als Datei oder Transkript" — [webapp-plan.md:155](uni/webapp-plan.md); ersetzt durch Abschnitt "Was nicht gebaut wird" — [ebd.:236](uni/webapp-plan.md). Der Abschnitt 5 steht weiter unverändert im Plan.
- Notion-Test: Felix und Henri ausdrücklich nicht dabei — [STATUS.md:141](STATUS.md). Das Annehmen nur von Jans Konto (`created_by`) schließt sie auch technisch aus — [STATUS.md:134](STATUS.md).

### Inferences
- [V] Ihr belegter Bedarf ist kommentieren, sehen, was neu ist, und Fragen stellen, nicht Agenten steuern. Das Recht zu starten ist Jans Entscheidung, nicht ihre Anforderung.
- [V] Mindestvoraussetzung: Name an jeder Handlung, sonst geht weder Überblick noch Abrechnung, noch korrekte Autorenzuordnung.

### Gaps
- Was Felix und Henri selbst wollen, welche Geräte und Programme sie nutzen und ob sie überhaupt ein weiteres Werkzeug nutzen würden: nicht im Repo. Nur Jan kann das klären.
- Abrechnung oder eigene Konten: offen — [portal-oberflaeche.md:368](uni/portal-oberflaeche.md). Ob ein Notion-Test mit Gruppenzugang Kosten nach sich zieht: nicht im Repo.
