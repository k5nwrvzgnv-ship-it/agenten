# Plan: Lia pflegt Fach → Klasse/Kurs → Reihe → Stunde selbst

Stand 03.11.2026. Nur Plan, nichts gebaut. Gebaut wird nach Jans Freigabe und Antworten auf die offenen Fragen
(Abschnitt 9, markiert mit **F1** bis **F19**).

Grundlage (selbst gelesen): `git log -p lia/instanz/reihen.toml` (8 Commits, mit der Vorgängerdatei
`lia/unterricht/reihen.toml`), alle Leser der Datei (`lia/unterricht/reihen.py`, `lia/examen/runde.py`,
`lia/recherche/kernstellen.py` und `faelle.py`, `lia/chat/kontext.py`, `shared/webapp/ordnung.py` und `logik.py`,
`shared/webapp/zustand.py`), die 14 erledigten Aufträge und den offenen Entwurf in `lia/instanz` (nur die Felder
`agent`, `reihe`, `quelle`), `lia/instanz/fassungen/`, `docs/webapp-aufbau.md`, `shared/webapp/board-plan.md`,
Punkt 24 der Haupt-STATUS.

---

## 1. Befund

### 1.1 Was die Handänderungen an reihen.toml zeigen

| Commit | Was Jan von Hand getan hat | Fall für die App |
|---|---|---|
| a8a4123 23.10. | Datei angelegt, nur Muster im Kommentar | – |
| 5ec30ad 23.10. | erste Reihe (Ethik 8, Straftheorien) mit Lerngruppe, Notizen, behandelt, bisherige_reihen; Reihenfrage optional, weil Lia sie noch sucht | **Reihe anlegen mit wenigen Feldern**, Rest später |
| bf3c279, 308465b 24.10. | Notizen zweimal in einer Minute geändert (Korrektur der Korrektur) | **Feld ändern**, schnelles **Rückgängig/Nachbessern** |
| 7e71902 24.10. | Merksätze der *abgeschlossenen* Reihe Helfen nachgetragen, als Freitext in `bisherige_reihen` (das Feld `merksaetze` gab es, aber Helfen ist kein eigener Block) | **abgeschlossene Reihe ändern**; frühere Reihen gehören als echte Reihen in die Datei |
| 691ea12 27.10. | Lerngruppe ergänzt (Schulform, Herkunft, Religion, Lebenswelt) | **Lerngruppe ändern**; Datenschutz (Abschnitt 6) |
| 9fcb2a9 30.10. | Datei umgezogen, `id`, `agenten`, Kurs 12 „Der nackte Wahnsinn“ neu (vorher in der App fälschlich bei Kurs 11) | **Reihe einer anderen Klasse zuordnen** (verschieben) |
| d4aba3a 30.10. | Kurs 11 (neu 2026/27) als *Reihe ohne Titel* angelegt, weil es Kurse nur über Reihen gibt; 11 Archiv-Reihen (Klasse 7 und Kurs 11 aus 2025/26) nachgetragen | **Kurs anlegen ohne Reihe**; **Archiv**; die Archiv-Reihen doppeln die Texte in `bisherige_reihen` |

Folgerungen:
- **Fach und Klasse gibt es heute nicht als Einträge.** Sie entstehen aus den Texten `fach`, `klasse`, `schuljahr`
  jeder Reihe. Ein leerer Kurs braucht einen Platzhalter (`darstellendes-spiel-kurs-11`, in der App „Noch ohne
  Titel“). Die Lerngruppe ist eine Eigenschaft der Klasse, steht aber an einer Reihe.
- **Der Stand steckt teils im Titel**: „Straftheorien (in Planung)“. Es gibt nur `laufend` und `abgeschlossen`.
- **Archiv ist eine Ableitung**: `schuljahr` gesetzt und `stand = "abgeschlossen"` (logik.reihen_aus). Die laufenden
  Reihen haben kein Schuljahr.
- **Dieselbe Klasse in zwei Jahren**: Ethik 7 (2025/26) ist heute Ethik 8. Eine Verbindung „gleiche Schüler*innen“
  gibt es nicht, nur Freitext in `bisherige_reihen`.

### 1.2 Wer die Struktur liest und woran er eine Reihe erkennt

| Leser | erkennt die Reihe an | prüft streng? | Risiko, wenn die App schreibt |
|---|---|---|---|
| `lia/unterricht/reihen.py` (jeder Material-Lauf) | `id` aus Feld `reihe` des Auftrags | ja: unbekannte Felder, `stand` außer laufend/abgeschlossen → ganze Datei verworfen, Lauf ohne Reihenkontext, Meldung an Jan | jedes neue Feld (z. B. `archiviert`, Stunden-`id`) muss hier zuerst erlaubt werden |
| `shared/webapp/logik.reihen_aus` | `id`, sonst aus Fach+Klasse+Titel abgeleitet | ja, aber je Reihe: fehlerhafte Reihe fehlt | Stunden-Regel anders als reihen.py (`nr` lückenlos 1..n hier, nur eindeutig dort) |
| `lia/examen/runde.py` | **Titelanfang** `titel_in_reihen_toml = "Straftheorien"`, genau ein Treffer | – | Titel ändern oder Reihe kopieren (zweimal „Straftheorien“) bricht examen ab. Stehen Stunden an der Reihe, stürzt `reihe_text` ab (`"; ".join` über eine Liste von Tabellen) |
| `lia/recherche/kernstellen.py` | erste Reihe mit „Straftheorien“ im Titel | – | nach einer Kopie ggf. die falsche (archivierte) Reihe |
| `lia/recherche/faelle.py` | Freitext `bisherige_reihen`, Regex auf „…: Frage?“ | – | wenn `bisherige_reihen` abgelöst wird, fehlen die früheren Reihenfragen |
| `lia/chat/kontext.py` | `id`, sonst abgeleitet (wie Web-App) | nein | ohne gespeicherte `id` ändert ein neuer Titel die Kennung |
| `logik.reihe_von` (Web-App) | Feld `reihe` des Auftrags, sonst `agenten`, **wenn der Agent in genau einer Reihe steht** | – | eine Kopie mit `agenten = ["theater"]` nimmt allen Theater-Aufträgen den Ort |

