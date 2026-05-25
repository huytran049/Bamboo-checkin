from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

import numpy as np

from .indexer import RAG_V2_INDEX_DIR, RAG_V2_INDEX_NAME, _embed_texts, detect_embed_model


TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹ]+", flags=re.UNICODE)
QUESTION_STOPWORDS = {
    "la",
    "là",
    "gi",
    "gì",
    "nao",
    "nào",
    "bao",
    "nhieu",
    "nhiêu",
    "o",
    "ở",
    "dau",
    "đâu",
    "co",
    "có",
    "the",
    "thể",
    "nhung",
    "những",
    "cua",
    "của",
    "cho",
    "duoc",
    "được",
    "voi",
    "với",
    "trong",
    "tai",
    "tại",
    "mot",
    "một",
    "cac",
    "các",
    "ve",
    "về",
    "ban",
    "bạn",
    "toi",
    "tôi",
    "biet",
    "biết",
    "hay",
    "hãy",
    "xin",
    "giup",
    "giúp",
    "long",
    "lòng",
}
SOLUTION_MARKERS = (
    "giải pháp",
    "giai phap",
    "giải pháp công nghệ",
    "giai phap cong nghe",
    "dịch vụ",
    "dich vu",
    "sản phẩm",
    "san pham",
    "danh mục",
    "danh muc",
    "giải pháp số hóa",
    "giai phap so hoa",
)
IDENTITY_MARKERS = (
    "tên đầy đủ",
    "ten day du",
    "tên công ty",
    "ten cong ty",
    "tên tiếng việt",
    "ten tieng viet",
    "viết tắt",
    "viet tat",
    "gọi đầy đủ",
    "goi day du",
)
FIELD_MARKERS = (
    "lĩnh vực",
    "linh vuc",
    "ngành nghề",
    "nganh nghe",
    "làm về",
    "lam ve",
    "hoạt động trong",
    "hoat dong trong",
)
TOKEN_ALIASES = {
    "ssg": "saomai",
    "sao": "saomai",
    "mai": "saomai",
}

PRIORITY_FILTER_PATTERNS = [
    (
        {"doc_types": {"small_talk"}, "products": {"qa"}},
        ("hello", "alo", "xin chào", "xin chao", "chào", "chao", "bạn là ai", "ban la ai", "bạn tên gì", "ban ten gi", "cảm ơn", "cam on", "tạm biệt", "tam biet", "hẹn gặp lại", "hen gap lai"),
    ),
    (
        {"products": {"ecosave"}},
        ("ecosave", "tiết kiệm điện", "tiết kiệm năng lượng", "máy nén khí", "khi nen"),
    ),
    (
        {"products": {"camera_ai"}},
        ("camera ai", "machine vision", "thị giác máy", "thi giac may", "ngoại quan", "cctv"),
    ),
    (
        {"products": {"smart_box"}},
        ("smart box", "hộp thông minh", "hop thong minh", "thu thập dữ liệu", "thu thap du lieu", "traceability"),
    ),
    (
        {"products": {"inspection_machine"}, "doc_types": {"manual"}},
        ("inspection machine", "máy inspection", "may inspection", "kiểm tra kích thước", "kiem tra kich thuoc", "nút", "start", "stop", "reset"),
    ),
    (
        {"products": {"bamboo"}},
        ("bamboo", "kiosk", "check-in", "check in", "lễ tân", "le tan", "đăng ký", "dang ky", "đặt lịch", "dat lich", "dashboard"),
    ),
]

SOURCE_GROUP_PATTERNS = [
    (
        {"source_groups": {"saomai"}, "products": {"saomai", "jss"}},
        ("sao mai", "saomai", "ssg", "công ty", "cong ty", "tập đoàn", "tap doan", "jss"),
    ),
]


