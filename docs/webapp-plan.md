# Web-App für Lia und weitere Lehrerinnen – Entwurf

Stand 29.10.2026. Entwurf zur Entscheidung, noch nichts gebaut, nichts installiert, keine Domain gekauft.
Baut auf `docs/lia-architektur.md`, Abschnitt 6 (Variante C), auf. Prototyp: `docs/webapp-prototyp.html`
(Beispieldaten, keine echten Schülerdaten),
veröffentlicht als privates Artifact https://claude.ai/artifact/JMoaDZKoS59tpG35fbxZDs (Lia kann es erst öffnen,
wenn Jan es über „Teilen“ freigibt).

Grundlage, selbst nachgesehen: `lia/instanz/` (Warteschlangen, 3 Aufträge, 1 offene Freigabe),
`lia/instanz/zentrale/logs/zentrale.log` (nur Ereignisarten gezählt), `shared/telegram/portal.py` und
`portal_logik.py`, `shared/agentkit/` (auftraege, freigabe, meldungen, config, ereignis),
`lia/auswertung/data/lia/anonym.json` (nur Kennzahlen, keine Inhalte übernommen), `lia/auswertung/data/ergebnis/`
(Einordnung von 245 Aufgaben, laut `lia/auswertung/STATUS.md` noch nicht mit Lia abgeglichen),
STATUS-Dateien von unterricht, examen, recherche, theater, `/etc/caddy/Caddyfile` (nur gelesen), DNS.

---

## 0. Was sich gegenüber Variante C ändert

| Thema | Variante C (21.10.) | Jetzt: eigene Domain, mehrere Lehrerinnen |
|---|---|---|
| Erreichbarkeit | nur über Tailscale, keine öffentliche Adresse | öffentlich unter HTTPS, jede und jeder im Netz kann die Anmeldeseite sehen |
| Anmeldung | keine eigene, das private Netz war der Schutz | eigene Anmeldung ist jetzt die wichtigste Schutzschicht (Passkey) |
| Nutzerinnen | Lia | Lia, später weitere Lehrerinnen: Mandanten, Einladung, Trennung, Löschung |
| Rolle Jan | Partner, der hilft | Anbieter eines Dienstes für Dritte, rechtlich vermutlich Auftragsverarbeiter (Abschnitt 1) |
| Claude-Konto | Lias Läufe über das gemeinsame Konto | für Dritte vermutlich nur über die API (Abschnitt 1.2) |
| Telegram | Kanal für Dringendes und Freigaben | nur noch Hinweis mit Link, Inhalte und Freigaben in der Web-App |
| Angriffsfläche | klein | Internet: Anmeldung, Uploads, Sitzungen, Header, Updates. Bedrohungsmodell in 4.6 |

Unverändert gilt: Claude denkt, Python handelt. Die Web-App ist eine weitere Oberfläche wie die Zentrale. Sie legt
Aufträge an und trägt Entscheidungen ein, sie führt nichts nach außen aus und ruft Claude nicht selbst auf.

---

## 1. Rahmen klären (Punkte zur Prüfung, keine Rechtsberatung)

Was hier steht, ist mein Kenntnisstand und ausdrücklich keine Auskunft. Jeder Punkt endet mit: was Jan klären muss
und bei wem. Die Reihenfolge ist die, in der ich klären würde.

### 1.1 Schülerdaten auf einem privaten Server unter öffentlicher Domain

**Was heute schon ankommt.** Lias Material-Aufträge sind meist ohne Personen. Aber: Lia schickt Fotos und
Screenshots (in ihren claude.ai-Chats 174 von 281 Anhängen png/jpeg), dazu kommen Bewertungsbögen, eine
Notentabelle (Renderer-Art arbeitsmappe), Mitarbeit im Theaterkurs. `lia/theater/STATUS.md` hält fest, dass in Lias
Dateien Erwartungshorizonte mit Schülernamen und Zwischennoten lagen, die von Hand gelöscht wurden. Schülerdaten
kommen also auch ohne Absicht in das System.

Zu prüfen:
1. **Wer ist verantwortlich?** Nach meinem Verständnis ist bei dienstlicher Verarbeitung von Schülerdaten die Schule
   (bzw. das Land) Verantwortliche im Sinne der DSGVO, nicht die Lehrkraft persönlich. Dann bräuchte jede
   Verarbeitung auf einem privaten Dienst eine Grundlage, die die Schule trägt.
   *Klären: bei der oder dem schulischen Datenschutzbeauftragten von Lias Schule.*
2. **Private Geräte und Dienste in Berlin.** Das Berliner Schulgesetz (Teil zum Datenschutz) und die
   Schuldatenverordnung regeln, nach meinem Kenntnisstand, dass Lehrkräfte personenbezogene Daten nur mit
   Genehmigung der Schulleitung auf privaten Geräten verarbeiten dürfen, mit Auflagen. Ob ein gemieteter Server
   eines Dritten (Jan) darunter fällt oder gar nicht zulässig ist, weiß ich nicht.
   *Klären: Schulleitung und schulische Datenschutzbeauftragte; bei Unklarheit die Senatsverwaltung für Bildung
   (Referat Datenschutz in Schulen) bzw. deren veröffentlichte Hinweise.*
3. **Übermittlung an Anthropic (USA).** Jeder claude-Lauf schickt den Auftrag samt Anhängen an Anthropic. Mit
   Schülerdaten ist das eine Übermittlung in ein Drittland. Zu prüfen: Grundlage (z. B. EU-US Data Privacy Framework
   oder Standardvertragsklauseln im Vertrag mit Anthropic), und ob die Schule das überhaupt zulässt.
   *Klären: schulische Datenschutzbeauftragte; Vertragslage bei Anthropic (Commercial Terms, Data Processing
   Addendum), siehe 1.2.*
4. **Datenschutz-Folgenabschätzung (Art. 35 DSGVO).** Daten von Minderjährigen, neue Technik (KI), möglicherweise
   Bewertungen: das klingt nach den Fällen, für die eine Folgenabschätzung verlangt wird. Wer sie schreiben müsste,
   hängt an Punkt 1 (vermutlich die Schule, mit Zuarbeit von Jan).
   *Klären: schulische Datenschutzbeauftragte; Muss-Listen der Aufsicht (Berliner Beauftragte für Datenschutz und
   Informationsfreiheit) ansehen.*
5. **Jan als Anbieter für weitere Lehrerinnen.** Sobald eine zweite Lehrerin (andere Schule, keine Partnerin) den
   Dienst nutzt, verarbeitet Jan in deren Auftrag. Dann braucht es nach meinem Verständnis einen
   Auftragsverarbeitungsvertrag (Art. 28 DSGVO), technische und organisatorische Maßnahmen schriftlich, ein
   Verzeichnis der Verarbeitungen, Unterauftragsverarbeiter benannt (Contabo als Hoster, Anthropic, Telegram,
   später Push-Dienste von Apple/Google), Meldewege bei Pannen (72 Stunden), Löschkonzept. Mit wem der Vertrag
   geschlossen wird, hängt wieder an Punkt 1 (Schule, nicht Lehrerin).
   *Klären: schulische Datenschutzbeauftragte der jeweiligen Schule; für Jans Pflichten als Anbieter eine
   Beratung (z. B. Anwältin für IT-Recht oder Datenschutzberatung), bevor die zweite Lehrerin startet.*
