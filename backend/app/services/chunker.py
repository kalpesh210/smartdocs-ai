import re
import uuid
from typing import List, Dict, Any
from app.core.config import settings

class RecursiveChunker:
    """
    Splits document pages into semantic chunks using recursive boundary hierarchy:
    Paragraphs (\\n\\n) -> Sentences (\\n, . ) -> Clauses (, ) -> Words ( )
    Preserves page numbers, char offsets, and estimated token counts.
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " "]

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimates token count (avg ~4 chars per token in English)."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return max(1, len(text) // 4)

    def split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Recursively breaks text using hierarchical delimiters to fit target chunk_size."""
        final_chunks = []
        separator = separators[-1]
        new_separators = []

        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator else list(text)
        good_splits = []

        for s in splits:
            if not s.strip():
                continue
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if new_separators:
                    other_chunks = self.split_text_recursive(s, new_separators)
                    good_splits.extend(other_chunks)
                else:
                    # Hard character split if no further separator available
                    for j in range(0, len(s), self.chunk_size):
                        good_splits.append(s[j:j + self.chunk_size])

        # Merge small splits together with overlap up to chunk_size
        current_chunk = []
        current_length = 0

        for piece in good_splits:
            piece_len = len(piece) + (len(separator) if separator else 0)
            if current_length + piece_len > self.chunk_size and current_chunk:
                merged = separator.join(current_chunk).strip()
                if merged:
                    final_chunks.append(merged)
                # Keep overlap from the end
                overlap_accum = []
                overlap_len = 0
                for prev in reversed(current_chunk):
                    if overlap_len + len(prev) <= self.chunk_overlap:
                        overlap_accum.insert(0, prev)
                        overlap_len += len(prev)
                    else:
                        break
                current_chunk = overlap_accum
                current_length = overlap_len

            current_chunk.append(piece)
            current_length += piece_len

        if current_chunk:
            merged = separator.join(current_chunk).strip()
            if merged:
                final_chunks.append(merged)

        return final_chunks

    def chunk_document_pages(
        self,
        document_id: str,
        pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Chunks all pages of a document while preserving page metadata and positions.
        """
        chunks = []
        global_chunk_idx = 0

        for page in pages:
            page_num = page.get("page_number", 1)
            page_text = page.get("text", "")
            if not page_text.strip():
                continue

            raw_chunks = self.split_text_recursive(page_text, self.separators)
            char_cursor = 0

            for raw_chunk in raw_chunks:
                clean_chunk = raw_chunk.strip()
                if not clean_chunk:
                    continue

                # Locate offset in page text
                char_start = page_text.find(clean_chunk[:50], char_cursor)
                if char_start == -1:
                    char_start = char_cursor
                char_end = char_start + len(clean_chunk)
                char_cursor = max(char_cursor, char_start + len(clean_chunk) - self.chunk_overlap)

                chunks.append({
                    "id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "chunk_index": global_chunk_idx,
                    "page_number": page_num,
                    "content": clean_chunk,
                    "char_start": char_start,
                    "char_end": char_end,
                    "token_count": self.estimate_tokens(clean_chunk),
                    "metadata": {
                        "page": page_num,
                        "chunk_index": global_chunk_idx,
                        "chars": len(clean_chunk)
                    }
                })
                global_chunk_idx += 1

        return chunks