def normalize_text(text: str) -> str:
    lowered = (text or "").strip().casefold()
    lowered = lowered.replace("đ", "d")
    lowered = unicodedata.normalize("NFD", lowered)
    lowered = "".join(ch for ch in lowered if unicodedata.category(ch) != "Mn")
    lowered = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
    lowered = re.sub(r"\s{2,}", " ", lowered).strip()
    return lowered


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "") if len(token) >= 2]


def _canonical_tokens(text: str, *, drop_stopwords: bool = False) -> list[str]:
    tokens: list[str] = []
    for token in tokenize(normalize_text(text)):
        canonical = TOKEN_ALIASES.get(token, token)
        if drop_stopwords and canonical in QUESTION_STOPWORDS:
            continue
        tokens.append(canonical)
    return tokens


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _item_bundle(item: dict) -> str:
    return normalize_text(
        " ".join(
            [
                str(item.get("section") or ""),
                str(item.get("text") or ""),
                str(item.get("topic") or ""),
                str(item.get("product") or ""),
            ]
        )
    )


def _normalize_vector(vector) -> np.ndarray:
    arr = np.asarray(vector, dtype=np.float32).reshape(-1)
    if arr.size == 0:
        return arr
    norm = float(np.linalg.norm(arr))
    if norm <= 0:
        return arr
    return arr / norm


def _cosine_similarity(query_vec, doc_vec) -> float:
    if query_vec.size == 0 or doc_vec.size == 0 or query_vec.shape != doc_vec.shape:
        return 0.0
    return float(np.dot(query_vec, doc_vec))


def _keyword_overlap_score(question: str, item: dict) -> float:
    query_tokens = set(_canonical_tokens(question))
    if not query_tokens:
        return 0.0
    text = " ".join(
        [
            str(item.get("source_name") or ""),
            str(item.get("section") or ""),
            str(item.get("text") or ""),
            str(item.get("product") or ""),
            str(item.get("topic") or ""),
        ]
    ).lower()
    matched = sum(1 for token in query_tokens if token in text)
    return matched / max(1, len(query_tokens))


def _doc_type_bonus(question: str, item: dict) -> float:
    lowered = normalize_text(question)
    doc_type = str(item.get("doc_type") or "")
    bundle = _item_bundle(item)
    bonus = 0.0
    if any(marker in lowered for marker in ("là gì", "la gi", "là ai", "la ai", "bao nhiêu", "bao nhieu", "ở đâu", "o dau")):
        if doc_type == "faq":
            bonus += 0.18
        if doc_type == "company_profile":
            bonus += 0.12
    if _contains_any(lowered, IDENTITY_MARKERS):
        if doc_type == "faq":
            bonus += 0.18
        if doc_type == "company_profile":
            bonus += 0.08
        if _contains_any(bundle, SOLUTION_MARKERS):
            bonus -= 0.08
    if _contains_any(lowered, SOLUTION_MARKERS):
        if doc_type == "faq" and _contains_any(bundle, SOLUTION_MARKERS):
            bonus += 0.24
        if doc_type in {"product_solution", "project_overview"}:
            bonus += 0.18
        if doc_type == "company_profile" and (
            _contains_any(bundle, SOLUTION_MARKERS) or _contains_any(bundle, FIELD_MARKERS)
        ):
            bonus += 0.12
        if _contains_any(bundle, IDENTITY_MARKERS):
            bonus -= 0.22
    if _contains_any(lowered, FIELD_MARKERS):
        if doc_type == "faq" and _contains_any(bundle, FIELD_MARKERS):
            bonus += 0.2
        if doc_type == "company_profile":
            bonus += 0.14
    if any(marker in lowered for marker in ("dùng để", "dung de", "làm gì", "lam gi", "ứng dụng", "ung dung")):
        if doc_type == "product_solution":
            bonus += 0.2
    if any(marker in lowered for marker in ("nút", "hướng dẫn", "huong dan", "start", "stop", "reset", "manual")):
        if doc_type == "manual":
            bonus += 0.22
    if any(marker in lowered for marker in ("xin chào", "xin chao", "cảm ơn", "cam on", "tạm biệt", "tam biet")):
        if doc_type == "small_talk":
            bonus += 0.22
    if any(marker in lowered for marker in ("dùng để", "dung de", "làm gì", "lam gi", "bao nhiêu", "bao nhieu", "là gì", "la gi")):
        text = str(item.get("text") or "")
        if text.startswith("Câu hỏi:") and "Trả lời:" in text:
            bonus += 0.08
    return round(bonus, 6)