6. **Contabo.** Prüfen, ob Contabo einen AVV anbietet und wo der Server steht (der Vertrag weiß es).
   *Klären: Jan im Kundenkonto von Contabo.*
7. **Pflichten einer öffentlichen Seite.** Impressum (Digitale-Dienste-Gesetz, wenn der Dienst geschäftsmäßig
   angeboten wird), Datenschutzerklärung, und ob ein Sitzungs-Cookie ohne Einwilligung zulässig ist (technisch
   notwendig, vermutlich ja). Wird Geld genommen: Gewerbe, Steuer.
   *Klären: Jan, bei Geld mit Steuerberatung.*

**Folgerung für den Bau, unabhängig vom Ergebnis:** Die Web-App startet für Aufgaben ohne Schülerdaten (Material,
Fachfragen, Theaterfassung, Recherche). Sie zeigt beim Hochladen und im Textfeld einen festen Hinweis „Bitte keine
Namen von Schülerinnen und Schülern“. Bewertung, Noten und Mitarbeit bleiben gesperrt, bis Punkt 1–4 geklärt sind
(so schon in `lia-architektur.md`, Abschnitt 0). Ein Löschkonzept wird vor der zweiten Lehrerin gebaut.

### 1.2 Darf Jans Claude-Login andere bedienen?

Heute laufen die Agenten beider Instanzen über ein Abo-Konto (`[konto] quelle = "token"`, eigenes
Agenten-Konto, `CLAUDE_CODE_OAUTH_TOKEN`, siehe STATUS.md, „Verbrauch“).

Zu prüfen:
- Nach meinem Kenntnisstand sind die Abos (Pro, Max) Verbraucherkonten für die eigene Nutzung. Anthropic hat für
  das Agent SDK geschrieben, dass Dritte ihren Produkten keinen claude.ai-Login und keine Abo-Kontingente anbieten
  dürfen, außer mit Genehmigung. Ob das den Haushalt (Lia) schon betrifft, ist unklar. Für Lehrerinnen außerhalb
  des Haushalts halte ich ein Abo für nicht tragfähig.
- Die API (Konto bei der Claude Console, Commercial Terms) ist für Dienste an Dritte gedacht, mit Budgetgrenze und
  einem Data Processing Addendum. `claude -p` läuft auch mit `ANTHROPIC_API_KEY`. In `claude_lauf` käme eine
  Kontoquelle „api“ je Instanz dazu (heute gilt `[konto]` für alle Instanzen gemeinsam, `config.py`, KONTINGENT_DIR).
- Größenordnung aus `shared/verbrauch/laeufe.jsonl` bzw. den STATUS-Dateien: ein Arbeitsblatt etwa 0,61 USD, die
  Theater-Runde vom 29.10. 6,84 USD. Pro Lehrerin wären also eher 10 bis 60 USD im
  Monat zu erwarten. Das ist eine Schätzung aus wenigen Läufen.
- Datenaufbewahrung bei Anthropic für API-Läufe und ob Training ausgeschlossen ist: in den Commercial Terms nachlesen.

*Klären: Jan liest die aktuellen Consumer Terms, Commercial Terms und die Hinweise zum Agent SDK. Bei Zweifel eine
Anfrage an den Anthropic-Support („Darf ich mit einem Abo-Konto Agenten für meine Partnerin bzw. für andere
Lehrkräfte betreiben?“). Entscheidung Jan: ab welcher Nutzerin die API Pflicht wird. Mein Vorschlag: für jede
Lehrerin außer Lia von Anfang an, für Lia mit dem Umzug auf die Domain.*

### 1.3 Wie kommen Ports 80/443 zustande, ohne sudo?

Geprüft (29.10.): Caddy 2.6.2 läuft schon als Systemdienst und hört auf 80 und 443 (`ss -ltn`), eingerichtet am
27.10. für `kcal.meldro.de` (`docs/kcalbot-https.md`). Die Caddyfile enthält nur den kcal-Block.
`/home/agent` hat Rechte 750, der User `caddy` kommt also nicht an einen Unix-Socket im Repo.
`lia.meldro.de` löst heute auf 185.181.104.242 auf, das ist der Platzhalter von INWX (Wildcard `*`), nicht unser Server.

| Weg | Was nötig ist | Wer sieht Inhalte im Klartext | Bewertung |
|---|---|---|---|
| **A: Caddy, zweiter Block (empfohlen)** | Jan als root: einen Block für die neue Adresse anhängen, `systemctl reload caddy`. App hört auf `127.0.0.1:<port>` | nur unser Server | Caddy ist da, Zertifikat holt Caddy selbst. Den kcal-Block nicht ändern. Ein `reload` ist unterbrechungsfrei, berührt aber denselben Dienst, über den kcalbot erreichbar ist: darum Jans Entscheidung |
| B: Cloudflare Tunnel als User-Dienst | `cloudflared` als Programmdatei, User-Unit, Konto bei Cloudflare, Domain bei Cloudflare | Cloudflare (TLS endet dort) | ohne root machbar, aber ein weiterer US-Dienst sieht alle Inhalte. Für Schülerdaten ungünstig |
| C: Tailscale Funnel | `tailscaled` im Userspace-Modus ohne root, Tailscale-Konto | nur unser Server (TLS endet bei uns) | ohne root denkbar, Adresse ist `*.ts.net`, keine eigene Domain, Abhängigkeit von Tailscale. Ob der Userspace-Modus Funnel kann, vorher testen |
| D: hoher Port und Weiterleitung | iptables-Regel | – | braucht root, also kein Vorteil gegenüber A |

Vorschlag zu A, für Jan als root, **erst nach den Klärungen 1.1 und 1.2**:

```
lia.meldro.de {
	encode zstd gzip
	reverse_proxy 127.0.0.1:8791
	request_body {
		max_size 60MB
	}
}
```

Kein `log`-Eintrag (wie beim kcal-Block), damit keine Adressen mit Inhalten im Zugriffslog landen. Sicherheits-Header
setzt die App selbst (4.6), damit sie mit getestet werden. Auf `127.0.0.1` kann jeder lokale Benutzer (z. B. `bot`)
die App erreichen. Das ist hinnehmbar, weil die App ohne Anmeldung nichts zeigt. Wer das nicht will: Caddy in die
Gruppe `agent` aufnehmen und einen Socket mit Gruppenrecht nutzen (ebenfalls root).

**Name.** `lia.meldro.de` kostet nichts (nur ein A- und ein AAAA-Eintrag bei INWX, wie bei kcal). Für weitere
Lehrerinnen ist ein neutraler Name besser als Jans private Domain (z. B. eine eigene Domain für den Dienst, rund
1 Euro im Monat). Gekauft wird nur nach Jans Okay. Der Name ist zugleich die Kennung der Passkeys: Ein späterer
Wechsel der Domain heißt, alle Passkeys neu einzurichten. Darum den Namen vor der ersten Lehrerin festlegen.

