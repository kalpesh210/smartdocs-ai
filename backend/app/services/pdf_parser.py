import os
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger("smartdocs.parser")

class DocumentParser:
    """
    Parses various document types (PDF, TXT, MD) into structured page/section units
    preserving page numbers, character offsets, and structural metadata.
    """

    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans anomalous whitespace, surrogate characters, and repetitive null bytes."""
        if not text:
            return ""
        # Remove null bytes
        text = text.replace("\x00", "")
        # Replace multiple spaces with a single space, but preserve paragraph breaks
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        # Group together multiple blank lines into double newline
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @classmethod
    def parse_pdf(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Parses PDF file page-by-page.
        Tries pypdf first, then pdfplumber if available.
        """
        pages = []
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                extracted = page.extract_text() or ""
                cleaned = cls.clean_text(extracted)
                if cleaned:
                    pages.append({
                        "page_number": idx + 1,
                        "text": cleaned,
                        "char_count": len(cleaned)
                    })
            if pages:
                return pages
        except Exception as e:
            logger.warning(f"pypdf extraction failed or yielded empty pages: {e}. Trying pdfplumber...")

        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    extracted = page.extract_text() or ""
                    cleaned = cls.clean_text(extracted)
                    if cleaned:
                        pages.append({
                            "page_number": idx + 1,
                            "text": cleaned,
                            "char_count": len(cleaned)
                        })
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")

        return pages

    @classmethod
    def parse_text_or_markdown(cls, file_path: str) -> List[Dict[str, Any]]:
        """Parses raw text, markdown, or code files."""
        encodings = ["utf-8", "latin-1", "utf-16", "cp1252"]
        content = ""
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        cleaned = cls.clean_text(content)
        # Return as page 1 (or split by Markdown headers if large)
        return [{
            "page_number": 1,
            "text": cleaned,
            "char_count": len(cleaned)
        }]

    @classmethod
    def parse_file(cls, file_path: str) -> List[Dict[str, Any]]:
        """Dispatches parser based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return cls.parse_pdf(file_path)
        elif ext in [".txt", ".md", ".csv", ".json", ".log"]:
            return cls.parse_text_or_markdown(file_path)
        else:
            # Fallback to plain text reading
            return cls.parse_text_or_markdown(file_path)
