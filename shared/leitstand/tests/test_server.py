import http.client
import json
import os
import socket
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from agentkit import ereignis

import server


class UnixVerbindung(http.client.HTTPConnection):
    def __init__(self, pfad):
        super().__init__("localhost")
        self.pfad = pfad

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.pfad)


class TestServer(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ordner = self.tmp / "ereignisse"
        patches = [mock.patch.object(ereignis, "ORDNER", self.ordner),
                   mock.patch.object(server, "unit_namen", lambda: []),
                   mock.patch.object(server.freigabe, "offene", lambda: []),
                   mock.patch.object(server.freigabe, "unklare", lambda: []),
                   mock.patch.object(server.verbrauch, "letzter_stand", lambda: None)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.sock = self.tmp / "data" / "leitstand.sock"
        self.server = server.starten(self.sock)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def hole(self, pfad, methode="GET"):
        v = UnixVerbindung(str(self.sock))
        v.request(methode, pfad)
        r = v.getresponse()
        inhalt = r.read()
        v.close()
        return r.status, (json.loads(inhalt) if r.getheader("Content-Type", "").startswith("application/json") else inhalt)

    def test_socket_nur_fuer_agent(self):
        self.assertEqual(stat.S_IMODE(self.sock.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(self.sock).st_mode) & 0o077, 0)

    def test_seite_und_api(self):
        status, seite = self.hole("/")
        self.assertEqual(status, 200)
        self.assertIn(b"<title>Leitstand</title>", seite)
        ereignis.schreiben("lauf.gestartet", "uni", lauf="l1", daten={"pid": os.getpid()}, ordner=self.ordner)
        erstes = ereignis.lesen(ordner=self.ordner)[0]["id"]
        ereignis.schreiben("werkzeug", "uni", lauf="l1", daten={"name": "Read"}, ordner=self.ordner)

        status, laeufe = self.hole("/api/laeufe")
        self.assertEqual((status, laeufe[0]["id"], laeufe[0]["status"]), (200, "l1", "laeuft"))
        self.assertNotIn("ereignisse", laeufe[0])
        status, lauf = self.hole("/api/laeufe/l1")
        self.assertEqual((status, len(lauf["ereignisse"]), lauf["auftrag_daten"]), (200, 2, None))
        self.assertEqual(self.hole("/api/laeufe/gibtsnicht")[0], 404)

        status, neu = self.hole("/api/ereignisse?seit=" + erstes)
        self.assertEqual([e["typ"] for e in neu], ["werkzeug"])
        self.assertEqual(self.hole("/api/ereignisse?seit=quatsch")[0], 400)

        status, z = self.hole("/api/zustand")
        self.assertEqual((status, z["agenten"], z["verbrauch"]["stand"]), (200, [], None))

    def test_nur_lesen(self):
        self.assertEqual(self.hole("/api/laeufe", "POST")[0], 405)
        self.assertEqual(self.hole("/unbekannt")[0], 404)


if __name__ == "__main__":
    unittest.main()
