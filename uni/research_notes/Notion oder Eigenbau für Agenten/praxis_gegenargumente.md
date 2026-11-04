# Praxiserfahrungen und Gegenargumente: Notion als Agenten-Oberfläche, Eigenbau gegen Kaufen

Stand der Recherche: 04.11.2026. Nichts installiert, nur gelesen.

Belegstärke, durchgehend markiert:
- **[Doku]** = Notions eigene Doku oder Statusmeldung (Herstellerangabe zu eigenen Grenzen, hier eher glaubwürdig).
- **[Studie]** = Messung mit Methode.
- **[Einzelstimme]** = eine Person, ein Fall. Forenbeiträge sind Stimmungsbild, keine Häufigkeitsaussage.
- **[Interesse]** = Quelle verkauft etwas, das vom Argument profitiert.
- **[nur Suchauszug]** = Seite nicht vollständig gelesen, nur Zusammenfassung aus der Websuche. Vor wörtlicher Verwendung prüfen.

## Was berichten Nutzer und Entwickler, die eigene Agenten oder Automationen an Notion hängen?

### Takeaway
Die harten Grenzen sind gut belegt und für kurze bis mittlere Seiten beherrschbar; Notion selbst empfiehlt aber Seiten "under a few thousand blocks". Echte Erfahrungsberichte von Entwicklern fand ich nur wenige. Die stärkste belegte Schwäche für eigene Agenten sind wiederkehrende Störungen im Jahr 2026, darunter eine von acht Tagen mit verlangsamtem API-Schreiben.

