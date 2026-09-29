#!/usr/bin/env python3
"""jev-kit 설치기: 이 킷을 다른 기기의 Claude Code와 Codex에 연결한다 (install.sh가 부른다).

사용:
  python3 kit/install/jev_install.py [install] [--options off|fake|jev] [--kit-dir DIR] [--options-only]
                                     [--key-env-file PATH | --key-stdin] [--no-claude] [--no-codex]
  python3 kit/install/jev_install.py doctor [--options-only] [--live]
  python3 kit/install/jev_install.py uninstall [--options-only] [--purge]

하는 일 (여러 번 실행해도 결과가 같다. 고치는 설정 파일은 먼저 *.bak-<시각>으로 백업한다):
- ~/.config/jev/env (권한 600): 선택지 hook 모드 JEV_OPTIONS와 TYPESAFE_API_KEY (또는 키가 든 dotenv 경로 JEV_OPTIONS_ENV_FILE), 사용자가 넣은 표시 형식 JEV_OPTIONS_FORMAT은 유지.
  키는 화면에 표시하지 않고 입력받는다 (getpass). 출력, 로그, 다른 파일에 키를 쓰지 않는다.
- Claude Code: 킷 디렉터리를 marketplace `jev-kit`로 등록하고 플러그인 `jev@jev-kit`를 설치하거나 갱신한다.
  선택지 hook은 플러그인의 hooks/hooks.json에 들어 있다 (모드가 off면 아무것도 하지 않는다).
  예전 수동 설정(settings.json의 jev_options.py hook, env, CLAUDE.md의 규약 블록)은 지운다.
- Codex: 같은 킷 디렉터리를 Codex marketplace `jev-kit`로 등록하고 플러그인 `jev@jev-kit`를 설치한다 (Claude와 같은 플러그인,
  같은 hooks/hooks.json. Codex는 CLAUDE_PLUGIN_ROOT를 넣어 준다). 플러그인 hook은 Codex CLI의 /hooks에서 신뢰해야 실행된다.
  예전에 ~/.codex/hooks.json에 직접 넣은 항목과 AGENTS.md의 규약 블록은 지운다.
표준 라이브러리만 쓴다. 종료 코드: 0 성공 · 1 일부 실패 (출력 참고) · 2 사용법 오류
"""
from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HOOK_MARK = "kit/options/jev_options.py"
MARKETPLACE = "jev-kit"
PLUGIN = "jev@jev-kit"
PLUGIN_OPTIONS_ONLY = "jev-options-only@jev-kit"
CONFIG_KEYS = ("JEV_OPTIONS", "TYPESAFE_API_KEY", "JEV_OPTIONS_ENV_FILE", "JEV_OPTIONS_FORMAT")
KIT_DEFAULT = Path(__file__).resolve().parents[2]


class Ctx:
    def __init__(self, home: Path, kit: Path, options_only: bool = False):
        self.home, self.kit = home, kit
        self.stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.problems: list[str] = []
        self.plugin = PLUGIN_OPTIONS_ONLY if options_only else PLUGIN

    @property
    def config(self) -> Path:
        return self.home / ".config" / "jev" / "env"

    def backup(self, p: Path):
        if p.exists():
            shutil.copy2(p, p.with_name(f"{p.name}.bak-{self.stamp}"))

    def say(self, msg: str):
        print(msg)

    def fail(self, msg: str):
        self.problems.append(msg)
        print(f"  ✗ {msg}")


# ---------------- 설정 파일 ----------------
def read_config(p: Path) -> dict:
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            k, sep, v = line.strip().removeprefix("export ").partition("=")
            if sep and k in CONFIG_KEYS:
                out[k] = v.strip().strip('"').strip("'")
    return out


