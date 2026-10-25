"""Scans auf archive.org: Druckseite -> Scan-Seite, OCR je Druckseite, Links (ohne Netz).

Quellen mit scan_id in quellen.toml (Liszt) haben keine brauchbare OCR für Wortlaut. Ihre Textfassung
ist die OCR je Druckseite, nur zur Orientierung und für den unscharfen Abgleich (abschrift.py).

Zuordnung (zuordnung): Grundlage ist <id>_page_numbers.json von archive.org. Belegt sind dort nur
Einträge mit confidence 100 (Anker). Eine Druckseite ohne eigenen Anker wird nur zwischen zwei Ankern
eingesetzt, wenn die Abstände von Blatt und Seite gleich sind (keine eingeschobenen Tafeln). Was davor
oder danach liegt, muss in quellen.toml als scan_von_hand stehen (am Bild geprüft). Widerspricht ein
Wert von Hand einem Anker, ist das ein ScanFehler. Nichts wird geraten.
Scan-Seite n (BookReader, 0-basiert) = Blatt + scan_versatz (Toronto-Scan: -1, am Bild geprüft).
Der OCR-Seitenindex (<id>_hocr_pageindex.json) zählt wie n.
"""

import gzip
import json

ARCHIV = "https://archive.org"


class ScanFehler(Exception):
    pass


def dateien(scan_id: str) -> dict[str, str]:
    """Die drei Dateien, die eine Scan-Quelle braucht (stehen auch als urls in quellen.toml)."""
    basis = f"{ARCHIV}/download/{scan_id}/{scan_id}"
    return {"seitenzahlen": f"{basis}_page_numbers.json", "text": f"{basis}_hocr_searchtext.txt.gz",
            "index": f"{basis}_hocr_pageindex.json.gz"}


def link(scan_id: str, n: int) -> str:
    return f"{ARCHIV}/details/{scan_id}/page/n{n}"


def bild_url(scan_id: str, n: int) -> str:
    return f"{ARCHIV}/download/{scan_id}/page/n{n}.jpg"


def _anker(seitenzahlen: dict, von: int, bis: int) -> dict[int, int]:
    """{Seite: Blatt} aus Einträgen mit confidence 100. Kommt eine Seitenzahl mehrfach vor (Beilagen am
    Bandende zählen neu), gilt das Blatt, dessen Abstand (Blatt - Seite) dem der eindeutigen Seiten im
    Bereich am nächsten liegt. Ist das nicht eindeutig: ScanFehler."""
    kandidaten: dict[int, set[int]] = {}
    for p in seitenzahlen.get("pages", []):
        nummer = str(p.get("pageNumber") or "")
        if p.get("confidence") == 100 and nummer.isdigit():
            kandidaten.setdefault(int(nummer), set()).add(p["leafNum"])
    abstaende = sorted(next(iter(b)) - s for s, b in kandidaten.items() if len(b) == 1 and von <= s <= bis)
    anker = {}
    for s, blaetter in kandidaten.items():
        if len(blaetter) == 1:
            anker[s] = next(iter(blaetter))
            continue
        if not von <= s <= bis:
            continue  # mehrfach und außerhalb des Bereichs: kein Anker
        if not abstaende:
            raise ScanFehler(f"Seite {s} mehrfach belegt (Blatt {sorted(blaetter)}), kein Vergleich möglich")
        mitte = abstaende[len(abstaende) // 2]
        nach_naehe = sorted(blaetter, key=lambda b: abs(b - s - mitte))
        if abs(nach_naehe[0] - s - mitte) == abs(nach_naehe[1] - s - mitte):
            raise ScanFehler(f"Seite {s} mehrfach belegt (Blatt {sorted(blaetter)}), nicht eindeutig")
        anker[s] = nach_naehe[0]
    return anker


def zuordnung(seitenzahlen: dict, von: int, bis: int, versatz: int, von_hand: dict | None = None) -> dict[int, int]:
    """{Druckseite: Scan-Seite n} für von..bis. Fehlt ein Beleg: ScanFehler."""
    anker = _anker(seitenzahlen, von, bis)
    hand = {int(s): int(n) for s, n in (von_hand or {}).items()}
    for s, n in hand.items():
        if s in anker and anker[s] + versatz != n:
            raise ScanFehler(f"Seite {s}: von Hand n{n}, page_numbers.json n{anker[s] + versatz}")
    ergebnis = {}
    for s in range(von, bis + 1):
        if s in anker:
            ergebnis[s] = anker[s] + versatz
        elif s in hand:
            ergebnis[s] = hand[s]
        else:
            vor = max((a for a in anker if a < s), default=None)
            nach = min((a for a in anker if a > s), default=None)
            if vor is None or nach is None or anker[nach] - anker[vor] != nach - vor:
                raise ScanFehler(f"Seite {s} ist nicht belegt (kein Anker, keine lückenlose Folge, nicht von Hand)")
            ergebnis[s] = anker[vor] + (s - vor) + versatz
    if len(set(ergebnis.values())) != len(ergebnis):
        raise ScanFehler("Zwei Druckseiten auf derselben Scan-Seite")
    return ergebnis


def ocr_seiten(text_gz: bytes, index_gz: bytes, zuord: dict[int, int]) -> dict[int, str]:
    """OCR-Text je Druckseite aus hocr_searchtext und hocr_pageindex (Zeichenbereiche je Scan-Seite)."""
    text = gzip.decompress(text_gz).decode("utf-8")
    index = json.loads(gzip.decompress(index_gz))
    seiten = {}
    for s, n in zuord.items():
        if n >= len(index):
            raise ScanFehler(f"Scan-Seite n{n} fehlt im OCR-Index ({len(index)} Seiten)")
        anfang, ende = index[n][0], index[n][1]
        seiten[s] = text[anfang:ende]
    return seiten
