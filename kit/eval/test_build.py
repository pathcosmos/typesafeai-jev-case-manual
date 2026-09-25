"""build.py 테스트: Python state 어댑터로 확인한다 (키, 네트워크 불필요). 예시(examples/triage)가 measure dry-run과 replay까지 통과하는지도 본다."""
from __future__ import annotations

import copy
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD, REPLAY, MEASURE = HERE / "build.py", HERE / "replay.py", HERE.parent / "measure" / "measure.py"
EX = HERE / "examples" / "triage"
sys.path.insert(0, str(HERE))
from build import merge  # noqa: E402

PY = shlex.quote(sys.executable)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.doc = json.loads((EX / "cases.json").read_text(encoding="utf-8"))

    def build(self, doc=None, state_cmd=None, *extra):
        (self.tmp / "cases.json").write_text(json.dumps(doc or self.doc, ensure_ascii=False), encoding="utf-8")
        p = subprocess.run([sys.executable, str(BUILD), "--cases", str(self.tmp / "cases.json"),
                            "--questions", str(EX / "questions.json"),
                            "--state-cmd", state_cmd or f"{PY} {shlex.quote(str(EX / 'state.py'))}",
                            "--out-dir", str(self.tmp / "out"), "--report", str(self.tmp / "report.json"), *extra],
                           capture_output=True, text=True)
        rep = json.loads((self.tmp / "report.json").read_text()) if (self.tmp / "report.json").exists() else None
        return p, rep

    def samples(self, split):
        return [json.loads(l) for l in (self.tmp / "out" / f"samples.{split}.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_example_builds_clean_with_ids_pairs_and_merge(self):
        p, rep = self.build(None, None, "--require-lang", "ko")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(rep["warnings"], [])
        self.assertEqual(rep["counts"]["samples"], 15)
        tune = {r["id"]: r for r in self.samples("tune")}
        # 변형이 둘 이상이면 -언어 접미사, 하나면 케이스 id 그대로
        self.assertIn("c01-ko", tune)
        self.assertIn("c03", tune)
        self.assertEqual(tune["c01-ko"]["pair"], "c01")
        self.assertIsNone(tune["c03"]["pair"])
        self.assertEqual(tune["c03"]["lang"], "en")  # default_lang
        # 공유 input(channel)과 변형(message)이 합쳐져 state가 된다
        self.assertEqual(tune["c01-ko"]["state"]["ticket"]["channel"], "email")
        self.assertIn("두 번", tune["c01-ko"]["state"]["ticket"]["message"])
        self.assertEqual(set(tune["c01-ko"]), {"id", "state", "label", "gold", "lang", "pair", "split", "category"})

    def test_output_feeds_measure_and_replay(self):
        p, _ = self.build()
        self.assertEqual(p.returncode, 0, p.stderr)
        for split in ("tune", "test"):
            s = self.tmp / "out" / f"samples.{split}.jsonl"
            m = subprocess.run([sys.executable, str(MEASURE), "--questions", str(EX / "questions.json"), "--samples", str(s),
                                "--dry-run", "--out", str(self.tmp / "m.json")], capture_output=True, text=True)
            self.assertEqual(m.returncode, 0, m.stderr)
            self.assertNotIn("warning", m.stderr)
            # 라벨로 만든 이상적인 답 -> 예시 정책 -> replay (배선 확인)
            per = []
            for r in self.samples(split):
                ans = {"topic": {"choice": r["label"]["topic"], "confidence": 0.9}}
                ans["refund_requested"] = {"noul": 0.9 if r["label"].get("refund_requested") else 0.1}
                per.append({"id": r["id"], "status": "ok", "answers": ans})
            (self.tmp / "oracle.json").write_text(json.dumps({"per_sample": per, "models": ["ORACLE"]}), encoding="utf-8")
            rp = subprocess.run([sys.executable, str(REPLAY), "--measure", str(self.tmp / "oracle.json"), "--samples", str(s),
                                 "--policy-cmd", f"{PY} {shlex.quote(str(EX / 'policy.py'))}", "--escalate", "human",
                                 "--decisions", "billing,orders,human", "--out", str(self.tmp / "r.json")], capture_output=True, text=True)
            self.assertEqual(rp.returncode, 0, rp.stderr)
            out = json.loads((self.tmp / "r.json").read_text())
            self.assertEqual(out["overall"]["errors_among_decided"], 0, (split, out["overall"]["error_ids"]))
            self.assertIn("adversarial", out["by_category"])

    def test_case_errors_write_nothing(self):
        bad = copy.deepcopy(self.doc)
        bad["cases"].append(copy.deepcopy(bad["cases"][0]))                      # 중복 id
        bad["cases"][2]["gold"] = "refunds"                                       # gold_values 밖
        bad["cases"][3]["label"] = {"topik": "billing"}                           # 모르는 라벨 키
        bad["cases"][4]["label"] = {"topic": "other", "refund_requested": "no"}   # noul 타입
        del bad["cases"][5]["split"]                                              # split 없음
        p, rep = self.build(bad)
        self.assertEqual(p.returncode, 3)
        e = "\n".join(rep["errors"])
        for needle in ("중복 케이스 id", "'refunds'", "'topik'", "true/false", "split가 없다"):
            self.assertIn(needle, e)
        self.assertFalse((self.tmp / "out").exists())

    def test_state_adapter_failures(self):
        cases = {
            "null_state": "import sys,json\nfor l in sys.stdin: print(json.dumps({'id': json.loads(l)['id'], 'state': None}))",
            "missing": "import sys\nsys.stdin.read()",
            "crash": "raise SystemExit(1)",
            "not_json": "print('x')",
        }
        for name, code in cases.items():
            (self.tmp / f"{name}.py").write_text(code, encoding="utf-8")
            p, rep = self.build(None, f"{PY} {shlex.quote(str(self.tmp / (name + '.py')))}")
            self.assertEqual(p.returncode, 5, name)
            self.assertEqual(rep["status"], "state_error", name)
        # 예시 state 함수는 빈 메시지에 None을 준다 -> 표본이 될 수 없다
        doc = copy.deepcopy(self.doc)
        doc["cases"][2]["input"]["message"] = "   "
        p, rep = self.build(doc)
        self.assertEqual(p.returncode, 5)
        self.assertIn("null", rep["errors"][0])

    def test_warnings(self):
        doc = copy.deepcopy(self.doc)
        doc["cases"] = [c for c in doc["cases"] if c["category"] not in ("adversarial", "boundary") and c.get("lang") != "ko"]
        for c in doc["cases"]:
            c.pop("variants", None)
            c.setdefault("input", {})["message"] = "Refund to jane@example.com please, call 010-1234-5678 or curl https://x.corp"
        doc["cases"] = [c for c in doc["cases"] if not (c["split"] == "test" and c["gold"] == "orders")]
        p, rep = self.build(doc, None, "--require-lang", "ko", "--budget", "2")
        self.assertEqual(p.returncode, 0, p.stderr)
        w = "\n".join(rep["warnings"])
        for needle in ("'adversarial'", "'boundary'", "언어 'ko'", "split 'test'에 gold ['orders']", "요청 예산 2",
                       "Cloudflare", "email", "phone", "internal_host"):
            self.assertIn(needle, w)
        self.assertIn("warning:", p.stderr)

    def test_translation_only_korean_slice_warns(self):
        doc = copy.deepcopy(self.doc)
        doc["cases"] = [c for c in doc["cases"] if c.get("lang") != "ko"]  # 원문 ko 케이스를 빼면 번역 쌍만 남는다
        p, rep = self.build(doc, None, "--require-lang", "ko")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(any("모두 번역 쌍" in w for w in rep["warnings"]), rep["warnings"])

    def test_merge_rule(self):
        self.assertEqual(merge({"a": {"x": 1, "y": 2}, "l": [1, 2]}, {"a": {"y": 3}, "l": [9]}),
                         {"a": {"x": 1, "y": 3}, "l": [9]})


if __name__ == "__main__":
    unittest.main()
