# Alternativen zu Notion als Oberfläche für eigene KI-Agenten (Stand: Anfang November 2026)

Lesehinweis: Nichts wurde installiert oder ausprobiert. "Dokumentiert" heißt: steht in Doku, Repo oder Preisseite des Herstellers. "Quellcode gelesen" heißt: Datei aus dem Repo gelesen, nicht ausgeführt. Vermutungen stehen nur unter "Inferences". Herstelleraussagen, die reine Werbung sind, tragen den Zusatz "Marketing". Mehrere Vergleichsseiten stammen von Wettbewerbern oder Hosting-Anbietern und sind entsprechend markiert. GitHub-Kennzahlen wurden am 04./05.11.2026 über die GitHub-API gelesen.

## Selbst hostbar ohne Docker und root? RAM, Abhängigkeiten, Passung zum Server

### Takeaway
Nur vier Wege sind ohne Docker und root überhaupt dokumentiert oder aus dem Repo ableitbar: Outline (from source), Docmost (Build aus dem Quellcode, offiziell als Entwicklungsanleitung), BookStack (manuell) und Nextcloud (manuell). Für AFFiNE, AppFlowy, Anytype fand ich als Weg nur Docker. Auf dem Server fehlen Postgres, Redis, PHP und MySQL; alles müsste ohne sudo nachgezogen werden. Das ist die eigentliche Hürde, und der freie Speicher reicht knapp für genau einen Dienst dieser Klasse.

### Cited Findings

Serverstand (am 04.11.2026 auf dem Server gemessen, Quelle: eigene Abfrage per `free -m`, `command -v`, `df`):
- 7941 MB RAM gesamt, 6413 MB belegt, 171 MB frei, 1527 MB verfügbar (inkl. freigebbarem Cache), kein Swap, 74 GB Platte frei.
- Vorhanden: Node v22.23.4, npm, Caddy, Git, Python 3.12.3. Nicht vorhanden: Postgres, Redis/Valkey, PHP, Composer, MySQL/MariaDB, Docker, Podman, Java, yarn, pnpm.

| Kandidat | Weg ohne Docker | Abhängigkeiten (dokumentiert) | RAM (dokumentiert) |
|---|---|---|---|
| Outline | "From source", gedacht für Entwicklung und nicht unterstützte Plattformen | Postgres 14+, Redis 4+, Datei-Speicher lokal oder S3, Anmeldeanbieter Pflicht | min. 512 MB, 1 GB+ empfohlen |
| Docmost | Build aus dem Quellcode (pnpm, nx) | Node 22+, Postgres 16+, Redis/Valkey 7+, Speicher lokal/S3/Azure | keine offizielle Angabe gefunden |
| AFFiNE | keiner gefunden, Docker Compose "empfohlen" | Postgres (einzige DB), Redis Pflicht | 2 GB, 4 GB bei langen Dokumenten, 4 Kerne empfohlen |
| AppFlowy | Hersteller nennt nur Docker Compose, Swarm, Helm | Postgres mit pgvector, Redis, GoTrue, Worker, Nginx u. a. | keine Herstellerangabe |
| Anytype (any-sync) | nur Docker Compose, für Produktion Puppet/Ansible-Module | MongoDB, Redis, Garage (S3), mehrere Knoten | ca. 1 GB verfügbar, je Daemon Grenze 500 MB |
| SiYuan | Kernel-Programm mit `serve`; Hersteller beschreibt Docker | keine externe DB genannt | keine Angabe gefunden |
| BookStack | manuell dokumentiert | PHP 8.2+, MySQL 8/MariaDB 10.6+, Composer, Webserver | keine Angabe |
| Nextcloud + Collectives | manuell dokumentiert, Beispiele mit sudo | PHP 8.3+, DB, Apache/nginx, Apps Teams und Text | 128 MB je Prozess, 512 MB empfohlen |
| Coda, Confluence | nicht selbst hostbar (reine Cloud in dieser Betrachtung) | keine | keine Serverlast |
| Obsidian Sync | Headless-Client statt Server | Node 22+ | keine Angabe |

