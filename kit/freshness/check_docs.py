#!/usr/bin/env python3
"""jev-kit freshness: live docs와 SDK 버전을 기준선과 비교해서 바뀐 것만 보고한다 (INTENT Q7).

사용:
  python3 kit/freshness/check_docs.py [--baseline kit/freshness/baseline.json] [--out report.md]
  python3 kit/freshness/check_docs.py --update-baseline   # 사람이 리포트를 보고 지식 베이스를 고친 뒤에만

- 추적 대상은 sources.md에 적힌 docs.typesafe.ai 페이지(와 공식 skill 원문)다. 페이지별 본문 sha256을 기준선과 비교하고,
  바뀐 페이지는 sources.md의 "반영 위치"(다시 볼 문서)와 함께 보고한다.
- llms.txt 목차의 새 페이지와 사라진 페이지, models 페이지의 모델 ID, PyPI·npm의 최신 SDK 버전도 비교한다.
- 이 스크립트는 **아무 문서도 고치지 않는다.** 기준선 갱신(--update-baseline)도 사람이 리포트를 확인하고 문서를 고친 뒤에 한다.
- 표준 라이브러리만 쓴다. API 키가 필요 없다 (공개 문서와 레지스트리만 읽는다).
- 종료 코드: 0 변화 없음 · 1 변화 있음 (리포트 확인 필요) · 2 가져오기 실패가 있음 (일부 결과만 신뢰) · 3 기준선 없음
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[2]
LLMS = "https://docs.typesafe.ai/llms.txt"
MODELS = "https://docs.typesafe.ai/models.md"
PYPI = "https://pypi.org/pypi/typesafe-sdk/json"
NPM = "https://registry.npmjs.org/@typesafe-ai/sdk/latest"
TRACK_HOSTS = ("https://docs.typesafe.ai/", "https://raw.githubusercontent.com/typesafe-ai/")
URL_RE = re.compile(r"https://[^\s|)>\]`]+")
MODEL_RE = re.compile(r"\bjev-(?:latest|preview|\d+\.\d+(?:\.\d+)?)\b")


def fetch(url: str, timeout: float = 20.0) -> tuple[int | None, str]:
    req = urllib.request.Request(url, headers={"User-Agent": f"jev-kit-freshness/{VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, str(e)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tracked_pages(sources_md: str) -> dict[str, str]:
    """sources.md 표에서 {url: 반영 위치}. 표 밖에서 언급된 추적 호스트 URL은 반영 위치 없이 넣는다."""
    pages: dict[str, str] = {}
    for line in sources_md.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        for url in URL_RE.findall(line):
            if not url.startswith(TRACK_HOSTS):
                continue
            where = cells[-1] if len(cells) >= 5 and url in line else pages.get(url, "")
            pages[url] = pages.get(url) or where
    return pages


def llms_urls(text: str) -> list[str]:
    return sorted({u for u in URL_RE.findall(text) if u.startswith("https://docs.typesafe.ai/")})


def snapshot(sources_md: str) -> tuple[dict, list[str]]:
    pages = tracked_pages(sources_md)
    errors: list[str] = []
    urls = sorted(set(pages) | {LLMS, MODELS})
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        results = dict(zip(urls, ex.map(fetch, urls)))
    snap = {"pages": {}, "llms_urls": [], "model_ids": [], "sdk": {}}
    for url in urls:
        status, body = results[url]
        if status is None:
            errors.append(f"{url}: 가져오기 실패 ({body[:120]})")
            continue
        snap["pages"][url] = {"status": status, "sha256": sha(body) if status == 200 else None, "where": pages.get(url, "")}
    st, body = results[LLMS]
    if st == 200:
        snap["llms_urls"] = llms_urls(body)
    st, body = results[MODELS]
    if st == 200:
        snap["model_ids"] = sorted(set(MODEL_RE.findall(body)))
    for name, url, pick in (("python:typesafe-sdk", PYPI, lambda d: d["info"]["version"]),
                            ("js:@typesafe-ai/sdk", NPM, lambda d: d["version"])):
        st, body = fetch(url)
        try:
            snap["sdk"][name] = pick(json.loads(body)) if st == 200 else None
        except (ValueError, KeyError):
            snap["sdk"][name] = None
        if snap["sdk"][name] is None:
            errors.append(f"{url}: 버전을 읽지 못했다 (status {st})")
    return snap, errors


def diff(base: dict, now: dict) -> dict:
    d = {"pages_changed": [], "pages_status": [], "pages_new_tracked": [], "llms_added": [], "llms_removed": [],
         "models_added": [], "models_removed": [], "sdk": []}
    bp, np_ = base.get("pages", {}), now.get("pages", {})
    for url, cur in sorted(np_.items()):
        old = bp.get(url)
        if old is None:
            d["pages_new_tracked"].append(url)
        elif old["status"] != cur["status"]:
            d["pages_status"].append({"url": url, "was": old["status"], "now": cur["status"], "where": cur["where"]})
        elif old["sha256"] != cur["sha256"]:
            d["pages_changed"].append({"url": url, "where": cur["where"]})
    if now.get("llms_urls"):  # 목차를 못 가져왔으면 비교하지 않는다 (오류로 이미 보고됨)
        b, n = set(base.get("llms_urls", [])), set(now["llms_urls"])
        d["llms_added"], d["llms_removed"] = sorted(n - b), sorted(b - n)
    if now.get("model_ids"):
        b, n = set(base.get("model_ids", [])), set(now["model_ids"])
        d["models_added"], d["models_removed"] = sorted(n - b), sorted(b - n)
    for k, v in now.get("sdk", {}).items():
        if v is not None and base.get("sdk", {}).get(k) != v:
            d["sdk"].append({"package": k, "was": base.get("sdk", {}).get(k), "now": v})
    return d


def has_changes(d: dict) -> bool:
    return any(d[k] for k in d)


def report_md(d: dict, errors: list[str], base_date: str, today: str) -> str:
    L = [f"# Jev 지식 베이스 주간 점검 ({today})", "",
         f"기준선: {base_date} · 도구: `kit/freshness/check_docs.py` {VERSION} · **이 리포트는 아무 문서도 고치지 않았다.**", ""]
    if not has_changes(d) and not errors:
        L += ["변화 없음. 할 일 없음.", ""]
        return "\n".join(L)
    if d["sdk"]:
        L += ["## SDK 새 버전", "", "| 패키지 | 기준선 | 지금 | 다시 볼 곳 |", "| --- | --- | --- | --- |"]
        L += [f"| `{s['package']}` | {s['was']} | **{s['now']}** | changelog → reference/12·13, sources.md 머리말, AGENTS.md, scaffold 버전 고정 (`kit/scaffolds/verify.sh`) |" for s in d["sdk"]]
        L.append("")
    if d["models_added"] or d["models_removed"]:
        L += ["## 모델 ID 변화 (models 페이지)", "",
              f"- 추가: {', '.join(f'`{m}`' for m in d['models_added']) or '없음'}",
              f"- 사라짐: {', '.join(f'`{m}`' for m in d['models_removed']) or '없음'}",
              "- 다시 볼 곳: reference/09, reference/10(jaggedness), 모든 문서의 기준 모델 표기, scaffold의 `MODEL` 고정값", ""]
    if d["pages_status"]:
        L += ["## 상태가 바뀐 페이지 (404 등)", "", "| 페이지 | 기준선 | 지금 | 반영 위치 |", "| --- | --- | --- | --- |"]
        L += [f"| {p['url']} | {p['was']} | **{p['now']}** | {p['where'] or '—'} |" for p in d["pages_status"]]
        L.append("")
    if d["pages_changed"]:
        L += ["## 본문이 바뀐 추적 페이지", "", "| 페이지 | 다시 볼 문서 (sources.md 반영 위치) |", "| --- | --- |"]
        L += [f"| {p['url']} | {p['where'] or '—'} |" for p in d["pages_changed"]]
        L += ["", "본문 비교는 해시 기준이다. 무엇이 바뀌었는지는 페이지를 읽어서 확인한다 (`curl -sL <url>`).", ""]
    if d["llms_added"] or d["llms_removed"]:
        L += ["## llms.txt 목차 변화", ""]
        L += [f"- 새 페이지: {u}" for u in d["llms_added"]]
        L += [f"- 사라진 페이지: {u}" for u in d["llms_removed"]]
        L += ["", "새 페이지가 기존 레퍼런스와 관련 있으면 sources.md에 추가하고 기준선을 갱신한다.", ""]
    if d["pages_new_tracked"]:
        L += ["## sources.md에 새로 추가된 추적 페이지 (기준선에 없음)", ""] + [f"- {u}" for u in d["pages_new_tracked"]] + [""]
    if errors:
        L += ["## 가져오기 실패 (이번 결과는 일부만 신뢰)", ""] + [f"- {e}" for e in errors] + [""]
    L += ["## 다음 단계 (사람이 결정)", "",
          "1. 위 페이지를 읽고 지식 베이스 수정이 필요한지 판단한다 (CLAUDE.md 작성 규칙, 같은 사실을 요약한 곳도 함께).",
          "2. 고쳤으면 sources.md 확인일을 갱신하고 `python3 kit/freshness/check_docs.py --update-baseline`으로 기준선을 갱신한다.",
          "3. 고칠 것이 없으면(문구 수정 등) 기준선만 갱신한다.", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sources", type=Path, default=ROOT / "sources.md")
    ap.add_argument("--baseline", type=Path, default=Path(__file__).with_name("baseline.json"))
    ap.add_argument("--out", type=Path, default=None, help="Markdown 리포트 경로 (없으면 stdout)")
    ap.add_argument("--json", type=Path, default=None, help="diff JSON 경로")
    ap.add_argument("--update-baseline", action="store_true", help="지금 상태를 기준선으로 저장한다 (리포트 확인 후에만)")
    a = ap.parse_args(argv)

    today = dt.date.today().isoformat()
    snap, errors = snapshot(a.sources.read_text(encoding="utf-8"))
    if a.update_baseline:
        if errors:
            sys.stderr.write("가져오기 실패가 있어서 기준선을 갱신하지 않는다:\n" + "\n".join(errors) + "\n")
            return 2
        a.baseline.write_text(json.dumps({"tool": "jev-kit freshness", "version": VERSION, "date": today, **snap},
                                         ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sys.stdout.write(f"기준선 저장: {a.baseline} (페이지 {len(snap['pages'])}, 목차 {len(snap['llms_urls'])}, 모델 {snap['model_ids']}, SDK {snap['sdk']})\n")
        return 0
    if not a.baseline.exists():
        sys.stderr.write(f"기준선이 없다: {a.baseline}. 먼저 --update-baseline을 실행한다\n")
        return 3
    base = json.loads(a.baseline.read_text(encoding="utf-8"))
    d = diff(base, snap)
    md = report_md(d, errors, base.get("date", "?"), today)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(md, encoding="utf-8")
    else:
        sys.stdout.write(md)
    if a.json:
        a.json.write_text(json.dumps({"date": today, "baseline_date": base.get("date"), "diff": d, "errors": errors},
                                     ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 2 if errors else (1 if has_changes(d) else 0)


if __name__ == "__main__":
    raise SystemExit(main())
