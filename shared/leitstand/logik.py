"""Reine Logik des Leitstands (ohne Netz, ohne systemctl): Ereignisse zu Läufen, Zustand der Agenten.

Stufe 1 (28.10.2026): nur lesen. Eingriffe (Abbruch, Freigabe, Einstellungen) kommen erst in Stufe 2/3.
Lias Instanz: Läufe erscheinen nur mit Agent, Status und Zeit, ohne Auftrags- und Ergebnistext.
"""

# Sichtbare Namen der Units, die zum Agenten-System gehören (vinted-bot: nur Anzeige, CLAUDE.md)
ANZEIGE = {"agentenzentrale": "Zentrale", "lia-zentrale": "Lias Zentrale", "vinted-bot": "Vinted-Bot"}
TEXT_MAX = 600


def lauf_status(lauf: dict, lebt) -> str:
    """laeuft, ok, fehlgeschlagen, abgestuerzt oder fehler:<grund>."""
    if lauf.get("fehler"):
        return f"fehler:{lauf['fehler']}"
    if lauf.get("ende") is not None:
        return "ok" if lauf.get("ok") else "fehlgeschlagen"
    pid = lauf.get("pid")
    return "laeuft" if pid is None or lebt(pid) else "abgestuerzt"


def laeufe(ereignisse: list[dict], lebt=lambda pid: True) -> list[dict]:
    """Fasst lauf.*- und werkzeug-Ereignisse je Lauf zusammen, neueste zuerst.

    lebt(pid): ob der Agent-Prozess noch läuft (ohne lauf.beendet sonst "abgestuerzt").
    """
    nach_id: dict[str, dict] = {}
    for e in ereignisse:
        lid = e.get("lauf")
        if not lid or not (e["typ"].startswith("lauf.") or e["typ"] == "werkzeug"):
            continue
        lauf = nach_id.setdefault(lid, {
            "id": lid, "agent": e.get("agent"), "instanz": e.get("instanz"), "auftrag": e.get("auftrag"),
            "start": e["zeit"], "ende": None, "werkzeuge": 0, "ereignisse": [],
        })
        d = e.get("daten") or {}
        lauf["ereignisse"].append({"id": e["id"], "zeit": e["zeit"], "typ": e["typ"], "daten": d})
        if e["typ"] == "lauf.gestartet":
            lauf.update(start=e["zeit"], modell=d.get("modell"), stufe=d.get("stufe"), konto=d.get("konto"),
                        zeitgesteuert=d.get("zeitgesteuert"), pid=d.get("pid"))
        elif e["typ"] == "werkzeug":
            lauf["werkzeuge"] += 1
        elif e["typ"] == "lauf.beendet":
            lauf.update(ende=e["zeit"], ok=d.get("ok"), tokens=d.get("tokens"), dauer_s=d.get("dauer_s"),
                        usd=d.get("usd"), auslastung_5h=d.get("auslastung_5h"), auslastung_7d=d.get("auslastung_7d"))
        elif e["typ"] == "lauf.fehler":
            lauf.update(fehler=d.get("grund"), ende=lauf["ende"] or e["zeit"])
    ergebnis = sorted(nach_id.values(), key=lambda lauf: lauf["start"], reverse=True)
    for lauf in ergebnis:
        lauf["status"] = lauf_status(lauf, lebt)
    return ergebnis


def auftrag_anzeigen(auftrag: dict | None, instanz: str | None) -> dict | None:
    """Teil eines Auftrags für die Anzeige. Lias Instanz: ohne Texte."""
    if not auftrag:
        return None
    teil = {k: auftrag.get(k) for k in ("id", "agent", "quelle", "modus", "status", "erstellt", "abgeschlossen",
                                        "von", "bezug")}
    if instanz is None:
        teil["text"] = (auftrag.get("text") or "")[:TEXT_MAX]
        teil["ergebnis"] = (auftrag.get("ergebnis") or "")[:TEXT_MAX]
    return teil


def systemctl_lesen(ausgabe: str) -> dict[str, dict]:
    """Ausgabe von `systemctl --user show -p Id,... <units>` (Blöcke durch Leerzeilen) -> {Id: {Feld: Wert}}."""
    units = {}
    for block in ausgabe.strip().split("\n\n"):
        felder = dict(z.split("=", 1) for z in block.splitlines() if "=" in z)
        if felder.get("Id"):
            units[felder["Id"]] = felder
    return units


def dienst_zustand(service: dict | None, timer: dict | None) -> dict:
    """Zustand eines Dienstes aus systemctl-Feldern: laeuft, wartet (Timer), bereit, gestoert, unbekannt."""
    if not service:
        return {"zustand": "unbekannt"}
    if service.get("ActiveState") in ("active", "activating", "reloading"):
        zustand = "laeuft"
    elif service.get("ActiveState") == "failed" or service.get("Result") not in (None, "success"):
        zustand = "gestoert"
    else:
        zustand = "bereit"
    d = {"zustand": zustand, "seit": service.get("StateChangeTimestamp") or None}
    if timer and timer.get("ActiveState") == "active":
        d["naechster_lauf"] = timer.get("NextElapseUSecRealtime") or None
    return d


def agenten(unit_namen: list[str], units: dict[str, dict], alle_laeufe: list[dict], offene: list[dict],
            unklare: list[dict]) -> list[dict]:
    """Karten für die Netz-Ansicht: je Dienst (ohne ausfall@) ein Eintrag mit Zustand, letztem Lauf, Freigaben."""
    namen = sorted({n.rsplit(".", 1)[0] for n in unit_namen if not n.startswith("ausfall@")})
    karten = []
    for name in namen:
        agent = name.removeprefix("lia-")
        instanz = "lia" if name.startswith("lia-") and name != "lia-zentrale" else None
        if name in ("agentenzentrale", "lia-zentrale", "vinted-bot", "sicherung"):
            agent = None
        letzter = next((lauf for lauf in alle_laeufe if agent and lauf["agent"] == agent
                        and lauf.get("instanz") == instanz), None)
        karte = {
            "name": name, "anzeige": ANZEIGE.get(name, name), "agent": agent, "instanz": instanz,
            "nur_anzeige": name == "vinted-bot",
            **dienst_zustand(units.get(f"{name}.service"), units.get(f"{name}.timer")),
            "letzter_lauf": letzter and {k: letzter.get(k) for k in ("id", "start", "status")},
            "freigaben_offen": sum(1 for f in offene if instanz is None and f.get("agent") == agent),
            "unklar": sum(1 for f in unklare if instanz is None and f.get("agent") == agent),
        }
        if karte["zustand"] != "gestoert" and letzter and letzter["status"] == "laeuft":
            karte["zustand"] = "laeuft"
        karten.append(karte)
    return karten


def verbrauch_anzeigen(stand: dict | None, stufe: str, quelle: str) -> dict:
    """Abo-Auslastung für die Kopfzeile. Stand nur aus Agenten-Läufen: Zeit des Stands mitgeben."""
    if not stand:
        return {"stufe": stufe, "konto": quelle, "stand": None}
    return {"stufe": stufe, "konto": quelle, "stand": stand.get("zeit"),
            "5h": round((stand.get("5h") or 0) * 100), "7d": round((stand.get("7d") or 0) * 100)}
