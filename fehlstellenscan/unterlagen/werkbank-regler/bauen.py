"""Baut die Einzeldatei mit eingebetteten Bildern und Schriften (nicht im Repo)."""

import base64
import pathlib
import re
import sys

ordner = pathlib.Path(__file__).parent


def uri(name, art):
    return f"data:{art};base64," + base64.b64encode((ordner / name).read_bytes()).decode()


def lies(name):
    return (ordner / name).read_text(encoding="utf-8")


css = re.sub(r"url\((schriften/.*?)\)", lambda m: f"url({uri(m[1], 'font/woff2')})", lies("stil.css") + lies("schriften.css"))
bilder = ",".join(f'"{i}":"{uri(f"klein/{i}.jpg", "image/jpeg")}"' for i in ("153200004", "153200015", "153200022"))
seite = lies("index.html").replace('<link rel="stylesheet" href="stil.css">', f"<style>{css}</style>")
seite = seite.replace(
    '<script src="daten.js"></script>', f"<script>window.BILDER={{{bilder}}};{lies('daten.js')}</script>"
)
seite = seite.replace('<link rel="stylesheet" href="schriften.css">', "")
seite = seite.replace('<script src="regler.js"></script>', f"<script>{lies('regler.js')}</script>")
seite = seite.replace('<script src="bedienung.js"></script>', f"<script>{lies('bedienung.js')}</script>")
assert "src=\"" not in seite.split("<script>")[0]
pathlib.Path(sys.argv[1]).write_text(seite, encoding="utf-8")