*Klären: Jan entscheidet Weg A/B/C, Name und ob er den Caddy-Block selbst einträgt. Vorher kurz prüfen, dass der
kcal-Block danach noch antwortet (`curl` aus kcalbot-https.md, Schritt 4).*

### 1.4 Übersicht: was Jan bei wem klärt

| # | Frage | bei wem | blockiert |
|---|---|---|---|
| K1 | Darf Lia dienstliche Inhalte überhaupt über einen privaten Server und Anthropic verarbeiten, mit oder ohne Schülerdaten? | Schulleitung, schulische Datenschutzbeauftragte | Domain (Bauschritt 8) |
| K2 | Folgenabschätzung nötig, wer schreibt sie? | schulische Datenschutzbeauftragte | Schülerdaten, zweite Lehrerin |
| K3 | Abo oder API für Lia und für andere | Anthropic-Bedingungen, ggf. Support | Domain, zweite Lehrerin |
| K4 | AVV, TOM, Verzeichnis, Impressum, Datenschutzerklärung als Anbieter | Datenschutz- oder IT-Rechtsberatung | zweite Lehrerin |
| K5 | AVV mit Contabo, Standort | Contabo-Kundenkonto | Domain |
| K6 | Weg zu 443 (A/B/C), Name, Kauf | Jan | Domain |

---

## 2. Rohmaterial: was Lia tut und wo Telegram hakt

### 2.1 Was die Daten zeigen

**claude.ai (26.07.–23.10., 27 Chats von Lia, anonymisiert):** 1.143 Nachrichten von Lia. Median 64 Zeichen, 90 %
unter 240 Zeichen: sie schreibt kurz und bessert nach. Im Median 10 Runden je Chat, bis zu 308. 131 Nachrichten mit
Anhang, davon die meisten Fotos oder Screenshots (png 114, jpeg 60), dann docx 59, pdf 40. Lia arbeitet vor allem
nachmittags und abends (15–21 Uhr: 658 von 1.143 Nachrichten) und am Donnerstag und Freitag. Ob am Handy oder am
Rechner, zeigt der Export nicht.

**Einordnung der Aufgaben (Sonnet, 245 Aufgaben, ungeprüft):** material 80, planung 47, fachklaerung 37,
eigener_text 28, auswahl 24, bewertung 13, verwaltung 9. Bei Material im Schnitt 1,85 Korrekturen je Aufgabe, am
häufigsten Form, fachlicher Fehler, Umfang, Niveau, „missverstanden“. Viele „missverstanden“ gehen auf fehlenden
Kontext der laufenden Reihe zurück.

**Telegram-Zentrale (21.–29.10., Log ohne Inhalte):** 13 Starts des Dienstes. Von Lia: 4-mal „Neues Material“
getippt, 1 Datei geschickt, 3-mal etwas ohne Text (Datei, Sprachnachricht o. Ä., das Log unterscheidet es nicht),
1 Auftrag bestätigt. Dieser eine Auftrag ist fehlgeschlagen („Kontingent aufgebraucht“). Die zwei übrigen Aufträge
in ihrer Instanz hat Jan bzw. ein Agent angelegt (Fallsuche, Theaterfassung), um Ergebnisse zuzustellen. Kein
einziges Feedback von Lia kam über Telegram. In den STATUS-Dateien steht dagegen oft „über Jan“: Feedback gesprochen,
Bewertungsbogen als docx, Regeln „von Lia freigegeben, über Jan“, eine 259-MB-PDF über Jan.

**Freigaben:** `lia/instanz/freigabe/offen/` enthält einen Entwurf (examen, „Lia setzt selbst ein“) seit 25.10.
`portal.py` kennt keine Freigaben. Lia kann ihn nicht sehen und nicht abschließen.

Ehrlich gesagt: Die Daten belegen, dass Lia Telegram kaum nutzt. Sie belegen nicht, dass sie eine Web-App nutzen
würde. Das muss die Beobachtung (Abschnitt 3) und der Prototyp-Test (Abschnitt 5) zeigen, bevor viel gebaut wird.

### 2.2 Die fünf häufigsten Aufgaben

Nach Zahl der Aufgaben und Runden in den Chats, ergänzt um das, was die Agenten heute liefern:

| # | Aufgabe | Beleg | Agent heute | Was die Web-App können muss |
|---|---|---|---|---|
| 1 | **Material erstellen und nachbessern** (Arbeitsblatt-Text, Bausteine, Argumentieren, Fallbeispiel) | 80 Aufgaben, 395 Runden, 1,85 Korrekturen je Aufgabe | unterricht | Wunsch kurz eingeben, Vorlage als Foto, Ergebnis als Vorschau lesen, gezielt ändern lassen, Versionen |
| 2 | **Stunde oder Reihe planen mit Kontext** | 47 Aufgaben, 239 Runden | keiner (bleibt Lias Gespräch), Kontext über `reihen.toml` von Jan | Reihen pflegen (Reihenfrage, Klasse, Positionen), damit jeder Auftrag den Kontext hat |
| 3 | **Fachfrage klären mit Beleg** (Philosophie, Quellen) | 37 Aufgaben, wenig Korrekturen | unterricht „Frage stellen“ (im Aufbau), recherche | Frage stellen, Antwort mit Belegen lesen, nachfragen |
| 4 | **Eigenen Text prüfen lassen** (UB-Entwurf) | 28 Aufgaben | noch keiner | Datei hochladen, Hinweise je Abschnitt lesen |
| 5 | **Auswählen** (Positionen, Fälle, Stücke) | 24 Aufgaben, 4,5 Runden im Median | recherche (Fallsuche), theater | Vorschläge vergleichen, auswählen, Begründung |

Dazu zwei Aufgaben, die keine Inhalte sind, aber an denen es heute hängt: **Feedback geben** und **Entwürfe
freigeben oder abschließen**.

### 2.3 Ablauf eines Auftrags vom Wunsch bis zur Freigabe, mit den Stellen, an denen Telegram hakt

