# Offizielle Wege, eigene Agenten an Notion anzubinden (Stand 4./5.11.2026)

Hinweise zur Belegqualität:
- Kennzeichnung: [P] = Primärquelle von Notion, [B] = Blog oder Presse Dritter, [D] = Status-Tracker Dritter. Notions eigener Blog zählt als [P], ist aber Werbetext.
- Die Seiten wurden über ein Abruf-Werkzeug gelesen, das sie zusammenfasst. Zitate sind kurz, Zahlen sollten vor einer harten Entscheidung auf der Originalseite nachgelesen werden.
- Nichts wurde getestet, kein Konto angelegt. Alle Aussagen zur Bedienung stammen aus Dokumentation, nicht aus eigener Anschauung.

## REST-API und Webhooks: Was geht, welche Grenzen?

### Takeaway
Die REST-API ist breit und aktiv gepflegt: Seiten, Blöcke, Markdown, Data Sources, Views, Kommentare, Datei-Upload bis 5 GiB (bezahlt) und Webhooks. Die Grenzen sind für eine Pipeline beherrschbar, aber Webhooks brauchen einen öffentlichen HTTPS-Endpunkt, liefern nur Signale ohne Inhalt, und neue Kommentar-Threads an markierten Textstellen kann die API nicht anlegen.