### Cited Findings
**Grenzen (Doku)**
- [Doku] API-Grenze im Schnitt 3 Anfragen pro Sekunde je Integration, Überschreitung gibt HTTP 429; Notion kündigt an, die Grenzen anzupassen und eventuell je Tarif zu unterscheiden — [Notion Rate Limits](https://developers.notion.com/reference/rate-limits) [nur Suchauszug]
- [Doku] Schreibanfrage: höchstens 1000 Blockelemente, 500 KB gesamt, jedes Array höchstens 100 Elemente; `text.content` höchstens 2000 Zeichen, `equation.expression` höchstens 1000 Zeichen; Relation je Anfrage 100 Seiten — [Notion Request Limits](https://developers.notion.com/reference/request-limits)
- [Doku] Markdown-Endpunkt: Anlegen über 5000 Blöcke (inkl. verschachtelter) schlägt fehl; Lesen wird bei etwa 20.000 Blöcken abgeschnitten (`<unknown>`-Tags, `truncated: true`); Empfehlung "under a few thousand blocks"; ohne numerische Grenze scheitert Markdown, das "too large or too heavily formatted" ist; Teil-Edits können teilweise greifen, Fehlschläge stehen dann nur in `warnings` — [Notion: Working with markdown content](https://developers.notion.com/guides/data-apis/working-with-markdown-content)
- [Doku] Link-Vorschau, Breadcrumb und als "unsupported" gelieferte Blöcke kommen als `<unknown>` zurück. Zur Verlustfreiheit beim Hin und Zurück sagt die Doku nichts direkt — [Notion: Working with markdown content](https://developers.notion.com/guides/data-apis/working-with-markdown-content)
- [Doku] Notion MCP unterliegt denselben Grenzen; es wiederholt nur bei Wartezeit bis 2 Sekunden automatisch, sonst Fehler an den Agenten — [Notion MCP Rate Limits](https://developers.notion.com/guides/mcp/rate-limits)

**Blockmodell in der Praxis**
- [Interesse: Truto verkauft eine Unified API] Jeder Block mit Kindern braucht einen eigenen Aufruf; Rechenbeispiel: Seite mit 250 Blöcken, 50 Toggles und 150 Kindern braucht 103 Aufrufe, geschätzt über 34 Sekunden. Beim Schreiben höchstens zwei Ebenen Verschachtelung je Aufruf; Datei-URLs laufen nach einer Stunde ab; Webhooks enthalten keinen Inhalt — [Truto Blog](https://truto.one/blog/how-to-integrate-with-the-notion-api-architecture-guide-for-b2b-saas.md). Hinweis: Das ist ein Rechenbeispiel, keine Messung. Die Zwei-Ebenen-Grenze steht auf der Limits-Seite nicht als Zahl. Der Markdown-Endpunkt entschärft das Leseproblem vermutlich, der Artikel behandelt ihn nicht (mein Eindruck, nicht geprüft).

**Störungen (Status)**
- [Doku, über Statusspiegel] Vorfall 13.–21.10.2026 (8 Tage 1 Stunde 38 Minuten, als "Minor" eingestuft): Seiten anlegen und ändern über API und MCP langsamer, Custom-Agent-Läufe fehlgeschlagen oder verzögert, Echtzeit-Updates verzögert oder fehlend; behoben durch Infrastrukturumzug — [Pulsetic: Incident 148016](https://pulsetic.com/status/notion/incidents/148016/)
- [nur Suchauszug, Statusspiegel] Weitere Vorfälle 2026: rund fünftägige Störung bis 07./08.04. bei Datenbankabfragen von Notion AI, MCP und Custom Agents; 21.04. API lieferte etwa 21 Minuten unvollständige Ergebnisse; Oktober Custom Agents konnten Notion-Tools rund 3,7 Stunden nicht laden — [isdown Verlauf](https://isdown.app/status/notion/outage-history), [Pingoru Verlauf](https://pingoru.io/providers/notion/outage-history). Der Abruf der isdown-Seite scheiterte (403), die Details sind deshalb nicht selbst geprüft. "Unvollständige Ergebnisse" ohne Fehlermeldung wären für einen Agenten das schlimmere Muster, weil er es nicht bemerkt.

**Erfahrungen von Entwicklern**
- [Einzelstimme, Reddit r/AI_Agents, Mai 2026, unter einem Werbebeitrag] Claude Code plus Notion gehe gut für Doku und leichtes Projekt-Tracking, werde unzuverlässig bei zustandsbehafteten Aufgaben; Relationen über MCP würden mit bedingter Logik brüchig, ab der dritten oder vierten verschachtelten Formel gehe es bergab. Eine zweite Stimme fragt ungeklärt, was bei veralteten Daten passiert, wenn jemand während des Laufs in Notion schreibt — [Reddit-Snapshot](https://reddit.sentinel-team.org/posts/1t9ydqb/snapshots/2026-05-15T18%3A26%3A28.525889Z)
- [Einzelfall, Bugmeldung, Juni 2026] Cursor: Notion-Plugin aktiv, aber Agenten erreichen die Werkzeuge oft nicht; das Problem liegt laut Maintainer auf Cursor-Seite (Race Condition) — [Cursor Forum](https://forum.cursor.com/t/plugin-mcp-notion-enabled-in-settings-but-agent-cannot-access-tools-until-mcp-list-is-toggled/162637) [nur Suchauszug]
- [Interesse, Community-Projekte, nur Suchauszug] Die Werkzeugdefinitionen des Notion-MCP sollen rund 26.000 bis 38.000 Tokens belegen, bevor etwas passiert. Die Zahlen widersprechen sich und stammen von Anbietern schlankerer Alternativen — [notion-lite-mcp](https://lobehub.com/vi-VN/mcp/tomaszcarter-notion-lite-mcp), [PolicyLayer](https://policylayer.com/token-cost/io-github-ai-aviate-better-notion). Für Jans System (Python handelt, kein MCP nötig) vermutlich unerheblich.

### Inferences
- Für uni-Entwürfe wichtig: `text.content` mit 2000 Zeichen und 100er-Arrays zwingen zum Zerlegen in Blöcke; das ist lösbare, aber dauerhafte Fremdlogik. Das ist eine Ableitung aus den Limits, kein berichteter Fall.
- Eine Oberfläche, von der Agentenläufe abhängen, erbt Notions Störungen. Bei Python-Agenten sollte der eigene Speicher maßgeblich bleiben und Notion nur Spiegel sein, sonst stoppt ein Vorfall die Arbeit. Das ist meine Folgerung.
- Der Markdown-Endpunkt nimmt dem Blockmodell einen Teil seiner Schärfe. Ältere Klagen über Blöcke treffen also nicht mehr voll zu, und ältere Berichte sind entsprechend vorsichtig zu lesen.

### Gaps
- Keine Messungen zu Lese- und Schreibzeiten echter langer Seiten über die API gefunden. Lässt sich nur im eigenen Test klären.
- Keine belastbaren Berichte von Einzelpersonen, die über Monate einen eigenen Agenten mit Notion als Hauptoberfläche betreiben. Weder Erfolgs- noch Abbruchberichte. Das Fehlen beweist nichts.
- Verfügbarkeit in Prozent nicht ermittelt. Eine Vorfallliste sagt ohne Vergleichswert wenig über Notion gegenüber anderen Diensten.

## Wie gut ist Notion für lange wissenschaftliche Texte, Zitate, Fassungen, Offline, große Datenbanken, Handy? Warum wechseln Leute weg?

### Takeaway
Zitate sind die klarste Schwäche: Notion erzeugt selbst keine Literaturangaben, verbreitet ist deshalb Zotero plus Word für die Endfassung. Bei Offline ist Notion dank des inzwischen vorhandenen Offline-Modus (Startdatum nicht geprüft) besser als sein alter Ruf, aber mit Handarbeit und nur 50 Datenbankzeilen. Wechselgründe sind vor allem Tempo, Offline und das eigene Format, viele der lauten Berichte sind allerdings alt; es gibt auch Rückwechsler zu Notion.

### Cited Findings
**Zitate, Abschlussarbeit**
- [Einzelstimme, Praxisbericht] Thesis-Organisation in Notion mit Kapitelseiten und Dashboard, Zotero bleibe aber "crucial" für den Export der Literaturangaben am Ende — [Simone Smerilli](https://simonesmerilli.com/writing/thesis-notion) [nur Suchauszug]
- [Fachbeitrag, Bibliothek] Notero synchronisiert Zotero-Daten nach Notion, erzeugt dort aber ohne Zotero keine Zitate — [Litsis](https://litsis.classcaster.net/2025/01/23/notero-the-next-generation-in-citation-software/) [nur Suchauszug]
- [Bibliothek] Zotero im Word-Plugin schafft lange Arbeiten, im Test 400 Seiten mit über 1600 Zitaten, Literaturverzeichnis in etwa 15 Minuten — [UCL Library](https://library-help.ucl.ac.uk/faq/280601) [nur Suchauszug]
- [Berkeley D-Lab, Workshop] Notion plus Zotero wird als Verwaltung für Paper gelehrt, also für Literaturarbeit, nicht als Schreibwerkzeug — [D-Lab](https://dlab.berkeley.edu/node/1734) [nur Suchauszug]

**Fassungen**
- [Sekundärquellen, nur Suchauszug] Seitenverlauf 7 Tage (Free), 30 (Plus), 90 (Business), unbegrenzt nur Enterprise; Wiederherstellen nur für die ganze Seite, Versionen entstehen mit Verzögerung — [Sparxno](https://sparxno.com/blog/notion-page-version-history), [Thomas Frank](https://thomasjfrank.com/learn-notion/edit-history-trash/). Tarifdetails vor Verwendung bei Notion prüfen, Quellen nennen teils alte Tarife ([McGill-Leitfaden](https://classroom-physicists.physics.mcgill.ca/documentation/notes/quick-guide-to-using-notion/version-history)).

**Offline**
- [Doku] Für alle Nutzer in Desktop- und Mobil-App, aber je Seite und je Gerät einzuschalten, Unterseiten einzeln. Datenbanken laden nur die ersten 50 Zeilen, restliche Zeilen einzeln. Automatisches Laden nur Business und Enterprise. Einbettungen, Formulare, Knöpfe brauchen Netz. Text wird automatisch zusammengeführt, Nicht-Text teils von Hand — [Notion Help](https://www.notion.com/help/guides/working-offline-in-notion-everything-you-need-to-know)
- [nur Suchauszug, Quelle unklar, wirbt für Backups] Warnung, Konflikte könnten Arbeit still überschreiben; das widerspricht der Doku nicht direkt, ist aber nicht bestätigt — [NotionBackups](https://notionbackups-static.pages.dev/guides/notion-offline-mode)

**Große Datenbanken**
- [Doku] Höchstens 250.000 Zeilen, 500 Eigenschaften, 2,5 MB Eigenschaftsdaten je Seite, 1,5 MB Schema; ab 10.000 Verweisen auf dieselbe Seite wird die Gegenrichtung der Relation nicht mehr aktualisiert. Formeln und Rollups verlangsamen, viele eingebettete Datenbanken auf einer Seite auch — [Notion Help](https://www.notion.com/en-gb/help/optimize-database-load-times-and-performance) [nur Suchauszug]

**Tempo, Wechselgründe (Stimmungsbild, keine Häufigkeit)**
- [Einzelstimmen, Anytype-Forum, 2024, wohlgesinntes Publikum eines Konkurrenten] Notion "soooo slow"; "wie ein altes Notebook booten". Dieselbe Person ging trotzdem zurück zu Notion, weil dem Konkurrenten Teilaufgaben und Listenfunktionen fehlten — [Anytype Community](https://community.anytype.io/t/moving-back-to-notion-after-1-5-years-full-time-on-anytype/25309)
- [Einzelstimme, 2021] Weg wegen Ausfällen, Offline und eigenem Format; vermisst danach Datenbanken und Kanban — [QuadrantNine](https://buttondown.com/QuadrantNine/archive/so-long-notion/)
- [Einzelstimme, 2022] "slow, messy, and complicated", wechselt zu Obsidian, räumt "significant feature gap" ein und nutzt es nur für Notizen ohne Handy, Datenbanken oder Teilen — [dev.to](https://dev.to/painhardcore/leaving-notion-for-179j)
- [Sammlung Bewertungen, 2026, nur Suchauszug] Mit Einbettungen, großen Tabellen, langen Dokumenten wirke Notion langsam und überladen — [Capterra](https://www.capterra.com/p/186596/Notion/reviews/?rating=1)
- [Interesse: Falconer und Fabric sind Konkurrenten] Artikel zu Notion-Tempo und Abwanderung vorhanden, nicht als Beleg zu werten — [Falconer](https://falconer.com/guides/why-is-notion-slow/), [Fabric](https://developers.fabric.so/blog/why-people-are-leaving-notion)

### Inferences
- Viele bekannte Wechselberichte stammen von vor 2025 und nennen fehlendes Offline. Seit dem Offline-Modus ist dieses Argument schwächer und sollte nicht ohne Einschränkung übernommen werden.
- Für Jan folgt: Literaturarbeit und Entwürfe gehen in Notion, die Endfassung mit Zitaten führt fast zwangsläufig aus Notion heraus (Word oder LaTeX mit Zotero). Das stimmt mit den Quellen überein, ist für seinen Fall aber nicht getestet.
- Fassungen: Ein 7- oder 30-Tage-Verlauf ohne Teilwiederherstellung ersetzt nicht Git oder die eigene Fassungskette. Vorausgesetzt, die Tarifangaben stimmen.

### Gaps
- Keine aktuelle Quelle mit Messung, ab welcher Länge ein Notion-Dokument im Alltag zäh wird. Nur Eindrücke und die Blockempfehlung der Doku.
- Vorschlagsmodus und Kommentierung in Notion für Überarbeitungsrunden: Keine brauchbare Quelle gefunden. Fußnoten und Formeln im Langtext ebenfalls nicht geprüft.
- Handy: Nur vereinzelte Eindrücke, keine belastbaren Berichte. Android-Authority-Vergleich konnte nicht abgerufen werden (403).
- Reddit-Threads waren nur über Spiegel und ausschnittweise erreichbar; keine Aussage, was die Mehrheit denkt.

## Wie entscheiden erfahrene Leute Eigenbau gegen Standardsoftware bei persönlichen Werkzeugen?

### Takeaway
Es gibt viele Meinungen und kaum Daten. Weitgehend einig ist man sich: Bauen wurde billiger, die Frage ist die Pflege und ob jemand den Code versteht. Für persönliche Werkzeuge mit kleinem Schadensradius gilt Eigenbau als vertretbar. Das Gegenbeispiel: Mancher Eigenbauer stellt auch eigene Apps wieder ein.

### Cited Findings
- [Einzelstimme, Praktiker, Okt. 2025, baut selbst] "The question is no longer what do you want to build but rather what are you willing to maintain?" Eigene erste App aufgegeben, spätere Bücher-App funktioniert; Fehler aus August wurden im September von neueren Modellen gelöst. Meint, die meisten zahlen weiter für gepflegte Produkte — [Nat Eliason](https://www.nateliason.com/blog/the-past-and-future-of-vibe-coding)
- [Studie] METR 2025: erfahrene Entwickler mit KI 19 % langsamer (95-%-KI +2 bis +39 %). Folgestudie ab Aug. 2025: -18 % (KI -38 bis +9) bei den alten Teilnehmern, -4 % (KI -15 bis +9) bei neuen; METR selbst nennt das unzuverlässig, der wahre Effekt sei wohl größer, unter anderem weil viele nicht mehr ohne KI arbeiten wollten. Gemessen: Open-Source-Aufgaben erfahrener Entwickler, nicht persönliche Werkzeuge — [METR](https://metr.org/blog/2026-02-24-uplift-update/)
- [Einzelstimme, Feb. 2026] Hat Apps für Ausgaben, Training, Schlaf begonnen, hörte auf: "Why am I polishing a frontend?" Statt Apps nun SQLite, Markdown und Claude Code direkt ("three databases replaced three apps"). Musste für den Zugriff vom Handy dann doch einen eigenen Relay-Server bauen. Keine Angabe zur Langzeitpflege — [dev.to chadbyte](https://dev.to/chadbyte/i-stopped-building-apps-with-claude-code-now-claude-code-is-the-app-h1f)
- [Forschungsgruppe, Essay, Juni 2025] KI-Codegenerierung allein genüge nicht; neu generierte Apps bleiben Silos, nötig seien gemeinsame Daten, damit Werkzeuge kombinierbar bleiben (Vorbild Dateisystem). Teilweise Eigeninteresse: Die Gruppe baut eine solche Umgebung (Patchwork) — [Ink & Switch](https://www.inkandswitch.com/essay/malleable-software/)
- [Einzelstimme, nur Suchauszug] Stunden für die Pflege eines Klons können die Abo-Ersparnis übersteigen; bauen nur, wenn ein SaaS eine echte Anforderung nicht erfüllt — [Hayden Cassar](https://hayden-cassar.web.app/blog/vibe-maintenance) (beim Abruf 404, nicht geprüft)
- [Meinung, Interesse: Hashnode] Vibe Coding funktioniert, wenn Fehler billig sind und jemand das Ergebnis beurteilen kann — [Hashnode](https://hashnode.com/blog/state-of-vibe-coding-2026) [nur Suchauszug]
- [Meinung ohne Daten, eine Anekdote, endet mit Werbung] Wer nur promptet, trifft die Architekturentscheidungen nicht und kann schlechter pflegen — [dev.to Emily Wood](https://dev.to/emilywoodsnyc/everyone-is-vibe-coding-but-nobody-is-maintaining-the-vibe-code-4399)
- [Einzelstimme, Interesse unklar, nur Suchauszug] Gegenrichtung: 500 US-Dollar SaaS im Monat in einer Woche durch Skripte ersetzt, geschätzt 200 Dollar laufend. Kein Bericht nach längerer Zeit — [theopsdesk](https://theopsdesk.pages.dev/blog/rebuilt-500-month-saas-stack-with-scripts.html)

### Inferences
- Jans Sorge ("schlechter als Vorhandenes") trifft den belegten Kern nur teilweise: Berichte scheitern seltener an der Qualität am ersten Tag als an späterer Pflege und nachlassendem Interesse. Das ist ein Muster aus Einzelfällen, keine Messung.
- Für Jan als Einsteiger ist der Punkt "jemand muss das Ergebnis beurteilen können" die empfindliche Stelle. Sein System mit Tests, pruefen.sh und STATUS.md senkt das Risiko, beseitigt es aber nicht; er selbst kann Code nur eingeschränkt prüfen.
- Die Erfolgsberichte über SaaS-Ablösung sind meist kurz nach dem Bau geschrieben. Berichte nach einem Jahr fehlen, das begünstigt den Eigenbau in der Wahrnehmung (Überlebensverzerrung, meine Einschätzung).
- Auch "Kaufen" hat Pflege: Ein Fremddienst ändert API, Limits und Preise. Notion kündigt Limit-Änderungen selbst an. Der Vergleich ist also nicht Pflege gegen keine Pflege.

### Gaps
- Keine quantitativen Daten zu Pflegestunden persönlicher Werkzeuge gefunden. Die oft zitierte Angabe, Wartung mache 60–80 % der Lebenszykluskosten aus, ließ sich nicht bis zur Originalquelle prüfen und betrifft ohnehin Unternehmenssoftware.
- Hacker-News-Diskussionen konnten nicht direkt gelesen werden (der gefundene Spiegel gab 404). Der Bereich ist darum schwächer abgedeckt als gewünscht.
- Keine Untersuchung zu Nichtentwicklern, die KI-gebaute Werkzeuge länger als ein Jahr betreiben.

## Gibt es Muster: Standardwerkzeug als Arbeitsfläche plus kleine Fachanwendung daneben?

### Takeaway
Das Muster existiert in mehreren Formen, die Belege sind aber meist Produktseiten, keine Erfahrungsberichte über Ergebnisse. Am besten gedeckt ist die Aufteilung für Literaturarbeit: Zotero für Zitate, Notion für Organisation, Word für die Endfassung.

### Cited Findings
- [Mehrere Praxis- und Bibliotheksquellen, nur Suchauszug] Zotero plus Notion plus Word, verbunden über Notero — [Berkeley D-Lab](https://dlab.berkeley.edu/node/1734), [Jen Stumbles](https://medium.com/@jenstumbles/integrating-zotero-and-notion-67ef0ad6d8c5), [Simone Smerilli](https://simonesmerilli.com/writing/thesis-notion)
- [Interesse: Anbieter, nur Suchauszug] Notion als Vorderseite für ein eigenes Backend mit Zwei-Wege-Abgleich — [Xano](https://community.xano.com/announcements/post/introducing-our-new-notion-xano-actions-package-ckbVNOrZzv4Bwxp). Notion als Datenquelle für eigene Oberflächen, wobei Softr nur Datenbanken, keine Seiteninhalte abgleicht — [Simone Smerilli zu Softr](https://simonesmerilli.squarespace.com/business/notion-softr)
- [Interesse: Open-Source-Projekte oder Anbieter, nur Suchauszug] Eigene kleine Prüfoberflächen für Agenten: Placet (selbst gehostete Eingangsbox), AgentClick (lokaler Server, Prüfschritt im Browser, merkt sich Rückmeldungen). Dass diese Klasse entsteht, zeigt den Bedarf, sagt aber nichts über Bewährung — [Placet](https://dev.to/kesimo/placet-an-open-source-human-in-the-loop-platform-for-ai-agents-and-automation-workflows-4bf9), [AgentClick](https://github.com/agentlayer-io/AgentClick), [gotoHuman](https://docs.gotohuman.com/human-reviews.md)
- [Fachbeitrag, nur Suchauszug] Hinweis zum Entwurf: Ohne klare Anzeige lässt sich "in Prüfung" nicht von "hängt" unterscheiden, Prüfung solle nach Risiko gestaffelt werden — [Towards Data Science](https://towardsdatascience.com/human-in-the-loop-without-killing-throughput/)
- [Forschungsgruppe] Gemeinsame Daten statt Silos machen die Kombination tragfähig; ein Dateisystem-Äquivalent fehle noch — [Ink & Switch](https://www.inkandswitch.com/essay/malleable-software/)

### Inferences
- Das Mischmuster hat einen eigenen Preis, den Befürworter selten nennen: Zwei-Wege-Abgleich. Schon die Webhooks ohne Inhalt, 100er-Grenzen und veraltete Daten beim gleichzeitigen Bearbeiten (Reddit-Frage oben) zeigen, wo es reibt. Ein Abgleich in nur eine Richtung (eigener Speicher maßgeblich, Notion Spiegel oder Lesefläche) wäre weniger riskant. Das ist meine Einschätzung, nicht berichtet.
- Das Muster vermeidet nicht die Pflege, sondern fügt die Schnittstelle als dritte Sache hinzu.

### Gaps
- Keine Berichte über Ergebnisse nach Monaten für das Muster "Notion plus eigene Fachanwendung" bei Einzelpersonen gefunden.
- Keine Beispiele für Obsidian oder Google Docs als Prüffläche für Agenten gefunden.

## Umgekehrt: Wo sind kleine Eigenbauten nachweislich besser als Notion?

### Takeaway
"Nachweislich" im Sinn einer Messung habe ich nichts gefunden. Belegbar sind Fälle, in denen Notions dokumentierte Grenzen einem Eigenbau oder einer lokalen Lösung strukturell den Vorteil geben: Tempo auf langen Texten, lokaler Besitz der Daten, verlässlich strukturierte Prozesse, eigene Fassungen. Berichte dazu sind Einzelstimmen.

### Cited Findings
- [Einzelstimmen] Lokale Dateien: schneller, offline, offenes Format, unabhängig vom Anbieter, das sind die wiederkehrenden Motive der Wechsler zu lokalen Werkzeugen. Es sind Fertigprodukte, keine Eigenbauten, zeigen aber den Wert des Prinzips. Wer wechselt, verliert Datenbankfunktionen — [QuadrantNine](https://buttondown.com/QuadrantNine/archive/so-long-notion/), [dev.to](https://dev.to/painhardcore/leaving-notion-for-179j)
- [Einzelstimme] SQLite plus Markdown statt mehrerer Tracking-Apps; persönlich zufrieden, jedoch kein Langzeitbericht — [dev.to chadbyte](https://dev.to/chadbyte/i-stopped-building-apps-with-claude-code-now-claude-code-is-the-app-h1f)
- [Doku, als Gegenfolie] Grenzen, die ein eigener Speicher nicht hat: 2000 Zeichen je Textobjekt beim Schreiben, Empfehlung unter einigen tausend Blöcken, Abschneiden bei rund 20.000, Datenbanklimits, Verlauf nach Tarif. Offline bei Datenbanken nur 50 Zeilen automatisch — [Notion Request Limits](https://developers.notion.com/reference/request-limits), [Notion Markdown-Guide](https://developers.notion.com/guides/data-apis/working-with-markdown-content), [Notion Help Offline](https://www.notion.com/help/guides/working-offline-in-notion-everything-you-need-to-know)
- [Einzelstimme, Reddit] Zustandsbehaftete Abläufe mit bedingter Logik werden in Notion brüchig, also genau das, was Code besser kann — [Reddit-Snapshot](https://reddit.sentinel-team.org/posts/1t9ydqb/snapshots/2026-05-15T18%3A26%3A28.525889Z)
- [Gegenstimme] Rückwechsler zeigen die Kehrseite: Wer Listen, Teilaufgaben, Ansichten braucht, vermisst sie schnell, selbst in einem schnelleren Fertigprodukt mit aktiver Gemeinde — [Anytype Community](https://community.anytype.io/t/moving-back-to-notion-after-1-5-years-full-time-on-anytype/25309)

### Inferences
- Vermutlich hält ein Eigenbau dort, wo die Aufgabe eng, festgelegt und zustandsbehaftet ist (Warteschlangen, Fassungsketten, Prüfregeln), und verliert dort, wo Oberflächenbreite zählt (Datenbankansichten, Teilen, Handy, Kommentieren, gemeinsames Bearbeiten). Das ist eine Ableitung aus den Quellen, keine belegte Regel.
- Jans Vergleichsmaßstab sollte nicht "Notion gegen alles Selbstgebaute" sein. Die Berichte sprechen dafür, je Funktion zu entscheiden.

### Gaps
- Keine Vergleichsmessung (Zeit, Fehler, Zufriedenheit) Eigenbau gegen Notion gefunden, weder für Einzelpersonen noch für Teams.
- Die fairste Klärung wäre ein eigener Test mit einem echten langen uni-Dokument: lesen, schreiben, tabellieren, auf dem Handy öffnen. Das ist Empfehlung, kein Befund.
