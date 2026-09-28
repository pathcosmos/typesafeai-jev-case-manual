#!/usr/bin/env python3
"""jev-kit options: 코딩 에이전트가 선택지를 제시하면 선택지별 속성 확률을 보여 주는 hook (research/agent-choice-scoring.md).

Claude Code와 Codex의 hook 명령으로 쓴다. stdin으로 hook payload(JSON)를 받고, 보여 줄 것이 있으면 stdout에 hook 출력 JSON을 쓴다.
- Stop: `last_assistant_message`에서 번호 목록 선택지를 코드로 찾는다 (Claude Code 실측, Codex 문서).
- PreToolUse(AskUserQuestion): 구조화된 선택지를 읽는다. 점수는 systemMessage로 보여 준다. 선택지 설명에 점수를 붙이는 JEV_OPTIONS_REWRITE=1은 도구 입력만 바꾸고 데스크톱 대화상자 화면에는 보이지 않았다 (권장하지 않음).

무엇을 묻나: "어느 선택지가 옳은가"가 아니라 선택지마다 좁은 속성을 묻는다 (Noul: 요청 범위 안인가, 되돌리기 쉬운가)와
요청과 가장 맞는 선택지 (Choice, 판정이 아니라 요청 부합). 결정은 사람이 한다.

환경변수 (hook 프로세스에 전달되어야 한다):
  설정 파일 ~/.config/jev/env (또는 JEV_OPTIONS_CONFIG): 아래 변수가 환경에 없으면 이 파일의 JEV_OPTIONS, TYPESAFE_API_KEY,
                       JEV_OPTIONS_ENV_FILE, JEV_OPTIONS_FORMAT을 읽는다 (install.sh가 만든다, 권한 600). 환경변수가 파일보다 우선한다
  JEV_OPTIONS          off(기본) | fake | jev
                       fake: 외부로 아무것도 보내지 않고 결정적인 가짜 점수를 쓴다
                       jev:  TYPESAFE_API_KEY가 있을 때만 api.typesafe.ai에 요청 1건을 보낸다 (요청 텍스트, 선택지 앞 문맥, 선택지).
                             키가 없거나 실패하면 아무것도 표시하지 않는다. 시간 상한 JEV_OPTIONS_TIMEOUT(초, 기본 4)
  JEV_OPTIONS_FORMAT   auto(기본) | table | line. auto는 Claude Code CLI(CLAUDE_CODE_ENTRYPOINT=cli)에서만 여러 줄 표,
                       그 밖(데스크톱 앱, Codex)은 한 줄. 데스크톱 앱은 줄마다 "Stop says:"를 붙여 표가 흐트러진다 (research §4.2)
  JEV_OPTIONS_REWRITE  1이면 AskUserQuestion 선택지 설명 앞에 점수를 붙인다 (기본 끔, 화면 미반영 확인, 권장하지 않음)
  JEV_OPTIONS_ENV_FILE TYPESAFE_API_KEY가 환경에 없을 때 이 dotenv 파일에서 그 한 줄만 읽는다 (키를 hook 설정에 복사하지 않기 위해)
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
import unicodedata
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
RECOMMENDED_CUE = re.compile(r"(?:추천|recommended)\s*[:：]\s*(\d{1,2})", re.I)  # 질문 줄의 "(추천: N)"에서 번호만 코드가 읽는다 (Jev로는 보내지 않음). 콜론 필수 — "추천 2가지 방법입니다" 같은 도입 문장 오탐 방지
RECOMMENDED_SUFFIX = re.compile(r"\s*\((?:recommended|추천)\)\s*$", re.I)  # AskUserQuestion 라벨 끝의 "(Recommended)"/"(추천)" — state로 보내기 전에 지운다 (anchoring)


# ---------------- 선택지 찾기 (코드가 한다) ----------------
def _strip_markdown(label: str) -> str:
    return re.sub(r"\*\*|__|`", "", label).strip()


def _clean(label: str) -> str:
    label = _strip_markdown(label)
    label = RECOMMENDED_SUFFIX.sub("", label).strip()
    return label[:300]


def parse_options(text: str) -> tuple[list[str], str, int | None] | None:
    """마지막 번호 목록 블록을 선택지로 본다. 코드 블록 안은 무시한다.
    선택을 묻는 신호(물음표, '할까요', 'which' 등)가 목록 바로 앞이나 뒤에 없으면 None (작업 단계 목록 같은 것은 건너뛴다).
    반환: (선택지 라벨들, 목록 앞 문맥, 추천 번호 또는 None)"""
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
    # 추천 번호는 질문 줄(목록 바로 뒤)에만 있다고 본다 (선택지 표시 규약) — 도입 줄(before)은 검사하지 않는다
    m = RECOMMENDED_CUE.search(after)
    recommended = int(m.group(1)) if m else None
    if recommended is not None and not 1 <= recommended <= len(items):
        recommended = None
    return items, context[-MAX_TEXT:], recommended


def ask_user_options(tool_input: dict) -> list[tuple[str, list[str], int | None]]:
    """AskUserQuestion의 questions[].options[].label. 세 번째 값은 라벨이 "(Recommended)"로 끝나는 선택지의 1-based 번호(없으면 None).
    그 문구는 state로 보내는 라벨에서는 지운다 (anchoring)."""
    out = []
    for q in (tool_input or {}).get("questions", []) or []:
        opts = [o for o in q.get("options", []) or [] if isinstance(o, dict)]
        if not 2 <= len(opts) <= MAX_OPTIONS:
            continue
        recommended = None
        labels = []
        for i, o in enumerate(opts):
            raw = o.get("label", "") or ""
            if recommended is None and RECOMMENDED_SUFFIX.search(_strip_markdown(raw)):
                recommended = i + 1
            label = _clean(raw) + (f" — {_clean(o['description'])}" if o.get("description") else "")
            labels.append(label)
        out.append((q.get("question") or q.get("header") or "", labels, recommended))
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


def key_from_env_file(path: str | None) -> str:
    """dotenv 파일에서 TYPESAFE_API_KEY 한 줄만 읽는다. 다른 줄은 보지 않는다. 없거나 못 읽으면 빈 문자열."""
    if not path:
        return ""
    try:
        for line in Path(os.path.expanduser(path)).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].lstrip()
            if line.startswith("TYPESAFE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def jev_scores(req: dict, env: dict) -> dict | None:
    """실제 Jev 호출 1건 (재시도 없음: hook은 턴을 늦추면 안 된다). 키는 환경변수(또는 JEV_OPTIONS_ENV_FILE)에서만 읽고 어디에도 쓰지 않는다."""
    key = (env.get("TYPESAFE_API_KEY") or "").strip() or key_from_env_file(env.get("JEV_OPTIONS_ENV_FILE"))
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


def recommend_status(recommended: int | None, scores: list[tuple[float, list[str]]], probs: dict, best: int) -> str:
    """에이전트가 문구로 밝힌 추천 번호를 코드가 계산한 점수와 대조해 3가지 상태 중 하나를 돌려준다 (판정이 아니라 재확인 신호,
    긍정 확인이 아니다 — "재검토 신호 없음"은 "진행해도 된다"는 뜻이 아니다):
      - 추천 선택지 자체에 ⚠ 경고(범위 밖·되돌리기 어려움)가 있으면 재검토 필요 (부합과 무관한 별개 신호라 그대로 본다)
      - 해당 없음이 크면(부합 자체가 근거가 약함) "추천 ≠ 종합 최고"만으로는 판단하지 않고 근거 약함이라고만 알린다
      - 그 밖에 추천이 종합 최고와 다르면 재검토 필요, 같으면 재검토 신호 없음
    "진행할 가치가 있는가"라는 참/거짓 판정 자체는 값·비용·위험을 하나로 뭉친 것이라 Jev에 묻지 않는다 (README §추천 재검토)."""
    if not recommended or not 1 <= recommended <= len(scores):
        return ""
    _, warn = scores[recommended - 1]
    if warn:
        return f"⚠추천 재검토({recommended}) 자체 경고: {'·'.join(warn)}"
    if probs.get("none", 0) >= 0.3:
        return f"추천({recommended}) 판단 근거 약함"
    if recommended != best:
        return f"⚠추천 재검토({recommended}) 종합 최고 {best}과 다름"
    return f"추천({recommended}) 재검토 신호 없음"


def _width(text: str) -> int:
    """터미널 표시 폭. 한글 같은 전각 문자는 2칸."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _cell(text: str, width: int) -> str:
    """표시 폭 기준으로 자르고 오른쪽을 공백으로 채운다. 말줄임은 ASCII ".."다 ("…"는 모호 폭이라 터미널에 따라 2칸)."""
    if _width(text) > width:
        while _width(text) > width - 2:
            text = text[:-1]
        text += ".."
    return text + " " * (width - _width(text))


