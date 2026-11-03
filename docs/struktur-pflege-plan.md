# Plan: Lia pflegt Fach → Klasse/Kurs → Reihe → Stunde selbst

Stand 03.11.2026. **Von Jan freigegeben am 03.11.2026.** Gebaut wird in den Bauschritten aus Abschnitt 11, je im
zuständigen Chat. Offene Fragen in Abschnitt 9 (**F1** bis **F24**). Entschieden (Jan 03.11.): F1 bis F6, F9, F11, F14, F19 bis F24. Offen: F7, F8, F10, F12, F13, F15 bis F18.

**Erweiterung 03.11. nach der Freigabe:** Jan beschreibt den Ablauf vom neuen Schuljahr an. Die Klasse bekommt
wiederkehrende Termine, die Reihe bekommt Termine zugeteilt (Abschnitt 2a). Das ändert Datenmodell, Masken und
Matrix. Bauschritte 1 und 2 bleiben gültig. Jan hat 2a angesehen und F20–F24 beantwortet (03.11.). Bauschritt 1b
ist erledigt (03.11.), Bauschritt 3 (Migration) kann folgen.

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

Jans frühere Entscheidung (30.10.) „Reihen pflegt vorerst Jan, Lia erst mit Konten“ gilt nicht mehr (Jan 03.11.,
F19): Lia pflegt die Struktur, sobald es gebaut ist, auch ohne Konten (Schutz bis dahin: Caddy-Passwort).

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
- **Examen ist eine Stunde** (Jan 03.11., F14): die Prüfungsstunde ist eine Stunde mit `marke = "Prüfung"` in einer
  normalen Reihe, nichts Eigenes. lia/examen findet seine Reihe darüber und nicht mehr über den Titelanfang
  (`titel_in_reihen_toml` entfällt) und nicht über `agenten = ["examen"]` (entfällt). Welche Stunde der Reihe die
  Prüfungsstunde ist, ergibt sich aus ihrer Stelle (`pruefungsstunde_in_reihe` in examen.toml entfällt). Gilt
  genauso für eine spätere Examensreihe in einer anderen Klasse: Lia setzt die Marke, mehr nicht. Hat keine oder
  mehr als eine Stunde die Marke „Prüfung“, meldet examen das an Jan und läuft nicht.

**Eine Leseschicht für alle.** Heute prüfen vier Stellen die Datei je anders. Vorschlag: `shared/agentkit/struktur.py`
(Hauptordner-Chat) mit `laden()` → aufgelöste Objekte (eine Reihe kennt Fachname, Klassenname, Schuljahr,
Lerngruppe, Stunden mit Nummer), `pruefen()`, `ort(id)`, `haengt_dran(id)` und den Schreib-Operationen
(Abschnitt 4). unterricht, examen, recherche, chat und Web-App lesen nur noch darüber; ihre Prompt-Texte bleiben
gleich, weil die aufgelösten Felder dieselben Namen haben. **F1.**

---

## 2a. Termine und Ablauf vom neuen Schuljahr an (Jan 03.11.)

Jans Vorgabe: Neues Schuljahr, neuer Kurs bzw. neue Klasse (beides dieselbe Organisationseinheit). Beim Anlegen gibt
man den wiederkehrenden Termin an, und die App erzeugt daraus alle Termine des Halbjahrs. In der Maske der Reihe
teilt man diese Termine der Reihe zu oder legt Stunden an, wenn es noch keine Termine gibt. Antworten (Jan 03.11.):
Die Maske fragt das Bundesland und erkennt Ferien selbst; bei Ausfall entscheidet Lia jedes Mal, ob alles nachrückt;
mehrere Termine je Woche und Doppelstunden kommen vor, aber nicht immer; A/B-Wochen gibt es nicht (F22); zum Halbjahr ändert sich teils
der Wochentag, die Anzahl der Termine nicht.

**Grundsatz Flexibilität (Jan 03.11.):** Kein starres System. Stunden und Reihen lassen sich im Jahr jederzeit
einfach hin- und herschieben, wenn Lia das will. Daraus folgt:
- Nichts ist gesperrt außer dem, was Daten kaputt machen würde (ein Termin trägt höchstens eine Stunde). Keine
  Pflichtreihenfolge der Reihen, Lücken zwischen Reihen sind erlaubt, Stunden ohne Termin auch.