### Cited Findings
**Inhalte**
- Markdown-Inhalts-API seit 26.02.2026, Markdown-GET auch für interne Integrationen seit 02.03.2026, Views-API mit acht Endpunkten seit 19.03.2026, Tab-Blöcke seit 25.03.2026 — [P: Changelog](https://developers.notion.com/page/changelog)
- Grenzen je Anfrage: 100 Elemente pro Block-Array, 1000 Blockelemente und 500 KB pro Payload, `text.content` 2000 Zeichen, `equation.expression` 1000 Zeichen, URL 2000 Zeichen, Multi-Select, Relation und People je 100 — [P: Request limits](https://developers.notion.com/reference/request-limits)
- Rate Limits: 600 Anfragen pro Minute pro Verbindung bei Business und Enterprise, 180 bei allen anderen; Data-Source-Abfragen zusätzlich etwa 3 pro Sekunde; dazu ein geteiltes Limit pro Workspace je nach Tarif, `Retry-After` dort teils über eine Minute — [P: Request limits](https://developers.notion.com/reference/request-limits)
- Markdown-Endpunkt: Lesen ist bei etwa 20.000 Blöcken abgeschnitten (`truncated: true`), Schreiben scheitert ab mehr als 5.000 erzeugten Blöcken mit `validation_error`. `unknown_block_ids` unterscheidet nicht zwischen abgeschnitten und nicht lesbar — [P: Working with markdown content](https://developers.notion.com/guides/data-apis/working-with-markdown-content)
- Maximal 10.000 Ergebnisse pro Abfrage seit 20.04.2026 — [P: Changelog](https://developers.notion.com/page/changelog)
- Nicht unterstützte Blöcke kommen als `type: "unsupported"` mit informativem `block_type` (z. B. `form`, `button`, `drive`), ohne Inhalt. Inhalte synchronisierter Blöcke lassen sich per API nicht aktualisieren — [P: Block](https://developers.notion.com/reference/block)

**Datenbanken und Data Sources**
- Seit 2025-09-03 kann eine Datenbank mehrere Data Sources haben; das Schema liegt je Data Source, die meisten Operationen nutzen `data_source_id` — [P: Upgrade-Guide 2025-09-03](https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03.md)
- Datenbanken können seit 02.09.2026 per `database_type` als `tasks`, `projects` oder `skills` angelegt werden — [P: Changelog](https://developers.notion.com/page/changelog)

**Kommentare**
- Möglich: Kommentar auf Seite (`parent.page_id`), an einen ganzen Block (`parent.block_id`), Antwort in bestehender Diskussion (`discussion_id`), eigene Kommentare ändern und löschen, Erwähnungen per Markdown. Kommentare erscheinen mit Name und Icon der Verbindung — [P: Working with comments](https://developers.notion.com/guides/data-apis/working-with-comments.md)
- Nicht möglich: neue Diskussion an einer markierten Textstelle starten; gelöste Kommentare abrufen; fremde Kommentare löschen. Überschriften, Listen, Code und Tabellen werden in Kommentaren nicht als Struktur dargestellt — [P: Working with comments](https://developers.notion.com/guides/data-apis/working-with-comments.md)
- Kommentar-Update und -Löschen sind seit 17.04.2026 allgemein verfügbar; Markdown-Body seit 07.04.2026 — [P: Changelog](https://developers.notion.com/page/changelog)

**Datei-Upload**
- Free 5 MiB, bezahlt bis 5 GiB pro Datei. Einfach-Upload bis 20 MB, darüber Mehrteil-Upload. DOCX, PPTX, PDF und HTML sind unterstützt — [P: Working with files and media](https://developers.notion.com/guides/data-apis/working-with-files-and-media.md)
- Beim Abruf eines HTML-Blocks ist die `embed.url` temporär und signiert, also nicht zwischenspeichern — [P: Block](https://developers.notion.com/reference/block)

**Webhooks**
- Der Endpunkt muss öffentlich und per SSL erreichbar sein, localhost geht nicht. Die URL ist nach der Verifizierung nicht mehr änderbar (löschen und neu anlegen). Für Kommentar-Ereignisse braucht die Verbindung `comment read`. Jedes Ereignis trägt eine kryptografische Signatur — [P: Webhooks](https://developers.notion.com/reference/webhooks)
- Ereignisfamilien: Page, Database, Data Source, Comment, File Upload, View, jeweils mit eigener Referenzseite — [P: llms.txt](https://developers.notion.com/llms.txt)
- Zustellung: Ziel laut Text „at-most-once", bis zu 8 Wiederholungen mit Backoff, letzter Versuch nach etwa 24 Stunden. Reihenfolge nicht garantiert. Ziel: innerhalb von 5 Minuten, die meisten innerhalb einer Minute. Ereignisse enthalten keinen Inhalt, nur IDs und Metadaten, also danach per API nachlesen — [P: Event types & delivery](https://developers.notion.com/reference/webhooks-events-delivery.md)
- Widerspruch in der Quelle: „at-most-once" passt nicht zu Wiederholungen nach fehlender Bestätigung. Empfänger sollte Duplikate wie Verluste abfangen — eigene Bewertung derselben [P-Seite](https://developers.notion.com/reference/webhooks-events-delivery.md)

### Inferences
- Für den Renderer genügt der vorhandene Weg: docx, pptx und PDF als Datei-Block hochladen. Lange Texte müssen wegen 2000 Zeichen pro Rich-Text-Objekt und 100 Elementen pro Array gestückelt werden, oder über den Markdown-Endpunkt laufen.
- Webhooks setzen einen neuen öffentlichen HTTPS-Endpunkt voraus. Das wäre auf dem Server neu, der Leitstand läuft bisher nur über Unix-Socket und SSH-Tunnel. Alternative wäre zeitgesteuertes Abfragen mit Limit 180/min im Plus-Tarif.

### Gaps
- Tarifgrenzen für Webhooks und Höhe des Workspace-Rate-Limits: Die Doku nennt keine Zahlen.
- Dauer des Aggregationsfensters: nur „brief time window".
- Ablaufzeit ungebundener Uploads und signierter URLs: nicht gelesen.
- Ob `comment.created` eine @-Erwähnung der Verbindung erkennbar macht: Die Zustell-Doku sagt nichts dazu. Vermutlich muss der Kommentar nachgelesen und im Text gesucht werden (nicht belegt).

## External Agents API, Workers, Database Sync, MCP, Custom Agents: Was ist das, wie reif, was kostet es, kann ein eigener Agent wie ein Notion-Agent erscheinen?

### Takeaway
Genau das Gewünschte, also ein selbst gebauter Agent als sichtbarer Teilnehmer in Notion, heißt External Agents API und ist laut Notions eigener Hilfe noch private Beta mit Warteliste, ohne öffentliche Doku. Allgemein verfügbar ist seit 02.11.2026 nur die Gegenrichtung (Agent APIs: eigene App ruft Notion-Agenten). Heute selbst nutzbar ist also: Bot-Verbindung mit Kommentaren und Webhooks, oder ein Custom Agent auf Notions Modellen und Credits, der den eigenen Server als Werkzeug aufruft. Beides ist nur eine Annäherung.

### Cited Findings
**External Agents API**
- Versprechen: „Bring your favorite agents into Notion with the External Agents API, even the ones you built yourself", Status dort Alpha, Warteliste — [P: Release 13.05.2026](https://www.notion.com/releases/2026-05-13)
- Beschreibung: „native workspace participants", erscheinen „in your agent list", „chat directly in Notion", „assign them work, and track progress", private Beta per Warteliste. @-Erwähnung und Kommentare nennt der Beitrag nicht, ebenso keine Kosten — [P: Blog Developer Platform](https://www.notion.com/blog/introducing-developer-platform)
- Status „private beta", Warteliste, keine Tarifangabe, keine Datumsangabe auf der Seite — [P: Hilfe Developer Platform](https://www.notion.com/help/what-is-the-notion-developer-platform)
- Produktseite: „one you've built", „Bring your in-house agents into Notion", Abschnitt mit „Alpha" und „Join the waitlist" — [P: Build with Notion](https://www.notion.com/product/dev)
- Im Doku-Index von developers.notion.com gibt es keinen Eintrag „external agent" — [P: llms.txt](https://developers.notion.com/llms.txt). Das heißt: keine öffentliche technische Doku gefunden. Auch der Changelog hat dazu keinen Eintrag — [P: Changelog](https://developers.notion.com/page/changelog)
- Widerspruch: Alpha (Release 13.05., Produktseite) gegen private Beta (Hilfe, Blog). Beide Bezeichnungen meinen Warteliste.

**Claude und Cursor als External Agents (fertige Partner, nicht der eigene Agent)**
- „Claude and Cursor are the first two External Agents in Notion", Aufgaben vom Board zuweisen, „@-mention them like teammates", „watch them run" — [P: Release 01.07.2026](https://www.notion.com/releases/2026-07-01)
- Claude-Agenten: Beta, schrittweiser Rollout, Business und Enterprise. Abgerechnet in Notion-Credits pro Lauf wie Custom Agents. „Using your own Anthropic account isn't possible." Gehostet von Notion über Anthropic-Infrastruktur (Claude Managed Agents). Kein Web-Zugriff, kein Aufruf anderer Agenten während einer Sitzung. Notions Zero-Data-Retention gilt hier nicht, Anthropic speichert Sitzungsdaten zwischen Anfragen — [P: Use Claude agents in Notion](https://www.notion.com/help/use-claude-agents-in-notion)
- Cursor: Beta, an einen persönlichen Cursor-API-Schlüssel gebunden (nur Suchausschnitt, Seite nicht vollständig gelesen) — [P: Connect Cursor to Notion](https://www.notion.com/help/connect-cursor-to-notion)
- Presse: dieselben Grenzen, „Enterprise-Kontrollen auf der Roadmap", Stand 25.06.2026 — [B: Android Authority](https://www.androidauthority.com/notion-getting-external-agents-support-3681305/)

**Notion Agent APIs (Gegenrichtung)**
- GA seit 02.11.2026, nicht mehr Beta; Private-Alpha-Routen veraltet; persönlicher Agent per `notion_ai` und Personal Access Token; „Update agent status" veraltet. Öffentliche Beta seit 20.08.2026 — [P: Changelog](https://developers.notion.com/page/changelog)
- Zweck: Custom Agents und Notion AI aus eigenen Apps ansprechen (Slack-Bot, internes Tool), Sessions starten, Antwort streamen, Ereignisverlauf lesen. Zitat zu Connection-Token: „Sessions created with a connection token have no user, so nobody can reply to them in Notion" — [P: Agent APIs Overview](https://developers.notion.com/guides/notion-agent-apis/overview)
- Die API erstellt keine Custom Agents und arbeitet nur mit bestehenden. Custom Agents nur auf Business und Enterprise. PAT-Erstellung dort standardmäßig gesperrt, ein Owner muss sie freischalten — [P: Quickstart](https://developers.notion.com/guides/notion-agent-apis/quickstart)
- Widerspruch beim Status des Agent SDK: öffentliche Beta laut [P: Release-Seite, 15.09.2026](https://www.notion.com/releases), private Alpha laut [P: Hilfe](https://www.notion.com/help/what-is-the-notion-developer-platform), Alpha laut [P: Produktseite](https://www.notion.com/product/dev), Agent APIs GA laut [P: Changelog](https://developers.notion.com/page/changelog). Hilfe und Produktseite wirken veraltet, das neueste Datum ist der Changelog. Ob „Agent SDK" und „Agent APIs" dasselbe sind, ist nicht ausdrücklich belegt.

**Custom Agents (Notion-eigene Agenten)**
- Business oder Enterprise nötig. Trigger: @-Erwähnung in Seiten, Datenbank-Eigenschaften und Kommentaren; „A comment is added to a page"; Zeitpläne; Datenbank-Ereignisse; Slack. Zugriff nur auf freigegebene Inhalte — [P: Custom Agents](https://www.notion.com/help/custom-agents)
- Sie laufen auf Notions Modellen und Credits: 1.500 Standard- und 500 Select-Credits pro Business-/Enterprise-Sitz im Monat; Custom Agents verbrauchen Select-Credits; Zukauf möglich — [P: Blog 19.10.2026](https://www.notion.com/blog/notion-ai-more-for-less). Danach 10 $ pro 1.000 Credits im Monat — [P: Pricing](https://www.notion.com/pricing)
- Neues Credit-System für Bestandskunden seit 02.11.2026 — [P: Blog 19.10.2026](https://www.notion.com/blog/notion-ai-more-for-less)
- Eigene Server als Werkzeug: Custom MCP-Verbindung, Beta, Business und Enterprise — [P: Release-Seite, 15.09.2026](https://www.notion.com/releases). Nötig sind öffentliche Server-URL, OAuth oder Header-Auth, Admin-Freischaltung. Jede Verbindung gehört zu genau einem Agenten und nutzt die Zugangsdaten der einrichtenden Person. Schreib-Werkzeuge fragen standardmäßig nach. Notion prüft eigene MCP-Server nicht (nur Suchausschnitte der Seite gelesen) — [P: MCP connections for Custom Agents](https://www.notion.com/help/mcp-connections-for-custom-agents)

**Bot-Verbindung**
- Seit 10.06.2026 können Bots, die als User-Objekte erscheinen, `people`-Eigenschaften zugewiesen und in `user`-Erwähnungen genutzt werden. Interne Bots von Datenbank-Automationen und Custom Agents bleiben ausgeschlossen — [P: Changelog, Seite 3](https://developers.notion.com/page/changelog?page=3)

**Workers und Database Sync**
- Workers: kleine Node/TypeScript-Programme, deployt per CLI, von Notion gehostet in einer Sandbox. Können Sync (Standard alle 30 Minuten), Tools für Custom Agents und eingehende Webhooks — [P: Workers Overview](https://developers.notion.com/workers/get-started/overview.md)
- Öffentliche Beta, Business und Enterprise — [P: Blog Developer Platform](https://www.notion.com/blog/introducing-developer-platform). Seit 11.08.2026 in Notion-Credits — [P: Release 13.05.2026](https://www.notion.com/releases/2026-05-13)
- Limits pro Workspace: Tool- und Webhook-Läufe 600/Stunde (Burst 60/Minute), Sync-Läufe 600/Stunde, Builds 100/Tag, Sync-Schreiben 1.000.000/Stunde. Keine Laufzeit- oder Speicherangabe — [P: Workers Limits](https://developers.notion.com/workers/reference/limits.md)
- Database Sync ist eine Worker-Funktion, Beta. Daneben seit 13.10.2026 neu gebaute „Synced Databases" für GitHub, Jira und Salesforce, offenbar ein anderes Produkt — [P: Release 13.05.2026](https://www.notion.com/releases/2026-05-13), [P: Release-Seite](https://www.notion.com/releases)

**Notion MCP**
- Gehostet unter `https://mcp.notion.com/mcp`. Auth per OAuth oder MCP-Token als Bearer „with no browser sign-in". MCP läuft auf allen Tarifen, MCP-Token aber nur Business und Enterprise. Gäste können keine Verbindung herstellen — [P: Connect MCP](https://developers.notion.com/guides/mcp/get-started-with-mcp.md)
- Das Open-Source-Paket `notion-mcp-server` wird nicht mehr aktiv gepflegt — [P: Hosting Notion MCP locally](https://developers.notion.com/guides/mcp/hosting-open-source-mcp)
- MCP ist ein Weg, mit dem externe Agenten auf Notion zugreifen, der Agent erscheint dadurch aber nicht als Teilnehmer. Admins sehen verbundene Tools und können sie einzeln widerrufen — [P: Release-Seite, 13.10.2026](https://www.notion.com/releases)

**Presse-Aussagen ohne Primärbeleg**
- „Inbound"-Einordnung der External Agents API und Fahrplan-Details stehen in Blogs wie [B: DEV Community](https://dev.to/akaranjkar08/notion-developer-platform-2026-workers-external-agents-api-database-sync-guide-3mea) und [B: MindStudio](https://www.mindstudio.ai/blog/notion-developer-platform-claude-codex-agents), nicht gelesen und nicht übernommen. Eine Nachricht nennt „respond to mentions" — [B: Let's Data Science](https://letsdatascience.com/news/notion-integrates-claude-and-cursor-as-external-agents-7f0782c7); für Claude und Cursor bestätigt das die Release-Seite, für selbst gebaute Agenten nicht.

### Inferences
Wie elegant wäre es aus Nutzersicht heute (nicht getestet, aus Doku abgeleitet):
- **Weg A, Bot plus Kommentare:** Lia schreibt einen Kommentar, Webhook geht an den Server, `claude -p` läuft, Antwort kommt als Kommentar mit Bot-Name und Icon, Ergebnis als Seite oder Datei. Vorteil: eigene Pipeline, kein Credit-Verbrauch. Nachteil: kein Chat-Fenster, kein Eintrag in der Agentenliste, kein Fortschritt, keine Struktur in Kommentaren, öffentlicher Endpunkt nötig. Antwort erst nach Minuten bei langer Recherche, also eigene „läuft"-Rückmeldung bauen. Wirkt wie ein Kommentar-Bot, nicht wie ein Kollege.
- **Weg B, Custom Agent als Empfang:** Echte @-Erwähnung und Chat, der eigene Server hängt als MCP-Werkzeug dran. Vorteil: wirkt nativ. Nachteil: ein zweites Modell auf Notions Credits sitzt davor und entscheidet über die Anfrage, Business nötig, Beta, öffentlicher Server. Inhalte laufen zusätzlich durch Notions KI-Anbieter. Das widerspricht dem Grundsatz, dass die eigene Pipeline denkt.
- **Weg C, External Agents API:** Wäre die saubere Lösung, ist aber nicht planbar: Warteliste, keine öffentliche Doku, keine Preise, unklar ob ein kleiner Workspace aufgenommen wird.
- **Weg D, Claude-Agent von Notion:** Wirkt nativ und ist am einfachsten, ist aber nicht der eigene Agent: läuft bei Notion, kein Zugriff auf den Server (außer über Verbindungen), kein eigenes Anthropic-Konto, also keine Nutzung des vorhandenen Kontingents.
- Die Agent APIs helfen dem Ziel nicht, sie gehen in die andere Richtung.

### Gaps
- Ob eine eigene Verbindung (Bot) in der Notion-Oberfläche von Menschen per @ auswählbar ist und dann ein Ereignis auslöst: nur die API-Seite ist belegt.
- Technik, Preis und Aufnahmekriterien der External Agents API: keine öffentliche Quelle. Aktueller Status im November 2026 nicht bestätigt, die Hilfeseite trägt kein Datum.
- Zeitlimit für MCP-Werkzeugaufrufe aus Custom Agents: entscheidend für lange Recherchen, nicht gefunden.
- Credit-Verbrauch pro Lauf: keine Zahlen.

## UI-Grenzen: Eigene Oberflächen, Embeds, Blöcke, Plugins; Fassungsvergleich, Karten-Lernen, eigene Ansichten

### Takeaway
Es gibt seit Juli 2026 HTML-Blöcke: eigene interaktive Oberflächen in einem Sandbox-iframe, auch per API. Das ist der einzige allgemein zugängliche Weg für eigene Oberflächen. Eigene wiederverwendbare Blöcke sind private Alpha, ein Plugin-System für die Notion-Oberfläche habe ich nicht gefunden. Fassungsvergleich und Karten-Lernen gehen also nur als eingebettete Inseln.

### Cited Findings
- HTML-Block: Embed auf Basis einer hochgeladenen `.html`/`.htm`-Datei, die App rendert ihn „interactively in a sandboxed iframe" — [P: Block](https://developers.notion.com/reference/block)
- Per API seit 03.07.2026 über File Upload und `embed.file_upload` — [P: Changelog, Seite 3](https://developers.notion.com/page/changelog?page=3)
- Beispiele von Notion: ROI-Rechner, Quiz mit Auswertung, Org-Chart. Keine Angaben zu Sandbox, Tarif und Netzwerkzugriff — [P: Release 01.07.2026](https://www.notion.com/releases/2026-07-01)
- Custom Blocks: „Definition creation remains in private alpha", `definition-key` ist „reserved for App deployments"; Instanzen mit Binding-Overrides erscheinen als `<unknown>` — [P: Working with markdown content](https://developers.notion.com/guides/data-apis/working-with-markdown-content)
- Embed-Block mit fremder URL ist per API möglich (`url` oder `file_upload`) — [P: Block](https://developers.notion.com/reference/block). Drittanbieter wie Blocky liefern einbettbare Widgets, darunter Karteikarten, per `/embed` — [P: Connections-Seite Blocky](https://www.notion.com/connections/blocky)
- Vorschläge: Agenten schlagen Änderungen vor, die Nutzer einzeln freigeben — [P: Release-Seite, 28.08.2026](https://www.notion.com/releases). MCP-Werkzeuge für Vorschläge und frühere Versionen sowie `notion-restore-version` seit 27.10. und 03.11.2026; Markdown-Ausgabe zeigt nur angenommene Inhalte — [P: Changelog](https://developers.notion.com/page/changelog)
- Views: Filter, Sortierung und Ansichten per API seit 19.03.2026 — [P: Changelog](https://developers.notion.com/page/changelog). Webhooks für Views existieren — [P: llms.txt](https://developers.notion.com/llms.txt)

### Inferences
- **Fassungsvergleich:** Notions Seitenverlauf zeigt nur Notion-eigene Stände. Ein Vergleich von Pipeline-Fassungen müsste selbst gerendert werden: entweder als statischer HTML-Block je Vergleich oder als Vorschläge, falls die über die offene Schnittstelle schreibbar sind. Letzteres ist nur für MCP belegt.
- **Karten-Lernen:** Als HTML-Block darstellbar. Ob Lernstand dauerhaft speicherbar ist, hängt an Sandbox und Netzzugriff, beides unbelegt. Ohne Speicher bleibt nur ein externer Server per Embed, dann mit eigener Anmeldung im iframe. Das ist faktisch Eigenbau, nur innerhalb von Notion angezeigt.
- **Eigene Ansichten:** Innerhalb der Datenbank-Ansichten gut konfigurierbar, darüber hinaus keine Erweiterung.
- HTML-Blöcke sind statische Dateien. Änderung heißt neu hochladen, keine geteilte Live-Komponente.

### Gaps
- Sandbox-Rechte des HTML-Blocks: ausgehendes Netz, localStorage, Größe, Zugriff auf Notion-Daten, Anzeige auf dem Handy und für Gäste. Keine Primärquelle gefunden, [die vermutete Hilfeseite](https://www.notion.com/help/html-blocks) lieferte 404. Das ist die wichtigste offene Frage für die UI-Entscheidung.
- Ob Embeds fremder Seiten technische Einschränkungen haben (Cookies im iframe, Anmeldung): nicht gefunden.
- Was „App deployments" bedeuten: Der Begriff deutet auf ein kommendes App-System, das ist aber Vermutung.
- Vorschau von docx und pptx in Notion: nicht geprüft.

## Tarife und Gäste: Free, Plus, Business; Kosten für 3 Personen; Dateigrößen; Versionsverlauf

### Takeaway
Plus kostet 9,50 €, Business 19,50 € pro Mitglied und Monat laut Preisseite, also für 3 Personen 28,50 € oder 58,50 € im Monat. Alles Agentische (Custom Agents, Workers, MCP-Token, höhere Limits) verlangt Business. Gäste sind kostenlos, ihre genauen Rechte in Agenten-Funktionen sind nicht belegt.

### Cited Findings
| Punkt | Free | Plus | Business | Enterprise | Quelle |
|---|---|---|---|---|---|
| Preis je Mitglied/Monat | 0 € | 9,50 € | 19,50 € | individuell | [P: Pricing](https://www.notion.com/pricing) |
| Datei pro Upload | 5 MB | 5 GB | 5 GB | 5 GB | [P: Pricing](https://www.notion.com/pricing) |
| Seitenverlauf | 7 Tage | 30 Tage | 90 Tage | individuell | [P: Pricing](https://www.notion.com/pricing) |
| Custom Agents, Workers | nein | nein | ja | ja | [P: Custom Agents](https://www.notion.com/help/custom-agents), [P: Developer Platform](https://www.notion.com/help/what-is-the-notion-developer-platform) |
| API-Limit | 180/min | 180/min | 600/min | 600/min | [P: Request limits](https://developers.notion.com/reference/request-limits) |
| Datenresidenz | nein | nein | nein | ja, kostenlos | [P: Data residency](https://www.notion.com/help/data-residency) |

- „Save up to 20% with yearly". Der Abruf ließ offen, ob die Euro-Preise Jahres- oder Monatszahlung meinen — [P: Pricing](https://www.notion.com/pricing)
- Free: unbegrenzte Blöcke für Einzelnutzer, Blocklimit für mehrere Nutzer, Zahl auf der Seite nicht genannt; KI im Free und Plus nur als begrenzte Testversion — [P: Pricing](https://www.notion.com/pricing)
- Gäste: kostenlos, sehen nur eingeladene Seiten. Limit 10 nennt die Preisseite, Abruf ohne eindeutige Tarifzuordnung — [P: Pricing](https://www.notion.com/pricing). Herabstufung auf Free begrenzt auf 10 Gäste; Suchausschnitt deutet auf „Unlimited guests" für die anderen Tarife, nicht bestätigt — [P: Plan-Herabstufung](https://www.notion.com/help/plan-downgrade)
- Gäste können ansehen, kommentieren oder bearbeiten, je nach Stufe pro Seite. Abrechnung nur pro Mitglied — [P: Mitglieder und Gäste](https://www.notion.com/help/add-members-admins-guests-and-groups)
- Education Plan nur für akkreditierte Hochschulen, Schüler und Lehrkräfte der Stufe K-12 sind ausgeschlossen; Einzelperson, 30 Tage Verlauf, bis zu 100 Gäste — [P: Notion for Education](https://www.notion.com/help/notion-for-education)

### Inferences
- Kostenrechnung nur für Sitze, Credits extra: Plus 3 Sitze 342 € im Jahr, Business 3 Sitze 702 € im Jahr, bei obigen Preisen als reine Multiplikation. Ein Sitz plus zwei Gäste auf Business wäre 19,50 € im Monat, aber dann fehlen Gästen vermutlich Agenten-Funktionen und Zugriff auf den ganzen Workspace.
- Für reine API- und Bot-Nutzung würde Plus reichen, ohne Custom Agents und MCP-Token.
- 90 Tage Verlauf bei Business reicht nicht als Fassungsarchiv. Fassungen müssten auf dem eigenen Server bleiben.

### Gaps
- Exakte Gästegrenzen für Plus und Business, Blocklimit im Free-Mehrnutzer, Monatspreis ohne Jahresrabatt, Steuerangabe: im Abruf nicht eindeutig. Vor Entscheidung auf der Preisseite im Browser prüfen.
- Ob Gäste Custom Agents auslösen oder den Agenten-Chat nutzen können: Die Hilfe nennt Gäste dabei nicht.

## Datenschutz: DPA/AVV, Standort, EU-Datenresidenz, KI-Training, Schul- und personenbezogene Daten

### Takeaway
Ein DPA gibt es. EU-Speicherung gibt es nur im Enterprise-Tarif, sonst liegen die Daten standardmäßig in den USA, und auch bei Residenz können Verarbeitung und KI-Anbieter außerhalb stattfinden. Training mit Kundendaten schließt Notion aus. Für Schülerdaten fand ich keine Freigabe oder Bewertung, verantwortlich bleibt die Schule. Daraus folgt für mich: Schülerdaten gehören ohne Klärung nicht in einen Plus- oder Business-Workspace.

### Cited Findings
- DPA gilt per Verweis, soweit Notion DSGVO-Daten verarbeitet („hereby incorporated by reference"); Übermittlung in Drittländer über SCCs. Das Data Privacy Framework erwähnt die Seite nicht — [P: GDPR at Notion](https://www.notion.com/help/gdpr-at-notion)
- „Notion provides a Data Processing Addendum (DPA) that governs the processing of personal data"; 31 Subprozessoren, darunter AWS (USA, EU, Korea, Japan), Anthropic (global), Baseten (global), AssemblyAI (USA), Runlayer (USA). Zertifikate SOC 2 Type II, ISO 27001, BSI C5 — [P: Trust Center](https://trust.notion.com/)
- Datenresidenz: nur Enterprise, kostenlos. Frankfurt, Backup Irland. Gespeichert in der Region: Seiten, Dateien, Suchindex. Außerhalb möglich: Konto- und Nutzungsdaten, Verarbeitung durch Subunternehmer samt LLM-Anbietern. Nicht abgedeckt: Beta-Dienste und Daten, die Integrationen verarbeiten. Standardmäßig bleiben Daten in den USA — [P: Data residency](https://www.notion.com/help/data-residency)
- Security-Seite bestätigt „nur Enterprise"; ISO 27701, ISO 27018, TLS 1.2+, AES-256 — [P: Security](https://www.notion.com/security)
- „By default, neither Notion nor our AI providers use your Customer Data to train any models." Free, Plus, Business: KI-Anbieter speichern „for 30 days or fewer". ZDR für die meisten Modelle nur bei Enterprise. Embeddings bis 60 Tage nach Löschung — [P: AI security practices](https://www.notion.com/help/notion-ai-security-practices)
- Claude-Agenten in Notion sind von ZDR ausgenommen — [P: Use Claude agents in Notion](https://www.notion.com/help/use-claude-agents-in-notion)
- Verantwortlich im Sinne der DSGVO ist die Schule, vertreten durch die Schulleitung, auch wenn Lehrkräfte zu Hause verarbeiten; Land Niedersachsen, nur Suchausschnitt — [Kultusministerium Niedersachsen](https://mk.niedersachsen.de/download/156933)
- Dienstliche Daten auf privaten Geräten verlangen in NRW Genehmigung und Verpflichtungserklärung, nur Suchausschnitt — [Bildungsportal NRW](https://www.schulministerium.nrw/themen/recht/datenschutz-im-schulbereich)

### Inferences
- Plus oder Business: Daten in den USA, Rechtsgrundlage SCCs. Enterprise ist für 3 Personen kein realistischer Tarif, Preis nur auf Anfrage.
- Weg über den eigenen Server hilft nur begrenzt: Sobald Ergebnisse in Notion liegen, gilt Notions Standort.
- External Agents und Workers sind Beta und damit laut Residenz-Seite ohnehin nicht abgedeckt, Claude-Agenten auch nicht von ZDR.
- Sinnvoll wäre eine Trennung: Schülerbezogenes bleibt außerhalb von Notion. Das ist keine Rechtsauskunft; die Entscheidung liegt bei Jan und, bei schulischen Daten, bei der Schule. Die Projektregel sieht ohnehin vor, dass Schülerdaten nie automatisch behandelt werden.

### Gaps
- DPA-Volltext nicht lesbar, die Seite lieferte über das Werkzeug nur Fragmente: [DPA](https://app.notion.com/p/Data-Processing-Addendum-361b540101274b1fa7e16b90402b0d99). Ob es für Free- und Plus-Kunden gleich gilt, ob eine unterzeichnete Fassung nötig ist und welche Löschfristen gelten, ist offen.
- Vollständige Subprozessorenliste nicht abrufbar (404 bei der geratenen URL).
- Standpunkt von Datenschutzbehörden oder Kultusministerien zu Notion: keine Quelle gefunden. Lias Bundesland und die dortigen Vorgaben wurden nicht geprüft.
- Datenschutzbestimmungen und AGB (Mindestalter): Die geratene Hilfeseite lieferte 404.

## Bindung: Export, Formate, Verluste, Änderungen und Ausfälle der API

### Takeaway
Der Export ist brauchbar für Text (Markdown, CSV, HTML, PDF), aber kein Abbild des Systems: Ansichten, Formulare, Agenten und Teile der Kommentare gehen verloren oder sind nicht belegt, und ein Reimport stellt nichts wieder her. Die API ändert sich schnell mit zwei brechenden Versionen seit September 2025; die neuen Agent-Funktionen kippen ihren Status teils binnen Wochen. Ausfälle sind kurz und regelmäßig, aber nur über Dritte belegt.

### Cited Findings
**Export**
- PDF, HTML, Markdown und CSV; Workspace-Export als HTML, Markdown oder CSV samt Dateien, Link 7 Tage gültig, kann bis 30 Stunden dauern. Unterseiten im PDF nur Business und Enterprise. Enterprise-Admin-API für geplante Exporte (Beta) — [P: Export](https://www.notion.com/help/export-your-content)
- Verluste: Callouts in Markdown bleiben HTML; Formularansicht nicht exportierbar; nur aktuelle oder Standardansicht; private Seiten anderer fehlen; Reimport stellt den Workspace nicht wieder her; Kommentare nur beim HTML-Export ausdrücklich genannt — [P: Export](https://www.notion.com/help/export-your-content)
- Gelöste Kommentare per API nicht abrufbar — [P: Working with comments](https://developers.notion.com/guides/data-apis/working-with-comments.md); der HTML-Export kann sie laut Hilfe mitnehmen — [P: Export](https://www.notion.com/help/export-your-content)
- EU Data Act: Für EU-Kunden gibt es einen Wechselweg (Addendum beim Support, 60 Tage Vorlauf, 30 Tage Wechsel, 30 Tage Abruf), Formate CSV oder HTML, Wechselgebühren möglich vor dem 12.01.2027 — [P: EU Data Act FAQ](https://www.notion.com/md/eu-data-act)

**Änderungen**
- Version 2025-09-03 laut Doku „not backwards-compatible"; bei älteren Verbindungen scheitern Lesen, Schreiben und Abfragen, sobald ein Nutzer eine zweite Data Source hinzufügt — [P: Upgrade-Guide](https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03.md)
- Version 2026-03-11: `after` wird `position`, `archived` wird `in_trash`, `transcription` wird `meeting_notes` — [P: Changelog](https://developers.notion.com/page/changelog)
- Markdown v1 wird abgelöst, soll etwa drei Monate nach der neuen Version abgeschaltet werden, Ankündigung mindestens drei Monate vorher — [P: Changelog, 30.10.2026](https://developers.notion.com/page/changelog)
- Agent APIs: Alpha-Routen mussten bis 30.09.2026 abgelöst sein, GA am 02.11.2026 mit weiterer Veralterung — [P: Changelog](https://developers.notion.com/page/changelog)
- Limits: Workspace-Limit neu am 16.06.2026, neues Fenster am 09.09.2026 — [P: Changelog](https://developers.notion.com/page/changelog)
- Preise: Workers wechselten am 11.08.2026 von kostenlos auf Credits, neues Credit-System am 02.11.2026 — [P: Release 13.05.2026](https://www.notion.com/releases/2026-05-13), [P: Blog 19.10.2026](https://www.notion.com/blog/notion-ai-more-for-less)

**Ausfälle (nur Dritte, status.notion.so nicht abgerufen; Angaben aus Suchzusammenfassungen, die Zuordnung zu den einzelnen Links ist nicht Seite für Seite geprüft)**
- 01.10.2026: Public API 16 Minuten 500er — [D: UptimeRobot](https://uptimerobot.com/is-it-down/notion/2026-10-01/)
- 23.10.2026: „Users unable to access Notion", 3 Stunden 6 Minuten, Einstufung kritisch — [D: Pulsetic](https://pulsetic.com/status/notion/)
- 11.07.2026: etwa 31 Minuten, breit inklusive API — [D: IsDown](https://isdown.app/status/notion/outage-history?page=2)
- 20./21.04.2026: Abfragen lieferten nach 300 statt 10.000 Seiten unvollständige Ergebnisse, ein stiller Datenfehler statt eines Ausfalls — [D: IsDown](https://isdown.app/status/notion/incidents/573978-notion-api-returning-incomplete-results)

### Inferences
- Die Bindung liegt weniger im Text als in Workflows: Agenten-Konfigurationen, Datenbankansichten, HTML-Blöcke und Kommentarverläufe. Wenn der eigene Server Quelle der Wahrheit bleibt (Fassungen, Renderer-JSON) und Notion nur Anzeige ist, bleibt das gering.
- Alles Agentische außerhalb der REST-API ist Beta oder jünger. Mit jährlich mehreren Pflichtumstellungen ist zu rechnen. Die API-Version wird pro Anfrage festgelegt, schützt aber nach dem 2025-09-Fall nicht vollständig, weil Nutzeraktionen alte Versionen brechen können.
- Der April-Vorfall zeigt: Vollständigkeit großer Abfragen im eigenen Code prüfen.

### Gaps
- Offizielle Verfügbarkeitszahlen und SLA: nicht gefunden. Enterprise-SLA unbekannt.
- Ob Custom-Agent-Konfigurationen, HTML-Blöcke und Verlauf im Export enthalten sind: nicht belegt.
- Rückgabeformat von Datei- und Datenbankbeziehungen im Markdown-Export im Detail: nicht geprüft.