def display_format(env: dict) -> str:
    """table | line. auto는 확인한 표면(Claude Code CLI)에서만 표를 쓴다."""
    fmt = (env.get("JEV_OPTIONS_FORMAT") or "auto").strip().lower()
    if fmt in ("table", "line"):
        return fmt
    return "table" if env.get("CLAUDE_CODE_ENTRYPOINT") == "cli" else "line"


LABEL_WIDTH = 20  # 표의 선택지 열 폭 (표시 칸)


def render(options: list[str], resp: dict, mode: str, fmt: str = "line", recommended: int | None = None) -> str:
    """line: 한 줄. 데스크톱 앱은 systemMessage의 줄마다 접두어("Stop says:")를 붙여서 여러 줄 표가 흐트러진다 (research §4.2).
    table: 고정폭 여러 줄 표 (Claude Code CLI). 줄바꿈 없이 읽히도록 한 행을 70칸 안으로 둔다.
    recommended: 에이전트 문구에 있던 추천 번호(코드가 파싱). 추천이 있으면 매번 3상태(재검토 필요·근거 약함·재검토 신호 없음)를 붙인다."""
    a = resp["answers"]
    probs = a["best_match"]["probabilities"]
    tag = "[가짜 점수] " if mode == "fake" else ""
    scores = composite(len(options), a)
    best = max(range(len(scores)), key=lambda i: scores[i][0]) + 1 if scores else 0
    tail = f" · 해당 없음 {probs['none']:.2f}" if probs.get("none", 0) >= 0.3 else ""
    note = recommend_status(recommended, scores, probs, best)
    if note:
        tail += f" · {note}"
    if fmt == "table":
        lines = [f"{tag}Jev 선택지 점검 (확률, 판정이 아님 · 종합 = 부합 비율 × 범위 × 되돌림)",
                 f" #  {_cell('선택지', LABEL_WIDTH)}  부합  범위  되돌림  종합"]
        for i, (o, (s, warn)) in enumerate(zip(options, scores)):
            n = i + 1
            lines.append(f" {n}  {_cell(_short(o, 48), LABEL_WIDTH)}  {probs.get(str(n), 0):.2f}  {a[f'in_scope_{n}']['noul']:.2f}  "
                         f"{a[f'reversible_{n}']['noul']:.2f}    {s:.2f}" + "".join(f"  ⚠{w}" for w in warn))
        lines.append(f"종합 최고 {best}{tail}")
        return "\n".join(lines)
    parts = [f"{i + 1} {_short(o)} {probs.get(str(i + 1), 0):.2f}/{a[f'in_scope_{i + 1}']['noul']:.2f}/{a[f'reversible_{i + 1}']['noul']:.2f}"
             f" 종합 {s:.2f}" + "".join(f" ⚠{w}" for w in warn)
             for i, (o, (s, warn)) in enumerate(zip(options, scores))]
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
CONFIG_KEYS = ("JEV_OPTIONS", "TYPESAFE_API_KEY", "JEV_OPTIONS_ENV_FILE", "JEV_OPTIONS_FORMAT")
CONVENTION = Path(__file__).with_name("convention.md")
DEFAULT_CONFIG = "~/.config/jev/env"  # 테스트는 이 값을 없는 경로로 바꾼다


