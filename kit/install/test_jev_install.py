"""jev_install.py 테스트: 임시 HOME과 가짜 claude/codex 명령으로 확인한다 (실제 설정, 네트워크를 건드리지 않는다)."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

INSTALL = Path(__file__).resolve().with_name("jev_install.py")
KIT = Path(__file__).resolve().parents[2]
CONV = (KIT / "kit" / "options" / "convention.md").read_text(encoding="utf-8").strip()
KEY = "test-secret-key-9f2c"

STUB_CODEX = r'''#!/usr/bin/env python3
import json, os, sys
d = os.environ["STUB_DIR"]; st = os.path.join(d, "codex-state.json")
s = json.load(open(st)) if os.path.exists(st) else {"mk": {}, "plugins": []}
open(os.path.join(d, "codex-calls.log"), "a").write(" ".join(sys.argv[1:]) + "\n")
a = sys.argv[1:]
if a[:3] == ["plugin", "marketplace", "list"]:
    print("MARKETPLACE  ROOT"); [print(f"{k}  {v}") for k, v in s["mk"].items()]
elif a[:3] == ["plugin", "marketplace", "add"]: s["mk"]["jev-kit"] = a[3]
elif a[:3] == ["plugin", "marketplace", "remove"]: s["mk"].pop(a[3], None)
elif a[:2] == ["plugin", "list"]: [print(f"{p}  installed, enabled  0.0.0  /x") for p in s["plugins"]]
elif a[:2] == ["plugin", "add"]: s["plugins"] = sorted(set(s["plugins"]) | {a[2]})
elif a[:2] == ["plugin", "remove"]: s["plugins"] = [p for p in s["plugins"] if p != a[2]]
json.dump(s, open(st, "w"))
'''

STUB_CLAUDE = r'''#!/usr/bin/env python3
import json, os, sys
d = os.environ["STUB_DIR"]; st = os.path.join(d, "state.json")
s = json.load(open(st)) if os.path.exists(st) else {"mk": [], "plugins": []}
open(os.path.join(d, "calls.log"), "a").write(" ".join(sys.argv[1:]) + "\n")
a = sys.argv[1:]
if a[:3] == ["plugin", "marketplace", "list"]: print(json.dumps(s["mk"]))
elif a[:3] == ["plugin", "marketplace", "add"]: s["mk"].append({"name": "jev-kit", "source": "directory", "path": a[3]})
elif a[:3] == ["plugin", "marketplace", "remove"]: s["mk"] = [m for m in s["mk"] if m["name"] != a[3]]
elif a[:2] == ["plugin", "list"]: print(json.dumps(s["plugins"]))
elif a[:2] == ["plugin", "install"]: s["plugins"].append({"id": a[2], "version": "0.0.0"})
elif a[:2] == ["plugin", "uninstall"]: s["plugins"] = [p for p in s["plugins"] if p["id"] != a[2]]
json.dump(s, open(st, "w"))
'''


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.home = self.tmp / "home"
        self.bin = self.tmp / "bin"
        self.home.mkdir(); self.bin.mkdir()
        (self.bin / "claude").write_text(STUB_CLAUDE); (self.bin / "claude").chmod(0o755)
        (self.bin / "codex").write_text(STUB_CODEX); (self.bin / "codex").chmod(0o755)
        (self.home / ".codex").mkdir()
        self.iterm = {"type": "command", "command": "/Users/x/.config/iterm2/cc-status"}
        (self.home / ".codex" / "hooks.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [self.iterm]}]}}))

    def run_install(self, *args, stdin=""):
        env = {"PATH": f"{self.bin}:/usr/bin:/bin", "STUB_DIR": str(self.tmp), "HOME": str(self.home)}
        return subprocess.run([sys.executable, str(INSTALL), *args, "--kit-dir", str(KIT), "--home", str(self.home)],
                              input=stdin, capture_output=True, text=True, env=env)

    def calls(self):
        p = self.tmp / "calls.log"
        return p.read_text().splitlines() if p.exists() else []

    def codex_calls(self):
        p = self.tmp / "codex-calls.log"
        return p.read_text().splitlines() if p.exists() else []

    def codex_hooks(self):
        return json.loads((self.home / ".codex" / "hooks.json").read_text())["hooks"]

    def test_install_writes_private_config_and_never_prints_key(self):
        p = self.run_install("install", "--options", "jev", "--key-stdin", stdin=KEY + "\n")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        cfg = self.home / ".config" / "jev" / "env"
        self.assertEqual(stat.S_IMODE(cfg.stat().st_mode), 0o600)
        self.assertIn(f"TYPESAFE_API_KEY={KEY}", cfg.read_text())
        self.assertIn("JEV_OPTIONS=jev", cfg.read_text())
        self.assertNotIn(KEY, p.stdout + p.stderr)
        self.assertIn("plugin marketplace add " + str(KIT), self.calls())
        self.assertIn("plugin install jev@jev-kit", self.calls())

    def test_codex_uses_the_plugin_not_hooks_json(self):
        self.run_install("install", "--options", "jev", "--key-stdin", stdin=KEY + "\n")
        p = self.run_install("install")  # 두 번째: 모드는 기존 값(jev) 유지
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(self.codex_hooks(), {"Stop": [{"hooks": [self.iterm]}]})  # hooks.json에는 아무것도 넣지 않는다
        self.assertEqual(self.codex_calls().count("plugin marketplace add " + str(KIT)), 1)  # 두 번째에는 이미 등록됨
        self.assertEqual(self.codex_calls().count("plugin add jev@jev-kit"), 2)  # 매번 현재 버전으로 다시 복사
        self.assertIn("plugin update jev@jev-kit", self.calls())  # Claude 쪽 두 번째 실행은 갱신
        self.assertIn(f"TYPESAFE_API_KEY={KEY}", (self.home / ".config" / "jev" / "env").read_text())  # 키 유지

    def test_codex_legacy_hooks_json_entries_removed(self):
        legacy = {"type": "command", "command": 'python3 "/old/kit/options/jev_options.py"', "timeout": 10}
        (self.home / ".codex" / "hooks.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [self.iterm]}, {"hooks": [legacy]}], "SessionStart": [{"hooks": [legacy]}]}}))
        self.run_install("install", "--options", "jev", "--key-stdin", stdin=KEY + "\n")
        self.assertEqual(self.codex_hooks(), {"Stop": [{"hooks": [self.iterm]}]})
        self.assertTrue(list((self.home / ".codex").glob("hooks.json.bak-*")))

    def test_legacy_manual_setup_is_migrated(self):
        (self.home / ".claude").mkdir()
        manual = {"type": "command", "command": "python3 /old/clone/kit/options/jev_options.py", "timeout": 10}
        (self.home / ".claude" / "settings.json").write_text(json.dumps({
            "env": {"JEV_OPTIONS": "jev", "JEV_OPTIONS_ENV_FILE": "/x/.env", "KEEP": "1"},
            "hooks": {"Stop": [{"hooks": [self.iterm]}, {"hooks": [manual]}], "PreToolUse": [{"matcher": "AskUserQuestion", "hooks": [manual]}]}}))
        (self.home / ".claude" / "CLAUDE.md").write_text("# 전역 지침\n\n" + CONV + "\n")
        (self.home / ".codex" / "AGENTS.md").write_text("# 내 규칙\n\n- 한국어로 답한다\n\n" + CONV + "\n")
        p = self.run_install("install", "--options", "fake")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        s = json.loads((self.home / ".claude" / "settings.json").read_text())
        self.assertEqual(s["env"], {"KEEP": "1"})
        self.assertEqual(s["hooks"], {"Stop": [{"hooks": [self.iterm]}]})
        self.assertFalse((self.home / ".claude" / "CLAUDE.md").exists())  # 규약만 있던 파일은 지운다
        self.assertEqual((self.home / ".codex" / "AGENTS.md").read_text(), "# 내 규칙\n\n- 한국어로 답한다\n")  # 사용자 내용은 남긴다
        self.assertTrue(list((self.home / ".claude").glob("settings.json.bak-*")))

    def test_key_env_file_pointer_instead_of_copy(self):
        p = self.run_install("install", "--options", "jev", "--key-env-file", str(self.tmp / "proj.env"))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        cfg = (self.home / ".config" / "jev" / "env").read_text()
        self.assertIn(f"JEV_OPTIONS_ENV_FILE={(self.tmp / 'proj.env').resolve()}", cfg)
        self.assertNotIn("TYPESAFE_API_KEY=", cfg)

    def test_uninstall_and_purge(self):
        self.run_install("install", "--options", "jev", "--key-stdin", stdin=KEY + "\n")
        p = self.run_install("uninstall")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        cfg = self.home / ".config" / "jev" / "env"
        self.assertIn("JEV_OPTIONS=off", cfg.read_text())
        self.assertIn(KEY, cfg.read_text())  # 끄기만 하면 키는 남는다
        self.run_install("uninstall", "--purge")
        self.assertFalse(cfg.exists())
        self.assertIn("plugin uninstall jev@jev-kit", self.calls())
        self.assertIn("plugin remove jev@jev-kit", self.codex_calls())

    def test_doctor_reports_without_key(self):
        self.run_install("install", "--options", "jev", "--key-stdin", stdin=KEY + "\n")
        p = self.run_install("doctor")
        self.assertEqual(p.returncode, 1)
        self.assertIn("✗ Codex 플러그인 hook 신뢰: 없음", p.stdout)  # 신뢰 전에는 문제로 표시
        (self.home / ".codex" / "config.toml").write_text(
            '[hooks.state."jev@jev-kit:hooks/hooks.json:session_start:0:0"]\ntrusted_hash = "x"\n'
            '[hooks.state."jev@jev-kit:hooks/hooks.json:stop:0:0"]\ntrusted_hash = "y"\n')
        p = self.run_install("doctor")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("키 설정 파일", p.stdout)
        self.assertIn("jev@jev-kit", p.stdout)
        self.assertNotIn(KEY, p.stdout)
        # 키 없이 jev 모드면 문제로 표시한다
        (self.home / ".config" / "jev" / "env").write_text("JEV_OPTIONS=jev\n")
        p = self.run_install("doctor")
        self.assertEqual(p.returncode, 1)
        self.assertIn("✗ 선택지 hook 모드 jev · 키 없음", p.stdout)


if __name__ == "__main__":
    unittest.main()
