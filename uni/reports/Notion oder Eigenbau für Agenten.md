# Notion anbinden, Kern behalten, Nachbau lassen

**Frage 1: Die offizielle Verknüpfung ist der schlaueste Weg zu Notion, aber noch nicht bewiesen der schlaueste Weg insgesamt. Frage 2: Reverse Engineering ist nicht schlauer, weder über private Schnittstellen noch als Nachbau von Notions Editor.** Private Schnittstellen bringen Jan fast nur Bequemlichkeit und kosten Stabilität, Kontosicherheit und womöglich das Konto. Der Nachbau löst ein Problem, das Jan nicht hat, denn sein Plan behält Word und will keinen Web-Editor. Meine Empfehlung: Fremdes Werkzeug für das, was Dokumentwerkzeuge als Standard mitbringen dürften (Ebenen, Kommentare, Konten, Überblick), eigener Code nur für die Agentenschicht (Aufträge, Fassungskette, Belegprüfung, Kosten, Lernen), Daten bleiben auf dem Server. Damit schützt sich Jan genau vor seiner Sorge, Schlechteres als Vorhandenes zu bauen, ohne das wegzuwerfen, was es nirgends fertig gibt. Der freigegebene Notion-Test bleibt, klärt so aber nicht die Frage, auf die das Portal wartet: Kommentare und Felix und Henri sind ausgeklammert. Davor gehört deshalb ein Handversuch ohne Code. Outline ist der ernsthafte Rückfallweg, vor allem wenn Uni-Inhalte nicht in die USA dürfen.

**Kein Werkzeug wurde benutzt, installiert oder getestet.** Notion, Outline und alle anderen sind nur aus Doku, Quellcode, Foren und Repo-Notizen beurteilt, teils über automatische Zusammenfassungen und Suchauszüge. "Belegt" heißt unten: steht in einer Quelle, nicht: selbst gesehen. Keine Rechtsberatung.

## Ein eigener Agent als echter Notion-Teilnehmer ist heute nicht planbar

