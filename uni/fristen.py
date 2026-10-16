"""Fristen-Erinnerungen: wann wird woran erinnert (ohne Netz, testbar).

Stufen (mit Jan abgesprochen am 16.10.2026): 7 Tage vorher, 2 Tage vorher und am
Tag selbst. Gezählt wird in Kalendertagen. Pro Frist und Stufe kommt höchstens
eine Erinnerung. Wird eine Stufe verpasst (z. B. Aufgabe erst 1 Tag vorher
erschienen), kommt nur die jüngste fällige Stufe.

Maßgeblich ist die Fälligkeit. Ist sie vorbei, aber eine spätere letzte Abgabe
(Nachfrist) erlaubt, gilt die Nachfrist. Abgegebene Fristen werden übergangen.
Ändert sich der Termin in Moodle, wird neu erinnert (der Termin steht im Schlüssel).
"""

from datetime import datetime

STUFEN = (7, 2, 0)


def termin(frist: dict, jetzt: int) -> tuple[int, bool] | None:
    """(Zeitpunkt, ist_nachfrist) oder None, wenn nichts mehr abgegeben werden kann."""
    if frist["faellig"] > jetzt:
        return frist["faellig"], False
    if frist.get("letzte_abgabe", 0) > jetzt:
        return frist["letzte_abgabe"], True
    return None


def tage_bis(zeitpunkt: int, jetzt: int) -> int:
    return (datetime.fromtimestamp(zeitpunkt).date() - datetime.fromtimestamp(jetzt).date()).days


def faellige_erinnerungen(fristen: list[dict], erinnert: set[str], jetzt: int) -> list[tuple[str, dict, int, bool]]:
    """Liefert (schluessel, frist, tage, ist_nachfrist) für jede jetzt fällige Erinnerung.

    `erinnert` sind die Schlüssel bereits verschickter Erinnerungen. Der Aufrufer
    trägt die gelieferten Schlüssel nach dem Melden dort ein.
    """
    ergebnis = []
    for f in fristen:
        if f.get("erledigt"):
            continue
        t = termin(f, jetzt)
        if t is None:
            continue
        zeitpunkt, nachfrist = t
        tage = tage_bis(zeitpunkt, jetzt)
        stufe = min((s for s in STUFEN if tage <= s), default=None)
        if stufe is None:
            continue
        schluessel = f"{f['id']}@{zeitpunkt}:{stufe}"
        # Eine kleinere Stufe ersetzt größere: wer schon "2 Tage" bekam, braucht kein "7 Tage" mehr.
        schon = {f"{f['id']}@{zeitpunkt}:{s}" for s in STUFEN if s <= stufe}
        if schon & erinnert:
            continue
        ergebnis.append((schluessel, f, tage, nachfrist))
    return ergebnis


def als_text(frist: dict, tage: int, nachfrist: bool, zeitpunkt: int) -> str:
    wann = datetime.fromtimestamp(zeitpunkt).strftime("%d.%m. %H:%M")
    bis = "heute" if tage == 0 else "morgen" if tage == 1 else f"in {tage} Tagen"
    art = "Nachfrist endet" if nachfrist else "fällig"
    return f"{frist['art']} {art} {bis} ({wann}): {frist['name']}\nKurs: {frist['kurs']}\n{frist['url']}"
