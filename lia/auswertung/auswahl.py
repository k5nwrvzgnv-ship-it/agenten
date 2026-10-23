"""Lias Chats aus dem Export herausfiltern (Schritt 4).

chatliste: eine Zeile je Chat (Nummer, Datum, Titel, Zahl der Prompts, Vorschlag Lia/Jan/unklar).
  Der Vorschlag zählt Stichwörter in Titel und erstem Prompt. Jan oder Lia korrigieren die Spalte wer in
  data/chatliste.tsv, erst dann wird gefiltert. Werte: Lia (wird ausgewertet), Jan, privat (Haushalt,
  Familie, Gesundheit, egal von wem: nicht ausgewertet), leer (Chat ohne Text im Export), unklar. Ausgegeben werden nur Titel, keine Prompts (Einwilligung).
Felder laut Export vom 23.10.2026: uuid, name, created_at, chat_messages[].sender (human/assistant).
Der Text steht in .text, bei 912 von 5687 Nachrichten nur in .content[] (Blöcke mit type "text").
Ohne Netz, getestet in tests/test_auswahl.py.
"""

import re

LIA = ["unterricht", "klasse", "schüler", "schueler", "arbeitsblatt", "ethik", "philosophie", "lehrplan",
       "elternbrief", "eltern", "zeugnis", "klausur", "klassenarbeit", "tafelbild", "stundenentwurf",
       "unterrichtsstunde", "fachkonferenz", "kollegium", "schule", "lehrkraft", "erwartungshorizont",
       "bewertungsraster", "kant", "moral", "sek i", "lernziel"]
JAN = ["hnee", "holzschutz", "vorlesung", "moodle", "studium", "python", "server", "linux", "git ",
       "telegram", "agent", "skript", "code", "vinted", "kcal", "systemd", "claude code"]
SPALTEN = ["nr", "uuid", "datum", "titel", "prompts", "wer"]
AUSGESCHLOSSEN = {"jan", "privat", "leer"}


def _treffer(text: str, woerter: list[str]) -> int:
    text = text.lower()
    return sum(1 for w in woerter if w in text)


def nachricht_text(nachricht: dict) -> str:
    """Text einer Nachricht: .text, sonst die text-Blöcke aus .content."""
    if (nachricht.get("text") or "").strip():
        return nachricht["text"]
    bloecke = [b.get("text") or "" for b in nachricht.get("content") or [] if b.get("type") == "text"]
    return "\n".join(b for b in bloecke if b)


def vorschlag(gespraech: dict) -> str:
    """Lia, Jan oder unklar, nach Stichwörtern in Titel und erstem Prompt."""
    prompts = [nachricht_text(n) for n in gespraech.get("chat_messages") or [] if n.get("sender") == "human"]
    text = f"{gespraech.get('name') or ''} {prompts[0] if prompts else ''}"
    lia, jan = _treffer(text, LIA), _treffer(text, JAN)
    if lia > jan:
        return "Lia"
    if jan > lia:
        return "Jan"
    return "unklar"


def _zelle(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def chatliste(gespraeche: list[dict]) -> str:
    """Tabelle (TSV) zum Korrigieren, älteste zuerst."""
    zeilen = ["\t".join(SPALTEN)]
    for nr, g in enumerate(sorted(gespraeche, key=lambda g: g.get("created_at") or ""), start=1):
        prompts = sum(1 for n in g.get("chat_messages") or [] if n.get("sender") == "human")
        zeilen.append("\t".join([str(nr), _zelle(g.get("uuid")), (g.get("created_at") or "")[:10],
                                 _zelle(g.get("name")) or "(ohne Titel)", str(prompts), vorschlag(g)]))
    return "\n".join(zeilen) + "\n"


def bestaetigte_lia(tsv: str) -> set[str]:
    """UUIDs mit wer = Lia. Bricht ab, solange eine Zeile noch unklar ist."""
    zeilen = tsv.strip().splitlines()
    if not zeilen or zeilen[0].split("\t") != SPALTEN:
        raise ValueError("chatliste.tsv hat nicht die erwarteten Spalten")
    lia, unklar = set(), []
    for zeile in zeilen[1:]:
        felder = zeile.split("\t")
        if len(felder) != len(SPALTEN):
            raise ValueError(f"Zeile kaputt: {zeile[:40]!r}")
        wer = felder[5].strip().lower()
        if wer == "lia":
            lia.add(felder[1])
        elif wer not in AUSGESCHLOSSEN:
            unklar.append(felder[0])
    if unklar:
        raise ValueError(f"Noch nicht entschieden (Nr.): {', '.join(unklar)}")
    return lia


def filtern(gespraeche: list[dict], lia: set[str]) -> list[dict]:
    """Nur Lias Chats. Bricht ab, wenn eine bestätigte UUID im Export fehlt (falsche Liste)."""
    behalten = [g for g in gespraeche if g.get("uuid") in lia]
    fehlen = lia - {g["uuid"] for g in behalten}
    if fehlen:
        raise ValueError(f"{len(fehlen)} bestätigte Chats fehlen im Export")
    return behalten
