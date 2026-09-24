#!/usr/bin/env python3
"""jev-kit check: 적용된 Jev 통합이 manual/06 불변 조건을 지키는지 정적으로 검사한다.

사용: python3 check.py <target-dir> [--jev-dir <path>]...
- --jev-dir를 생략하면 policy와 questions 파일이 있는 `jev` 디렉터리를 자동으로 찾는다.
- 표준 라이브러리만 쓴다. 대상 프로젝트를 수정하지 않는다.
- 종료 코드: 0 = fail 없음 (warn 허용) · 1 = fail 있음 · 2 = 검사 불가 (jev 디렉터리 없음 등)
검사 목록과 판정 기준: kit/check/README.md
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

VERSION = "0.1.0"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", ".next",
             "coverage", ".jev", "site-packages", ".mypy_cache", ".pytest_cache", "target", "vendor", ".tox"}
PY_EXT = {".py"}
TS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"}
TEST_FILE_RE = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*\.py$|_test\.py$|\.(test|spec)\.[cm]?[jt]sx?$")
NO_MATCH_KEYS = {"other", "others", "none", "none_of_the_above", "no_match", "nomatch", "unknown", "not_applicable",
                 "n/a", "na", "unclear", "기타", "해당없음", "해당_없음", "없음"}
NO_MATCH_WAIVER = "jev-check: no-match-not-needed"
STATUS_TAG_RE = re.compile(r"\[(잠정|측정|공식 예시)\]")
ALIAS_RE = re.compile(r"""["']jev-(latest|preview)["']""")
PINNED_RE = re.compile(r"""["']jev-\d+\.\d+\.\d+["']""")
KEY_RES = [
    re.compile(r"""TYPESAFE_API_KEY\s*[:=]\s*["'][^"'\s]{12,}["']"""),
    re.compile(r"""\bapi_?key\s*[:=]\s*["'][A-Za-z0-9_\-]{16,}["']""", re.I),
    re.compile(r"""\bBearer\s+[A-Za-z0-9_\-]{20,}"""),
]
BROWSER_RE = re.compile(r"dangerouslyAllowBrowser\s*:\s*true")


# ---------------- 파일 수집 ----------------
def source_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if p.suffix in PY_EXT | TS_EXT:
                yield p


def rel(p: Path, root: Path) -> str:
    return p.relative_to(root).as_posix()


def is_test(r: str) -> bool:
    return bool(TEST_FILE_RE.search(r))


def find_jev_dirs(root: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        d = Path(dirpath)
        if d.name == "jev":
            stems = {Path(f).stem for f in filenames}
            if {"policy", "questions"} <= stems:
                found.append(d)
    return sorted(found)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------- TS 보조: 괄호 깊이, 인자 분할 ----------------
def ts_depth_map(text: str) -> list[int]:
    """각 문자 위치의 중괄호/괄호 깊이. 문자열과 주석은 건너뛴다."""
    depth, out, i, n = 0, [0] * (len(text) + 1), 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'`":
            q = c
            out[i] = depth
            i += 1
            while i < n and text[i] != q:
                if text[i] == "\\":
                    i += 1
                i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j == -1 else j
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        elif c in "({[":
            depth += 1
        elif c in ")}]":
            depth = max(0, depth - 1)
        if i < n:
            out[i] = depth
        i += 1
    return out


def ts_call_args(text: str, start: int) -> list[str] | None:
    """text[start]가 '(' 일 때, 최상위 인자 문자열 목록."""
    if start >= len(text) or text[start] != "(":
        return None
    args, depth, buf, i = [], 0, [], start
    while i < len(text):
        c = text[i]
        if c in "\"'`":
            q, j = c, i + 1
            while j < len(text) and text[j] != q:
                j += 2 if text[j] == "\\" else 1
            buf.append(text[i:j + 1])
            i = j + 1
            continue
        if c in "([{":
            depth += 1
            if depth == 1:
                i += 1
                continue
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                args.append("".join(buf).strip())
                return [a for a in args if a]
        elif c == "," and depth == 1:
            args.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    return None


def ts_split_top(inner: str) -> list[str]:
    """배열 / 객체 리터럴 내부를 최상위 콤마로 나눈다."""
    return [a for a in (ts_call_args("(" + inner + ")", 0) or [])]


def ts_strip_comments(s: str) -> str:
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", s, flags=re.S)


# ---------------- 개별 검사 ----------------
class Report:
    def __init__(self):
        self.checks: dict[str, dict] = {}

    def add(self, cid: str, title: str):
        self.checks[cid] = {"id": cid, "title": title, "status": "pass", "findings": []}

    def hit(self, cid: str, level: str, file: str, line: int | None, msg: str):
        c = self.checks[cid]
        c["findings"].append({"level": level, "file": file, "line": line, "message": msg})
        order = {"pass": 0, "skip": 0, "warn": 1, "fail": 2}
        if order[level] > order[c["status"]]:
            c["status"] = level

    def skip(self, cid: str, why: str):
        self.checks[cid]["status"] = "skip"
        self.checks[cid]["findings"].append({"level": "skip", "file": None, "line": None, "message": why})


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def py_call_name(node: ast.Call) -> str | None:
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def py_questions(tree: ast.AST):
    """(kind, node, criteria_node) — SDK 클래스 호출과 원시 dict 질문."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and py_call_name(node) in ("Choice", "Score", "Noul"):
            kind = py_call_name(node).lower()
            crit = next((k.value for k in node.keywords if k.arg == "criteria"), None)
            if crit is None and len(node.args) >= 2:
                crit = node.args[1]
            yield kind, node, crit
        elif isinstance(node, ast.Dict):
            keys = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
            t = keys.get("type")
            if isinstance(t, ast.Constant) and t.value in ("choice", "score", "noul"):
                yield t.value, node, keys.get("criteria")


def check_python_file(p: Path, r: str, rep: Report, in_jev: bool, text: str, question_files: set):
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        rep.hit("parse", "fail", r, e.lineno, f"Python 구문 오류: {e.msg}")
        return
    lines = text.splitlines()
    for kind, node, crit in py_questions(tree):
        question_files.add(r)
        if kind == "score":
            if isinstance(crit, (ast.List, ast.Tuple)):
                n = len(crit.elts)
                if not 2 <= n <= 10:
                    rep.hit("score_levels", "fail", r, node.lineno, f"Score 레벨이 {n}개다 (2~10개여야 한다)")
                if any(isinstance(e, ast.Constant) and e.value is None for e in crit.elts):
                    rep.hit("score_levels", "fail", r, node.lineno, "Score 레벨에 None이 있다 (API가 422를 반환한다)")
            else:
                rep.hit("score_levels", "warn", r, node.lineno, "Score criteria가 리터럴이 아니라 정적으로 검사할 수 없다")
        if kind == "choice" and isinstance(crit, ast.Dict):
            keys = {str(k.value).lower() for k in crit.keys if isinstance(k, ast.Constant)}
            near = "\n".join(lines[max(0, node.lineno - 3):getattr(node, "end_lineno", node.lineno)])
            if not keys & NO_MATCH_KEYS and NO_MATCH_WAIVER not in near:
                rep.hit("choice_no_match", "warn", r, node.lineno,
                        f"Choice에 no-match 선택지(other/none 등)가 없다: {sorted(keys)}. 목록이 모든 입력을 덮는다면 `# {NO_MATCH_WAIVER}` 주석을 단다")
    # 모듈 최상위에서의 클라이언트 생성
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call) and py_call_name(node) in ("TypeSafeClient", "AsyncTypeSafeClient"):
                rep.hit("client_not_at_import", "fail", r, node.lineno,
                        "클라이언트를 import 시점에 만든다 (생성자가 API 키를 검증하므로 키 없는 CI에서 import가 실패한다). 지연 생성하거나 주입한다")
    if in_jev:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and py_call_name(node) == "system_one" \
                    and not any(k.arg == "model" for k in node.keywords):
                rep.hit("model_per_request", "warn", r, node.lineno,
                        "system_one 호출에 model=가 없다. 주입된 클라이언트는 기본값(jev-latest)으로 요청한다. model=policy.MODEL을 넣는다")
    if in_jev and Path(r).stem == "decide":
        handled = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                t = node.type
                names = [t] if t is not None else []
                if isinstance(t, ast.Tuple):
                    names = list(t.elts)
                for n in names:
                    nm = n.id if isinstance(n, ast.Name) else n.attr if isinstance(n, ast.Attribute) else ""
                    if nm.startswith("TypeSafe") or nm in ("Exception", "BaseException"):
                        handled = True
        if not handled:
            rep.hit("fallback_on_error", "warn", r, None, "decide 모듈에서 TypeSafeError를 잡아 fallback으로 보내는 코드가 없다")
    if in_jev and Path(r).stem == "policy":
        for stmt in tree.body:
            if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and isinstance(getattr(stmt, "value", None), ast.Constant) \
                    and isinstance(stmt.value.value, (int, float)) and not isinstance(stmt.value.value, bool):
                ln = lines[stmt.lineno - 1]
                if not STATUS_TAG_RE.search(ln):
                    rep.hit("threshold_tags", "fail", r, stmt.lineno,
                            f"임계값에 상태 태그([잠정]/[측정]/[공식 예시])가 없다: {ln.strip()}")


TS_Q_RE = re.compile(r"\b(choice|score|noul)\s*\(")


def check_ts_file(p: Path, r: str, rep: Report, in_jev: bool, text: str, question_files: set):
    imports_sdk = "@typesafe-ai/sdk" in text
    depth = ts_depth_map(text)
    if imports_sdk:
        for m in TS_Q_RE.finditer(text):
            if depth[m.start()] < 0 or (m.start() > 0 and text[m.start() - 1] in ".$"):
                continue
            args = ts_call_args(text, m.end() - 1)
            if args is None:
                continue
            question_files.add(r)
            kind, ln = m.group(1), line_of(text, m.start())
            crit = ts_strip_comments(args[1]).strip() if len(args) >= 2 else None
            if kind == "score":
                if crit and crit.startswith("["):
                    items = ts_split_top(crit[1:-1])
                    if not 2 <= len(items) <= 10:
                        rep.hit("score_levels", "fail", r, ln, f"Score 레벨이 {len(items)}개다 (2~10개여야 한다)")
                    if any(i.strip() in ("null", "undefined") for i in items):
                        rep.hit("score_levels", "fail", r, ln, "Score 레벨에 null이 있다 (API가 422를 반환한다)")
                else:
                    rep.hit("score_levels", "warn", r, ln, "Score criteria가 배열 리터럴이 아니라 정적으로 검사할 수 없다")
            if kind == "choice" and crit and crit.startswith("{"):
                keys = set()
                for item in ts_split_top(crit[1:-1]):
                    km = re.match(r"""\s*["']?([^"':\s]+)["']?\s*:""", item)
                    if km:
                        keys.add(km.group(1).lower())
                near = text[max(0, m.start() - 200):m.start() + len(",".join(args)) + 10]
                if not keys & NO_MATCH_KEYS and NO_MATCH_WAIVER not in near:
                    rep.hit("choice_no_match", "warn", r, ln,
                            f"Choice에 no-match 선택지(other/none 등)가 없다: {sorted(keys)}. 목록이 모든 입력을 덮는다면 `// {NO_MATCH_WAIVER}` 주석을 단다")
    if in_jev:
        for m in re.finditer(r"\.systemOne\s*\(", text):
            args = ts_call_args(text, m.end() - 1)
            if args and not re.search(r"(^|[{,\s])model\s*[:,}]", ts_strip_comments(args[0])):
                rep.hit("model_per_request", "warn", r, line_of(text, m.start()),
                        "systemOne 요청에 model이 없다. 주입된 클라이언트는 기본값(jev-latest)으로 요청한다. model: POLICY.model을 넣는다")
    for m in re.finditer(r"\bnew\s+TypeSafeClient\s*\(", text):
        if depth[m.start()] == 0:
            rep.hit("client_not_at_import", "fail", r, line_of(text, m.start()),
                    "클라이언트를 모듈 최상위에서 만든다 (생성자가 API 키를 검증한다). 함수 안에서 지연 생성하거나 주입한다")
    for m in BROWSER_RE.finditer(text):
        rep.hit("no_key_exposure", "fail", r, line_of(text, m.start()),
                "dangerouslyAllowBrowser: true (API 키가 브라우저 사용자에게 노출된다)")
    if in_jev and Path(r).stem == "decide" and not re.search(r"instanceof\s+(TypeSafeError|APIError|APIConnectionError)", text):
        rep.hit("fallback_on_error", "warn", r, None, "decide 모듈에서 TypeSafeError를 fallback으로 보내는 코드가 없다")
    if in_jev and Path(r).stem == "policy":
        for i, ln in enumerate(text.splitlines(), 1):
            code = ln.split("//")[0]
            if re.search(r"[:=]\s*-?\d+(?:\.\d+)?\s*[,;]?\s*$", code) and not STATUS_TAG_RE.search(ln):
                rep.hit("threshold_tags", "fail", r, i, f"임계값에 상태 태그([잠정]/[측정]/[공식 예시])가 없다: {ln.strip()}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target")
    ap.add_argument("--jev-dir", action="append", default=[], help="대상 기준 상대 경로 또는 절대 경로 (여러 번 지정 가능)")
    a = ap.parse_args(argv)
    root = Path(a.target).resolve()
    jev_dirs = [(Path(d) if Path(d).is_absolute() else root / d).resolve() for d in a.jev_dir] or find_jev_dirs(root)
    jev_dirs = [d for d in jev_dirs if d.is_dir()]
    if not jev_dirs:
        print(json.dumps({"tool": "jev-kit check", "version": VERSION, "target": str(root),
                          "error": "jev 디렉터리를 찾지 못했다 (policy.* 와 questions.* 가 있는 `jev/`). --jev-dir로 지정한다"},
                         ensure_ascii=False, indent=2))
        return 2

    rep = Report()
    for cid, title in [
        ("model_pinned", "모델 버전 고정 (jev-latest / jev-preview 금지, policy에 jev-X.Y.Z)"),
        ("model_per_request", "jev 모듈의 호출마다 model 지정 (주입된 클라이언트의 기본값으로 새지 않게)"),
        ("score_levels", "Score 레벨 2~10개, null 없음"),
        ("choice_no_match", "Choice에 no-match 선택지"),
        ("single_questions_module", "질문 정의가 한 모듈에 모여 있음"),
        ("policy_module", "policy 모듈에 모델 버전과 임계값"),
        ("threshold_tags", "임계값마다 상태 태그 [잠정]/[측정]/[공식 예시]"),
        ("client_not_at_import", "클라이언트를 import 시점에 만들지 않음"),
        ("no_key_exposure", "API 키 리터럴 없음, 브라우저 노출 없음"),
        ("fallback_on_error", "decide에서 TypeSafeError → fallback"),
        ("parse", "소스 파싱"),
    ]:
        rep.add(cid, title)

    question_files: set[str] = set()
    for p in source_files(root):
        r = rel(p, root)
        if is_test(r):
            continue
        text = read(p)
        in_jev = any(d == p.parent or d in p.parents for d in jev_dirs)
        for m in ALIAS_RE.finditer(text):
            rep.hit("model_pinned", "fail", r, line_of(text, m.start()),
                    f"alias {m.group(0)} 사용: 튜닝한 버전으로 고정한다 (예: \"jev-1.13.0\")")
        for rx in KEY_RES:
            for m in rx.finditer(text):
                rep.hit("no_key_exposure", "fail", r, line_of(text, m.start()), "API 키로 보이는 리터럴이 있다. 환경변수에서 읽는다")
        if p.suffix in PY_EXT:
            check_python_file(p, r, rep, in_jev, text, question_files)
        else:
            check_ts_file(p, r, rep, in_jev, text, question_files)

    for d in jev_dirs:
        dr = rel(d, root) if d != root else "."
        policies = [f for f in d.iterdir() if f.stem == "policy" and f.suffix in PY_EXT | TS_EXT]
        if not policies:
            rep.hit("policy_module", "fail", dr, None, "policy 모듈이 없다")
        elif not any(PINNED_RE.search(read(f)) for f in policies):
            rep.hit("policy_module", "fail", rel(policies[0], root), None, "policy 모듈에 고정된 모델 버전(jev-X.Y.Z)이 없다")
            rep.hit("model_pinned", "fail", rel(policies[0], root), None, "고정된 모델 버전이 없다")

    # 질문 정의는 jev 디렉터리마다 한 모듈에 모인다. jev 디렉터리 밖의 질문 정의도 흩어진 것으로 본다
    groups: dict[str, list[str]] = {}
    for f in sorted(question_files):
        owner = next((rel(d, root) if d != root else "." for d in jev_dirs if d in (root / f).parents), None)
        groups.setdefault(owner or "(jev 디렉터리 밖)", []).append(f)
    for owner, fs in groups.items():
        if owner == "(jev 디렉터리 밖)":
            for f in fs:
                rep.hit("single_questions_module", "fail", f, None, "jev 디렉터리 밖에 질문 정의가 있다. jev/questions로 옮긴다")
        elif len(fs) > 1:
            for f in fs:
                rep.hit("single_questions_module", "fail", f, None,
                        f"{owner} 안의 질문 정의가 여러 모듈에 흩어져 있다: {fs}. 한 모듈(questions)로 모은다")
    if not question_files:
        rep.skip("single_questions_module", "질문 정의를 찾지 못했다 (SDK 헬퍼나 원시 dict가 아닌 방식일 수 있다)")

    checks = list(rep.checks.values())
    fails = sum(c["status"] == "fail" for c in checks)
    warns = sum(c["status"] == "warn" for c in checks)
    out = {"tool": "jev-kit check", "version": VERSION, "target": str(root),
           "jev_dirs": [rel(d, root) if d != root else "." for d in jev_dirs],
           "question_files": sorted(question_files),
           "summary": {"fail": fails, "warn": warns, "passed": fails == 0},
           "checks": checks}
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
