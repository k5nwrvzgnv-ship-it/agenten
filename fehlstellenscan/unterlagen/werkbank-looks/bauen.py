"""Baut aus diesem Ordner eine Einzeldatei mit eingebetteten Bildern und Schriften."""

import base64
import pathlib
import re

ordner = pathlib.Path(__file__).parent


def lies(name):
    return (ordner / name).read_text(encoding="utf-8")


def daten_uri(name, art):
    return f"data:{art};base64," + base64.b64encode((ordner / name).read_bytes()).decode()


schriften = re.sub(r"url\((.*?)\)", lambda m: f"url({daten_uri(m[1], 'font/woff2')})", lies("schriften.css"))
bilder = {i: daten_uri(f"{i}.jpg", "image/jpeg") for i in ("153200004", "153200015", "153200022")}
eintraege = ",".join(f"'{i}':'{u}'" for i, u in bilder.items())
bedienung = lies("bedienung.js")
alt = "B[i].src=i+'.jpg'"
assert alt in bedienung
bedienung = bedienung.replace(alt, "B[i].src=BILDER[i]")
seite = lies("index.html")
for name, inhalt in (("schriften.css", schriften), ("stil.css", lies("stil.css"))):
    seite = seite.replace(f'<link rel="stylesheet" href="{name}">', f"<style>{inhalt}</style>")
for name, inhalt in (("daten.js", lies("daten.js")), ("looks.js", lies("looks.js")), ("bedienung.js", bedienung)):
    vorweg = f"const BILDER={{{eintraege}}};" if name == "bedienung.js" else ""
    seite = seite.replace(f'<script src="{name}"></script>', f"<script>{vorweg}{inhalt}</script>")
assert 'src="' not in seite.split("<script>")[0] and "href=" not in seite.split("</head>")[0].split("<style>")[0]
(ordner / "neurolign-looks-einzeldatei.html").write_text(seite, encoding="utf-8")
