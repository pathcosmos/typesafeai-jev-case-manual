#!/usr/bin/env python3
"""jev-kit options: 코딩 에이전트가 선택지를 제시하면 선택지별 속성 확률을 보여 주는 hook (research/agent-choice-scoring.md).

Claude Code와 Codex의 hook 명령으로 쓴다. stdin으로 hook payload(JSON)를 받고, 보여 줄 것이 있으면 stdout에 hook 출력 JSON을 쓴다.
- Stop: `last_assistant_message`에서 번호 목록 선택지를 코드로 찾는다 (Claude Code 실측, Codex 문서).
- PreToolUse(AskUserQuestion): 구조화된 선택지를 읽는다. 점수는 systemMessage로 보여 준다. 선택지 설명에 점수를 붙이는 JEV_OPTIONS_REWRITE=1은 도구 입력만 바꾸고 데스크톱 대화상자 화면에는 보이지 않았다 (권장하지 않음).

무엇을 묻나: "어느 선택지가 옳은가"가 아니라 선택지마다 좁은 속성을 묻는다 (Noul: 요청 범위 안인가, 되돌리기 쉬운가)와
요청과 가장 맞는 선택지 (Choice, 판정이 아니라 요청 부합). 결정은 사람이 한다.

환경변수 (hook 프로세스에 전달되어야 한다):
  JEV_OPTIONS          off(기본) | fake | jev
                       fake: 외부로 아무것도 보내지 않고 결정적인 가짜 점수를 쓴다
                       jev:  TYPESAFE_API_KEY가 있을 때만 api.typesafe.ai에 요청 1건을 보낸다 (요청 텍스트, 선택지 앞 문맥, 선택지).
                             키가 없거나 실패하면 아무것도 표시하지 않는다. 시간 상한 JEV_OPTIONS_TIMEOUT(초, 기본 4)
  JEV_OPTIONS_REWRITE  1이면 AskUserQuestion 선택지 설명 앞에 점수를 붙인다 (기본 끔, 화면 미반영 확인, 권장하지 않음)
  JEV_OPTIONS_LOG      경로를 주면 만든 Jev 요청(state 포함)을 로컬 JSONL로 남긴다 (검토용, 외부 전송 없음)
표준 라이브러리만 쓴다. 어떤 오류가 나도 에이전트를 막지 않는다 (종료 코드 0, 출력 없음).
"""
from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.request
import json
import os
import re
import sys
from pathlib import Path

