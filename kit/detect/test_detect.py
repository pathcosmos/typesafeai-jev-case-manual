"""detect.py 인수 테스트 (표준 라이브러리 unittest).

실행: python3 -m unittest kit/detect/test_detect.py -v   (저장소 루트에서)
fixture마다 심어 둔 지점을 찾는지, 무관한 코드를 LLM 지점으로 잘못 잡지 않는지 확인한다.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
DETECT = HERE / "detect.py"
FIXTURES = HERE.parent / "fixtures"


def run_detect(target: Path) -> dict:
    out = subprocess.run([sys.executable, str(DETECT), str(target)],
                         check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def files(sites: list[dict]) -> set[str]:
    return {s["file"] for s in sites}


class PythonFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = run_detect(FIXTURES / "py-openai-json")

    def test_stack(self):
        py = [s for s in self.r["stacks"] if s["language"] == "python"]
        self.assertEqual(len(py), 1)
        self.assertEqual(py[0]["package_manager"], "uv")   # [dependency-groups] → uv 관례
        self.assertEqual(py[0]["test_runner"], "pytest")
        self.assertIn("fastapi", py[0]["frameworks"])

    def test_llm_sites(self):
        self.assertEqual(files(self.r["llm_call_sites"]), {"app/triage.py", "app/summary.py"})
        sdks = {s["sdk"] for s in self.r["llm_call_sites"]}
        self.assertEqual(sdks, {"openai"})
        kinds = {(s["file"], s["kind"]) for s in self.r["llm_call_sites"]}
        self.assertIn(("app/triage.py", "call"), kinds)

    def test_parse_and_heuristic(self):
        parse = [s for s in self.r["parse_sites"] if s["file"] == "app/triage.py"]
        self.assertTrue(any("json.loads" in s["snippet"] for s in parse))
        self.assertTrue(all(s["near_llm"] for s in parse))
        self.assertIn("app/triage.py", files(self.r["heuristic_sites"]))

    def test_no_false_positives(self):
        for key in ("llm_call_sites", "parse_sites", "heuristic_sites"):
            self.assertNotIn("app/dates.py", files(self.r[key]), key)

    def test_language(self):
        self.assertEqual(self.r["language_signal"]["label"], "ko")

    def test_no_typesafe_yet(self):
        self.assertEqual(self.r["typesafe_usage"], [])


class TsFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = run_detect(FIXTURES / "ts-llm-heuristic")

    def test_stack(self):
        ts = [s for s in self.r["stacks"] if s["language"] == "typescript"]
        self.assertEqual(len(ts), 1)
        self.assertEqual(ts[0]["package_manager"], "npm")
        self.assertEqual(ts[0]["test_runner"], "vitest")
        self.assertIn("express", ts[0]["frameworks"])

    def test_llm_sites(self):
        self.assertEqual(files(self.r["llm_call_sites"]), {"src/moderation.ts"})
        self.assertEqual({s["sdk"] for s in self.r["llm_call_sites"]}, {"anthropic"})

    def test_yes_no_parse(self):
        parse = [s for s in self.r["parse_sites"] if s["file"] == "src/moderation.ts"]
        self.assertTrue(any("startsWith" in s["snippet"] for s in parse))

    def test_heuristics(self):
        spam = [s for s in self.r["heuristic_sites"] if s["file"] == "src/spam.ts"]
        snippets = " ".join(s["snippet"] for s in spam)
        self.assertIn("SPAM_KEYWORDS", snippets)
        self.assertIn("URL_SHORTENER = /", snippets)       # 정규식 리터럴 정의
        self.assertIn("URL_SHORTENER.test(", snippets)     # 이름 붙은 정규식 사용
        strength = {s["snippet"].split("=")[0].strip(): s["strength"] for s in spam}
        self.assertEqual(strength["const SPAM_KEYWORDS"], "strong")
        self.assertEqual(strength["const URL_SHORTENER"], "weak")
        self.assertTrue(all(s["signal"] for s in spam))

    def test_test_files_excluded(self):
        self.assertNotIn("test/spam.test.ts", files(self.r["heuristic_sites"]))

    def test_language(self):
        self.assertEqual(self.r["language_signal"]["label"], "en")


class NoiseFilter(unittest.TestCase):
    """구조 파싱용 정규식(경로, 마크업)은 휴리스틱 후보로 잡지 않는다."""

    def test_structural_regex_ignored(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            Path(d, "paths.py").write_text(
                'import re\n'
                'm = re.search(r"diagram-(\\d+)\\.svg", name)\n'
                'h = re.search(r"^(#\\s+.+?)\\n", body)\n'
                'if re.search(r"refund|chargeback|money back", text):\n'
                '    pass\n'
                'if "spec" in data:\n'          # dict 키 검사 → 제외
                '    pass\n'
                'if "urgent" in message.lower():\n'  # 텍스트 변수에 대한 포함 검사 → strong
                '    pass\n', encoding="utf-8")
            Path(d, "win.ts").write_text(
                "export const isAbs = (p: string) => /^[a-zA-Z]:/.test(p);\n"
                "const GLOB = /[*?[{]/;\n", encoding="utf-8")
            r = run_detect(Path(d))
            snippets = [s["snippet"] for s in r["heuristic_sites"]]
            self.assertEqual(len(snippets), 2, snippets)
            self.assertIn("refund|chargeback", snippets[0])
            self.assertIn('"urgent" in message', snippets[1])


class CustomTransports(unittest.TestCase):
    """SDK 없이 자체 provider 계층으로 모델을 부르는 프로젝트 (2026-09-25 파일럿에서 발견한 사각지대)."""

    def test_raw_http_cli_and_platform_calls(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            src = Path(d, "src/providers")
            src.mkdir(parents=True)
            (src / "openai-compat.ts").write_text(
                "export async function call(base: string, body: object) {\n"
                "  const res = await fetch(`${base}/chat/completions`, { method: 'POST', body: JSON.stringify({ ...body, response_format: { type: 'json_schema' } }) });\n"
                "  return JSON.parse(await res.text());\n}\n", encoding="utf-8")
            (src / "anthropic-api.ts").write_text(
                "const res = await fetch(`${base}/v1/messages`, { headers: { 'anthropic-version': '2023-06-01' } });\n", encoding="utf-8")
            (src / "claude-cli.ts").write_text(
                "import { spawn } from 'node:child_process';\n"
                "export const run = (prompt: string) => spawn('claude', ['-p', prompt, '--output-format', 'json']);\n", encoding="utf-8")
            (src / "codex_exec.py").write_text(
                "import subprocess\n"
                "def run(prompt):\n    return subprocess.run(['codex', 'exec', '--output-schema', 's.json', prompt])\n", encoding="utf-8")
            (src / "transcribe.ts").write_text(
                'const r = await c.env.AI.run("@cf/openai/whisper", { audio });\n', encoding="utf-8")
            (src / "injected.ts").write_text(  # spawn 주입 방식: bin 이름만 있고 spawn 호출은 다른 파일에 있다
                "export const opts = { bin: this.opts.bin ?? 'claude', spawn: this.opts.spawn };\n", encoding="utf-8")
            (src / "verify.ts").write_text(  # 'llm'이라는 enum 값은 CLI 호출이 아니다
                "import { spawn } from 'node:child_process';\ntype By = 'engine' | 'llm';\n", encoding="utf-8")
            (Path(d, "test")).mkdir()
            (Path(d, "test/providers.test.ts")).write_text("fetch(`${base}/chat/completions`);\n", encoding="utf-8")
            (src / "ui_api.ts").write_text(  # 자기 서버 API 호출은 LLM이 아니다
                "export const get = (path: string) => fetch(`/api/projects/${path}`);\n", encoding="utf-8")
            r = run_detect(Path(d))
            by_file = {}
            for s in r["llm_call_sites"]:
                by_file.setdefault(s["file"].split("/")[-1], set()).add((s["sdk"], s["kind"]))
            self.assertIn(("raw-http", "http"), by_file["openai-compat.ts"])
            self.assertIn(("raw-http", "http"), by_file["anthropic-api.ts"])
            self.assertIn(("claude-cli", "cli"), by_file["claude-cli.ts"])
            self.assertIn(("codex-cli", "cli"), by_file["codex_exec.py"])
            self.assertIn(("workers-ai", "platform"), by_file["transcribe.ts"])
            self.assertNotIn("ui_api.ts", by_file)
            self.assertIn(("claude-cli", "cli"), by_file["injected.ts"])
            self.assertNotIn("verify.ts", by_file)
            tests = [s for s in r["llm_call_sites"] if s["file"].endswith("providers.test.ts")]
            self.assertTrue(tests and all(s["in_test"] for s in tests))
            self.assertTrue(all(not s["in_test"] for s in r["llm_call_sites"] if "src/" in s["file"]))
            # 구조화 출력 요청(json_schema, --output-schema)은 파싱 신호로도 기록한다
            parse_files = {s["file"].split("/")[-1] for s in r["parse_sites"]}
            self.assertTrue({"openai-compat.ts", "codex_exec.py"} <= parse_files, parse_files)


class Robustness(unittest.TestCase):
    def test_kit_repo_itself_runs(self):
        # 저장소 자체(스캐폴드, 픽스처, 문서 포함)에도 크래시 없이 동작하고, typesafe 사용을 탐지한다
        r = run_detect(HERE.parent.parent)
        self.assertTrue(any("scaffolds" in s["file"] for s in r["typesafe_usage"]))

    def test_max_files(self):
        out = subprocess.run([sys.executable, str(DETECT), str(FIXTURES / "py-openai-json"), "--max-files", "1"],
                             check=True, capture_output=True, text=True)
        self.assertTrue(json.loads(out.stdout)["scan"]["truncated"])


if __name__ == "__main__":
    unittest.main()
