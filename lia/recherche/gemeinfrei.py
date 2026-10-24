"""Ist eine Quelle gemeinfrei? Reine Funktion, ohne Netz.

Regel (Plan Examensreihe, Jan 25.10.2026):
- Gesetze sind amtliche Werke und nach § 5 Abs. 1 UrhG frei.
- Sonst frei, wenn alle beteiligten Personen (Autor, Herausgeber, Übersetzer) mindestens 70 volle
  Jahre tot sind: Todesjahr + 70 < Jahr. Wer 1955 starb, ist ab 2026 frei, wer 1956 starb, ab 2027.
- Fehlt ein Name oder ein Todesjahr, ist das Ergebnis "ungeklaert". Die Quelle darf dann nicht
  verwendet werden. Ist eine Person sicher noch geschützt, ist es "nicht_frei" (auch wenn eine
  andere zusätzlich ungeklärt ist).
- Gibt es ausdrücklich keine solche Person, steht statt des Namens <rolle>_entfaellt mit Grund
  (z. B. herausgeber_entfaellt = "Zeitschriftenaufsatz": bei einem Aufsatz zählt der Autor).
  Ein leerer Name bleibt ungeklärt.
"""

FRIST = 70
ROLLEN = (("autor", "Autor"), ("herausgeber", "Herausgeber"), ("uebersetzer", "Übersetzer"))


def pruefen(quelle: dict, jahr: int) -> dict:
    """{"status": "frei" | "nicht_frei" | "ungeklaert", "verwendbar": bool, "begruendung": str}"""
    if quelle.get("art") == "gesetz":
        return _ergebnis("frei", ["Gesetz, amtliches Werk nach § 5 Abs. 1 UrhG"])
    frei, geschuetzt, offen = [], [], []
    for feld, rolle in ROLLEN:
        grund = quelle.get(f"{feld}_entfaellt")
        if grund and feld not in quelle:
            frei.append(f"kein {rolle} ({grund})")
            continue
        if feld not in quelle:
            continue
        name = (quelle.get(feld) or "").strip()
        tod = quelle.get(f"todesjahr_{feld}" if feld == "autor" else f"{feld}_todesjahr")
        if not name:
            offen.append(f"{rolle} nicht geklärt")
        elif not isinstance(tod, int) or isinstance(tod, bool):
            offen.append(f"{rolle} {name}: Todesjahr fehlt")
        elif tod + FRIST < jahr:
            frei.append(f"{rolle} {name} gest. {tod}, frei seit {tod + FRIST + 1}")
        else:
            geschuetzt.append(f"{rolle} {name} gest. {tod}, geschützt bis Ende {tod + FRIST}")
    if not (geschuetzt or offen) and not any(" gest. " in f for f in frei):
        return _ergebnis("ungeklaert", ["Keine beteiligte Person angegeben"])
    if geschuetzt:
        return _ergebnis("nicht_frei", geschuetzt + offen + frei)
    if offen:
        return _ergebnis("ungeklaert", offen + frei)
    return _ergebnis("frei", frei)


def _ergebnis(status: str, gruende: list[str]) -> dict:
    return {"status": status, "verwendbar": status == "frei", "begruendung": "; ".join(gruende)}
