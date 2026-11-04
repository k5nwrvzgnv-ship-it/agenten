# Notion reverse engineeren: private Schnittstellen (A) und Nachbau im eigenen Portal (B)

Stand: 05.11.2026. Nur öffentliche Quellen gelesen. Notion wurde nicht abgetastet, keine internen Endpunkte aufgerufen, nichts installiert. GitHub-Zahlen stammen aus der öffentlichen GitHub-API (Abruf 04.11.2026). Rechtliche Einordnung: keine Rechtsberatung.

Gesamturteil (Schlussfolgerung, siehe die Inferences unten): Für einen Einzelnutzer mit Python-Agenten ist Bedeutung A nicht klüger als die offizielle Anbindung. Bedeutung B ist in stark verkleinerter Form machbar (Blockmodell plus fertiger Editor, ohne Echtzeit und ohne Offline), aber nur sinnvoll, wenn das Portal ohnehin gebaut wird.

## A1: Was ist über die interne API öffentlich bekannt, wie gepflegt sind die Projekte, wie oft bricht es?

### Takeaway
Die interne API ist dokumentiert nur durch Notions Architektur-Blog und durch Gemeinschaftsprojekte. Sie bricht nachweisbar immer wieder. Die Projekte leben weiter, aber reaktiv, und das Schreiben scheint durch Notions CRDT-Umbau zusätzlich unter Druck zu stehen.

