"""Kursmaterial aus Moodle nach data/kurse/ spiegeln, damit Claude es lesen kann.

Pro Kurs: data/kurse/<Kurs>/uebersicht.md (Abschnitte, Texte, Links, Dateipfade)
und die Dateien in Unterordnern je Abschnitt. Nur neue oder geänderte Dateien
werden geladen (data/kurse/.stand.json: Datei-URL -> timemodified).
Nicht geladen: Dateien über MAX_MB, Ton/Video über MEDIEN_MAX_MB und ZIP-Archive über ZIP_MAX_MB
(stehen nur in der Übersicht). Ton und Video transkribiert transkription.py nachts.
Kleinere ZIPs werden nach <name>_entpackt/ entpackt (Namen bereinigt, höchstens
ENTPACKT_MAX_MB), dazu eine Inhaltsliste <name>.zip.txt.
PDF, Word, PowerPoint und Excel bekommen daneben eine Textfassung <datei>.txt (mit
Seiten- bzw. Foliennummern), damit Claude mit Grep gezielt suchen kann, statt ganze
Dateien zu lesen. Alte Formate (doc, ppt, xls) nicht.
In Moodle gelöschte Dateien bleiben liegen.
Ein Kurs, der zum ersten Mal gespiegelt wird (noch keine uebersicht.md), meldet sein
Material nicht als neu. Mehrere Moodles (HNEE, BFH) teilen sich ZIEL und den Stand.
Aufgaben (Beschreibung, Fristen, Abgabeart, Status, Anhänge) stehen in
data/kurse/<Kurs>/aufgaben.md, Anhänge in data/kurse/<Kurs>/Aufgaben/<Aufgabe>/.
"""

import json
import logging
import re
import shutil
import urllib.request
import zipfile
from datetime import datetime
from html import unescape
from pathlib import Path

HIER = Path(__file__).resolve().parent
ZIEL = HIER / "data" / "kurse"
STAND_DATEI = ZIEL / ".stand.json"
MAX_MB = 100
MEDIEN_MAX_MB = 300
MEDIEN_ENDUNGEN = {".mp4", ".m4a", ".mp3", ".webm", ".mkv", ".mov", ".wav", ".ogg"}
ZIP_MAX_MB = 50
ENTPACKT_MAX_MB = 300


def sicherer_name(name: str) -> str:
    """Ein Pfadteil ohne HTML-Zeichen (&amp;), Schrägstriche, Steuerzeichen und führende Punkte."""
    name = re.sub(r'[\x00-\x1f/\\:*?"<>|]', "_", unescape(name)).strip().lstrip(".")
    return name[:120] or "_"


def grenze_mb(dateiname: str) -> int:
    endung = Path(dateiname).suffix.lower()
    return ZIP_MAX_MB if endung == ".zip" else MEDIEN_MAX_MB if endung in MEDIEN_ENDUNGEN else MAX_MB


def html_zu_text(html: str) -> str:
    text = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", html or "", flags=re.I)
    text = unescape(re.sub(r"<[^>]+>", "", text))
    return "\n".join(z.strip() for z in text.splitlines() if z.strip())