| Schritt | Heute (Telegram) | hakt | Beleg |
|---|---|---|---|
| 1. Wunsch entsteht | im Gespräch, oft mündlich an Jan | Lia spricht lieber, als zu tippen. Sprachnachrichten versteht die Zentrale nicht | 3 Nachrichten ohne Text im Log; examen „gesprochen, über Jan“ |
| 2. Formulieren | Freitext nach „Neues Material“ | Kontext fehlt (Klasse, Reihe, schon behandelte Positionen), Lia schreibt kurz | 43 Korrekturen „missverstanden“; Median 64 Zeichen |
| 3. Dateien anhängen | Foto oder Datei, Album-Logik, erst danach Text | Reihenfolge Datei-dann-Text ist versteckte Mechanik; 20-MB-Grenze | 259-MB-PDF über Jan; Hinweis „Dateien warten“ |
| 4. Abschicken | Bestätigen-Ansicht | ein Tipp mehr, sonst ok | 1 von 1 bestätigt |
| 5. Warten | „Meine Anfragen“ zeigt in Arbeit/fertig | kein Fortschritt, keine Dauer, Kontingent-Fehler kommt erst am Ende | einziger Auftrag nach 44 s fehlgeschlagen |
| 6. Ergebnis ansehen | Text plus docx als Telegram-Datei | docx am Handy öffnen ist mühsam, lange Dossiers (19 Seiten) am Handy kaum zu prüfen | Theater: vier docx auf einmal |
| 7. Feedback | Knöpfe Passt / Zu lang / Falscher Fokus / Feedback schreiben, Antwort auf Ergebnis | Lia nutzt es nicht, Feedback kommt mündlich über Jan; Bezug auf eine Stelle im Dokument geht nicht | 0 Feedback-Aufträge aus Lias Instanz; 1,85 Korrekturen je Material in claude.ai |
| 8. Freigabe | in Lias Zentrale nicht vorhanden | Entwurf bleibt liegen | examen-0c44bf offen seit 25.10. |

---

## 3. Leitfaden für die Beobachtung

Ziel: einmal sehen, wie Lia eine echte Aufgabe erledigt, bevor Ansichten gebaut werden. Dauer 30–45 Minuten.
Jan schreibt mit, hilft nicht und erklärt nichts, solange Lia nicht festhängt.

**Vorher**
- Einen Termin nehmen, an dem Lia ohnehin etwas vorbereitet (Donnerstag oder Freitag Nachmittag passt zu den Daten).
- Lia fragen, ob Jan zusehen und mitschreiben darf. Keine Aufnahme von Bildschirm oder Ton, wenn Schülerdaten zu
  sehen sein könnten.
- Bogen bereitlegen: Uhrzeit, Schritt, Werkzeug (Handy, Laptop, Papier, Telegram, claude.ai, IServ, Word), was sie
  sagt, wo sie zögert.

**Während**
1. „Zeig mir, was du gerade für nächste Woche vorbereitest. Mach es so, wie du es sonst auch machst.“
2. Mitschreiben, nicht deuten: Welches Gerät? Wo fängt sie an? Welche Dateien braucht sie, woher (Fotos, IServ,
   Drive, Mail)? Wann wechselt sie das Werkzeug? Wann tippt sie, wann diktiert sie?
3. Bei Pausen nur: „Was denkst du gerade?“ Keine Suggestivfragen („Wäre ein Knopf praktisch?“).
4. Wenn ein Ergebnis kommt: Wie prüft sie es? Liest sie alles, druckt sie, ändert sie in Word, schreibt sie zurück?
5. Merken, an welcher Stelle sie sagt „das mache ich später“ und was dann liegen bleibt.

**Danach (5 Minuten)**
- „Was war heute nervig?“ „Was hättest du gern jemandem abgegeben?“ „Wann hättest du lieber gesprochen als
  geschrieben?“
- „Wo hast du das zuletzt mit Telegram versucht, und was ist passiert?“
- Notizen am selben Tag in drei Listen ordnen: tut sie oft, hakt, will sie selbst behalten. Nur ohne Namen von
  Schülerinnen und Schülern ablegen (`lia/auswertung/data/`, nicht im Repo).

**Drei Fragen für weitere Lehrerinnen** (kurz, am Telefon oder per Nachricht):
1. „Welche Vorbereitung hat dich letzte Woche am meisten Zeit gekostet, und was davon war Routine?“
2. „Womit arbeitest du dafür heute (Gerät, Programme, Schulplattform), und was darfst du dort laut deiner Schule
   nicht verwenden?“
3. „Würdest du einem Assistenten Entwürfe überlassen, die du vor dem Einsatz prüfst? Wofür nie?“

---

## 4. Entwurf

### 4.1 Informationsarchitektur

> Ersetzt am 30.10.2026 (Desktop zuerst, Baum Fach → Klasse → Reihe → Stunde): `docs/webapp-aufbau.md`.
> 4.1 und 4.2 bleiben als Herkunft stehen.

Fünf Bereiche, unten als Leiste (Handy) bzw. links (Rechner). Alles andere ist eine Ebene darunter.

```
Heute            was wartet auf mich, was ist in Arbeit, großer Knopf „Neuer Auftrag“
  ├─ Ergebnis    Kern, Seiten als Vorschau, Anmerkungen, Fassungen, Dateien (PDF, Word), Feedback
  │    └─ Seite  eine Seite groß, Stelle antippen, Anmerkung dazu schreiben
  └─ Entwurf     ganzer Text, Freigeben / Ändern / Ablehnen / „Setze ich selbst ein“
Neu              Auftrag: Art, Text (Diktieren), Reihe, Dateien und Fotos, „Das beachte ich“
Anfragen         alle Aufträge, Filter nach Stand und Art, Suche im Auftragstext
Unterricht       Meine Reihen: Klasse, Reihenfrage, behandelte Positionen (heute reihen.toml)
                 Meine Vorlagen: Gestaltung, Musterblätter, Materialsammlung
Ich              Gelernte Regeln (lesen, Stopp vorschlagen), Benachrichtigungen, Geräte und Passkeys, Abmelden
(Verwaltung)     nur Jan: Mandanten, Einladungen, Zustand. Kein Zugriff auf Inhalte anderer Mandanten
```

Begriffe aus Lias Sicht: „Auftrag“, „Ergebnis“, „Entwurf“, „Reihe“. Keine Agentennamen, keine IDs (wie in der
Zentrale, `portal_logik.ergebnis_nachricht`). Der zuständige Agent ergibt sich aus der Art, wie heute aus `ARTEN`.

### 4.2 Ansichten fürs Handy zuerst

Gestaltung für einen Daumen, 360–430 px breit, große Ziele (mindestens 44 px), keine Tabellen, keine Hover-Effekte.
Ein Bildschirm, eine Aufgabe. Was im Prototyp zu sehen ist:

1. **Heute.** Oben „Wartet auf dich“ (Ergebnisse ungelesen, Entwürfe offen), darunter „In Arbeit“ mit grober Dauer
   und Hinweis bei Kontingent („startet um 14:00“, statt am Ende zu scheitern), unten „Neuer Auftrag“.
2. **Neuer Auftrag.** Art als Chips (Material, Frage, Text prüfen, Recherche, Theater). Ein Textfeld mit dem Hinweis
   auf die Diktiertaste der Handy-Tastatur (keine eigene Spracherkennung, das hält Ton von Lias Server fern). Reihe
   als Auswahl aus „Reihen“, vorbelegt mit der zuletzt genutzten. „Foto oder Datei“ öffnet Kamera oder Dateien
   (Vorlage nur für diesen Auftrag). Fester Hinweis „Bitte keine Namen von Schülerinnen und Schülern“.
   Darunter, eingeklappt, **„Das beachte ich“**: Reihe mit Reihenfrage und Behandeltem, aktive Gestaltung,
   Musterblätter für diese Art, Zahl der gelernten Regeln, Materialsammlung. Die Liste baut Python aus denselben
   Dateien, die der Agent im Prompt bekommt, sie ist also keine Behauptung des Modells. Abschicken ohne zweiten
   Bestätigen-Schritt, stattdessen 10 Sekunden „Zurücknehmen“.
