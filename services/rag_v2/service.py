"""Primary QA/RAG service helpers for the current runtime."""

from __future__ import annotations

from pathlib import Path
import json

from services.rag_v2.chunkers import build_chunks, draft_chunk_strategy
from services.rag_v2.indexer import RAG_V2_INDEX_DIR, RAG_V2_INDEX_NAME, build_index, invalidate_model_cache
from services.rag_v2.qa import answer_question, stream_answer_question
from services.rag_v2.loaders import load_documents
from services.rag_v2.retriever import retrieve, invalidate_index_cache

SAMPLE_QUESTIONS = [
    "Sao Mai Solution Group được thành lập năm nào?",
    "SSG có bao nhiêu nhân sự và đã triển khai bao nhiêu dự án?",
    "EcoSave giúp tiết kiệm điện như thế nào?",
    "Smart Box dùng để làm gì trong nhà máy?",
    "Inspection Machine có thể kiểm tra những gì?",
    "Camera AI của SSG có thể ứng dụng vào đâu?",
    "SSG cung cấp những dịch vụ chính nào?",
    "Nhà máy thông minh của SSG gồm những thành phần nào?",
    "QC Gate dùng để làm gì?",
    "Các giải pháp nổi bật của SSG gồm những gì?",
    "Kiosk hiện hỗ trợ những chức năng chính nào?",
    "Dashboard hiện đang có các phân hệ nào?",
]


def inspect_corpus(data_dir: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for doc in load_documents(data_dir):
        strategy = draft_chunk_strategy(doc)
        items.append(
            {
                "source_name": doc.meta.source_name,
                "doc_type": doc.meta.doc_type.value,
                "source_group": doc.meta.source_group,
                "product": doc.meta.product,
                "topic": doc.meta.topic,
                "chunk_strategy": strategy["strategy"],
                "expected_improvement": strategy["expected_improvement"],
            }
        )
    return items


def preview_chunks(data_dir: Path) -> list[dict[str, str | int]]:
    items: list[dict[str, str | int]] = []
    for doc in load_documents(data_dir):
        for chunk in build_chunks(doc):
            items.append(
                {
                    "source_name": chunk.source_name,
                    "chunk_index": chunk.chunk_index,
                    "doc_type": chunk.doc_type,
                    "chunk_type": chunk.chunk_type,
                    "section": chunk.section,
                    "source_group": chunk.source_group,
                    "product": chunk.product,
                    "topic": chunk.topic,
                    "text": chunk.text,
                }
            )
    return items


def build_index_artifact(data_dir: Path, *, output_dir: Path | None = None) -> dict[str, str | int]:
    result = build_index(data_dir, output_dir=output_dir)
    return json.loads(json.dumps(result, ensure_ascii=False))


def _make_json_safe(value):
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, dict):
        return {key: _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    return value


def preview_retrieval(question: str, *, top_k: int = 5) -> dict:
    result = retrieve(question, top_k=top_k)
    return json.loads(json.dumps(_make_json_safe(result), ensure_ascii=False))


def preview_answer(question: str, *, language: str = "vi", channel: str = "preview") -> dict:
    result = answer_question(question, language=language, channel=channel)
    return json.loads(json.dumps(_make_json_safe(result), ensure_ascii=False))


def get_sample_questions() -> list[str]:
    return SAMPLE_QUESTIONS[:]


def rebuild_index(*, data_dir: Path | None = None, force: bool = True) -> dict[str, str | int]:
    target_dir = data_dir or Path("Rag_data")
    result = build_index(target_dir, force=force)
    # Xóa cache sau rebuild để request tiếp theo load collection mới
    invalidate_index_cache()
    invalidate_model_cache()
    return json.loads(json.dumps(result, ensure_ascii=False))


def get_index_status() -> dict:
    index_path = RAG_V2_INDEX_DIR / f"{RAG_V2_INDEX_NAME}.json"
    if not index_path.exists():
        return {
            "index_name": RAG_V2_INDEX_NAME,
            "is_ready": False,
            "index_path": str(index_path.resolve()),
            "chunk_count": 0,
        }
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    return {
        "index_name": payload.get("index_name") or RAG_V2_INDEX_NAME,
        "is_ready": True,
        "index_path": str(index_path.resolve()),
        "chunk_count": int(payload.get("chunk_count") or 0),
        "embed_model": payload.get("embed_model") or "",
        "embed_model_reason": payload.get("embed_model_reason") or "",
        "generate_model": payload.get("generate_model") or "",
        "source_files": list(payload.get("source_files") or []),
    }
