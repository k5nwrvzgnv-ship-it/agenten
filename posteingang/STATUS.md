# Status: Agent posteingang

## Zweck
Jans privates Postfach jan@kleinke.org überwachen: Wichtiges (Fristen, Rechnungen, persönliche Mails,
Termine, Bestellungen) per Telegram melden, Werbung und Newsletter weglassen. Stufe 2: Mail-Aufträge von Jan
("Termin bei Frau X absagen"): Kontext und Schreibstil selbst im Postfach suchen, Entwurf in die Freigabe.

## Stand (27.10.2026)
- agent.py fertig (Schritt post_pruefen). Ablauf: Mails holen, in data/mails_offen.json
  sichern, vorfiltern, Rest per claude_lauf (routine, zeitgesteuert) einordnen (einordnung.py), Meldung
  "[post] Wichtige Mails (n geprüft, m vorgefiltert)", danach mails_offen.json löschen. Arten: Frist/Rechnung,
  Persönlich, Termin, Bestellung/Versand; Verdacht auf Betrug wird mit "Vorsicht" gemeldet. KEINE = nichts.
  Claude wartet (Limit, Pause): Mails bleiben offen. Lauf fehlgeschlagen: Mails bleiben offen, Fehlermeldung
  höchstens einmal am Tag (data/schritt_fehler.json).
- Erster Lauf von Hand 27.10. 23:15: Marke gesetzt (data/postfach.json, letzte UID 51748), alte Mails nicht geholt.
  Ab jetzt holt jeder Lauf neue Mails und ruft Claude auf.
- Dienst und Timer eingerichtet 27.10. 23:20 nach Jans Okay (~/.config/systemd/user/, aus systemd/).
  Erster Timer-Lauf 28.10. 8:00, zugleich erster echter Lauf der Einordnung: Meldung und Log danach prüfen.
- Mail-Aufträge (Stufe 2, Plan von Jan 27.10. freigegeben, Senden von jan@kleinke.org und Kalender okay):
  gebaut und getestet. agentkit.mail und agentkit.imap.suchen sind da (Bedarf Nr. 19 erledigt 27.10.), mit dem
  echten agentkit.mail geprüft (pruefen, anzeige). Sende-Werte stehen in .env (27.10.). Bereit für den ersten echten Auftrag.
  Ablauf (agent.py, Logik in auftrag.py): /posteingang <Auftrag> -> Claude (routine) nennt Suchbegriffe ->
  Python sucht in INBOX, Archive und Sent (von/an Person, Stichwort, seit) und im Kalender (agentkit.kalender,
  KALENDER_ICS_URLS aus shared/.env) -> Claude (anspruchsvoll) schreibt Entwurf oder Rückfrage als JSON ->
  agentkit.mail.pruefen -> Freigabe (typ mail). Stilvorlage: Jans gesendete Mails an die Person, sonst seine
  letzten 5 gesendeten. Kontext in data/auftraege/<id>/kontext.json, Zuordnung Freigabe -> Auftrag in
  data/entwuerfe.json. Antwort auf das Ergebnis = Nachtrag (ganzer Ablauf neu), Ändern = neuer Entwurf mit
  demselben Kontext, Gesprächsbezug bleibt. Freigegeben -> mail.senden genau einmal (vor den Aufträgen im Lauf).
  Reihenfolge im Lauf: freigegebene_ausfuehren, auftraege_abarbeiten, post_pruefen.
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
- Code: posteingang/agent.py (Einstieg), vorfilter.py, einordnung.py (Prompt und Meldung), auftrag.py
  (Mail-Aufträge: Suchbegriffe, Kontext, Prompts)
- .venv: posteingang/.venv, agentkit per .pth eingebunden
- Dienst: posteingang.service (oneshot), Timer: posteingang.timer (8, 13, 19 Uhr), aktiv. Quelle in systemd/,
  nach Änderung neu kopieren und systemctl --user daemon-reload.
- Zugangsdaten: posteingang/.env (chmod 600), Vorlage posteingang/.env.example
- Laufzeitdaten: posteingang/data/, Logs: posteingang/logs/ (beide nicht im Repo)

## Entscheidungen
- 27.10.2026: Eigener Agent statt Erweiterung von uni (Trennung Uni/privat, eigene Zugangsdaten).
- 27.10.2026: Login direkt bei jan@kleinke.org mit dem Postfach-Kennwort (All-Inkl hat keine
  App-Passwörter; Jan wollte kein zweites Postfach). Kennwort trägt Jan selbst in .env ein.
- 27.10.2026: Stufe 1 nur lesen und melden. Senden erst in Stufe 2, nur nach Freigabe.
- 27.10.2026: Mail-Aufträge: Claude bekommt keinen Postfach-Zugriff, sondern nennt Suchbegriffe; Python sucht.
  Schlüssel m1, m2 ... statt UIDs, weil UIDs je Ordner doppelt sind.

## Offene Punkte (Plan Stufe 1)
1. Jan: Kennwort in KAS ändern (stand am 27.10. im Chat auf einem Screenshot), dann neu in .env.
2. Vorfilter: erledigt bis auf "kopf" aus agentkit.imap (Hauptordner-Chat, Bedarf Nr. 18).
3. agent.py: erledigt 27.10. Offen: Aufträge von Jan (auftraege) gibt es noch nicht. Bleibt Claude lange
   gesperrt, wächst mails_offen.json (bis 50 neue je Lauf) und damit der Prompt; bei Bedarf deckeln.
4. Aufbewahrung: data/mails/ nach 30 Tagen löschen.
5. Dienst und Timer: erledigt 27.10. Offen: ersten Lauf 28.10. 8:00 prüfen (logs/posteingang.log, Meldung).
6. Später: Termine über agentkit.kalender, Bestellungen an einkauf.
7. Mail-Aufträge: Sende-Werte in .env eingetragen 27.10. Offen: erster echter Test mit Jans Auftrag (Absage Paarberatung bei Frau Oppenheimer): Suchbegriffe, gefundene
   Mails und Entwurf im Log und in data/auftraege/ prüfen, erst dann freigeben.
8. data/auftraege/ (Mailtexte, auch sensibel) wie data/mails/ nach 30 Tagen löschen (zu Punkt 4).
9. Bedarf (Hauptordner 28.10.): auftrag.py auf agentkit.mailauftrag umstellen (gleicher Inhalt, dort für uni
   verallgemeinert, Schnittstelle in ../STATUS.md Punkt 20). Standard mailauftrag.STANDARD entspricht dem
   heutigen auftrag.py; gesendet kommt jetzt über Postfach(gesendet=GESENDET_ORDNER), nicht als Argument von
   kontext_sammeln. Danach auftrag.py und tests/test_auftrag.py löschen.

## Gelernte Regeln
- 28.10.2026: Absender weglassen: @klarna.de, @klarna.com (Anlass: Jan, Klarna interessiert ihn nicht)