3. **Ergebnis (Dokumentenausgabe).** Oben der Kern in drei Punkten (wie `daten.kern`) und „Bitte prüfen“. Darunter
   die **Seiten als Vorschaubilder**, zwei nebeneinander. Die Bilder baut der Renderer schon (`bauen(...,
   vorschau=True)`), die App zeigt sie nur. Je Datei zwei Knöpfe: „PDF zum Drucken“ und „Word“ bzw. „PowerPoint“
   zum Weiterbearbeiten, immer für die gerade gewählte Fassung. Fassungen als Chips („Fassung 1“, „Fassung 2“),
   die alte bleibt erhalten. Dossiers und Antworten ohne Seitenvorschau zeigen Kern, Belege und die PDF.
4. **Seite groß, Anmerkung an einer Stelle.** Tippen auf ein Vorschaubild öffnet die Seite groß, mit Blättern.
   Lia tippt auf eine Stelle (Überschrift, Falltext, Aufgabe, Begleittext) und schreibt dazu eine Anmerkung, oder
   zur ganzen Seite. Anmerkungen sammeln sich beim Ergebnis; „Neue Fassung mit 2 Anmerkungen“ legt **eine**
   Nachbesserung an (CLAUDE.md: höchstens eine Nachbesserung je Ergebnis automatisch). Technik: Der Renderer kennt
   die Blöcke der Beschreibung (JSON), also kann er je Block die Lage auf der Seite mitliefern. Die Anmerkung geht
   mit Blocknummer und Text in den Nachbesserungs-Auftrag. Bedarf an `shared/renderer`: Blocklage je Seite in der
   Vorschau ausgeben. Bis dahin reicht „Anmerkung zur Seite“.
5. **Feedback mit Geltungsbereich und Rückmeldung.** Knöpfe Passt, Zu lang, Falscher Fokus, Ändern … wie in
   Telegram. Neu: Bei „Zu lang“ fragt die App „Nur bei diesem oder ab jetzt immer?“ (gibt es in Telegram schon), bei
   „Ändern“ ein Schalter „Auch bei künftigen Aufträgen so machen“. Danach steht im Ergebnis ein Kasten
   **„Das mache ich aus deinem Feedback“**: „Ich mache eine neue Fassung“ und gegebenenfalls „Ich merke mir ab jetzt:
   …“ mit „Nicht merken“, dazu „Jan bekommt eine kurze Zusammenfassung und kann es stoppen“ (Vetorecht, CLAUDE.md).
   Der Kasten zeigt, was `agentkit.feedback` wirklich entschieden hat (nachbesserung, regel, notiz, Vorschlag an Jan),
   nicht was die Oberfläche vermutet. Im Prototyp ist das nachgestellt.
6. **Entwurf.** Ganzer Text ohne Kürzung, Empfänger und Details als Zeilen (wie in Jans Zentrale). Knöpfe:
   Freigeben, Ändern, Ablehnen, und bei Typ „entwurf“ (Lia setzt selbst ein) „Erledigt, setze ich selbst ein“.
   Freigeben mit 10 Sekunden „Rückgängig“ (Vorschlag aus STATUS.md Punkt 23, Feld „nicht vor“). Kein „Alle
   freigeben“.
7. **Anfragen.** Liste wie „Meine Anfragen“, aber vollständig, mit Filter und Suche.
8. **Unterricht, Meine Reihen.** Je Reihe: Fach, Klasse, Reihenfrage, behandelte Positionen, Stand. Änderungen schreibt die App in
   eine Datei der Instanz, die die Agenten bei jedem Lauf lesen (heute `lia/unterricht/reihen.toml`, von Jan
   gepflegt). Das ist der größte inhaltliche Hebel aus der Auswertung.
9. **Unterricht, Meine Vorlagen.** Drei Fächer, jedes mit „Hochladen“, Stand („wird gelesen“, „wird genutzt“,
   „pausiert“), „Ansehen“ (Probeseite) und „Nicht mehr nutzen“. Gelöscht wird nichts automatisch.
   - *Gestaltung:* eine Word- bzw. PowerPoint-Datei (auch .dotx/.potx, der Renderer wandelt sie mit
     `vorlage_umwandeln()` um) für Kopfzeile, Logo, Ränder. Gilt ab dem nächsten Auftrag, alte Ergebnisse bleiben.
     Heute: `<agent>/data/vorlagen/` und `profil.toml`, von Jan gepflegt. Eine Schulvorlage hat Lia am 25.10.
     zurückgestellt, das Fach ist also anfangs fast leer.
   - *Musterblätter:* gelungene Beispiele je Materialtyp (Fallbeispiel, Arbeitsblatt-Text, Argumentieren, Aufgaben,
     Theater). Der Agent schreibt beim Einlesen „was daran gut ist“, Lia kann es korrigieren. Gelernte Regel vom
     24.10.: Musterblätter sind Anregung, keine Schablone. Heute: die Beispielsammlung in `lia/unterricht`
     (beispiele.py). „Passt“ unter einem Ergebnis kann es als Musterblatt vorschlagen.
   - *Materialsammlung:* alte Blätter, Texte, Folien zum Nachschlagen. Heute `lia/unterricht/data/wissen/eingang/`
     (211 Dateien) mit Textfassung und `katalog.md`. Ergebnisse nennen die genutzte Datei.
   Ablage je Mandant in der Instanz (`<instanz>/vorlagen/gestaltung|muster|sammlung/` plus eine `vorlagen.toml` mit
   Stand und Typ), die Agenten lesen sie bei jedem Lauf. Uploads wie in 4.4 geprüft, Hinweis „keine Namen“.
   Das betrifft nur Lias Dateien, keine Regeln und keinen Code, braucht also keine Freigabe.
10. **Ich.** Gelernte Regeln (aus `regeln.md` und den STATUS-Dateien, nur lesen, „Diese Regel stoppen“ wird ein
   Vorschlag an Jan, CLAUDE.md: Löschen nie automatisch), Benachrichtigungen, Passkeys.

PWA: Manifest und Symbol, damit Lia die Seite auf den Home-Bildschirm legen kann. Ein Service Worker nur für die
Offline-Seite und später Web-Push, er speichert keine Inhalte zwischen.

### 4.3 Anmeldung

| | Passkey (WebAuthn) | Magic Link per Mail |
|---|---|---|
| Sicherheit | phishing-fest, kein Geheimnis auf dem Server | so sicher wie das Postfach, Link kann weitergeleitet werden |
| Bedienung | Face ID / Fingerabdruck, ein Tipp | Mail öffnen, Link tippen, oft im falschen Browser |
| Aufwand | Paket `webauthn`, Domain fest (siehe 1.3) | SMTP-Konto für den Dienst, Zustellbarkeit, das ist Handeln nach außen |
| Ohne Domain | geht auf `localhost` (sicherer Kontext), also im ersten Schritt testbar | geht |

