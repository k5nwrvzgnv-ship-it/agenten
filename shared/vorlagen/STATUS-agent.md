# Status: Agent <name>

## Zweck
<Was der Agent für Jan erledigt, 1–3 Sätze.>

## Stand (<TT.MM.JJJJ>)
- <Was ist fertig, was läuft, was wurde getestet.>

## Aufbau
- Code: <name>/agent.py (Einstieg), weitere Module
- .venv: <name>/.venv, agentkit per .pth eingebunden
- Dienst: <name>.service (oneshot, arbeitet Aufträge ab), Timer: <name>.timer (zeitgesteuerte Läufe)
- Zugangsdaten: <name>/.env (chmod 600), Vorlage <name>/.env.example
- Laufzeitdaten: <name>/data/, Logs: <name>/logs/ (beide nicht im Repo)

## Entscheidungen
- <Datum>: <Entscheidung> (<Begründung>)

## Offene Punkte
1. <...>

## Gelernte Regeln
- (noch keine)
