# Status: Agent chat (Lia)

## Zweck
Beantwortet Lias Fragen in der rechten Spalte „Fragen“ der Web-App (shared/webapp), kurz und mit dem Ort als
Kontext („Ethik › 8 › Straftheorien“) oder ohne Ort. Startet nie einen Auftrag und handelt nie nach außen;
„Daraus Auftrag machen“ macht die Web-App. Plan: plan.md (Jans Okay 30.10.2026).

## Stand (30.10.2026)
- Gebaut und im echten Test gelaufen: drei Fragen über die Warteschlange (Ethik 8 mit Ort, zwei ohne Ort),
  Antwort nach 8–14 s (claude-Lauf 3–4 s, Rest Start und Warten auf die vorige Frage), je ca. 0,03 USD (Sonnet).
  Testeinträge danach aus dem Verlauf gelöscht. „Gründlich“ (Opus) ist getestet nur ohne echten Lauf.
- Dienste eingerichtet und aktiv: lia-chat.path (startet lia-chat.service, sobald eine Frage wartet),
  lia-chat-aufraeumen.timer (täglich 03:40).
- Die Web-App nutzt den Chat noch nicht (Spalte „Fragen“ ist dort Platzhalter, Bedarf in Punkt 24 der Haupt-STATUS).

## Aufbau
- Code: agent.py (Einstieg, Fehlertexte, claude_lauf), kontext.py (Reihe aus Dateien, Kontext-Text, Prompt; rein),
  chatverlauf.py (Verlauf, Aufräumen), schnittstelle.py (für die Web-App, nur Bordmittel), tests/.
- .venv: lia/chat/.venv, agentkit per .pth, keine Pakete.
- Dienste: Vorlagen in systemd/, installiert in ~/.config/systemd/user/, AGENTKIT_INSTANZ=lia/instanz.
- Laufzeitdaten: data/ (fragen/, antworten/, tmp/, verlauf.jsonl), Logs: logs/ (ohne Frage- und Antworttext).

## Schnittstelle (für shared/webapp)
- `sys.path` um lia/chat ergänzen, dann `import schnittstelle` (nur Python-Bordmittel, Module schnittstelle und
  chatverlauf):
  - `frage_stellen(text, ort=None, gruendlich=False) -> id` (12 Hex-Zeichen). Ungültig: `FrageFehler` mit Satz
    für Lia (leer, über 4.000 Zeichen, Ort falsch).
  - `ort`: None (ohne Ort) oder `{"reihe": "<kennung>", "stunde": n, "chip": "Ethik › 8 › Straftheorien",
    "stunde_thema": "…", "materialien": ["Titel", …]}`; nur `reihe` ist Pflicht. Reihe, Lerngruppe, Stunden usw.
    liest der Agent selbst aus lia/instanz/reihen.toml.
  - `antwort_holen(id) -> dict | None` (None = noch nicht fertig, Vorschlag: alle 2 s nachfragen),
    `wartet(id) -> bool`, `verlauf() -> list` (beantwortete Fragen, älteste zuerst: id, zeit, reihe, chip,
    gruendlich, frage, antwort).
- Antwort: `{"id", "zeit", "ok", "text", "gruendlich", "reihe", "chip", "fehler", "wieder_frei"}`. `fehler`:
  None, "limit" (Kontingent voll, `wieder_frei` z. B. "31.10. 14:30"), "belegt" (alle Plätze besetzt, 1 min
  gewartet), "zeit", "technik" (Jan bekommt eine Meldung), "ungueltig". Bei Fehlern steht in `text` ein fertiger
  Satz für Lia. `text` ist Markdown (fett, Listen).
- Dateien statt Aufruf: Die Web-App schreibt nur data/fragen/<id>.json (über data/tmp, atomar); systemd startet den
  Agenten. Antwortzeit schnell ca. 10–15 s, gründlich (Opus) länger, Zeitgrenze 2 bzw. 5 min.

## Entscheidungen
- 30.10.2026 (Jan): Plan wie plan.md, mit Ordner, .venv und Diensten. Verlauf 30 Tage, Wartegrenze auf einen Platz
  1 min (kein eigener Platz für den Chat).
- 30.10.2026: Warteschlange in Dateien statt Unix-Socket (kein Dauerdienst, Muster wie shared/auftraege).
- 30.10.2026: Claude ohne Werkzeuge (`--tools ""` über eine Kopie der Einstellungen in agent.py), höchstens 3
  Schritte. Schnell = art "routine" (Sonnet, in der Sparstufe Haiku), gründlich = "anspruchsvoll" (Opus).
- 30.10.2026: claude legt jede Sitzung unter ~/.claude/projects/-home-agent-agenten-lia-chat/ ab; der Agent löscht
  sie nach jedem Lauf, der Timer täglich alle übrigen.
- 30.10.2026: Hinweis auf „Daraus Auftrag machen“ nur, wenn Lia ausdrücklich Material will (vorher kam er bei
  jeder Antwort).

## Offene Punkte
1. Web-App: Spalte „Fragen“ an schnittstelle.py anschließen (shared/webapp-Chat, Punkt 24).
2. Ein echter Lauf mit „gründlich“ (Opus) fehlt; Antwortzeit dann hier eintragen.
3. Uploads im Chat (PDF/Word/Bild) sind nicht gebaut (docs/webapp-aufbau.md 3.1), erst nach dem Test mit Lia.
4. Sauberer als das Löschen der Sitzungen: Option `--no-session-persistence` in agentkit.claude_lauf
   (Hauptordner-Chat, kein Muss).

## Gelernte Regeln
- (noch keine)
