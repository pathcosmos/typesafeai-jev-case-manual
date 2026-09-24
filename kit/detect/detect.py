#!/usr/bin/env python3
"""jev-kit detect: 대상 프로젝트의 스택과 Jev 적용 후보 신호를 JSON으로 출력한다.

사용: python3 detect.py <target-dir> [--max-files N] [--max-bytes N]
- 표준 라이브러리만 쓴다 (python 3.10+). 대상 프로젝트를 수정하지 않는다 (읽기 전용).
- 결과는 **후보를 좁히는 신호**일 뿐이다. 채택 판단은 에이전트가 KIT/manual/01로 한다.
출력 스키마: kit/detect/README.md
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

VERSION = "0.1.0"

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", ".next",
    ".turbo", "coverage", ".jev", "site-packages", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "target", "vendor", ".tox", ".cache", "out", ".output", ".svelte-kit",
}
PY_EXT = {".py"}
JS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"}
MAX_PER_FILE = 20

# ---------- LLM SDK 식별 ----------
PY_SDK = [  # (import 모듈 접두사 정규식, sdk 이름)
    (r"openai", "openai"), (r"anthropic", "anthropic"),
    (r"google\.genai|google\.generativeai|vertexai", "google"),
    (r"langchain\w*", "langchain"), (r"litellm", "litellm"), (r"ollama", "ollama"),
    (r"mistralai", "mistral"), (r"cohere", "cohere"), (r"groq", "groq"),
    (r"llama_index", "llamaindex"), (r"pydantic_ai", "pydantic-ai"), (r"dspy", "dspy"),
    (r"instructor", "instructor"), (r"together", "together"),
]
JS_SDK = [
    (r"openai", "openai"), (r"@anthropic-ai/sdk", "anthropic"),
    (r"@google/genai|@google/generative-ai", "google"),
    (r"ai|@ai-sdk/(?!typesafe-ai)[\w-]+", "vercel-ai"),
    (r"langchain|@langchain/[\w-]+", "langchain"), (r"ollama", "ollama"),
    (r"@mistralai/mistralai", "mistral"), (r"cohere-ai", "cohere"), (r"groq-sdk", "groq"),
    (r"llamaindex", "llamaindex"),
]
PY_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(%s)\b" % "|".join(p for p, _ in PY_SDK))
JS_IMPORT_RE = re.compile(
    r"""(?:from\s+|require\(\s*|import\(\s*)["'](%s)(?:/[^"']*)?["']""" % "|".join(p for p, _ in JS_SDK))
CALL_RE = re.compile(
    r"\.chat\.completions\.create\(|\.completions\.create\(|\.messages\.create\(|\.responses\.create\("
    r"|\.generate_content\(|\.generateContent\(|\bgenerateText\(|\bgenerateObject\(|\bstreamText\("
    r"|\bstreamObject\(|\.a?invoke\(|\ba?completion\(|\bollama\.chat\(|\.models\.generate_content\("
)
CLIENT_RE = re.compile(r"\bnew\s+(OpenAI|Anthropic|GoogleGenAI|Groq|Mistral)\s*\(|\b(OpenAI|AsyncOpenAI|Anthropic|AsyncAnthropic)\s*\(")
TYPESAFE_RE = re.compile(r"typesafe_sdk|@typesafe-ai/sdk|@ai-sdk/typesafe-ai|langchain_typesafe|api\.typesafe\.ai")

# ---------- 파싱 / 휴리스틱 신호 ----------
YESNO = r"(?:yes|no|true|false|y|n)"
PARSE_RE = {
    "py": re.compile(
        r"json\.loads\(|model_validate_json\(|parse_raw\(|ast\.literal_eval\("
        rf"|\.startswith\(\s*[\"']{YESNO}[\"']|==\s*[\"']{YESNO}[\"']|\bin\s*\(\s*[\"']{YESNO}[\"']",
        re.I),
    "js": re.compile(
        rf"JSON\.parse\(|\.startsWith\(\s*[\"']{YESNO}[\"']|===?\s*[\"']{YESNO}[\"']|\.includes\(\s*[\"']{YESNO}[\"']",
        re.I),
}
HEUR_LIST_NAME = r"[A-Z][A-Z0-9_]*(?:KEYWORDS?|WORDS|TERMS|PHRASES|PATTERNS|BLOCKLIST|ALLOWLIST|BANNED|SPAM|PROFANITY)[A-Z0-9_]*"
REGEX_LIT = r"/(?:\\.|[^/\n\\])+/[gimsuy]*"  # 이스케이프(\/ 등)를 허용하는 정규식 리터럴
# 의미 판정 신호 (signal, strength, 언어별 정규식)
#  strong: 키워드 목록과 포함 검사처럼 "텍스트의 의미"를 판정하는 것이 분명한 코드
#  weak:   정규식. 구조 파싱(경로, 마크업)과 구분이 어려우므로 단어 대안(a|b)이 있을 때만 기록한다
HEUR_RULES = {
    "py": [
        ("keyword_list", "strong", re.compile(rf"^\s*{HEUR_LIST_NAME}\s*[:=]")),
        ("keyword_any", "strong", re.compile(r"\bany\(\s*\w+\s+in\s+[\w.()]+\s+for\s+\w+\s+in\b")),
        # "리터럴" in 텍스트: 리터럴에 공백이나 비ASCII 글자가 있거나, 대상 변수가 텍스트류 이름일 때만 (dict 키 검사 제외)
        ("literal_in", "strong", re.compile(
            r"\bif\s+(?:[\"'][^\"'\n]*(?:\s|[^\x00-\x7f])[^\"'\n]*[\"']\s+in\s+\w+"
            r"|[\"'][^\"'\n]{2,}[\"']\s+in\s+(?:\w+\.)?(?:text|message|msg|content|body|post|comment|query|prompt|title|subject|description|input|answer|reply|name)\w*\b)",
            re.I)),
        ("regex_use", "weak", re.compile(r"\bre\.(?:search|match|fullmatch|findall|compile)\(")),
    ],
    "js": [
        ("keyword_list", "strong", re.compile(rf"^\s*(?:export\s+)?(?:const|let|var)\s+{HEUR_LIST_NAME}\s*=")),
        ("keyword_includes", "strong", re.compile(r"\.some\(\s*\(?\w+\)?\s*=>\s*[\w.]+\.includes\(")),
        ("regex_def", "weak", re.compile(rf"^\s*(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*{REGEX_LIT}\s*;?\s*$")),
        ("regex_use", "weak", re.compile(rf"{REGEX_LIT}\.test\(|\bnew\s+RegExp\(|\.match\(\s*/")),
        ("named_regex_use", "weak", re.compile(r"\b[A-Z][A-Z0-9_]{2,}\.test\(")),
    ],
}
# weak 정규식은 "단어 대안"이 있을 때만 의미 판정으로 본다: free money|click here, bit\.ly|tinyurl
WORD_ALT_RE = re.compile(r"[A-Za-z가-힣]{3,}[^|\n]{0,40}\|[^|\n]{0,40}?[A-Za-z가-힣]{3,}")
TEST_FILE_RE = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*\.py$|_test\.py$|\.(test|spec)\.[cm]?[jt]sx?$")


def heuristic_signal(lang: str, line: str) -> tuple[str, str] | None:
    for signal, strength, rx in HEUR_RULES[lang]:
        if rx.search(line):
            if strength == "weak" and signal != "named_regex_use" and not WORD_ALT_RE.search(line):
                continue
            return signal, strength
    return None


STRING_RE = re.compile(r'"""(.*?)"""|\'\'\'(.*?)\'\'\'|"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`([^`]*)`', re.S)
HANGUL_RE = re.compile(r"[가-힣]")
LATIN_RE = re.compile(r"[A-Za-z]")


def lang_of(path: Path) -> str | None:
    if path.suffix in PY_EXT:
        return "py"
    if path.suffix in JS_EXT:
        return "js"
    return None


def iter_files(root: Path, max_files: int, max_bytes: int):
    count, truncated = 0, False
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") or d in {".github"})
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if lang_of(p) is None:
                continue
            try:
                if p.stat().st_size > max_bytes:
                    continue
            except OSError:
                continue
            if count >= max_files:
                truncated = True
                return_value = (count, truncated)
                yield None, return_value
                return
            count += 1
            yield p, None
    yield None, (count, truncated)


def sdk_for(module: str, table) -> str:
    for pat, name in table:
        if re.fullmatch(pat, module):
            return name
    return module


def snippet(line: str) -> str:
    s = line.strip()
    return s if len(s) <= 160 else s[:157] + "..."


def scan_file(p: Path, rel: str, lang: str, out: dict, lang_counts: dict):
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    lines = text.splitlines()

    # 언어 신호: 문자열 리터럴 안의 한글 / 라틴 문자 수
    for m in STRING_RE.finditer(text):
        s = next(g for g in m.groups() if g is not None) if any(m.groups()) else ""
        lang_counts["hangul"] += len(HANGUL_RE.findall(s))
        lang_counts["latin"] += len(LATIN_RE.findall(s))

    sdks: list[str] = []
    llm_lines: list[int] = []
    for i, line in enumerate(lines, 1):
        if TYPESAFE_RE.search(line):
            out["typesafe_usage"].append({"file": rel, "line": i, "snippet": snippet(line)})
            continue
        m = (PY_IMPORT_RE if lang == "py" else JS_IMPORT_RE).search(line)
        if m:
            sdk = sdk_for(m.group(1), PY_SDK if lang == "py" else JS_SDK)
            if lang == "js" and sdk == "vercel-ai" and not re.search(r"""["'](ai|@ai-sdk/[\w-]+)["']""", line):
                continue
            sdks.append(sdk)
            out["llm_call_sites"].append({"file": rel, "line": i, "sdk": sdk, "kind": "import", "snippet": snippet(line)})
            llm_lines.append(i)
    if sdks:
        primary = sdks[0]
        n = 0
        for i, line in enumerate(lines, 1):
            if n >= MAX_PER_FILE:
                break
            kind = "call" if CALL_RE.search(line) else "client" if CLIENT_RE.search(line) else None
            if kind:
                out["llm_call_sites"].append({"file": rel, "line": i, "sdk": primary, "kind": kind, "snippet": snippet(line)})
                llm_lines.append(i)
                n += 1
        # 파싱 신호는 LLM을 쓰는 파일에서만 기록한다 (그 외의 JSON 파싱은 잡음)
        n = 0
        for i, line in enumerate(lines, 1):
            if n >= MAX_PER_FILE:
                break
            if PARSE_RE[lang].search(line):
                dist = min(abs(i - j) for j in llm_lines)
                out["parse_sites"].append({"file": rel, "line": i, "snippet": snippet(line),
                                           "near_llm": True, "llm_line_distance": dist})
                n += 1

    if TEST_FILE_RE.search(rel):
        return  # 테스트 코드의 정규식과 키워드는 적용 후보가 아니다
    n = 0
    for i, line in enumerate(lines, 1):
        if n >= MAX_PER_FILE:
            break
        hit = heuristic_signal(lang, line)
        if hit:
            out["heuristic_sites"].append({"file": rel, "line": i, "signal": hit[0], "strength": hit[1],
                                           "snippet": snippet(line), "in_llm_file": bool(sdks)})
            n += 1


# ---------- 스택 ----------
def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


PY_FRAMEWORKS = ["fastapi", "django", "flask", "starlette", "langchain", "llama-index", "pydantic-ai",
                 "apache-airflow", "pyspark", "streamlit", "celery", "sqlalchemy", "pandas", "torch", "transformers"]
JS_FRAMEWORKS = ["next", "express", "fastify", "hono", "react", "vue", "svelte", "@nestjs/core", "remix",
                 "astro", "ai", "langchain", "@langchain/core", "prisma", "drizzle-orm"]


def python_stack(d: Path, root: Path) -> dict | None:
    pyproject, reqs = d / "pyproject.toml", sorted(d.glob("requirements*.txt"))
    setup_py, pipfile = d / "setup.py", d / "Pipfile"
    if not (pyproject.exists() or reqs or setup_py.exists() or pipfile.exists()):
        return None
    pp = read(pyproject)
    deps_text = (pp + "\n" + "\n".join(read(r) for r in reqs) + read(setup_py) + read(pipfile)).lower()
    if (d / "uv.lock").exists() or "[tool.uv" in pp:
        pm = "uv"
    elif (d / "poetry.lock").exists() or "[tool.poetry" in pp:
        pm = "poetry"
    elif pipfile.exists():
        pm = "pipenv"
    elif "[dependency-groups]" in pp:
        pm = "uv"
    else:
        pm = "pip"
    manifest = "pyproject.toml" if pyproject.exists() else (reqs[0].name if reqs else setup_py.name if setup_py.exists() else "Pipfile")
    runner = "pytest" if ("pytest" in deps_text or (d / "pytest.ini").exists() or (d / "conftest.py").exists()) else (
        "unittest" if list(d.glob("tests/test_*.py")) or list(d.glob("test_*.py")) else None)
    fw = [f for f in PY_FRAMEWORKS if re.search(rf"(^|[\s\"'\[,]){re.escape(f)}\b", deps_text)]
    return {"root": rel_of(d, root), "language": "python", "package_manager": pm, "manifest": manifest,
            "test_runner": runner, "frameworks": fw}


def js_stack(d: Path, root: Path) -> dict | None:
    pkg = d / "package.json"
    if not pkg.exists():
        return None
    try:
        data = json.loads(read(pkg) or "{}")
    except json.JSONDecodeError:
        data = {}
    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    if (d / "pnpm-lock.yaml").exists():
        pm = "pnpm"
    elif (d / "yarn.lock").exists():
        pm = "yarn"
    elif (d / "bun.lockb").exists() or (d / "bun.lock").exists():
        pm = "bun"
    else:
        pm = str(data.get("packageManager", "npm")).split("@")[0] or "npm"
    language = "typescript" if ((d / "tsconfig.json").exists() or "typescript" in deps) else "javascript"
    test_script = str(data.get("scripts", {}).get("test", ""))
    runner = next((r for r in ["vitest", "jest", "mocha", "ava", "playwright"] if r in deps or r in test_script), None)
    if runner is None and "node --test" in test_script:
        runner = "node:test"
    fw = [f for f in JS_FRAMEWORKS if f in deps]
    return {"root": rel_of(d, root), "language": language, "package_manager": pm, "manifest": "package.json",
            "test_runner": runner, "frameworks": fw}


def rel_of(p: Path, root: Path) -> str:
    r = p.relative_to(root).as_posix()
    return r if r else "."


def find_stacks(root: Path, max_depth: int = 3) -> list[dict]:
    stacks = []
    for dirpath, dirnames, _ in os.walk(root):
        d = Path(dirpath)
        depth = len(d.relative_to(root).parts)
        dirnames[:] = sorted(x for x in dirnames if x not in SKIP_DIRS and not x.startswith(".")) if depth < max_depth else []
        for fn in (python_stack, js_stack):
            s = fn(d, root)
            if s:
                stacks.append(s)
    return stacks


# ---------- git ----------
def git(root: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def repo_info(root: Path) -> dict:
    top = git(root, "rev-parse", "--show-toplevel")
    if top is None:
        return {"is_git": False}
    status = git(root, "status", "--porcelain")
    head = git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    return {"is_git": True, "toplevel": top, "clean": status == "", "branch": git(root, "branch", "--show-current"),
            "default_branch": head.split("/", 1)[1] if head and "/" in head else None}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target")
    ap.add_argument("--max-files", type=int, default=3000)
    ap.add_argument("--max-bytes", type=int, default=512_000)
    a = ap.parse_args(argv)
    root = Path(a.target).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"not a directory: {root}"}), file=sys.stderr)
        return 2

    out = {"llm_call_sites": [], "parse_sites": [], "heuristic_sites": [], "typesafe_usage": []}
    lang_counts = {"hangul": 0, "latin": 0}
    scanned, truncated = 0, False
    for p, done in iter_files(root, a.max_files, a.max_bytes):
        if p is None:
            scanned, truncated = done
            break
        scan_file(p, rel_of(p, root), lang_of(p), out, lang_counts)

    h, l = lang_counts["hangul"], lang_counts["latin"]
    ratio = h / (h + l) if (h + l) else 0.0
    label = "ko" if ratio >= 0.2 else "mixed" if ratio >= 0.03 else "en" if (h + l) else "unknown"

    result = {
        "tool": "jev-kit detect", "version": VERSION, "target": str(root),
        "scan": {"files_scanned": scanned, "truncated": truncated, "max_files": a.max_files},
        "repo": repo_info(root),
        "stacks": find_stacks(root),
        **out,
        "language_signal": {"label": label, "hangul_chars": h, "latin_chars": l, "hangul_ratio": round(ratio, 3),
                            "basis": "string literals in scanned source files"},
    }
    result["summary"] = {k: len(result[k]) for k in ("stacks", "llm_call_sites", "parse_sites", "heuristic_sites", "typesafe_usage")}
    result["summary"]["llm_files"] = len({s["file"] for s in result["llm_call_sites"]})
    result["summary"]["heuristic_strong"] = sum(s["strength"] == "strong" for s in result["heuristic_sites"])
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
