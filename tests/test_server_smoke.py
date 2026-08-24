import json
import os
import sys
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as appmod
import config

BASE = "http://127.0.0.1:8099"


class TestServerSmoke(unittest.TestCase):
    server = None

    @classmethod
    def setUpClass(cls):
        config.HOST = "127.0.0.1"
        config.PORT = 8099
        cls.server = ThreadingHTTPServer((config.HOST, config.PORT), appmod.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()

    def _post(self, path, payload):
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    def test_status(self):
        with urllib.request.urlopen(BASE + "/api/status") as r:
            d = json.loads(r.read().decode("utf-8"))
        self.assertIn("demo", d)

    def test_inquiry(self):
        d = self._post(
            "/api/inquiry",
            {
                "grade": "四年级",
                "topic": "水的蒸发",
                "goal": "理解蒸发",
                "duration": "40分钟",
                "materials": "普通教室材料",
            },
        )
        self.assertIn("result", d)
        self.assertIn("trace", d)
        self.assertIn("retrieved", d)
        self.assertTrue(d["demo"])

    def test_audit(self):
        d = self._post(
            "/api/audit",
            {"content": "水只有烧开以后才会变成水蒸气，所以蒸发就是沸腾。"},
        )
        self.assertIn("审核结果", d["result"])

    def test_index(self):
        with urllib.request.urlopen(BASE + "/") as r:
            self.assertEqual(r.status, 200)
            self.assertIn("ScienceCopilot", r.read().decode("utf-8"))

    def test_intro(self):
        with urllib.request.urlopen(BASE + "/intro.html") as r:
            self.assertEqual(r.status, 200)


if __name__ == "__main__":
    unittest.main()
