# Local RAG Memo

macOS 로컬 RAG(Retrieval-Augmented Generation) 기반 문서 Q&A 데스크톱 앱.

문서를 추가하고 Ollama(로컬 LLM) 또는 Claude API로 자연어 질문을 할 수 있는 오프라인 우선 메모 도구.

---

## 기능 현황 (v1.0.0)

| 기능 | 상태 | 설명 |
|------|------|------|
| F-01 문서 인덱싱 | ✅ | PDF / Markdown / TXT 지원, ChromaDB |
| F-02 RAG Q&A | ✅ | 의미 검색 + LLM 답변 생성 |
| F-03 컬렉션 | ✅ | 주제별 컬렉션 생성/전환/삭제 |
| F-04 스트리밍 | ✅ | 토큰 단위 실시간 응답 |
| F-05 대화 기록 | ✅ | 세션 저장/검색/복원 |
| F-06 설정 다이얼로그 | ✅ | LLM 설정, 임베딩 모델, 데이터 디렉토리 이동 |
| F-07 온보딩 | ✅ | 최초 실행 시 LLM 선택 가이드 |
| F-08 출처 보기 | ✅ | 답변 근거 청크 확인 |
| F-09 인덱싱 진행률 | ✅ | 실시간 진행 표시, 취소 지원 |
| F-10 메뉴바 상주 | ✅ | 창 닫아도 트레이 상주, 빠른 복원 |
| F-11 마크다운 렌더링 | ✅ | 헤딩, 굵게, 코드블록, 목록 렌더링 |
| F-12 문서 태그 | ✅ | 태그 추가/편집, 필터링 |
| F-13 대화 내보내기 | ✅ | Markdown 파일로 내보내기 |

---

## 빠른 시작 (새 PC)

### 1. 필수 조건

- **Python 3.11+**
- **Ollama** (로컬 LLM, 권장): [ollama.ai](https://ollama.ai) 에서 설치 후 모델 pull
  ```bash
  ollama pull qwen2.5:7b      # 권장 (빠름)
  # 또는
  ollama pull llama3.2:3b     # 경량
  ```
- **또는 Anthropic API 키** (Claude 사용 시)

### 2. 저장소 클론

```bash
git clone https://github.com/jyp90/local-rag-memo-app.git
cd local-rag-memo-app
```

### 3. 가상환경 및 패키지 설치

```bash
python3 -m venv .venv
source .venv/bin/activate

# 최소 의존성 설치
pip install -r requirements_install.txt

# 또는 전체 고정 버전 설치 (재현 가능한 환경)
pip install -r requirements.txt
```

### 4. 실행

```bash
source .venv/bin/activate
python main.py
```

---

## 프로젝트 구조

```
local-rag-memo/
├── main.py                     # 앱 진입점
├── app/
│   ├── ui/                     # PyQt6 UI 레이어
│   │   ├── main_window.py      # 메인 윈도우 (전체 레이아웃, 시그널 연결)
│   │   ├── chat_panel.py       # 채팅 패널 (스트리밍, 마크다운, 내보내기)
│   │   ├── document_panel.py   # 문서 목록 + 태그 필터
│   │   ├── history_panel.py    # 대화 기록 목록 + 검색
│   │   ├── collection_panel.py # 컬렉션 선택/관리
│   │   ├── settings_dialog.py  # 설정 다이얼로그
│   │   ├── onboarding_dialog.py# 최초 실행 온보딩
│   │   ├── source_viewer.py    # 출처 청크 뷰어
│   │   ├── indexing_progress.py# 인덱싱 진행 위젯
│   │   └── menu_bar_app.py     # 시스템 트레이 (F-10)
│   ├── controller/
│   │   ├── rag_controller.py   # 앱 컨트롤러 (단일 진입점)
│   │   ├── indexing_worker.py  # QThread 인덱싱 워커
│   │   └── query_worker.py     # QThread 쿼리 워커
│   ├── domain/
│   │   ├── document_processor.py  # PDF/MD/TXT 텍스트 추출
│   │   ├── chunking_service.py    # 청크 분할 (LangChain)
│   │   ├── embedding_service.py   # 임베딩 (sentence-transformers)
│   │   ├── query_engine.py        # RAG 프롬프트 조립
│   │   └── conversation_manager.py# 대화 컨텍스트 관리
│   └── infrastructure/
│       ├── document_store.py   # SQLite 메타데이터 + 세션/메시지 저장
│       ├── vector_store.py     # ChromaDB 벡터 저장소
│       ├── config_store.py     # 앱 설정 (JSON)
│       ├── ollama_client.py    # Ollama API 클라이언트
│       ├── claude_client.py    # Anthropic API 클라이언트
│       └── llm_client.py      # LLM 추상 인터페이스
├── tests/                      # pytest 테스트 (131 케이스)
├── resources/
│   └── styles/dark_theme.qss   # Catppuccin Mocha 다크 테마
├── requirements.txt            # 전체 고정 의존성
├── requirements_install.txt    # 최소 설치 의존성
└── pyproject.toml              # 프로젝트 메타데이터
```

---

## 아키텍처

```
Presentation (PyQt6 UI)
    ↕ pyqtSignal
Application (RagController)
    ↕ Python call
Domain (Document/Embedding/Query/Conversation)
    ↕ Python call
Infrastructure (SQLite / ChromaDB / Ollama / Claude)
```

- **단방향 의존성**: UI → Controller → Domain → Infrastructure
- **QThread 워커**: 인덱싱·쿼리는 별도 스레드 (UI 블로킹 없음)
- **LLM 추상화**: `LlmClient` ABC → `OllamaClient` / `ClaudeClient` 교체 가능

---

## 테스트 실행

```bash
source .venv/bin/activate
python -m pytest tests/ -v
# 현재: 131 passed
```

---

## 기본 임베딩 모델

`jhgan/ko-sroberta-multitask` (한국어 특화, 약 500MB)
첫 실행 시 HuggingFace에서 자동 다운로드.
설정 → 임베딩 탭에서 다른 모델로 변경 가능.

---

## 데이터 저장 위치

기본값: `~/.local-rag-memo/`
- `meta.db` — SQLite (문서 메타데이터, 대화 세션, 메시지)
- `chroma/` — ChromaDB 벡터 저장소
- `config.json` — 앱 설정

설정 → 데이터 탭에서 다른 경로로 이동 가능.
