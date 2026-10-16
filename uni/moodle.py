"""Moodle der HNEE (und der BFH Biel) lesen, wie die Moodle-App (nur lesend).

Anmeldung über login/token.php (Dienst moodle_mobile_app) mit HNEE_NUTZER und
HNEE_KENNWORT. Der Schlüssel liegt in data/moodle_token.json (chmod 600) und wird
neu geholt, wenn Moodle ihn ablehnt. Jan kann ihn im Moodle-Profil unter
"Sicherheitsschlüssel" widerrufen.

Fristen: Der Moodle-Kalender (action events) zeigte am 16.10.2026 eine fällige
Aufgabe nicht an. Deshalb werden Aufgaben und Tests direkt abgefragt.

BFH Biel (MoodleMitToken): Anmeldung nur per SSO (SWITCH edu-ID), login/token.php geht
nicht. Der App-Schlüssel wird einmal von Jan im Browser geholt (siehe STATUS.md) und
steht als BFH_MOODLE_TOKEN in .env. Läuft er ab, kommt MoodleFehler mit Hinweis.
"""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
TOKEN_DATEI = HIER / "data" / "moodle_token.json"


class MoodleFehler(Exception):
    pass


def _post(url: str, daten: dict) -> object:
    anfrage = urllib.request.Request(url, data=urllib.parse.urlencode(daten, doseq=True).encode())
    with urllib.request.urlopen(anfrage, timeout=60) as antwort:
        return json.load(antwort)


class Moodle:
    praefix = ""  # vor Fristen-IDs, damit sich IDs verschiedener Moodles nicht mischen

    def __init__(self, cfg: dict):
        self.url = cfg["MOODLE_URL"].rstrip("/")
        self.nutzer = cfg["HNEE_NUTZER"]
        self.kennwort = cfg["HNEE_KENNWORT"]
        self._token = None
        self._userid = None

    def _neuer_token(self) -> str:
        antwort = _post(f"{self.url}/login/token.php", {
            "username": self.nutzer, "password": self.kennwort, "service": "moodle_mobile_app"})
        if "token" not in antwort:
            raise MoodleFehler(f"Anmeldung fehlgeschlagen: {antwort.get('error', antwort)}")
        TOKEN_DATEI.parent.mkdir(exist_ok=True)
        fd = os.open(TOKEN_DATEI, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"token": antwort["token"]}, f)
        return antwort["token"]

    def token(self) -> str:
        if self._token is None:
            if TOKEN_DATEI.exists():
                self._token = json.loads(TOKEN_DATEI.read_text())["token"]
            else:
                self._token = self._neuer_token()
        return self._token

    def aufruf(self, funktion: str, **parameter) -> object:
        for versuch in (1, 2):
            antwort = _post(f"{self.url}/webservice/rest/server.php",
                            {"wstoken": self.token(), "wsfunction": funktion,
                             "moodlewsrestformat": "json", **parameter})
            if isinstance(antwort, dict) and "exception" in antwort:
                if antwort.get("errorcode") == "invalidtoken" and versuch == 1:
                    self._token = self._neuer_token()
                    continue
                raise MoodleFehler(f"{funktion}: {antwort.get('message')}")
            return antwort

    def userid(self) -> int:
        if self._userid is None:
            self._userid = self.aufruf("core_webservice_get_site_info")["userid"]
        return self._userid

    def kurse(self) -> list[dict]:
        return self.aufruf("core_enrol_get_users_courses", userid=self.userid())

    def fristen(self, ab: int) -> list[dict]:
        """Aufgaben und Tests, deren Frist oder Nachfrist nach `ab` (Unix-Zeit) liegt.

        Jeder Eintrag: id, art, kurs, name, faellig, letzte_abgabe (0 = keine), erledigt, url.
        """
        ergebnis = []
        for kurs in self.aufruf("mod_assign_get_assignments")["courses"]:
            for a in kurs["assignments"]:
                if max(a["duedate"], a["cutoffdate"]) <= ab:
                    continue
                ergebnis.append({
                    "id": f"{self.praefix}assign-{a['id']}", "art": "Aufgabe", "kurs": kurs["fullname"], "name": a["name"],
                    "faellig": a["duedate"], "letzte_abgabe": a["cutoffdate"],
                    "erledigt": self._aufgabe_abgegeben(a["id"]),
                    "url": f"{self.url}/mod/assign/view.php?id={a['cmid']}",
                })
        for q in self.aufruf("mod_quiz_get_quizzes_by_courses")["quizzes"]:
            if (q.get("timeclose") or 0) <= ab:
                continue
            versuche = self.aufruf("mod_quiz_get_user_attempts", quizid=q["id"], status="finished")
            ergebnis.append({
                "id": f"{self.praefix}quiz-{q['id']}", "art": "Test", "kurs": self._kursname(q["course"]), "name": q["name"],
                "faellig": q["timeclose"], "letzte_abgabe": 0, "erledigt": bool(versuche["attempts"]),
                "url": f"{self.url}/mod/quiz/view.php?id={q['coursemodule']}",
            })
        return ergebnis

    def _aufgabe_abgegeben(self, assignid: int) -> bool:
        s = self.aufruf("mod_assign_get_submission_status", assignid=assignid)
        versuch = s.get("lastattempt") or {}
        abgabe = versuch.get("teamsubmission") or versuch.get("submission") or {}
        return abgabe.get("status") == "submitted"

    def _kursname(self, kursid: int) -> str:
        if not hasattr(self, "_kursnamen"):
            self._kursnamen = {k["id"]: k["fullname"] for k in self.kurse()}
        return self._kursnamen.get(kursid, f"Kurs {kursid}")


class MoodleMitToken(Moodle):
    """Moodle mit festem App-Schlüssel (Hochschulen mit SSO). Neu holen kann nur Jan im Browser."""

    def __init__(self, url: str, token: str, praefix: str):
        self.url = url.rstrip("/")
        self._token = token
        self._userid = None
        self.praefix = praefix

    def _neuer_token(self) -> str:
        raise MoodleFehler(f"Schlüssel für {self.url} abgelaufen oder widerrufen. "
                           "Jan muss ihn im Browser neu holen (siehe uni/STATUS.md).")
