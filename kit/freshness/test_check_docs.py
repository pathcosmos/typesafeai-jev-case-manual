"""check_docs.py 테스트: 네트워크 없이 fetch를 바꿔 끼워 확인한다."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_docs as cd  # noqa: E402

SOURCES = """# Sources
| 페이지 | URL | 확인일 | 상태 | 반영 위치 |
| --- | --- | --- | --- | --- |
| Choice | https://docs.typesafe.ai/primitives/choice.md | 2026-09-24 | ✅ | reference/04 |
| Models | https://docs.typesafe.ai/models.md | 2026-09-24 | ✅ | reference/09 |
| Other host | https://example.com/x.md | 2026-09-24 | ✅ | — |
"""


def web(pages: dict):
    """url -> (status, body). 없으면 404. 값이 None이면 연결 실패."""
    def fetch(url, timeout=20.0):
        if url in pages and pages[url] is None:
            return None, "connection refused"
        return pages.get(url, (404, ""))
    return fetch


BASE_WEB = {
    cd.LLMS: (200, "- [Choice](https://docs.typesafe.ai/primitives/choice.md)\n- [Models](https://docs.typesafe.ai/models.md)\n"),
    cd.MODELS: (200, "Use jev-1.13.0 or jev-latest / jev-preview."),
    "https://docs.typesafe.ai/primitives/choice.md": (200, "choice v1"),
    cd.PYPI: (200, json.dumps({"info": {"version": "0.7.1"}})),
    cd.NPM: (200, json.dumps({"version": "0.6.0"})),
}


class CheckDocsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "sources.md").write_text(SOURCES, encoding="utf-8")

    def run_main(self, pages, *extra):
        args = ["--sources", str(self.tmp / "sources.md"), "--baseline", str(self.tmp / "baseline.json"),
                "--out", str(self.tmp / "report.md"), "--json", str(self.tmp / "diff.json"), *extra]
        with mock.patch.object(cd, "fetch", web(pages)):
            code = cd.main(args)
        report = (self.tmp / "report.md").read_text(encoding="utf-8") if (self.tmp / "report.md").exists() else ""
        return code, report

    def test_tracked_pages_only_official_hosts_with_where(self):
        p = cd.tracked_pages(SOURCES)
        self.assertEqual(p, {"https://docs.typesafe.ai/primitives/choice.md": "reference/04",
                             "https://docs.typesafe.ai/models.md": "reference/09"})

    def test_no_baseline_then_unchanged(self):
        code, _ = self.run_main(BASE_WEB)
        self.assertEqual(code, 3)
        code, _ = self.run_main(BASE_WEB, "--update-baseline")
        self.assertEqual(code, 0)
        code, report = self.run_main(BASE_WEB)
        self.assertEqual(code, 0)
        self.assertIn("변화 없음", report)

    def test_changes_are_reported_with_where_to_look(self):
        self.run_main(BASE_WEB, "--update-baseline")
        now = dict(BASE_WEB)
        now["https://docs.typesafe.ai/primitives/choice.md"] = (200, "choice v2")
        now[cd.MODELS] = (200, "Use jev-1.14.0 or jev-latest / jev-preview.")
        now[cd.PYPI] = (200, json.dumps({"info": {"version": "0.8.0"}}))
        now[cd.LLMS] = (200, BASE_WEB[cd.LLMS][1] + "- [New](https://docs.typesafe.ai/primitives/list.md)\n")
        code, report = self.run_main(now)
        self.assertEqual(code, 1)
        self.assertIn("| https://docs.typesafe.ai/primitives/choice.md | reference/04 |", report)
        self.assertIn("`jev-1.14.0`", report)
        self.assertIn("`jev-1.13.0`", report)  # 사라진 모델
        self.assertIn("**0.8.0**", report)
        self.assertIn("새 페이지: https://docs.typesafe.ai/primitives/list.md", report)
        d = json.loads((self.tmp / "diff.json").read_text())["diff"]
        self.assertEqual(d["models_added"], ["jev-1.14.0"])
        self.assertEqual(d["sdk"], [{"package": "python:typesafe-sdk", "was": "0.7.1", "now": "0.8.0"}])

    def test_page_status_change_404(self):
        self.run_main(BASE_WEB, "--update-baseline")
        now = dict(BASE_WEB)
        now["https://docs.typesafe.ai/primitives/choice.md"] = (404, "")
        code, report = self.run_main(now)
        self.assertEqual(code, 1)
        self.assertIn("| 200 | **404** | reference/04 |", report)

    def test_fetch_failure_is_exit_2_and_never_updates_baseline(self):
        self.run_main(BASE_WEB, "--update-baseline")
        before = (self.tmp / "baseline.json").read_text()
        now = dict(BASE_WEB)
        now[cd.LLMS] = None
        now[cd.NPM] = (503, "")
        code, report = self.run_main(now)
        self.assertEqual(code, 2)
        self.assertIn("가져오기 실패", report)
        self.assertNotIn("사라진 페이지", report)  # 목차를 못 가져왔으면 비교하지 않는다
        code, _ = self.run_main(now, "--update-baseline")
        self.assertEqual(code, 2)
        self.assertEqual((self.tmp / "baseline.json").read_text(), before)


if __name__ == "__main__":
    unittest.main()
