import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools


class TestTools(unittest.TestCase):
    def test_retrieve_tool(self):
        out = tools.execute("retrieve_curriculum", {"topic": "水的蒸发"})
        self.assertIn("检索到的课标参考", out)

    def test_safety_tool(self):
        out = tools.execute("check_safety", {"materials": "酒精灯 明火"})
        self.assertIn("安全", out)

    def test_unknown_tool(self):
        out = tools.execute("nope", {})
        self.assertIn("未知工具", out)

    def test_schemas_registered(self):
        names = [t["function"]["name"] for t in tools.TOOL_SCHEMAS]
        self.assertIn("retrieve_curriculum", names)
        self.assertIn("check_safety", names)


if __name__ == "__main__":
    unittest.main()
