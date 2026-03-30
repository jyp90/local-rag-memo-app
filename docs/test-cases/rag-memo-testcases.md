# TestCase: rag-memo

> Created: 2026-03-30
> Target: Local RAG Memo — 전체 기능 검증
> Total cases: 16

---

## TC List

| TC# | Category | Test Item | Execution | Expected | Result | Iteration |
|-----|---------|------------|---------|----------|------|------|
| TC-001 | Functional | MessageBubble 텍스트 렌더링 | pytest test_chat_panel.py | 텍스트 content 설정 후 toPlainText() == content | ✅ | 1 |
| TC-002 | Functional | MessageBubble 높이 계산 | pytest test_chat_panel.py | minimumHeight >= 24 | ✅ | 1 |
| TC-003 | Functional | MessageBubble 스트리밍 append | pytest test_chat_panel.py | append_text 후 전체 텍스트 포함 | ✅ | 1 |
| TC-004 | Functional | DocumentProcessor PDF 추출 | pytest test_document_processor.py | content.text 반환 | ✅ | 1 |
| TC-005 | Functional | ChunkingService 청크 분할 | pytest test_chunking_service.py | len(chunks) > 0 | ✅ | 1 |
| TC-006 | Functional | VectorStore upsert/search | pytest test_vector_store.py | similarity_search 결과 반환 | ✅ | 1 |
| TC-007 | Functional | DocumentStore CRUD | pytest test_document_store.py | save/get/delete 모두 동작 | ✅ | 1 |
| TC-008 | Functional | QueryEngine 프롬프트 조립 | pytest test_query_engine.py | 질문+컨텍스트 포함된 프롬프트 | ✅ | 1 |
| TC-009 | Functional | LlmClient 추상화 | pytest (import check) | OllamaClient/ClaudeClient is ABC subclass | ✅ | 1 |
| TC-010 | Functional | EmbeddingService 로드 | pytest test_embedding_service.py | is_loaded() == True after load() | ✅ | 1 |
| TC-011 | Boundary | 빈 컬렉션 질문 | 코드 검증 | add_user_message + no-doc 메시지 표시 | ✅ | 1 |
| TC-012 | Boundary | MessageBubble 빈 content | pytest | minimumHeight >= 24 even with empty string | ✅ | 1 |
| TC-013 | Exception | PDF 파싱 실패 처리 | pytest test_document_processor.py | 손상 파일 → RuntimeError 예외 처리 | ✅ | 1 |
| TC-014 | Exception | Ollama 미연결 시 is_available | pytest (mock) | is_available() == False without server | ✅ | 1 |
| TC-015 | Integration | RagController 초기화 | pytest (import+init) | RagController() 정상 생성 | ✅ | 1 |
| TC-016 | Integration | EmbeddingService 모듈 import | pytest | reload_embedding_model 메서드 존재 | ✅ | 1 |

---

## Result Legend
- ⬜ Not run
- ✅ PASS
- ❌ FAIL
- ⏭️ SKIP (reason: ___)

---

## Issue Log

### FAIL Cases
(없음 — 실행 전)
