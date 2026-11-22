"""Rundgang nur lesend: Bildschirmfotos (Desktop 1440, Handy 390) und optional axe-core je Seite.

Aufruf (aus dem Hauptordner):
  LD_LIBRARY_PATH=shared/arbeitsplatz/.venv/syslibs/root/usr/lib/x86_64-linux-gnu \
    shared/arbeitsplatz/.venv/bin/python -I shared/arbeitsplatz/bildschirmfotos.py <praefix> <zielordner> [--axe]
    [--lernen-basis URL] [--nur heute,dokument]; BASIS=http://127.0.0.1:<port> für eine andere Instanz.
Braucht Playwright (nur in .venv, nicht in requirements.txt), Chromium-Headless-Shell in ~/.cache/ms-playwright, die
fehlenden Systembibliotheken in .venv/syslibs (apt-get download, dpkg-deb -x) und axe-core in .venv/axe (npm pack).
Jeder Nicht-GET-Request wird abgebrochen, damit Jans Instanz unverändert bleibt. Die Seitenliste nennt echte
Dokumente aus Jans Instanz; fehlt eins, steht dort 404.
"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASIS = os.environ.get("BASIS", "http://127.0.0.1:8794")
AXE = Path(__file__).resolve().parent / ".venv" / "axe" / "package" / "axe.min.js"
U = "20261102-165741-uni-ac9dcc"
SEITEN = [
    ("heute", "/"),
    ("ordner", "/ort/forschungsprojekt-fehlstellen"),
    ("ordner-modul", "/ort/modul-holzschutz"),
    ("dokument", f"/dokument/{U}"),
    ("dokument-zusammenfassung", "/dokument/20261022-225119-dokumente-8e2548"),
    ("betrachter", f"/dokument/{U}/datei/20261104-203511-uni-fde8fe/1/ansehen?seite=1"),
    ("galerie", "/neu"),
    ("formular", "/neu/zusammenfassung"),
    ("archiv", "/archiv"),
    ("recherche", "/recherche/lia/reihe-strafe"),
    ("unterlage", "/unterlage/markt-und-wettbewerb/0"),
    ("lernen-modul", "/modul/holzschutz"),
    ("lernen-karten", "/modul/holzschutz/ueben"),
]
GROESSEN = {"desktop": (1440, 900), "handy": (390, 844)}


def main():
    praefix, ziel = sys.argv[1], Path(sys.argv[2])
    mit_axe = "--axe" in sys.argv
    lernen = sys.argv[sys.argv.index("--lernen-basis") + 1] if "--lernen-basis" in sys.argv else BASIS
    nur = sys.argv[sys.argv.index("--nur") + 1].split(",") if "--nur" in sys.argv else None
    ziel.mkdir(parents=True, exist_ok=True)
    ergebnis = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for gname, (w, h) in GROESSEN.items():
            ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, bypass_csp=True,
                                is_mobile=gname == "handy", has_touch=gname == "handy")
            ctx.route("**/*", lambda r: r.abort() if r.request.method != "GET" else r.continue_())
            pg = ctx.new_page()
            for name, pfad in SEITEN:
                if nur and name not in nur:
                    continue
                url = (lernen if pfad.startswith("/modul") else BASIS) + pfad
                antwort = pg.goto(url, wait_until="networkidle")
                status = antwort.status if antwort else 0
                pg.screenshot(path=str(ziel / f"{praefix}-{name}-{gname}.png"), full_page=True)
                eintrag = {"status": status}
                if mit_axe and gname == "desktop" or mit_axe and name in ("heute", "dokument"):
                    pg.add_script_tag(content=AXE.read_text())
                    r = pg.evaluate("async () => { const r = await axe.run(document, {resultTypes:['violations']});"
                                    " return r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length,"
                                    " ziel: v.nodes.slice(0,3).map(n => n.target.join(' '))})); }")
                    eintrag["axe"] = r
                ergebnis[f"{name}-{gname}"] = eintrag
                print(name, gname, status, len(eintrag.get("axe", [])) if "axe" in eintrag else "", flush=True)
            ctx.close()
        b.close()
    (ziel / f"{praefix}-rundgang.json").write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
