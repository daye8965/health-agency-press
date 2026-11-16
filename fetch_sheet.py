# -*- coding: utf-8 -*-
"""구글 시트 「보건의료 4개 기관 보도자료 | 매일 수집」 → docs/press.json

Aside가 매일 09:00(KST)에 시트를 채우고, 이 스크립트가 그것을 대시보드가 읽는
JSON으로 옮긴다. 화면(docs/index.html)은 시트를 직접 보지 않고 이 파일만 읽는다 —
구글 문서 주소는 브라우저에서 바로 가져올 수 없고(CORS), 시트를 비공개로 되돌려도
화면이 멈추지 않아야 하기 때문이다.

읽는 길이 둘이다. 위부터 된다.

  ① 통째 내려받기 — https://docs.google.com/spreadsheets/d/{id}/export?format=xlsx
     시트가 '링크가 있는 모든 사용자 = 뷰어'로 열려 있으면 열쇠 없이 된다. 지금 이 방식이다.
     **한 번 요청으로 네 탭을 다 받는다.** gviz CSV(`?tqx=out:csv&sheet=이름`)도 있지만
     탭 이름이 한글이면 `sheet=`가 먹지 않아 어느 탭을 달라고 해도 첫 탭만 옵니다 — 실제로 걸렸다.

  ② 서비스 계정 — 환경변수 GOOGLE_SERVICE_ACCOUNT_JSON 이 있으면 Sheets API로 읽는다.
     시트를 비공개로 되돌렸을 때 쓰는 길이다. 그때는 **시트를 서비스 계정 이메일과 공유**해야 한다.

둘 다 실패하면 **기존 docs/press.json을 그대로 두고** 0이 아닌 코드로 끝난다 —
빈 파일로 덮어써서 화면이 통째로 비는 것이 가장 나쁘다.

    python fetch_sheet.py
    SHEET_ID=... python fetch_sheet.py
"""
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs", "press.json")
SHEET_ID = os.environ.get("SHEET_ID", "1-TjXV6gGCtLYJUvNXWLbGhoefV5aMljJKwWTytoZPIw")
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
TABS = ["보도자료", "수집로그", "기관설정"]          # 운영안내 탭은 사람이 읽는 메모라 안 가져온다
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; health-agency-press)"


def now_kst():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


# ── ① 공개 링크로 통째 내려받기 ────────────────────────────────────────────────
def read_public():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as res:
        blob = res.read()
    # 공유가 꺼져 있으면 구글이 로그인 페이지(HTML)를 200으로 돌려준다 — xlsx는 'PK'로 시작한다
    if not blob.startswith(b"PK"):
        raise RuntimeError("시트가 링크 공유로 열려 있지 않습니다 (로그인 페이지가 왔습니다)")
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
    out = {}
    for tab in TABS:
        if tab not in wb.sheetnames:
            out[tab] = []
            continue
        out[tab] = [[cell_text(v) for v in row] for row in wb[tab].iter_rows(values_only=True)]
    return out, "링크 공유"


