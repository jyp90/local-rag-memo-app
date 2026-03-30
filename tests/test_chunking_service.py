"""Tests for ChunkingService."""
import pytest

from app.domain.chunking_service import ChunkingService, Chunk
from app.domain.document_processor import DocumentContent, PageContent


class TestChunkingService:
    """Test suite for ChunkingService text chunking."""

    def test_init_defaults(self):
        cs = ChunkingService()
        assert cs.chunk_size == 500
        assert cs.overlap == 50

    def test_init_custom(self):
        cs = ChunkingService(chunk_size=200, overlap=20)
        assert cs.chunk_size == 200
        assert cs.overlap == 20

    def test_invalid_chunk_size(self):
        with pytest.raises(ValueError, match="chunk_size must be >= 50"):
            ChunkingService(chunk_size=10)

    def test_invalid_overlap(self):
        with pytest.raises(ValueError, match="overlap must be >= 0"):
            ChunkingService(chunk_size=100, overlap=-1)
        with pytest.raises(ValueError, match="overlap must be >= 0"):
            ChunkingService(chunk_size=100, overlap=100)

    def test_short_text_single_chunk(self):
        cs = ChunkingService(chunk_size=500, overlap=50)
        content = DocumentContent(
            file_name="test.txt",
            file_path="/test.txt",
            file_type="txt",
            pages=[PageContent(text="Short text.")],
            full_text="Short text.",
        )
        chunks = cs.chunk(content, doc_id="test-id")
        assert len(chunks) == 1
        assert chunks[0].text == "Short text."
        assert chunks[0].doc_id == "test-id"

    def test_long_text_multiple_chunks(self):
        cs = ChunkingService(chunk_size=100, overlap=10)
        long_text = "This is a sentence about testing. " * 50
        content = DocumentContent(
            file_name="test.txt",
            file_path="/test.txt",
            file_type="txt",
            pages=[PageContent(text=long_text)],
            full_text=long_text,
        )
        chunks = cs.chunk(content, doc_id="test-id")
        assert len(chunks) > 1
        # Each chunk should have reasonable size
        for chunk in chunks:
            assert len(chunk.text) > 0

    def test_chunks_have_metadata(self):
        cs = ChunkingService(chunk_size=500, overlap=0)
        content = DocumentContent(
            file_name="doc.md",
            file_path="/path/doc.md",
            file_type="md",
            pages=[PageContent(text="Test content", page_num=1, section="Intro")],
            full_text="Test content",
        )
        chunks = cs.chunk(content, doc_id="doc-123")
        assert len(chunks) == 1
        assert chunks[0].metadata["doc_id"] == "doc-123"
        assert chunks[0].metadata["file_name"] == "doc.md"
        assert chunks[0].metadata["page_num"] == 1
        assert chunks[0].metadata["section"] == "Intro"

    def test_multiple_pages(self):
        cs = ChunkingService(chunk_size=500, overlap=0)
        content = DocumentContent(
            file_name="doc.pdf",
            file_path="/doc.pdf",
            file_type="pdf",
            pages=[
                PageContent(text="Page 1 content here.", page_num=1),
                PageContent(text="Page 2 content here.", page_num=2),
            ],
            full_text="Page 1 content here.\n\nPage 2 content here.",
        )
        chunks = cs.chunk(content, doc_id="doc-456")
        assert len(chunks) == 2
        assert chunks[0].page_num == 1
        assert chunks[1].page_num == 2

    def test_empty_page_skipped(self):
        cs = ChunkingService(chunk_size=500, overlap=0)
        content = DocumentContent(
            file_name="test.txt",
            file_path="/test.txt",
            file_type="txt",
            pages=[
                PageContent(text="Content"),
                PageContent(text=""),  # Empty page
                PageContent(text="More content"),
            ],
            full_text="Content\n\nMore content",
        )
        chunks = cs.chunk(content, doc_id="test")
        assert len(chunks) == 2

    def test_chunk_ids_unique(self):
        cs = ChunkingService(chunk_size=100, overlap=10)
        text = "Test sentence. " * 50
        content = DocumentContent(
            file_name="test.txt",
            file_path="/test.txt",
            file_type="txt",
            pages=[PageContent(text=text)],
            full_text=text,
        )
        chunks = cs.chunk(content, doc_id="test")
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs should be unique"

    def test_overlap_between_chunks(self):
        cs = ChunkingService(chunk_size=100, overlap=20)
        # Create text that will produce multiple chunks
        text = "Word " * 200  # ~1000 chars
        content = DocumentContent(
            file_name="test.txt",
            file_path="/test.txt",
            file_type="txt",
            pages=[PageContent(text=text)],
            full_text=text,
        )
        chunks = cs.chunk(content, doc_id="test")
        assert len(chunks) > 1
