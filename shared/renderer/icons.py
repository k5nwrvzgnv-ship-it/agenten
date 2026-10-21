"""Icons als PNG in jeder Farbe, gezeichnet aus den Tabler-Icons-Schriften (MIT-Lizenz, Version 3.49.0).

Claude wählt ein Icon über seinen deutschen Namen (NAMEN). Pillow zeichnet das Zeichen aus der Schrift
in der gewünschten Farbe auf transparenten Hintergrund. Schriften und Lizenz liegen in icons/.
Neue Icons: tabler.io/icons, Zeichencode aus dist/tabler-icons.css bzw. tabler-icons-filled.css des
npm-Pakets @tabler/icons-webfont@3.49.0 in ICONS eintragen.
"""

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ORDNER = Path(__file__).resolve().parent / "icons"
SCHRIFT_UMRISS = ORDNER / "tabler-icons.ttf"
SCHRIFT_GEFUELLT = ORDNER / "tabler-icons-filled.ttf"
STANDARD_PX = 512

# deutscher Name: (Tabler-Name, Zeichen Umriss, Zeichen gefüllt oder None)
ICONS = {
    "handschlag": ("heart-handshake", 0xf0f3, None),
    "ziel": ("target-arrow", 0xf51a, None),
    "wecker": ("alarm", 0xea04, 0xf709),
    "uhr": ("clock", 0xea70, 0xf73a),
    "sanduhr": ("hourglass", 0xef93, 0xf756),
    "zeigefinger": ("hand-finger-right", 0xff4d, None),
    "smiley": ("mood-smile", 0xeaf7, 0xf7f8),
    "traurig": ("mood-sad", 0xeaf6, 0xf7f7),
    "neutral": ("mood-empty", 0xeeb5, 0xf7f3),
    "paket": ("packages", 0xf2c9, None),
    "schale": ("bowl", 0xf4fa, 0xfb22),
    "gluehbirne": ("bulb", 0xea51, 0xf66a),
    "frage": ("help-circle", 0xf91d, 0xfa3d),
    "achtung": ("alert-circle", 0xea05, 0xf6ee),
    "buch": ("book", 0xea39, 0xfa87),
    "buecher": ("books", 0xeff2, None),
    "stift": ("pencil", 0xeb04, 0x101cf),
    "schreiben": ("writing", 0xef08, 0x1018b),
    "gruppe": ("users-group", 0xfa21, None),
    "partner": ("users", 0xebf2, None),
    "person": ("user", 0xeb4d, 0xfd19),
    "gespraech": ("messages", 0xeb6c, 0x101d0),
    "sprechblase": ("message-circle", 0xeaed, 0xfecf),
    "waage": ("scale", 0xebc2, 0x101cd),
    "herz": ("heart", 0xeabe, 0xf67c),
    "haken": ("check", 0xea5e, 0x101e6),
    "kreuz": ("x", 0xeb55, 0x101c6),
    "stern": ("star", 0xeb2e, 0xf6a6),
    "pfeil": ("arrow-right", 0xea1f, None),
    "puzzle": ("puzzle", 0xeb10, 0xf699),
    "lupe": ("search", 0xeb1c, 0x101cb),
    "notizen": ("notes", 0xeb6e, None),
    "checkliste": ("list-check", 0xeb6a, 0x101d4),
    "kalender": ("calendar", 0xea53, 0xfb27),
    "welt": ("world", 0xeb54, 0x101c7),
    "schule": ("school", 0xecf7, 0x101cc),
    "tafel": ("chalkboard", 0xf34d, None),
    "mikrofon": ("microphone", 0xeaf0, 0xfe0f),
    "video": ("video", 0xed22, 0x1009b),
    "musik": ("music", 0xeafc, None),
    "bild": ("photo", 0xeb0a, 0xfa4a),
    "daumen_hoch": ("thumb-up", 0xeb3c, 0xf6ab),
    "daumen_runter": ("thumb-down", 0xeb3b, 0xf6aa),
    "rakete": ("rocket", 0xec45, None),
    "gesetz": ("gavel", 0xef90, None),
    "haus": ("home", 0xeac1, 0x102b3),
    "auge": ("eye", 0xea9a, 0xf679),
    "ohr": ("ear", 0xebce, None),
    "gehirn": ("brain", 0xf59f, None),
    "flagge": ("flag", 0xeaa6, 0xf67a),
    "text": ("file-text", 0xeaa2, 0x10114),
    "aufgabe": ("clipboard-list", 0xea6d, 0x100ea),
    "megafon": ("speakerphone", 0xed61, None),
    "karte": ("map", 0xeae9, None),
    "zitat": ("quote", 0xefbe, 0x1009c),
}
NAMEN = tuple(sorted(ICONS))

_FARBE = re.compile(r"^[0-9A-Fa-f]{6}$")


def zeichnen(name: str, ziel: Path, farbe: str = "000000", gefuellt: bool = False, px: int = STANDARD_PX) -> Path:
    """Icon `name` als quadratisches PNG (px x px, transparent) nach `ziel`. Gibt es keine gefüllte Form,
    kommt die Umrissform. Unbekannter Name oder falsche Farbe: ValueError."""
    if name not in ICONS:
        raise ValueError(f"Icon {name!r} gibt es nicht, erlaubt sind: {', '.join(NAMEN)}")
    if not _FARBE.match(farbe.lstrip("#")):
        raise ValueError(f"Farbe {farbe!r} ist keine Farbe wie \"C00000\"")
    _, umriss, voll = ICONS[name]
    schrift, zeichen = (SCHRIFT_GEFUELLT, voll) if gefuellt and voll else (SCHRIFT_UMRISS, umriss)
    bild = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    # Einfacher Textsatz: raqm (komplexer Satz) scheitert an manchen Zeichen aus dem Unicode-Privatbereich.
    font = ImageFont.truetype(str(schrift), size=px, layout_engine=ImageFont.Layout.BASIC)
    stift = ImageDraw.Draw(bild)
    # Genau mittig nach dem tatsächlichen Umriss, nicht nach den Schriftmaßen (die passen bei Icons nicht).
    links, oben, rechts, unten = stift.textbbox((0, 0), chr(zeichen), font=font)
    ort = ((px - (rechts - links)) / 2 - links, (px - (unten - oben)) / 2 - oben)
    stift.text(ort, chr(zeichen), font=font, fill="#" + farbe.lstrip("#"))
    bild.save(ziel)
    return Path(ziel)
