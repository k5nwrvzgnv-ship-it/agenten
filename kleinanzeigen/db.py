"""SQLite-Speicher: Suchen je Nutzer, gesehene Anzeigen, Tageszähler der Claude-Läufe."""

import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS suchen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    titel TEXT NOT NULL,
    beschreibung TEXT NOT NULL,
    begriffe TEXT NOT NULL,          -- JSON-Liste
    ausschluss TEXT NOT NULL,        -- JSON-Liste
    max_preis REAL,
    marktwert REAL,
    plz TEXT,
    ort_id INTEGER,
    umkreis_km INTEGER,
    status TEXT NOT NULL,            -- entwurf | aktiv | pause
    erstellt REAL NOT NULL,
    letzter_lauf REAL
);
CREATE TABLE IF NOT EXISTS gesehen (
    suche_id INTEGER NOT NULL,
    anzeige_id INTEGER NOT NULL,
    preis REAL,
    zeit REAL NOT NULL,
    PRIMARY KEY (suche_id, anzeige_id)
);
CREATE TABLE IF NOT EXISTS zaehler (
    tag TEXT PRIMARY KEY,
    laeufe INTEGER NOT NULL DEFAULT 0,
    grenze_gemeldet INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS werte (
    schluessel TEXT PRIMARY KEY,
    wert TEXT
);
"""


class Speicher:
    def __init__(self, pfad: Path | str):
        if str(pfad) != ":memory:":
            Path(pfad).parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(pfad), check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)

    # ---------- Suchen ----------

    def suche_anlegen(self, chat_id: int, daten: dict) -> int:
        cur = self.con.execute(
            "INSERT INTO suchen (chat_id, titel, beschreibung, begriffe, ausschluss, max_preis, marktwert, "
            "status, erstellt) VALUES (?, ?, ?, ?, ?, ?, ?, 'entwurf', ?)",
            (chat_id, daten["titel"], daten["beschreibung"], json.dumps(daten["begriffe"], ensure_ascii=False),
             json.dumps(daten["ausschluss"], ensure_ascii=False), daten.get("max_preis"), daten.get("marktwert"),
             time.time()))
        self.con.commit()
        return cur.lastrowid

    def _suche(self, zeile) -> dict | None:
        if zeile is None:
            return None
        s = dict(zeile)
        s["begriffe"] = json.loads(s["begriffe"])
        s["ausschluss"] = json.loads(s["ausschluss"])
        return s

    def suche(self, suche_id: int, chat_id: int | None = None) -> dict | None:
        """Eine Suche; mit chat_id nur, wenn sie diesem Nutzer gehört."""
        if chat_id is None:
            z = self.con.execute("SELECT * FROM suchen WHERE id = ?", (suche_id,)).fetchone()
        else:
            z = self.con.execute("SELECT * FROM suchen WHERE id = ? AND chat_id = ?", (suche_id, chat_id)).fetchone()
        return self._suche(z)

    def suchen(self, chat_id: int | None = None, status: str | None = None) -> list[dict]:
        sql, werte = "SELECT * FROM suchen WHERE 1=1", []
        if chat_id is not None:
            sql += " AND chat_id = ?"
            werte.append(chat_id)
        if status:
            sql += " AND status = ?"
            werte.append(status)
        return [self._suche(z) for z in self.con.execute(sql + " ORDER BY id", werte)]

    def entwurf(self, chat_id: int) -> dict | None:
        """Neueste Suche des Nutzers, die noch auf Preis und Ort wartet."""
        z = self.con.execute("SELECT * FROM suchen WHERE chat_id = ? AND status = 'entwurf' ORDER BY id DESC",
                             (chat_id,)).fetchone()
        return self._suche(z)

    def suche_aendern(self, suche_id: int, **felder) -> None:
        erlaubt = {"max_preis", "plz", "ort_id", "umkreis_km", "status", "letzter_lauf", "titel"}
        if not felder or set(felder) - erlaubt:
            raise ValueError(f"Unbekannte Felder: {set(felder) - erlaubt}")
        sets = ", ".join(f"{k} = ?" for k in felder)
        self.con.execute(f"UPDATE suchen SET {sets} WHERE id = ?", (*felder.values(), suche_id))
        self.con.commit()

    def suche_loeschen(self, suche_id: int) -> None:
        self.con.execute("DELETE FROM gesehen WHERE suche_id = ?", (suche_id,))
        self.con.execute("DELETE FROM suchen WHERE id = ?", (suche_id,))
        self.con.commit()

    def entwuerfe_verwerfen(self, chat_id: int) -> None:
        """Alte Entwürfe des Nutzers weg, wenn er eine neue Suche beginnt."""
        for s in self.suchen(chat_id, "entwurf"):
            self.suche_loeschen(s["id"])

    # ---------- gesehene Anzeigen ----------

    def gesehen_ids(self, suche_id: int) -> set[int]:
        return {z[0] for z in self.con.execute("SELECT anzeige_id FROM gesehen WHERE suche_id = ?", (suche_id,))}

    def gesehen_merken(self, suche_id: int, anzeigen: list[tuple[int, float | None]]) -> None:
        jetzt = time.time()
        self.con.executemany("INSERT OR IGNORE INTO gesehen (suche_id, anzeige_id, preis, zeit) VALUES (?, ?, ?, ?)",
                             [(suche_id, aid, preis, jetzt) for aid, preis in anzeigen])
        self.con.commit()

    def preise(self, suche_id: int, max_anzahl: int = 300) -> list[float]:
        return [z[0] for z in self.con.execute(
            "SELECT preis FROM gesehen WHERE suche_id = ? AND preis IS NOT NULL ORDER BY zeit DESC LIMIT ?",
            (suche_id, max_anzahl))]

    def gesehen_aufraeumen(self, aelter_als_tage: int = 60) -> None:
        self.con.execute("DELETE FROM gesehen WHERE zeit < ?", (time.time() - aelter_als_tage * 86400,))
        self.con.commit()

    # ---------- Tageszähler ----------

    def laeufe(self, tag: str) -> int:
        z = self.con.execute("SELECT laeufe FROM zaehler WHERE tag = ?", (tag,)).fetchone()
        return z[0] if z else 0

    def lauf_zaehlen(self, tag: str) -> int:
        self.con.execute("INSERT INTO zaehler (tag, laeufe) VALUES (?, 1) "
                         "ON CONFLICT(tag) DO UPDATE SET laeufe = laeufe + 1", (tag,))
        self.con.commit()
        return self.laeufe(tag)

    def grenze_erstmals(self, tag: str) -> bool:
        """True genau einmal pro Tag (für die Meldung 'Tagesgrenze erreicht')."""
        self.con.execute("INSERT OR IGNORE INTO zaehler (tag) VALUES (?)", (tag,))
        cur = self.con.execute("UPDATE zaehler SET grenze_gemeldet = 1 WHERE tag = ? AND grenze_gemeldet = 0",
                               (tag,))
        self.con.commit()
        return cur.rowcount == 1

    # ---------- einfache Werte ----------

    def wert(self, schluessel: str) -> str | None:
        z = self.con.execute("SELECT wert FROM werte WHERE schluessel = ?", (schluessel,)).fetchone()
        return z[0] if z else None

    def wert_setzen(self, schluessel: str, wert: str | None) -> None:
        self.con.execute("INSERT INTO werte (schluessel, wert) VALUES (?, ?) "
                         "ON CONFLICT(schluessel) DO UPDATE SET wert = excluded.wert", (schluessel, wert))
        self.con.commit()
