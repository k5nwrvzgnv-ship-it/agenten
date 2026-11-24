# Alte Optik, neue Bedienung, 24.11.2026
Jan: „optisch find ich das alte besser. von den funktionen das neue besser.“

Was die alte Optik trägt (`git show edfff76`, werkbank-entwurf): fast schwarze Fläche, auf der das Holz leuchtet; Logo mit Outfit; Gold sparsam; ein weißer Pillenknopf; große dünne Maßzahl; Drehregler; runde Vorschauen; runde Bildbühne.
Was die neue Bedienung trägt: Bilder hinzufügen, Objektliste mit unsicherstem zuerst, Stimmt/Enter, Löschen mit Rückgängig, Speicherstand, gleiche Buchstaben in Liste und Bild, Warnung bei doppelten Vorlabeln, Werkzeuge neben dem Bild, Mobilansicht. In allen Looks vollständig.

| Look | Aufbau | Form und Schrift |
|---|---|---|
| Neurolign | Zahl, Regler und Klassen rechts, Liste darunter | nah am alten, Outfit, rund |
| Neurolign ruhig | Werkzeugband über dem Bild, Liste klappt auf | alte Farben und Pillen, Schieber |
| Nachtschicht | drei Spalten: Liste, Bild, Objekt | dicht, kantig, JetBrains Mono, Mint |
| Messblatt | Bild links, Messtabelle mit Größtmaß rechts | weiß, Serifen, rot, Linien |
| Farbfeld | Objektfeld links in Klassenfarbe, Kacheln | groß, rund, Bricolage Grotesque |
| Waldkante | Bild über volle Höhe, Film als dunkle Spalte | hell, grün, Schibsted Grotesk |

Bedienfeld („Anpassen“): Schrift (11 und Systemschrift), Größe, hell/dunkel, Akzent, Fläche, Bildumgebung, Dichte, Ecken, Umrisse, Regler, große Zahl, Vorschau. Je Look gemerkt, zurücksetzbar, als Text kopierbar. Schriftfarben rechnet die Seite aus den gewählten Flächen, damit sie lesbar bleiben.

Geändert gegenüber werkbank-startansicht: Hinzugefügte Bilder bleiben nach dem Neuladen (Ablage im Browser). Hinweise fangen keine Klicks auf dem Bild mehr ab. Dateinamen werden nicht als HTML gelesen.
Grenzen: alles nur im Browser; kein echtes Vorlabeln neuer Bilder, dort Maße in px. Am Handy ist der Aufbau in allen Looks gleich, nur Schrift, Form und Farbe wechseln.

Einzeldatei bauen: `python3 bauen.py`. Schriften: Google Fonts, SIL Open Font License.