def write_config(ctx: Ctx, conf: dict):
    ctx.config.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(ctx.config.parent, 0o700)
    body = "# jev-kit 설정 (install.sh가 관리한다). 이 파일에는 API 키가 들어갈 수 있다: 권한 600을 유지한다.\n"
    body += "".join(f"{k}={conf[k]}\n" for k in CONFIG_KEYS if conf.get(k))
    fd = os.open(ctx.config, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    os.chmod(ctx.config, 0o600)


def key_source(conf: dict) -> str:
    if os.environ.get("TYPESAFE_API_KEY"):
        return "환경변수"
    if conf.get("TYPESAFE_API_KEY"):
        return "설정 파일"
    if conf.get("JEV_OPTIONS_ENV_FILE"):
        p = Path(os.path.expanduser(conf["JEV_OPTIONS_ENV_FILE"]))
        has = p.exists() and any(l.strip().removeprefix("export ").startswith("TYPESAFE_API_KEY=") and l.split("=", 1)[1].strip() for l in p.read_text(encoding="utf-8").splitlines())
        return f"{p} ({'키 있음' if has else '키 없음'})"
    return "없음"


# ---------------- JSON 설정 편집 ----------------
def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_json(p: Path, d: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def strip_our_hooks(hooks: dict) -> int:
    """hooks 맵에서 jev_options.py를 부르는 항목만 지운다. 다른 hook은 그대로 둔다. 지운 개수를 돌려준다."""
    removed = 0
    for ev in list(hooks):
        groups = []
        for g in hooks[ev]:
            keep = [h for h in g.get("hooks", []) if HOOK_MARK not in h.get("command", "")]
            removed += len(g.get("hooks", [])) - len(keep)
            if keep:
                groups.append({**g, "hooks": keep})
        if groups:
            hooks[ev] = groups
        else:
            del hooks[ev]
    return removed


def strip_convention_block(ctx: Ctx, p: Path) -> bool:
    """예전 수동 설치가 넣은 규약 블록(kit/options/convention.md와 같은 내용)을 지운다. 파일이 제목만 남으면 지운다."""
    if not p.exists():
        return False
    conv = (ctx.kit / "kit" / "options" / "convention.md").read_text(encoding="utf-8").strip()
    text = p.read_text(encoding="utf-8")
    if conv not in text:
        return False
    ctx.backup(p)
    rest = text.replace(conv, "").strip()
    if rest in ("", "# 전역 지침"):
        p.unlink()
    else:
        p.write_text(rest + "\n", encoding="utf-8")
    return True


# ---------------- Claude Code ----------------
def run(cmd: list[str]) -> subprocess.CompletedProcess:
    # stdin을 부모 것(파이프거나 tty가 아닐 수 있다)으로 물려받으면, Bun으로 빌드된 claude/codex CLI가
    # kqueue 기반 fd 감시 중 "EINVAL: invalid argument, kqueue"로 죽는 사례가 있다 (macOS, non-tty 부모).
    # 아래 명령은 모두 비대화형이라 stdin이 필요 없으므로 명시적으로 끊는다.
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)


def claude_step(ctx: Ctx):
    ctx.say("• Claude Code")
    settings = ctx.home / ".claude" / "settings.json"
    if settings.exists():
        d = load_json(settings)
        env = d.get("env") or {}
        n = strip_our_hooks(d.get("hooks") or {})
        dropped = [k for k in ("JEV_OPTIONS", "JEV_OPTIONS_ENV_FILE") if k in env]
        if n or dropped:
            ctx.backup(settings)
            for k in dropped:
                env.pop(k)
            if "env" in d and not d["env"]:
                del d["env"]
            if "hooks" in d and not d["hooks"]:
                del d["hooks"]
            save_json(settings, d)
            ctx.say(f"  예전 수동 설정 정리: hook {n}개, env {dropped} (백업 settings.json.bak-{ctx.stamp})")
    if strip_convention_block(ctx, ctx.home / ".claude" / "CLAUDE.md"):
        ctx.say("  예전 규약 블록을 ~/.claude/CLAUDE.md에서 지움 (이제 플러그인이 세션 시작 때 전달)")
    if not shutil.which("claude"):
        ctx.fail("claude 명령이 없다. Claude Code를 설치한 뒤 다시 실행한다")
        return
    try:
        mkts = json.loads(run(["claude", "plugin", "marketplace", "list", "--json"]).stdout or "[]")
    except ValueError:
        mkts = []
    mk = next((m for m in mkts if m.get("name") == MARKETPLACE), None)
    if mk and Path(mk.get("path") or "").resolve() != ctx.kit.resolve():
        ctx.say(f"  marketplace {MARKETPLACE}가 다른 경로({mk.get('path') or mk.get('repo')})를 가리켜서 다시 등록한다")
        run(["claude", "plugin", "marketplace", "remove", MARKETPLACE])
        mk = None
    if not mk:
        r = run(["claude", "plugin", "marketplace", "add", str(ctx.kit)])
        if r.returncode != 0:
            ctx.fail(f"marketplace 등록 실패: {r.stderr.strip()[-300:]}")
            return
        ctx.say(f"  marketplace {MARKETPLACE} 등록: {ctx.kit}")
    try:
        plugins = json.loads(run(["claude", "plugin", "list", "--json"]).stdout or "[]")
    except ValueError:
        plugins = []
    installed = any((p.get("id") or p.get("name")) == ctx.plugin for p in plugins)
    r = run(["claude", "plugin", "update" if installed else "install", ctx.plugin])
    if r.returncode != 0:
        ctx.fail(f"플러그인 {'갱신' if installed else '설치'} 실패: {r.stderr.strip()[-300:]}")
        return
    ctx.say(f"  플러그인 {ctx.plugin} {'갱신' if installed else '설치'} 완료 (새 세션부터 적용)")


# ---------------- Codex ----------------
def codex_marketplaces() -> dict:
    """`codex plugin marketplace list` (표: NAME ROOT)를 {이름: 루트}로."""
    out = {}
    for line in run(["codex", "plugin", "marketplace", "list"]).stdout.splitlines()[1:]:
        parts = line.split(None, 1)
        if len(parts) == 2:
            out[parts[0]] = parts[1].strip()
    return out


def codex_plugin_installed() -> bool:
    return any(l.split()[:1] == [PLUGIN] and "installed" in l and "not installed" not in l
               for l in run(["codex", "plugin", "list"]).stdout.splitlines())


def codex_cleanup_legacy(ctx: Ctx):
    """예전 방식(~/.codex/hooks.json에 직접 넣은 jev_options.py 항목, AGENTS.md 규약 블록)을 지운다."""
    hooks_file = ctx.home / ".codex" / "hooks.json"
    if hooks_file.exists():
        d = load_json(hooks_file)
        if strip_our_hooks(d.get("hooks") or {}):
            ctx.backup(hooks_file)
            save_json(hooks_file, d)
            ctx.say(f"  예전 hooks.json 항목 정리 (백업 hooks.json.bak-{ctx.stamp})")
    if strip_convention_block(ctx, ctx.home / ".codex" / "AGENTS.md"):
        ctx.say("  예전 규약 블록을 ~/.codex/AGENTS.md에서 지움 (이제 플러그인 SessionStart hook이 전달)")


def codex_step(ctx: Ctx):
    codex_dir = ctx.home / ".codex"
    if not codex_dir.exists() and not shutil.which("codex"):
        ctx.say("• Codex: 설치되어 있지 않아 건너뜀")
        return
    ctx.say("• Codex")
    codex_cleanup_legacy(ctx)
    if not shutil.which("codex"):
        ctx.fail("codex 명령이 없어 플러그인을 설치하지 못했다")
        return
    mk = codex_marketplaces()
    if MARKETPLACE in mk and Path(mk[MARKETPLACE]).resolve() != ctx.kit.resolve():
        ctx.say(f"  Codex marketplace {MARKETPLACE}가 다른 경로({mk[MARKETPLACE]})를 가리켜서 다시 등록한다")
        run(["codex", "plugin", "marketplace", "remove", MARKETPLACE])
        mk.pop(MARKETPLACE)
    if MARKETPLACE not in mk:
        r = run(["codex", "plugin", "marketplace", "add", str(ctx.kit)])
        if r.returncode != 0:
            ctx.fail(f"Codex marketplace 등록 실패: {(r.stderr or r.stdout).strip()[-300:]}")
            return
        ctx.say(f"  Codex marketplace {MARKETPLACE} 등록: {ctx.kit}")
    was = codex_plugin_installed()
    r = run(["codex", "plugin", "add", ctx.plugin])  # 이미 있으면 현재 킷 버전으로 다시 복사한다
    if r.returncode != 0:
        ctx.fail(f"Codex 플러그인 설치 실패: {(r.stderr or r.stdout).strip()[-300:]}")
        return
    ctx.say(f"  Codex 플러그인 {ctx.plugin} {'갱신' if was else '설치'} 완료")
    ctx.say("  ⚠ 처음 설치했거나 hook 정의(hooks/hooks.json)가 바뀌었으면 Codex CLI의 /hooks에서 jev-options-only@jev-kit 또는 jev@jev-kit hook을 신뢰(trust)해야 실행된다")


# ---------------- 명령 ----------------
def cmd_install(ctx: Ctx, a) -> int:
    mode_label = "선택지 hook만" if ctx.plugin == PLUGIN_OPTIONS_ONLY else "전체"
    ctx.say(f"jev-kit 설치: 킷 {ctx.kit} ({mode_label})")
    if sys.version_info < (3, 10):
        ctx.fail(f"Python 3.10 이상이 필요하다 (지금 {sys.version.split()[0]})")
        return 1
    conf = read_config(ctx.config)
    mode = a.options or conf.get("JEV_OPTIONS") or "off"
    conf["JEV_OPTIONS"] = mode
    if a.key_env_file:
        conf["JEV_OPTIONS_ENV_FILE"] = str(Path(os.path.expanduser(a.key_env_file)).resolve())
        conf.pop("TYPESAFE_API_KEY", None)
    elif a.key_stdin:
        key = sys.stdin.readline().strip()
        if key:
            conf["TYPESAFE_API_KEY"] = key
            conf.pop("JEV_OPTIONS_ENV_FILE", None)
    elif mode == "jev" and key_source(conf) == "없음" and sys.stdin.isatty():
        key = getpass.getpass("TypeSafe API 키 (입력은 화면에 표시되지 않는다, 건너뛰려면 Enter): ").strip()
        if key:
            conf["TYPESAFE_API_KEY"] = key
    write_config(ctx, conf)
    ctx.say(f"• 설정 {ctx.config} (권한 600): 선택지 hook 모드 {mode}, 키 {key_source(conf)}")
    if mode == "jev" and key_source(conf) == "없음":
        ctx.say("  ⚠ 키가 없어서 실제 점수는 표시되지 않는다. 나중에 install.sh --options jev를 다시 실행해 키를 넣는다")
    if not a.no_claude:
        claude_step(ctx)
    if not a.no_codex:
        codex_step(ctx)
    ctx.say("완료" if not ctx.problems else f"일부 실패 {len(ctx.problems)}건")
    ctx.say("다음: 새 Claude Code / Codex 세션부터 적용된다. 상태 점검: install.sh doctor")
    return 1 if ctx.problems else 0


def cmd_doctor(ctx: Ctx, a) -> int:
    ok = True
    def line(good: bool, msg: str):
        nonlocal ok
        ok &= good
        print(f"{'✔' if good else '✗'} {msg}")
    line(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}")
    head = run(["git", "-C", str(ctx.kit), "rev-parse", "--short", "HEAD"]).stdout.strip() if (ctx.kit / ".git").exists() else "(git 아님)"
    plugin_json = ctx.kit / ".claude-plugin" / "plugin.json"
    ver = json.loads(plugin_json.read_text())["version"] if plugin_json.exists() else "?"
    line((ctx.kit / HOOK_MARK).exists(), f"킷 {ctx.kit} (버전 {ver}, 커밋 {head})")
    conf = read_config(ctx.config)
    perm = oct(stat.S_IMODE(ctx.config.stat().st_mode)) if ctx.config.exists() else None
    line(perm == "0o600", f"설정 {ctx.config}: {'없음' if perm is None else '권한 ' + perm}")
    mode = os.environ.get("JEV_OPTIONS") or conf.get("JEV_OPTIONS") or "off"
    src = key_source(conf)
    line(mode != "jev" or src != "없음", f"선택지 hook 모드 {mode} · 키 {src}")
    if shutil.which("claude"):
        try:
            plugins = json.loads(run(["claude", "plugin", "list", "--json"]).stdout or "[]")
        except ValueError:
            plugins = []
        p = next((p for p in plugins if (p.get("id") or p.get("name")) == ctx.plugin), None)
        line(p is not None, f"Claude 플러그인 {ctx.plugin}: {p.get('version') if p else '설치 안 됨'}")
        s = load_json(ctx.home / ".claude" / "settings.json")
        legacy = strip_our_hooks(json.loads(json.dumps(s.get("hooks") or {})))
        line(legacy == 0, f"Claude 예전 수동 hook: {legacy}개" + (" (install을 다시 실행하면 정리된다)" if legacy else ""))
    else:
        print("- Claude Code 없음")
    if shutil.which("codex"):
        line(codex_plugin_installed(), f"Codex 플러그인 {ctx.plugin}: {'설치됨' if codex_plugin_installed() else '설치 안 됨'}")
        cfg = ctx.home / ".codex" / "config.toml"
        trusted = [e for e in ("session_start", "stop", "pre_tool_use") if cfg.exists() and f'"{ctx.plugin}:hooks/hooks.json:{e}:0:0"' in cfg.read_text(encoding="utf-8")]
        line(mode == "off" or {"session_start", "stop"} <= set(trusted), f"Codex 플러그인 hook 신뢰: {trusted or '없음'} (Codex CLI /hooks에서 신뢰)")
        legacy = sum(HOOK_MARK in h.get("command", "") for gs in load_json(ctx.home / ".codex" / "hooks.json").get("hooks", {}).values() for g in gs for h in g.get("hooks", []))
        line(legacy == 0, f"Codex 예전 hooks.json 항목: {legacy}개" + (" (install을 다시 실행하면 정리된다)" if legacy else ""))
    else:
        print("- Codex 없음")
    if a.live and mode in ("fake", "jev"):
        sys.path.insert(0, str(ctx.kit / "kit" / "options"))
        import jev_options  # noqa: E402
        payload = {"hook_event_name": "Stop", "last_assistant_message": "1. 테스트 추가\n2. 기능 삭제\n어느 것으로 할까요?"}
        out = jev_options.handle(payload, {**os.environ, "JEV_OPTIONS_FORMAT": "line"})  # 점검 줄 하나에 담는다
        line(bool(out), "실제 점수 호출 (합성 선택지 1건): " + (out["systemMessage"][:120] if out else "표시 없음 (키, 네트워크 확인)"))
    print("정상" if ok else "문제 있음")
    return 0 if ok else 1


def cmd_uninstall(ctx: Ctx, a) -> int:
    ctx.say("jev-kit 선택지 hook 끄기" + (" + 전체 제거" if a.purge else ""))
    conf = read_config(ctx.config)
    if ctx.config.exists() and not a.purge:
        conf["JEV_OPTIONS"] = "off"
        write_config(ctx, conf)
        ctx.say(f"• {ctx.config}: 모드 off (키는 남겨 둔다. 지우려면 --purge)")
    if (ctx.home / ".codex").exists():
        codex_cleanup_legacy(ctx)
    settings = ctx.home / ".claude" / "settings.json"
    if settings.exists():
        d = load_json(settings)
        if strip_our_hooks(d.get("hooks") or {}):
            ctx.backup(settings)
            save_json(settings, d)
    if a.purge:
        if shutil.which("claude"):
            run(["claude", "plugin", "uninstall", ctx.plugin])
            run(["claude", "plugin", "marketplace", "remove", MARKETPLACE])
            ctx.say(f"• Claude 플러그인 {ctx.plugin}와 marketplace {MARKETPLACE} 제거")
        if shutil.which("codex"):
            run(["codex", "plugin", "remove", ctx.plugin])
            run(["codex", "plugin", "marketplace", "remove", MARKETPLACE])
            ctx.say(f"• Codex 플러그인 {ctx.plugin}와 marketplace {MARKETPLACE} 제거")
        if ctx.config.exists():
            ctx.config.unlink()
            ctx.say(f"• {ctx.config} 삭제 (키 포함)")
    ctx.say("완료. 새 세션부터 적용된다")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", nargs="?", default="install", choices=["install", "doctor", "uninstall"])
    ap.add_argument("--options", choices=["off", "fake", "jev"], help="선택지 hook 모드 (없으면 기존 값, 처음이면 off)")
    ap.add_argument("--options-only", action="store_true", help="선택지 hook만 설치 (jev@jev-kit 대신 jev-options-only@jev-kit). /jev:apply 스킬 제외")
    ap.add_argument("--kit-dir", type=Path, default=KIT_DEFAULT)
    ap.add_argument("--key-env-file", help="키를 복사하지 않고 이 dotenv 파일의 TYPESAFE_API_KEY를 읽게 한다")
    ap.add_argument("--key-stdin", action="store_true", help="키를 표준입력 첫 줄에서 읽는다 (자동화용)")
    ap.add_argument("--no-claude", action="store_true")
    ap.add_argument("--no-codex", action="store_true")
    ap.add_argument("--live", action="store_true", help="doctor: 합성 선택지로 점수 호출을 한 번 해 본다")
    ap.add_argument("--purge", action="store_true", help="uninstall: 플러그인과 설정 파일(키 포함)까지 지운다")
    ap.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    ctx = Ctx(a.home, a.kit_dir.resolve(), options_only=a.options_only)
    return {"install": cmd_install, "doctor": cmd_doctor, "uninstall": cmd_uninstall}[a.command](ctx, a)


if __name__ == "__main__":
    raise SystemExit(main())
