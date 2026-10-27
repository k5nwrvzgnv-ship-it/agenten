# Status: Agent posteingang

## Zweck
Jans privates Postfach jan@kleinke.org überwachen: Wichtiges (Fristen, Rechnungen, persönliche Mails,
Termine, Bestellungen) per Telegram melden, Werbung und Newsletter weglassen. Später Antwortentwürfe.

## Stand (27.10.2026)
- agent.py fertig (Schritt post_pruefen), noch kein Dienst. Ablauf: Mails holen, in data/mails_offen.json
  sichern, vorfiltern, Rest per claude_lauf (routine, zeitgesteuert) einordnen (einordnung.py), Meldung
  "[post] Wichtige Mails (n geprüft, m vorgefiltert)", danach mails_offen.json löschen. Arten: Frist/Rechnung,
  Persönlich, Termin, Bestellung/Versand; Verdacht auf Betrug wird mit "Vorsicht" gemeldet. KEINE = nichts.
  Claude wartet (Limit, Pause): Mails bleiben offen. Lauf fehlgeschlagen: Mails bleiben offen, Fehlermeldung
  höchstens einmal am Tag (data/schritt_fehler.json).
- Erster Lauf von Hand 27.10. 23:15: Marke gesetzt (data/postfach.json, letzte UID 51748), alte Mails nicht geholt.
  Ab jetzt holt jeder Lauf neue Mails und ruft Claude auf.
- vorfilter.py (ohne Netz, tests/test_vorfilter.py): fällt weg bei X-Spam-Flag YES, gesperrtem Absender,
  List-Unsubscribe, Precedence bulk/list/junk. Auto-Submitted bleibt (Rechnungen, Versand).
  Gesperrte Absender aus Regelzeilen "Absender weglassen: a@b.de, @domain.de" (@domain mit Subdomains).
  Wartet auf "kopf" in agentkit.imap.zerlege (Bedarf Nr. 18 in der Haupt-STATUS.md), bis dahin wirkt nur
  die Absender-Sperre.
- Vorhanden: .env.example, .gitignore, requirements.txt (nur Bordmittel), systemd/ (Vorlagen
  posteingang.service und .timer, NICHT kopiert), tests/test_umgebung.py (in pruefen.sh eingetragen),
  .venv mit agentkit per .pth.
- Postfach: All-Inkl (KAS), IMAP w005718f.kasserver.com:993, SMTP 465 (SSL) und 587 (STARTTLS).
  Am 27.10. vom Server aus erreichbar, TLS 1.3, Zertifikat *.kasserver.com.
- Lesetest 27.10.: Anmeldung mit jan@kleinke.org (volle Adresse als Nutzer) geht, .env ist eingetragen (600).
  Posteingang 12.101 Mails, davon 6.786 ungelesen: "ungelesen" taugt nicht als Filter.
  Ordner: INBOX, Archive, Sent, Trash, Junk, Drafts. Spam landet in Junk, gelesen wird nur INBOX.
- Kopfzeilen 27.10. (letzte 200 INBOX, 40 Junk): All-Inkl setzt X-Spam-Flag YES und verschiebt nach Junk,
  kein Betreff-Präfix. INBOX: 22/200 List-Unsubscribe, 1 Precedence bulk, 7 Auto-Submitted, kein Spam-Flag.
  Der Vorfilter nimmt also wenig weg, den Großteil ordnet Claude ein.
- Lesen über agentkit.imap.neue_mails (readonly, BODY.PEEK, Marke in data/postfach.json, erster Lauf
  setzt nur die Marke, max. 50 Mails pro Lauf).

## Aufbau
- Code: posteingang/agent.py (Einstieg), vorfilter.py, einordnung.py (Prompt und Meldung)
- .venv: posteingang/.venv, agentkit per .pth eingebunden
- Dienst: posteingang.service (oneshot), Timer: posteingang.timer (8, 13, 19 Uhr). Vorlagen in systemd/.
- Zugangsdaten: posteingang/.env (chmod 600), Vorlage posteingang/.env.example
- Laufzeitdaten: posteingang/data/, Logs: posteingang/logs/ (beide nicht im Repo)

## Entscheidungen
- 27.10.2026: Eigener Agent statt Erweiterung von uni (Trennung Uni/privat, eigene Zugangsdaten).
- 27.10.2026: Login direkt bei jan@kleinke.org mit dem Postfach-Kennwort (All-Inkl hat keine
  App-Passwörter; Jan wollte kein zweites Postfach). Kennwort trägt Jan selbst in .env ein.
- 27.10.2026: Stufe 1 nur lesen und melden. Senden erst in Stufe 2, nur nach Freigabe.

## Offene Punkte (Plan Stufe 1)
1. Jan: Kennwort in KAS ändern (stand am 27.10. im Chat auf einem Screenshot), dann neu in .env.
2. Vorfilter: erledigt bis auf "kopf" aus agentkit.imap (Hauptordner-Chat, Bedarf Nr. 18).
3. agent.py: erledigt 27.10. Offen: Aufträge von Jan (auftraege) gibt es noch nicht. Bleibt Claude lange
   gesperrt, wächst mails_offen.json (bis 50 neue je Lauf) und damit der Prompt; bei Bedarf deckeln.
4. Aufbewahrung: data/mails/ nach 30 Tagen löschen.
5. Dienst und Timer einrichten, erst nach Jans Okay.
6. Später: Termine über agentkit.kalender, Bestellungen an einkauf, Stufe 2 Entwürfe und Senden
   (mail.py aus uni dann nach agentkit verallgemeinern).

## Gelernte Regeln
- (noch keine)