**Vorschlag: Passkey als einziger Weg, keine Passwörter.** Einrichten und Wiederherstellen über einen einmaligen
Einladungslink (15 Minuten gültig, einmal nutzbar), den Jan erzeugt und über die bestehende Telegram-Zentrale der
Lehrerin schickt oder persönlich zeigt. Mindestens zwei Passkeys je Konto empfehlen (Handy und Laptop, oder
iCloud-Schlüsselbund). Kein Magic Link, damit der Dienst keine Mails verschicken muss.

Sitzung: zufällige ID (`secrets.token_urlsafe(32)`), in SQLite nur als Hash gespeichert, Cookie `__Host-sitzung`
mit `Secure`, `HttpOnly`, `SameSite=Strict`, 30 Tage gleitend, Abmelden aller Geräte unter „Ich“.
Formulare zusätzlich mit CSRF-Token und Prüfung des `Origin`-Headers.

### 4.4 Mandanten über Instanzen

Ein Mandant ist eine Instanz wie heute `lia/instanz/` (`AGENTKIT_INSTANZ`). Die Inhalte bleiben in deren
Warteschlangen und Agent-Ordnern. SQLite (`shared/webapp/data/konten.sqlite`, chmod 600) hält nur:
`konto` (id, name, instanz, rolle lehrerin/admin), `passkey` (konto, credential_id, public_key, zaehler),
`sitzung` (hash, konto, ablauf), `einladung` (hash, konto, ablauf, benutzt), `push_abo` (später).

Technisch: `agentkit.config` setzt die Instanz heute einmal je Prozess (`SHARED_DIR` beim Import). Die Funktionen
von `auftraege`, `freigabe` und `meldungen` nehmen aber schon `basis=` und `agenten_dir=`. Die Web-App bekommt eine
kleine Klasse `Mandant` (Instanzpfad, Agenten-Ordner, Person, erlaubte Arten), die jede Ansicht aus der Sitzung holt
und an agentkit weiterreicht. Keine Ansicht greift ohne `Mandant` auf Dateien zu.

| Schicht | Trennung |
|---|---|
| Anfrage | Sitzung → Konto → Mandant. IDs aus der Adresse werden nur innerhalb dieses Mandanten gesucht, sonst 404 |
| Dateien | Downloads nur aus `ergebnis_dateien` eines Auftrags dieses Mandanten, Pfad aufgelöst und gegen den Agent-Ordner geprüft (wie `anhaenge_pruefen`) |
| Uploads | in `<instanz>/webapp/eingang/` je Mandant, dann wie heute über `neuer_auftrag(..., dateien=)` verschoben |
| Prozesse | ein Web-Prozess für alle, die Agenten weiter je Instanz (`<instanz>-<agent>.service`) |
| Linux | alle Mandanten unter User `agent`. Das trennt gegen Programmierfehler, nicht gegen einen Fehler im Web-Prozess. Echte Trennung je Lehrerin gäbe es nur mit eigenem Linux-User und eigenem Web-Prozess (root nötig) |

Offen gesagt: Für Lia allein reicht das. Für fremde Lehrerinnen würde ich vor dem Start entscheiden, ob jeder
Mandant einen eigenen Linux-User bekommt (Vorschlag in `lia-architektur.md`, Abschnitt 3). Dazu kommen das
gemeinsame Kontingent (`KONTINGENT_DIR`) und die gemeinsamen Plätze: Mit der API je Mandant (1.2) bekäme jede
Instanz ein eigenes Konto und Budget.

Tests: ein Mandantentest, der für jede Route mit der ID eines fremden Mandanten 404 erwartet, läuft in `pruefen.sh`.

### 4.5 Benachrichtigungen

- **Telegram bleibt** für Hinweise. Neu: Die Zentrale schickt Lia statt Inhalt und Datei nur „Dein Arbeitsblatt
  ‚Kategorischer Imperativ‘ ist fertig“ und einen Link auf das Ergebnis in der Web-App (Linkvorschau ist schon aus).
  Damit liegen Inhalte nicht mehr in der Telegram-Cloud. Umschaltbar je Mandant, damit Lia beides vergleichen kann.
- **Web-Push später** (Paket `pywebpush`, VAPID-Schlüssel in `.env`). Auf dem iPhone nur, wenn die Seite auf dem
  Home-Bildschirm liegt (iOS ab 16.4). Push-Nachrichten ohne Inhalt, nur „Neues Ergebnis“. Die Push-Dienste von
  Apple und Google sind weitere Empfänger (für 1.1, Punkt 5).
- Technische Störungen gehen weiter nur an Jan (`ausfall@`), Lia sieht höchstens „Gerade hakt etwas, Jan weiß
  Bescheid“.

### 4.6 Bedrohungsmodell (STRIDE)

