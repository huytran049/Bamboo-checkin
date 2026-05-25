from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from urllib import request

import numpy as np
import chromadb

from .chunkers import RagChunk, build_chunks
from .loaders import iter_rag_files, load_documents


OLLAMA_HOST = (os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
OLLAMA_TIMEOUT_SEC = int((os.getenv("QA_OLLAMA_TIMEOUT_SECONDS") or "25").strip() or "25")
RAG_V2_INDEX_DIR = Path(os.getenv("RAG_V2_INDEX_DIR") or "rag/indexes")
RAG_V2_INDEX_NAME = (os.getenv("RAG_V2_INDEX_NAME") or "rag_v2_default").strip() or "rag_v2_default"
RAG_V2_EMBED_BATCH_SIZE = max(1, int((os.getenv("RAG_V2_EMBED_BATCH_SIZE") or "16").strip() or "16"))

EMBED_MODEL_CANDIDATES = [
    "bge-m3",
    "bge-m3:latest",
    "nomic-embed-text:latest",
    "nomic-embed-text",
]

GENERATE_MODEL_CANDIDATES = [
    "qwen3:8b",
    "qwen3:14b",
    "llama3:latest",
]

# Module-level cache để tránh gọi Ollama /api/tags mỗi request
_model_cache: dict[str, tuple[str, str]] = {}


def _installed_ollama_models() -> set[str]:
    try:
        payload = request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=5).read().decode("utf-8")
        data = json.loads(payload)
    except Exception:
        return set()
    models = data.get("models") or []
    return {
        str(item.get("name") or "").strip()
        for item in models
        if str(item.get("name") or "").strip()
    }


def _pick_installed_model(candidates: list[str], installed: set[str]) -> str:
    for candidate in candidates:
        if candidate in installed:
            return candidate
        if ":" not in candidate and f"{candidate}:latest" in installed:
            return f"{candidate}:latest"
    return ""


def detect_embed_model() -> tuple[str, str]:
    cache_key = "embed"
    if cache_key in _model_cache:
        return _model_cache[cache_key]
    configured = (os.getenv("RAG_V2_EMBED_MODEL") or "").strip()
    installed = _installed_ollama_models()
    if configured:
        result = (configured, "configured") if configured in installed else (configured, "configured_missing")
    else:
        picked = _pick_installed_model(EMBED_MODEL_CANDIDATES, installed)
        if picked:
            reason = "preferred_bge" if picked.startswith("bge-m3") else "fallback_installed"
            result = (picked, reason)
        else:
            result = (EMBED_MODEL_CANDIDATES[0], "default_missing")
    _model_cache[cache_key] = result
    return result


def detect_generate_model() -> tuple[str, str]:
    cache_key = "generate"
    if cache_key in _model_cache:
        return _model_cache[cache_key]
    configured = (os.getenv("RAG_V2_GENERATE_MODEL") or "").strip()
    installed = _installed_ollama_models()
    if configured:
        result = (configured, "configured") if configured in installed else (configured, "configured_missing")
    else:
        picked = _pick_installed_model(GENERATE_MODEL_CANDIDATES, installed)
        result = (picked, "auto") if picked else (GENERATE_MODEL_CANDIDATES[0], "default_missing")
    _model_cache[cache_key] = result
    return result


def invalidate_model_cache() -> None:
    """Gọi hàm này sau khi rebuild index hoặc thay đổi model."""
    _model_cache.clear()


