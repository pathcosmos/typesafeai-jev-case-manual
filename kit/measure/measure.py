#!/usr/bin/env python3
"""jev-kit measure: 승인된 표본으로 실제 Jev를 호출해 분포, 토큰, 지연, 임계값 초안을 잰다 (kit/procedure.md 6단계).

사용:
  python3 measure.py --questions spec.json --samples samples.jsonl [--budget-requests 50]
                     [--budget-input-tokens 200000] [--model jev-1.13.0] [--out .jev/measure.json] [--dry-run]

- spec.json: HTTP API 형식의 questions map ({id: {type, instructions, criteria}}).
- samples.jsonl: 한 줄에 {"id": ..., "state": ..., "label": {질문id: 기대값}(선택)}. 합성 데이터나 사용자가 승인한 표본만 쓴다.
- API 키는 환경변수 TYPESAFE_API_KEY에서만 읽는다. 출력, 로그, 파일에 키와 state 원문을 남기지 않는다.
- 표준 라이브러리만 쓴다 (대상 프로젝트의 의존성과 무관하게 동작해야 하므로).
- 종료 코드: 0 완료(표본별 오류 포함) · 2 건너뜀(키 없음) · 3 잘못된 spec · 4 중단(인증 / 요청 형식 오류)
출력 스키마와 판정 기준: kit/measure/README.md
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "0.1.0"
PRICE_PER_MTOK = 0.042          # 입력 토큰 기준, 출력 무료 (reference/09, 2026-09-24 확인)
DEFAULT_BASE_URL = "https://api.typesafe.ai"
MAX_RETRY_AFTER_S = 10.0
THRESHOLD_STATUS = "[잠정] 표본은 평가셋이 아니다. [측정]은 manual/04 평가셋 절차를 거친 뒤에만 붙인다"


# ---------------- spec 검증 ----------------
def validate_spec(spec) -> list[str]:
    errs = []
    if not isinstance(spec, dict) or not spec:
        return ["questions spec은 비어 있지 않은 객체여야 한다"]
    for qid, q in spec.items():
        if not isinstance(q, dict):
            errs.append(f"{qid}: 객체가 아니다")
            continue
        t, crit = q.get("type"), q.get("criteria")
        if t not in ("choice", "score", "noul"):
            errs.append(f"{qid}: type은 choice/score/noul 중 하나여야 한다 ({t!r})")
            continue
        if q.get("instructions") in (None, "", {}, []):
            errs.append(f"{qid}: instructions가 없다")
        if t == "choice":
            if not isinstance(crit, dict) or not crit:
                errs.append(f"{qid}: choice criteria는 비어 있지 않은 객체여야 한다")
            elif len(crit) > 255:
                errs.append(f"{qid}: choice 선택지는 최대 255개다 ({len(crit)})")
        elif t == "score":
            if not isinstance(crit, list) or not 2 <= len(crit) <= 10:
                errs.append(f"{qid}: score criteria는 2~10개의 배열이어야 한다")
            elif any(c is None for c in crit):
                errs.append(f"{qid}: score 레벨에 null이 있다 (API가 422를 반환한다)")
        elif t == "noul" and crit is not None:
            if not isinstance(crit, dict) or not set(crit) <= {"true", "false"}:
                errs.append(f"{qid}: noul criteria는 {{true, false}} 객체여야 한다")
    return errs


def load_samples(path: Path) -> list[dict]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "state" not in row:
            raise ValueError(f"samples {n}행: state가 없다")
        row.setdefault("id", f"line{n}")
        rows.append(row)
    return rows


# ---------------- HTTP ----------------
def classify(status: int | None, content_type: str) -> str:
    if status is None:
        return "connection"
    is_json = "json" in (content_type or "")
    if status == 401 or (status == 403 and is_json):
        return "auth"                       # 키가 없으면 403, 틀리면 401 (reference/11)
    if status == 403:
        return "waf_blocked"                # Cloudflare HTML 403: state에 명령어나 URL 문자열
    if status in (400, 422):
        return "request_invalid"            # 문서는 422, 실제로는 400도 온다
    if status == 413:
        return "too_large"
    if status in (408, 429, 529) or 500 <= status < 600:
        return "capacity"
    return "other"


def post(base_url: str, key: str, body: dict, timeout: float):
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/systemone", data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": f"jev-kit-measure/{VERSION}"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, resp.headers, data, (time.monotonic() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.headers, None, (time.monotonic() - t0) * 1000
    except (urllib.error.URLError, TimeoutError, OSError):
        return None, {}, None, (time.monotonic() - t0) * 1000


def retry_after_seconds(headers, attempt: int) -> float:
    try:
        ra = float(headers.get("retry-after", ""))
        return max(0.0, min(ra, MAX_RETRY_AFTER_S))
    except (TypeError, ValueError):
        return min(0.5 * (2 ** attempt), MAX_RETRY_AFTER_S)


# ---------------- 집계 ----------------
def pct(values: list[float], p: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 4)


def stats(values: list[float]) -> dict:
    if not values:
        return {}
    return {"n": len(values), "min": round(min(values), 4), "p25": pct(values, .25), "median": pct(values, .5),
            "p75": pct(values, .75), "max": round(max(values), 4)}


def best_f1_threshold(pairs: list[tuple[float, bool]]) -> dict | None:
    if not pairs or len({y for _, y in pairs}) < 2:
        return None
    best = None
    for i in range(5, 96, 5):
        t = i / 100
        tp = sum(p >= t and y for p, y in pairs)
        fp = sum(p >= t and not y for p, y in pairs)
        fn = sum(p < t and y for p, y in pairs)
        f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
        if best is None or f1 > best["f1"]:
            best = {"threshold": t, "f1": round(f1, 4), "n": len(pairs)}
    best["status"] = "[잠정]"
    return best


def summarize(spec: dict, results: list[dict], labels: dict) -> dict:
    out = {}
    for qid, q in spec.items():
        answers = [(r["id"], r["answers"][qid]) for r in results if qid in r.get("answers", {})]
        t = q["type"]
        s: dict = {"type": t, "n": len(answers)}
        if t == "choice":
            counts: dict = {}
            for _, a in answers:
                counts[a["choice"]] = counts.get(a["choice"], 0) + 1
            s["choice_counts"] = dict(sorted(counts.items()))
            s["confidence"] = stats([a["confidence"] for _, a in answers])
            s["p_top"] = stats([max(a["probabilities"].values()) for _, a in answers])
            s["n_options"] = len(q["criteria"])
            lab = [(a["choice"], labels[i][qid]) for i, a in answers if qid in labels.get(i, {})]
            if lab:
                s["label_accuracy"] = round(sum(p == y for p, y in lab) / len(lab), 4)
                s["label_n"] = len(lab)
        elif t == "noul":
            vals = [a["noul"] for _, a in answers]
            s["noul"] = stats(vals)
            s["histogram_10"] = [sum(1 for v in vals if min(int(v * 10), 9) == b) for b in range(10)]
            lab = [(a["noul"], bool(labels[i][qid])) for i, a in answers if qid in labels.get(i, {})]
            if lab:
                s["label_accuracy_at_0.5"] = round(sum((p >= .5) == y for p, y in lab) / len(lab), 4)
                s["label_n"] = len(lab)
                s["threshold_draft"] = best_f1_threshold(lab)
        else:
            s["score"] = stats([a["score"] for _, a in answers])
            s["confidence"] = stats([a["confidence"] for _, a in answers])
            s["n_levels"] = len(q["criteria"])
            lab = [(a["score"], int(labels[i][qid])) for i, a in answers if qid in labels.get(i, {})]
            if lab:
                s["label_accuracy_rounded"] = round(sum(round(p) == y for p, y in lab) / len(lab), 4)
                s["label_n"] = len(lab)
        out[qid] = s
    return out


def compact(answers: dict) -> dict:
    c = {}
    for qid, a in answers.items():
        if a.get("type") == "choice":
            c[qid] = {"choice": a["choice"], "confidence": a.get("confidence"), "probabilities": a.get("probabilities")}
        elif a.get("type") == "noul":
            c[qid] = {"noul": a["noul"]}
        elif a.get("type") == "score":
            c[qid] = {"score": a["score"], "confidence": a.get("confidence"), "probabilities": a.get("probabilities")}
    return c


# ---------------- main ----------------
def write(out_path: Path | None, result: dict):
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    brief = {k: result[k] for k in ("status", "reason", "usage", "samples", "errors", "budget") if k in result}
    sys.stdout.write(json.dumps(brief, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions", required=True, type=Path)
    ap.add_argument("--samples", required=True, type=Path)
    ap.add_argument("--budget-requests", type=int, default=50)
    ap.add_argument("--budget-input-tokens", type=int, default=200_000)
    ap.add_argument("--model", default="jev-1.13.0")
    ap.add_argument("--base-url", default=os.environ.get("TYPESAFE_BASE_URL") or DEFAULT_BASE_URL)
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true", help="검증과 계획만 하고 호출하지 않는다")
    a = ap.parse_args(argv)

    base = {"tool": "jev-kit measure", "version": VERSION, "model_requested": a.model,
            "threshold_status": THRESHOLD_STATUS}
    spec = json.loads(a.questions.read_text(encoding="utf-8"))
    errs = validate_spec(spec)
    if errs:
        write(a.out, {**base, "status": "invalid_spec", "errors_spec": errs})
        return 3
    samples = load_samples(a.samples)
    labels = {s["id"]: s.get("label", {}) for s in samples}

    if a.dry_run:
        est = [len(json.dumps({"state": s["state"], "questions": spec}, ensure_ascii=False)) // 3 for s in samples]
        write(a.out, {**base, "status": "dry_run", "plan": {
            "requests": min(len(samples), a.budget_requests), "samples": len(samples),
            "estimated_input_tokens_rough": sum(est), "estimated_cost_usd_rough": round(sum(est) * PRICE_PER_MTOK / 1e6, 6),
            "note": "토큰 추정은 문자 수 / 3의 거친 값이다. 실제 값은 usage.input_tokens로 잰다"}})
        return 0

    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not key:
        write(a.out, {**base, "status": "skipped", "reason": "no_api_key",
                      "note": "TYPESAFE_API_KEY가 없어서 측정을 건너뛰었다. 임계값은 [잠정]으로 유지한다"})
        return 2

    requests_used, tokens_used, last_tokens = 0, 0, None
    errors = {k: 0 for k in ("auth", "waf_blocked", "request_invalid", "too_large", "capacity", "connection", "other")}
    results, latencies, models, stopped, abort = [], [], set(), False, None
    for s in samples:
        body = {"state": s["state"], "model": a.model, "questions": spec}
        est = last_tokens or len(json.dumps(body, ensure_ascii=False)) // 3
        rec = {"id": s["id"], "status": "not_run"}
        for attempt in range(a.max_retries + 1):
            if requests_used >= a.budget_requests or tokens_used + est > a.budget_input_tokens:
                stopped = True
                break
            status, headers, data, ms = post(a.base_url, key, body, a.timeout)
            requests_used += 1
            if status == 200 and data:
                used = int((data.get("usage") or {}).get("input_tokens") or 0)
                tokens_used += used
                last_tokens = used or last_tokens
                latencies.append(ms)
                models.add(data.get("model"))
                rid = headers.get("x-typesafe-request-id") if headers else None
                rec = {"id": s["id"], "status": "ok", "latency_ms": round(ms, 1), "request_id": rid,
                       "input_tokens": used, "answers": compact(data.get("answers", {}))}
                break
            kind = classify(status, headers.get("Content-Type", "") if headers else "")
            errors[kind] += 1
            rec = {"id": s["id"], "status": "error", "error": kind, "http_status": status}
            if kind in ("auth", "request_invalid"):
                abort = kind
                break
            if kind in ("capacity", "connection") and attempt < a.max_retries:
                time.sleep(retry_after_seconds(headers or {}, attempt))
                continue
            break
        results.append(rec)
        if abort or stopped:
            break

    ok = [r for r in results if r["status"] == "ok"]
    out = {**base,
           "status": "aborted" if abort else "completed",
           **({"reason": abort} if abort else {}),
           "models": sorted(m for m in models if m),
           "usage": {"requests": requests_used, "input_tokens": tokens_used,
                     "estimated_cost_usd": tokens_used * PRICE_PER_MTOK / 1e6},
           "budget": {"requests": a.budget_requests, "input_tokens": a.budget_input_tokens, "stopped_by_budget": stopped},
           "samples": {"total": len(samples), "ok": len(ok), "error": sum(r["status"] == "error" for r in results),
                       "not_run": len(samples) - len([r for r in results if r["status"] != "not_run"])},
           "errors": errors,
           "latency_ms": ({"p50": pct(latencies, .5), "p95": pct(latencies, .95), "n": len(latencies)} if latencies else {}),
           "questions": summarize(spec, ok, labels),
           "per_sample": results}
    write(a.out, out)
    return 4 if abort else 0


if __name__ == "__main__":
    raise SystemExit(main())
