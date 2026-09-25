#!/usr/bin/env python3
"""jev-kit replay: measure.py 결과에 프로젝트의 결정 정책을 다시 적용해서 결정 수준 gold와 비교한다 (INTENT Q6, manual/04).

사용:
  python3 replay.py --measure .jev/measure.json --samples .jev/eval/samples.test.jsonl \
                    --policy-cmd "node .jev/eval/policy.mjs" [--cwd TARGET] [--gold-field gold]
                    [--escalate unsure] [--decisions yes,no,unsure] [--costly yes:no] [--out .jev/replay.json]

- API를 호출하지 않는다. 임계값을 바꾸면 replay만 다시 돌리면 된다 (측정을 다시 하지 않는다).
- 정책은 프로젝트 코드 그대로 쓴다: --policy-cmd 프로세스 하나에 stdin으로 {"id", "answers"} JSONL을 보내고
  stdout으로 {"id", "decision"} JSONL을 받는다. answers는 measure.json per_sample의 answers 그대로다.
- 출력에는 id만 쓴다 (state 원문 없음). 결과는 항상 [잠정]이다. 튜닝은 tune split으로, 보고 수치는 test split으로 한다.
- 표준 라이브러리만 쓴다.
- 종료 코드: 0 완료 · 3 입력 오류 (파일, 사용 가능한 표본 0건) · 5 정책 명령 오류 (실패, id 누락이나 초과, 허용되지 않은 결정)
출력 스키마와 지표 정의: kit/eval/README.md
"""
from __future__ import annotations

import argparse
import json
import math
import shlex
import subprocess
import sys
from pathlib import Path

VERSION = "0.1.0"
THRESHOLD_STATUS = "[잠정] 합성셋이나 소규모 표본의 replay 결과다. [측정]은 manual/04 절차(충분한 평가셋, tune/test 분리)를 거친 뒤에만 붙인다"


class PolicyError(Exception):
    pass


