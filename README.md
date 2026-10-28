# Agenten

Persönliches Agenten-System von Jan, dazu eine eigene Instanz für Lia.
Regeln: CLAUDE.md. Aktueller Stand: STATUS.md.

## Wo liegt was

```
/home/agent/
├── agenten/                 dieses Repo, das Agenten-System
│   ├── CLAUDE.md            Regeln für alle Chats
│   ├── STATUS.md            Stand des Gesamtsystems
│   ├── pruefen.sh           alle Tests und Linter (läuft vor jedem Commit)
│   ├── docs/                Architektur (lia-architektur.md) und Übergaben
│   │
│   ├── shared/              gemeinsamer Code UND Jans Daten
│   │   ├── agentkit/        Code: Bibliothek für alle Agenten (Warteschlangen, claude-Läufe, Verbrauch …)
│   │   ├── telegram/        Code: Jans Zentrale (zentrale.py) und Lias Zentrale (portal.py)
│   │   ├── renderer/        Code: Dateien aus JSON bauen (docx, pptx), noch im Aufbau
│   │   ├── leitstand/       Code: Web-Ansicht der Agenten (Netz, Läufe), nur lesen, per SSH-Tunnel
│   │   ├── vorlagen/        Gerüst für neue Agenten
│   │   ├── systemd/         Dienst ausfall@ (meldet Ausfälle an Jan)
│   │   ├── auftraege/ freigabe/ meldungen/ ausfall/   Jans Warteschlangen (nicht im Repo)
│   │   ├── verbrauch/       Verbrauch und Plätze, gemeinsam für Jan und Lia (ein Claude-Konto)
│   │   ├── ereignisse/      Ereignisse für den Leitstand, eine Datei pro Tag, 30 Tage (nicht im Repo)
│   │   ├── einstellungen.toml   Limits, Stufen, Modelle, Werkzeuge (gilt für beide)
│   │   ├── regeln.md        Jans allgemeine Regeln
│   │   └── .env             Jans Bot-Token, Chat-ID, Kauflimit (nicht im Repo)
│   │
│   ├── uni/                 Jans Agent uni (läuft)
│   ├── dokumente/           Jans Agent dokumente (Gerüst, noch kein agent.py)
│   ├── posteingang/         Jans Agent posteingang, privates Postfach (Gerüst, noch kein agent.py)
│   │
│   └── lia/                 Lias Instanz
│       ├── instanz/         Lias Daten: .env, Warteschlangen, Regeln, Daten ihrer Zentrale
│       └── unterricht/      Lias Agent unterricht (Platzhalter, antwortet „kommt bald“)
│
├── agents/vinted/           alter Vinted-Bot, gehört NICHT zum System (nicht anfassen, Ausnahme: CLAUDE.md)
└── .config/systemd/user/    die laufenden Dienste (Kopien der Vorlagen aus dem Repo)
```

posteingang (Jans privates Postfach): Gerüst angelegt, noch kein agent.py, kein Dienst.
Geplant, noch ohne Ordner: einkauf (Recherche mit Preisen).
Der Ordner entsteht mit dem Agenten.

## Jeder Agent-Ordner hat denselben Aufbau
| Teil | Inhalt |
|---|---|
| `agent.py` | Einstieg |
| `STATUS.md` | Stand des Agenten, Übergabe an den nächsten Chat |
| `systemd/` | Vorlagen der Dienste. Zum Einrichten nach `~/.config/systemd/user/` kopieren |
| `tests/` | Tests, in `pruefen.sh` eingetragen |
| `.venv/` | eigene Python-Umgebung, agentkit per .pth eingebunden |
| `.env` | Zugangsdaten (chmod 600, nicht im Repo) |
| `data/`, `logs/` | Laufzeitdaten und Logs (nicht im Repo) |

## Dienste (`systemctl --user …`)
| Dienst | Was | Vorlage |
|---|---|---|
| `agentenzentrale` | Jans Telegram-Bot @Agentenzentralebot | `shared/telegram/systemd/` |
| `lia-zentrale` | Lias Telegram-Bot @zentraleliabot | `shared/telegram/systemd/` |
| `uni` + `uni.timer` | Agent uni, 8/13/19 Uhr und nach Aufträgen | `uni/systemd/` |
| `uni-transkript` + Timer | Vorlesungen transkribieren | `uni/systemd/` |
| `lia-unterricht` | Lias Platzhalter, startet nach Aufträgen | `lia/unterricht/systemd/` |
| `feedback`, `lia-feedback` | Feedback zu Ergebnissen zuordnen und übernehmen, Jans Stopp | `shared/feedback/systemd/` |
| `ausfall@` | Meldung an Jan, wenn ein Dienst ausfällt | `shared/systemd/` |
| `leitstand` (noch nicht eingerichtet) | Web-Ansicht, Unix-Socket `shared/leitstand/data/leitstand.sock` | `shared/leitstand/systemd/` |
| `vinted-bot` | alter Vinted-Bot, nicht Teil des Systems; zählt in /verbrauch mit, meldet Ausfälle | `~/agents/vinted/systemd/` |

Status: `systemctl --user status <dienst>`. Logs: `journalctl --user -u <dienst>` oder `<ordner>/logs/`.
Nach Änderung einer Vorlage: Vorlage kopieren, dann `systemctl --user daemon-reload`, dann `systemctl --user restart <dienst>`.

## Bedienung über Telegram
- **Jan (@Agentenzentralebot):**
  - `/start` oder `/menue` öffnet das Menü mit Knöpfen.
  - Befehle gehen weiterhin: `/uni <Auftrag>`, `/unilern <Auftrag>`, `/status`, `/verbrauch`, `/hilfe`.
  - Entwürfe kommen mit Freigeben / Ablehnen / Ändern.
- **Lia (@zentraleliabot):** nur Knöpfe (Neues Material, Meine Woche, Frage stellen, Meine Anfragen, Hilfe).

## Arbeiten mit Claude Code
- **Ein Chat pro Ordner**, gestartet im Ordner auf dem Server (SSH-Verbindung `agents-user`, User agent):
  - `~/agenten` für Struktur und shared/
  - `~/agenten/shared/renderer` für den Renderer
  - `~/agenten/<agent>` bzw. `~/agenten/lia/<agent>` je Agent
- Ein Chat ändert nur seinen Ordner. Bedarf anderswo schreibt er in die STATUS.md des Hauptordners.
- Das Wissen steht in den STATUS.md-Dateien, nicht im Chat. Für jede neue Aufgabe darf ein frischer Chat starten.

## Nach neuem Klonen einmal
`git config core.hooksPath githooks` und `python3 -m venv .venv && .venv/bin/pip install -r requirements-werkzeuge.txt`