def read_config(path: str) -> dict:
    """dotenv 형식 설정 파일에서 CONFIG_KEYS만 읽는다. 다른 줄은 무시한다."""
    out: dict = {}
    try:
        for line in Path(os.path.expanduser(path)).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].lstrip()
            k, sep, v = line.partition("=")
            if sep and k in CONFIG_KEYS:
                out[k] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def effective_env(env: dict) -> dict:
    """환경변수 + 설정 파일. 환경에 있는 값이 우선한다 (세션 하나만 끄거나 바꿀 수 있게)."""
    conf = read_config(env.get("JEV_OPTIONS_CONFIG") or DEFAULT_CONFIG)
    return {**{k: v for k, v in conf.items() if v}, **{k: v for k, v in env.items() if v != ""}}


def handle(payload: dict, env: dict) -> dict | None:
    env = effective_env(env)
    mode = (env.get("JEV_OPTIONS") or "off").strip().lower()
    if mode not in ("fake", "jev"):
        return None
    event = payload.get("hook_event_name")
    if event == "SessionStart":
        # 켜져 있을 때만 선택지 표시 규약을 에이전트 맥락에 넣는다 (CLAUDE.md를 기기마다 고치지 않도록)
        try:
            text = CONVENTION.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}
    user_request = last_user_text(payload.get("transcript_path"))
    if event == "Stop":
        if payload.get("stop_hook_active"):
            return None
        found = parse_options(payload.get("last_assistant_message") or "")
        if not found:
            return None
        options, context, recommended = found
        req = build_request(options, user_request, context)
        log_request(req, event, env)
        resp = score(req, mode, env)
        return {"systemMessage": render(options, resp, mode, display_format(env), recommended)} if resp else None
    if event == "PreToolUse" and payload.get("tool_name") == "AskUserQuestion":
        ti = payload.get("tool_input") or {}
        per_q, msgs = [], []
        fmt = display_format(env)
        for question, options, recommended in ask_user_options(ti):
            req = build_request(options, user_request, question)
            log_request(req, event, env)
            resp = score(req, mode, env)
            if not resp:
                return None
            per_q.append({"answers": resp["answers"], "fake": mode == "fake"})
            msgs.append(render(options, resp, mode, fmt, recommended))
        if not per_q:
            return None
        out: dict = {"systemMessage": ("\n\n" if fmt == "table" else "\n").join(msgs)}
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