### 1.3 Was heute an der Struktur hängt

- **Aufträge**: keiner der 14 erledigten Aufträge und nicht der offene Entwurf trägt das Feld `reihe`. 7 Theater-
  Aufträge und der examen-Entwurf hängen nur über `agenten` an ihrer Reihe; 4 Material-Aufträge, 1 Recherche und
  2 Feedback-Aufträge haben keinen Ort. Auftrags-JSONs liegen nicht in Git (`.gitignore`).
- **Fassungen**: `lia/instanz/fassungen/` (1 Datei, theater-0baec0) hängt über `ursprung` am Auftrag, nicht an der
  Reihe. Der Ordner ist **weder versioniert noch ignoriert** (taucht in `git status` auf, **F15**).
- **Web-App-Zustand** (`shared/webapp/data/zustand/`, Stunden, Stunde je Material, Lias Zuordnung): existiert auf dem
  Server noch nicht. **Stunde je Material ist dort über die Nummer gespeichert** (`stunde_von: {"reihe", "nr"}`):
  Verschieben oder Löschen einer Stunde würde Material still an die falsche Stunde hängen.
- **Chat-Verlauf** (`lia/chat/data/verlauf.jsonl`, Feld `reihe`): heute leer.
- **Stunden**: Das Format `[[reihe.stunde]]` (nr, thema, marke) ist in reihen.py und logik.py schon erlaubt, die
  Datei enthält aber keine. Die Web-App speichert eigene Stunden in data/ (Agenten sehen sie nur als Textzeile).

Fazit: Heute hängen nur `agenten`-Zuordnungen an Reihen-Kennungen. **Ein Formatwechsel ist jetzt billig**; nach
den ersten App-Aufträgen mit Feld `reihe` nicht mehr.

Jans frühere Entscheidung (Haupt-STATUS Punkt 24, 30.10.): „Reihen pflegt vorerst Jan, Lia erst mit Konten.“
Konten gibt es noch nicht (Schutz heute: Caddy-Passwort). **F19.**

---

## 2. Datenmodell (Vorschlag)

Eine Datei bleibt die Quelle: `lia/instanz/reihen.toml`, jetzt mit allen vier Ebenen als Einträge mit fester `id`.

```toml
[[fach]]
id = "ethik"
name = "Ethik"

[[klasse]]
id = "ethik-8"
fach = "ethik"                 # id des Fachs
name = "8"                     # „8“ oder „Kurs 11“
schuljahr = "2026/27"
lerngruppe = """…"""           # siehe Abschnitt 6 (ggf. ausgelagert)
herkunft = "ethik-7-2025-26"   # gleiche Schüler*innen im Vorjahr (ersetzt bisherige_reihen)

[[reihe]]
id = "ethik-8-straftheorien"
klasse = "ethik-8"             # id der Klasse (heute Anzeigetext „8“)
titel = "Straftheorien"        # ohne „(in Planung)“, das sagt jetzt stand
stand = "geplant"
agenten = ["examen"]

[[reihe.stunde]]
id = "s-4k2m9a"
thema = "Kant: Vergeltung"
marke = "Prüfung"
```

- Eine `id` gilt über alle Ebenen, Kleinbuchstaben/Ziffern/Bindestriche, ändert sich nie (auch wenn Titel oder
  Klasse wechseln: `ethik-8-straftheorien` bleibt, auch wenn die Reihe in die 9 wandert).
- **Stunden ohne gespeicherte Nummer**: Reihenfolge = Reihenfolge der Blöcke, die Nummer zählt die Leseschicht
  (nur nicht ausgeblendete Stunden). Verschieben ist dann ein verschobener Block, wie von Hand. Das alte `nr` wurde
  nie benutzt, der Wechsel kostet nichts (**F3**).
- `archiviert = "2026-11-03"` (Datum) an jedem Objekt, getrennt von `stand`: Wiederherstellen löscht die Zeile, der
  alte Stand ist unverändert da.
- `herkunft` an Klasse und Reihe: Kopie bzw. Vorjahr. Ersetzt den Freitext `bisherige_reihen`
  („Frühere Reihen der Klasse“ = Reihen der Klassen in der Herkunftskette). **F10.**
- Systemfelder, die keine Maske zeigt: `id`, `herkunft`, `archiviert`, `agenten` (nur Jan, **F18**).

**Eine Leseschicht für alle.** Heute prüfen vier Stellen die Datei je anders. Vorschlag: `shared/agentkit/struktur.py`
(Hauptordner-Chat) mit `laden()` → aufgelöste Objekte (eine Reihe kennt Fachname, Klassenname, Schuljahr,
Lerngruppe, Stunden mit Nummer), `pruefen()`, `ort(id)`, `haengt_dran(id)` und den Schreib-Operationen
(Abschnitt 4). unterricht, examen, recherche, chat und Web-App lesen nur noch darüber; ihre Prompt-Texte bleiben
gleich, weil die aufgelösten Felder dieselben Namen haben. **F1.**

---

## 3. Lebenslauf je Objekt

