from __future__ import annotations

import re
from dataclasses import dataclass

from .schema import DocType, RagDocument


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


def split_blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text or "") if block.strip()]


def draft_chunk_strategy(doc: RagDocument) -> dict[str, str]:
    """Return the intended chunk strategy for each document type.

    This is intentionally simple in phase 1. The actual chunk builders will
    be implemented in the next step after taxonomy validation.
    """

    if doc.meta.doc_type == DocType.FAQ:
        return {"strategy": "qa_pair", "expected_improvement": "high"}
    if doc.meta.doc_type == DocType.MANUAL:
        return {"strategy": "section_step", "expected_improvement": "high"}
    if doc.meta.doc_type == DocType.PRODUCT_SOLUTION:
        return {"strategy": "semantic_block", "expected_improvement": "high"}
    if doc.meta.doc_type == DocType.COMPANY_PROFILE:
        return {"strategy": "fact_block", "expected_improvement": "medium"}
    if doc.meta.doc_type == DocType.SMALL_TALK:
        return {"strategy": "short_exchange", "expected_improvement": "medium"}
    if doc.meta.doc_type == DocType.PROJECT_OVERVIEW:
        return {"strategy": "overview_block", "expected_improvement": "medium"}
    return {"strategy": "review_required", "expected_improvement": "unknown"}


def _clean_inline(text: str) -> str:
    cleaned = " ".join((text or "").split()).strip()
    cleaned = cleaned.strip("-*• ")
    return cleaned


def _normalize_section_title(text: str) -> str:
    cleaned = _clean_inline(text)
    if not cleaned:
        return "general"
    if len(cleaned) > 80:
        return cleaned[:80].rsplit(" ", 1)[0].strip() or cleaned[:80]
    return cleaned


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [_clean_inline(part) for part in parts if _clean_inline(part)]


