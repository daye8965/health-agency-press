# -*- coding: utf-8 -*-
"""우리 쪽 자료를 추려 docs/ours.json에 둔다 — 정부 보도자료와 엮어 보기 위한 것.

두 곳에서 받는다. **둘 다 이미 공개된 파일이라 열쇠가 필요 없다.**

  · 아산 보도자료 제목 ← hospital-news-dashboard/docs/hospital_press.json
      amc.seoul.kr 보도자료 게시판에서 받아 둔 날짜·제목. 36KB.
  · 아산 기사        ← hospital-news-dashboard/docs/news.csv 의 `병원그룹 = 아산` 행 중
      **제목에 `서울아산병원`이 글자 그대로 있는 것만.**
      네이버 뉴스 수집분. **17MB라 화면에서 직접 읽지 않는다** — 여기서 추려 둔다.
      최근 OURS_DAYS일치(기본 365일)만 담는다.

`news.csv`의 `매체`는 한글 이름을 못 찾으면 도메인 조각(`newdaily`)으로 남아 있다.
여기서는 그대로 둔다 — 한글로 바꾸는 목록(`MEDIA_MAP_FE`)이 저쪽 index.html에 있고,
세 번째 사본을 두면 반드시 어긋나기 때문이다. 화면에는 보이는 대로 나온다.

**화면에서 가리는 기사(`isNoise`) 규칙은 안 걸었다.** 그쪽 규칙이 저쪽 index.html의
자바스크립트라 여기로 옮기면 또 한 벌이 된다. 정부 보도자료와 엮을 때는 정책 낱말이
두 개 이상 겹쳐야 하므로 부동산·연예인 기사가 끼어들 일이 거의 없다(실제로 재 봤다).

    python build_ours.py
    OURS_DAYS=180 python build_ours.py
    OURS_LOCAL=../hospital-news-dashboard python build_ours.py   # 내려받지 않고 옆 폴더에서 읽기
"""
import csv
import io
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs", "ours.json")
RAW = "https://raw.githubusercontent.com/daye8965/hospital-news-dashboard/main/docs/"
DAYS = int(os.environ.get("OURS_DAYS", "365"))
LOCAL = os.environ.get("OURS_LOCAL", "").strip()
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; health-agency-press)"


def grab(name):
    """**맨 앞 BOM을 떼야 한다.** news.csv에 BOM이 있어 첫 열 이름이 '\\ufeff날짜'가 되고,
    `row['날짜']`가 통째로 None이 되어 기사가 0건으로 나왔다."""
    if LOCAL:
        with open(os.path.join(LOCAL, "docs", name), encoding="utf-8-sig") as f:
            return f.read()
    req = urllib.request.Request(RAW + name, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as res:
        return res.read().decode("utf-8-sig", "replace")


def main():
    since = (datetime.now(KST) - timedelta(days=DAYS)).strftime("%Y-%m-%d")

    # ── 우리 보도자료 (amc.seoul.kr 게시판) ──────────────────────────────────
    releases = []
    try:
        board = json.loads(grab("hospital_press.json"))
        for ymd, title in board.get("보도자료", {}).get("아산", []):
            if ymd >= since:
                releases.append([ymd, title])
    except Exception as e:                               # noqa: BLE001
        print("! 보도자료 목록을 못 읽었습니다: %s %s" % (type(e).__name__, e))

    # ── 우리 기사 (news.csv 의 아산 행) ──────────────────────────────────────
    # **제목에 `서울아산병원`이 글자 그대로 있는 기사만** 담는다(2026-11-16).
    # `병원그룹 = 아산`에는 아산이 스쳐 지나가는 기사까지 들어 있어, 정부 보도자료와
    # 엮으면 우리와 상관없는 것이 끌려왔다 — `혁신의료기기 포럼`(식약처)에
    # `한국보건산업진흥원 AI 기본의료` 기사가, `마약류 점검`에 `알보젠코리아 ADHD
    # 치료제` 기사가 붙었다. 둘 다 우리 병원 이야기가 아니다.
    # 요약·본문은 `news.csv`에서 안 가져오므로 **제목에 없으면 못 거릅니다** —
    # 본문에만 우리 이름이 있는 기사는 여기서 빠집니다.
    OURS_RE = re.compile(r"서울아산병원")
    articles = []
    try:
        text = grab("news.csv")
        for r in csv.DictReader(io.StringIO(text)):
            if r.get("병원그룹") != "아산":
                continue
            ymd = (r.get("날짜") or "")[:10]
            if ymd < since:
                continue
            title = (r.get("제목") or "").strip()
            if not title or not OURS_RE.search(title):
                continue
            articles.append([ymd, (r.get("매체") or "").strip(), title,
                             (r.get("언론사원문") or r.get("네이버링크") or "").strip()])
    except Exception as e:                               # noqa: BLE001
        print("! 기사를 못 읽었습니다: %s %s" % (type(e).__name__, e))

    if not releases and not articles:
        sys.exit("우리 쪽 자료를 하나도 못 받았습니다 — 기존 docs/ours.json을 그대로 둡니다.")

    releases.sort(reverse=True)
    articles.sort(reverse=True)
    data = {
        "기준시각": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
        "기준일": since,
        "출처": "daye8965/hospital-news-dashboard (docs/hospital_press.json · docs/news.csv)",
        "보도자료": releases,
        "기사": articles,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print("보도자료 %d건 · 기사 %d건 (%s 이후) → %s (%.1fMB)"
          % (len(releases), len(articles), since, OUT, os.path.getsize(OUT) / 1e6))


if __name__ == "__main__":
    main()