```
Reihe:   geplant ──► laufend ──► abgeschlossen        (jeder Schritt auch zurück, nur durch Lia)
            │           │             │
            └───────────┴──────┬──────┘
                               ▼
                          archiviert  ──Wiederherstellen──►  derselbe Stand wie vorher
                               │
          Löschen (nur wenn nichts dranhängt, Abschnitt 3.1) ──► weg, Rückgängig möglich

Fach, Klasse:  aktiv ◄──► archiviert;  Löschen wie oben
Stunde:        sichtbar ◄──► ausgeblendet (= archiviert, zählt nicht mit);  Löschen wie oben
```

- **Kein Automatismus.** Ende des Schuljahrs: Hinweis in „Heute“ („Schuljahr 2025/26 vorbei: Klassen
  archivieren?“), nie selbst (**F16**).
- **Archivieren vererbt sich beim Lesen, nicht beim Schreiben**: Wird eine Klasse archiviert, bekommt nur sie die
  Zeile `archiviert`; ihre Reihen gelten als archiviert, solange die Klasse es ist. Wiederherstellen entfernt die eine
  Zeile, und genau der Zustand vorher ist zurück, auch Reihen, die schon vorher einzeln archiviert waren, bleiben es.
- **Archivieren und Wiederherstellen ändern keine Zuordnung**: Aufträge, Fassungen, Stunden-Material, Chat-Verlauf
  bleiben, wo sie sind. Archiviert heißt nur: im Baum unter „Archiv“, eingeklappt, keine „+ Neu“-Knöpfe.
- Im Prompt der Agenten: `geplant` und `laufend` stehen als laufende Reihen (Straftheorien ist geplant und genau
  die Reihe, an der Lia arbeitet), `abgeschlossen` und archiviert als kurze Liste „was die Klassen schon kennen“
  (wie heute).
- Stunde: kein eigener Stand. „gehalten“ und ein Datum erst, wenn Lia es will (**F11**).

### 3.1 Löschen: wann es geht

Löschen geht nur, wenn an dem Objekt **und allem darunter** nichts hängt. Geprüft wird (`struktur.haengt_dran`):
1. Ebenen darunter (Löschen nur ohne Kinder, erst die Kinder löschen; **F17**),
2. Aufträge in `auftraege/neu` und `erledigt` mit dieser Kennung (Feld `reihe`, später `ort`),
3. Entwürfe in `freigabe/` mit dieser Kennung,
4. `agenten` nicht leer (dann hängen alle Aufträge dieser Agenten ohne eigene Reihe daran),
5. Web-App-Zustand: Zuordnungen von Material zu Reihe oder Stunde,
6. Chat-Verlauf mit dieser Kennung,
7. feste Verweise anderer Agenten (heute examen und recherche per Titel, nach Bauschritt 2 per `id`).

Sonst bietet die App statt „Löschen“ nur „Archivieren“ an und sagt, was dranhängt („3 Materialien, 1 Entwurf“).
Weil nur gelöscht wird, woran nichts hängt, kann eine frei gewordene Kennung nichts Falsches treffen.

**Rückgängig** gibt es für jede Aktion: Hinweis „Reihe archiviert · Rückgängig“ direkt danach, dazu die Liste
„Letzte Änderungen“ (die letzten 20, unter „Ich“). Rückgängig ist die Gegen-Aktion als neuer Commit
(„Rückgängig: …“), kein `git revert`. Sie geht, solange der betroffene Block seitdem unverändert ist; sonst sagt die
App, dass Jan inzwischen etwas geändert hat, und tut nichts. Gelöschte Blöcke (mit ihrem Kommentar darüber) hebt die
App dafür in `shared/webapp/data/aktionen/` auf.

---

## 4. Aktionsmatrix

Legende: **ja** / **nein** / **–** (gibt es nicht). „Darunter“ = Ebenen unter dem Objekt. „Aufträge“ = Aufträge,
Entwürfe, Fassungen, Material-Zuordnungen, Chat-Verlauf. Grundsatz für alle Zellen: **Auftrags-JSONs und
Fassungen werden nie umgeschrieben**; sie zeigen auf eine `id`, und die bleibt.

### 4.1 Fach

| Aktion | erlaubt | Pflichtfelder der Maske | Darunter | Aufträge |
|---|---|---|---|---|
| anlegen | ja | Name | – | – |
| ändern | ja (Name, Kurzform) | Name | zeigen den neuen Namen | bleiben; alte Auftragstexte nennen den alten Namen (Verlauf) |
| verschieben | – | | | |
| kopieren | nein (kein Fall) | | | |
| archivieren | ja | – (Bestätigung) | gelten als archiviert | bleiben dran, im Archiv sichtbar |
| wiederherstellen | ja | – | wie vorher | wie vorher |
| löschen | nur ohne Klassen und ohne Fach-Aufträge | – (Bestätigung) | – | – |

### 4.2 Klasse/Kurs

| Aktion | erlaubt | Pflichtfelder | Darunter | Aufträge |
|---|---|---|---|---|
| anlegen | ja | Name („8“, „Kurs 11“), Schuljahr (vorbelegt: laufendes, **F9**); Fach vom Ort vorbelegt | – | – |
| ändern | ja (Name, Schuljahr, Lerngruppe) | Name, Schuljahr | zeigen den neuen Namen | bleiben |
| verschieben | ja, in ein anderes Fach (Korrektur) | Ziel-Fach | Reihen und Stunden gehen mit | bleiben (über `id`) |
| kopieren | ja, als „Ins nächste Schuljahr übernehmen“ | Name (vorbelegt wie bisher, Lia ändert z. B. 7 → 8), Schuljahr (vorbelegt +1) | Reihen werden **nicht** kopiert (die gibt es einzeln, 4.3); die neue Klasse bekommt `herkunft` | bleiben an der alten Klasse; Lerngruppe mitnehmen? **F8** |
| archivieren | ja | – | gelten als archiviert | bleiben dran |
| wiederherstellen | ja | – | wie vorher | wie vorher |
| löschen | nur ohne Reihen und ohne Klassen-Aufträge | – | – | – |