**Belegt.** Genau das Gewünschte heißt External Agents API: Selbstgebaute Agenten sollen "native workspace participants" werden ([Notion-Blog](https://www.notion.com/blog/introducing-developer-platform)). Es gibt aber nur eine Warteliste und keine öffentliche technische Doku ([Hilfe](https://www.notion.com/help/what-is-the-notion-developer-platform), [Doku-Index](https://developers.notion.com/llms.txt)). Die Agent APIs, seit 02.11.2026 allgemein verfügbar, gehen in die Gegenrichtung: Eigene Apps rufen Notions Agenten auf ([Changelog](https://developers.notion.com/page/changelog)).

| Weg heute | Stand | Haken für Jan |
|---|---|---|
| Bot plus Kommentare (eigene Verbindung, API = dokumentierte Schnittstelle) | Verfügbar | Wirkt wie Kommentar-Bot. Neue Kommentare an markierten Textstellen und das Abrufen gelöster Kommentare gehen nicht ([Doku](https://developers.notion.com/guides/data-apis/working-with-comments.md)) |
| Notions Custom Agent ruft den eigenen Server als Werkzeug | Beta, Business nötig | Notions Modell und Credits sitzen davor ([Hilfe](https://www.notion.com/help/custom-agents)) |
| Claude-Agent in Notion | Beta, Business und Enterprise | Nicht Jans Agent, "Using your own Anthropic account isn't possible" ([Hilfe](https://www.notion.com/help/use-claude-agents-in-notion)) |
| External Agents API | Warteliste | Technik, Preis und Aufnahme unbekannt |

Webhooks (Notion meldet Änderungen aktiv an den Server) brauchen eine öffentliche HTTPS-Adresse und liefern nur IDs, keinen Inhalt ([Webhooks](https://developers.notion.com/reference/webhooks), [Zustellung](https://developers.notion.com/reference/webhooks-events-delivery.md)).

**Schlussfolgerung.** Bis die External Agents API offen ist, bleibt der Bot der einzige Weg, der "Claude denkt, Python handelt" und Jans Kontingent erhält. Eleganter als Kommentar und Status wird es offiziell vorerst nicht. Jan kann sich auf die Warteliste setzen; planen sollte er damit nicht.

## Private Schnittstellen bringen Bequemlichkeit, keine neuen Fähigkeiten

**Belegt.** Die interne Schnittstelle von Notion (Reverse Engineering heißt hier: abschauen, wie die App intern mit dem Server spricht) ist nicht offiziell dokumentiert. Die Python-Bibliothek notion-py brauchte Reparaturen im Juni 2024, Juni 2025 und Februar 2026 und hatte zwei Monate nach der letzten schon den nächsten offenen Fehler ([Commits](https://api.github.com/repos/jamalex/notion-py/commits?per_page=8), [Issues](https://github.com/jamalex/notion-py/issues)). Ein Issue-Titel nennt Notions neues Datenmodell (CRDT, Verfahren zum Zusammenführen gleichzeitiger Änderungen) als Fehlerquelle beim Schreiben; der Mechanismus ist nicht belegt. Der genannte Vorteil: Anmeldung per Browser-Cookie, keine Freigabe einzelner Seiten, Sicht auf alles im Konto. Dasselbe Projekt warnt: "effectively your account password", "not for production" ([Projektbeschreibung](https://glama.ai/mcp/servers/kirvigen/notion-private-api-mcp)). Das Master Subscription Agreement verbietet Reverse Engineering "except to the extent this restriction is prohibited by applicable law" und behält Sperrung vor ([MSA v.4, undatierte Kopie](https://d7umqicpi7263.cloudfront.net/eula/3QkIRed56NURE2biK8-iR9WZUHjl261rslq5f-W45yA)). §§ 69d und 69e UrhG erlauben in engen Grenzen Beobachten und Interoperabilität ([§ 69d](https://www.gesetze-im-internet.de/urhg/__69d.html), [§ 69e](https://www.gesetze-im-internet.de/urhg/__69e.html)). Berichte über tatsächliche Sperren wurden nicht gefunden, was kein Beleg gegen das Risiko ist.

**Schlussfolgerung.** Der Hauptvorteil ist für Jan ein Nachteil: Die freigegebene Internal Connection sieht nur die Test-Datenbank, das Cookie sähe alles und unterliefe die Isolation je Agent. Eigene Blöcke oder eine Agenten-Oberfläche liefert die private Schnittstelle auch nicht, weil Notions App die Darstellung bestimmt. Das realistische Risiko ist nicht die Klage, sondern Kontoverlust und unangekündigte Brüche. Das steht in keinem Verhältnis zum Gewinn.

Beim Nachbau trennt sich Muster von Produkt. **Belegt:** Das Blockmodell ist einfach und von Notion selbst beschrieben ([Notion-Blog 2021](https://www.notion.com/blog/data-model-behind-notion)). Ein Einzelentwickler berichtet dagegen 3,5 Jahre und über 80.000 Zeilen am eigenen Editor, noch ohne Start, mit eigenem kommerziellem Interesse ([HN Showcase](https://www.hnshowcase.com/post/47027463/lightwave-real-time-notes-app-3-5-years-of-hand-rolled-javas)). Fertige Bausteine wie [BlockNote](https://github.com/TypeCellOS/BlockNote) sind gepflegt. **Schlussfolgerung:** Muster abschauen ist in Ordnung (Baum, Brotkrumen, alles-oder-nichts-Änderungen), einen Editor bauen nicht. Jan hat ihn abgelehnt ([webapp-plan.md:154, 230](../webapp-plan.md)), und die Agenten brauchen ihn nicht. Klausel 9 des MSA betrifft Zugriff auf den Dienst, um Funktionen oder Oberfläche zu kopieren; Bildschirm-für-Bildschirm-Nachbau wäre also auch deshalb unklug.

Notions eigene Blöcke (Custom Blocks) sind laut Doku private Alpha und keine heutige Option. Die [Doku](https://developers.notion.com/custom-blocks/overview) bittet, das Thema nicht öffentlich zu diskutieren. Darum steht hier nur dieser Absatz, und vor einer öffentlichen Weitergabe dieses Berichts sollte er entfallen.

## Das Portal wird kleiner, nicht abgeschafft

**Belegt.** Das Portal hat rund 5.200 Zeilen und entstand an einem Tag, Lias App rund 10.600 Zeilen ([Messung in anforderungen.md](../research_notes/Notion%20oder%20Eigenbau%20für%20Agenten/anforderungen.md)). Jan nannte es "furchtbar", zu viel Information, keine Hierarchie ([uni/STATUS.md:437](../STATUS.md)). Am 04.11. waren keine Karte bewertet und keine Übung ausgewertet. Auch Eigenbau fällt aus: Eine Vorlagenänderung legte Lias App rund 14 Minuten lahm, ohne dass `pruefen.sh` es bemerkte ([shared/webapp/STATUS.md:322-324](../../shared/webapp/STATUS.md)).

**Schlussfolgerung.** "Behalten" heißt unten: Dafür fand sich nichts Fertiges mit Anschluss an die Agenten. Bewährt ist es damit nicht.

| Teil von `uni/portal` | Empfehlung | Grund |
|---|---|---|
| Ebenen und freie Reiter (Schritt 4) | Nicht bauen, Vorhandenes nehmen | Standard in Dokumentwerkzeugen, und hier setzte Jans Kritik an |
| Personen und drei Caddy-Konten, Rechte, Aktivitäts-Überblick | Nicht bauen, Vorhandenes nehmen | Standard, im Portal noch gar nicht gebaut |
| Fassungsvergleich | Vorerst nicht bauen | Bisher nur Wunsch, kein belegter Fall; Notions Verlauf hilft bei Agenten-Dateien nicht |
| Rückmeldung zum Exposé (Text oder kommentierte Datei wird Auftrag in der Kette) | Behalten | Einziger gebauter Kommentarweg, passt zur Praxis (17 Kommentare von Felix und Henri in der Datei), Exposé ist im Test ausgeschlossen |
| Fassungen, Renderer-Ausgabe als Dateien auf dem Server | Behalten, bleibt maßgeblich | Notion-Verlauf endet bei 7, 30 oder 90 Tagen ([Preise](https://www.notion.com/pricing)) |
| Recherche-Daten (Aussage, Status, Beleg, Zitatprüfung) | Behalten; Ansicht nicht ausbauen | Dieser Beleg-Mechanismus ist Jans Eigenheit. Die heutige Ansicht mit 16.635 Wörtern ist unübersichtlich, gehört aber erst nach dem Test umgebaut |
| Recherche-Start, Nachfrage | Noch nicht bauen | Logik gehört auf den Server, der Knopf kann in Notion liegen, falls der Test trägt |
| Karten mit FSRS, Probeprüfung mit Rubrik | Behalten, erst nutzen, nicht erweitern | Passt in kein Dokumentwerkzeug; als HTML-Block wäre es wieder Eigenbau |
| Laufstand, Warten, Kosten | Behalten | Das fehlende Lebenszeichen ist ein belegtes Problem ([webapp-plan.md:50](../webapp-plan.md)), Notion kennt Jans Warteschlange nicht |
| Schriftverkehr-Auszug | Behalten, nie spiegeln | Mailinhalte Dritter, keine Inhalte für Notion |

Eine Lücke bleibt: Die Notizen prüfen keine fertige Lernsoftware. Für Karten stellt sich Jans Frage genauso; Anki wäre der naheliegende Kandidat (meine Anregung, in den Notizen nicht untersucht). Lias App und Lias Daten sind von alldem nicht betroffen: Eine Entscheidung für ihre Daten in einem Fremdwerkzeug gibt es nicht, und Schülerdaten gehören ohne Klärung nicht in einen Plus- oder Business-Workspace. Notion speichert dort standardmäßig in den USA, EU-Speicherung gibt es nur bei Enterprise ([Datenresidenz](https://www.notion.com/help/data-residency)).

## Der Notion-Test klärt bisher nicht, worauf das Portal wartet

**Belegt.** Portal-Schritt 4 wartet auf den Test, weil er klären soll, "ob Notion die Ebenen und die gemeinsame Arbeit übernimmt" ([portal-oberflaeche.md:6](../portal-oberflaeche.md)). Der Testplan enthält aber nur eine Datenbank "Aufträge" und schließt Kommentare an den Agenten sowie Felix und Henri aus ([STATUS.md:131, 141](../../STATUS.md)). Die häufigste belegte Aufgabe ist "der agent schreibt und wir kommentieren", am Exposé ([portal-oberflaeche.md:26-35](../portal-oberflaeche.md)); genau das Exposé ist ausgeschlossen. Die Regelausnahme aus dem Plan steht noch nicht in CLAUDE.md.

**Schlussfolgerung und Empfehlung.** Den Test nicht verwerfen und die Brücke nicht vergrößern. Der Entwurf ist technisch richtig: Timer statt Webhook erspart die öffentliche Adresse, die Internal Connection begrenzt den Schaden, der Server bleibt maßgeblich, Telegram bleibt die Freigabe. Vorschalten würde ich einen Handversuch ohne Code, mit unkritischen Inhalten, geschätzt ein Abend: Jan legt seine Ebenen in seinen eigenen Worten an, lädt mehrere Fassungen derselben unkritischen Datei hoch, liest einen langen Text und kommentiert ihn. Scheitert schon das, spart Jan die Brücke. Danach wird die Brücke wie freigegeben gebaut, mit zwei Vorsichtsregeln: Abfragen auf Vollständigkeit prüfen, weil die API laut Statusspiegel im April unvollständige Ergebnisse ohne Fehlermeldung lieferte ([IsDown](https://isdown.app/status/notion/incidents/573978-notion-api-returning-incomplete-results)), und Störungen dürfen keine Aufträge verlieren. Kommentare an den Agenten kommen höchstens als zweite Stufe, nach Jans Urteil und mit neuer Zusammenfassung. Schritt 4 bleibt bis dahin pausiert, Prüfungsseite und Lernen laufen weiter. Abnahme bleibt Jans Eindruck, wie von ihm festgelegt.

Kosten für später: Plus 9,50 €, Business 19,50 € je Mitglied, für drei also 28,50 € oder 58,50 € im Monat, ob bei Jahreszahlung ist offen ([Preise](https://www.notion.com/pricing)). Gäste sind kostenlos und können je Seite bearbeiten ([Hilfe](https://www.notion.com/help/add-members-admins-guests-and-groups)). Für die Bot-Lösung reicht laut Einordnung Plus; ein Sitz plus zwei Gäste wäre der billigste Versuch, wenn die Gastrechte reichen. Die genauen Gastgrenzen sind nicht geklärt.

## Outline schlägt Notion beim Agentenanschluss, verliert bei Aufträgen und Betrieb

**Belegt.** Outline ist ein Wiki mit API für Dokumente und Kommentare, signierten Webhooks und eingebautem MCP (MCP ist ein Standard, über den KI-Werkzeuge Programme ansprechen), inklusive Inline-Kommentaren ([API](https://www.getoutline.com/developers), [Quellcode](https://raw.githubusercontent.com/outline/outline/main/plugins/webhooks/server/tasks/DeliverWebhookTask.ts), [Changelog](https://www.getoutline.com/changelog)). Es gibt einen Notion-Import ([GitHub](https://github.com/outline/outline)). Die Lizenz BSL erlaubt interne Nutzung, verbietet aber den Betrieb als Dienst für andere ([Lizenz](https://raw.githubusercontent.com/outline/outline/main/LICENSE)).

| | Notion | Outline selbst gehostet | Outline Cloud |
|---|---|---|---|
| Kosten für 3 | 0 bis 58,50 € im Monat | 0 | 10 USD im Monat bis 10 Mitglieder ([Preise](https://www.getoutline.com/pricing)) |
| Daten | USA standardmäßig | Eigener Server (Contabo) | USA ([Security](https://docs.getoutline.com/s/guide/doc/security-DlJBglbImQ)) |
| Serverlast | Keine | Postgres, Redis (Datenbank und Zwischenspeicher), Anmeldedienst Pflicht, mindestens 512 MB, empfohlen 1 GB+ ([Anforderungen](https://docs.getoutline.com/s/hosting/doc/requirements-ULdYnwi4wG)) | Keine |
| Kommentar an Textstelle per API | Nein | Ja, laut Changelog über MCP | wie selbst gehostet, nicht geprüft |
| Auftragsliste mit Status und Knopf | Datenbank, Button | Fehlt, nur Konvention (Schlussfolgerung) | wie selbst gehostet |
| Bindung | Export mit Verlusten ([Hilfe](https://www.notion.com/help/export-your-content)) | Eigene Datenbank, Exportformat nicht belegt | Exportformat nicht belegt |

Der Server hatte am 04.11. in eigener Abfrage rund 1.527 MB verfügbar, am Vormittag etwa 4.070 MB ([webapp-plan.md:130](../webapp-plan.md)), dazu kein Swap und kein Docker. Die Installation "from source" ist laut Hersteller für Entwicklung und nicht unterstützte Plattformen gedacht ([Installation](https://docs.getoutline.com/s/hosting/doc/installation-methods-pSvgz9j0QC)).

**Schlussfolgerung.** Outline ist stärker, wenn die Kommentarschleife im Browser wichtig wird oder die Daten nicht in die USA sollen. Notion ist stärker bei Auftragslisten und braucht keinen Betrieb. Selbst hosten heißt Backups, Updates, Sicherheit bei Jan, und der Frontend-Build könnte den Server in Speichermangel bringen, was hier schon Dienste getötet hat. Das "ohne root" in den Notizen gilt für Agenten-Chats: Jan selbst hat root ([webapp-plan.md:202, 272](../webapp-plan.md)), die Hürde ist also Arbeit und Risiko, nicht Unmöglichkeit. Unterschätzt ist die Cloud: Für 10 USD lässt sich dieselbe Handprobe ohne Serverarbeit wiederholen (30 Tage Testphase laut Preisseite; ob die API darin nutzbar ist, ist nicht belegt). Selbsthosten erst, wenn die Probe trägt. Es bleibt: Was ein Agent verarbeitet, geht auch bei selbst gehostetem Wiki weiter an Anthropic. Docmost scheidet praktisch aus, weil API-Schlüssel und MCP erst im Bezahlplan kommen, mit 10 Plätzen Minimum rund 720 USD im Jahr ([Preise](https://docmost.com/pricing)).

## Vier Einwände sprechen gegen die Empfehlung, und Jan kann sie selbst prüfen

**Der Schnitt ist genau das Falsche, wenn Jan einen einzigen Ort will.** Jans Satz lautet: Jeder Auftrag und jedes Dokument hat einen Ort ([portal-oberflaeche.md:117-122](../portal-oberflaeche.md)). Zwei Oberflächen plus Brücke sind das Gegenteil und könnten die Unübersichtlichkeit verschlimmern. Die Brücke ist außerdem eine dritte Sache in der Pflege. **Widerlegt, wenn** Jan nach dem Test ständig zwischen Notion und Portal springt und den Ort nicht mehr weiß. Dann ist ein gut gebauter Eigenbau-Baum mit Ebenen besser, und Lias App zeigt das Muster bereits.

**Lange wissenschaftliche Arbeit passt schlecht zu Notion.** Notion empfiehlt Seiten "under a few thousand blocks" und schneidet beim Lesen um 20.000 Blöcke ab ([Doku](https://developers.notion.com/guides/data-apis/working-with-markdown-content)). Notion erzeugt selbst keine Zitate, verbreitet ist Zotero plus Word ([Smerilli, Suchauszug](https://simonesmerilli.com/writing/thesis-notion)). Die Endfassung bliebe also außerhalb. **Widerlegt zugunsten von "nur Word plus Portal", wenn** beim Handversuch das Lesen zäh ist und Jan die Fassungen dort nicht als ein Dokument empfindet.

**Fremddienst ist nicht pflegefrei.** Zwei brechende API-Versionen seit September 2025 ([Upgrade-Guide](https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03.md), [Changelog](https://developers.notion.com/page/changelog)), laut Statusspiegel im Oktober acht Tage verlangsamtes Schreiben über die API ([Pulsetic](https://pulsetic.com/status/notion/incidents/148016/)), Preiswechsel bei Workers. **Widerlegt, wenn** die Brücke im Testzeitraum mehr Reparatur braucht, als Schritt 4 gekostet hätte; das bleibt Jans Eindruck.

**Felix und Henri wollen vielleicht gar kein neues Werkzeug.** Von ihnen gibt es im Repo keine eigene Aussage; ihr belegter Weg ist die kommentierte Datei. **Widerlegt, wenn** sie Notion oder Outline beim Handversuch nicht öffnen. Dann fällt der Hauptgrund für ein Fremdwerkzeug weg, und das Portal mit Datei-Rückmeldung reicht.

Reverse Engineering wäre nur neu zu bewerten, wenn eine konkrete, belegte Aufgabe offiziell unmöglich bleibt und auf nur-lesenden Zugriff begrenzt werden kann. So einen Fall nennen die Notizen nicht. Umgekehrt ändert eine offene External Agents API die Rechnung zugunsten von Notion.

Die Belege für all das sind dünn. Es fanden sich keine Berichte über Einzelpersonen, die eigene Agenten über Monate mit Notion als Hauptoberfläche betreiben, und keine Vergleichsmessung Eigenbau gegen Notion. Die Zuordnung "Standardfunktion" ist Einordnung, nicht Prüfung.

## Widersprüche und Quellengrenzen bleiben stehen

| Punkt | Widerspruch oder Grenze | Folge |
|---|---|---|
| External Agents API | Alpha (Release, Produktseite) gegen private Beta (Hilfe, Blog); Stand November unbestätigt | In jedem Fall Warteliste |
| Agent SDK | Öffentliche Beta, private Alpha, Alpha, daneben Agent APIs GA; ob SDK und APIs dasselbe sind, ist offen | Changelog am neuesten, für Jan nicht entscheidend |
| Webhook-Zustellung | "at-most-once" gegen Wiederholungen | Duplikate und Verluste abfangen |
| Workers, Ende der Gratisphase | 11.08. gegen 15.10., englische Hilfe ohne Datum | Für den Test egal |
| Notion-Bedingungen | Wörtlich nur undatierte MSA-Kopie; Personal Use und Developer Terms nur Suchauszug, eine Kopie als "Deprecated" markiert; welche Fassung für Jan gilt, ist offen | Vor jeder Berufung im Browser lesen |
| HN-Thread zu den Bedingungen | Zitiert vermutlich ein anderes Unternehmen (getnotion.com) | Nicht Notion zuschreiben |
| Ausfälle | Nur Drittanbieter-Statusspiegel, teils Suchzusammenfassung; keine Verfügbarkeit in Prozent | Keine Aussage, ob Notion schlechter als andere ist |
| HTML-Block | Sandbox-Rechte (Netz, Speicher) nicht gefunden | Karten in Notion bleiben unbelegt |
| Outline | Nur-Lesen-Kommentare: Doku gegen Release v1.8.0; unbegrenzte Verschachtelung und MCP in der Community Edition nicht ausdrücklich belegt, RAM im Betrieb nicht gemessen | In der Probe prüfen |
| Docmost | MCP Business (englisch) gegen Enterprise (deutsch); Kommentar-Auflösen unklar | Preisseite gilt vorläufig |
| Portal-Erreichbarkeit | "von außen noch nicht erreichbar" gegen "ohne Passwort 401" in uni/STATUS.md; Plan nennt zudem noch den überholten Satz "Felix und Henri bekommen keinen Zugang" | Vermutlich veraltete Stellen |
| Serverspeicher | 1.527 und 1.553 MB gegen etwa 4.070 MB je nach Tageszeit | Stichproben, kein Dauerwert |
| Aufwand | Bau in Stunden und Geld nicht erfasst; Fremdschätzungen zu Notion-Klonen stammen von Verkäufern | Keine Kostenrechnung Eigenbau gegen Kauf möglich |

## Fazit: Nicht die erste Fassung ist das Risiko, sondern die Pflege

Jans Sorge trifft nur halb. Die Berichte scheitern seltener am ersten Tag als an späterer Pflege; "what are you willing to maintain?" ist die bessere Frage ([Eliason](https://www.nateliason.com/blog/the-past-and-future-of-vibe-coding), Einzelstimme). "Die haben sich etwas gedacht" gilt für Oberflächenbreite, nicht für Jans Fassungskette und Belegprüfung, von denen Notion nichts weiß. Darum lautet die nützliche Frage nicht Notion oder Eigenbau, sondern je Funktion: Wer pflegt das in einem Jahr, und könnte Jan es selbst beurteilen?

**Entscheidung 1: Handversuch vor der Brücke, mit Felix und Henri als Gästen?** Empfehlung: ja, und sie vorher fragen, ob sie überhaupt ein weiteres Werkzeug wollen. Das ändert Jans bisherige Testgrenze, deshalb braucht es sein Okay.

**Entscheidung 2: Dürfen Uni-Projektinhalte (Exposé, Normen, Interviewstoff) grundsätzlich in einen US-Dienst?** Im Repo steht dazu für Normen und Skripte nichts. Bei Nein ist Notion nur für Unkritisches brauchbar, dann wird Outline selbst gehostet die Hauptoption, was Jans Okay für die Installation braucht. Das ist keine Rechtsauskunft; ob die Gruppe oder die Uni das klären muss, entscheidet Jan.

**Entscheidung 3: Gilt der Schnitt im Portal?** Empfehlung: ja, unter Vorbehalt. Schritt 4, Konten und Überblick werden nur dann gestrichen, wenn der Test nach Jans Eindruck trägt; die Teile, die im Portal bleiben, werden erst genutzt, bevor sie wachsen.