- Verschieben geht mit einem Griff: Stunde oder ganze Reihe ziehen bzw. „Verschieben nach …“ mit Terminauswahl.
  Trifft das Ziel belegte Termine, fragt die App einmal: „Dahinter alles nachrücken“ oder „Tauschen“.
- Jede Verschiebung ist eine Aktion mit Rückgängig, ohne Rückfrage.
- Die App rechnet Daten, Lia entscheidet. Kein Automatismus verschiebt etwas, ohne dass Lia es auslöst.

### 2a.1 Ablauf

| Schritt | Wer, wann | Was Lia angibt | Was die App macht |
|---|---|---|---|
| 0 Schule | einmal (beim ersten Kurs) | Bundesland | Schuljahr und Halbjahre aus den Ferien des Bundeslands (Schuljahr = nach den Sommerferien bis zu den nächsten); Feiertage dazu |
| 1 Klasse/Kurs anlegen | Schuljahresbeginn | Fach (vorbelegt), Name, Schuljahr (vorbelegt); **Stundenplan**: je wiederkehrendem Termin Wochentag, Unterrichtsstunde, Einzel- oder Doppelstunde; beliebig viele | erzeugt alle Termine bis Halbjahresende ohne Ferien und Feiertage; sie sind zunächst **frei** (gehören zur Klasse, zu keiner Reihe) |
| 2 Reihe anlegen | wenn Lia plant | Titel; optional in derselben Maske: **freie Termine zuteilen** (Häkchen in der Terminliste oder „ab Di 11.11., 8 Termine“), oder **Stunden ohne Termin** anlegen | je zugeteiltem Termin eine Stunde der Reihe mit Datum, Thema zunächst offen |
| 3 Stunden füllen | laufend | Thema, Marke (UB/Prüfung), Material | wie bisher |
| 4 Alltag | laufend | Termin fällt aus: **„Alles rückt nach“** oder **„Diese Stunde fällt weg“**; Stunde verschieben; Reihe bekommt mehr oder weniger Termine; einzelner Zusatztermin | rechnet Daten neu (2a.3) |
| 5 Halbjahr | Halbjahreswechsel | „Stundenplan ab 2. Halbjahr“: vorbelegt der alte, Lia ändert z. B. den Wochentag | erzeugt die Termine des 2. Halbjahrs; Stunden nach dem Stichtag behalten ihre Reihenfolge und bekommen die neuen Daten (gleiche Anzahl, Jans Antwort 4) |
| 6 Schuljahresende | Sommer | archivieren; „Ins nächste Schuljahr übernehmen“; Reihe kopieren | wie Abschnitt 4 |

### 2a.2 Modell

Termin und Stunde bleiben getrennt: Der **Termin** ist ein Platz im Stundenplan der Klasse (Datum, Unterrichtsstunde),
die **Stunde** ist der Inhalt einer Reihe. Eine Stunde liegt auf höchstens einem Termin, ein Termin trägt höchstens
eine Stunde. Freie Termine werden nicht gespeichert, sondern aus dem Stundenplan berechnet; gespeichert wird nur, was
Lia festlegt.

```toml
[schule]
bundesland = "BE"

[[klasse]]
id = "ethik-9"
fach = "ethik"
name = "9"
schuljahr = "2026/27"
ausfall = ["2026-11-18/3"]       # gestrichene Termine („alles rückt nach“)

[[klasse.zeitplan]]              # ein wiederkehrender Termin; beliebig viele
tag = "Di"
stunde = 3                       # Unterrichtsstunde laut Stundenplan
laenge = 1                       # 1 Einzelstunde, 2 Doppelstunde (= ein Termin, F21)
ab = "2026-08-31"
bis = "2027-01-29"               # neuer Eintrag ab dem 2. Halbjahr, wenn sich der Tag ändert

[[reihe.stunde]]
id = "s-4k2m9a"
termin = "2026-11-11/3"          # Datum/Unterrichtsstunde; fehlt bei einer Stunde ohne Termin
thema = "Kant: Vergeltung"
```

- **Ferien und Feiertage** kommen aus einer Datei je Bundesland und Schuljahr, die die App nur liest (Quelle **F20**).
  Bewegliche Ferientage und Studientage der Schule stehen in keiner Quelle: Lia streicht diese Termine als Ausfall.
- **Stunde ohne Termin** (in der Maske angelegt, bevor es Termine gibt): steht in der Reihe ohne Datum; „Termine
  zuteilen“ füllt die Daten später der Reihe nach.