Doppelte Klasse (gleicher Name, gleiches Schuljahr, gleiches Fach): Hinweis „gibt es schon“, kein Anlegen.

### 4.3 Reihe

| Aktion | erlaubt | Pflichtfelder | Darunter | Aufträge |
|---|---|---|---|---|
| anlegen | ja | Titel; Klasse vom Ort vorbelegt; `stand = "geplant"` | – | – |
| ändern | ja (Titel, Reihenfrage, Stand, Notizen, behandelt, Merksätze); nicht `id`, nicht `agenten` | Titel | – | bleiben; neue Läufe sehen den neuen Titel |
| verschieben | ja, in eine andere Klasse (auch anderes Fach, auch Archiv-Klasse) | Ziel-Klasse | Stunden gehen mit | bleiben (über `id`) |
| kopieren | ja, z. B. „in die 9 von 2026/27 übernehmen“ | Ziel-Klasse | Stunden kopiert mit neuen `id`s, nur Thema, ohne Marke (UB/Prüfung gehören zum alten Jahr) | **nicht** kopiert. Neue Reihe: `herkunft` = alte id, `stand = "geplant"`, ohne `agenten`, ohne `archiviert`. Material aus der alten Reihe übernehmen: **F7** |
| archivieren | ja; läuft noch ein Auftrag, Hinweis „läuft weiter, Ergebnis landet im Archiv“ | – | gelten als ausgeblendet | bleiben dran |
| wiederherstellen | ja | – | wie vorher | wie vorher |
| löschen | nur wenn nichts dranhängt (3.1) | – | – | – |

### 4.4 Stunde (bzw. Probe)

| Aktion | erlaubt | Pflichtfelder | Darunter | Aufträge |
|---|---|---|---|---|
| anlegen | ja (ans Ende oder „davor einfügen“) | Thema (bis 120 Zeichen, wie heute) | – | – |
| ändern | ja (Thema, Marke UB/Prüfung) | Thema | – | bleiben; alte Auftragstexte nennen das alte Thema |
| verschieben | ja, in der Reihe (Reihenfolge) und in eine andere Reihe | Ziel (Reihe, Stelle) | – | Material geht mit (Zuordnung über Stunden-`id`, nicht Nummer). Das Feld `reihe` alter Aufträge bleibt; der Ort eines Materials folgt der Stunde (Regel: Lias Zuordnung vor Feld `reihe` vor `agenten`) |
| kopieren | ja, einzeln in eine andere Reihe | Ziel-Reihe | – | nicht kopiert (nur das Thema) |
| archivieren (ausblenden) | ja | – | – | Material bleibt an der Stunde, sichtbar unter „Ausgeblendete Stunden“ |
| wiederherstellen | ja, an der alten Stelle | – | – | wie vorher |
| löschen | nur ohne Material und Aufträge | – | – | – |

---

## 5. Masken

Regel: Beim Anlegen nur Pflichtfelder, alles andere später über „Bearbeiten“ an der Ansicht des Objekts. Ort ist immer
vorbelegt (Lia legt dort an, wo sie gerade ist). Fehlertexte in Lias Worten, nichts wird gespeichert, solange ein
Pflichtfeld fehlt.

| Objekt | Anlegen (Pflicht) | Später ergänzbar | nie in einer Maske |
|---|---|---|---|
| Fach | Name | Kurzform | id |
| Klasse/Kurs | Name, Schuljahr (Auswahl: voriges, laufendes, nächstes) | Lerngruppe (mit festem Hinweis, Abschnitt 6) | id, herkunft, archiviert |
| Reihe | Titel | Reihenfrage, Stand, Notizen, schon behandelt, Merksätze (je Zeile einer) | id, herkunft, archiviert, agenten |
| Stunde | Thema | Marke (UB, Prüfung) | id, archiviert |

Längen: Titel und Namen bis 80 Zeichen, Thema bis 120 (wie heute), Reihenfrage bis 300, Notizen und Lerngruppe
bis 1500 (Vorschlag; heute längste Texte: Lerngruppe und Notizen der Straftheorien, je rund 440 Zeichen).

Bestätigungen nur bei Löschen und Archivieren einer Klasse oder eines Fachs (nennt die Zahl der Reihen). Alles
andere ohne Rückfrage, dafür mit Rückgängig.

---

## 6. Datenschutz: Feld Lerngruppe

Was heute drinsteht (Ethik 8): Leistungsstand, Lernschwierigkeiten, Sprache, Schulform und Bezirk, Herkunft und
Religion der Gruppe. Keine Namen. Ob das zusammen mit Schulort personenbeziehbar ist, kann ich nicht beurteilen;
K1/K2 aus `docs/webapp-plan.md` (Schulleitung, Datenschutzbeauftragte) sind offen.

Wohin der Text heute geht: Git-Verlauf seit 23.10. (bleibt dort auch nach Löschen), das Remote `sicherung` auf
GitHub (ob privat und ob es gepusht wird, weiß ich nicht), jeder Prompt von unterricht, chat und examen
(examen gibt alle Felder der Reihe weiter).