def wilson_upper(k: int, n: int, z: float = 1.96) -> float | None:
    """k/n 비율의 Wilson 95% 상한. n=0이면 None."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(min(1.0, (centre + margin) / denom), 4)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def run_policy(cmd: str, cwd: Path | None, items: list[dict], allowed: set[str]) -> dict[str, str]:
    stdin = "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items)
    try:
        p = subprocess.run(shlex.split(cmd), input=stdin, capture_output=True, text=True, cwd=cwd, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise PolicyError(f"정책 명령을 실행하지 못했다: {e}")
    if p.returncode != 0:
        raise PolicyError(f"정책 명령이 {p.returncode}로 끝났다: {p.stderr.strip()[-500:]}")
    out: dict[str, str] = {}
    for n, line in enumerate(p.stdout.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            sid, dec = row["id"], row["decision"]
        except (ValueError, KeyError, TypeError):
            raise PolicyError(f"정책 출력 {n}행이 {{\"id\", \"decision\"}} JSON이 아니다: {line[:200]}")
        if sid in out:
            raise PolicyError(f"정책 출력에 id {sid!r}가 두 번 있다")
        if dec not in allowed:
            raise PolicyError(f"{sid}: 허용되지 않은 결정 {dec!r} (허용: {sorted(allowed)})")
        out[sid] = dec
    want = {i["id"] for i in items}
    missing, extra = sorted(want - set(out)), sorted(set(out) - want)
    if missing or extra:
        raise PolicyError(f"정책 출력 id 불일치: 누락 {missing[:10]} · 초과 {extra[:10]}")
    return out


def metrics(rows: list[dict], escalate: str, costly: list[tuple[str, str]]) -> dict:
    """rows: {id, gold, decision}. 정의는 README 참조."""
    n = len(rows)
    decided = [r for r in rows if r["decision"] != escalate]
    errors = [r for r in decided if r["decision"] != r["gold"]]
    gold_esc = [r for r in rows if r["gold"] == escalate]
    labels = sorted({r["gold"] for r in rows} | {r["decision"] for r in rows})
    confusion = {g: {d: sum(r["gold"] == g and r["decision"] == d for r in rows) for d in labels} for g in labels}
    m = {
        "n": n,
        "decided": len(decided),
        "coverage": round(len(decided) / n, 4) if n else None,
        "errors_among_decided": len(errors),
        "error_rate_among_decided": round(len(errors) / len(decided), 4) if decided else None,
        "error_rate_upper95": wilson_upper(len(errors), len(decided)),
        "error_ids": sorted(r["id"] for r in errors),
        "gold_escalate": {"n": len(gold_esc), "escalated": sum(r["decision"] == escalate for r in gold_esc),
                          "decided_wrongly": sorted(r["id"] for r in gold_esc if r["decision"] != escalate)},
        "gold_decided_but_escalated": sum(r["gold"] != escalate and r["decision"] == escalate for r in rows),
        "costly": {},
        "confusion": confusion,
    }
    for g, d in costly:
        hit = sorted(r["id"] for r in rows if r["gold"] == g and r["decision"] == d)
        m["costly"][f"{g}->{d}"] = {"count": len(hit), "of_gold": sum(r["gold"] == g for r in rows), "ids": hit}
    return m


def pair_disagreement(rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("pair"):
            groups.setdefault(r["pair"], []).append(r)
    complete = {k: v for k, v in groups.items() if len(v) >= 2}
    diff = sorted(k for k, v in complete.items() if len({r["decision"] for r in v}) > 1)
    return {"pairs_complete": len(complete), "pairs_incomplete": len(groups) - len(complete),
            "disagree": len(diff), "disagree_pairs": diff}


def write(out_path: Path | None, result: dict):
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    o = result.get("overall", {})
    brief = {k: result[k] for k in ("status", "reason") if k in result}
    if o:
        brief.update({k: o[k] for k in ("n", "coverage", "error_rate_among_decided", "error_rate_upper95")})
        brief["costly"] = {k: v["count"] for k, v in o["costly"].items()}
    sys.stdout.write(json.dumps(brief, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--measure", required=True, type=Path)
    ap.add_argument("--samples", required=True, type=Path)
    ap.add_argument("--policy-cmd", required=True)
    ap.add_argument("--cwd", type=Path, default=None, help="정책 명령을 실행할 디렉터리 (보통 TARGET)")
    ap.add_argument("--gold-field", default="gold")
    ap.add_argument("--escalate", default="unsure", help="에스컬레이션(결정 보류)을 뜻하는 결정 값")
    ap.add_argument("--decisions", default=None, help="정책이 낼 수 있는 결정 값, 쉼표 구분 (예: yes,no,unsure). 없으면 gold 값 + escalate + costly")
    ap.add_argument("--costly", action="append", default=[], metavar="GOLD:PRED",
                    help="따로 셀 비싼 오류. 여러 번 줄 수 있다 (예: --costly yes:no)")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv)

    base = {"tool": "jev-kit replay", "version": VERSION, "threshold_status": THRESHOLD_STATUS,
            "policy_cmd": a.policy_cmd, "gold_field": a.gold_field, "escalate": a.escalate}
    try:
        costly = [tuple(c.split(":", 1)) for c in a.costly]
        if any(len(c) != 2 or not all(c) for c in costly):
            raise ValueError("--costly는 GOLD:PRED 형식이어야 한다")
        measure = json.loads(a.measure.read_text(encoding="utf-8"))
        samples = load_jsonl(a.samples)
    except (OSError, ValueError) as e:
        write(a.out, {**base, "status": "invalid_input", "reason": str(e)})
        return 3
    base.update({"model_requested": measure.get("model_requested"), "models": measure.get("models", []),
                 "measure_status": measure.get("status")})

    per = {r["id"]: r for r in measure.get("per_sample", [])}
    warns, rows, excluded = [], [], {"not_in_measure": [], "error": [], "not_run": []}
    for s in samples:
        sid = s.get("id")
        gold = s.get(a.gold_field)
        r = per.get(sid)
        if r is None:
            excluded["not_in_measure"].append(sid)
            continue
        if r.get("status") != "ok":
            excluded["error" if r.get("status") == "error" else "not_run"].append(sid)
            continue
        if gold is None:
            warns.append(f"{sid}: gold 필드 {a.gold_field!r}가 없다 (제외)")
            continue
        rows.append({"id": sid, "gold": gold, "answers": r.get("answers", {}),
                     "lang": s.get("lang"), "split": s.get("split"), "pair": s.get("pair")})
    for w in warns:
        sys.stderr.write(f"warning: {w}\n")
    counts = {"samples": len(samples), "usable": len(rows), **{k: len(v) for k, v in excluded.items()}}
    if not rows:
        write(a.out, {**base, "status": "invalid_input", "reason": "사용 가능한 표본이 0건이다 (id 불일치, 측정 실패, gold 없음)",
                      "counts": counts, "excluded": excluded, **({"warnings": warns} if warns else {})})
        return 3

    allowed = (set(a.decisions.split(",")) if a.decisions else {r["gold"] for r in rows} | {x for c in costly for x in c}) | {a.escalate}
    try:
        decisions = run_policy(a.policy_cmd, a.cwd, [{"id": r["id"], "answers": r["answers"]} for r in rows], allowed)
    except PolicyError as e:
        write(a.out, {**base, "status": "policy_error", "reason": str(e), "counts": counts})
        return 5
    for r in rows:
        r["decision"] = decisions[r["id"]]

    def slice_by(key):
        vals = sorted({r[key] for r in rows if r.get(key)})
        return {v: metrics([r for r in rows if r.get(key) == v], a.escalate, costly) for v in vals}

    out = {**base, "status": "completed", "counts": counts, "excluded": excluded,
           **({"warnings": warns} if warns else {}),
           "overall": metrics(rows, a.escalate, costly),
           "by_split": slice_by("split"), "by_lang": slice_by("lang"),
           "pairs": pair_disagreement(rows),
           "per_sample": [{"id": r["id"], "gold": r["gold"], "decision": r["decision"]} for r in rows]}
    write(a.out, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