def _normalize_vector(vector) -> list[float]:
    arr = np.asarray(vector, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return []
    norm = float(np.linalg.norm(arr))
    if norm <= 0:
        return arr.tolist()
    return (arr / norm).tolist()


def _build_source_signature(paths: list[Path]) -> str:
    parts: list[str] = []
    for path in paths:
        stat = path.stat()
        parts.append(f"{path.name}:{int(stat.st_mtime)}:{stat.st_size}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _embed_texts(texts: list[str], model: str) -> list[list[float]]:
    body = json.dumps({"model": model, "input": texts}, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{OLLAMA_HOST}/api/embed",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=OLLAMA_TIMEOUT_SEC) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    embeddings = payload.get("embeddings") or []
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise ValueError("Invalid embedding response for rag_v2")
    return embeddings


def build_chunk_records(data_dir: Path) -> list[dict]:
    records: list[dict] = []
    for doc in load_documents(data_dir):
        for chunk in build_chunks(doc):
            records.append(_chunk_to_record(chunk))
    return records


def _chunk_to_record(chunk: RagChunk) -> dict:
    text = str(chunk.text or "").strip()
    record = asdict(chunk)
    record["content_hash"] = hashlib.sha256(
        f"{chunk.source_name}||{chunk.chunk_index}||{text}".encode("utf-8")
    ).hexdigest()
    record["search_text"] = "\n".join(
        [
            f"Source: {chunk.source_name}",
            f"DocType: {chunk.doc_type}",
            f"Section: {chunk.section}",
            text,
        ]
    ).strip()
    return record


def get_chroma_client():
    db_path = RAG_V2_INDEX_DIR / "chromadb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(db_path))


def build_index(data_dir: Path, *, output_dir: Path | None = None, force: bool = True) -> dict:
    files = iter_rag_files(data_dir)
    if not files:
        raise RuntimeError("No Rag_data files found for rag_v2")

    chunk_records = build_chunk_records(data_dir)
    if not chunk_records:
        raise RuntimeError("No chunk records generated for rag_v2")

    embed_model, embed_reason = detect_embed_model()
    generate_model, generate_reason = detect_generate_model()

    # Embed text thuần (không có prefix metadata) để vector space khớp với query embedding
    embed_texts = [item["text"] for item in chunk_records]
    embeddings: list[list[float]] = []
    for start in range(0, len(embed_texts), RAG_V2_EMBED_BATCH_SIZE):
        batch = embed_texts[start : start + RAG_V2_EMBED_BATCH_SIZE]
        embeddings.extend(_embed_texts(batch, embed_model))

    if len(embeddings) != len(chunk_records):
        raise RuntimeError("Embedding count mismatch in rag_v2 build")
        
    client = get_chroma_client()
    if force:
        try:
            client.delete_collection(name=RAG_V2_INDEX_NAME)
        except Exception:
            pass
            
    # Dùng cosine distance để dense_score = 1 - distance tính đúng
    collection = client.get_or_create_collection(
        name=RAG_V2_INDEX_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    
    ids = []
    documents = []
    metadatas = []
    normalized_embeddings = []
    
    for item, embedding in zip(chunk_records, embeddings):
        chunk_id = item["content_hash"]
        ids.append(chunk_id)
        documents.append(item["text"])
        
        # Prepare metadata, filter out empty/complex types
        meta = {k: str(v) for k, v in item.items() if k not in ["text", "search_text", "content_hash"]}
        metadatas.append(meta)
        
        normalized_embeddings.append(_normalize_vector(embedding))

    # Add to ChromaDB in batches
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        collection.add(
            ids=ids[i:i+batch_size],
            embeddings=normalized_embeddings[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size]
        )

    source_signature = _build_source_signature(files)
    
    # Save a small JSON to represent index status (for legacy compatibility)
    index_dir = output_dir or RAG_V2_INDEX_DIR
    payload = {
        "index_name": RAG_V2_INDEX_NAME,
        "source_signature": source_signature,
        "source_files": [path.name for path in files],
        "embed_model": embed_model,
        "embed_model_reason": embed_reason,
        "generate_model": generate_model,
        "generate_model_reason": generate_reason,
        "chunk_count": len(ids),
    }
    index_path = index_dir / f"{RAG_V2_INDEX_NAME}.json"
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Invalidate model cache sau rebuild để pick up model mới nếu có
    invalidate_model_cache()

    return {
        "index_path": str(index_path.resolve()),
        "index_name": RAG_V2_INDEX_NAME,
        "chunk_count": len(ids),
        "embed_model": embed_model,
        "embed_model_reason": embed_reason,
        "generate_model": generate_model,
        "generate_model_reason": generate_reason,
        "source_signature": source_signature,
    }