def _lexical_idf_score(question: str, item: dict) -> float:
    query_tokens = [token for token in tokenize(normalize_text(question)) if token not in QUESTION_STOPWORDS]
    if not query_tokens:
        return 0.0
    content_tokens = tokenize(normalize_text(str(item.get("text") or "")))
    if not content_tokens:
        return 0.0
    content_counts: dict[str, int] = {}
    for token in content_tokens:
        content_counts[token] = content_counts.get(token, 0) + 1
    score = 0.0
    doc_len = max(1, len(content_tokens))
    for token in query_tokens:
        tf = content_counts.get(token, 0)
        if tf <= 0:
            continue
        score += (1.0 + math.log(1.0 + tf)) / math.sqrt(doc_len)
    return round(score, 6)


def _faq_match_bonus(question: str, item: dict) -> float:
    text = str(item.get("text") or "")
    if not (text.startswith("Câu hỏi:") and "Trả lời:" in text):
        return 0.0
    question_part = text.split("Trả lời:", 1)[0].replace("Câu hỏi:", "", 1).strip()
    normalized_query = normalize_text(question)
    normalized_stored = normalize_text(question_part)
    if not normalized_query or not normalized_stored:
        return 0.0
    if normalized_query == normalized_stored:
        return 0.3
    query_tokens = set(_canonical_tokens(question))
    stored_tokens = set(_canonical_tokens(question_part))
    if not query_tokens or not stored_tokens:
        return 0.0
    overlap = len(query_tokens & stored_tokens) / max(1, len(query_tokens | stored_tokens))
    if overlap >= 0.82:
        return 0.18
    if overlap >= 0.68:
        return 0.1
    lowered_query = normalize_text(question)
    lowered_stored = normalize_text(question_part)
    query_meaningful = set(_canonical_tokens(question, drop_stopwords=True))
    stored_meaningful = set(_canonical_tokens(question_part, drop_stopwords=True))
    if query_meaningful and query_meaningful.issubset(stored_meaningful):
        if len(query_meaningful) >= 2:
            return 0.22
    if stored_meaningful and stored_meaningful.issubset(query_meaningful):
        if len(stored_meaningful) >= 2:
            return 0.18
    if _contains_any(lowered_query, SOLUTION_MARKERS) and _contains_any(lowered_stored, SOLUTION_MARKERS):
        if len(query_tokens & stored_tokens) >= 2:
            return 0.16
    if _contains_any(lowered_query, IDENTITY_MARKERS) and _contains_any(lowered_stored, IDENTITY_MARKERS):
        if len(query_tokens & stored_tokens) >= 2:
            return 0.14
    if _contains_any(lowered_query, FIELD_MARKERS) and _contains_any(lowered_stored, FIELD_MARKERS):
        if len(query_tokens & stored_tokens) >= 2:
            return 0.14
    return 0.0


def infer_filters(question: str) -> dict[str, set[str]]:
    lowered = normalize_text(question)
    filters = {"doc_types": set(), "products": set(), "source_groups": set()}
    for rule, patterns in PRIORITY_FILTER_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            for key, values in rule.items():
                filters[key].update(values)
            return filters
    for rule, patterns in SOURCE_GROUP_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            for key, values in rule.items():
                filters[key].update(values)
    return filters


