import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent
import llm


class TestAgent(unittest.TestCase):
    def setUp(self):
        self._orig = llm.HAS_KEY
        llm.HAS_KEY = False  # 强制走演示分支，测试不依赖外部 API

    def tearDown(self):
        llm.HAS_KEY = self._orig

    def test_inquiry_demo(self):
        data = {
            "grade": "四年级",
            "topic": "水的蒸发",
            "goal": "理解蒸发",
            "duration": "40分钟",
            "materials": "普通教室材料，避免明火",
        }
        res = agent.run("inquiry", data)
        self.assertTrue(res["demo"])
        self.assertIn("探究主题", res["result"])
        actions = [s for s in res["trace"] if s["type"] == "action"]
        self.assertTrue(any(a["tool"] == "retrieve_curriculum" for a in actions))
        self.assertTrue(any(a["tool"] == "check_safety" for a in actions))

    def test_audit_demo_misconception(self):
        res = agent.run(
            "audit",
            {"content": "水只有烧开以后才会变成水蒸气，所以蒸发就是沸腾。"},
        )
        self.assertIn("审核结果", res["result"])
        self.assertIn("蒸发", res["result"])
        self.assertTrue(res["trace"])


if __name__ == "__main__":
    unittest.main()
