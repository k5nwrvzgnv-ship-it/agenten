# claude.ai-Export anfordern und auf den Server laden (Schritt 3)

Die Menünamen stammen aus meinem Wissensstand und können in claude.ai inzwischen anders heißen.
Wenn etwas nicht passt, schreib mir, was du siehst.

## 1. Anfordern (Browser, dein Konto)
1. claude.ai, Settings, Privacy, **Export data**.
2. Die Mail geht an die Adresse des claude.ai-Kontos. Sie enthält ein Manifest (JSON) mit einem Link je
   Datei. Jeder Link gilt 24 Stunden und kann nach dem ersten Öffnen ungültig werden: jede Datei
   gleich vollständig laden.
3. Der Export vom 23.10.2026 bestand aus 6 ZIPs: light_metadata, projects, memories, design_chats,
   frames, conversations (je `-000.zip`). Gebraucht werden nur:
   - `conversations-000.zip` (die Chats),
   - `projects-000.zip` (falls Lia Projekte mit Anweisungen oder Dateien genutzt hat),
   - `light_metadata-000.zip` (Kontodaten, für die Struktur).
   memories, design_chats und frames nicht laden (Datensparsamkeit). Sollte sich zeigen, dass Lia
   Design-Chats geführt hat, holen wir das mit einem neuen Export nach.

## 2. Auf den Server laden (Terminal auf deinem Rechner)
`scp` kopiert Dateien über dieselbe SSH-Verbindung, mit der du dich sonst anmeldest.
`<server>` ist der Name oder die Adresse, die du sonst bei `ssh` angibst:

```bash
scp ~/Downloads/conversations-000.zip ~/Downloads/projects-000.zip ~/Downloads/light_metadata-000.zip <server>:/home/agent/agenten/lia/auswertung/data/
```

Der Ordner `data/` existiert schon und ist nur für den User `agent` lesbar.

## 3. Auf dem Server entpacken und Struktur prüfen
```bash
cd ~/agenten/lia/auswertung && .venv/bin/python auswertung.py entpacken data/*-000.zip
```
Entpackt je ZIP nach `data/export/<name>/` (Ordner chmod 700, Dateien chmod 600), lehnt verdächtige Pfade im ZIP ab
und löscht danach die ZIP-Dateien auf dem Server.

```bash
cd ~/agenten/lia/auswertung && .venv/bin/python auswertung.py struktur
```
Zeigt nur Feldnamen, Datentypen und Anzahlen, keine Inhalte. Auch, ob es Verzweigungen gibt
(neu erzeugte Antworten oder bearbeitete Prompts). Ergebnis auch in `data/struktur.txt`.

## 4. Danach
- Die ZIP-Dateien und die Manifest-Mail in deinem Download-Ordner löschen (so mit Lia vereinbart).
- Mir Bescheid geben. Ich lese `data/struktur.txt`, prüfe meine Annahmen über die Felder und
  erzeuge mit `auswertung.py chatliste` die Vorschlagsliste von Lias Chats (Schritt 4).