Vorschlag (**F6**):
1. **Lerngruppe an die Klasse**, nicht an jede Reihe: ein Ort, wird beim Kopieren einer Reihe nicht mitkopiert.
2. **Auslagern aus dem Repo**: `lia/instanz/lerngruppen.toml` (gitignored, chmod 600), Schlüssel = Klassen-`id`,
   gelesen von `agentkit.struktur`. Dann landet die Lerngruppe nicht mehr in Git und auf GitHub; Rückgängig geht
   trotzdem (Aktionsliste der App). Der bestehende Git-Verlauf bleibt, wie er ist (Umschreiben der Geschichte nur
   mit Jans ausdrücklichem Auftrag, nicht vorgeschlagen).
   Gegenvorschlag: bleibt in reihen.toml, dann gilt die Abnahme „Diff wie Handänderung“ auch für sie.
3. **Fester Hinweis an der Maske**: „Nur die Gruppe beschreiben. Keine Namen, keine Angaben zu einzelnen
   Schüler*innen (Diagnosen, Förderbedarf, Noten).“ Eine zuverlässige Namenserkennung gibt es nicht; die App
   behauptet keine.
4. Lerngruppe **nie** in Commit-Nachricht („Lerngruppe von Ethik 8 geändert“), Log, Ereignis, Telegram-Meldung oder
   Aktionsliste (dort nur „geändert“, der alte Text liegt für Rückgängig in der 0600-Ablage).
5. Archivierte Klassen: Lerngruppe nach Ablauf einer Frist leeren? (Löschkonzept, **F6**).

---

## 7. Datenquelle: Wie die App schreibt

Anforderungen: Jans Kommentare bleiben, ein App-Diff sieht aus wie eine Handänderung, keine Kollision mit Jans
Handänderungen, atomar, je Änderung ein Commit.

### 7.1 Optionen