Belege:
- Outline: Anforderungen — [Requirements](https://docs.getoutline.com/s/hosting/doc/requirements-ULdYnwi4wG); Installationswege — [Installation methods](https://docs.getoutline.com/s/hosting/doc/installation-methods-pSvgz9j0QC).
- Outline, Quellcode gelesen: `engines` verlangt Node `>=22.23.4 <23` (u. a.), Paketmanager yarn 4.18.0, Build mit `yarn vite:build` und `build:server`, Start mit `node ./build/server/index.js` — [package.json](https://raw.githubusercontent.com/outline/outline/main/package.json). Die installierte Node-Version erfüllt das exakt, ohne Spielraum nach unten.
- Outline: "local" speichert Anhänge auf der Platte, S3 ist optional; mindestens ein Anmeldeanbieter ist Pflicht; OIDC generisch; E-Mail-Anmeldung braucht SMTP; Faustregel Prozesse = Speicher / 512 — [.env.sample](https://raw.githubusercontent.com/outline/outline/main/.env.sample).
- Docmost: Node >= 22, Postgres >= 16, Redis/Valkey >= 7, Build per pnpm/nx — [Development-Anleitung](https://docmost.com/docs/self-hosting/development); `DATABASE_URL`, `REDIS_URL`, `STORAGE_DRIVER` local/s3/azure — [Environment Variables](https://docmost.com/docs/self-hosting/environment-variables). Das Repo enthält docker-compose und Dockerfile — [GitHub](https://github.com/docmost/docmost).
- AFFiNE: Zitat "AFFiNE can't run without a Redis server provided", Postgres einzige DB, Prometheus zusätzlich ca. 200 MB — [Requirements](https://docs.affine.pro/self-host-affine/install/requirements); Compose als "Recommended", andere Wege nicht beschrieben — [Install](https://docs.affine.pro/self-host-affine/install).
- AppFlowy: Das alte Repo AppFlowy-Cloud ist archiviert und baut nicht mehr den aktuellen Server — [AppFlowy-Cloud](https://github.com/AppFlowy-IO/AppFlowy-Cloud). Selbsthosting läuft über das kommerzielle Repo per Docker Compose — [AppFlowy-SelfHost-Commercial](https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial). Drittquelle nennt 2–4 GB, andere 4–8 GB — [Cloudzy, Hosting-Anbieter](https://cloudzy.com/blog/affine-vs-appflowy-vs-docmost/). "Direct installation on bare metal" erwähnt nur eine Drittseite — [Mintlify](https://mintlify.com/AppFlowy-IO/AppFlowy/self-hosting/overview); widerspricht dem Hersteller-Repo in der Tendenz, nicht geprüft.
- Anytype: Komponenten, Docker, ca. 1 GB; laut Repo für persönliche Netze, Tests und Reviews — [any-sync-dockercompose](https://github.com/anyproto/any-sync-dockercompose).
- SiYuan: `serve`-Unterbefehl, Docker-Image, "One workspace, one writer" — [GitHub](https://github.com/siyuan-note/siyuan).
- BookStack: Anforderungen und manuelle Schritte; sudo nur bei den Ubuntu-Skripten erwähnt — [Installation](https://www.bookstackapp.com/docs/admin/installation/).
- Nextcloud 36: RAM je Prozess, PHP 8.3–8.5, SQLite "nur für Tests und Minimalinstallationen" — [System requirements](https://docs.nextcloud.com/server/latest/admin_manual/installation/system_requirements.html); Beispiele mit sudo/a2enmod — [Source installation](https://docs.nextcloud.com/server/latest/admin_manual/installation/source_installation.html). Collectives braucht Teams und Text — [GitHub](https://github.com/nextcloud/collectives).
- Obsidian Headless: Node 22+, `npm install -g obsidian-headless`, open beta — [Obsidian Help](https://obsidian.md/help/headless).

Weitere Kandidaten:
- Notara: eine SQLite-Datei, keine externen Dienste, Wege auch per Bun; 277 Commits, eine Person, Version 0.1.x — [GitHub](https://github.com/DnzzL/notara). 3 Sterne laut GitHub-API.
- Colanode: Postgres mit pgvector, Redis, Server als Docker-Image — [GitHub](https://github.com/colanode/colanode). Letztes Release v0.4.7 am 03.04.2026 laut GitHub-API.
- Wiki.js: Anforderungen ließen sich nicht lesen (Doku-URL 404). Trilium verweist auf eigene Server-Doku, Docker nur als eine Möglichkeit — [GitHub](https://github.com/TriliumNext/Trilium).

### Inferences
- Postgres und Redis lassen sich ohne root vermutlich als Benutzerprogramme betreiben (etwa entpackte Pakete oder Conda-artige Umgebung, dazu systemd-User-Dienst). Nicht erprobt und keine Herstelleraussage. Das ist Installation neuer Software und braucht laut CLAUDE.md Jans Okay.
- Geschätzter Bedarf für Outline mit Postgres und Redis: etwa 1 GB, wenn Doku-Empfehlung und kleine DB-Instanzen stimmen. Bei 1527 MB verfügbar und ohne Swap bleibt wenig Reserve, und die Zahl schwankt mit der Zahl laufender Claude-Prozesse (einzeln 180–360 MB gemessen). Ein zweiter Dienst dieser Klasse passt nicht.
- Der Frontend-Build von Outline und Docmost könnte auf dem Server selbst den Speicher sprengen; das Repo-Gedächtnis kennt OOM-Ausfälle von Diensten. Vermutlich besser auf dem Mac oder anderswo bauen und das Ergebnis kopieren. Nicht geprüft, wie viel RAM der Build wirklich braucht.
- AFFiNE scheidet bei dieser Speicherlage aus (2 GB Mindestempfehlung plus Postgres und Redis, keine Docker-freie Anleitung). AppFlowy und Anytype scheiden am Docker-Weg aus.
- BookStack und Nextcloud brauchen PHP ohne root, zusätzlich zur DB. Das ist mehr Fremdtechnik als Outline, das die vorhandene Node-Laufzeit nutzen kann.

### Gaps
- Keine belastbaren Messwerte zum echten RAM von Outline oder Docmost im Betrieb gefunden. Docmost nennt keine Zahl.
- Die Installationsseite von Outline nennt "From source", die Schritte selbst habe ich nicht gesehen. Deren Eignung für den Dauerbetrieb bleibt offen ("for development or platforms ...").
- SiYuan: Betrieb ohne Docker wird nicht ausdrücklich als Serverweg beschrieben.

## Lizenz, Kosten für 3 Personen, Aktivität und Reife 2026

### Takeaway
Outline ist kostenlos, aber nicht Open Source im engeren Sinn (BSL, interne Nutzung erlaubt). Docmost ist im Kern AGPL, die für Agenten wichtigen Teile kosten aber real rund 720 USD im Jahr wegen 10 Plätzen Minimum. AppFlowy ist für drei gleichberechtigte Personen ohne Lizenz nicht passend. Alle Hauptkandidaten sind 2026 aktiv gepflegt.

### Cited Findings

| Kandidat | Lizenz | Kosten für 3 | Letztes Release (GitHub-API) | Sterne |
|---|---|---|---|---|
| Outline | BSL 1.1 | selbst gehostet 0, Cloud 10 USD/Monat | v1.12.0, 23.10.2026 | 41k |
| Docmost | AGPL-3.0 + EE-Teile | Community 0; Business 6 USD/Platz, min. 10 Plätze | v0.97.0, 25.10.2026 | 22k |
| AFFiNE | MIT (CE) laut Readme | selbst gehostet 0 | v0.27.4, 18.08.2026 | 74k |
| AppFlowy | AGPL (Client), Server kommerziell | Free: 1 Platz + 3 Gast-Editoren | 0.15.0, 02.11.2026 | 78k |
| Anytype | any-sync MIT; Client nicht als SPDX erkannt | Selbsthosting 0, Client-Lizenz prüfen | v0.57.7, 03.11.2026 | 9k |
| SiYuan | AGPL-3.0, manches nur für Zahlende | 0 | v3.8.9, 29.10.2026 | 47k |
| BookStack | MIT | 0 | v26.09.2, 20.10.2026 | Codeberg 311 |
| Collectives | AGPL-3.0+ | 0 | v4.8.0, 04.11.2026 | 200 |
| Confluence | proprietär | Free bis 10 Nutzer; Standard ca. 6 USD/Nutzer | n/a | n/a |
| Coda (jetzt Superhuman Docs) | proprietär | Free; nur Doc Maker zahlen | n/a | n/a |
| Obsidian Sync | proprietär | ca. 4–5 USD/Person/Monat | n/a | n/a |

Belege:
- Outline: Licensor General Outline, Inc.; "may not use the Licensed Work for a Document Service"; Change Date 2030-10-23, dann Apache 2.0 — [LICENSE](https://raw.githubusercontent.com/outline/outline/main/LICENSE). Verboten ist "selling, reselling, or hosting Outline as a service" — [License restrictions](https://docs.getoutline.com/s/hosting/doc/license-restrictions-f9aq6uEL3H).
- Outline: Starter 10 USD/Monat für 1–10 Mitglieder; On-Premises Community kostenlos ohne Support; Business min. 10 Nutzer zu 4 USD — [Pricing](https://www.getoutline.com/pricing). Der Community Edition fehlen namentlich SAML, Audit Log, strukturierte Datenattribute, Confluence-Importer — [Business + Enterprise](https://docs.getoutline.com/s/hosting/doc/business-enterprise-rv0715NxO3).
- Docmost: AGPL plus getrennte EE-Ordner — [GitHub](https://github.com/docmost/docmost); Business 6 USD/Platz/Monat jährlich, 10 Plätze Minimum, Bildungsrabatt über Vertrieb möglich — [Pricing](https://docmost.com/pricing). Lizenz wird offline geprüft, nach Ablauf fällt die Instanz auf Open Source zurück — [Editions](https://docmost.com/docs/editions).
- AFFiNE: CE unter MIT, EE noch nicht veröffentlicht — [GitHub](https://github.com/toeverything/AFFiNE); eine Drittquelle sagt AGPL-3.0 — [DEV](https://dev.to/selfhostingsh/affine-vs-appflowy-open-source-notion-clones-2mg4). Die GitHub-API meldet "NOASSERTION", also kein eindeutiger Lizenztyp.
- AppFlowy: eigene "Self-Hosted Commercial License"; Free 1 Platz, bis 3 Gast-Editoren; AppFlowy-Cloud am 11.09.2026 archiviert — [AppFlowy-SelfHost-Commercial](https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial), [AppFlowy-Cloud](https://github.com/AppFlowy-IO/AppFlowy-Cloud). Railway behauptet "fully open-source" — [Railway](https://railway.com/deploy/appflowy); das stimmt für den Selbsthost-Server nicht mehr.
- SiYuan: "Most features are free", einzelne Funktionen nur für Mitglieder — [GitHub](https://github.com/siyuan-note/siyuan).
- BookStack: MIT — [LICENSE](https://codeberg.org/bookstack/bookstack/raw/branch/development/LICENSE). 2026 viele Sicherheitsreleases (u. a. ZIP-Import mit RCE-Szenario, v26.05.4), Umzug nach Codeberg; PHP-Sicherheitswarnung vom 23.10.2026 — [Blog](https://www.bookstackapp.com/blog/).
- Confluence Free: bis 10 Nutzer, 2 GB, Community-Support — [Atlassian Licensing](https://www.atlassian.com/licensing/confluence). Standard: 5,78 USD laut veralteten Strukturdaten der Preisseite, 6,05 USD laut Forum — [Pricing](https://www.atlassian.com/software/confluence/pricing), [Community](https://community.atlassian.com/forums/Confluence-questions/How-much-is-quot-standard-quot-confluence-per-annum/qaq-p/2522055). Aktueller Preis ungesichert.
- Coda: heißt seit 08.07.2026 Superhuman Docs — [Docmost-Blog, Wettbewerber](https://docmost.com/blog/coda-vs-confluence/); bestätigt durch Weiterleitung der API-Doku auf [docs.superhuman.com](https://docs.superhuman.com/developers/apis/v1). Preise widersprechen sich (Pro 10, 12 oder 15 USD je Doc Maker) — [G2](https://www.g2.com/products/grammarly-coda/pricing), [Eesel](https://www.eesel.ai/blog/coda-pricing), [Toolradar](https://toolradar.com/tools/coda/pricing). Die offizielle Hilfeseite war nicht lesbar (403).
- Obsidian Sync: 4 USD jährlich, 5 USD monatlich, jede mitarbeitende Person braucht ein Abo — [Eesel](https://www.eesel.ai/blog/obsidian-pricing), [Lindy](https://www.lindy.ai/blog/obsidian-pricing). Nur Drittquellen.

### Inferences
- Interne Nutzung in einer Uni-Projektgruppe verstößt nach dem Lizenzwortlaut wohl nicht gegen die BSL von Outline, weil niemand als Dienst an Dritte verkauft wird. Das ist keine Rechtsberatung, und ein Anschluss an Dritte außerhalb der Gruppe wäre neu zu prüfen.
- Docmost Business für 3 Personen: 10 × 6 × 12 = 720 USD/Jahr, sofern kein Bildungsrabatt greift. Für eine dreiköpfige Gruppe unverhältnismäßig.
- Docmost ist noch vor 1.0; häufige Updates sind zu erwarten. Bei BookStack spricht die Sicherheitsrelease-Dichte für aktive Pflege, verlangt aber schnelles Nachziehen.

### Gaps
- Anytype-Clientlizenz nicht gelesen.
- Confluence- und Coda-Preise von November 2026 nicht aus erster Hand. Der Hinweis "Coda Pricing Change — September 2026" auf [Costbench](https://costbench.com/changelog/coda-price-increase-2026-09/) wurde nicht geprüft.

## Verschachtelte Seiten, umbenennen und verschieben, Kommentare an Textstellen, Rechte, Verlauf, Dateien, Echtzeit

### Takeaway
Outline und Docmost decken die Punkte am ehesten ab. Einschränkung: Bei Docmost liegen Seitenrechte (und vermutlich das Auflösen von Kommentaren) im Bezahlplan, bei Outline hängen Rechte hauptsächlich an Collections. BookStack hat Kommentare an Textstellen, aber nur drei feste Ebenen. Nextcloud Collectives hat dafür offenbar noch keine Kommentare, Obsidian keine Echtzeit.

### Cited Findings
- Outline Kommentare: am Dokument und an markiertem Text, Antworten, Reaktionen, auflösen; für Nur-Lesen-Nutzer laut Doku nicht möglich — [Commenting](https://docs.getoutline.com/s/guide/doc/commenting-z7eSWvI5TI); v1.8.0 meldet das Gegenteil — [Release v1.8.0](https://github.com/outline/outline/releases/tag/v1.8.0). Widerspruch, neuere Angabe vermutlich richtig.
- Outline Rechte: "targeted at the Collections level", einzelne Personen und Gruppen; Revisionsverlauf je Dokument; öffentliche Freigabe je Collection steuerbar — [Security](https://docs.getoutline.com/s/guide/doc/security-DlJBglbImQ). Die API hat auch Dokument-Freigaben an Nutzer und Gruppen sowie Verschieben — [API](https://www.getoutline.com/developers).
- Outline Echtzeit: im Quellcode der Webhook-Ereignisse tauchen `documents.move`, `documents.title_change`, `documents.add_user` auf — [DeliverWebhookTask.ts](https://raw.githubusercontent.com/outline/outline/main/plugins/webhooks/server/tasks/DeliverWebhookTask.ts). Echtzeit, Quellcode gelesen: Abhängigkeiten `yjs`, `y-prosemirror`, `@hocuspocus/server` — [package.json](https://raw.githubusercontent.com/outline/outline/main/package.json); Readme nennt "collaborative" — [README](https://raw.githubusercontent.com/outline/outline/main/README.md).
- Outline Import: ein Notion-Plugin liegt im Repo (`plugins/notion`) — [GitHub](https://github.com/outline/outline).
- Docmost Community: Realtime, Spaces, Rechte, Gruppen, Kommentare, Seitenhistorie, Anhänge, Einbettungen (Marketing-nahe Feature-Liste) — [GitHub](https://github.com/docmost/docmost). Seitengenaue Rechte erst ab Business — [Pricing](https://docmost.com/pricing). "Comments" und "Resolve comments" sind getrennte Zeilen, Zuordnung nicht ablesbar — [Pricing Compare](https://docmost.com/pricing#compare). Auflösen nur Enterprise laut Dienstleister — [WZ-IT](https://wz-it.com/en/blog/docmost-community-vs-enterprise-edition/). Versionsverlauf steht sowohl als Community-Zeile als auch in der Business-Liste — unklar.
- BookStack: Kommentare an markiertem Text seit v25.05, Markierung veraltet sichtbar, Seitenleiste nur im neuen Editor (damals Beta), nur der erste Kommentar eines Threads verweist auf Text — [Release v25.05](https://www.bookstackapp.com/blog/bookstack-release-v25-05/). Struktur: Shelves enthalten Books, Books enthalten Pages direkt oder über optionale Chapters; Inhalte nur in Pages; verschachtelte Chapters nicht erwähnt — [Content Overview](https://www.bookstackapp.com/docs/user/content-overview/).
- Nextcloud Collectives: kollaboratives Bearbeiten per Text-App, Markdown, Volltextsuche, Sammlung gehört einem Team — [GitHub](https://github.com/nextcloud/collectives). Kommentare an Textstellen sind ein offener Wunsch — [Forum](https://help.nextcloud.com/tag/Nextcloud%20Collectives/254); [nextcloud/text#185](https://github.com/nextcloud/text/issues/185).
- AFFiNE: Community-MCP-Listings zeigen teils Kommentarwerkzeuge, teils nicht — [LobeHub](https://lobehub.com/de/mcp/dawncr0w-affine-mcp-server). Keine Funktionsprüfung.
- SiYuan: Der Maintainer sagt, gleichzeitiger Mehrbenutzerbetrieb könne "unpredictable problems" haben, SiYuan sei für Einzelne — [Forum](https://liuyun.io/article/1742557486683). Kommentare nicht beschrieben; im Docker-Betrieb kein Export nach PDF, HTML, Word — [GitHub](https://github.com/siyuan-note/siyuan).
- Anytype: Ausrichtung auf objektbasierte, verschlüsselte Notizen — [OpenAlternative](https://openalternative.co/compare/anytype/vs/siyuan). Keine Herstellerbestätigung zu Kommentaren.
- Obsidian: Shared Vault bis 20 Personen, alle mit denselben Rechten bis auf Einladen, keine feinen Rollen; keine eingebaute Echtzeit — [Review-Seiten, Drittquelle](https://www.eesel.ai/blog/obsidian-pricing), [Lindy](https://www.lindy.ai/blog/obsidian-pricing).
- Confluence Free: keine anpassbaren Rechte — [Features](https://www.atlassian.com/software/confluence/features). Inline-Kommentare existieren in der v2-API — [API-Klasse](https://pub.dev/documentation/atlassian_apis/latest/confluence_v2/CommentApi-class.html).

### Inferences
- Für drei Personen reichen Rechte auf Collection-Ebene bei Outline wohl aus; Jans Agenten-Konto lässt sich auf eine Collection begrenzen. Ungeprüft, ob das alle Anforderungen deckt.
- Docmost Community reicht fürs Schreiben zu dritt, aber Kommentarauflösen und Seitenrechte müssten vor einer Wahl in einer Testinstanz geprüft werden.
- Tiefe Verschachtelung ist bei BookStack durch die feste Struktur (Book, Chapter, Page) begrenzt, also kein freies Notion-Gefühl.

### Gaps
- Für Outline und Docmost fand ich keine Herstellerseite, die unbegrenzte Verschachtelung ausdrücklich nennt. Sehr wahrscheinlich gegeben, aber nicht belegt.
- Echtzeit bei BookStack nicht belegt, ich fand keine Herstellerbestätigung.
- Dateigrößen und Dateiverhalten nur bei Outline teilweise sichtbar (`FILE_STORAGE_UPLOAD_MAX_SIZE=262144000` in [.env.sample](https://raw.githubusercontent.com/outline/outline/main/.env.sample)).

## API, Webhooks, MCP, Agenten-Einbindung; eigene Seiten oder Knöpfe

### Takeaway
Outline ist hier klar vorn: REST-artige API mit Kommentaren, signierte Webhooks für Dokument- und Kommentar-Ereignisse und ein eingebauter MCP-Server, der im Open-Code-Repo liegt. Ein Python-Agent kann also Aufträge per Kommentar oder Dokumentänderung annehmen und Ergebnisse als Text oder Kommentar zurückschreiben. Bei Docmost sind API-Schlüssel und MCP Bezahlfunktionen, Webhooks fand ich keine. Eigene Knöpfe bietet keiner der freien Kandidaten sauber an.

### Cited Findings
- Outline API: Dokumente erstellen, ändern, verschieben, suchen, Import/Export; Kommentare erstellen, auflisten, auflösen, wieder öffnen; Webhook-Abos über API, nur für Admins; bei Überlast 429 mit Retry-After — [Developers](https://www.getoutline.com/developers).
- Outline Webhooks, Quellcode gelesen: u. a. `documents.create/update/move/publish/title_change`, `comments.create/update/delete`, Header `Outline-Signature` — [DeliverWebhookTask.ts](https://raw.githubusercontent.com/outline/outline/main/plugins/webhooks/server/tasks/DeliverWebhookTask.ts).
- Outline MCP: Changelog-Einträge 18.02.2026 (MCP) und 26.04.2026 (Dokumente patchen, verschieben, löschen, Anhänge, Inline-Kommentare erstellen und auflösen); WebMCP 09.09.2026 — [Changelog](https://www.getoutline.com/changelog). Quellcode: Ordner `server/mcp` mit Werkzeugen, Einstieg `server/routes/mcp`; Prüfung auf `TeamPreference.MCP`, in den gelesenen Zeilen keine Lizenzprüfung — [README](https://raw.githubusercontent.com/outline/outline/main/server/mcp/README.md), [Route](https://raw.githubusercontent.com/outline/outline/main/server/routes/mcp/index.ts). Selbst gehostet per eigene Domain und `/mcp` laut Drittquelle — [mcp.directory](https://mcp.directory/blog/outline-mcp-complete-guide-2026). Community-Server nennt den offiziellen als Ersatz — [outline-mcp-server](https://github.com/mmmeff/outline-mcp-server).
- Docmost MCP: Endpunkt `/mcp`, Werkzeuge u. a. `create_page`, `update_page`, `move_page`, `create_comment`, `get_comments` — [Docs DE](https://docmost.com/docs/de/user-guide/mcp). Lizenz: englische Seite sagt Business oder Enterprise — [Docs EN](https://docmost.com/docs/user-guide/mcp); deutsche Seite sagt Enterprise — [Docs DE](https://docmost.com/docs/de/user-guide/mcp). Widerspruch, deutsche Fassung vermutlich veraltet; die Preisseite nennt "AI & MCP" bei Business.
- Docmost API: API-Schlüssel ab Business — [Pricing](https://docmost.com/pricing). Ein Community-Wrapper nutzt die interne REST-API mit Sitzung und eigenem Agentenkonto und nennt das offen in der Community Edition — [Conare](https://conare.ai/marketplace/mcp/docmost-mcp). Inoffiziell, nicht stabil zugesagt.
- Docmost Webhooks: im öffentlichen Baum keine Datei mit "webhook" im Pfad (eigene Abfrage des [Repo-Baums](https://github.com/docmost/docmost)); der EE-Teil ist ein getrenntes Submodul und daher nicht geprüft.
- Docmost Einbettung: Iframes von anderen Ursprüngen standardmäßig blockiert, per Einstellung freigebbar — [Configuration](https://docmost.com/docs/self-hosting/configuration). Das betrifft Einbettung von Docmost; KI-Anbindung u. a. an OpenAI-kompatible und Ollama.
- BookStack: REST-API unter `/api/docs`; Theme-System (visuell und logisch über PHP-Events); "Custom HTML Head Content" erlaubt eigenes JS und CSS, nicht als stabil zugesagt — [Hacking BookStack](https://www.bookstackapp.com/docs/admin/hacking-bookstack/). Webhooks mit `text`-Feld, Slack-kompatibel, ohne Queue synchron — [Email & Webhooks](https://www.bookstackapp.com/docs/admin/email-webhooks/). MCP: kein offizieller gefunden.
- Nextcloud Collectives: OCS-API mit `openapi.json` — [GitHub](https://github.com/nextcloud/collectives).
- AFFiNE: kein offizieller MCP gefunden, Community-Server mit Token oder Cookie, auch für selbst gehostete Instanzen — [LobeHub](https://lobehub.com/de/mcp/dawncr0w-affine-mcp-server). Readme nennt weder API noch MCP — [GitHub](https://github.com/toeverything/AFFiNE).
- AppFlowy: MCP und KI optional genannt — [AppFlowy-SelfHost-Commercial](https://github.com/AppFlowy-IO/AppFlowy-SelfHost-Commercial).
- Anytype: Local API läuft "entirely on localhost" in der Desktop-App, MCP nur als Community-Ökosystem erwähnt — [Local API](https://doc.anytype.io/anytype/features/integrations/local-api.md).
- SiYuan: API-Doku und API-Token im Repo, Schlagwort mcp, aber keine Beschreibung — [GitHub](https://github.com/siyuan-note/siyuan); Community-MCP — [PyPI](https://pypi.org/user/leolulu/).
- Confluence: offizieller Rovo-MCP-Server unter mcp.atlassian.com, OAuth 2.1; API-Token für Headless nur, wenn Org-Admin das erlaubt — [Atlassian Support](https://support.atlassian.com/rovo/docs/atlassian-remote-mcp-server). Webhooks über App-Modul, Zustellung "best effort", Connect läuft aus; `comment_created` fehlt in der Confluence-Liste, Beispiel zeigt es aber — [Webhook-Modul](https://developer.atlassian.com/cloud/confluence/modules/webhook/). Entwickler melden 404 bei v2-Inline-Kommentaren — [Atlassian Community](https://community.developer.atlassian.com/t/confluence-rest-api-v2-doesnt-return-inline-comment-404-instead-v1-works-bug/86668).
- Coda: REST-API mit Zeilen, Tabellen, Automation-Auslöser; Schreiblimit 10 pro 6 s, Doc-Inhalte 5 pro 10 s — [API-Doku](https://docs.superhuman.com/developers/apis/v1). MCP nur als Community-Paket gefunden — [mcp-coda](https://pypi.org/project/mcp-coda/). Es erwähnt Webhooks und Button-Trigger als Anleitung.
- Obsidian: Headless nennt ausdrücklich Team-Vault auf einem Server und "agentische Tools" als Einsatz — [Obsidian Help](https://obsidian.md/help/headless) (Marketing-nah). Der Agent arbeitet dann auf Markdown-Dateien.
- Notara: REST-API `/api/v1` mit OpenAPI, API-Schlüssel, CLI — [GitHub](https://github.com/DnzzL/notara).

### Inferences
- Skizze für Outline: Webhook (`comments.create` oder `documents.update`) geht über Caddy an einen kleinen Python-Dienst, der einen Auftrag in `shared/auftraege/` legt; das Ergebnis schreibt der Agent per API zurück. Das passt zu "Claude denkt, Python handelt", weil Python mit einem begrenzten Agentenkonto schreibt. MCP wäre dabei optional, nicht nötig. Nicht erprobt.
- Ein Knopf in Outline müsste vermutlich als Text- oder Kommentar-Konvention laufen oder als Link in eine eigene Seite. Ein Plugin würde einen eigenen Build mit Wartungsaufwand bedeuten.
- Jeder dieser Wege schreibt ins Wiki. Ob das unter "nach außen handeln" fällt und durch `shared/freigabe/` muss, muss Jan entscheiden, wenn andere Gruppenmitglieder die Inhalte sehen.

### Gaps
- Nicht belegt, dass der MCP-Server von Outline in der selbst gehosteten Community Edition ohne Einschränkung läuft; nur Quellcode-Stellen gelesen, nicht ausgeführt.
- Eigene Seiten oder Knöpfe einbetten: Für Outline fand ich keine Herstellerdoku; das Repo enthält ein `iframely`-Plugin, Einzelheiten offen. Für Confluence (Forge) nicht geprüft.
- Webhooks von AFFiNE, SiYuan, Anytype und Notara: nichts gefunden.

## Datenschutz (Selbsthosting oder EU) gegenüber Notion, Export und Bindung

### Takeaway
Selbsthosting von Outline oder Docmost legt alle Inhalte auf den eigenen Server. Die Cloud von Outline steht dagegen in den USA, EU-Datenhaltung bei Confluence gibt es erst ab Standard. Am wenigsten Bindung haben Markdown-basierte Werkzeuge wie Obsidian; am stärksten bindet Coda.

### Cited Findings
- Outline Cloud: Server in den USA, Rechenzentren von AWS; TLS und AES-256 at rest — [Security](https://docs.getoutline.com/s/guide/doc/security-DlJBglbImQ).
- Outline Testphase: Nach 30 Tagen ohne Zahlung schreibgeschützt, Export bleibt möglich — [Pricing](https://www.getoutline.com/pricing). API kennt Import/Export — [Developers](https://www.getoutline.com/developers). Backups als eigene Doku-Seite — [Hosting](https://docs.getoutline.com/s/hosting).
- Docmost: "Your data never leaves your servers" (Marketing, gilt nur fürs Selbsthosting) — [Pricing](https://docmost.com/pricing). Telemetrie an, solange nicht `DISABLE_TELEMETRY=true` gesetzt — [Configuration](https://docmost.com/docs/self-hosting/configuration).
- Confluence: Datenresidenz für Standard, Premium, Enterprise; Free nicht genannt; EU = Frankfurt und Dublin, Deutschland = Frankfurt; Kontodaten nicht festlegbar — [Atlassian Support](https://support.atlassian.com/security-and-access-policies/docs/understand-data-residency/).
- Anytype: Selbsthosting nur als eigenes Netz — [any-sync-dockercompose](https://github.com/anyproto/any-sync-dockercompose).
- Obsidian Sync: Ende-zu-Ende-Verschlüsselung laut Herstellerseite (Marketing, nicht geprüft) — [Obsidian Help](https://obsidian.md/help/headless).
- Nextcloud: CVE-2026-45810, angemeldete Nutzer konnten fremde Dateikommentare lesen, behoben in 31.0.12 und 32.0.3 — [OSV](https://api.osv.dev/v1/vulns/CVE-2026-45810). Selbsthosting nimmt das Patchen nicht ab.

### Inferences
- Selbsthosting verschiebt die Verantwortung: Backups, Updates, Sicherheit liegen dann bei Jan. Bei Daten der Uni-Projektgruppe liegen die Inhalte dann bei Contabo als Hoster. Ob das reicht, ist eine Frage an die Gruppe oder die Uni.
- Solange ein Agent Claude nutzt, gehen die Inhalte, die er verarbeitet, weiter an Anthropic. Selbsthosting des Wikis ändert das nicht.
- Bindung: Outline-Export vermutlich als Markdown oder ähnliches. Das Format ist hier nicht belegt.

### Gaps
- Notions Datenstandort und AVV wurden hier nicht nachgelesen, ein direkter Vergleich fehlt also.
- Coda: Datenstandort und Exportformat nicht gefunden.
- Export von Docmost, AFFiNE, AppFlowy nicht geprüft.

## Welche zwei bis drei passen am ehesten, und was fehlt gegenüber Notion?

### Takeaway
1. Outline selbst gehostet: bester Treffer für Agenten, nutzt das vorhandene Node, kostet nichts. Haken: Postgres und Redis ohne root, Anmeldeanbieter (SMTP oder OIDC) und knapper Speicher.
2. Docmost Community: ähnlicher Betrieb, angenehme Lizenz, aber Agentenzugang nur über inoffiziellen Weg oder 720 USD im Jahr.
3. Confluence Standard oder Free: nur als Rückfallebene ohne Serverlast, mit offiziellem MCP, aber EU-Datenhaltung erst bezahlt und schwächerem Webhook-Weg. BookStack wäre die leichtere selbst gehostete Alternative, wenn Echtzeit und freie Verschachtelung nicht wichtig sind und PHP auf dem Server machbar ist.

### Cited Findings
- Outline: siehe oben — [API](https://www.getoutline.com/developers), [Changelog](https://www.getoutline.com/changelog), [Requirements](https://docs.getoutline.com/s/hosting/doc/requirements-ULdYnwi4wG).
- Docmost: siehe oben — [Pricing](https://docmost.com/pricing), [MCP](https://docmost.com/docs/user-guide/mcp).
- Confluence: siehe oben — [Rovo MCP](https://support.atlassian.com/rovo/docs/atlassian-remote-mcp-server), [Datenresidenz](https://support.atlassian.com/security-and-access-policies/docs/understand-data-residency/).
- Fehlend gegenüber Notion, belegt: Strukturierte Datenattribute sind bei Outline ein Enterprise-Merkmal — [Business + Enterprise](https://docs.getoutline.com/s/hosting/doc/business-enterprise-rv0715NxO3). Datenbanken mit Tabelle, Kanban und Kalender nennt unter den geprüften Selbsthost-Kandidaten Colanode ausdrücklich — [Colanode](https://github.com/colanode/colanode).

### Inferences
- Gegenüber Notion fehlen bei Outline und Docmost vermutlich Datenbanken mit Ansichten, native Knöpfe und Automationen, die Notion-Vorlagenwelt und die reifen Mobil-Apps. Für die Anforderung "Seiten, Kommentare, Agent schreibt zurück" dürfte das tragbar sein. Für Auftragslisten als Datenbank nicht: Die müssten Seiten plus Konvention oder die eigene Warteschlange sein.
- Was fehlt, könnte eine kleine eigene Seite hinter Caddy liefern. Das kostet RAM und schmilzt den Vorsprung gegenüber einem kompletten Eigenbau. Zu vergleichen mit dem Eigenbau-Strang der Recherche.
- Nicht empfohlen: AFFiNE und AppFlowy (Docker, RAM, bei AppFlowy Platzgrenze), Anytype (Docker, API nur am Desktop), SiYuan (laut Maintainer nicht für gleichzeitige Mehrbenutzung), Nextcloud (schwer für nur eine App, keine Kommentare an Textstellen), Coda (Bindung, kein offizieller MCP gefunden), Obsidian Sync (keine Echtzeit, keine Rollen, Beta-Headless, aber geringste Bindung), Notara (sehr jung, eine Person), Colanode (seit April 2026 kein Release, Docker-Image).
- Vor einer Entscheidung lohnt ein kurzer, gemessener Probelauf von Outline in Benutzerumgebung, nachdem Jan die Installation freigegeben hat.

### Gaps
- Kein Vergleichstest: Die Rangfolge beruht auf Doku und Quellcode, nicht auf Bedienung oder Messung.
- Wiki.js 3.0.2 (Release 02.11.2026, laut GitHub-API; AGPL), HedgeDoc, SilverBullet, XWiki und Trilium ([GitHub](https://github.com/TriliumNext/Trilium): persönliche Wissensdatenbank, keine Mehrbenutzer-Aussage) wurden nur angerissen. Wiki.js 3 wäre der interessanteste Nachprüfkandidat, die Requirements-Seite war nicht lesbar.