- **Reihenfolge** bleibt Reihenfolge der Blöcke (F3); bei Stunden mit Termin ist sie zugleich die Reihenfolge der
  Daten. Die Leseschicht zählt Nummer und Datum.
- **Prüfungsstunde**: ihr Datum ist der Prüfungstermin; `termin` in examen.toml kann dann entfallen (später, im
  examen-Chat).
- Die Agenten bekommen das Datum je Stunde in den Kontext („Stunde 3, Di 25.11.: Kant“).

### 2a.3 Rechenregeln

- **Alles rückt nach**: Der Termin kommt in `ausfall`. Jede spätere Stunde der Klasse rückt auf den nächsten Termin,
  über Reihengrenzen hinweg (F23, Jan 03.11.). Die letzte Stunde nimmt den nächsten freien Termin; gibt es keinen mehr im
  Halbjahr, steht sie ohne Termin da und die App sagt es. Inhalte, ids und Material bleiben.
- **Diese Stunde fällt weg**: Der Termin kommt in `ausfall`, die Stunde wird ausgeblendet (Abschnitt 3). Alle
  anderen Daten bleiben.
- **Stunde verschieben**: Der Inhalt wandert, die Termine bleiben. Die Stunden zwischen alter und neuer Stelle
  rücken je einen Termin weiter.
- **Halbjahreswechsel mit neuem Wochentag**: Die Stunden ab dem Stichtag werden der Reihe nach auf die neuen Termine
  gelegt. Bei gleicher Anzahl bleibt keine Stunde ohne Termin; bei abweichender Anzahl sagt die App, welche.
- **Reihe zeitlich verschieben**: Die ganze Reihe beginnt an einem anderen Termin (z. B. „Würde vor Strafe“ oder „ab
  12.01.“); ihre Stunden liegen dann der Reihe nach auf den Terminen ab dort. Belegte Termine: „Dahinter alles
  nachrücken“ (die andere Reihe rückt hinter sie) oder „Tauschen“ (zwei Reihen tauschen ihre Termine). Freie Termine
  dazwischen bleiben frei.
- **Stunde auf einen bestimmten Termin**: Eine Stunde lässt sich direkt auf einen freien Termin legen, auch in eine
  Lücke oder in eine andere Reihe; auf einen belegten Termin nur mit „nachrücken“ oder „tauschen“.
- **Zusatztermin** (Nachholen, Projekttag): einzelner Termin an der Klasse, `zusatz = ["2026-12-02/5"]`.
- **Ausfall zurücknehmen**: über Rückgängig (Abschnitt 3.1), stellt alle Daten wieder her.

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
Termin:        frei ──zuteilen──► trägt eine Stunde;  frei oder belegt ──Ausfall──► gestrichen (Rückgängig möglich)
               vergangen = gehalten (aus dem Datum, kein eigenes Feld)
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
- Stunde: kein eigener Stand. Das Datum kommt vom Termin, „gehalten“ heißt: der Termin liegt in der Vergangenheit
  (F11, durch Jans Ablauf entschieden).

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
| anlegen | ja | Name („8“, „Kurs 11“), Schuljahr (vorbelegt aus den Ferien des Bundeslands); Fach vom Ort vorbelegt; Stundenplan optional, aber gleich in der Maske (2a.1) | erzeugt freie Termine | – |
| ändern | ja (Name, Schuljahr, Lerngruppe, Stundenplan ab einem Stichtag) | Name, Schuljahr | Stundenplan ab Stichtag: Stunden danach bekommen neue Daten (2a.3) | bleiben |
| verschieben | ja, in ein anderes Fach (Korrektur) | Ziel-Fach | Reihen und Stunden gehen mit | bleiben (über `id`) |
| kopieren | ja, als „Ins nächste Schuljahr übernehmen“ | Name (vorbelegt wie bisher, Lia ändert z. B. 7 → 8), Schuljahr (vorbelegt +1) | Reihen werden **nicht** kopiert (die gibt es einzeln, 4.3); die neue Klasse bekommt `herkunft` | bleiben an der alten Klasse; Lerngruppe mitnehmen? **F8** |
| archivieren | ja | – | gelten als archiviert | bleiben dran |
| wiederherstellen | ja | – | wie vorher | wie vorher |
| löschen | nur ohne Reihen und ohne Klassen-Aufträge | – | – | – |

