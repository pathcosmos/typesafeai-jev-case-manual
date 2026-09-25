#!/usr/bin/env python3
"""jev-kit build: 케이스 정의 파일로 평가셋(samples.<split>.jsonl)을 만든다 (INTENT Q6, templates/evalset.md).

사용:
  python3 build.py --cases .jev/eval/cases.json --questions .jev/eval/questions.json \
                   --state-cmd "node .jev/eval/state.mjs" [--cwd TARGET] [--out-dir .jev/eval]
                   [--gold-field gold] [--budget 50] [--require-lang ko]

- state는 프로젝트의 state 함수로 만든다 (다시 구현하지 않는다): --state-cmd 프로세스 하나에 stdin으로
  {"id", "input"} JSONL을 보내고 stdout으로 {"id", "state"} JSONL을 받는다. state가 null이면 오류다
  (운영에서 API에 도달하지 않는 입력은 평가 표본이 될 수 없다).
- 출력 표본은 measure.py와 replay.py가 그대로 읽는 형식이다:
  {"id", "state", "label", <gold-field>, "lang", "pair", "split", "category"}
- 라벨 검사는 measure.py의 check_labels를 그대로 쓴다 (유효한 라벨의 정의는 한 곳).
- 오류가 하나라도 있으면 아무 파일도 쓰지 않는다. 경고는 쓰되 stderr와 --report에 남긴다.
- 표준 라이브러리만 쓴다.
- 종료 코드: 0 완료(경고 포함 가능) · 3 케이스·라벨 오류 · 5 state 명령 오류
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "measure"))
from measure import check_labels, validate_spec  # noqa: E402

VERSION = "0.1.0"
RECOMMENDED = ("clear", "boundary", "adversarial")  # + escalate 값이 gold에 있으면 "escalate"
WAF = re.compile(r"\b(curl|wget)\s+https?://", re.I)
PII = [("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
       ("phone", re.compile(r"\b0\d{1,2}-\d{3,4}-\d{4}\b|\+\d{1,3}[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}")),
       ("internal_host", re.compile(r"\b[\w-]+\.(internal|corp|local|lan|intra)\b|\b10\.\d+\.\d+\.\d+\b|\b192\.168\.\d+\.\d+\b", re.I))]


class StateError(Exception):
    pass


def merge(base, over):
    """variant 병합: 객체는 키 단위로 재귀 병합하고, 그 밖의 값(리스트 포함)은 통째로 바꾼다."""
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = merge(base.get(k), v) if k in base else v
        return out
    return over


def expand(doc: dict, gold_values: list[str]) -> tuple[list[dict], list[str]]:
    """케이스를 표본 단위(변형별)로 펼친다. 반환: (표본 목록, 오류)."""
    errs, rows, seen = [], [], set()
    for n, c in enumerate(doc.get("cases", []), 1):
        cid = c.get("id") if isinstance(c, dict) else None
        where = cid or f"cases[{n}]"
        if not cid:
            errs.append(f"{where}: id가 없다")
            continue
        if cid in seen:
            errs.append(f"{cid}: 중복 케이스 id")
            continue
        seen.add(cid)
        for f in ("split", "gold", "label"):
            if c.get(f) in (None, ""):
                errs.append(f"{cid}: {f}가 없다")
        if c.get("gold") is not None and c["gold"] not in gold_values:
            errs.append(f"{cid}: gold {c['gold']!r}가 gold_values {gold_values}에 없다")
        variants = c.get("variants") or {"": {}}
        if not isinstance(variants, dict):
            errs.append(f"{cid}: variants는 {{언어: 덮어쓸 input}} 객체여야 한다")
            continue
        multi = len(variants) > 1
        for lang, over in variants.items():
            rows.append({"id": f"{cid}-{lang}" if multi else cid, "case": cid,
                         "input": merge(c.get("input", {}), over or {}),
                         "label": c.get("label"), "gold": c.get("gold"), "lang": lang or c.get("lang") or doc.get("default_lang"),
                         "pair": cid if multi else None, "split": c.get("split"), "category": c.get("category")})
    ids = [r["id"] for r in rows]
    for d in sorted({i for i in ids if ids.count(i) > 1}):
        errs.append(f"{d}: 펼친 표본 id가 겹친다 (케이스 id와 -언어 접미사 충돌)")
    return rows, errs


def run_state(cmd: str, cwd: Path | None, rows: list[dict]) -> dict:
    stdin = "".join(json.dumps({"id": r["id"], "input": r["input"]}, ensure_ascii=False) + "\n" for r in rows)
    try:
        p = subprocess.run(shlex.split(cmd), input=stdin, capture_output=True, text=True, cwd=cwd, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise StateError(f"state 명령을 실행하지 못했다: {e}")
    if p.returncode != 0:
        raise StateError(f"state 명령이 {p.returncode}로 끝났다: {p.stderr.strip()[-500:]}")
    out = {}
    for n, line in enumerate(p.stdout.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            sid, state = row["id"], row["state"]
        except (ValueError, KeyError, TypeError):
            raise StateError(f"state 출력 {n}행이 {{\"id\", \"state\"}} JSON이 아니다: {line[:200]}")
        if sid in out:
            raise StateError(f"state 출력에 id {sid!r}가 두 번 있다")
        if state is None:
            raise StateError(f"{sid}: state가 null이다 (운영에서 API에 도달하지 않는 입력은 평가 표본이 될 수 없다)")
        out[sid] = state
    want = {r["id"] for r in rows}
    missing, extra = sorted(want - set(out)), sorted(set(out) - want)
    if missing or extra:
        raise StateError(f"state 출력 id 불일치: 누락 {missing[:10]} · 초과 {extra[:10]}")
    return out


def warnings_for(rows: list[dict], gold_values: list[str], escalate: str | None, budget: int, require_lang: list[str]) -> list[str]:
    w = []
    cats = {r["category"] for r in rows}
    want = list(RECOMMENDED) + (["escalate"] if escalate in gold_values else [])
    for c in want:
        if c not in cats:
            w.append(f"권장 category {c!r}가 없다 (templates/evalset.md §2)")
    decided = [g for g in gold_values if g != escalate]
    clear_gold = {r["gold"] for r in rows if r["category"] == "clear"}
    for g in decided:
        if g not in clear_gold:
            w.append(f"gold {g!r}의 clear 케이스가 없다")
    langs = {r["lang"] for r in rows if r["lang"]}
    for lang in require_lang:
        if lang not in langs:
            w.append(f"언어 {lang!r} 표본이 없다 (--require-lang)")
        elif not any(r["lang"] == lang and not r["pair"] for r in rows):
            w.append(f"언어 {lang!r} 표본이 모두 번역 쌍이다. 원문 {lang} 케이스(단일 변형)를 넣어야 슬라이스 정확도를 잴 수 있다 (templates/evalset.md §4)")
    for split in sorted({r["split"] for r in rows}):
        in_split = [r for r in rows if r["split"] == split]
        miss = [g for g in gold_values if g not in {r["gold"] for r in in_split}]
        if miss:
            w.append(f"split {split!r}에 gold {miss}가 없다 (replay에 --decisions를 줘야 한다)")
        if len(in_split) > budget:
            w.append(f"split {split!r}가 {len(in_split)}건으로 요청 예산 {budget}을 넘는다 (measure를 나눠 돌려야 한다)")
    for r in rows:
        text = json.dumps(r["state"], ensure_ascii=False)
        if WAF.search(text):
            w.append(f"{r['id']}: state에 명령어+URL 문자열이 있다 (Cloudflare가 HTML 403으로 막는다, reference/11)")
        for name, rx in PII:
            if rx.search(text):
                w.append(f"{r['id']}: state에 {name}처럼 보이는 문자열이 있다 (합성 데이터인지 확인)")
    return w


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cases", required=True, type=Path)
    ap.add_argument("--questions", required=True, type=Path)
    ap.add_argument("--state-cmd", required=True)
    ap.add_argument("--cwd", type=Path, default=None, help="state 명령을 실행할 디렉터리 (보통 TARGET)")
    ap.add_argument("--out-dir", type=Path, default=None, help="없으면 cases 파일이 있는 디렉터리")
    ap.add_argument("--gold-field", default="gold")
    ap.add_argument("--budget", type=int, default=50, help="split 하나의 요청 예산 (measure 기본값과 같게)")
    ap.add_argument("--require-lang", action="append", default=[])
    ap.add_argument("--report", type=Path, default=None, help="요약 JSON을 쓸 경로")
    a = ap.parse_args(argv)

    def finish(result: dict, code: int) -> int:
        text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if a.report:
            a.report.parent.mkdir(parents=True, exist_ok=True)
            a.report.write_text(text, encoding="utf-8")
        brief = {k: result[k] for k in ("status", "counts") if k in result}
        brief["errors"], brief["warnings"] = len(result.get("errors", [])), len(result.get("warnings", []))
        sys.stdout.write(json.dumps(brief, ensure_ascii=False) + "\n")
        return code

    base = {"tool": "jev-kit build", "version": VERSION}
    try:
        doc = json.loads(a.cases.read_text(encoding="utf-8"))
        spec = json.loads(a.questions.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return finish({**base, "status": "invalid_cases", "errors": [str(e)]}, 3)
    errs = [f"questions: {e}" for e in validate_spec(spec)]
    gold_values = doc.get("gold_values") or []
    escalate = doc.get("escalate")
    if not gold_values:
        errs.append("cases 파일에 gold_values가 없다")
    if escalate is not None and escalate not in gold_values:
        errs.append(f"escalate {escalate!r}가 gold_values에 없다")
    rows, e2 = expand(doc, gold_values)
    errs += e2
    if not validate_spec(spec):  # spec이 깨졌으면 라벨 검사는 의미가 없다
        # 변형들은 같은 라벨을 공유하므로 케이스 단위로 한 번씩 검사한다. 평가셋에서는 라벨 문제를 오류로 본다
        per_case = {r["case"]: r["label"] if r["label"] is not None else {} for r in rows}
        _, label_warns = check_labels(spec, [{"id": cid, "label": lab} for cid, lab in per_case.items()])
        errs += [f"label: {w}" for w in label_warns]
    if errs:
        for e in errs:
            sys.stderr.write(f"error: {e}\n")
        return finish({**base, "status": "invalid_cases", "errors": errs}, 3)

    try:
        states = run_state(a.state_cmd, a.cwd, rows)
    except StateError as e:
        sys.stderr.write(f"error: {e}\n")
        return finish({**base, "status": "state_error", "errors": [str(e)]}, 5)
    for r in rows:
        r["state"] = states[r["id"]]

    warns = warnings_for(rows, gold_values, escalate, a.budget, a.require_lang)
    for w in warns:
        sys.stderr.write(f"warning: {w}\n")
    out_dir = a.out_dir or a.cases.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    splits = sorted({r["split"] for r in rows})
    for split in splits:
        lines = [json.dumps({"id": r["id"], "state": r["state"], "label": r["label"], a.gold_field: r["gold"],
                             "lang": r["lang"], "pair": r["pair"], "split": r["split"], "category": r["category"]},
                            ensure_ascii=False) for r in rows if r["split"] == split]
        (out_dir / f"samples.{split}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def count(key):
        vals = sorted({str(r[key]) for r in rows})
        return {v: sum(str(r[key]) == v for r in rows) for v in vals}

    return finish({**base, "status": "built", "files": [str(out_dir / f"samples.{s}.jsonl") for s in splits],
                   "counts": {"cases": len({r["case"] for r in rows}), "samples": len(rows),
                              "pairs": len({r["pair"] for r in rows if r["pair"]}),
                              "split": count("split"), "gold": count("gold"), "lang": count("lang"), "category": count("category")},
                   "warnings": warns}, 0)


if __name__ == "__main__":
    raise SystemExit(main())
