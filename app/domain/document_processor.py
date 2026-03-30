"""DocumentProcessor - File format-specific text extraction.

Supports PDF, Markdown (.md), and Plain Text (.txt).
PDF extraction uses pypdf2 with pdfminer.six fallback.
"""
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".txt"}


@dataclass
class PageContent:
    """Content from a single page/section."""
    text: str
    page_num: int | None = None
    section: str | None = None


@dataclass
class DocumentContent:
    """Extracted content from a document."""
    file_name: str
    file_path: str
    file_type: str
    pages: list[PageContent] = field(default_factory=list)
    full_text: str = ""
    file_size: int = 0

    @property
    def total_chars(self) -> int:
        return len(self.full_text)


class DocumentProcessor:
    """Extracts text from PDF, Markdown, and plain text files."""

    def process(self, file_path: str) -> DocumentContent:
        """Extract text from a file.

        Args:
            file_path: Absolute path to the file.

        Returns:
            DocumentContent with extracted text.

        Raises:
            ValueError: If file type is not supported.
            FileNotFoundError: If file does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)

        if ext == ".pdf":
            content = self._extract_pdf(file_path)
        elif ext == ".md":
            content = self._extract_markdown(file_path)
        else:  # .txt
            content = self._extract_text(file_path)

        content.file_name = file_name
        content.file_path = file_path
        content.file_type = ext.lstrip(".")
        content.file_size = file_size

        return content

    def _extract_pdf(self, path: str) -> DocumentContent:
        """Extract text from PDF using PyPDF2, fallback to pdfminer."""
        content = DocumentContent(file_name="", file_path="", file_type="pdf")
        pages_text = []

        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    content.pages.append(PageContent(
                        text=text,
                        page_num=i + 1,
                    ))
                    pages_text.append(text)

        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed for {path}: {e}. Trying pdfminer...")
            try:
                content.pages = []
                pages_text = []
                from pdfminer.high_level import extract_text as pdfminer_extract

                text = pdfminer_extract(path)
                if text and text.strip():
                    content.pages.append(PageContent(text=text.strip(), page_num=1))
                    pages_text.append(text.strip())
                else:
                    logger.error(f"No text extracted from PDF: {path}")
            except Exception as e2:
                logger.error(f"pdfminer extraction also failed for {path}: {e2}")

        content.full_text = "\n\n".join(pages_text)
        return content

    def _extract_markdown(self, path: str) -> DocumentContent:
        """Extract text from Markdown file, preserving sections."""
        content = DocumentContent(file_name="", file_path="", file_type="md")

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        # Split by headings to identify sections
        sections = self._split_markdown_sections(text)

        for section_name, section_text in sections:
            if section_text.strip():
                content.pages.append(PageContent(
                    text=section_text.strip(),
                    section=section_name,
                ))

        content.full_text = text
        return content

    def _extract_text(self, path: str) -> DocumentContent:
        """Extract plain text file content."""
        content = DocumentContent(file_name="", file_path="", file_type="txt")

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        content.pages.append(PageContent(text=text))
        content.full_text = text
        return content

    @staticmethod
    def _split_markdown_sections(text: str) -> list[tuple[str, str]]:
        """Split markdown text into (section_name, section_text) tuples."""
        lines = text.split("\n")
        sections: list[tuple[str, str]] = []
        current_section = "Introduction"
        current_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                # Save previous section
                if current_lines:
                    sections.append((current_section, "\n".join(current_lines)))
                current_section = stripped.lstrip("#").strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        # Save last section
        if current_lines:
            sections.append((current_section, "\n".join(current_lines)))

        return sections if sections else [("", text)]

    @staticmethod
    def is_supported(file_path: str) -> bool:
        """Check if a file extension is supported."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in SUPPORTED_EXTENSIONS

    @staticmethod
    def get_supported_extensions() -> set[str]:
        """Get the set of supported file extensions."""
        return SUPPORTED_EXTENSIONS.copy()