def als_text(pfad: Path) -> str | None:
    """Text aus pdf, docx, pptx oder xlsx (mit Seiten-, Folien- bzw. Blattangabe). Andere Formate: None."""
    endung = pfad.suffix.lower()
    if endung == ".pdf":
        import pypdf
        logging.getLogger("pypdf").setLevel(logging.ERROR)  # kaputte PDFs sonst sehr gesprächig
        teile, mit_text = [], 0
        for nr, seite in enumerate(pypdf.PdfReader(pfad).pages, 1):
            text = (seite.extract_text() or "").strip()
            mit_text += bool(text)
            teile += [f"--- Seite {nr}", text]
        if not mit_text:
            return "(Kein Text gefunden, vermutlich ein Scan. Das PDF selbst mit Read öffnen.)"
        return "\n".join(teile)
    if endung == ".docx":
        import docx
        d = docx.Document(pfad)
        teile = [a.text for a in d.paragraphs if a.text.strip()]
        for t in d.tables:
            teile += [" | ".join(z.text.strip() for z in reihe.cells) for reihe in t.rows]
        return "\n".join(teile)
    if endung == ".pptx":
        import pptx
        teile = []
        for nr, folie in enumerate(pptx.Presentation(pfad).slides, 1):
            teile.append(f"--- Folie {nr}")
            for form in folie.shapes:
                if form.has_text_frame and form.text_frame.text.strip():
                    teile.append(form.text_frame.text.strip())
                if getattr(form, "has_table", False) and form.has_table:
                    teile += [" | ".join(z.text.strip() for z in reihe.cells) for reihe in form.table.rows]
            if folie.has_notes_slide and folie.notes_slide.notes_text_frame.text.strip():
                teile.append(f"Notizen: {folie.notes_slide.notes_text_frame.text.strip()}")
        return "\n".join(teile)
    if endung == ".xlsx":
        import openpyxl
        teile = []
        for blatt in openpyxl.load_workbook(pfad, read_only=True, data_only=True).worksheets:
            teile.append(f"--- Blatt {blatt.title}")
            for reihe in blatt.iter_rows(values_only=True):
                if any(w is not None for w in reihe):
                    teile.append(" | ".join("" if w is None else str(w) for w in reihe))
        return "\n".join(teile)
    return None


def _textfassung(pfad: Path, erneuern: bool) -> bool:
    """Schreibt <pfad>.txt, falls das Format unterstützt wird. True, wenn es eine Textfassung gibt."""
    if pfad.suffix.lower() not in (".pdf", ".docx", ".pptx", ".xlsx", ".zip"):
        return False
    txt = pfad.with_name(pfad.name + ".txt")
    if erneuern or not txt.exists():
        try:
            if pfad.suffix.lower() == ".zip":
                inhalt = f"Entpackt nach: {pfad.stem}_entpackt/\n" + "\n".join(entpacken(pfad))
            else:
                inhalt = als_text(pfad) or ""
            txt.write_text(inhalt, encoding="utf-8")
        except Exception as f:  # noqa: BLE001 – kaputte Datei soll den Abgleich nicht stoppen
            txt.write_text(f"(Textfassung fehlgeschlagen: {f})", encoding="utf-8")
    return True


def entpacken(pfad: Path) -> list[str]:
    """Entpackt ein ZIP nach <name>_entpackt/ (alter Inhalt wird ersetzt). Gibt die Inhaltsliste zurück.

    Jeder Pfadteil wird mit sicherer_name bereinigt, damit nichts außerhalb landet.
    Ab ENTPACKT_MAX_MB wird abgebrochen, der Rest steht nur in der Liste.
    """
    ziel = pfad.with_name(pfad.stem + "_entpackt")
    shutil.rmtree(ziel, ignore_errors=True)
    liste, summe = [], 0
    with zipfile.ZipFile(pfad) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            rel = Path(*[sicherer_name(t) for t in info.filename.replace("\\", "/").split("/") if t])
            summe += info.file_size
            if summe > ENTPACKT_MAX_MB * 1e6:
                liste.append(f"{rel} ({info.file_size / 1e6:.1f} MB, nicht entpackt: Grenze erreicht)")
                continue
            (ziel / rel).parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as quelle, open(ziel / rel, "wb") as f:
                shutil.copyfileobj(quelle, f)
            _textfassung(ziel / rel, erneuern=True)
            liste.append(f"{rel} ({info.file_size / 1e6:.1f} MB)")
    return liste


ABGABEARTEN = {"onlinetext": "Online-Text (direkt in Moodle eintippen)", "file": "Datei-Upload"}


