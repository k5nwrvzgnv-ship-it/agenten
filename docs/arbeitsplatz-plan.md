# Arbeitsplatz für Jan: neutrale Oberfläche über alle Agenten

Stand 09.11.2026, abends. Jans Okay 09.11. („Ja, so starten“), Bau bis 10.11. 17 Uhr.
Grundlage: `uni/portal-oberflaeche.md` (Kernaufgaben, Jans Idee zu Ebenen), `uni/reports/Notion oder Eigenbau für Agenten.md`,
`docs/webapp-aufbau.md` (Lias App als Muster), STATUS.md von uni, dokumente, finance, shared/webapp.

## Jans Entscheidungen (09.11.2026)

1. Eigenbau, Notion nur als Muster (Seiten in Seiten, „+ Neu“ auf jeder Seite, Seitenleiste). Die freigegebene
   Notion-Brücke (Haupt-STATUS, Entscheidungen) ruht und wird nicht gebaut.
2. Neuer Ordner `shared/arbeitsplatz/`, gebaut im Hauptordner-Chat. Ersetzt `uni/portal` schrittweise; dessen
   bewährte Teile (Rückmeldung, Laufstand, Karten üben, Prüfungsauswertung, Recherche-Ansicht) werden übernommen.
   `shared/webapp` (Lias App) bleibt unberührt.
3. dokumente bekommt die Arten „Präsentation“ und „Bericht“ (bei Zeitnot nur eine).
4. Über Nacht drei Sitzungen parallel (Hauptordner, uni, dokumente) ohne Einzelfreigabe je Schritt. Commits nur über
   commit.sh mit grünem pruefen.sh, pruefen.sh nur mit flock auf commit.sperre.
5. Testläufe am 10.11. nachmittags auf dem Agenten-Konto. Jan 09.11. abends: alle Arten echt testen außer Exposé
   (Exposé mit Recherche bis 50 USD; Recherche nur Umfang „kurz“, bis 15 USD; beides laut uni geschätzt, nicht
   gemessen). Zusammen grob 25 USD.

## Kernmodell

| Begriff | Was es ist |
|---|---|
| **Ort** | Seite in einem freien Baum, beliebig tief. Anlegen, umbenennen, verschieben, archivieren, frei benannt („Forschungsprojekt Fehlstellen“ › „Schriftlicher Teil“ › „Kapitel 3“, „Modul Holzschutz“, „Finanzen“). |
| **Art** | Arbeitsanweisung: Name, kurze Beschreibung, Felder des Formulars, zuständiger Agent, Ausgabe, optional eigene Ansicht. Steht in einer Datei, nicht im Code. Die Galerie zeigt nur Arten, deren Agent sie kann (`aktiv = true`). |
| **Dokument** | Entsteht aus einem Auftrag an einem Ort; hat Fassungen (Kette über `bezug`), höchstens eine final, eigene Fassungen hochladbar (`agentkit.fassungen`). |
| **Rückmeldung** | Text oder kommentierte Datei, wird die nächste Fassung derselben Kette. |

Nicht alles ist ein Dokument: Lernkarten, mündliche Prüfung und Recherche mit Belegen liegen an einem Ort wie jedes
Dokument, haben aber eine eigene Ansicht (Art mit `ansicht = "<name>"`). Die Standardansicht ist Vorschau, Dateien,
Fassungen, Rückmeldung, final.

Kein Editor im Browser: bearbeitet wird in Word, zurück kommt die Datei (eigene Fassung oder Rückmeldung).

## Schnittstellen (verbindlich für alle drei Sitzungen)

### Auftrag
- `agentkit.auftraege.neuer_auftrag(agent, text, quelle="arbeitsplatz", ort=<orts-id>, art=<art-kennung>, dateien=...)`.
  `ort` gibt es schon (Muster `[a-z0-9][a-z0-9-]{0,79}`). `art` kommt neu dazu (Sitzung A), gleiches Muster, steht nur
  im Auftrag, wenn gesetzt.
- Die Felder des Formulars stehen im Auftragstext als Zeilen `Feldname: Wert` unter einer ersten Zeile `Art: <Name>`,
  dazu im Auftrag als `felder` (dict, nur Text, Sitzung A). Agenten lesen `a.get("art")` und `a.get("felder")`; ohne
  `art` verhalten sie sich wie bisher (Telegram bleibt unverändert).
- Nachbesserung und Rückmeldung wie bisher: `bezug` = Fassung, `sitzung` fortsetzen. Eine Nachbesserung erbt `ort` und
  `art` vom Ursprung (Sitzung A in `agentkit.fassungen.rueckmeldung` bzw. der App).

### Ergebnis
- `abschliessen(id, ergebnis, dateien=[...], daten={"kern": "1-2 Sätze", "punkte": [...], "pruefen": "...", "titel": "..."})`.
  `titel` ist neu: Name des Dokuments für die Seite (ohne ID). Fehlt er, nimmt die App den Dateinamen.
- Dateien: PDF zum Lesen, dazu docx/pptx/xlsx zum Bearbeiten. Seitenbilder nach Renderer-Konvention
  (`<stem>-vorschau/<stem>-seite-NN.png`), wenn der Renderer sie anlegt.