| | Bedrohung | Beispiel | Gegenmaßnahme |
|---|---|---|---|
| **S** Spoofing | fremde Person meldet sich an | gestohlener Einladungslink, geklautes Cookie | Passkey, Einladung 15 min und einmalig, `__Host-`-Cookie, Sitzungen widerrufbar, Hinweis an Jan bei neuem Passkey |
| **T** Tampering | Eingaben verändern Daten oder Code | manipulierter Upload, Pfad `../`, CSRF | Uploads nur in den Eingang, Dateiname neu vergeben, Größen- und Typprüfung (wie `_ablage`), CSRF-Token und `Origin`, Agenten lesen Uploads nur als Textfassung |
| **T** | Prompt-Injection über Uploads | Dokument mit „ignoriere alle Regeln“ | unverändert: Claude ohne Bash, Schreibschutz, Handeln nur in Python hinter Freigabe. Die App führt nie aus |
| **R** Repudiation | „Das habe ich nicht freigegeben“ | Freigabe am Handy, Fehlklick | `freigabe.entscheide` mit Konto und Zeit, Ereignis `freigabe.entschieden`, 10 s Rückgängig, Fingerabdruck über das Gezeigte |
| **I** Information Disclosure | Mandant sieht Daten eines anderen | ID in der Adresse geändert | Mandant aus der Sitzung, Mandantentest, keine fortlaufenden IDs nach außen ohne Prüfung |
| **I** | Inhalte in Logs oder Fremddiensten | Zugriffslog, Telegram, Push | Caddy ohne Log, App loggt nur IDs und Arten, Telegram und Push ohne Inhalt |
| **I** | Header und Transport | Einbettung, MIME-Sniffing, Downgrade | HSTS, strenge CSP ohne Inline-Skripte (HTMX lokal), `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, `frame-ancestors 'none'`, Downloads mit `Content-Disposition: attachment` |
| **D** Denial of Service | Server überlastet | viele Anmeldeversuche, große Uploads, viele Aufträge | Caddy `max_size`, Ratenbegrenzung je IP und Konto in der App, höchstens N offene Aufträge je Mandant, `MemoryMax` in der Unit, Kontingent-Stufen wie heute |
| **D** | Kosten | Aufträge laufen das Budget leer | Budget je Mandant (API), Hinweis vor teuren Arten, Kostenschätzung wie in der Feedback-Regel (1 USD) |
| **E** Elevation of Privilege | Lehrerin wird Admin, Web-Prozess wird zum Angreifer | Fehler in der Rollenprüfung, Lücke in einem Paket | Admin-Routen getrennt und nur mit Rolle admin, Web-Prozess ohne Schreibrecht auf Code (`ProtectHome=read-only` plus `ReadWritePaths` auf Instanzen und `data/`), Pakete fest in `requirements.txt`, Updates nach `pruefen.sh` |

### 4.7 Technik

- **FastAPI** mit **Jinja2**-Vorlagen, **HTMX** für Teil-Aktualisierungen (eine JS-Datei, lokal ausgeliefert, kein
  Build-Schritt), eigenes kleines CSS. **Uvicorn** auf `127.0.0.1:8791` (bzw. Unix-Socket im ersten Schritt).
- Ordner `shared/webapp/` mit eigener `.venv` und `STATUS.md`: `app.py` (Routen, dünn), `logik.py` (reine Logik:
  Ansichtsdaten aus Aufträgen, Mandantenprüfung, Rechte, getestet), `konten.py` (SQLite), `vorlagen/` (Jinja),
  `statisch/` (CSS, htmx.min.js, Manifest, Service Worker), `tests/`.
- Inhalte nur in den Warteschlangen. Die App nutzt `auftraege.neuer_auftrag`, `freigabe.entscheide`,
  `auftraege.erledigte` usw. mit `basis=` des Mandanten. Wiederverwendet aus `shared/telegram/`: die Arten
  (`portal_logik.ARTEN`), die Feedback-Vorlagen (`vorlagen.py`) und die Textvorlagen für Ergebnisse. Was beide
  Oberflächen brauchen, wandert nach agentkit, damit Telegram und Web nicht auseinanderlaufen.
- Ereignisse über `agentkit.ereignis` (6), ohne Inhalte.
- Dienst `webapp.service` (User-Unit) mit `OnFailure=ausfall@%n.service`, `MemoryMax=300M`, Startgrenze.

**Neue Pakete zur Freigabe** (in `shared/webapp/requirements.txt`, nur in dessen `.venv`):

| Paket | wofür | Bemerkung |
|---|---|---|
| fastapi | Routen, Formulare | zieht starlette, pydantic |
| uvicorn | Server | ohne `[standard]`, damit es klein bleibt |
| jinja2 | Vorlagen | |
| python-multipart | Formulare und Uploads | von FastAPI für Formulare verlangt |
| webauthn | Passkeys | zieht cryptography, cbor2, pyOpenSSL |
| htmx (JS-Datei, Version fest) | Teil-Aktualisierung | keine Paketverwaltung, Datei mit Prüfsumme ins Repo |
| später: pywebpush | Web-Push | erst Bauschritt 10 |
| Prüfung: playwright (Python) | Oberflächentests, axe | lädt Chromium (~150 MB). Geprüft 29.10.: das vorhandene Headless-Chromium im Cache startet nicht, `libatk-1.0.so.0` fehlt. Also braucht `playwright install-deps` root (Jan) |
| Prüfung: axe-core (JS-Datei) | Barrierefreiheit | wird in Playwright eingespielt, kein npm |

Nicht nötig: Datenbank-Server, ORM (sqlite3 aus der Standardbibliothek), Sitzungs-Bibliothek, Node-Build.

---

## 5. Prototyp und Testplan

**Prototyp:** `docs/webapp-prototyp.html`, eine einzelne Datei ohne Netzzugriff außer Schriften, klickbar: Heute,
Neuer Auftrag mit „Das beachte ich“, Ergebnis mit Seitenvorschau, Seite groß mit Anmerkung an einer Stelle, Feedback
mit Geltungsbereich und Rückmeldung, Fassung 2, Entwurf mit „Setze ich selbst ein“, Anfragen, Unterricht (Reihen und
Vorlagen), Ich, Testleitung (A1–A7, stoppt die Zeit selbst).
Alle Inhalte sind erfunden (Themen aus Lias Fächern, keine Personen). Lia kann ihn am Handy öffnen (Link über
Telegram oder als Datei).

**Testplan.** Ein Termin von 40 Minuten, Lia am eigenen Handy, Jan schreibt mit. Zum Vergleich A1–A5
auch in Telegram (Lias Zentrale, an einem Testauftrag), in wechselnder Reihenfolge (erst Web, beim nächsten Mal
erst Telegram), damit nicht immer die zweite Runde vom Üben profitiert.

Anleitung an Lia: „Bitte sag laut, was du denkst und was du suchst. Es gibt kein Falsch, getestet wird die Seite,
nicht du.“

| # | Aufgabe (so vorlesen) | Erfolg, wenn | Zeit messen ab–bis |
|---|---|---|---|
| A1 | „Bestell ein Arbeitsblatt zum kategorischen Imperativ für Klasse 10, 45 Minuten, für deine Reihe Pflicht und Neigung, und häng ein Foto deines alten Arbeitsblatts an.“ | Auftrag abgeschickt mit Reihe und Foto | erster Tipp bis „ist unterwegs“ |
| A2 | „Dein Fallbeispiel ist fertig. Es ist dir zu lang. Sorg dafür, dass du eine kürzere Fassung bekommst.“ | Ändern mit Text oder „Zu lang“ abgeschickt | Öffnen des Ergebnisses bis Bestätigung |
| A3 | „Da liegt ein Entwurf für eine Umfrage, die du selbst auf Papier austeilst. Schließ ihn ab.“ | „Setze ich selbst ein“ getippt, nicht „Freigeben“ | Start bis Bestätigung |
| A4 | „In deiner Reihe zur Strafe ist jetzt auch Hegel behandelt. Trag das ein.“ | Position in der Reihe ergänzt | Start bis gespeichert |
| A5 | „Finde das Ergebnis zur Fallsuche Strafe von letzter Woche und lade das Dokument herunter.“ | Datei geöffnet | Start bis Datei |
| A6 | „Im Fallbeispiel ist die Aufgabe für die 8 zu offen. Merk genau dort an, dass sie zum Ankreuzen sein soll, und fordere eine neue Fassung an.“ | Anmerkung an der Aufgabe, neue Fassung angefordert | Öffnen des Ergebnisses bis Anforderung |
| A7 | „Leg ein gelungenes Fallbeispiel als Musterblatt ab.“ | Datei unter Musterblätter mit Typ Fallbeispiel | Start bis hochgeladen |

A6 und A7 gibt es nur in der Web-App, sie gehen nicht in den Vergleich mit Telegram.

Messen je Aufgabe: Erfolg (ja / mit Hilfe / nein), Dauer in Sekunden, Fehltipps (Zurück, falsche Ansicht),
Schwierigkeit nach jeder Aufgabe 1–7 („Wie leicht war das?“), wörtliche Zitate bei Zögern.
Abbruchregel: nach 3 Minuten oder auf Lias Wunsch, dann „mit Hilfe“ notieren.

Ziel für den Prototyp: A1–A7 ohne Hilfe, jede unter 90 Sekunden, Schwierigkeit im Schnitt mindestens 5.
Ergebnis kommt als Tabelle in `shared/webapp/STATUS.md` (ohne Zitate mit Schülerbezug), Änderungen am Entwurf
danach. Mit einer Person ist das kein statistischer Nachweis, sondern das Aufdecken von Hürden.

---

## 6. Nachweis: woran wir erkennen, dass es stimmt

| Frage | Messung | Ziel | wann |
|---|---|---|---|
| Ist die Web-App für Lia leichter als Telegram? | Testplan 5 in beiden Oberflächen: Erfolg, Dauer, Schwierigkeit | Web: 5 von 5 ohne Hilfe, im Schnitt schneller als Telegram | Prototyp, dann Bauschritt 7 |
| Nutzt Lia sie wirklich? | `agentkit.ereignis` ohne Inhalte: `web.anmeldung`, `web.auftrag` (Art), `web.ergebnis_gesehen`, `web.feedback` (Art), `web.freigabe` (Entscheidung). Auswertung: aktive Tage, Aufträge je Woche, Anteil Ergebnisse mit Feedback, Zeit von Ergebnis bis Ansicht | nach zwei Wochen: an mindestens 5 Tagen genutzt, mindestens 5 eigene Aufträge, Feedback zu mindestens der Hälfte der Ergebnisse, kein Entwurf älter als 48 h | 14 Tage nach Bauschritt 7 |
| Geht weniger über Jan? | Strichliste Jan: Aufträge oder Feedback, die Lia ihm mündlich gibt | sinkt deutlich gegenüber den zwei Wochen davor | gleichzeitig |
| Kann sich eine zweite Lehrerin selbst einrichten? | Jan erzeugt nur die Einladung und schaut zu. Gemessen: Zeit bis erster Auftrag, Zahl der Rückfragen | unter 15 Minuten, ohne Hilfe | Bauschritt 11 |
| Ist der Transport sicher? | SSL Labs (ssllabs.com/ssltest) | A oder besser | nach Bauschritt 8 |
| Sind die Header richtig? | Mozilla HTTP Observatory | A oder besser | nach Bauschritt 8 |
| Gibt es offensichtliche Lücken? | OWASP ZAP Baseline (passiv) gegen die öffentliche Adresse. ZAP braucht Java oder Docker, beides ist auf dem Server nicht da: von Jans Mac aus laufen lassen | keine Funde „High“ oder „Medium“, Rest begründet | nach Bauschritt 8, danach monatlich |
| Ist sie barrierearm? | axe-core in Playwright auf allen Ansichten, 375 px und 1280 px breit | keine Verstöße „serious“ oder „critical“ | jeder Lauf von `pruefen.sh` |
| Bleibt sie funktionsfähig? | Playwright-Durchlauf der fünf Testaufgaben gegen eine Test-Instanz mit Beispieldaten, Mandantentest, Unit-Tests von `logik.py` | grün in `pruefen.sh` | jeder Commit |

Playwright in `pruefen.sh`: eigener Eintrag `shared/webapp|.venv/bin/python|tests`, die Browser-Tests laufen nur,
wenn Chromium installiert ist, sonst erscheint „übersprungen“ deutlich in der Ausgabe statt still grün.

---

## 7. Bauplan

Jeder Schritt endet mit `./pruefen.sh` ALLES GRÜN und einem eigenen Commit (`git commit -- shared/webapp ...`).
Vor jedem mit (Okay) markierten Schritt wartet der Chat auf Jans Okay.

| # | Schritt | Ergebnis | Okay nötig |
|---|---|---|---|
| 0 | Klärungen K1–K6 (Abschnitt 1.4) anstoßen, Beobachtung (3) und Prototyp-Test (5) mit Lia | Antworten bzw. Termine, Testtabelle | – (Jan) |
| 1 | Gerüst `shared/webapp/`: `.venv`, Pakete, `app.py` mit „Heute“ nur lesend für eine Test-Instanz, Unix-Socket wie der Leitstand, Zugriff per SSH-Tunnel, `logik.py` mit Tests, Eintrag in `pruefen.sh` | Seite im Tunnel, Tests grün | (Okay) Pakete |
| 2 | Konten: SQLite, Einladung, Passkey auf `localhost`, Sitzung, Abmelden, Mandant aus Sitzung, Mandantentest | Anmeldung im Tunnel | – |
| 3 | Neuer Auftrag mit Upload, Ergebnis-Ansicht mit Vorschau und Download, Anfragen | Auftrag hin und zurück in der Test-Instanz | – |
| 4 | Feedback mit Geltungsbereich und Rückmeldung aus `agentkit.feedback`, Fassungen, Seitenvorschau groß, Anmerkung zur Seite; Anmerkung zur Stelle, sobald der Renderer die Blocklage liefert | Nachbesserung kommt als Fassung 2 | – |
| 5 | Entwürfe: Freigeben / Ändern / Ablehnen / „Setze ich selbst ein“, 10 s Rückgängig. Bedarf an agentkit.freigabe (Typ entwurf abschließen, überholte Entwürfe sperren, Punkt 23 der STATUS.md) | Lias offener Entwurf lässt sich abschließen | – |
| 6 | Reihen, Vorlagen (drei Fächer, Ablage in der Instanz, Agenten lesen sie) und Regeln (lesen, Stopp als Vorschlag), „Das beachte ich“, Ereignisse `web.*`, Playwright und axe | Messung läuft | (Okay) Chromium und Systembibliotheken |
| 7 | Lia testet intern: im Tunnel auf Jans Laptop oder über Tailscale (Variante C). Testplan 5 mit der echten App, zwei Wochen Nutzung messen | Vergleichstabelle, Entscheidung weiterbauen ja/nein | (Okay) Dienst `webapp.service` |
| 8 | Nach K1, K3, K5, K6: DNS-Eintrag, Caddy-Block (Jan als root), App auf `127.0.0.1:8791`, Header, SSL Labs, Observatory, ZAP | öffentliche Adresse mit Nachweisen | (Okay) Domain, Caddy, Port |
| 9 | Telegram-Hinweis mit Link statt Inhalt in Lias Zentrale (umschaltbar) | Inhalte nicht mehr in Telegram | – |
| 10 | Web-Push (optional) | Hinweis ohne Telegram | (Okay) pywebpush |
| 11 | Zweite Lehrerin: nach K2 und K4, Instanz-Vorlage, eigenes API-Konto, Löschkonzept, Verwaltungsseite für Jan, Selbsteinrichtung messen | zweite Instanz läuft | (Okay) je Lehrerin |

Was ich bewusst nicht vorschlage: Chat-Oberfläche im Browser, Bearbeiten von Dokumenten im Browser, eigene
Spracherkennung, Zugang für Schülerinnen und Schüler, Bewertung und Noten vor den Klärungen.
