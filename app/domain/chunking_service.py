"""ChunkingService - Text chunking strategy management.

Uses recursive character splitting for optimal chunk boundaries.
Configurable chunk_size and overlap.
"""
import logging
import uuid
from dataclasses import dataclass, field

from app.domain.document_processor import DocumentContent, PageContent

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk ready for embedding."""
    id: str
    doc_id: str
    text: str
    page_num: int | None = None
    section: str | None = None
    char_start: int = 0
    char_end: int = 0
    metadata: dict = field(default_factory=dict)


class ChunkingService:
    """Manages text chunking with recursive splitting strategy."""

    # Separators ordered by priority (try to split on these first)
    SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        if chunk_size < 50:
            raise ValueError("chunk_size must be >= 50")
        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be >= 0 and < chunk_size")

        self._chunk_size = chunk_size
        self._overlap = overlap

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    @property
    def overlap(self) -> int:
        return self._overlap

    def chunk(self, content: DocumentContent, doc_id: str) -> list[Chunk]:
        """Split document content into chunks.

        Args:
            content: Extracted document content.
            doc_id: Document UUID for chunk association.

        Returns:
            List of Chunk objects.
        """
        chunks: list[Chunk] = []
        global_offset = 0

        for page in content.pages:
            page_chunks = self._chunk_page(page, doc_id, global_offset, content.file_name)
            chunks.extend(page_chunks)
            global_offset += len(page.text) + 2  # +2 for "\n\n" between pages

        logger.info(
            f"Chunked '{content.file_name}': {len(chunks)} chunks "
            f"(size={self._chunk_size}, overlap={self._overlap})"
        )
        return chunks

    def _chunk_page(
        self,
        page: PageContent,
        doc_id: str,
        global_offset: int,
        file_name: str,
    ) -> list[Chunk]:
        """Chunk a single page/section."""
        text = page.text.strip()
        if not text:
            return []

        splits = self._recursive_split(text)
        chunks = []

        for split_text in splits:
            if not split_text.strip():
                continue

            # Calculate position in original text
            char_start = global_offset + text.find(split_text)
            char_end = char_start + len(split_text)

            chunk = Chunk(
                id=str(uuid.uuid4()),
                doc_id=doc_id,
                text=split_text.strip(),
                page_num=page.page_num,
                section=page.section,
                char_start=char_start,
                char_end=char_end,
                metadata={
                    "doc_id": doc_id,
                    "file_name": file_name,
                    "page_num": page.page_num,
                    "section": page.section or "",
                },
            )
            chunks.append(chunk)

        return chunks

    def _recursive_split(self, text: str) -> list[str]:
        """Recursively split text into chunks respecting boundaries.

        Tries separators in order: paragraph > line > sentence > word > char.
        Applies overlap between chunks.
        """
        if len(text) <= self._chunk_size:
            return [text] if text.strip() else []

        # Find the best separator
        chunks = []
        current_parts: list[str] = []
        current_len = 0

        # Try each separator
        for separator in self.SEPARATORS:
            if separator in text:
                parts = text.split(separator)
                result = self._merge_splits(parts, separator)
                if result:
                    return result

        # Fallback: hard split at chunk_size
        return self._hard_split(text)

    def _merge_splits(self, parts: list[str], separator: str) -> list[str]:
        """Merge small parts into chunks of appropriate size with overlap."""
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for part in parts:
            part_len = len(part) + len(separator)

            if current_len + part_len > self._chunk_size and current:
                # Save current chunk
                chunk_text = separator.join(current)
                chunks.append(chunk_text)

                # Apply overlap: keep trailing parts
                overlap_parts: list[str] = []
                overlap_len = 0
                for p in reversed(current):
                    if overlap_len + len(p) + len(separator) > self._overlap:
                        break
                    overlap_parts.insert(0, p)
                    overlap_len += len(p) + len(separator)

                current = overlap_parts
                current_len = overlap_len

            current.append(part)
            current_len += part_len

        # Don't forget the last chunk
        if current:
            chunk_text = separator.join(current)
            chunks.append(chunk_text)

        # If any chunk is still too large, split it further
        final_chunks = []
        for chunk in chunks:
            if len(chunk) > self._chunk_size * 1.5:
                final_chunks.extend(self._hard_split(chunk))
            else:
                final_chunks.append(chunk)

        return final_chunks

    def _hard_split(self, text: str) -> list[str]:
        """Hard split text at chunk_size boundaries."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + self._chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - self._overlap if self._overlap > 0 else end
        return chunks
