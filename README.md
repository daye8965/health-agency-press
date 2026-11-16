# 보건의료 4개 기관 보도자료 대시보드

보건복지부 · 식품의약품안전처 · 국민건강보험공단 · 건강보험심사평가원의 공식 보도자료를
한 화면에서 보고, **우리 병원에 적용할 만한 것**을 가려내고, **우리가 낸 보도자료·기사 중
관련 있는 것**을 함께 보여 줍니다.

**👉 https://daye8965.github.io/health-agency-press/**

## 어떻게 도는가

```
Aside (매일 09:00 KST, 내 컴퓨터)
   └→ 구글 시트 「보건의료 4개 기관 보도자료 | 매일 수집」
        └→ GitHub Actions (하루 두 번)  fetch_sheet.py → docs/press.json
                                        build_ours.py  → docs/ours.json
             └→ GitHub Pages  docs/index.html
```

- 수집(Aside)과 화면 갱신(Actions)은 **따로 돕니다.** 화면이 안 바뀌면 수집이 아직 안 돈 것입니다.
- 지금 바로 갱신하려면 Actions 탭 → `시트 읽어 대시보드 갱신` → **Run workflow**.

## 화면에서 하는 일

| | |
|---|---|
| **관련도** | 높음 / 보통 / 낮음. 주제 태그로 정한 **추정**이고 판단은 사람이 합니다 |
| **주제 태그** | 수가·급여 · 의료AI·데이터 · 의료인력·수련 · 환자안전 · 응급·중증 · 질환·검진 · 돌봄·지역의료 · 연구·R&D · 의약품·의료기기 · 행사·협약 · 식품·위생 · 복지일반 · 기관 내부 |
| **우리 쪽 관련 자료** | 우리 보도자료(amc.seoul.kr 게시판)와 아산 기사 중 낱말이 겹치는 것. **어떤 말이 겹쳤는지 함께 보여 줍니다** |
| 필터 | 기관 · 기간 · 관련도 · 주제 · 검색(제목·본문, `-낱말`은 제외) · 우리 자료와 엮인 것만 |
| 엑셀 | 화면이 보여 주는 그대로 한 장 |

판정 규칙은 전부 `docs/index.html` 안의 상수입니다. 고치면 **수집을 다시 돌리지 않아도**
새로고침만으로 반영됩니다. 자세한 배경은 [CLAUDE.md](CLAUDE.md)에 적어 두었습니다.

## 파일

| 파일 | 역할 |
|---|---|
| `fetch_sheet.py` | 구글 시트 → `docs/press.json` |
| `build_ours.py` | `hospital-news-dashboard`의 공개 파일 → `docs/ours.json` |
| `docs/index.html` | 대시보드 본체 (단일 파일) |
| `docs/press.json` · `docs/ours.json` | 위 두 스크립트가 쓰는 데이터. **사람이 직접 고치지 말 것** |

로컬 확인:

```bash
python -m http.server 8767
```

그리고 `http://localhost:8767/docs/` (고친 뒤에는 `Ctrl+F5`).
