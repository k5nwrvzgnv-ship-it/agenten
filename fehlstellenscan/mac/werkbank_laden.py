"""Werkbank auf Jans Mac: Bilder, Markierung und Vorhersagen in FiftyOne laden, auswerten, Ansichten speichern
und die Oberfläche im Browser öffnen. Läuft nur in ~/fehlstellenscan/.venv-werkbank (Python 3.13, fiftyone;
Freigabe Jan 23.11.2026). Braucht werkbank.py, auswertung.py, masken.py, datensatz.py im Ordner darüber.
Anleitung: STATUS.md, Abschnitt „Werkbank (Mac)“.

Beispiele (in ~/fehlstellenscan, Umgebung .venv-werkbank an):
  python mac/werkbank_laden.py kodytek --datensatz datensaetze/kodytek-seg-1 --teil val \
      --vorhersage runs/segment/val-vorhersage/seg1/labels --name kodytek-seg1-val
  python mac/werkbank_laden.py kacheln --kacheln balken-felix/kacheln \
      --vorhersage runs/segment/balken-felix/vorhersage/labels --name balken-felix-iso800
  python mac/werkbank_laden.py zeigen --name kodytek-seg1-val
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fiftyone as fo  # noqa: E402
import fiftyone.brain as fob  # noqa: E402
from fiftyone import ViewField as F  # noqa: E402
from PIL import Image  # noqa: E402

import werkbank as w  # noqa: E402

KONF_AUSWERTUNG = 0.25      # wie yolo predict; Vorhersagen darunter bleiben sichtbar, zählen aber nicht


def detektionen(liste: list[dict]) -> fo.Detections:
    return fo.Detections(detections=[
        fo.Detection(label=o["name"], bounding_box=o["rechteck"], mask=o["maske"], confidence=o["konfidenz"],
                     klasse=o["klasse"], kurz_mm=o["kurz_mm"], lang_mm=o["lang_mm"], groesse=o["groesse"],
                     ast=o["ast"])
        for o in liste])


def neuer_datensatz(name: str, ersetzen: bool) -> fo.Dataset:
    if fo.dataset_exists(name):
        if not ersetzen:
            sys.exit(f"Datensatz {name} gibt es schon. Zum Neuladen --ersetzen, zum Ansehen: zeigen --name {name}")
        fo.delete_dataset(name)
    datensatz = fo.Dataset(name)
    datensatz.persistent = True
    return datensatz


def proben(bilder: list[Path], markierung: Path | None, vorhersage: Path | None) -> list[fo.Sample]:
    ergebnis = []
    for i, bild in enumerate(bilder, start=1):
        with Image.open(bild) as b:
            breite, hoehe = b.size
        probe = fo.Sample(filepath=str(bild.resolve()), nummer=bild.stem)
        if markierung is not None:
            probe["markierung"] = detektionen(w.datei_objekte(markierung / f"{bild.stem}.txt", breite, hoehe, False))
        if vorhersage is not None:
            probe["vorhersage"] = detektionen(w.datei_objekte(vorhersage / f"{bild.stem}.txt", breite, hoehe, True))
        ergebnis.append(probe)
        if i % 200 == 0:
            print(f"  {i} von {len(bilder)} Bildern gelesen")
    return ergebnis


def auswerten(datensatz: fo.Dataset) -> None:
    """Treffer/Fehlalarm/übersehen je Objekt (Masken-IoU 0,5 ab Konfidenz 0,25), verdächtige Labels, Ansichten."""
    sicher = datensatz.filter_labels("vorhersage", F("confidence") >= KONF_AUSWERTUNG, only_matches=False)
    ergebnis = sicher.evaluate_detections("vorhersage", gt_field="markierung", eval_key="eval", use_masks=True,
                                          iou=0.5, compute_mAP=True)
    ergebnis.print_report()
    print(f"mAP (Masken, COCO-Art über IoU 0,5-0,95): {ergebnis.mAP():.3f}")
    # Ohne Klassenzwang: zeigt, mit welcher Klasse ein Objekt verwechselt wird (Verwechslungsmatrix)
    sicher.evaluate_detections("vorhersage", gt_field="markierung", eval_key="eval_frei", use_masks=True,
                               iou=0.5, classwise=False)
    fob.compute_mistakenness(datensatz, "vorhersage", label_field="markierung")

    ast = F("ast") == True  # noqa: E712 – Ausdruck für FiftyOne, kein Python-Vergleich
    ansichten = {
        "1 übersehen": datensatz.filter_labels("markierung", F("eval") == "fn"),
        "2 Fehlalarme": datensatz.filter_labels("vorhersage", F("eval") == "fp"),
        "3 kleine Äste übersehen (unter 10 mm)":
            datensatz.filter_labels("markierung", (F("eval") == "fn") & ast & (F("kurz_mm") < 10)),
        "4 Klasse vertauscht": datensatz.filter_labels(
            "markierung", (F("eval") == "fn") & (F("eval_frei") == "tp")),
        "5 verdächtige Labels zuerst": datensatz.sort_by("mistakenness", reverse=True),
    }
    for name, ansicht in ansichten.items():
        datensatz.save_view(name, ansicht, overwrite=True)
    print("Gespeicherte Ansichten (oben links in der Oberfläche):", ", ".join(ansichten))


def zeigen(name: str) -> None:
    sitzung = fo.launch_app(fo.load_dataset(name))
    print("Oberfläche läuft (Browser: http://localhost:5151). Beenden mit ctrl-c.")
    sitzung.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    befehle = parser.add_subparsers(dest="befehl", required=True)
    k = befehle.add_parser("kodytek", help="Datensatzteil mit Markierung und Vorhersage laden und auswerten")
    k.add_argument("--datensatz", type=Path, required=True, help="z. B. datensaetze/kodytek-seg-1")
    k.add_argument("--teil", default="val", choices=["train", "val"], help="test bleibt gesperrt")
    k.add_argument("--vorhersage", type=Path, required=True, help="labels-Ordner von yolo segment predict")
    k.add_argument("--name", required=True)
    k.add_argument("--ersetzen", action="store_true")
    b = befehle.add_parser("kacheln", help="Bilder ohne Markierung mit Vorhersage laden (z. B. Balken-Kacheln)")
    b.add_argument("--kacheln", type=Path, required=True)
    b.add_argument("--vorhersage", type=Path, required=True)
    b.add_argument("--name", required=True)
    b.add_argument("--ersetzen", action="store_true")
    for p in (k, b):
        p.add_argument("--nur-laden", action="store_true", help="Oberfläche danach nicht öffnen")
    z = befehle.add_parser("zeigen", help="Oberfläche für einen geladenen Datensatz öffnen")
    z.add_argument("--name", required=True)
    args = parser.parse_args()

    if args.befehl == "zeigen":
        zeigen(args.name)
        return 0
    if args.befehl == "kodytek":
        bilder = w.bilder_finden(args.datensatz / "images" / args.teil)
        markierung = args.datensatz / "labels" / args.teil
    else:
        bilder, markierung = w.bilder_finden(args.kacheln), None
    if not bilder:
        sys.exit("keine Bilder gefunden")
    datensatz = neuer_datensatz(args.name, args.ersetzen)
    print(f"Lese {len(bilder)} Bilder ...")
    datensatz.add_samples(proben(bilder, markierung, args.vorhersage))
    if markierung is not None:
        auswerten(datensatz)
    if not args.nur_laden:
        zeigen(args.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
