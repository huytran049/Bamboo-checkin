from __future__ import annotations

import re
from dataclasses import dataclass

from .schema import RagDocument

@dataclass(frozen=True)
class RagChunk:
    source_name: str
    chunk_index: int
    doc_type: str
    chunk_type: str
    section: str
    text: str
    source_group: str
    product: str
    topic: str


def _clean_inline(text: str) -> str:
    cleaned = " ".join((text or "").split()).strip()
    cleaned = cleaned.strip("-*• ")
    return cleaned


class RecursiveCharacterTextSplitter:
    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    def split_text(self, text: str) -> list[str]:
        if not text:
            return []
        # Tìm separator phù hợp nhất
        separator = ""
        remaining_separators: list[str] = []
        for i, sep in enumerate(self.separators):
            if sep == "":
                separator = sep
                break
            if re.search(re.escape(sep), text):
                separator = sep
                remaining_separators = self.separators[i + 1:]
                break

        # Tách text theo separator
        if separator:
            parts = re.split(re.escape(separator), text)
        else:
            parts = list(text)

        # Gộp các phần nhỏ thành chunks có overlap
        chunks: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for part in parts:
            part_len = len(part) + len(separator)
            if current_len + part_len > self.chunk_size and current_parts:
                # Flush chunk hiện tại
                chunk_text = separator.join(current_parts).strip()
                if chunk_text:
                    # Nếu chunk vẫn quá lớn, đệ quy với separator nhỏ hơn
                    if len(chunk_text) > self.chunk_size and remaining_separators:
                        sub = RecursiveCharacterTextSplitter(self.chunk_size, self.chunk_overlap)
                        sub.separators = remaining_separators
                        chunks.extend(sub.split_text(chunk_text))
                    else:
                        chunks.append(chunk_text)
                # Giữ lại overlap: lấy các part cuối sao cho tổng <= chunk_overlap
                overlap_parts: list[str] = []
                overlap_len = 0
                for p in reversed(current_parts):
                    p_len = len(p) + len(separator)
                    if overlap_len + p_len > self.chunk_overlap:
                        break
                    overlap_parts.insert(0, p)
                    overlap_len += p_len
                current_parts = overlap_parts
                current_len = overlap_len

            current_parts.append(part)
            current_len += part_len

        # Flush phần còn lại
        if current_parts:
            chunk_text = separator.join(current_parts).strip()
            if chunk_text:
                if len(chunk_text) > self.chunk_size and remaining_separators:
                    sub = RecursiveCharacterTextSplitter(self.chunk_size, self.chunk_overlap)
                    sub.separators = remaining_separators
                    chunks.extend(sub.split_text(chunk_text))
                else:
                    chunks.append(chunk_text)

        return [c for c in chunks if c.strip()]


def _chunk_qa_pairs(text: str) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    # Thử bắt format chuẩn Q & A
    qa_matches = list(re.finditer(r"(?:^|\n)\s*Q:\s*(?P<question>.+?)\n\s*A:\s*(?P<answer>.+?)(?=(?:\n\s*Q:)|\Z)", text, flags=re.IGNORECASE | re.DOTALL))
    if qa_matches:
        for match in qa_matches:
            q = _clean_inline(match.group("question"))
            a = _clean_inline(match.group("answer"))
            if q and a: pairs.append((q, a, "qa_pair"))
        return pairs
        
    return []


def draft_chunk_strategy(doc: RagDocument) -> dict[str, str]:
    return {"strategy": "semantic_recursive", "expected_improvement": "high"}


def build_chunks(doc: RagDocument) -> list[RagChunk]:
    raw_items: list[tuple[str, str, str]] = []

    # Prefer explicit Q/A pairs for every document type. Most Rag_data product
    # files are structured as Q:/A: even when their doc_type is not FAQ.
    qa_pairs = _chunk_qa_pairs(doc.text)
    if qa_pairs:
        for question, answer, chunk_type in qa_pairs:
            raw_items.append((question, f"Câu hỏi: {question}\nTrả lời: {answer}", chunk_type))

    # Nếu không bắt được QA, dùng RecursiveCharacterTextSplitter
    if not raw_items:
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks_text = splitter.split_text(doc.text)
        for i, c in enumerate(chunks_text):
            first_line = c.split("\n")[0][:60]
            raw_items.append((first_line, c, "semantic_recursive_block"))

    chunks: list[RagChunk] = []
    for idx, item in enumerate(raw_items):
        section, text, chunk_type = item
        normalized_text = text.strip()
        if not normalized_text:
            continue
        chunks.append(
            RagChunk(
                source_name=doc.meta.source_name,
                chunk_index=idx,
                doc_type=doc.meta.doc_type.value,
                chunk_type=chunk_type,
                section=section.strip(),
                text=normalized_text,
                source_group=doc.meta.source_group,
                product=doc.meta.product,
                topic=doc.meta.topic,
            )
        )
    return chunks
