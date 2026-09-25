"""replay.py 테스트: 손으로 만든 measure.json과 표본, 작은 Python 정책 명령으로 확인한다 (키, 네트워크 불필요)."""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPLAY = Path(__file__).with_name("replay.py")
sys.path.insert(0, str(REPLAY.parent))
from replay import wilson_upper  # noqa: E402

# noul 하나(touches)로 yes/no/unsure를 정하는 정책. 실제 프로젝트에서는 프로젝트 코드를 부르는 어댑터가 이 자리에 온다.
POLICY = (
    "import sys, json\n"
    "for l in sys.stdin:\n"
    "    r = json.loads(l); p = r['answers']['touches']['noul']\n"
    "    d = 'yes' if p >= 0.8 else 'no' if p <= 0.2 else 'unsure'\n"
    "    print(json.dumps({'id': r['id'], 'decision': d}))\n"
)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "policy.py").write_text(POLICY, encoding="utf-8")
        self.policy = f"{shlex.quote(sys.executable)} policy.py"

    def write(self, rows):
        """rows: (id, gold, noul 또는 'error'/'not_run', extra dict)."""
        samples, per = [], []
        for sid, gold, p, extra in rows:
            samples.append({"id": sid, "state": {"x": "SECRET STATE TEXT"}, **({"gold": gold} if gold is not None else {}), **extra})
            if p in ("error", "not_run"):
                per.append({"id": sid, "status": p})
            elif p is not None:
                per.append({"id": sid, "status": "ok", "answers": {"touches": {"noul": p}}})
        (self.tmp / "s.jsonl").write_text("".join(json.dumps(s) + "\n" for s in samples), encoding="utf-8")
        (self.tmp / "m.json").write_text(json.dumps({"status": "completed", "model_requested": "jev-1.13.0",
                                                     "models": ["jev-1.13.0"], "per_sample": per}), encoding="utf-8")

    def run_replay(self, *extra, policy=None):
        p = subprocess.run([sys.executable, str(REPLAY), "--measure", str(self.tmp / "m.json"),
                            "--samples", str(self.tmp / "s.jsonl"), "--policy-cmd", policy or self.policy,
                            "--cwd", str(self.tmp), "--out", str(self.tmp / "out.json"), *extra],
                           capture_output=True, text=True)
        out = json.loads((self.tmp / "out.json").read_text()) if (self.tmp / "out.json").exists() else None
        return p, out

    def test_metrics_coverage_errors_costly_escalate(self):
        self.write([
            ("a", "yes", 0.9, {}),      # 맞음
            ("b", "yes", 0.1, {}),      # 비싼 오류 yes->no
            ("c", "no", 0.1, {}),       # 맞음
            ("d", "no", 0.5, {}),       # 결정 가능했는데 보류 (coverage 손실, 오류 아님)
            ("e", "unsure", 0.5, {}),   # 올바른 에스컬레이션
            ("f", "unsure", 0.9, {}),   # 모호한데 결정해 버림 = 오류
        ])
        p, out = self.run_replay("--costly", "yes:no")
        self.assertEqual(p.returncode, 0, p.stderr)
        o = out["overall"]
        self.assertEqual(o["n"], 6)
        self.assertEqual(o["decided"], 4)
        self.assertEqual(o["coverage"], round(4 / 6, 4))
        self.assertEqual(o["errors_among_decided"], 2)
        self.assertEqual(o["error_ids"], ["b", "f"])
        self.assertEqual(o["costly"]["yes->no"], {"count": 1, "of_gold": 2, "ids": ["b"]})
        self.assertEqual(o["gold_escalate"], {"n": 2, "escalated": 1, "decided_wrongly": ["f"]})
        self.assertEqual(o["gold_decided_but_escalated"], 1)
        self.assertEqual(o["confusion"]["yes"]["no"], 1)
        self.assertIn("[잠정]", out["threshold_status"])
        self.assertEqual(out["models"], ["jev-1.13.0"])
        self.assertNotIn("SECRET STATE TEXT", (self.tmp / "out.json").read_text())

    def test_slices_and_pairs(self):
        self.write([
            ("p1-en", "yes", 0.9, {"lang": "en", "pair": "p1", "split": "test"}),
            ("p1-ko", "yes", 0.5, {"lang": "ko", "pair": "p1", "split": "test"}),   # 쌍 불일치
            ("p2-en", "no", 0.1, {"lang": "en", "pair": "p2", "split": "tune"}),
            ("p2-ko", "no", 0.1, {"lang": "ko", "pair": "p2", "split": "tune"}),
            ("p3-en", "no", 0.1, {"lang": "en", "pair": "p3", "split": "tune"}),
            ("p3-ko", "no", "error", {"lang": "ko", "pair": "p3", "split": "tune"}),  # 쌍이 불완전
        ])
        p, out = self.run_replay()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(out["pairs"], {"pairs_complete": 2, "pairs_incomplete": 1, "disagree": 1, "disagree_pairs": ["p1"]})
        self.assertEqual(out["by_lang"]["ko"]["n"], 2)
        self.assertEqual(out["by_lang"]["ko"]["coverage"], 0.5)
        self.assertEqual(set(out["by_split"]), {"test", "tune"})
        self.assertEqual(out["by_category"], {})  # category가 없으면 빈 slice
        self.assertEqual(out["counts"]["error"], 1)
        self.assertEqual(out["excluded"]["error"], ["p3-ko"])

    def test_excluded_and_missing_gold_are_counted_not_silent(self):
        self.write([("a", "yes", 0.9, {}), ("b", "yes", "not_run", {}), ("c", None, 0.9, {}), ("d", "no", None, {})])
        p, out = self.run_replay()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(out["counts"], {"samples": 4, "usable": 1, "not_in_measure": 1, "error": 0, "not_run": 1})
        self.assertIn("c: gold", out["warnings"][0])
        self.assertIn("warning:", p.stderr)

    def test_no_usable_samples_is_input_error(self):
        self.write([("a", "yes", "error", {})])
        p, out = self.run_replay()
        self.assertEqual(p.returncode, 3)
        self.assertEqual(out["status"], "invalid_input")

    def test_policy_failures_are_hard_errors(self):
        self.write([("a", "yes", 0.9, {}), ("b", "no", 0.1, {})])
        cases = {
            "exit": "import sys; sys.exit(2)",
            "missing": "import sys,json\nr=[json.loads(l) for l in sys.stdin]\nprint(json.dumps({'id': r[0]['id'], 'decision': 'yes'}))",
            "extra": "import sys,json\nfor l in sys.stdin: print(json.dumps({'id': json.loads(l)['id'], 'decision': 'yes'}))\nprint(json.dumps({'id': 'zzz', 'decision': 'yes'}))",
            "bad_value": "import sys,json\nfor l in sys.stdin: print(json.dumps({'id': json.loads(l)['id'], 'decision': 'maybe'}))",
            "not_json": "print('hello')",
        }
        for name, code in cases.items():
            (self.tmp / f"{name}.py").write_text(code, encoding="utf-8")
            p, out = self.run_replay(policy=f"{shlex.quote(sys.executable)} {name}.py")
            self.assertEqual(p.returncode, 5, name)
            self.assertEqual(out["status"], "policy_error", name)

    def test_decisions_option_allows_values_absent_from_gold(self):
        self.write([("a", "yes", 0.9, {}), ("b", "yes", 0.1, {})])  # gold에 'no'가 없다
        p, _ = self.run_replay()
        self.assertEqual(p.returncode, 5)
        p, out = self.run_replay("--decisions", "yes,no,unsure")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(out["overall"]["errors_among_decided"], 1)

    def test_wilson_upper(self):
        self.assertIsNone(wilson_upper(0, 0))
        self.assertAlmostEqual(wilson_upper(0, 20), 0.1611, places=3)  # 20건에 오류 0건이어도 상한은 약 16%
        self.assertLess(wilson_upper(0, 400), 0.01)
        self.assertEqual(wilson_upper(5, 5), 1.0)


if __name__ == "__main__":
    unittest.main()
