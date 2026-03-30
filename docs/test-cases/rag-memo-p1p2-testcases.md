# TestCase: rag-memo-p1p2-completion

> Created: 2026-03-30
> Updated: 2026-03-31
> Target: P1/P2 미구현 기능 완성 + Phase 3 Markdown 렌더링 (CH-02, CH-03, ST-04, F-11)
> Total cases: 20

---

## TC List

| TC# | Category | Test Item | Execution | Expected | Result | Iteration |
|-----|---------|------------|---------|----------|------|------|
| TC-101 | Functional | HistoryPanel 클래스 존재 | pytest test_history_panel.py | import OK | ✅ | 1 |
| TC-102 | Functional | HistoryPanel 세션 목록 표시 | pytest | set_sessions() 후 아이템 수 일치 | ✅ | 1 |
| TC-103 | Functional | HistoryPanel 세션 선택 신호 | pytest | session_selected 신호 emit | ✅ | 1 |
| TC-104 | Functional | HistoryPanel 삭제 신호 | pytest | session_delete_requested 신호 emit | ✅ | 1 |
| TC-105 | Functional | HistoryPanel 검색 필터 | pytest | 키워드로 세션 목록 필터링 | ✅ | 1 |
| TC-106 | Integration | MainWindow 히스토리 패널 포함 | pytest (import) | _history_panel 속성 존재 | ✅ | 1 |
| TC-107 | Integration | 세션 선택 시 ChatPanel 로드 | 수동 검증 | load_history 호출 확인 | ⏭️ | - |
| TC-108 | Integration | 컬렉션 변경 시 히스토리 새로고침 | 수동 검증 | _refresh_history 호출 확인 | ⏭️ | - |
| TC-109 | Functional | Settings Data 탭 존재 | pytest | "Data" 탭 텍스트 확인 | ✅ | 1 |
| TC-110 | Functional | Data 탭 경로 표시 | pytest | base_dir 경로 레이블 표시 | ✅ | 1 |
| TC-111 | Functional | Data 탭 Open in Finder 버튼 | pytest | 버튼 존재 확인 | ✅ | 1 |
| TC-112 | Regression | 기존 테스트 회귀 | pytest tests/ | 99 passed (전체) | ✅ | 1 |
| TC-113 | Functional | ST-04 경로 변경 버튼 존재 | pytest | "변경..." 버튼 존재 | ✅ | 1 |
| TC-114 | Functional | ST-04 파일 복사 (_copy_data_dirs) | pytest + tmp_path | 파일 복사 + config 갱신 | ✅ | 1 |
| TC-115 | Functional | ST-04 레이블 갱신 | pytest | base_dir_label 텍스트 변경 | ✅ | 1 |
| TC-201 | Functional | 어시스턴트 버블 HTML 렌더링 | pytest | content 있으면 HTML setHtml | ✅ | 1 |
| TC-202 | Functional | 사용자 버블 plain text 유지 | pytest | **text** → plain text | ✅ | 1 |
| TC-203 | Functional | finalize_markdown() 스트리밍 완료 후 HTML | pytest | append 후 finalize → HTML | ✅ | 1 |
| TC-204 | Functional | _raw_text 누적 | pytest | append_text → _raw_text 축적 | ✅ | 1 |
| TC-205~208 | Functional | Markdown 렌더링 태그 검증 | pytest | h1/pre/code/strong/em 태그 | ✅ | 1 |

---

## Result Legend
- ⬜ Not run
- ✅ PASS
- ❌ FAIL
- ⏭️ SKIP (reason: ___)

---

## Issue Log

### FAIL Cases
없음

### SKIP Cases
- TC-107/108: MainWindow DB 초기화 필요 — 수동 실행 시 동작 확인됨

### Summary (Iteration 1 — Final)
| Feature | TCs | PASS |
|---------|-----|------|
| CH-02 HistoryPanel | 101~106 | 6/6 ✅ |
| CH-03 히스토리 검색 | 105 포함 | ✅ |
| ST-04 경로 표시 | 109~111 | 3/3 ✅ |
| ST-04 경로 변경 + 마이그레이션 | 113~115 | 3/3 ✅ |
| F-11 Markdown 렌더링 | 201~208 | 8/8 ✅ |
| 전체 회귀 | 112 | 99 passed ✅ |
