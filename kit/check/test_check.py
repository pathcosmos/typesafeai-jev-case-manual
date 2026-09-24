"""check.py 인수 테스트 (표준 라이브러리 unittest).

실행: python3 -m unittest kit/check/test_check.py -v   (저장소 루트에서)
검증된 scaffold는 통과해야 하고, 일부러 깨뜨린 변형은 해당 검사에서 fail(또는 warn)해야 한다.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE / "check.py"
SCAFFOLDS = HERE.parent / "scaffolds"


def run_check(target: Path, jev_dir: str | None = "jev") -> tuple[int, dict]:
    args = [sys.executable, str(CHECK), str(target)]
    if jev_dir:
        args += ["--jev-dir", jev_dir]
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


def status(result: dict, check_id: str) -> str:
    return next(c["status"] for c in result["checks"] if c["id"] == check_id)


class Base(unittest.TestCase):
    stack = "python"

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(SCAFFOLDS / self.stack, self.tmp / "proj",
                        ignore=shutil.ignore_patterns("node_modules", "dist", ".venv", "__pycache__"))
        self.root = self.tmp / "proj"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel: str, old: str, new: str):
        p = self.root / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text, f"fixture text not found in {rel}: {old!r}")
        p.write_text(text.replace(old, new, 1), encoding="utf-8")


class PythonScaffold(Base):
    stack = "python"

    def test_scaffold_passes(self):
        code, r = run_check(self.root)
        self.assertEqual(code, 0, json.dumps(r, ensure_ascii=False, indent=1))
        self.assertTrue(all(c["status"] in ("pass", "skip") for c in r["checks"]), r["checks"])

    def test_auto_locate_jev_dir(self):
        code, r = run_check(self.root, jev_dir=None)
        self.assertEqual(code, 0)
        self.assertEqual(r["jev_dirs"], ["jev"])

    def test_latest_alias_fails(self):
        self.edit("jev/policy.py", '"jev-1.13.0"', '"jev-latest"')
        code, r = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertEqual(status(r, "model_pinned"), "fail")

    def test_score_too_many_levels(self):
        self.edit("jev/questions.py", '"Very angry or threatening to leave"]',
                  '"Very angry or threatening to leave"' + ', "x"' * 8 + "]")
        self.assertEqual(status(run_check(self.root)[1], "score_levels"), "fail")

    def test_score_null_level(self):
        self.edit("jev/questions.py", '"Frustrated but civil",', 'None,')
        self.assertEqual(status(run_check(self.root)[1], "score_levels"), "fail")

    def test_choice_without_no_match_warns(self):
        self.edit("jev/questions.py", '"other":   "None of the above",                       # no-match 선택지', "")
        code, r = run_check(self.root)
        self.assertEqual(status(r, "choice_no_match"), "warn")
        self.assertEqual(code, 0)  # warn은 게이트를 막지 않는다

    def test_client_at_import_fails(self):
        self.edit("jev/decide.py", "@lru_cache(maxsize=1)", "CLIENT = TypeSafeClient()\n\n@lru_cache(maxsize=1)")
        self.assertEqual(status(run_check(self.root)[1], "client_not_at_import"), "fail")

    def test_key_literal_fails(self):
        self.edit("jev/decide.py", "model=policy.MODEL,", 'model=policy.MODEL, api_key="tsk_live_abcdefghijklmnop1234",')
        self.assertEqual(status(run_check(self.root)[1], "no_key_exposure"), "fail")

    def test_untagged_threshold_fails(self):
        self.edit("jev/policy.py", "# [잠정] refund_requested.noul", "# refund_requested.noul")
        self.assertEqual(status(run_check(self.root)[1], "threshold_tags"), "fail")

    def test_questions_in_two_modules_fail(self):
        (self.root / "jev" / "extra.py").write_text(
            'from typesafe_sdk import Noul\nEXTRA = {"x": Noul(instructions="Is it spam?")}\n', encoding="utf-8")
        self.assertEqual(status(run_check(self.root)[1], "single_questions_module"), "fail")

    def test_missing_fallback_warns(self):
        text = (self.root / "jev/decide.py").read_text(encoding="utf-8")
        (self.root / "jev/decide.py").write_text(text.replace("except TypeSafeError:", "except ValueError:"), encoding="utf-8")
        self.assertEqual(status(run_check(self.root)[1], "fallback_on_error"), "warn")

    def test_model_not_per_request_warns(self):
        self.edit("jev/decide.py", ", model=policy.MODEL)", ")")
        self.assertEqual(status(run_check(self.root)[1], "model_per_request"), "warn")

    def test_no_jev_dir_reports_error(self):
        shutil.rmtree(self.root / "jev")
        code, r = run_check(self.root, jev_dir=None)
        self.assertEqual(code, 2)
        self.assertIn("error", r)


class Monorepo(unittest.TestCase):
    def test_two_jev_dirs_each_with_one_questions_module_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for stack in ("python", "ts"):
                shutil.copytree(SCAFFOLDS / stack, root / stack,
                                ignore=shutil.ignore_patterns("node_modules", "dist", ".venv", "__pycache__"))
            code, r = run_check(root, jev_dir=None)
            self.assertEqual(sorted(r["jev_dirs"]), ["python/jev", "ts/jev"])
            self.assertEqual(code, 0, json.dumps(r["checks"], ensure_ascii=False, indent=1))

    def test_questions_outside_jev_dir_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(SCAFFOLDS / "python", root / "app",
                            ignore=shutil.ignore_patterns("node_modules", "dist", ".venv", "__pycache__"))
            (root / "app" / "routes.py").write_text(
                'from typesafe_sdk import Noul\nQ = {"x": Noul(instructions="Is it spam?")}\n', encoding="utf-8")
            code, r = run_check(root, jev_dir=None)
            self.assertEqual(status(r, "single_questions_module"), "fail")


class TsScaffold(Base):
    stack = "ts"

    def test_scaffold_passes(self):
        code, r = run_check(self.root)
        self.assertEqual(code, 0, json.dumps(r, ensure_ascii=False, indent=1))
        self.assertTrue(all(c["status"] in ("pass", "skip") for c in r["checks"]), r["checks"])

    def test_preview_alias_fails(self):
        self.edit("jev/policy.ts", '"jev-1.13.0"', '"jev-preview"')
        self.assertEqual(status(run_check(self.root)[1], "model_pinned"), "fail")

    def test_score_single_level_fails(self):
        self.edit("jev/questions.ts",
                  '["Calm and matter-of-fact", "Frustrated but civil", "Very angry or threatening to leave"]',
                  '["Calm and matter-of-fact"]')
        self.assertEqual(status(run_check(self.root)[1], "score_levels"), "fail")

    def test_choice_without_no_match_warns(self):
        self.edit("jev/questions.ts", ', other: "None of the above"', "")
        self.assertEqual(status(run_check(self.root)[1], "choice_no_match"), "warn")

    def test_top_level_client_fails(self):
        self.edit("jev/decide.ts", "let _client: TypeSafeClient | undefined;",
                  "const eager = new TypeSafeClient();\nlet _client: TypeSafeClient | undefined;")
        self.assertEqual(status(run_check(self.root)[1], "client_not_at_import"), "fail")

    def test_browser_flag_fails(self):
        self.edit("jev/decide.ts", "timeout: 3000,", "timeout: 3000, dangerouslyAllowBrowser: true,")
        self.assertEqual(status(run_check(self.root)[1], "no_key_exposure"), "fail")

    def test_untagged_threshold_fails(self):
        self.edit("jev/policy.ts", "// [잠정] refund_requested.noul", "// refund_requested.noul")
        self.assertEqual(status(run_check(self.root)[1], "threshold_tags"), "fail")

    def test_model_not_per_request_warns(self):
        self.edit("jev/decide.ts", ", model: POLICY.model }", " }")
        self.assertEqual(status(run_check(self.root)[1], "model_per_request"), "warn")

    def test_missing_fallback_warns(self):
        self.edit("jev/decide.ts", "if (e instanceof TypeSafeError) return { route: \"fallback\" };", "")
        self.assertEqual(status(run_check(self.root)[1], "fallback_on_error"), "warn")


if __name__ == "__main__":
    unittest.main()