def load_index(index_path: Path | None = None) -> dict:
    path = index_path or (RAG_V2_INDEX_DIR / f"{RAG_V2_INDEX_NAME}.json")
    if not path.exists():
        raise RuntimeError(f"rag_v2 index not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_filters(items: list[dict], filters: dict[str, set[str]]) -> list[dict]:
    doc_types = set(filters.get("doc_types") or set())
    products = set(filters.get("products") or set())
    source_groups = set(filters.get("source_groups") or set())
    if not doc_types and not products and not source_groups:
        return items
    filtered: list[dict] = []
    for item in items:
        if doc_types and str(item.get("doc_type") or "") not in doc_types:
            continue
        if products and str(item.get("product") or "") not in products:
            continue
        if source_groups and str(item.get("source_group") or "") not in source_groups:
            continue
        filtered.append(item)
    return filtered


def _merge_filters(base: dict[str, set[str]], override: dict[str, set[str]] | None) -> dict[str, set[str]]:
    merged = {
        "doc_types": set(base.get("doc_types") or set()),
        "products": set(base.get("products") or set()),
        "source_groups": set(base.get("source_groups") or set()),
    }
    if not override:
        return merged
    for key in ("doc_types", "products", "source_groups"):
        merged[key].update(set(override.get(key) or set()))
    return merged


def retrieve(question: str, *, top_k: int = 5, index_path: Path | None = None, filters_override: dict[str, set[str]] | None = None) -> dict:
    index_payload = load_index(index_path)
    chunks = list(index_payload.get("chunks") or [])
    if not chunks:
        return {"items": [], "filters": infer_filters(question), "index_name": index_payload.get("index_name") or ""}

    filters = _merge_filters(infer_filters(question), filters_override)
    filtered_chunks = _apply_filters(chunks, filters)
    working_set = filtered_chunks or chunks

    embed_model = str(index_payload.get("embed_model") or "")
    if not embed_model:
        embed_model, _ = detect_embed_model()
    query_embedding = _embed_texts([question], embed_model)[0]
    query_vec = _normalize_vector(query_embedding)

    scored: list[dict] = []
    for item in working_set:
        doc_vec = _normalize_vector(item.get("embedding") or [])
        dense_score = _cosine_similarity(query_vec, doc_vec)
        lexical_score = _lexical_idf_score(question, item)
        keyword_score = _keyword_overlap_score(question, item)
        doc_type_bonus = _doc_type_bonus(question, item)
        faq_match_bonus = _faq_match_bonus(question, item)
        final_score = dense_score + (lexical_score * 0.12) + (keyword_score * 0.28) + doc_type_bonus + faq_match_bonus
        scored.append(
            {
                "source_name": item.get("source_name") or "",
                "chunk_index": int(item.get("chunk_index") or 0),
                "doc_type": item.get("doc_type") or "",
                "chunk_type": item.get("chunk_type") or "",
                "section": item.get("section") or "",
                "text": item.get("text") or "",
                "source_group": item.get("source_group") or "",
                "product": item.get("product") or "",
                "topic": item.get("topic") or "",
                "dense_score": round(dense_score, 6),
                "lexical_score": round(lexical_score, 6),
                "keyword_score": round(keyword_score, 6),
                "doc_type_bonus": round(doc_type_bonus, 6),
                "faq_match_bonus": round(faq_match_bonus, 6),
                "score": round(final_score, 6),
            }
        )

    scored.sort(
        key=lambda row: (
            float(row.get("score") or 0),
            float(row.get("dense_score") or 0),
            float(row.get("keyword_score") or 0),
            float(row.get("lexical_score") or 0),
        ),
        reverse=True,
    )
    return {
        "index_name": index_payload.get("index_name") or "",
        "embed_model": embed_model,
        "filters": filters,
        "items": scored[: max(1, top_k)],
        "candidate_count": len(working_set),
        "filtered": bool(filtered_chunks),
    }