### Arten-Datei `shared/arbeitsplatz/arten.toml`
```toml
[[art]]
kennung = "praesentation"
name = "Präsentation"
beschreibung = "Folien aus Material oder Stichpunkten, als PowerPoint und PDF"
agent = "dokumente"
aktiv = true            # nur aktive stehen in der Galerie
ausgabe = ["pptx", "pdf"]
ansicht = ""            # leer = Standardansicht
[[art.feld]]
name = "Thema"
art = "zeile"           # zeile | text | auswahl | zahl
pflicht = true
[[art.feld]]
name = "Umfang"
art = "auswahl"
werte = ["5 Folien", "10 Folien", "20 Folien"]
```
Die Prüfung der Datei (Pflichtfelder, Agent existiert, Kennungen eindeutig) liegt in agentkit (Sitzung A) und läuft in
den Tests.

### Orte
`agentkit.orte` (Sitzung A): Datei `<instanz>/orte.json`, ein Baum aus Knoten `{id, titel, eltern, position,
archiviert, angelegt}`. Funktionen: laden, anlegen, umbenennen, verschieben (kein Zyklus), archivieren,
wiederherstellen; Schreiben unter Sperre, jede Änderung mit Rückgängig (wie strukturpflege). ids nach dem Muster oben,
fest, ändern sich beim Umbenennen nicht.

## Arten zum Start

| Kennung | Name | Agent | Stand 09.11. | Ansicht |
|---|---|---|---|---|
| recherche | Research-Bericht | uni | läuft | recherche |
| expose | Exposé | uni | läuft | Standard |
| zusammenfassung | Vorlesungszusammenfassung | dokumente | läuft | Standard |
| wirtschaftlichkeit | Wirtschaftlichkeit | finance | läuft | Standard |
| anlage | Anlagemöglichkeiten | finance | läuft | Standard |
| lernkarten | Lernkarten | uni | läuft | karten |
| pruefung | Mündliche Prüfung üben | uni | läuft (Portal-Auswertung) | pruefung |
| praesentation | Präsentation | dokumente | neu (Sitzung C) | Standard |
| bericht | Bericht (z. B. Praktikumsbericht) | dokumente | neu (Sitzung C) | Standard |

## Oberfläche

Drei Spalten wie Lias App, Gestaltung Modernist (CSS, Schrift, htmx aus shared/webapp kopieren, nicht verändern):
- links der Baum (oben „Heute“: wartet auf mich, läuft gerade), mit „+ Seite“ auf jeder Ebene;
- Mitte die Seite des Orts: Unterseiten, Dokumente mit Marke (läuft, Fassung n, final, hat nicht geklappt),
  „+ Neu“ öffnet die Galerie, der Ort ist vorbelegt; Brotkrumen oben;
- rechts: Läuft gerade und Kosten der letzten Läufe (aus agentkit.verbrauch).
Dokument-Ansicht: Seitenbilder, PDF und Original, Rückmeldung (Text oder Datei), eigene Fassung, als final markieren,
Fassungen aufklappbar.

Betrieb: eigener Dienst `arbeitsplatz.service`, eigener Port 127.0.0.1:8794, Unix-Socket-Tests wie shared/webapp.
Vorlagen wirken sofort auf den laufenden Dienst: keine neuen Python-Filter in Vorlagen ohne Neustart.
Zugang wie das Portal (Caddy, Passwort). Umschalten in Caddy macht Jan als root nach der Abnahme.

## Ablauf bis 10.11. 17 Uhr

| Zeit | Wer | Was |
|---|---|---|
| Nacht | A (Hauptordner) | agentkit: `art`/`felder` in neuer_auftrag, `orte`, Arten-Prüfung; dann Gerüst shared/arbeitsplatz (Rahmen, Baum mit Pflege, Ort-Seite, Galerie, Formular) |
| Nacht | B (uni) | Aufträge mit `art` (recherche, expose, lernkarten) gezielt annehmen, `daten.titel/kern`, Ergebnisdateien; Prüfungsauswertung als Auftrag mit Art `pruefung` erreichbar |
| Nacht | C (dokumente) | Arten präsentation und bericht über den Renderer, mit Selbstkontrolle wie bei der Zusammenfassung; zusammenfassung mit `art` |
| 8–13 | A | Dokument-Ansicht, Rückmeldung, final, eigene Fassung, Heute, Läuft gerade; finance: `art` und `daten.titel` (kleiner Eingriff, im finance-Ordner) |
| 13–15 | A | Umzug: Projekt Fehlstellen und Modul Holzschutz als Orte, eigene Ansichten aus uni/portal einhängen, finance-Ergebnisse unter „Finanzen“ |
| 15–16 | Koordination | je Art ein echter Lauf, Durchklicken in Chrome |
| 16–17 | Jan | Abnahme, Caddy umstellen, STATUS.md |

Nicht bis 17 Uhr: Zugänge für Felix und Henri, Abrechnung, Fassungsvergleich, Änderungen an Lias App, Notion-Brücke.