VERSION = "0.1.0"
MODEL = "jev-1.13.0"
MAX_OPTIONS = 9
MAX_TEXT = 2000  # state 필드별 문자 상한
WARN_BELOW = 0.3  # 범위 안·되돌리기 쉬움이 이보다 낮으면 종합과 별도로 경고
MAX_CUE_LINE = 160  # 목록 뒤 질문 줄의 최대 길이 (긴 마무리 문단은 선택 질문으로 보지 않는다)
NUM_ITEM = re.compile(r"^\s{0,3}(?:(\d{1,2})[.)]|([①-⑨]))\s+(.+?)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
CHOICE_CUE = re.compile(
    r"\?|？|할까|할까요|원하시|원하는|골라|선택|어느|어떤 것|어떻게 할|진행할|정해 주|결정해|알려 주"
    r"|which|would you like|should i|do you want|prefer|choose|pick|option|let me know",
    re.I)


# ---------------- 선택지 찾기 (코드가 한다) ----------------
def _clean(label: str) -> str:
    label = re.sub(r"\*\*|__|`", "", label).strip()
    return label[:300]


def parse_options(text: str) -> tuple[list[str], str] | None:
    """마지막 번호 목록 블록을 선택지로 본다. 코드 블록 안은 무시한다.
    선택을 묻는 신호(물음표, '할까요', 'which' 등)가 목록 바로 앞이나 뒤에 없으면 None (작업 단계 목록 같은 것은 건너뛴다).
    반환: (선택지 라벨들, 목록 앞 문맥)"""
    if not text:
        return None
    lines, in_code, blocks, cur = text.splitlines(), False, [], None
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = NUM_ITEM.match(line)
        if m:
            if cur is None:
                cur = {"start": i, "end": i, "items": []}
            cur["items"].append(_clean(m.group(3)))
            cur["end"] = i
        elif cur is not None and line.strip() and re.match(r"^\s{2,}\S", line):
            cur["end"] = i  # 들여쓴 설명 줄은 앞 항목에 속한다
        elif cur is not None and not line.strip():
            continue
        elif cur is not None:
            blocks.append(cur)
            cur = None
    if cur is not None:
        blocks.append(cur)
    if not blocks:
        return None
    b = blocks[-1]
    items = b["items"]
    if not 2 <= len(items) <= MAX_OPTIONS:
        return None
    # 신호는 목록에 붙어 있어야 한다: 바로 앞의 도입 줄, 또는 바로 뒤의 짧은 질문 줄 (다른 문단의 물음표는 세지 않는다)
    before = next((l for l in reversed(lines[:b["start"]]) if l.strip()), "")
    after = next((l for l in lines[b["end"] + 1:] if l.strip()), "")
    if not (CHOICE_CUE.search(before) or (CHOICE_CUE.search(after) and len(after.strip()) <= MAX_CUE_LINE)):
        return None
    context = "\n".join(lines[max(0, b["start"] - 12):b["start"]]).strip()
    return items, context[-MAX_TEXT:]


def ask_user_options(tool_input: dict) -> list[tuple[str, list[str]]]:
    """AskUserQuestion의 questions[].options[].label."""
    out = []
    for q in (tool_input or {}).get("questions", []) or []:
        labels = [_clean(o.get("label", "")) + (f" — {_clean(o['description'])}" if o.get("description") else "")
                  for o in q.get("options", []) or [] if isinstance(o, dict)]
        if 2 <= len(labels) <= MAX_OPTIONS:
            out.append((q.get("question") or q.get("header") or "", labels))
    return out


def last_user_text(transcript_path: str | None) -> str:
    """Claude Code transcript JSONL에서 마지막 사용자 메시지(도구 결과 제외). 없으면 빈 문자열."""
    if not transcript_path:
        return ""
    try:
        rows = Path(transcript_path).read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
    except OSError:
        return ""
    for line in reversed(rows):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "user":
            continue
        c = (d.get("message") or {}).get("content")
        if isinstance(c, str) and c.strip():
            return c.strip()[-MAX_TEXT:]
        if isinstance(c, list):
            texts = [x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text"]
            if texts and not any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
                return "\n".join(texts).strip()[-MAX_TEXT:]
    return ""


# ---------------- Jev 요청 (실제 모드와 같은 모양) ----------------
def build_request(options: list[str], user_request: str, context: str) -> dict:
    """한 요청에 모든 질문을 넣는다 (fan-out). state는 필요한 것만 (요청, 선택지 앞 문맥, 선택지)."""
    state = {"user": {"request": user_request or "(not available)"},
             "agent": {"context": context or "(none)"},
             "options": [{"n": i + 1, "text": o} for i, o in enumerate(options)]}
    questions: dict = {
        "best_match": {"type": "choice",
                       "instructions": "Which option in `options` most directly does what `user.request` asks for? Judge fit to the request as written, not which option is technically best.",
                       "criteria": {**{str(i + 1): f"Option {i + 1}" for i in range(len(options))},
                                    "none": "None of the options fits the request, or the request is not available"}},
    }
    for i in range(len(options)):
        n = i + 1
        questions[f"in_scope_{n}"] = {"type": "noul", "instructions": f"Does option {n} in `options` stay within what `user.request` asks for, without adding work the user did not ask for?"}
        questions[f"reversible_{n}"] = {"type": "noul", "instructions": f"If option {n} in `options` turns out to be wrong, could it be undone easily (no deleted data, no push, no deploy, no external message sent)?"}
    return {"model": MODEL, "state": state, "questions": questions}


# ---------------- 점수 (지금은 가짜만) ----------------
def fake_scores(req: dict) -> dict:
    """결정적인 가짜 답 (같은 입력이면 같은 값). 외부로 아무것도 보내지 않는다. 확률은 소수 둘째 자리 (실제 API와 같은 양자화)."""
    seed = hashlib.sha256(json.dumps(req, sort_keys=True, ensure_ascii=False).encode()).digest()
    def u(k: int) -> float:
        return round(seed[k % len(seed)] / 255, 2)
    answers, k = {}, 0
    for qid, q in req["questions"].items():
        if q["type"] == "noul":
            answers[qid] = {"type": "noul", "noul": u(k)}
            k += 1
        else:
            keys = list(q["criteria"])
            raw = [u(k + j) + 0.01 for j in range(len(keys))]
            k += len(keys)
            total = sum(raw)
            probs = {c: round(r / total, 2) for c, r in zip(keys, raw)}
            best = max(probs, key=probs.get)
            answers[qid] = {"type": "choice", "choice": best, "probabilities": probs}
    return {"model": "FAKE (" + MODEL + " 요청 형식)", "answers": answers}


def jev_scores(req: dict, env: dict) -> dict | None:
    """실제 Jev 호출 1건 (재시도 없음: hook은 턴을 늦추면 안 된다). 키는 환경변수에서만 읽고 어디에도 쓰지 않는다."""
    key = (env.get("TYPESAFE_API_KEY") or "").strip()
    if not key:
        sys.stderr.write("jev-options: TYPESAFE_API_KEY가 없어서 점수를 건너뛴다\n")
        return None
    base = (env.get("TYPESAFE_BASE_URL") or "https://api.typesafe.ai").rstrip("/")
    try:
        timeout = float(env.get("JEV_OPTIONS_TIMEOUT") or 4)
    except ValueError:
        timeout = 4.0
    http = urllib.request.Request(base + "/v1/systemone", data=json.dumps(req).encode("utf-8"), method="POST",
                                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                           "User-Agent": f"jev-kit-options/{VERSION}"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(http, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"jev-options: HTTP {e.code} ({'auth' if e.code in (401, 403) else 'request' if e.code in (400, 422) else 'capacity' if e.code == 429 or e.code >= 500 else 'other'})\n")
        return None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        sys.stderr.write(f"jev-options: {type(e).__name__} (connection/timeout)\n")
        return None
    answers = data.get("answers") or {}
    if "best_match" not in answers or any(q not in answers for q in req["questions"]):
        sys.stderr.write("jev-options: 응답에 질문 답이 빠졌다\n")
        return None
    data["latency_ms"] = round((time.monotonic() - t0) * 1000)
    return data


def score(req: dict, mode: str, env: dict | None = None) -> dict | None:
    if mode == "fake":
        return fake_scores(req)
    if mode == "jev":
        return jev_scores(req, env or {})
    return None


# ---------------- 표시 ----------------
def _short(label: str, width: int = 24) -> str:
    """표시용 짧은 이름: " — 설명"과 ": 설명" 앞부분만, 길면 자른다."""
    head = re.split(r"\s+—\s+|:\s", label, maxsplit=1)[0].strip() or label
    return head if len(head) <= width else head[:width - 1] + "…"


def composite(n: int, answers: dict) -> list[tuple[float, list[str]]]:
    """선택지마다 (종합, 경고). 종합 = (부합 ÷ 가장 높은 부합) × 범위 안 × 되돌리기 쉬움.
    부합은 선택지끼리 나눠 갖는 몫이라 선택지 수에 따라 작아지므로 가장 높은 부합에 대한 비율로 바꾼다.
    곱만 보면 약점 하나가 묻히므로 범위 안·되돌리기 쉬움이 WARN_BELOW 미만이면 따로 경고한다."""
    probs = answers["best_match"]["probabilities"]
    fits = [probs.get(str(i + 1), 0) for i in range(n)]
    top = max(fits) if fits else 0
    out = []
    for i, fit in enumerate(fits):
        scope, rev = answers[f"in_scope_{i + 1}"]["noul"], answers[f"reversible_{i + 1}"]["noul"]
        warn = (["범위 밖"] if scope < WARN_BELOW else []) + (["되돌리기 어려움"] if rev < WARN_BELOW else [])
        out.append(((fit / top if top > 0 else 0.0) * scope * rev, warn))
    return out


def render(options: list[str], resp: dict, mode: str) -> str:
    """한 줄로 만든다. 데스크톱 앱은 systemMessage의 줄마다 접두어("Stop says:")를 붙여서 여러 줄 표가 흐트러진다 (research §4.2)."""
    a = resp["answers"]
    probs = a["best_match"]["probabilities"]
    tag = "[가짜 점수] " if mode == "fake" else ""
    scores = composite(len(options), a)
    parts = [f"{i + 1} {_short(o)} {probs.get(str(i + 1), 0):.2f}/{a[f'in_scope_{i + 1}']['noul']:.2f}/{a[f'reversible_{i + 1}']['noul']:.2f}"
             f" 종합 {s:.2f}" + "".join(f" ⚠{w}" for w in warn)
             for i, (o, (s, warn)) in enumerate(zip(options, scores))]
    best = max(range(len(scores)), key=lambda i: scores[i][0]) + 1 if scores else 0
    tail = f" · 해당 없음 {probs['none']:.2f}" if probs.get("none", 0) >= 0.3 else ""
    return (f"{tag}Jev 선택지 점검 (요청 부합/범위 안/되돌리기 쉬움 → 종합, 판정이 아님): " + " · ".join(parts)
            + f" · 종합 최고 {best}" + tail)


def annotate_ask(tool_input: dict, per_question: list[dict]) -> dict:
    """AskUserQuestion 선택지 설명 앞에 짧은 점수 표시를 붙인 사본."""
    ti = json.loads(json.dumps(tool_input))
    qi = 0
    for q in ti.get("questions", []):
        opts = [o for o in q.get("options", []) if isinstance(o, dict)]
        if not 2 <= len(opts) <= MAX_OPTIONS or qi >= len(per_question):
            continue
        a = per_question[qi]["answers"]
        probs = a["best_match"]["probabilities"]
        for i, o in enumerate(opts):
            n = i + 1
            mark = f"[jev{'·가짜' if per_question[qi]['fake'] else ''} 부합 {probs.get(str(n), 0):.2f} · 범위 {a[f'in_scope_{n}']['noul']:.2f} · 되돌림 {a[f'reversible_{n}']['noul']:.2f}]"
            o["description"] = f"{mark} {o.get('description', '')}".strip()
        qi += 1
    return ti


def log_request(req: dict, event: str, env: dict):
    path = env.get("JEV_OPTIONS_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"event": event, "request": req}, ensure_ascii=False) + "\n")


# ---------------- hook 진입점 ----------------
def handle(payload: dict, env: dict) -> dict | None:
    mode = (env.get("JEV_OPTIONS") or "off").strip().lower()
    if mode not in ("fake", "jev"):
        return None
    event = payload.get("hook_event_name")
    user_request = last_user_text(payload.get("transcript_path"))
    if event == "Stop":
        if payload.get("stop_hook_active"):
            return None
        found = parse_options(payload.get("last_assistant_message") or "")
        if not found:
            return None
        options, context = found
        req = build_request(options, user_request, context)
        log_request(req, event, env)
        resp = score(req, mode, env)
        return {"systemMessage": render(options, resp, mode)} if resp else None
    if event == "PreToolUse" and payload.get("tool_name") == "AskUserQuestion":
        ti = payload.get("tool_input") or {}
        per_q, msgs = [], []
        for question, options in ask_user_options(ti):
            req = build_request(options, user_request, question)
            log_request(req, event, env)
            resp = score(req, mode, env)
            if not resp:
                return None
            per_q.append({"answers": resp["answers"], "fake": mode == "fake"})
            msgs.append(render(options, resp, mode))
        if not per_q:
            return None
        out: dict = {"systemMessage": "\n".join(msgs)}
        if env.get("JEV_OPTIONS_REWRITE") == "1":
            out["hookSpecificOutput"] = {"hookEventName": "PreToolUse", "updatedInput": annotate_ask(ti, per_q)}
        return out
    return None


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        out = handle(payload, dict(os.environ))
        if out:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    except Exception as e:  # hook은 에이전트를 막지 않는다
        sys.stderr.write(f"jev-options: {type(e).__name__}: {e}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
