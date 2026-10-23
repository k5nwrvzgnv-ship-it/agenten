# claude.ai-Export anfordern und auf den Server laden (Schritt 3)

Die Menünamen stammen aus meinem Wissensstand und können in claude.ai inzwischen anders heißen.
Wenn etwas nicht passt, schreib mir, was du siehst.

## 1. Anfordern (Browser, dein Konto)
1. claude.ai öffnen, unten links auf deinen Namen, dann **Settings** (Einstellungen).
2. Unter **Privacy** (Datenschutz) **Export data** wählen und bestätigen.
3. Anthropic schickt eine Mail mit einem Download-Link an die Adresse deines Kontos. Das kann Minuten
   bis Stunden dauern. Der Link gilt nur begrenzt (meines Wissens etwa 24 Stunden), also bald laden.
4. Herunterladen: eine ZIP-Datei, zum Beispiel `data-2026-10-23-....zip`.

## 2. Auf den Server laden (Terminal auf deinem Rechner)
`scp` kopiert eine Datei über dieselbe SSH-Verbindung, mit der du dich sonst anmeldest.
`<server>` ist der Name oder die Adresse, die du sonst bei `ssh` angibst:

```bash
scp ~/Downloads/data-*.zip <server>:/home/agent/agenten/lia/auswertung/data/
```

Der Ordner `data/` existiert schon und ist nur für den User `agent` lesbar.

## 3. Auf dem Server entpacken und Struktur prüfen
```bash
cd ~/agenten/lia/auswertung && .venv/bin/python auswertung.py entpacken data/data-*.zip
```
Entpackt nach `data/export/` (Ordner chmod 700, Dateien chmod 600), lehnt verdächtige Pfade im ZIP ab
und löscht danach die ZIP-Datei auf dem Server.

```bash
cd ~/agenten/lia/auswertung && .venv/bin/python auswertung.py struktur
```
Zeigt nur Feldnamen, Datentypen und Anzahlen, keine Inhalte. Auch, ob es Verzweigungen gibt
(neu erzeugte Antworten oder bearbeitete Prompts). Ergebnis auch in `data/struktur.txt`.

## 4. Danach
- Die ZIP-Datei in deinem Download-Ordner löschen (so mit Lia vereinbart).
- Mir Bescheid geben. Ich lese `data/struktur.txt` und schlage in Schritt 4 die Liste von Lias Chats vor.