| | Wie | Vorteile | Nachteile |
|---|---|---|---|
| **A** Block-Editor (Bordmittel) | App ändert den Text zeilenweise: Block per `id` finden, eine Zeile `schluessel = …` ersetzen/einfügen/löschen, Block einfügen/löschen/verschieben. Neue Werte im Stil der Datei (Text in `"…"`, lange Texte als `"""…"""` mit `\`-Umbruch wie Jan). Danach `tomllib` auf dem neuen Text und Vergleich mit dem erwarteten Inhalt, sonst Abbruch | kein neues Paket; Diffs minimal; Kommentare und Jans Umbrüche unberührt; vollständig testbar mit der echten Datei als Vorlage | eigener Code für eine Teilmenge von TOML; Konstrukte außerhalb (Inline-Tabellen, gepunktete Schlüssel) → App verweigert und meldet Jan |
| **B** tomlkit (neues Paket, nur Vorschlag) | lesen, ändern, schreiben mit Erhalt von Kommentaren und Format | weniger eigener Code, deckt ganzes TOML ab | neues Paket in shared/webapp/.venv (und agentkit, wenn struktur.py schreibt); neue Werte im Stil von tomlkit, nicht in Jans Stil; gelegentliche Umformatierung fremder Zeilen möglich, Diffs dann größer |
| **C** zweite Datei der App | App schreibt `struktur-app.toml`, Leser legen beide übereinander | reihen.toml bleibt reine Handdatei | zwei Quellen, jeder Leser muss zusammenführen; widerspricht „EINE Datei“; Diff in reihen.toml gibt es dann nicht |
| **D** Datenbank als Quelle | SQLite/JSON ist führend, reihen.toml wird erzeugt | einfachstes Schreiben, Transaktionen | Jan kann nicht mehr von Hand pflegen, Kommentare gehen verloren |

**Empfehlung A**, B nur, falls A in der Umsetzung zu groß wird. Der Editor sitzt in `agentkit.struktur`, nicht in
der Web-App, damit ihn später auch ein Agent oder ein Skript für Jan nutzen kann.

### 7.2 Ablauf einer Änderung

1. Operation statt Datei: Die Maske erzeugt z. B. `setzen(id, "titel", "Würde")`, nie eine ganze neue Datei.
2. Sperre `lia/instanz/.reihen.sperre` (flock) für Lesen-Ändern-Schreiben (App, später Skripte).
3. **Handänderungen schützen**: Hat `reihen.toml` ungespeicherte Änderungen (`git diff` nicht leer) und stammen sie
   nicht von der App selbst (Hash ihres letzten Schreibens), schreibt die App nicht und meldet Jan „reihen.toml hat
   ungespeicherte Handänderungen“.
4. Frisch lesen; hat sich seit dem Öffnen der Maske genau dieser Block-Schlüssel geändert → „Inzwischen geändert,
   bitte neu laden“, sonst Operation auf den aktuellen Text anwenden (Jans Änderungen an anderen Stellen bleiben).
5. Neuen Text prüfen mit `struktur.pruefen` (bis Bauschritt 2 zusätzlich mit `reihen.laden` und `logik.reihen_aus`).
   Ungültig → nichts schreiben.
6. **Atomar**: temporäre Datei im selben Ordner, `fsync`, `os.replace` auf den echten Pfad
   `lia/instanz/reihen.toml` (nie auf den Symlink `lia/unterricht/reihen.toml`, der bliebe sonst keine Verknüpfung).
7. Commit nur dieses Pfads (7.3), Eintrag in die Aktionsliste mit Gegen-Operation.

### 7.3 Commit (**F4**, **F5**)

Je Änderung ein Commit, Nachricht deutsch, z. B. „lia/instanz: Reihe „Würde“ in Ethik 9 angelegt (Lia, Web-App)“.

Problem: `commit.sh` startet den Hook `pruefen.sh` – gemessen heute **76 s**, und er bricht ab, wenn in irgendeinem
Ordner ein Test rot ist. Dann wäre Lias Änderung geschrieben, aber nicht committet.

| | Wie | Vorteile | Nachteile |
|---|---|---|---|
| a | `commit.sh` im Hintergrund, Datei ist sofort geschrieben | keine Ausnahme von der Regel | 76 s je Klick, bei fremdem Rot bleibt der Commit hängen (dann Meldung an Jan, neuer Versuch später) |
| b | eigenes Skript `commit-daten.sh` im Hauptordner: dieselbe flock-Sperre wie `commit.sh`, nur `lia/instanz/reihen.toml`, prüft nur die Struktur statt aller Tests | sekundenschnell, unabhängig von fremden Tests | Ausnahme von „Hook immer“; braucht Jans Okay (`--no-verify` für genau diesen Pfad) |
| c | eigenes Git-Repo für die Instanzdaten | sauber getrennt | großer Umbau, Verlauf wandert |

Empfehlung b. Autor der Commits: Jan, oder ein eigener Autor „Lia (Web-App)“? Eine Adresse dafür erfinde ich nicht.

---

## 8. Ebene Stunde: Speicherort

| | Ort | Vorteile | Nachteile |
|---|---|---|---|
| 1 | `[[reihe.stunde]]` in reihen.toml, mit `id`, ohne `nr` | eine Datei, Agenten lesen sie schon, Git-Verlauf, Diff wie von Hand | Datei wächst (bei 10 Stunden je Reihe um ~40 Zeilen je Reihe) |
| 2 | eine Datei je Reihe (`lia/instanz/stunden/<reihe-id>.toml`) | kleine Dateien | zweiter Ort für alle Leser; Stunde in andere Reihe = zwei Dateien in einem Commit |
| 3 | wie heute im Web-App-Zustand (data/, nicht in Git) | gebaut | Agenten sehen Stunden nur als Textzeile; kein Verlauf; Zuordnung über Nummer |

**Empfehlung 1.** Material einer Stunde: Zuordnung über die Stunden-`id` (Web-App-Zustand `stunde_von` wird von
`{"reihe", "nr"}` auf `{"stunde": id}` umgestellt; heute keine Daten zu übernehmen). Ein Auftrag aus einer Stunde
trägt künftig das Feld `ort` = Stunden-`id` (agentkit.auftraege, Hauptordner; `reihe` bleibt für ältere Leser
gesetzt). Die Zeile „Stunde n: Thema“ im Auftragstext bleibt für den Agenten.

Wo die Web-App Stunden aus der Datei heute sperrt („+ Stunde“ nur ohne Stunden in der Datei), entfällt die Sperre.

---

## 9. Offene Fragen an Jan

| | Frage | Mein Vorschlag |
|---|---|---|
| F1 | Eine Leseschicht `agentkit.struktur` für alle Leser (Hauptordner-Chat)? | ja |
| F2 | Formatwechsel wie Abschnitt 2 (`[[fach]]`, `[[klasse]]`, `reihe.klasse` = id)? Bricht alle Leser, bis sie umgestellt sind | ja, jetzt (heute hängt fast nichts an den Kennungen) |
| F3 | Stunden ohne gespeicherte Nummer, Reihenfolge = Reihenfolge in der Datei? | ja |
| F4 | Commit-Weg a, b oder c (7.3); bei b Ausnahme vom Hook für genau diesen Pfad | b |
| F5 | Autor der App-Commits? | offen |
| F6 | Lerngruppe auslagern (gitignored) oder in reihen.toml lassen? Frist zum Leeren im Archiv? | auslagern; Frist offen |
| F7 | Reihe kopieren: nur Struktur, oder auch finale Fassungen als Kopie mit Herkunft (Regel R10)? | erst nur Struktur, Material der alten Reihe als Liste „aus dem Vorjahr“ sichtbar |
| F8 | Klasse ins nächste Schuljahr: Lerngruppe mitnehmen? | als Häkchen, Standard aus |
| F9 | Wann beginnt das Schuljahr (für die Vorbelegung)? Ich vermute 1. August, weiß es aber nicht sicher | – |
| F10 | `bisherige_reihen` ablösen: Helfen (Ethik 8, mit Merksätzen) als echte abgeschlossene Reihe, Klasse 7 als Herkunft von Klasse 8? recherche/faelle.py liest das Feld heute | ja, mit Umstellung in recherche |
| F11 | Stunde mit Datum und „gehalten“? | erst nach Lias Test fragen |
| F12 | Reihe-Art „Inszenierung“ als Feld (heute: Probe statt Stunde nur bei `agenten = ["theater"]`; eine neue Inszenierung im nächsten Jahr hätte „Stunden“) | Feld `art`, freiwillig |
| F13 | „Keine Aufträge ohne Ort“: nur für neue Aufträge aus der App, oder auch für die 7 alten ohne Ort (4 Material, 2 Feedback, 1 Recherche)? | neue immer; alte bleiben in „Ohne Ort“, Lia kann sie zuordnen (gebaut) |
| F14 | Abnahme examen: echter Lauf (Runde 1 = mehrere anspruchsvolle Läufe, Kosten kenne ich nicht) oder Kontextprobe (`reihe_text` und `skizzen.kontext` ohne Claude)? | Kontextprobe plus ein echter unterricht-Lauf |
| F15 | `lia/instanz/fassungen/` in `.gitignore`? | ja (Hauptordner) |
| F16 | Am Schuljahresende Hinweis „Klassen archivieren?“ in Heute? | ja, nie automatisch |
| F17 | Löschen nur ohne Ebenen darunter, oder mitlöschen, wenn nirgends etwas hängt? | nur ohne Ebenen darunter |
| F18 | `agenten` pflegt nur Jan von Hand? | ja; Test: ein Agent höchstens in einer Reihe |
| F19 | Darf Lia schon schreiben, solange nur das Caddy-Passwort schützt, oder erst mit Konten (Entscheidung 30.10.)? | Jans Entscheidung |

---

## 10. Feste Regeln als Testliste

Ort der Tests: `shared/agentkit/tests/test_struktur.py` (schon in `pruefen.sh`), Web-App in `shared/webapp/tests/`,
Leser je in ihrem Ordner. Grundlage vieler Tests: eine Kopie der echten `reihen.toml` als Vorlage (nicht nur
Beispieldaten), Stand eingefroren in den Testdaten. Kein neuer Testordner nötig.

**Kennungen**
1. `id` ändert sich nie: ändern, verschieben, archivieren, wiederherstellen, Titel ändern lassen jede `id` gleich;
   eine Operation, die `id` setzen will, wird abgelehnt.
2. `id` einmalig über alle Ebenen; eine neue `id` kommt weder in der Datei noch in Aufträgen, Entwürfen, Zustand
   oder Chat-Verlauf vor.
3. Nach jedem Schreiben der App hat jedes Objekt eine gespeicherte `id` (keine abgeleitete).

**Ort**
4. Keine Aufträge ohne Ort: Ein Auftrag aus der App trägt immer einen Ort, den es gibt.
5. Keine Aktion nimmt einem Auftrag seinen Ort: Für jede Aktion gilt, jeder Auftrag, Entwurf und jede Zuordnung,
   der vorher einen Ort hatte, hat nachher einen (verschieben: denselben, mit neuer Lage).
6. Ein Agent steht in höchstens einer Reihe unter `agenten`; Kopieren übernimmt `agenten` nie.
7. Stunde verschieben: Ihr Material folgt (Zuordnung per Stunden-`id`), die Nummern sind danach 1..n lückenlos.

**Lebenslauf**
8. Löschen wird abgelehnt, wenn etwas hängt, je Quelle aus 3.1 ein eigener Fall.
9. Archivieren ändert genau eine Zeile, keine Zuordnung; Wiederherstellen ergibt die Datei byte-gleich wie vorher.
10. Rückgängig jeder Aktion ergibt den Ausgangstext byte-gleich, wenn dazwischen nichts geändert wurde; wurde der
    Block geändert, wird Rückgängig abgelehnt und nichts geschrieben.
11. Kopie einer Reihe: neue `id`s (auch Stunden), `herkunft` gesetzt, `stand = "geplant"`, ohne `agenten`,
    `archiviert`, Marken, Aufträge.

**Schreiben**
12. Atomar: Abbruch zwischen temporärer Datei und Ersetzen lässt die alte Datei unverändert, keine `.tmp` bleibt;
    `lia/unterricht/reihen.toml` ist danach noch ein Symlink.
13. Eine Änderung eines anderen Blocks zwischen Lesen und Schreiben bleibt erhalten; eine Änderung desselben
    Schlüssels führt zum Abbruch mit Hinweis.
14. Ungespeicherte Handänderung in Git → die App schreibt nicht, Meldung an Jan.
15. Die App schreibt nie in eine Datei, die schon ungültig ist, und nie eine ungültige.
16. Datei mit Konstrukten, die der Editor nicht kennt → Ablehnung statt Umformatieren.
17. Ohne Änderung lesen und schreiben ergibt die Datei byte-gleich.

**Aussehen wie von Hand**
18. Kommentare bleiben: Jede Operation auf der Kopie der echten Datei lässt alle Kommentarzeilen stehen (Ausnahme
    Löschen: der Kommentar direkt über dem Block geht mit und kommt mit Rückgängig zurück).
19. Diff je Operation gegen erwartete Diffs (z. B. Titel ändern = eine Zeile weg, eine dazu; Stunde verschieben =
    ein Block an anderer Stelle; Archivieren = eine Zeile dazu).

**Commit**
20. Jede Änderung ist genau ein Commit, nur mit dem Pfad `lia/instanz/reihen.toml`, deutsche Nachricht mit Objekt
    und Aktion.
21. Commit-Nachricht, Log, Ereignis, Meldung und Aktionsliste enthalten keinen Lerngruppen-Text.

**Leser**
22. Nach jeder Operation liefern unterricht (`prompt_reihen` mit gewählter Reihe), chat (`kontext_text`), examen
    (`reihe_text`, genau ein Treffer, auch mit Stunden) und Web-App (Baum) die Reihe richtig.
23. Auftrags-JSONs und Fassungen sind nach jeder Strukturaktion byte-gleich (Prüfsumme vorher/nachher).

**Eingaben**
24. Leeres Pflichtfeld, zu lang, doppelte Klasse im selben Schuljahr → kein Schreiben, Fehlertext für Lia.
25. Schreibende Formulare nur mit Formular-Token und passendem Origin (wie „Neuer Auftrag“ heute).

---

## 11. Bauschritte (je ein Chat, je ein Commit, `./pruefen.sh` grün)

0. Jan: Antworten auf F1–F19, Freigabe dieses Plans.
1. **Hauptordner**: `agentkit.struktur` lesend (laden, prüfen, auflösen, `haengt_dran`), Tests 1–3, 6, 15, 17;
   `.gitignore` für `lia/instanz/fassungen/` (F15); Feld `ort` in `agentkit.auftraege`; ggf. `commit-daten.sh` (F4).
2. **Leser umstellen**, je in ihrem Chat: lia/unterricht (reihen.py über struktur), lia/examen (`id` statt
   Titelanfang, behebt den Absturz mit Stunden), lia/recherche (`id` statt „Straftheorien“, frühere Reihenfragen aus
   struktur statt Regex), lia/chat (kontext), shared/webapp (ordnung, logik). Test 22 je Ordner.
3. **Migration der Datei** (dieser Ordner, ein Commit wie von Hand, nach Jans Okay): `[[fach]]`, `[[klasse]]`,
   Schuljahr 2026/27 an den laufenden Klassen, `stand = "geplant"` und Titel ohne „(in Planung)“, Platzhalter-Reihe
   Kurs 11 wird Klasse, Helfen als Reihe (F10), ggf. Lerngruppe auslagern (F6). Vorher und nachher: echter Prompt
   von unterricht für eine Reihe vergleichen.
4. **Hauptordner**: Schreib-Operationen und Block-Editor in `agentkit.struktur`, Rückgängig, Tests 4–5, 7–14, 16,
   18–21, 23.
5. **shared/webapp**: „Bearbeiten“ und „+ Neu“ je Ebene, Aktionen aus Abschnitt 4, Rückgängig-Hinweis und „Letzte
   Änderungen“, Stunden aus der Datei statt aus data/, Tests 24–25.
6. Abnahme (Abschnitt 12), dann Test mit Lia.

---

## 12. Abnahme

| Kriterium | Wie geprüft |
|---|---|
| `./pruefen.sh` ALLES GRÜN mit Tests aus Abschnitt 10 | Ausgabe im Commit des letzten Bauschritts |
| Echter Lauf von unterricht und examen greift die Reihe richtig auf | In der App: Reihe umbenennen und eine Stunde verschieben, dann ein Arbeitsblatt-Auftrag an dieser Stunde (echter unterricht-Lauf). Prüfen: Prompt nennt die Reihe als gewählt, die Stunde mit neuer Nummer und Thema. examen je nach F14. |
| Git-Diff sieht aus wie eine Handänderung | je Aktion `git show` des App-Commits: nur die betroffenen Zeilen, Kommentare unverändert, Stil wie Jans Einträge |
| Wiederherstellungsprobe | Reihe mit Material und Stunden (Testinstanz) archivieren, wiederherstellen: Datei byte-gleich, Material an denselben Stunden, „Heute“ zeigt dieselben Brotkrumen, Prüfsummen der Aufträge gleich |
| Test mit Lia | Abschnitt 13 |

---

## 13. Test mit Lia (Aufbau wie webapp-aufbau.md Abschnitt 6, diesmal mit Zahlen)

**Rahmen.** Lias Rechner, echte App, aber auf der **Testinstanz** (`WEBAPP_INSTANZ`, Kopie der echten
`reihen.toml` mit Beispiel-Stunden in Straftheorien und ein paar Test-Aufträgen), damit nichts in Lias echte
Daten gerät. Jan liest vor, legt den Zettel hin, hilft erst nach 2 Minuten Stillstand (dann „mit Hilfe“). Lia denkt
laut. Hinweis vorher: „Getestet wird die Seite, nicht du.“

| # | Aufgabe (vorlesen, ohne Wörter der Oberfläche) | Erfolg, wenn | richtiger erster Klick |
|---|---|---|---|
| 1 | „Du bekommst ab Februar noch einen Ethik-Kurs, eine 9. Trag ihn ein.“ | Klasse „9“ in Ethik, Schuljahr 2026/27 | Fach Ethik bzw. „+ Klasse“ dort |
| 2 | „Die Reihe Freundschaft aus deiner 7 vom letzten Jahr willst du in der neuen 9 wieder machen. Hol sie dorthin.“ | Kopie in Ethik 9, Original bleibt im Archiv | Archiv Klasse 7 · 2025/26 bzw. die Reihe Freundschaft |
| 3 | „In der Strafe-Reihe soll die Stunde zu von Liszt vor die Stunde zu Kant.“ | Reihenfolge geändert, Material bei seiner Stunde | Reihe Straftheorien |
| 4 | „Die Reihe zum nackten Wahnsinn ist vorbei. Räum sie aus deiner Übersicht, ohne dass etwas verloren geht.“ | Reihe archiviert (nicht gelöscht) | Reihe Der nackte Wahnsinn |
| 5 | „Du brauchst sie doch noch mal. Hol sie zurück, mit allem, was dazugehört.“ | wiederhergestellt; Lia findet ein Material darin wieder | Archiv bzw. Rückgängig |

**Gemessen je Aufgabe**: Erfolg (ohne Hilfe / mit Hilfe / nicht), erster Klick (richtig/falsch, wohin), Zeit bis
Erfolg in Sekunden, wörtliche Äußerungen. Bogen: `shared/webapp/data/ia/testbogen-struktur.csv`.

**Ziel**: 5 von 5 ohne Hilfe (Jans Vorgabe „alles ohne Hilfe“), erster Klick bei mindestens 4 von 5 richtig.
Zeiten werden erhoben, aber ohne Sollwert (einen belastbaren Vergleichswert habe ich nicht).

**Danach (5 Minuten)**: „Was war unklar?“, „Fehlt dir beim Anlegen ein Feld?“, „Willst du an einer Stunde ein Datum
oder ‚gehalten‘?“ (F11), „Was erwartest du, wenn du eine Reihe in ein neues Jahr holst: auch die Materialien?“ (F7).

**Auswertung**: Was zweimal falsch angeklickt wird, wird geändert. Unter 5 von 5: ändern, zweiter Test.
