# Local RAG Memo — Backlog

> 최종 업데이트: 2026-03-31
> 현재 버전: v1.0.0 (131 tests passed)

---

## 우선순위 정의

- **P0** Critical / 버그 수정
- **P1** 주요 기능 개선
- **P2** Nice-to-have
- **P3** 장기 검토

---

## P0 — 버그 / 안정성

### BUG-01: `Thread-auto_conversion` 예외 로그
- **현상**: 앱 실행 시 `Exception in thread Thread-auto_conversion:` 로그 출력
- **추정 원인**: 임베딩 모델 로드 중 비동기 변환 쓰레드 예외 (sentence-transformers 내부)
- **영향**: 현재는 기능적 영향 없음, 로그 오염
- **작업**: 원인 추적 후 suppress 또는 수정

### BUG-02: `requirements_install.txt` 누락 패키지
- **현상**: `requirements_install.txt`에 `pdfminer.six`, `ollama`, `langchain-text-splitters` 미포함
- **영향**: 새 PC에서 최소 설치 후 앱 실행 불가
- **작업**:
  ```
  requirements_install.txt에 추가:
  - pdfminer.six>=20231228
  - ollama>=0.1.0
  - langchain-text-splitters>=0.0.1
  ```

### BUG-03: `pyproject.toml` 버전 불일치
- **현상**: `chromadb = "^0.4"` (실제 설치: 1.5.5), `sentence-transformers = "^2.3"` (실제: 5.3.0)
- **영향**: `poetry install`로 신규 환경 구성 시 버전 충돌 가능
- **작업**: pyproject.toml 의존성 버전 현행화

---

## P1 — 주요 기능 개선

### F-14: .docx 지원
- `requirements_install.txt`에 `python-docx` 포함됐으나 `document_processor.py`에 구현 없음
- `SUPPORTED_EXTENSIONS`에 `.docx` 추가 + `_extract_docx()` 메서드 구현
- 드래그 앤 드롭 UI도 `.docx` 추가

### F-15: 앱 번들링 (.app / DMG)
- 현재 `python main.py`로만 실행 가능
- `py2app` 또는 `PyInstaller`로 macOS `.app` 번들 생성
- `setup.py` (py2app) 또는 `local-rag-memo.spec` (PyInstaller) 작성
- GitHub Actions 빌드 파이프라인

### F-16: 폴더 드래그 앤 드롭 (일괄 인덱싱)
- 현재 파일 단위로만 추가 가능
- 폴더를 드롭하면 하위 지원 파일 전체 인덱싱

### F-17: 태그 관리 패널
- 현재 문서 우클릭으로만 태그 편집 가능
- 설정 또는 별도 패널에서 태그 일괄 관리 (이름 변경, 삭제)

### F-18: 내보내기 포맷 확장
- 현재 Markdown 한 가지만 지원
- JSON 포맷 추가 (개발/분석용)
- HTML 포맷 추가 (공유용, 스타일 포함)

### F-19: HF_TOKEN 설정
- 임베딩 모델 다운로드 시 `Warning: You are sending unauthenticated requests` 출력
- 설정 탭에 HuggingFace 토큰 입력란 추가
- `HF_TOKEN` 환경변수 또는 keyring 저장

---

## P2 — UX 개선

### UX-01: 키보드 단축키 문서화
- 현재 `Cmd+Enter` (전송)만 표시
- 전체 단축키 목록: `Cmd+N` (새 세션), `Cmd+,` (설정), `Cmd+E` (내보내기) 등 추가 정의

### UX-02: 다크/라이트 테마 전환
- 현재 다크(Catppuccin Mocha) 고정
- 설정에서 라이트 테마 선택 가능하도록

### UX-03: 채팅 내 텍스트 검색
- 현재 채팅 패널에 Ctrl+F 검색 없음
- `QTextBrowser` 또는 별도 검색 바 추가

### UX-04: 문서 미리보기
- 문서 목록에서 더블클릭 시 텍스트 미리보기 다이얼로그
- 청크 단위로 페이지네이션

### UX-05: 인덱싱 완료 알림
- 현재 상태바에만 표시
- 트레이 알림(showMessage) 또는 macOS 알림 센터 연동

### UX-06: 컬렉션 가져오기/내보내기
- 다른 PC로 컬렉션(벡터 DB + 메타DB) 이동 지원
- `.zip` 또는 폴더 단위 내보내기/가져오기

---

## P2 — 코드 품질

### QA-01: 누락된 UI 테스트
현재 테스트 없는 컴포넌트:
- `test_collection_panel.py`
- `test_source_viewer.py`
- `test_onboarding_dialog.py`
- `test_indexing_progress.py`

### QA-02: 통합 테스트
- `RagController` → 실제 파일 인덱싱 → 쿼리 흐름 E2E
- 현재는 각 레이어 단위 테스트만 존재

### QA-03: 코드 커버리지 리포트
- `pytest --cov=app --cov-report=html` 설정 추가
- 목표: 80% 이상

---

## P3 — 장기 검토

### F-20: 멀티 LLM 동시 비교
- 같은 질문에 Ollama + Claude 답변을 나란히 비교하는 뷰

### F-21: 문서 청크 시각화
- 문서별 청크 분할 결과를 그래프 또는 테이블로 시각화

### F-22: 자동 태그 추천
- 문서 내용 기반으로 태그 자동 제안 (LLM 활용)

### F-23: iCloud Drive / 외장 폴더 동기화
- 지정 폴더를 감시하여 신규 파일 자동 인덱싱

### F-24: 모바일 앱 (iOS)
- Swift + local embedding 또는 API 기반 iOS 버전

---

## 완료된 작업 (v1.0.0)

- ✅ F-01~F-09: 핵심 기능 (인덱싱, RAG, 컬렉션, 스트리밍, 기록, 설정, 온보딩, 출처, 진행률)
- ✅ F-10: 메뉴바 트레이 상주 (QSystemTrayIcon)
- ✅ F-11: 마크다운 렌더링 (markdown-it-py, Catppuccin CSS)
- ✅ F-12: 문서 태그 (SQLite migration, 필터 UI)
- ✅ F-13: 대화 내보내기 (Markdown)
- ✅ ST-04: 데이터 경로 변경 (파일 복사 + config 갱신)
- ✅ 131 pytest cases PASS
