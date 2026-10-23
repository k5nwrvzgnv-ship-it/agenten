"""Auswertung von Lias claude.ai-Chats: Welche wiederkehrenden Aufgaben lohnen sich für ihre Agenten?

Werkzeug, das Jan von Hand startet (kein Dienst, kein Timer). Rohdaten nur in data/ (ablage.py).
Aufruf: .venv/bin/python auswertung.py
Bisher wird nur data/ angelegt. Die Schritte (Export prüfen, filtern, anonymisieren, auswerten)
kommen einzeln nach Jans Okay dazu, Plan in STATUS.md.
"""

import ablage


def main() -> None:
    ordner = ablage.datenordner()
    print(f"Datenordner bereit: {ordner} (chmod 700)")


if __name__ == "__main__":
    main()
