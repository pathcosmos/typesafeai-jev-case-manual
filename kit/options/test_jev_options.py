"""jev_options.py 테스트: 선택지 찾기, 요청 모양, 가짜 점수, 표시, hook 입출력 (키, 네트워크 불필요)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jev_options as jo  # noqa: E402

KO = """R7 수정이 끝났습니다. 다음으로 할 수 있는 일:

1. **dynamic-agents 브랜치 push**: 리뷰용
2. **평가셋 라벨링**: 키 필요
3. Q3/Q6 결정

어느 것부터 진행할까요?"""

EN = """Two ways to fix this:
1) Retry the request in the client
2) Raise the timeout in the gateway
Which would you prefer?"""

STEPS = """Done. What I did:
1. Added the test
2. Fixed the harness
3. Ran 431 tests"""

CODE = """Which command should I run?
```bash
1. rm -rf build
2. make clean
```
Let me know."""

FAKE = {"JEV_OPTIONS": "fake"}


class ParseTests(unittest.TestCase):
    def test_korean_numbered_options_with_question_after(self):
        opts, ctx = jo.parse_options(KO)
        self.assertEqual(opts, ["dynamic-agents 브랜치 push: 리뷰용", "평가셋 라벨링: 키 필요", "Q3/Q6 결정"])
        self.assertIn("다음으로 할 수 있는 일", ctx)

    def test_english_paren_style_with_question(self):
        opts, _ = jo.parse_options(EN)
        self.assertEqual(opts, ["Retry the request in the client", "Raise the timeout in the gateway"])

    def test_step_list_without_choice_cue_is_skipped(self):
        self.assertIsNone(jo.parse_options(STEPS))

    def test_code_block_lines_are_ignored(self):
        self.assertIsNone(jo.parse_options(CODE))

    def test_single_item_or_empty_is_skipped(self):
        self.assertIsNone(jo.parse_options("Should I do this?\n1. only one"))
        self.assertIsNone(jo.parse_options(""))

    def test_cue_in_a_separate_paragraph_does_not_count(self):
        summary = "**What changed:**\n1. Scaffolds: fixed\n2. check.py: new check\n\n**Open questions:**\n- Which projects?"
        self.assertIsNone(jo.parse_options(summary))
        long_tail = "Done:\n1. a\n2. b\n\n" + "Next I will do many things. " * 10 + "Want me to go on?"
        self.assertIsNone(jo.parse_options(long_tail))

    def test_last_block_wins(self):
        text = "Plan:\n1. a\n2. b\n\nWhich next?\n1. push\n2. wait"
        self.assertEqual(jo.parse_options(text)[0], ["push", "wait"])


class RequestAndScoreTests(unittest.TestCase):
    def test_one_request_fan_out_and_model_pinned(self):
        req = jo.build_request(["a", "b", "c"], "do X", "ctx")
        self.assertEqual(req["model"], "jev-1.13.0")
        self.assertEqual(len(req["questions"]), 1 + 2 * 3)
        self.assertIn("none", req["questions"]["best_match"]["criteria"])  # no-match 선택지
        self.assertEqual(req["state"]["options"][2], {"n": 3, "text": "c"})
        # 모든 질문은 사람이 읽을 수 있는 완결된 문장이다 (id는 모델에 가지 않는다)
        for q in req["questions"].values():
            self.assertIn("`options`", q["instructions"])

    def test_fake_scores_are_deterministic_and_valid(self):
        req = jo.build_request(["a", "b"], "do X", "")
        r1, r2 = jo.fake_scores(req), jo.fake_scores(req)
        self.assertEqual(r1, r2)
        self.assertIn("FAKE", r1["model"])
        probs = r1["answers"]["best_match"]["probabilities"]
        self.assertEqual(set(probs), {"1", "2", "none"})
        self.assertAlmostEqual(sum(probs.values()), 1.0, delta=0.03)
        for k in ("in_scope_1", "reversible_2"):
            self.assertTrue(0 <= r1["answers"][k]["noul"] <= 1)

    def test_render_marks_fake_and_not_a_verdict(self):
        req = jo.build_request(["a", "b"], "", "")
        text = jo.render(["a", "b"], jo.fake_scores(req), "fake")
        self.assertTrue(text.startswith("[가짜 점수]"))
        self.assertIn("판정이 아님", text)
        self.assertIn("  1. a  ", text)


class HookTests(unittest.TestCase):
    def test_off_by_default(self):
        self.assertIsNone(jo.handle({"hook_event_name": "Stop", "last_assistant_message": KO}, {}))
        self.assertIsNone(jo.handle({"hook_event_name": "Stop", "last_assistant_message": KO}, {"JEV_OPTIONS": "jev"}))  # 실제 모드는 아직 없다

    def test_stop_claude_payload_with_transcript(self):
        tmp = Path(tempfile.mkdtemp()) / "t.jsonl"
        tmp.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
            {"type": "user", "message": {"content": "다음 작업 뭐가 있는지 확인해 줘"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "..."}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}},
        ]), encoding="utf-8")
        log = Path(tempfile.mkdtemp()) / "req.jsonl"
        out = jo.handle({"hook_event_name": "Stop", "last_assistant_message": KO, "transcript_path": str(tmp),
                         "stop_hook_active": False}, {**FAKE, "JEV_OPTIONS_LOG": str(log)})
        self.assertIn("[가짜 점수]", out["systemMessage"])
        self.assertIn("3. Q3/Q6 결정", out["systemMessage"])
        req = json.loads(log.read_text(encoding="utf-8").splitlines()[0])["request"]
        self.assertEqual(req["state"]["user"]["request"], "다음 작업 뭐가 있는지 확인해 줘")  # 도구 결과가 아닌 마지막 사용자 메시지

    def test_stop_codex_payload_without_transcript(self):
        out = jo.handle({"hook_event_name": "Stop", "last_assistant_message": EN, "turn_id": "t1", "stop_hook_active": False}, FAKE)
        self.assertIn("2. Raise the timeout", out["systemMessage"])

    def test_stop_hook_active_and_no_options_do_nothing(self):
        self.assertIsNone(jo.handle({"hook_event_name": "Stop", "last_assistant_message": KO, "stop_hook_active": True}, FAKE))
        self.assertIsNone(jo.handle({"hook_event_name": "Stop", "last_assistant_message": STEPS}, FAKE))

    def test_ask_user_question_message_and_optional_rewrite(self):
        ti = {"questions": [{"question": "Which color?", "header": "Color", "multiSelect": False,
                             "options": [{"label": "Red", "description": "warm"}, {"label": "Blue", "description": "cool"}]}]}
        p = {"hook_event_name": "PreToolUse", "tool_name": "AskUserQuestion", "tool_input": ti}
        out = jo.handle(p, FAKE)
        self.assertIn("1. Red — warm", out["systemMessage"])
        self.assertNotIn("hookSpecificOutput", out)  # 설명 수정은 기본 끔
        out = jo.handle(p, {**FAKE, "JEV_OPTIONS_REWRITE": "1"})
        new = out["hookSpecificOutput"]["updatedInput"]["questions"][0]["options"]
        self.assertTrue(new[0]["description"].startswith("[jev·가짜 부합 "))
        self.assertTrue(new[0]["description"].endswith("warm"))
        self.assertEqual(ti["questions"][0]["options"][0]["description"], "warm")  # 원본은 그대로
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")

    def test_cli_never_blocks_on_bad_input(self):
        for stdin in ("not json", "{}", json.dumps({"hook_event_name": "Stop", "last_assistant_message": KO})):
            p = subprocess.run([sys.executable, str(HERE / "jev_options.py")], input=stdin, capture_output=True, text=True,
                               env={"JEV_OPTIONS": "fake", "PATH": "/usr/bin:/bin"})
            self.assertEqual(p.returncode, 0, stdin)
        self.assertIn("systemMessage", p.stdout)


if __name__ == "__main__":
    unittest.main()