Doppelte Klasse (gleicher Name, gleiches Schuljahr, gleiches Fach): Hinweis „gibt es schon“, kein Anlegen.

### 4.3 Reihe

| Aktion | erlaubt | Pflichtfelder | Darunter | Aufträge |
|---|---|---|---|---|
| anlegen | ja | Titel; Klasse vom Ort vorbelegt; `stand = "geplant"`; optional freie Termine zuteilen oder Stunden ohne Termin anlegen (2a.1) | je Termin eine Stunde, Thema offen | – |
| ändern | ja (Titel, Reihenfrage, Stand, Notizen, behandelt, Merksätze); nicht `id`, nicht `agenten` | Titel | – | bleiben; neue Läufe sehen den neuen Titel |
| verschieben | ja, in eine andere Klasse (auch anderes Fach, auch Archiv-Klasse) | Ziel-Klasse | Stunden gehen mit (ohne Termin, wenn die Ziel-Klasse andere Termine hat) | bleiben (über `id`) |
| zeitlich verschieben | ja, jederzeit (Grundsatz Flexibilität, 2a) | Start-Termin; bei belegten Terminen „nachrücken“ oder „tauschen“ | Stunden bekommen neue Daten, Reihenfolge bleibt | bleiben |
| kopieren | ja, z. B. „in die 9 von 2026/27 übernehmen“ | Ziel-Klasse | Stunden kopiert mit neuen `id`s, nur Thema, ohne Marke (UB/Prüfung gehören zum alten Jahr) | **nicht** kopiert. Neue Reihe: `herkunft` = alte id, `stand = "geplant"`, ohne `agenten`, ohne `archiviert`. Material aus der alten Reihe übernehmen: **F7** |
| archivieren | ja; läuft noch ein Auftrag, Hinweis „läuft weiter, Ergebnis landet im Archiv“ | – | gelten als ausgeblendet | bleiben dran |
| wiederherstellen | ja | – | wie vorher | wie vorher |
| löschen | nur wenn nichts dranhängt (3.1) | – | – | – |

### 4.4 Stunde (bzw. Probe)

| Aktion | erlaubt | Pflichtfelder | Darunter | Aufträge |
|---|---|---|---|---|
| anlegen | ja (ans Ende oder „davor einfügen“; auch über „Termine zuteilen“) | keins: Thema darf offen bleiben („Thema offen“), bis 120 Zeichen | – | – |
| ändern | ja (Thema, Marke UB/Prüfung) | – | – | bleiben; alte Auftragstexte nennen das alte Thema |
| verschieben | ja, in der Reihe (Reihenfolge; der Inhalt wandert, die Termine bleiben, 2a.3) und in eine andere Reihe | Ziel (Reihe, Stelle) | – | Material geht mit (Zuordnung über Stunden-`id`, nicht Nummer). Das Feld `reihe` alter Aufträge bleibt; der Ort eines Materials folgt der Stunde (Regel: Lias Zuordnung vor Feld `reihe` vor `agenten`) |
| kopieren | ja, einzeln in eine andere Reihe | Ziel-Reihe | – | nicht kopiert (nur das Thema) |
| archivieren (ausblenden) | ja | – | – | Material bleibt an der Stunde, sichtbar unter „Ausgeblendete Stunden“ |
| wiederherstellen | ja, an der alten Stelle | – | – | wie vorher |
| löschen | nur ohne Material und Aufträge | – | – | – |

### 4.5 Termin

| Aktion | erlaubt | Pflichtfelder | Folgen | Aufträge |
|---|---|---|---|---|
| anlegen | über den Stundenplan der Klasse; einzeln als Zusatztermin | Stundenplan: Wochentag, Unterrichtsstunde (Einzel/Doppel); Zusatztermin: Datum, Unterrichtsstunde | freie Termine | – |
| zuteilen | ja, an eine Reihe (in der Maske der Reihe oder an der Reihe) | Auswahl der Termine | je Termin eine Stunde, Thema offen; Stunden ohne Termin bekommen der Reihe nach Daten | – |
| freigeben | ja (Reihe braucht weniger) | – | nur leere Stunden (ohne Thema, ohne Material) verschwinden; sonst wird die Stunde ohne Termin behalten | bleiben |
| ausfallen | ja, Lia wählt jedes Mal: „Alles rückt nach“ oder „Diese Stunde fällt weg“ (Jan 03.11.) | Auswahl | 2a.3 | bleiben an ihren Stunden |
| Stundenplan ändern | ja, ab einem Stichtag (Halbjahr) | Stichtag, neuer Stundenplan (vorbelegt der alte) | Stunden ab Stichtag bekommen neue Daten | bleiben |
| kopieren, archivieren | – (gehört zur Klasse) | | | |
| wiederherstellen | über Rückgängig | – | Daten wie vorher | wie vorher |