def cell_text(v):
    """엑셀 칸을 글자로. **숫자를 그냥 str()하면 '5.0'이 된다** — 확인건수가 그렇게 보였다."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "예" if v else "아니오"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v).strip()


# ── ② 서비스 계정으로 읽기 ────────────────────────────────────────────────────
def read_service_account(sa_json):
    from urllib.parse import quote
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    creds = service_account.Credentials.from_service_account_info(
        json.loads(sa_json), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    sess = AuthorizedSession(creds)
    qs = "&".join("ranges=" + quote(t, safe="") for t in TABS)
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchGet?{qs}"
    resp = sess.get(url, timeout=60)
    resp.raise_for_status()
    out = {}
    for tab, block in zip(TABS, resp.json().get("valueRanges", [])):
        out[tab] = [[str(c).strip() for c in row] for row in block.get("values", [])]
    return out, "서비스 계정"


# ── 표 → 레코드 ──────────────────────────────────────────────────────────────
def as_records(rows):
    """첫 줄을 머리글로 보고 dict 목록으로 바꾼다. 통째로 빈 줄은 버린다."""
    if not rows:
        return []
    head = [h.strip() for h in rows[0]]
    out = []
    for row in rows[1:]:
        if not any(str(c).strip() for c in row):
            continue
        out.append({head[i]: (row[i] if i < len(row) else "") for i in range(len(head))})
    return out


def ymd(v):
    """'2026-11-16' · '2026-11-16 00:00:00' · '2026. 11. 16' 을 모두 2026-11-16으로."""
    m = re.search(r"(\d{4})\D(\d{1,2})\D(\d{1,2})", str(v))
    return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3))) if m else ""


def build(tables, how):
    press = []
    for r in as_records(tables.get("보도자료", [])):
        rid = (r.get("id") or "").strip()
        if not rid:
            continue                                   # id 없는 줄은 집계 대상이 아니다
        attach = [u.strip() for u in re.split(r"\s*\|\s*", r.get("첨부_URL") or "") if u.strip()]
        press.append({
            "id": rid,
            "기관": r.get("기관", ""),
            "날짜": ymd(r.get("게시일", "")),
            "제목": re.sub(r"\s+", " ", r.get("제목", "")).strip(),
            "부서": r.get("부서", ""),
            "원문": r.get("원문_URL", ""),
            "본문": re.sub(r"[ \t]+", " ", r.get("본문", "")).strip(),
            "첨부": attach,
            "상태": r.get("본문상태", ""),
            "비고": r.get("수집비고", ""),
        })
    # 같은 id가 두 번 들어오면 뒤엣것을 버린다 (시트에서 중복 id를 막지만 안전장치로 둔다)
    seen, uniq = set(), []
    for p in press:
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        uniq.append(p)
    uniq.sort(key=lambda p: (p["날짜"], p["id"]), reverse=True)

    log = []
    for r in as_records(tables.get("수집로그", [])):
        log.append({
            "실행시각": r.get("실행시각_KST", ""), "기관": r.get("기관", ""),
            "확인": r.get("확인건수", ""), "신규": r.get("신규건수", ""), "갱신": r.get("갱신건수", ""),
            "결과": r.get("결과", ""), "비고": r.get("오류_비고", ""), "범위": r.get("확인범위", ""),
        })
    log.sort(key=lambda x: x["실행시각"], reverse=True)

    agency = [{"기관": r.get("기관", ""), "코드": r.get("코드", ""),
               "게시판": r.get("공식게시판_URL", "")}
              for r in as_records(tables.get("기관설정", [])) if r.get("기관")]

    return {
        "기준시각": now_kst(),
        "읽은방법": how,
        "시트": SHEET_URL,
        "건수": len(uniq),
        "기관": agency,
        "수집로그": log[:200],        # 로그는 최근 것만 — 화면은 마지막 실행만 본다
        "보도자료": uniq,
    }


def main():
    sa = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    errors = []
    tables = how = None
    for name, fn in (("링크 공유", read_public),
                     ("서비스 계정", (lambda: read_service_account(sa)) if sa else None)):
        if fn is None:
            continue
        try:
            tables, how = fn()
            break
        except Exception as e:                          # noqa: BLE001
            errors.append(f"{name}: {type(e).__name__} {e}")
    if tables is None:
        # 기존 파일을 덮지 않는다 — 빈 화면보다 어제 데이터가 낫다
        sys.exit("시트를 읽지 못했습니다. 기존 docs/press.json을 그대로 둡니다.\n  " + "\n  ".join(errors))

    data = build(tables, how)
    if not data["보도자료"]:
        sys.exit("보도자료 탭이 비어 있습니다 — 기존 파일을 그대로 둡니다.")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
        f.write("\n")
    by = {}
    for p in data["보도자료"]:
        by[p["기관"]] = by.get(p["기관"], 0) + 1
    print("%s · %d건 (%s)" % (how, data["건수"], ", ".join(f"{k} {v}" for k, v in by.items())))
    print("→ %s" % OUT)


if __name__ == "__main__":
    main()
