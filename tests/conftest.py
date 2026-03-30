"""Test fixtures and configuration."""
import os
import shutil
import tempfile

import pytest


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test data."""
    d = tempfile.mkdtemp(prefix="rag_memo_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def sample_pdf(tmp_dir):
    """Create a minimal PDF file for testing."""
    try:
        from PyPDF2 import PdfWriter

        writer = PdfWriter()
        # PyPDF2 >= 3.0 blank page approach
        from PyPDF2._page import PageObject
        from PyPDF2.generic import RectangleObject

        page = PageObject.create_blank_page(width=612, height=792)
        writer.add_page(page)

        pdf_path = os.path.join(tmp_dir, "test_doc.pdf")
        with open(pdf_path, "wb") as f:
            writer.write(f)
        return pdf_path
    except Exception:
        # Fallback: create a minimal valid PDF manually
        pdf_path = os.path.join(tmp_dir, "test_doc.pdf")
        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
            b"4 0 obj\n<< /Length 44 >>\nstream\n"
            b"BT /F1 12 Tf 100 700 Td (Test content) Tj ET\n"
            b"endstream\nendobj\n"
            b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000266 00000 n \n"
            b"0000000360 00000 n \n"
            b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
            b"startxref\n441\n%%EOF\n"
        )
        with open(pdf_path, "wb") as f:
            f.write(pdf_content)
        return pdf_path


@pytest.fixture
def sample_md(tmp_dir):
    """Create a sample Markdown file."""
    md_path = os.path.join(tmp_dir, "test_doc.md")
    content = """# Test Document

## Section 1

This is the first section of the test document.
It contains information about testing.

## Section 2

This section covers more details about the topic.
It includes multiple paragraphs.

Additional content in section 2 for testing chunking behavior.

## Section 3

Final section with conclusion and summary.
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    return md_path


@pytest.fixture
def sample_txt(tmp_dir):
    """Create a sample text file."""
    txt_path = os.path.join(tmp_dir, "test_doc.txt")
    content = "This is a plain text document for testing purposes.\n" * 20
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(content)
    return txt_path


@pytest.fixture
def sample_korean_md(tmp_dir):
    """Create a sample Korean Markdown file."""
    md_path = os.path.join(tmp_dir, "korean_doc.md")
    content = """# RAG 시스템 설계

## 개요

로컬 RAG 기반 문서 질의응답 시스템의 설계 문서입니다.
ChromaDB를 벡터 DB로 사용하고 Ollama로 로컬 LLM을 구동합니다.

## 아키텍처

4계층 아키텍처를 사용합니다.
프레젠테이션, 애플리케이션, 도메인, 인프라스트럭처 계층으로 구성됩니다.

## 결론

이 시스템은 완전히 로컬에서 동작하며 외부 API 호출이 필요하지 않습니다.
"""
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
    return md_path
