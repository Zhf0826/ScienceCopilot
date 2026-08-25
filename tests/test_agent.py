import os
import sys
import unittest
from unittest import mock

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

    def test_companion_demo(self):
        res = agent.run(
            "companion",
            {"grade": "四年级", "topic": "水的蒸发", "goal": "理解蒸发"},
        )
        self.assertTrue(res["demo"])
        self.assertIn("随堂练习", res["result"])
        self.assertIn("评分量规", res["result"])
        self.assertTrue(any(a["tool"] == "retrieve_curriculum" for a in res["trace"] if a["type"] == "action"))

    def test_diagnose_demo(self):
        res = agent.run(
            "diagnose",
            {"grade": "四年级", "topic": "水的蒸发", "errors": "学生说水只有烧开才变水蒸气"},
        )
        self.assertTrue(res["demo"])
        self.assertIn("诊断题", res["result"])
        self.assertIn("课标依据", res["result"])

    def test_unknown_task_raises(self):
        with self.assertRaises(ValueError):
            agent.run("nope", {})


class TestAgentRealToolCalls(unittest.TestCase):
    """验证真实 function calling 分支构造的回传消息满足 OpenAI/豆包规范：
    每次工具调用都要带 id，且 role=tool 的消息要带 tool_call_id 指回它。
    这对应此前豆包报 `missing messages.tool_calls.id` 的修复。"""

    def test_tool_call_roundtrip_carries_ids(self):
        with mock.patch.object(agent.llm, "HAS_KEY", True), \
             mock.patch.object(agent.llm, "chat") as chat:
            # 第一轮返回工具调用，第二轮返回最终内容
            chat.side_effect = [
                {
                    "role": "assistant",
                    "content": "我先检索课标核心概念。",
                    "tool_calls": [
                        {
                            "id": "call_abc123",
                            "name": "retrieve_curriculum",
                            "arguments": {
                                "topic": "水的蒸发",
                                "grade": "4",
                                "goal": "理解蒸发",
                            },
                        }
                    ],
                },
                {"role": "assistant", "content": "最终探究方案……"},
            ]

            res = agent._run_real("sys", "user input", "水的蒸发", "材料")
            self.assertFalse(res["demo"])
            self.assertEqual(res["result"], "最终探究方案……")

            # 第二轮请求时，messages 里应含带 id 的 tool_calls 与带 tool_call_id 的 tool 消息
            messages = chat.call_args_list[1].args[0]
            assistant_tc = [
                m for m in messages
                if m.get("role") == "assistant" and m.get("tool_calls")
            ]
            self.assertEqual(len(assistant_tc), 1)
            tc = assistant_tc[0]["tool_calls"][0]
            self.assertEqual(tc["id"], "call_abc123")
            self.assertEqual(tc["type"], "function")

            tool_msgs = [m for m in messages if m.get("role") == "tool"]
            self.assertEqual(len(tool_msgs), 1)
            self.assertEqual(tool_msgs[0]["tool_call_id"], "call_abc123")


if __name__ == "__main__":
    unittest.main()