---

## 5. Masken

Regel: Beim Anlegen nur Pflichtfelder, alles andere später über „Bearbeiten“ an der Ansicht des Objekts. Ort ist immer
vorbelegt (Lia legt dort an, wo sie gerade ist). Fehlertexte in Lias Worten, nichts wird gespeichert, solange ein
Pflichtfeld fehlt.

| Objekt | Anlegen (Pflicht) | Später ergänzbar | nie in einer Maske |
|---|---|---|---|
| Fach | Name | Kurzform | id |
| Schule (einmal) | Bundesland | – | – |
| Klasse/Kurs | Name, Schuljahr (vorbelegt); in derselben Maske, aber freiwillig: Stundenplan (je Zeile Wochentag, Unterrichtsstunde, Einzel/Doppel; „+ weiterer Termin“) | Lerngruppe (mit festem Hinweis, Abschnitt 6), Stundenplan ab Stichtag | id, herkunft, archiviert, ausfall |
| Reihe | Titel; in derselben Maske, aber freiwillig: freie Termine zuteilen (Liste mit Häkchen, Schnellwahl „ab … n Termine“) oder „+ Stunde ohne Termin“ | Reihenfrage, Stand, Notizen, schon behandelt, Merksätze (je Zeile einer) | id, herkunft, archiviert, agenten |
| Stunde | – (Thema darf offen sein) | Thema, Marke (UB, Prüfung) | id, archiviert, termin (ändert sich nur über Zuteilen, Verschieben, Ausfall) |
| Ausfall | Termin, „Alles rückt nach“ oder „Diese Stunde fällt weg“ | – | – |

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

Entschieden (Jan 03.11., **F6**): Lerngruppe an die Klasse und aus dem Repo auslagern (Punkte 1 und 2).
1. **Lerngruppe an die Klasse**, nicht an jede Reihe: ein Ort, wird beim Kopieren einer Reihe nicht mitkopiert.
2. **Auslagern aus dem Repo**: `lia/instanz/lerngruppen.toml` (gitignored, chmod 600), Schlüssel = Klassen-`id`,
   gelesen von `agentkit.struktur`. Dann landet die Lerngruppe nicht mehr in Git und auf GitHub; Rückgängig geht
   trotzdem (Aktionsliste der App). Der bestehende Git-Verlauf bleibt, wie er ist (Umschreiben der Geschichte nur
   mit Jans ausdrücklichem Auftrag, nicht vorgeschlagen).
3. **Fester Hinweis an der Maske**: „Nur die Gruppe beschreiben. Keine Namen, keine Angaben zu einzelnen
   Schüler*innen (Diagnosen, Förderbedarf, Noten).“ Eine zuverlässige Namenserkennung gibt es nicht; die App
   behauptet keine.
4. Lerngruppe **nie** in Commit-Nachricht („Lerngruppe von Ethik 8 geändert“), Log, Ereignis, Telegram-Meldung oder
   Aktionsliste (dort nur „geändert“, der alte Text liegt für Rückgängig in der 0600-Ablage).
5. Archivierte Klassen: Lerngruppe nach Ablauf einer Frist leeren? (Löschkonzept, offen, Teil von F6).

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