def _zeit(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M") if ts else "keine"


def aufgabe_als_text(a: dict, status: str, anhaenge: list[str]) -> list[str]:
    """Abschnitt für aufgaben.md aus einem Eintrag von mod_assign_get_assignments."""
    cfg = {(c["plugin"], c["name"]): c["value"] for c in a.get("configs", []) if c["subtype"] == "assignsubmission"}
    arten = [text for plugin, text in ABGABEARTEN.items() if cfg.get((plugin, "enabled")) == "1"]
    if cfg.get(("file", "enabled")) == "1":
        anzahl, typen = cfg.get(("file", "maxfilesubmissions")), cfg.get(("file", "filetypeslist"))
        arten[-1] += f", höchstens {anzahl} Datei(en)" if anzahl else ""
        arten[-1] += f", erlaubte Typen: {typen}" if typen else ""
    zeilen = [
        f"## {a['name']}", "",
        f"- Moodle: {{url}}/mod/assign/view.php?id={a['cmid']}",
        f"- Fällig: {_zeit(a['duedate'])}",
        f"- Letzte Abgabe (Nachfrist): {_zeit(a['cutoffdate'])}",
        f"- Abgabe ab: {_zeit(a['allowsubmissionsfromdate'])}",
        f"- Abgabeart: {'; '.join(arten) or 'keine Abgabe in Moodle'}",
        f"- Teamabgabe: {'ja' if a['teamsubmission'] else 'nein'}",
        f"- Eigenständigkeitserklärung nötig: {'ja' if a.get('requiresubmissionstatement') else 'nein'}",
        f"- Jans Abgabestatus: {status}",
    ]
    zeilen += [f"- Anhang: {x}" for x in anhaenge]
    zeilen += ["", "Beschreibung:", html_zu_text(a.get("intro", "")) or "(keine)", ""]
    if anweisung := html_zu_text(a.get("activity", "")):
        zeilen += ["Arbeitsanweisungen:", anweisung, ""]
    return zeilen


STATUS_TEXT = {"submitted": "abgegeben", "draft": "Entwurf (noch nicht abgegeben)", "new": "nichts abgegeben"}


def _aufgaben(m, kurse_ordner: dict[int, tuple[str, Path]], stand: dict, neu: list[str]) -> None:
    for kurs in m.aufruf("mod_assign_get_assignments")["courses"]:
        if kurs["id"] not in kurse_ordner or not kurs["assignments"]:
            continue
        kursname, ordner = kurse_ordner[kurs["id"]]
        zeilen = [f"# Aufgaben: {kurs['fullname']}", ""]
        for a in kurs["assignments"]:
            s = m.aufruf("mod_assign_get_submission_status", assignid=a["id"]).get("lastattempt") or {}
            abgabe = s.get("teamsubmission") or s.get("submission") or {}
            status = STATUS_TEXT.get(abgabe.get("status"), abgabe.get("status") or "unbekannt")
            anhaenge = []
            for datei in a.get("introattachments", []):
                rel = Path(sicherer_name(kursname), "Aufgaben", sicherer_name(a["name"]), sicherer_name(datei["filename"]))
                if stand.get(datei["fileurl"]) != datei.get("timemodified") or not (ZIEL / rel).exists():
                    _laden(datei["fileurl"], m.token(), ZIEL / rel)
                    stand[datei["fileurl"]] = datei.get("timemodified")
                    neu.append(str(rel))
                _textfassung(ZIEL / rel, erneuern=False)
                anhaenge.append(str(rel.relative_to(sicherer_name(kursname))))
            zeilen += [z.replace("{url}", m.url) for z in aufgabe_als_text(a, status, anhaenge)]
        (ordner / "aufgaben.md").write_text("\n".join(zeilen), encoding="utf-8")


def _laden(url: str, token: str, ziel: Path) -> None:
    trenner = "&" if "?" in url else "?"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp = ziel.with_name(f".{ziel.name}.tmp")
    with urllib.request.urlopen(f"{url}{trenner}token={token}", timeout=300) as antwort, open(tmp, "wb") as f:
        shutil.copyfileobj(antwort, f)
    tmp.replace(ziel)


def spiegeln(m) -> list[str]:
    """Gleicht alle Kurse ab. Gibt neue oder geänderte Dateien zurück (relativ zu ZIEL).

    Beim ersten Abgleich (noch kein Stand) kommt eine leere Liste zurück, damit
    nicht der ganze Bestand als "neu" gemeldet wird.
    """
    erster = not STAND_DATEI.exists()
    neue_kurse = set()
    stand = json.loads(STAND_DATEI.read_text()) if not erster else {}
    neu = []
    vergeben = set()
    kurse = m.kurse()
    namen = [k["fullname"] for k in kurse]
    kurse_ordner = {}
    for k in kurse:
        kursname = k["fullname"] if namen.count(k["fullname"]) == 1 else f"{k['fullname']} ({k['id']})"
        kursordner = ZIEL / sicherer_name(kursname)
        kurse_ordner[k["id"]] = (kursname, kursordner)
        if not (kursordner / "uebersicht.md").exists():
            neue_kurse.add(sicherer_name(kursname))
        zeilen = [f"# {k['fullname']}", "", f"Moodle: {m.url}/course/view.php?id={k['id']}",
                  "Aufgaben mit Beschreibung, Fristen, Abgabeart und Status: aufgaben.md (falls vorhanden)", ""]
        for nr, abschnitt in enumerate(m.aufruf("core_course_get_contents", courseid=k["id"])):
            titel = abschnitt.get("name") or f"Abschnitt {nr}"
            abschnitt_ordner = f"{nr:02d} {sicherer_name(titel)}"
            zeilen += [f"## {titel}", ""]
            if text := html_zu_text(abschnitt.get("summary", "")):
                zeilen += [text, ""]
            for mod in abschnitt["modules"]:
                zeilen.append(f"- {mod['modname']}: {mod.get('name', '')}")
                if mod["modname"] == "url":
                    zeilen += [f"  Link: {c['fileurl']}" for c in mod.get("contents") or [] if c.get("fileurl")]
                if text := html_zu_text(mod.get("description", "")):
                    zeilen += [f"  {z}" for z in text.splitlines()]
                for c in mod.get("contents") or []:
                    if c.get("type") != "file":
                        continue
                    teile = [sicherer_name(t) for t in (c.get("filepath") or "/").split("/") if t]
                    unterordner = [sicherer_name(mod["name"])] if mod["modname"] == "folder" else []
                    rel = Path(sicherer_name(kursname), abschnitt_ordner, *unterordner, *teile,
                               sicherer_name(c["filename"]))
                    if rel in vergeben:  # gleicher Dateiname in zwei Moodle-Einträgen eines Abschnitts
                        rel = rel.with_name(f"{rel.stem} ({mod['id']}){rel.suffix}")
                    vergeben.add(rel)
                    mb = c.get("filesize", 0) / 1e6
                    if mb > grenze_mb(c["filename"]):
                        zeilen.append(f"  Datei (nicht geladen, {mb:.0f} MB): {c['filename']}")
                        continue
                    zeilen.append(f"  Datei: {rel.relative_to(sicherer_name(kursname))}")
                    schluessel = c["fileurl"]
                    geladen = stand.get(schluessel) != c.get("timemodified") or not (ZIEL / rel).exists()
                    if geladen:
                        _laden(c["fileurl"], m.token(), ZIEL / rel)
                        stand[schluessel] = c.get("timemodified")
                        neu.append(str(rel))
                        _speichern(stand)
                    if rel.suffix.lower() in MEDIEN_ENDUNGEN:
                        zeilen.append(f"  Transkript (wird nachts erstellt): {rel.relative_to(sicherer_name(kursname))}.txt")
                    if _textfassung(ZIEL / rel, erneuern=geladen):
                        art = "Inhaltsliste" if rel.suffix.lower() == ".zip" else "Textfassung"
                        zeilen.append(f"  {art}: {rel.relative_to(sicherer_name(kursname))}.txt")
            zeilen.append("")
        kursordner.mkdir(parents=True, exist_ok=True)
        (kursordner / "uebersicht.md").write_text("\n".join(zeilen), encoding="utf-8")
    _aufgaben(m, kurse_ordner, stand, neu)
    _speichern(stand)
    return [] if erster else [r for r in neu if r.split("/")[0] not in neue_kurse]


def _speichern(stand: dict) -> None:
    ZIEL.mkdir(parents=True, exist_ok=True)
    tmp = STAND_DATEI.with_suffix(".tmp")
    tmp.write_text(json.dumps(stand))
    tmp.replace(STAND_DATEI)
