import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rag


class TestRag(unittest.TestCase):
    def test_retrieve_hits_water(self):
        hits = rag.retrieve("四年级 水的蒸发 理解蒸发")
        self.assertTrue(hits, "应检索到相关课标片段")
        self.assertEqual(hits[0]["id"], "water-evaporation")
        self.assertIn("蒸发", hits[0]["matched_keywords"])

    def test_retrieve_returns_list(self):
        hits = rag.retrieve("zzz 不存在的主题 123")
        self.assertIsInstance(hits, list)

    def test_check_safety_open_flame(self):
        hits = rag.check_safety("使用酒精灯加热")
        self.assertTrue(any(h["label"] == "明火 / 高温" for h in hits))

    def test_check_safety_safe(self):
        hits = rag.check_safety("用普通纸张记录实验结果")
        self.assertEqual(hits, [])

    def test_check_safety_negation(self):
        # "避免明火" 应视为已规避，而非存在风险。
        hits = rag.check_safety("普通教室材料，避免明火")
        self.assertFalse(any(h["label"] == "明火 / 高温" for h in hits))


if __name__ == "__main__":
    unittest.main()
