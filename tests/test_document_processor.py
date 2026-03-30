"""Tests for DocumentProcessor."""
import os
import pytest

from app.domain.document_processor import DocumentProcessor, SUPPORTED_EXTENSIONS


class TestDocumentProcessor:
    """Test suite for DocumentProcessor text extraction."""

    def setup_method(self):
        self.processor = DocumentProcessor()

    def test_supported_extensions(self):
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".txt" in SUPPORTED_EXTENSIONS
        assert ".docx" not in SUPPORTED_EXTENSIONS

    def test_is_supported(self):
        assert DocumentProcessor.is_supported("test.pdf")
        assert DocumentProcessor.is_supported("test.md")
        assert DocumentProcessor.is_supported("test.txt")
        assert not DocumentProcessor.is_supported("test.docx")
        assert not DocumentProcessor.is_supported("test.jpg")

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            self.processor.process("/nonexistent/file.pdf")

    def test_unsupported_format(self, tmp_dir):
        bad_file = os.path.join(tmp_dir, "test.docx")
        with open(bad_file, "w") as f:
            f.write("fake docx")
        with pytest.raises(ValueError, match="Unsupported file type"):
            self.processor.process(bad_file)

    def test_extract_markdown(self, sample_md):
        content = self.processor.process(sample_md)
        assert content.file_name == "test_doc.md"
        assert content.file_type == "md"
        assert content.file_size > 0
        assert len(content.pages) > 0
        assert "Section 1" in content.full_text
        assert "testing" in content.full_text

    def test_markdown_sections(self, sample_md):
        content = self.processor.process(sample_md)
        sections = [p.section for p in content.pages if p.section]
        # Should have multiple sections
        assert len(sections) >= 3

    def test_extract_text(self, sample_txt):
        content = self.processor.process(sample_txt)
        assert content.file_name == "test_doc.txt"
        assert content.file_type == "txt"
        assert "plain text" in content.full_text
        assert len(content.pages) == 1

    def test_extract_korean(self, sample_korean_md):
        content = self.processor.process(sample_korean_md)
        assert "RAG" in content.full_text
        assert "ChromaDB" in content.full_text
        assert content.total_chars > 0

    def test_empty_file(self, tmp_dir):
        empty = os.path.join(tmp_dir, "empty.txt")
        with open(empty, "w") as f:
            f.write("")
        content = self.processor.process(empty)
        assert content.full_text == ""

    def test_pdf_extraction(self, sample_pdf):
        """Test PDF extraction (may have empty text for minimal PDFs)."""
        content = self.processor.process(sample_pdf)
        assert content.file_name == "test_doc.pdf"
        assert content.file_type == "pdf"
        assert content.file_size > 0
