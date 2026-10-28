# Leitstand: Plan für ein Frontend zur Steuerung der Agenten (28.10.2026)

Stand: Plan und klickbarer Entwurf, nichts gebaut. Entwurf (privat, Beispieldaten):
https://claude.ai/artifact/6DVm6MiPQHtjiMbjb6buzT

Grundlage: STATUS.md, Git-Verlauf, shared/auftraege, shared/freigabe, shared/verbrauch/laeufe.jsonl.
Claude läuft über das Abo (`claude -p`, OAuth-Token oder Jans Login), nicht über die API.

## 1. Eingriffspunkte (aus bisheriger Handarbeit)

| Bisher von Hand | Eingriff im Leitstand |
|---|---|
| Entwürfe in Telegram freigeben, ändern, ablehnen | Freigabe: dieselbe Funktion `freigabe.entscheide`, gleicher Fingerabdruck |
| 27.10.: Konto dreimal in einstellungen.toml umgestellt, danach Sperre bis 20:10 (Punkt 17) | Konfiguration: Konto, Stufen-Grenzen, Modell, Zeitplan |
| Liszt-Lauf (25.10.) im Chat abgebrochen; claude_lauf kennt nur das Zeitlimit | Abbruch (neu) |
| Nachbesserung als neuer Auftrag mit bezug/sitzung; Läufe nach Limit neu angestoßen | Wiederholen, Nachbessern |
| Freigaben vom Typ "entwurf" von Hand abgeschlossen; unklare Ausführungen von Hand geprüft | Als erledigt markieren, unklare Ausführung klären |
| Dienste und Timer per systemctl | Agent pausieren, fortsetzen |
| reihen.toml von Hand, Regelvorschläge warten, Feedback-Stopp | Regeln und Kontext |
| Kein Fortschritt sichtbar (Punkt 14) | Lauf-Detail mit Ereignissen |

Nicht im Leitstand: Tokens und .env, Code, Vinted-Bot (nur Anzeige).

## 2. Ereignisse und Schnittstelle

Ereignisse: je Lauf `shared/ereignisse/<auftrag-id>.jsonl`, nur anhängen. Felder
`{v, id, zeit, auftrag, agent, instanz, typ, daten}`. Typen:
- auftrag.angelegt, lauf.gestartet, lauf.fortschritt
- werkzeug, datei.geschrieben, weitergabe
- freigabe.wartet, freigabe.entschieden, freigabe.ausgefuehrt, freigabe.unklar
- lauf.beendet, lauf.abgebrochen
- fehler.limit, fehler.konto, fehler.zeit, fehler.technik
- verbrauch (Tokens, 5h- und 7d-Auslastung)

Quelle: `claude -p --output-format stream-json` (verbrauch.auslastung_aus_event liest das schon). Schreiben über
ein neues Modul agentkit.ereignis, aufgerufen in claude_lauf, auftraege und freigabe.

Dienst `leitstand` (Python-Bordmittel, nur 127.0.0.1, Zugriff per SSH-Tunnel):
- `GET /zustand`: Agenten, Dienste, offene Freigaben, Stufe
- `GET /laeufe`, `GET /laeufe/{id}`
- `GET /ereignisse` als SSE mit Last-Event-ID (nach Neuladen wird nachgeholt)
- `POST /auftraege`
- `POST /laeufe/{id}/abbrechen`: legt eine Abbruch-Datei ab, claude_lauf beendet die Prozessgruppe
- `POST /laeufe/{id}/wiederholen`
- `POST /freigaben/{id}` mit `{entscheidung, fingerabdruck, kommentar}`
- `PUT /einstellungen`: nur Schlüssel aus fester Liste, Unterschied anzeigen, als Commit speichern
- `POST /dienste/{agent}/pausieren`

Zustand bleibt in Dateien, die Oberfläche hält keinen. Die Oberfläche legt Dateien ab, Python handelt.

Abo statt API: Der Leitstand ruft Claude nie auf, kein API-Schlüssel. Grenze ist die 5h-/7d-Auslastung in
Prozent, USD nur umgerechnet. Auslastung wird nur bei Agenten-Läufen aktualisiert: "Stand von ..." anzeigen.

AG-UI: Begriffe passen (Lauf-Lebenszyklus, Momentaufnahme plus Änderungen, SSE), gedacht ist es aber für
Copilot-Chats, in denen die Oberfläche den Lauf startet. Hier starten Warteschlange und Timer, mehrere Läufe
parallel. Entscheidung: eigenes Schema mit Namen nahe an AG-UI, Adapter später möglich. Aktueller Umfang von
AG-UI nicht nachgeprüft.

## 3. Varianten

- Framework-eigene Oberfläche: agentkit hat keine; Telegram bleibt die Oberfläche für unterwegs.
- Low-Code (n8n, Retool o. ä.): eigener Server oder Docker auf 7,8 GB ohne Swap, Zustand doppelt, Zugangsdaten
  in einem weiteren Werkzeug, bricht "Python handelt". Nein.
- CopilotKit / AI SDK: für LLM-Chats per API-Schlüssel in einer App. Mit Abo kein Schlüssel, die Oberfläche
  soll nicht mit Claude sprechen, dazu React-Build. Nein.
- Eigenes Dashboard (Empfehlung): ein Python-Dienst, eine HTML-Datei, kein Build, keine neuen Pakete. Nutzt
  dieselben agentkit-Funktionen wie Telegram, Logik getestet wie logik.py. Telegram für schnelle Entscheidungen
  am Handy, Leitstand für Überblick und Einstellungen am PC.

## 4. Oberfläche (im Entwurf klickbar)

- Netz: Eingang -> Zentralen -> Agenten -> Ausgang, Zustand und Eingriffe je Agent.
- Läufe: Liste, Ereignisse des gewählten Laufs, Abbrechen, Wiederholen, Nachbessern, `claude --resume`.
- Freigabe: Kopf, Mailtext als Zitat, "Bitte prüfen", Freigeben / Ändern / Ablehnen, Fingerabdruck.
- Einstellungen: Konto, Agenten mit Pause-Schalter, gelernte Regeln mit Stopp, Unterschied vor dem Speichern.

## 5. Messgrößen

- Zeit bis zum Eingriff: Abstand freigabe.wartet bzw. fehler.* bis zu Jans Entscheidung, aus den Ereignissen.
  Telegram und Leitstand vergleichen. Ziel Abbruch: unter 30 s ab Öffnen.
- Anteil Eingriffe ohne Code: zwei Wochen zählen, Leitstand/Telegram gegen Chat, Shell, Commits an
  einstellungen.toml/regeln.md, Handarbeit an Warteschlangen. Ziel: mindestens 80 %.
- Usability-Test mit einer Fremdperson, laut denken, ohne Hilfe: Entwurf ändern, Lauf abbrechen, gescheiterten
  Lauf wiederholen, Agent pausieren, Konto umstellen. Erfolg, Zeit, Fehler. Ziel: 4 von 5 ohne Hilfe.
- Robustheit als automatische Tests: Neuladen mitten im Lauf (gleicher Stand), Doppelklick auf Freigeben
  (genau eine Ausführung), Abbruch während eines Werkzeugaufrufs (nichts nach außen, Status abgebrochen),
  Neustart des Dienstes und zwei offene Tabs (keine Ereignisse verloren).

## Reihenfolge (jede Stufe nur nach Jans Okay)

1. Ereignisse schreiben (agentkit.ereignis), Läufe nur lesend anzeigen.
2. Freigabe und Abbruch.
3. Einstellungen.