Entschieden (Jan 03.11., F4): **b**. Das ist eine Ausnahme vom Hook für genau den Pfad `lia/instanz/reihen.toml`
und genau dieses Skript. Sie kommt als Zeile unter „Fertig heißt“ in CLAUDE.md (Bauschritt 1). Alle anderen
Commits laufen weiter über `commit.sh` mit Hook. Autor der Commits: Jan, oder ein eigener Autor „Lia (Web-App)“?
Eine Adresse dafür erfinde ich nicht. Entschieden (F5, Jan hatte keine Vorliebe): Autor bleibt Jan
(git-Einstellung wie heute), die Nachricht nennt „(Lia, Web-App)“. Keine neue Identität, keine erfundene Adresse.

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
| F1 | Eine Leseschicht `agentkit.struktur` für alle Leser (Hauptordner-Chat)? | **entschieden: ja** (Jan 03.11.) |
| F2 | Formatwechsel wie Abschnitt 2 (`[[fach]]`, `[[klasse]]`, `reihe.klasse` = id)? Bricht alle Leser, bis sie umgestellt sind | **entschieden: ja** (Jan 03.11.); Migration erst nach Bauschritt 2 |
| F3 | Stunden ohne gespeicherte Nummer, Reihenfolge = Reihenfolge in der Datei? | **entschieden: ja** (Jan 03.11.) |
| F4 | Commit-Weg a, b oder c (7.3); bei b Ausnahme vom Hook für genau diesen Pfad | **entschieden: b** (Jan 03.11.) |
| F5 | Autor der App-Commits? | **entschieden:** Jan als Autor, „(Lia, Web-App)“ in der Nachricht (7.3) |
| F6 | Lerngruppe auslagern (gitignored) oder in reihen.toml lassen? Frist zum Leeren im Archiv? | **entschieden: auslagern** (Jan 03.11.); Frist offen |
| F7 | Reihe kopieren: nur Struktur, oder auch finale Fassungen als Kopie mit Herkunft (Regel R10)? | erst nur Struktur, Material der alten Reihe als Liste „aus dem Vorjahr“ sichtbar |
| F8 | Klasse ins nächste Schuljahr: Lerngruppe mitnehmen? | als Häkchen, Standard aus |
| F9 | Wann beginnt das Schuljahr (für die Vorbelegung)? | **entschieden** (Jan 03.11.): die Maske fragt das Bundesland, Schuljahr und Halbjahre ergeben sich aus dessen Ferien (2a.1) |
| F10 | `bisherige_reihen` ablösen: Helfen (Ethik 8, mit Merksätzen) als echte abgeschlossene Reihe, Klasse 7 als Herkunft von Klasse 8? recherche/faelle.py liest das Feld heute | **teils entschieden** (Jan 03.11.): Helfen ist Reihe, Klasse 7 Herkunft von Klasse 8; `bisherige_reihen` fällt erst, wenn unterricht frühere Reihen aus der Herkunft liest (recherche liest es im neuen Format nicht mehr) |
| F11 | Stunde mit Datum und „gehalten“? | **entschieden** durch Jans Ablauf: Datum vom Termin, gehalten = vergangen (2a) |
| F12 | Reihe-Art „Inszenierung“ als Feld (heute: Probe statt Stunde nur bei `agenten = ["theater"]`; eine neue Inszenierung im nächsten Jahr hätte „Stunden“) | Feld `art`, freiwillig |
| F13 | „Keine Aufträge ohne Ort“: nur für neue Aufträge aus der App, oder auch für die 7 alten ohne Ort (4 Material, 2 Feedback, 1 Recherche)? | neue immer; alte bleiben in „Ohne Ort“, Lia kann sie zuordnen (gebaut) |
| F14 | Wie findet examen seine Reihe, und wie wird es abgenommen? | **entschieden** (Jan 03.11.): Examen ist eine Stunde mit Marke „Prüfung“ (Abschnitt 2); Abnahme mit echtem Lauf (Abschnitt 12) |
| F15 | `lia/instanz/fassungen/` in `.gitignore`? | ja (Hauptordner) |
| F16 | Am Schuljahresende Hinweis „Klassen archivieren?“ in Heute? | ja, nie automatisch |
| F17 | Löschen nur ohne Ebenen darunter, oder mitlöschen, wenn nirgends etwas hängt? | nur ohne Ebenen darunter |
| F18 | `agenten` pflegt nur Jan von Hand? | ja; Test: ein Agent höchstens in einer Reihe |
| F19 | Darf Lia schon schreiben, solange nur das Caddy-Passwort schützt, oder erst mit Konten (Entscheidung 30.10.)? | **entschieden: ja, ohne Konten** (Jan 03.11.) |
| F20 | Woher kommen Ferien und Feiertage je Bundesland? a) Datei im Repo, je Schuljahr von Hand aus der amtlichen Übersicht der Kultusministerkonferenz gepflegt; b) ein Skript holt sie einmal je Schuljahr über eine offene Schnittstelle (z. B. OpenHolidays API; Angebot und Bedingungen habe ich nicht geprüft) in dieselbe Datei. Die App selbst geht in beiden Fällen nicht ins Netz | **entschieden: b mit a als Rückfall** (Jan 03.11., Okay für den Abruf einmal je Schuljahr) |
| F21 | Doppelstunde = ein Termin mit einer Stunde (90 Minuten) oder zwei Termine? | **entschieden: ein Termin** (Jan 03.11.) |
| F22 | A/B-Wochen? | **entschieden: gibt es nicht** (Jan 03.11.); kein Feld `woche` |
| F23 | „Alles rückt nach“ auch über die Grenze zur nächsten Reihe der Klasse? | **entschieden: ja** (Jan 03.11.), alle späteren Stunden der Klasse |
| F24 | Halbjahr endet mit Beginn der Winterferien, Stichtag änderbar? | **entschieden: ja** (Jan 03.11.) |

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