def _chunk_qa_pairs(text: str) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []

    qa_matches = list(
        re.finditer(
            r"(?:^|\n)\s*Q:\s*(?P<question>.+?)\n\s*A:\s*(?P<answer>.+?)(?=(?:\n\s*Q:)|\Z)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )
    if qa_matches:
        for match in qa_matches:
            question = _clean_inline(match.group("question"))
            answer = _clean_inline(match.group("answer"))
            if question and answer:
                pairs.append((question, answer, "qa_pair"))
        return pairs

    numbered_matches = list(
        re.finditer(
            r"(?:^|\n)\s*\d+\.\s*(?P<question>.+?)\n\s*(?:Trả lời gợi ý:\s*)?(?P<answer>.+?)(?=(?:\n\s*\d+\.\s*)|\Z)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
    )
    if numbered_matches:
        for match in numbered_matches:
            question = _clean_inline(match.group("question"))
            answer = _clean_inline(match.group("answer"))
            if question and answer:
                pairs.append((question, answer, "numbered_qa"))
        return pairs

    lines = [_clean_inline(line) for line in text.splitlines() if _clean_inline(line)]
    idx = 0
    while idx + 1 < len(lines):
        question = lines[idx]
        answer = lines[idx + 1]
        if question.endswith("?") or question.lower().startswith(("ssg", "jss", "bamboo", "công ty", "ten", "tên")):
            pairs.append((question, answer, "line_pair"))
            idx += 2
            continue
        idx += 1
    return pairs


def _chunk_manual_blocks(text: str) -> list[tuple[str, str, str]]:
    blocks = split_blocks(text)
    chunks: list[tuple[str, str, str]] = []
    current_section = "manual"
    buffer_lines: list[str] = []

    def flush_buffer() -> None:
        nonlocal buffer_lines
        content = " ".join(buffer_lines).strip()
        if content:
            chunks.append((current_section, content, "manual_block"))
        buffer_lines = []

    for block in blocks:
        lines = [_clean_inline(line) for line in block.splitlines() if _clean_inline(line)]
        if not lines:
            continue
        first = lines[0]
        if len(lines) == 1 and len(first) <= 70 and ":" not in first:
            flush_buffer()
            current_section = _normalize_section_title(first)
            continue
        if len(first) <= 70 and not re.search(r"[.:]", first):
            flush_buffer()
            current_section = _normalize_section_title(first)
            content = " ".join(lines[1:]).strip()
            if content:
                buffer_lines.append(content)
            continue
        joined = " ".join(lines).strip()
        if joined:
            buffer_lines.append(joined)
    flush_buffer()
    return chunks


def _chunk_fact_blocks(text: str) -> list[tuple[str, str, str]]:
    blocks = split_blocks(text)
    chunks: list[tuple[str, str, str]] = []
    current_section = "facts"
    for block in blocks:
        lines = [_clean_inline(line) for line in block.splitlines() if _clean_inline(line)]
        if not lines:
            continue
        first = lines[0]
        if len(lines) == 1 and len(first) <= 70:
            current_section = _normalize_section_title(first)
            continue
        if len(first) <= 70 and not re.search(r"[.:]", first):
            current_section = _normalize_section_title(first)
        content = " ".join(lines).strip()
        if content:
            chunks.append((current_section, content, "fact_block"))
    return chunks


def _chunk_semantic_blocks(text: str) -> list[tuple[str, str, str]]:
    blocks = split_blocks(text)
    chunks: list[tuple[str, str, str]] = []
    current_section = "overview"
    for block in blocks:
        lines = [_clean_inline(line) for line in block.splitlines() if _clean_inline(line)]
        if not lines:
            continue
        first = lines[0]
        if len(lines) == 1 and len(first) <= 70:
            current_section = _normalize_section_title(first)
            continue
        if len(first) <= 90 and re.match(r"^\d+[\.\)]", first):
            current_section = _normalize_section_title(first)
            content = " ".join(lines[1:]).strip()
            if content:
                chunks.append((current_section, content, "semantic_section"))
            continue
        content = " ".join(lines).strip()
        if content:
            chunks.append((current_section, content, "semantic_block"))
    return chunks


def _chunk_overview_blocks(text: str) -> list[tuple[str, str, str]]:
    blocks = split_blocks(text)
    chunks: list[tuple[str, str, str]] = []
    current_section = "overview"
    for block in blocks:
        lines = [_clean_inline(line) for line in block.splitlines() if _clean_inline(line)]
        if not lines:
            continue
        joined = " ".join(lines).strip()
        if not joined:
            continue
        if len(lines) == 1 and len(lines[0]) <= 70:
            current_section = _normalize_section_title(lines[0])
            continue
        sentences = _split_sentences(joined)
        if len(sentences) >= 3:
            for start in range(0, len(sentences), 2):
                chunk_text = " ".join(sentences[start : start + 2]).strip()
                if chunk_text:
                    chunks.append((current_section, chunk_text, "overview_sentence_group"))
        else:
            chunks.append((current_section, joined, "overview_block"))
    return chunks


def build_chunks(doc: RagDocument) -> list[RagChunk]:
    raw_items: list[tuple[str, str, str]] = []
    if doc.meta.doc_type in {DocType.FAQ, DocType.SMALL_TALK}:
        raw_items = [
            (question, f"Câu hỏi: {question}\nTrả lời: {answer}", chunk_type)
            for question, answer, chunk_type in _chunk_qa_pairs(doc.text)
        ]
    elif doc.meta.doc_type == DocType.MANUAL:
        raw_items = _chunk_manual_blocks(doc.text)
    elif doc.meta.doc_type == DocType.COMPANY_PROFILE:
        raw_items = _chunk_fact_blocks(doc.text)
    elif doc.meta.doc_type == DocType.PRODUCT_SOLUTION:
        raw_items = _chunk_semantic_blocks(doc.text)
    elif doc.meta.doc_type == DocType.PROJECT_OVERVIEW:
        raw_items = _chunk_overview_blocks(doc.text)
    else:
        raw_items = [("general", block, "fallback_block") for block in split_blocks(doc.text)]

    chunks: list[RagChunk] = []
    for idx, item in enumerate(raw_items):
        section, text, chunk_type = item
        normalized_text = _clean_inline(text)
        if not normalized_text:
            continue
        chunks.append(
            RagChunk(
                source_name=doc.meta.source_name,
                chunk_index=idx,
                doc_type=doc.meta.doc_type.value,
                chunk_type=chunk_type,
                section=_normalize_section_title(section),
                text=normalized_text,
                source_group=doc.meta.source_group,
                product=doc.meta.product,
                topic=doc.meta.topic,
            )
        )
    return chunks