### Cited Findings
- Notion beschreibt selbst die internen Bausteine: `/saveTransactions` zum Schreiben, `loadPageChunk` zum Laden, `syncRecordValues` zum Nachladen, WebSocket-Abos über MessageStore — [Notion-Blog, 18.05.2021](https://www.notion.com/blog/data-model-behind-notion). Das ist Architekturbeschreibung, keine Schnittstellenzusage.
- Für `api/v3` fand die Suche keine offizielle Dokumentation, nur Gemeinschaftsprojekte — [Suchergebnis, Beispiel glama.ai](https://glama.ai/mcp/servers/kirvigen/notion-private-api-mcp).
- react-notion-x sagt über sich: "uses the unofficial Notion API (which is what all Notion apps use)". Für private Seiten nutzt es die Cookies `token_v2` und `notion_user_id`. Die README warnt nicht ausdrücklich vor Instabilität; Bild-URLs privater Seiten laufen ab; "Calendar"-Ansicht fehlt — [GitHub README](https://github.com/NotionX/react-notion-x).

Pflegezustand (Abruf 04.11.2026, [GitHub-API](https://api.github.com/repos/jamalex/notion-py)):

| Projekt | Zweck | Sterne | Letzter Push | Lizenz | Anmerkung |
|---|---|---|---|---|---|
| [jamalex/notion-py](https://github.com/jamalex/notion-py) | Python, lesen und schreiben | 4372 | 16.02.2026 | MIT | Nur vereinzelte Reparaturen, siehe unten |
| [NotionX/react-notion-x](https://github.com/NotionX/react-notion-x) (mit `notion-client`) | TypeScript, vor allem Darstellung | 5440 | 18.10.2026 | MIT | Aktiv |
| [splitbee/react-notion](https://github.com/splitbee/react-notion) | React-Darstellung | 3000 | 28.10.2024 | MIT | Seit zwei Jahren kein Push |
| splitbee/notion-api | Worker-Proxy | - | - | - | Unter dieser Adresse liefert die API 404; Verbleib nicht geklärt |
| [kirvigen/notion-private-api-mcp](https://glama.ai/mcp/servers/kirvigen/notion-private-api-mcp) | MCP auf `token_v2` | 4 | 01.06.2026 | MIT | Klein, warnt selbst deutlich |

Zum Vergleich offizielle SDKs: [makenotion/notion-sdk-js](https://github.com/makenotion/notion-sdk-js) (5678 Sterne, Push 04.11.2026), [ramnes/notion-sdk-py](https://github.com/ramnes/notion-sdk-py) (2196 Sterne, Push 04.11.2026).

Brüche, belegt:
- notion-py, Commit-Verlauf: 04.06.2024 "Updates to query logic to new schema", 17.06.2025 "Fix to pulling space data", 16.02.2026 "Update to Notion API v3 changes and bump to 0.1.0" — [GitHub-Commits](https://api.github.com/repos/jamalex/notion-py/commits?per_page=8). Paket `notion` 0.1.0 auf PyPI am 16.02.2026 — [PyPI](https://pypi.org/pypi/notion/json).
- notion-py, offene Issues: #407 (16.04.2026, also zwei Monate nach dem Reparatur-Release) `KeyError: 'space_view_pointers'`; #406 (18.08.2025) 500 bei `submitTransaction`; #405 (25.06.2025) "Space that has CRDT enabled should have crdt"; #392 (12/2023) HTTP 400 beim Laden einer Datenbank; #380 (11/2022) Frage, ob das Modul überhaupt noch funktioniert — [Issue-Liste](https://github.com/jamalex/notion-py/issues). Nur Titel und Datum gelesen.
- react-notion-x: "Failed to send .../api/v3/queryCollection request" (08.10.2025), "Fix undefined error due to nested value.value structure in Notion response" (09.02.2026), "Custom emojis are not properly loaded" (01.10.2026), offen "loadPageChank" (26.10.2025) — [GitHub-Suche](https://github.com/NotionX/react-notion-x/issues). Nur Titel gelesen, Ursache nicht geprüft.
- Ein notion-py-Fork schreibt, die automatische Aktualisierung von Notion nach Python sei kaputt und standardmäßig aus — [vzts/notion-py](https://github.com/vzts/notion-py), als Suchauszug.
- Notion überführt offline verfügbare Seiten dynamisch in ein neues Datenmodell: "pages that are marked as available offline are dynamically migrated to our new CRDT data model for conflict-resolution" — [Notion-Blog, 11.12.2025](https://notion.com/blog/how-we-made-notion-available-offline).

### Inferences
- Aus #405 und dem Offline-Artikel folgt als Verdacht: Der alte Schreibweg über Einzeltransaktionen passt zunehmend nicht mehr zu CRDT-Seiten. Lesen ist dadurch weniger betroffen als Schreiben. Für Agenten, die in Notion schreiben sollen, wäre das der kritische Pfad. Belegt ist nur die Fehlermeldung, nicht der Mechanismus.
- Muster bei notion-py: ein Reparaturschub pro Jahr, gefolgt von neuen Brüchen. Für einen Dienst, der täglich laufen soll, heißt das Ausfälle ohne Vorwarnung und Abhängigkeit vom Zeitbudget eines Einzelnen.
- react-notion-x ist gepflegt, ist aber vor allem ein Anzeigewerkzeug, also kein Ersatz für einen Schreibpfad.

### Gaps
- Keine belastbare Statistik zur Bruchhäufigkeit. Das Bild beruht auf Issue-Titeln und Commit-Nachrichten.
- Kein Beleg, wie weit die CRDT-Umstellung über Offline-Seiten hinaus reicht.
- Für den genannten Namen `notion-client` meint die Quelle das Paket aus react-notion-x. Das offizielle JS-SDK heißt ähnlich (`@notionhq/client`); bei Suchen leicht zu verwechseln.

## A2: Was bringt die interne API gegenüber der offiziellen konkret, was bleibt unmöglich?

### Takeaway
Echter Vorteil ist vor allem Bequemlichkeit: kein Einrichten einer Verbindung, kein Freigeben einzelner Seiten, Sicht auf alles, was das Konto sieht. Eigene Blöcke oder eine Agenten-Oberfläche in Notion liefert sie nicht. Die offizielle Seite hat 2026 deutlich aufgeholt.

### Cited Findings
- Vorteile laut Projekt: Anmeldung per Cookie statt Integration-Token, keine Freigabe einzelner Seiten, Zugriff auf alles, was das Konto sehen kann. Für Produktion und Mehrbenutzerbetrieb verweist es selbst auf das offizielle Notion-MCP — [glama.ai](https://glama.ai/mcp/servers/kirvigen/notion-private-api-mcp).
- Offizielle API meldet nicht unterstützte Blöcke als `"type": "unsupported"`, mit `block_type` etwa `form`, `button`, `drive`, ausdrücklich "informational only" und ohne Inhalt. `synced_block` lässt sich nicht aktualisieren; Template-Blöcke lassen sich seit 2023 nicht mehr anlegen; `table_width` ist nach dem Anlegen fest — [Notion-Referenz](https://developers.notion.com/reference/block).
- Offizielle Grenzen: 180 Anfragen pro Minute je Verbindung (600 auf Business/Enterprise), Datenquellen-Abfragen etwa 3/s, 2000 Zeichen je Rich-Text, 100 Elemente je Block-Array, höchstens 1000 Blöcke und 500 KB je Anfrage — [Request limits](https://developers.notion.com/reference/request-limits).
- Offizielle Neuerungen 2026: `heading_4` (30.03.), Tab-Blöcke (25.03.), Webhook-Ereignisse für Ansichten (19.03.), Personal Access Tokens und Workers im Developer-Portal (12.05.), HTML-Blöcke per API über Datei-Upload (03.07.), Webhook-Signaturprüfung im SDK (08.07.), Markdown-API fortlaufend (zuletzt 30.10.), MCP-Werkzeuge für Vorschlagsbearbeitung (27.10.) — [Changelog](https://developers.notion.com/page/changelog).
- Eigene Blöcke gibt es inzwischen offiziell, aber eingeschränkt: Custom Blocks sind laut Doku private Alpha, Zugang je Workspace, APIs können sich ohne Ankündigung ändern, die Doku bittet, sie nicht öffentlich zu diskutieren. Ein Block ist eine Web-App im sandboxed iframe auf eigener Origin, ohne Zugangsdaten, gebunden an einen Worker — [Custom Blocks Übersicht](https://developers.notion.com/custom-blocks/overview), [Sicherheit](https://developers.notion.com/custom-blocks/guides/security.md). "Definition creation remains in private alpha", bestehende Definitionen lassen sich aber platzieren — [Changelog, 30.09.2026](https://developers.notion.com/page/changelog).
- Workers: in der Beta kostenlos nur auf Business und Enterprise, etwa 0,0023 USD je Lauf, Webhooks als Alpha gekennzeichnet — [Notion-Hilfe](https://www.notion.com/help/understand-pricing-for-workers). Worker-Grenzen: [Limits](https://developers.notion.com/workers/reference/limits). Das Ende der Gratisphase ist widersprüchlich: die englische Hilfeseite nennt kein Datum, ein [spanischer Suchauszug](https://www.notion.com/es-es/help/understand-pricing-for-workers) nennt den 11.08.2026, ein [deutscher Drittanbieter-Guide](https://matthiasfrank.de/notion-workers-dev-day-2026/) den 15.10.2026.
- Echtzeit intern: Clients halten eine WebSocket-Verbindung zu MessageStore und laden veraltete Records nach — [Notion-Blog 2021](https://www.notion.com/blog/data-model-behind-notion). Offiziell gibt es stattdessen Webhooks.

Einordnung der Wunschliste (Schlussfolgerung, siehe Inferences):

| Wunsch | Private API | Offiziell |
|---|---|---|
| Inhalte von `form`, `button` usw. | Vermutlich sichtbar, da die App sie auch lädt; nicht geprüft | Nur Platzhalter |
| Lange Texte, große Schreibvorgänge | Grenzen unbekannt, Missbrauch riskiert Sperre | Dokumentierte Grenzen |
| Eigene Blöcke darstellen | Nein: Darstellung liegt in Notions Client | HTML-Blöcke, Custom Blocks (Alpha) |
| Agent in der Oberfläche | Nein, höchstens Schreiben als Konto | MCP, Kommentare, Vorschläge, Notion-eigene Custom Agents |
| Echtzeit-Ereignisse | Theoretisch, ohne gepflegte Bibliothek gefunden | Webhooks mit Verzögerung |
| Kein Einrichtungsaufwand | Ja, aber mit vollem Kontorecht | Einmalig Verbindung und Seitenfreigabe |

### Inferences
- Der meiste Mehrwert fällt für Jans Fall weg: Agenten müssen nicht alles sehen, was das Konto sieht. Seitenweise Freigabe ist für das Agentensystem ein Vorteil, nicht ein Nachteil.
- Eigene Blöcke sind über die private API nicht erreichbar, weil das Zeichnen im Notion-Client passiert. Unbekannte Blocktypen dort einzuschleusen, wäre kein stabiler Weg und ist hier auch nicht zu empfehlen.
- Grenzen wie 2000 Zeichen je Rich-Text sind lästig, aber durch Aufteilen in Python lösbar. Sie rechtfertigen keinen Wechsel.

### Gaps
- Kein öffentlicher Nachweis, was die interne API heute an Rate Limits oder Größen zulässt. Bewusst nicht ausprobiert.
- Keine gepflegte Python-Bibliothek gefunden, die das interne WebSocket nutzt.
- Die Details zu Custom Blocks stammen aus Suchauszügen der Doku; die Seiten selbst wurden nicht vollständig gelesen.

## A3: Was sagen die Bedingungen, wie ist die Rechtslage, welches Sperr- und Sicherheitsrisiko besteht?

### Takeaway
Die Vertragstexte verbieten Reverse Engineering und, je nach Dokument, automatisiertes Abgreifen. Sperrung ist ausdrücklich vorbehalten. Das deutsche Urheberrecht schützt Beobachten und Interoperabilität in engen Grenzen, löst aber das Vertrags- und Kontoproblem nicht. Größtes praktisches Risiko ist das Session-Token mit vollem Kontozugriff. Keine Rechtsberatung.

### Cited Findings
Wortlaut Master Subscription Agreement v.4, § 2.1 (für Geschäftskunden; PDF ohne Datum, [auf einem Cloudfront-EULA-Host](https://d7umqicpi7263.cloudfront.net/eula/3QkIRed56NURE2biK8-iR9WZUHjl261rslq5f-W45yA), nicht auf notion.com, also möglicherweise nicht die aktuelle Fassung):
- "(4) circumvent or disable any security or other technological features of the Services"
- "(5) reverse engineer, decompile, disassemble, or otherwise attempt to discover the source code, object code, or underlying structure, ideas, know-how, or algorithms related to the Services (except to the extent this restriction is prohibited by applicable law)"
- "(9) access the Services for the purpose of building a competitive product or service or copying its features or user interface"
- "(10) use the Services for evaluation, benchmarking, or other comparative analysis intended for publication without Notion's prior written consent"
- Rechtsfolge: "If we reasonably suspect that you or your Customer Data are in violation of the foregoing, we may investigate that violation and suspend or terminate your access to the Services."
- § 1.8: API-Zugang kann "with or without notice" geändert oder eingestellt werden, Developer Terms gehen bei Konflikt vor. § 13.6: Recht von Kalifornien, Gerichtsstand San Francisco County.

Weitere Dokumente, nur als Auszug und nicht wörtlich gesichert:
- Personal Use Terms § 2: Verbot von Dekompilieren und Reverse Engineering, auch der zugrunde liegenden Ideen und Algorithmen, sowie von Robotern, Spidern, Crawlern und manuellen Verfahren zum Extrahieren von Daten, außerdem von Überlastung und Überschreiten von Fair-Use-Grenzen. Eine Kopie der Seite ist als "Deprecated April 5, 2024" markiert, eine zweite nicht — [Personal Use Terms](https://notion.notion.site/Personal-Use-Terms-of-Service-00e4e5d0f2b9411cbee6493f15779500). Der Abruf der Seite lieferte nur "Notion", der Inhalt stammt aus dem Suchauszug.
- Developer Terms § 3.1: Verbot von Reverse Engineering der APIs oder Dienste (e), Scraping und Crawlern gegen die API (g), Umgehen von Sicherheit und Grenzen (b), Integrationen, die Notion ersetzen oder nachbilden (c, h), Training nicht personalisierter KI mit Integrationsdaten (k); § 3.2 nennt Teile der API Geschäftsgeheimnisse — [Developer Terms](https://notion.notion.site/Developer-Terms-ba4131408d0844e08330da2cbb225c20), ebenfalls Suchauszug. Zuletzt aktualisiert am 02.04.2026 — [Changelog](https://developers.notion.com/page/changelog).
- Vorsicht Verwechslung: Der HN-Thread "Notion's TOS makes using it for MCP illegal" (10.03.2025) zitiert "Notion Web Services Terms of Service" — [HN](https://news.ycombinator.com/item?id=43325133). Ein Dokument dieses Namens fand sich unter [support.getnotion.com](https://support.getnotion.com/hc/en-us/articles/29788117154455-Notion-Web-Services-Terms-of-Service), einer anderen Domain als notion.com. Vermutlich ein anderes Unternehmen; der Abruf schlug fehl, daher nicht bestätigt. Diese Quelle nicht Notion zuschreiben. Auch in Suchantworten wurde sie Notion zugeordnet.

Gesetz (Einordnung, keine Rechtsberatung):
- § 69d Abs. 3 UrhG: Wer zur Nutzung berechtigt ist, darf das Funktionieren des Programms beobachten, untersuchen und testen, um Ideen und Grundsätze zu ermitteln, sofern das im Rahmen erlaubter Handlungen wie Laden, Anzeigen, Ausführen geschieht — [§ 69d](https://www.gesetze-im-internet.de/urhg/__69d.html).
- § 69e UrhG (Dekompilierung): erlaubt Vervielfältigung oder Codeübersetzung, wenn für die Interoperabilität eines unabhängig geschaffenen Programms unerlässlich, nur durch Berechtigte, nur wenn die Informationen nicht ohne Weiteres zugänglich sind, nur für die nötigen Teile. Keine Weitergabe, keine anderen Zwecke, keine Nutzung für ein Programm mit im Wesentlichen ähnlicher Ausdrucksform — [§ 69e](https://www.gesetze-im-internet.de/urhg/__69e.html).
- § 69g Abs. 2 UrhG: Vertragsbestimmungen im Widerspruch zu § 69d Abs. 2, 3, 5, 7 und § 69e sind nichtig — [§ 69g](https://www.gesetze-im-internet.de/urhg/__69g.html). Die Klausel (5) im MSA enthält passend dazu den Vorbehalt "except to the extent this restriction is prohibited by applicable law".

Sperre und Token:
- Über tatsächliche Kontosperren wegen privater API-Nutzung fand ich keinen Bericht — [Suchergebnis](https://glama.ai/mcp/servers/kirvigen/notion-private-api-mcp). Fehlende Berichte sind kein Beleg für fehlendes Risiko.
- "Auth is your browser cookie (`token_v2`) — effectively your account password. Never commit it." sowie "Notion can change or break this API at any time, and using it may be against Notion's ToS." und "inherently fragile and not for production" — [glama.ai, Projektbeschreibung](https://glama.ai/mcp/servers/kirvigen/notion-private-api-mcp).
- Das Token endet mit der Sitzung (Abmelden, Passwortwechsel, lange Inaktivität) — [mcp.so](https://mcp.so/servers/notion-private-api-mcp). Ein 401 bei `loadUserContent` passt dazu, Ursache im Thread aber nicht belegt — [notion-graph-view #1](https://github.com/stevedsun/notion-graph-view/issues/1).
- Zum Vergleich: offizielle Verbindungen sehen nur freigegebene Seiten — [Notion: Secure API credentials](https://developers.notion.com/guides/get-started/handling-api-keys), Inhalt nur als Suchtreffer, nicht im Detail gelesen.

### Inferences (keine Rechtsberatung)
- §§ 69d, 69e betreffen Programmcode. Bei einem Clouddienst bleibt der Servercode ohnehin außer Reichweite. Der entscheidende Punkt ist vermutlich nicht das Urheberrecht, sondern der Vertrag: Dass ein Konto sich an den Bedingungen messen lassen muss, ändert § 69g nur für die dort genannten Fälle. Ein Verbot automatisierter Zugriffe oder die Kontosperre dürfte davon nicht erfasst sein.
- § 69e greift nur, wenn die Informationen nicht ohne Weiteres zugänglich sind und die Handlung unerlässlich ist. Da Notion eine dokumentierte API, Markdown-Endpunkte und MCP bietet, wird die Berufung darauf für übliche Agentenaufgaben schwach.
- Für einen Einzelnutzer ist nicht eine Klage das realistische Risiko, sondern Kontoverlust ohne Vorwarnung, mit allen Inhalten darin. Das steht in keinem Verhältnis zum Bequemlichkeitsgewinn.
- Das Token passt nicht zu den Hausregeln: Es wäre ein ungezieltes Vollrecht auf das ganze Konto auf einem Server, wenn auch in einer `.env` mit chmod 600. Ein Fehler in einem Agenten könnte alles ändern, und die Isolierung je Agent würde unterlaufen. Dazu käme Handarbeit: Nach Ablauf müsste Jan den Cookie aus dem Browser neu kopieren.
- Zwei-Faktor-Anmeldung schützt vermutlich nicht mehr, wenn eine laufende Sitzung kopiert wird. Allgemeines Prinzip, nicht Notion-spezifisch belegt.
- Klausel (9) ist auch für Bedeutung B lesenswert: Sie zielt auf Zugriff auf die Dienste zum Nachbau von Funktionen oder Oberfläche. Das Lesen öffentlicher Blogartikel ist etwas anderes als das Nachbilden der Oberfläche durch Untersuchen des Dienstes. Ein privates Portal mit einem offenen Editor aus eigenen Ideen dürfte unproblematisch sein. Wer Notion aber Bildschirm für Bildschirm abbildet, sollte das bedenken.

### Gaps
- Die aktuellen Bedingungen auf notion.com konnte ich nicht direkt lesen: [notion.com/notion/terms](https://www.notion.com/notion/terms) leitet auf app.notion.com weiter und ergab 404, die Notion-Seiten liefern ohne JavaScript nur "Notion". Wörtlich gesichert ist deshalb nur das MSA v.4, und das nur in einer undatierten Kopie. Vor jeder Entscheidung sollte Jan die aktuelle Fassung im Browser lesen. Welche Fassung für sein Konto gilt (Personal oder MSA), ist offen.
- Nicht recherchiert: Wirksamkeit dieser Klauseln gegenüber einem deutschen Verbraucher, Rechtswahl im Verbraucherfall, Strafrecht (etwa §§ 202a ff. StGB), § 95a UrhG, Rechtsprechung zu SaaS-Schnittstellen. Dafür wäre fachlicher Rat nötig.
- Keine offizielle Stellungnahme von Notion zur Nutzung der privaten API gefunden.

## B1: Wie ist Notion technisch aufgebaut, was ist einfach, was jahrelange Arbeit?

### Takeaway
Das Blockmodell selbst ist einfach und gut beschrieben. Der Aufwand steckt im Editor-Gefühl, im Konfliktverhalten, in Offline und in Datenbankansichten. Für Einzelnutzer mit Agenten fällt das meiste davon weg.

### Cited Findings
- Blockmodell: "Everything you see in Notion is a block." Jeder Block hat UUID, Typ, Properties, Inhaltsliste von Kind-IDs und Parent-Verweis. Typwechsel ändern nur den Typ, Properties bleiben erhalten. Einrücken ist eine Strukturänderung — [Notion-Blog, Jake Teton-Landis, 18.05.2021](https://www.notion.com/blog/data-model-behind-notion).
- Rechte: Blöcke erben von Vorfahren; der Parent-Verweis dient dafür als Aufwärtszeiger — ebenda.
- Sync: Aktionen werden zu Transaktionen gebündelt und alles oder nichts angenommen. Der Client wendet sie sofort lokal an und legt sie in eine Warteschlange; der Server prüft auf einer Kopie Rechte und Konsistenz, speichert und benachrichtigt MessageStore — ebenda.
- Offline: Der frühere SQLite-Cache war nur "best-effort". Für Offline kam eine persistente Schicht mit Wald aus Offline-Bäumen (Tabellen `offline_page`, `offline_action`), Push pro Seite statt Polling, Zeitstempelvergleich und CRDT für Konflikte. Automatischer Download ist auf etwa 50 Seiten je Ansicht begrenzt. Der Artikel nennt Offline die jahrelang meistgewünschte Funktion — [Notion-Blog, Raymond Xu, 11.12.2025](https://notion.com/blog/how-we-made-notion-available-offline). Laut einer Dritt-Quelle startete v1 im August 2025 — [Thrive Culture Media](https://thrive-culture-media.super.site/articles/how-notion-shipped-offline-mode-and-why-it-was-not-the-easy-fix-everyone-thinks).
- Ein Dienstleister nennt die Sync-Engine die Schicht, die sich "cannot be faked with a good UI"; dazu die Rechtematrix mit Vererbung und Audit-Logs. Schätzung: Editor 5 bis 7 Wochen, Sync 6 bis 8 Wochen, Co-Editing +20.000 bis 35.000 USD — [RaftLabs, 12.10.2026](https://www.raftlabs.com/blog/how-to-build-productivity-app-like-notion). Verkäufer-Zahlen ohne Beleg.
- Andere Schätzungen: 9 bis 14 Monate mit vier Entwicklern für das Ganze, 8 bis 12 Wochen für den Block-Editor, oder 3 bis 4 Wochen mit Tiptap gegenüber 6 bis 8 auf reinem ProseMirror; die Datenbank-Engine und der CRDT-Teil seien die größten Kostentreiber — [RaftLabs](https://www.raftlabs.com/blog/build-app-like-notion), [RapidDevelopers](https://rapidevelopers.com/clone/notion). Nur Suchauszug, Zuordnung der Zahlen zur jeweiligen Seite nicht geprüft. Beide verkaufen Entwicklung.
- Technikvorschlag aus einem Systemdesign-Text: zeichengenaues CRDT nur innerhalb eines Blocks, Blockoperationen (einfügen, löschen, verschieben) gröber — [techinterview.org](https://www.techinterview.org/post/3233474953/frontend-system-design-notion-block-editor/).

Einordnung des Aufwands (Schlussfolgerung):

| Teil | Für das eigene Portal | Einschätzung |
|---|---|---|
| Blockmodell, Baum, Speichern | Nötig | Einfach, Tage |
| Anzeige fertiger Blöcke | Nötig | Einfach |
| Bearbeiten mit Slash-Menü, Ziehen | Falls gewünscht | Mit Baustein gut machbar, von Hand sehr teuer |
| Agent und Mensch gleichzeitig | Selten | Reicht meist Versionsprüfung, sonst Yjs |
| Datenbankansichten, Formeln, Relationen | Verlockend | Groß, nur als feste Ansichten für eigene Daten sinnvoll |
| Rechtematrix | Einzelnutzer: nein | Entfällt weitgehend |
| Offline, Mobil, Skalierung | Nein | Mehrjährig bei Notion, nicht anfangen |

### Inferences
- Agenten brauchen gar nicht die Editor-Oberfläche. Sie schreiben auf dem Server strukturierte Blöcke. Damit ist das Schwere an Notion (viele gleichzeitige Tipper, Offline) für diesen Fall eigentlich nicht das Problem, das gelöst werden muss.
- Das Transaktionsmuster aus dem 2021er-Artikel (Operation, Prüfung auf Kopie, alles oder nichts) lässt sich einfach in Python übernehmen und passt zu Jans Grundsatz "Claude denkt, Python handelt".

### Gaps
- Keine Zahlen von Notion selbst zu Teamgröße oder Dauer.
- Der Datenmodell-Artikel ist von 2021; wie viel davon heute gilt, ist nur teilweise belegt.

## B2: Welche Bausteine gibt es, was bekäme ein kleiner Python-Server damit realistisch?

### Takeaway
Es gibt reife Bausteine. BlockNote kommt dem Notion-Gefühl am nächsten, Tiptap gibt mehr Kontrolle, und Yjs lässt sich dank pycrdt auch an Python anschließen. Alle Editoren sind aber JavaScript: Das eigene Portal bekäme damit erstmals einen Frontend-Build.

### Cited Findings

Stand GitHub-API 04.11.2026:

| Baustein | Sterne | Letzter Push | Lizenz | Hinweise |
|---|---|---|---|---|
| [BlockNote](https://github.com/TypeCellOS/BlockNote) | 10353 | 04.11.2026 | Kern MPL-2.0 | Fertige Blöcke, Slash-Menü, Ziehen, Echtzeit, Kommentare im freien Plan. XL-Pakete (KI, mehrspaltig, Export PDF/DOCX/ODT/Mail) GPL-3.0 oder kommerziell, 195 USD/Monat — [Preise](https://www.blocknotejs.org/pricing). Aufgebaut auf ProseMirror und Tiptap — [ProseMirror-Forum](https://discuss.prosemirror.net/t/blocknote-open-source-block-based-notion-style-editor-on-top-of-prosemirror/4898) |
| [Tiptap](https://github.com/ueberdosis/tiptap) | 38960 | 04.11.2026 | MIT | Editor frei, Plattform ab 49 USD/Monat. Das fertige Notion-Muster braucht für Produktion mindestens den Start-Plan — [Preise](https://tiptap.dev/pricing), [Doku](https://tiptap.dev/docs/ui-components/templates/notion-like-editor). Ohne Styling, Kenntnisse in ProseMirror-Konzepten nötig — [Velt, Anbieter](https://velt.dev/blog/blocknote-collaborative-editor-guide) |
| [Hocuspocus](https://github.com/ueberdosis/hocuspocus) | 2646 | 03.11.2026 | MIT | Yjs-Server in Node.js, offener Teil neben Tiptap |
| ProseMirror | [view: 2037](https://github.com/ProseMirror/prosemirror-view) | 01.04.2026 | MIT | Fundament. Das Repo `prosemirror-view` ist auf GitHub als archiviert markiert; Grund nicht geprüft, daher keine Aussage zum Projekt ableiten |
| [Lexical](https://github.com/meta/lexical) | 23997 | 04.11.2026 | MIT | Von Meta, jetzt unter `meta/lexical`; Sync über `@lexical/yjs` — [Vergleich](https://liveblocks.io/blog/which-rich-text-editor-framework-should-you-choose-in-2025) |
| [Plate](https://github.com/udecode/plate) | 16689 | 04.11.2026 | MIT-Badge | Auf Slate, React-Komponenten. Notion-Vorlage auf pro.platejs.org, Bedingungen nicht geprüft |
| [Editor.js](https://github.com/codex-team/editor.js) | 31996 | 01.11.2026 | Apache-2.0 | Block-Editor, 702 offene Issues und PRs |
| [Yjs](https://github.com/yjs/yjs) | 23022 | 02.11.2026 | MIT ([Lizenzdatei](https://raw.githubusercontent.com/yjs/yjs/HEAD/LICENSE)) | CRDT-Standard. Braucht ein Backend zum Speichern — [Liveblocks](https://liveblocks.io/blog/which-rich-text-editor-framework-should-you-choose-in-2025) |
| [pycrdt](https://github.com/y-crdt/pycrdt) | 208 | 04.11.2026 | MIT | Python-Anbindung an den Yjs-Kern (y-crdt) |
| [pycrdt-websocket](https://github.com/y-crdt/pycrdt-websocket) | 50 | 02.11.2026 | MIT | "Python equivalent to y-websocket" — [Jupyter-Issue](https://www.github.com/jupyterlab/jupyter-collaboration/issues/247). Release 0.16.6 am 02.11.2026 — [PyPI](https://pypi.org/pypi/pycrdt-websocket/json). Älteres `ypy-websocket` steht bei 0.12.4 — [PyPI](https://pypi.org/project/ypy-websocket) |

Fertige Apps statt Baukasten: [AppFlowy](https://github.com/AppFlowy-IO/AppFlowy) (78195 Sterne, AGPL-3.0), [AFFiNE](https://github.com/toeverything/AFFiNE) (74224 Sterne, Lizenz nicht von der API erkannt), [Outline](https://github.com/outline/outline) (41170, Lizenz nicht erkannt), [Docmost](https://github.com/docmost/docmost) (22225, AGPL-3.0). Alle am 02. bis 04.11.2026 gepflegt. Nicht näher geprüft.

Hinweis: Die API zeigt für BlockNote, Plate und Yjs die Lizenz als `NOASSERTION`. Bei Yjs bestätigt die Lizenzdatei MIT, bei BlockNote die Preisseite MPL-2.0, bei Plate nur das README-Badge. Ein Vergleichstext aus der Suche nannte BlockNote "MIT-ish" (welcher genau, ist nicht gesichert, Kandidaten: [weaver-docs](https://weaver-docs.pages.dev/docs/comparison), [starterdocs](https://starterdocs.js.org/docs/comparisons/editors)). Das widerspricht der Anbieterseite, die gilt.

Zwei Bewertungsquellen sind Anbieter mit eigenem Interesse (Liveblocks, Velt) oder älter als 2026.

### Inferences
Realistisch für einen kleinen Python-Server (eigene Einschätzung, keine Messung, Zeiten grob):
- Stufe 1, ohne Editor: Blöcke als JSON, Python schreibt, Portal zeigt an. Agenten erzeugen Blöcke direkt. Tage. Keine neuen Pakete nötig. Vermutlich der größte Nutzen je Aufwand.
- Stufe 2, Editor: BlockNote im Portal, Speichern als JSON per HTTP mit Versionsprüfung. Etwa ein bis zwei Wochen, weil Frontend-Build, Blockschema und Abgleich mit dem Agenten-Schema dazukommen. Bedarf Jans Okay für Node und npm, da es den Grundsatz "möglichst Bordmittel" verlässt. Der Export-Teil (XL) ist vermutlich unnötig, weil `shared/renderer/` schon docx, pptx und PDF erzeugt.
- Stufe 3, gleichzeitiges Bearbeiten: pycrdt plus pycrdt-websocket, damit ein Agent live in ein offenes Dokument schreiben kann. Technisch reizvoll und ohne Node-Server möglich, aber mit kleinem Projekt (50 Sterne) und zusätzlichem Dauerdienst auf einem Server mit 7,8 GB RAM. Erst bei echtem Bedarf.
- Lizenz für den Privatgebrauch: MPL-2.0 ist unkritisch, solange der BlockNote-Quelltext nicht verändert wird oder Änderungen offengelegt werden. Die GPL-Pakete nur bei klarem Bedarf prüfen.
- Stolperstein: Der Schreibpfad der Agenten und das Schema des Editors müssen zusammenpassen. Wer Blöcke frei erzeugt, die der Editor nicht kennt, baut dieselbe Bruchstelle wie bei Notion, nur im eigenen Haus. Dafür braucht es dann einen getesteten Prüfer in Python.

### Gaps
- BlockNotes Speicherformat und JSON-Stabilität zwischen Versionen nicht in den Quellen geprüft.
- Plates Yjs-Doku war nicht abrufbar (HTTP 500), Yjs-Unterstützung daher nicht belegt. Für Editor.js nichts Belastbares zu Echtzeit gefunden.
- Kein Erfahrungsbericht zur Kombination pycrdt-websocket und BlockNote gefunden.
- Ob Jans Portal eine Build-Kette verträgt, ist hier nicht geprüft.

## B3: Erfahrungsberichte von Teams und Einzelnen

### Takeaway
Echte Nachberichte sind selten. Die vorhandenen Belege zeigen dasselbe Muster: Ein Editor ist schnell gezeigt, Fertigwerden dauert Jahre. Wer das Ziel eng hält, kommt ans Ziel. Die Belegbasis ist dünn.

### Cited Findings
- Lightwave, Einzelentwickler: etwa 3,5 Jahre, über 80.000 Zeilen, handgeschriebenes JavaScript, eigene Cursor- und Auswahllogik statt `contenteditable`, Laravel, MySQL, Redis, IndexedDB. Selbst nach dieser Zeit laut Autor noch Stresstest statt Start, fehlende Tastenkürzel und Barrierefreiheit, nur Desktop. Kostenpflichtiges Produkt geplant, also Eigeninteresse — [HN Showcase, 15.02.2026](https://www.hnshowcase.com/post/47027463/lightwave-real-time-notes-app-3-5-years-of-hand-rolled-javas).
- Ein Schreibwerkzeug mit eigenem Block-Editor, in Entwicklung seit 2019. In der Diskussion Widerspruch dagegen, Notiz-Apps als Notion-Ersatz zu bezeichnen — [Show HN](https://silkenweb.netlify.app/examples/hackernews-clone/item/44317242), Spiegel, nur Auszug gelesen.
- BlockNote-Gründung 2022: Der Autor wollte ausdrücklich einen Editor "on par with Notion's editor", aber nicht das ganze Produkt nachbauen, und ließ Datenbanken und Tabellen weg — [HN](https://hn.jakechampion.name/item/32764493), Spiegel, nur Auszug. BlockNote ist heute mit über 10.000 Sternen gepflegt, siehe B2.
- Lernprojekte: ein Bericht nennt als Lernstoff Cursor- und Auswahlverwaltung, Block- gegenüber Inline-Modell, Tastaturbedienung — [dev.to](https://dev.to/oathanrex/building-a-notion-style-editor-from-scratch-with-modern-web-tech-1288). Ein anderer baute einen leichten Editor in rund einer Woche mit Svelte — [SlashNote](https://www.github.com/umairrsyedd/SlashNote). Beide zeigen Machbarkeit eines Prototyps, nicht Dauerbetrieb.
- Verkäufer-Zahlen zu Monaten und Kosten siehe B1. Als Erfahrungsbericht nicht zu werten.

### Inferences
- Die Spannweite (eine Woche bis 3,5 Jahre) beschreibt vor allem das Ziel: leichter Editor oder Produkt. Für ein persönliches Portal zählt nur das untere Ende, solange die Versuchung "noch eine Notion-Funktion" kontrolliert wird.
- Die Berichte stützen, keinen Editor von Grund auf zu schreiben, sondern einen Baustein zu nehmen, und Datenbanken gezielt wegzulassen.

### Gaps
- Keinen ehrlichen Nachbericht eines Teams gefunden, das einen großen Notion-Klon gebaut und seine Fehler benannt hat. Mögliche Quellen wären Blogs von AppFlowy, AFFiNE, Outline oder Docmost; nicht geprüft.
- Kein Bericht eines Einzelnutzers, der privat von Notion auf einen Eigenbau mit Agenten gewechselt ist und das nach einem Jahr bewertet.