**Termine** (2a)
26. Aus dem Stundenplan entstehen genau die Schultage ohne Ferien und Feiertage (Prüfdaten: Ferien-Datei eines
    Bundeslands, eingefroren).
27. Doppelstunde ergibt einen Termin, mehrere Termine je Woche stehen in Datumsfolge.
28. „Alles rückt nach“: Alle späteren Stunden der Klasse wandern um genau einen Termin, ids, Themen und Material
    bleiben; Rückgängig stellt alle Daten wieder her.
29. „Diese Stunde fällt weg“: nur diese Stunde ausgeblendet, alle anderen Daten unverändert.
30. Stundenplan ab Stichtag mit neuem Wochentag: Stunden danach behalten die Reihenfolge und bekommen neue Daten;
    bei gleicher Anzahl keine Stunde ohne Termin.
31. Ein Termin trägt höchstens eine Stunde, eine Stunde liegt auf höchstens einem Termin; ein gestrichener Termin
    trägt keine.
32. Reihe anlegen mit zugeteilten Terminen ist eine Aktion, ein Commit, ein Rückgängig.
33. Reihe zeitlich verschieben: mit „nachrücken“ rückt die getroffene Reihe dahinter, mit „tauschen“ tauschen beide
    ihre Termine; Lücken bleiben; ids, Themen, Material unverändert; Rückgängig stellt alles her.
34. Stunde auf einen freien Termin in einer Lücke: nur diese Stunde ändert ihr Datum.
35. Keine Aktion verschiebt etwas, das Lia nicht ausgelöst hat (Laden und Lesen ändern nie Daten).

---

## 11. Bauschritte (je ein Chat, je ein Commit, `./pruefen.sh` grün)

0. Jan: Antworten auf F1–F19, Freigabe dieses Plans.
1. **Hauptordner**: `agentkit.struktur` lesend (laden, prüfen, auflösen, `haengt_dran`), Tests 1–3, 6, 15, 17;
   `.gitignore` für `lia/instanz/fassungen/` (F15) und `lia/instanz/lerngruppen.toml` (F6); Feld `ort` in
   `agentkit.auftraege`; `commit-daten.sh` mit der Ausnahme-Zeile in CLAUDE.md (F4). **Erledigt 03.11.**
1b. **Erledigt 03.11.** **Hauptordner** (neu; Jans Antworten F20–F24 vom 03.11. liegen vor): `agentkit.termine` ohne Netz (Termine aus
   Stundenplan, Ferien, Feiertagen, Ausfällen, Zusatzterminen; Nachrücken; Halbjahreswechsel), Ferien-Datei je
   Bundesland (F20: Abrufskript einmal je Schuljahr, Datei im Repo als Rückfall und Prüfstand), `agentkit.struktur` liest `[schule]`, `klasse.zeitplan`, `ausfall`, `zusatz` und
   `stunde.termin`. Rechenregeln aus 2a.3 als reine Funktionen (auch Reihe zeitlich verschieben). Tests 26–31,
   33–35 (soweit Rechnung).
2. **Erledigt 03.11.** **Leser umstellen**, je in ihrem Chat: lia/unterricht (reihen.py über struktur), lia/examen (Reihe und
   Prüfungsstunde über die Marke „Prüfung“, `titel_in_reihen_toml` und `pruefungsstunde_in_reihe` raus, behebt den
   Absturz mit Stunden), lia/recherche (`id` statt „Straftheorien“, frühere Reihenfragen aus
   struktur statt Regex), lia/chat (kontext), shared/webapp (ordnung, logik). Test 22 je Ordner.
