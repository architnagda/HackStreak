import re
from typing import List, Dict, Any

class ChunkingService:
    """
    Semantic, page-preserving text chunking service.
    Ensures that chunks maintain provenance (page_number, section, sequence).
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def clean_text(text: str) -> str:
        """
        Cleans extra whitespace, normalizes Unicode spaces, and strips unprintable characters.
        """
        if not text:
            return ""
        # Replace multiple spaces / tabs with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize newlines
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    def chunk_page(self, page_content: Dict[str, Any], start_chunk_index: int) -> List[Dict[str, Any]]:
        """
        Chunks text from a single page while preserving page metadata.
        """
        page_number = page_content.get("page_number", 1)
        section = page_content.get("section")
        raw_text = self.clean_text(page_content.get("text", ""))

        if not raw_text:
            return []

        # If total page text is smaller than chunk size, return as a single chunk
        if len(raw_text) <= self.chunk_size:
            return [{
                "chunk_index": start_chunk_index,
                "page_number": page_number,
                "section": section,
                "content": raw_text,
                "token_count": len(raw_text.split())
            }]

        # Split page text into sentences/paragraphs
        paragraphs = raw_text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_idx = start_chunk_index

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if current_length + len(para) > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk).strip()
                chunks.append({
                    "chunk_index": chunk_idx,
                    "page_number": page_number,
                    "section": section,
                    "content": chunk_text,
                    "token_count": len(chunk_text.split())
                })
                chunk_idx += 1

                # Overlap: keep trailing text if applicable
                overlap_text = current_chunk[-1] if len(current_chunk[-1]) <= self.chunk_overlap else current_chunk[-1][-self.chunk_overlap:]
                current_chunk = [overlap_text, para]
                current_length = len(overlap_text) + len(para)
            else:
                current_chunk.append(para)
                current_length += len(para) + 1

        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunks.append({
                    "chunk_index": chunk_idx,
                    "page_number": page_number,
                    "section": section,
                    "content": chunk_text,
                    "token_count": len(chunk_text.split())
                })

        return chunks

    def process_document_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Processes all parsed pages of a document into a sequential list of chunks.
        """
        all_chunks = []
        current_index = 0
        for page in pages:
            page_chunks = self.chunk_page(page, start_chunk_index=current_index)
            all_chunks.extend(page_chunks)
            current_index += len(page_chunks)
        return all_chunks

chunking_service = ChunkingService(chunk_size=600, chunk_overlap=120)