3. **Erledigt 03.11.** **Migration der Datei** (dieser Ordner, ein Commit wie von Hand, nach Jans Okay): `[[fach]]`, `[[klasse]]`,
   Schuljahr 2026/27 an den laufenden Klassen, `stand = "geplant"` und Titel ohne „(in Planung)“, Platzhalter-Reihe
   Kurs 11 wird Klasse, Helfen als Reihe (F10), Lerngruppe nach `lerngruppen.toml` (F6), `agenten = ["examen"]`
   raus, dafür die Prüfungsstunde als Stunde mit Marke (sobald Lia ihre Stunden der Reihe kennt; bis dahin läuft
   examen nicht, siehe Abschnitt 2). Vorher und nachher: echter Prompt
   von unterricht für eine Reihe vergleichen. **Wartet auf 1b**, damit die Datei nur einmal umgestellt wird; dabei
   `[schule] bundesland` und der Stundenplan der laufenden Klassen (von Lia zu erfragen).
   Stand: ohne Termine und ohne Prüfungsstunde (Jan 03.11.: Stundenplan kommt über die Maske, Lia kennt die
   Stunden noch nicht); `bisherige_reihen` bleibt, bis unterricht frühere Reihen aus der Herkunft liest.
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
| Echter Lauf von unterricht und examen greift die Reihe richtig auf | In der App: Reihe umbenennen und eine Stunde verschieben, dann ein Arbeitsblatt-Auftrag an dieser Stunde (echter unterricht-Lauf). Prüfen: Prompt nennt die Reihe als gewählt, die Stunde mit neuer Nummer und Thema. examen: in der App die
Prüfungsstunde verschieben, dann echte Runde 1 (am 25.10. kostete sie 2,47 USD). Prüfen: Kontext nennt die Reihe
und die Prüfungsstunde mit ihrer neuen Stelle. |
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
| 1 | „Du bekommst ab Februar noch einen Ethik-Kurs, eine 9, immer dienstags in der 3. Stunde. Trag ihn ein.“ | Klasse „9“ in Ethik mit Stundenplan, Termine bis Halbjahresende sichtbar | Fach Ethik bzw. „+ Klasse“ dort |
| 2 | „Die Reihe Freundschaft aus deiner 7 vom letzten Jahr willst du in der neuen 9 wieder machen, in den ersten sechs Terminen. Hol sie dorthin.“ | Kopie in Ethik 9 mit sechs Terminen, Original bleibt im Archiv | Archiv Klasse 7 · 2025/26 bzw. die Reihe Freundschaft |
| 3 | „In der Strafe-Reihe soll die Stunde zu von Liszt vor die Stunde zu Kant.“ | Reihenfolge geändert, Material bei seiner Stunde | Reihe Straftheorien |
| 4 | „Am nächsten Dienstag fällt der Unterricht in der 9 aus. Alles soll einen Termin später kommen.“ | Ausfall mit „Alles rückt nach“ | Klasse 9 bzw. der Termin |
| 5 | „Die Reihe zum nackten Wahnsinn ist vorbei. Räum sie aus deiner Übersicht, ohne dass etwas verloren geht.“ | Reihe archiviert (nicht gelöscht) | Reihe Der nackte Wahnsinn |
| 6 | „Du brauchst sie doch noch mal. Hol sie zurück, mit allem, was dazugehört.“ | wiederhergestellt; Lia findet ein Material darin wieder | Archiv bzw. Rückgängig |

**Gemessen je Aufgabe**: Erfolg (ohne Hilfe / mit Hilfe / nicht), erster Klick (richtig/falsch, wohin), Zeit bis
Erfolg in Sekunden, wörtliche Äußerungen. Bogen: `shared/webapp/data/ia/testbogen-struktur.csv`.

**Ziel**: 6 von 6 ohne Hilfe (Jans Vorgabe „alles ohne Hilfe“), erster Klick bei mindestens 5 von 6 richtig.
Zeiten werden erhoben, aber ohne Sollwert (einen belastbaren Vergleichswert habe ich nicht).

**Danach (5 Minuten)**: „Was war unklar?“, „Fehlt dir beim Anlegen ein Feld?“, „Fehlt dir beim Stundenplan
etwas?“, „Was erwartest du, wenn du eine Reihe in ein neues Jahr holst: auch die Materialien?“ (F7).

**Auswertung**: Was zweimal falsch angeklickt wird, wird geändert. Unter 6 von 6: ändern, zweiter Test.
