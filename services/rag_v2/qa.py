from __future__ import annotations

import re
import time

from .generator import build_prompt, call_generate, iter_generate
from .intent import IntentDecision, classify_intent
from .retriever import normalize_text, retrieve


FALLBACK_ANSWER = "Tôi chưa có đủ thông tin, vui lòng liên hệ lễ tân"
FALLBACK_ANSWER_JA = "申し訳ございませんが、詳細については受付スタッフにお問い合わせください"


def _get_fallback(language: str = "vi") -> str:
    return FALLBACK_ANSWER_JA if language == "ja" else FALLBACK_ANSWER
FOLLOW_UP_MARKERS = (
    "con",
    "theo do",
    "the thi",
    "nhu the",
    "vay",
    "no",
    "he thong nay",
    "may nay",
    "cong ty nay",
    "san pham nay",
    "thiet bi nay",
    "cai nay",
)
SOLUTION_MARKERS = (
    "giải pháp",
    "giai phap",
    "dịch vụ",
    "dich vu",
    "sản phẩm",
    "san pham",
    "danh mục",
    "danh muc",
    "giải pháp công nghệ",
    "giai phap cong nghe",
)
IDENTITY_MARKERS = (
    "tên đầy đủ",
    "ten day du",
    "tên công ty",
    "ten cong ty",
    "viết tắt",
    "viet tat",
    "tên tiếng việt",
    "ten tieng viet",
)
FIELD_MARKERS = (
    "lĩnh vực",
    "linh vuc",
    "ngành nghề",
    "nganh nghe",
    "làm về",
    "lam ve",
)
OVERVIEW_MARKERS = (
    "cho toi biet ve",
    "cho tôi biết về",
    "gioi thieu",
    "giới thiệu",
    "tong quan",
    "tổng quan",
    "noi ve",
    "nói về",
)
TOKEN_ALIASES = {
    "ssg": "saomai",
    "sao": "saomai",
    "mai": "saomai",
}
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


def _postprocess_answer(answer: str, question: str) -> str:
    cleaned = " ".join((answer or "").split()).strip()
    if not cleaned:
        return FALLBACK_ANSWER
    for prefix in ("Trả lời:", "Câu trả lời:", "Answer:"):
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix) :].strip()
    normalized_question = " ".join((question or "").split()).strip()
    if normalized_question:
        lower_cleaned = cleaned.casefold()
        lower_question = normalized_question.casefold()
        prefixed_forms = (
            f"{lower_question}:",
            f"{lower_question} :",
            f"{lower_question} -",
            f"{lower_question},",
            f"{lower_question}?",
        )
        if any(lower_cleaned.startswith(prefix) for prefix in prefixed_forms):
            cleaned = cleaned[len(normalized_question) :].lstrip(" :,-?")
    return _limit_answer_length(_format_answer_for_question(cleaned or FALLBACK_ANSWER, question), question)


def _format_answer_for_question(answer: str, question: str) -> str:
    normalized_question = normalize_text(question)
    cleaned = " ".join((answer or "").split()).strip()
    if not cleaned:
        return FALLBACK_ANSWER
    if "nut" in normalized_question or "nút" in normalized_question:
        labels = [
            "Emergency STOP",
            "Reset",
            "Auto/manual",
            "Main switch",
            "Cảm biến an toàn",
            "Màn hình thao tác",
            "Start 1 Time",
            "Start Repeat",
            "Stop",
            "Origin",
            "Measure 1 Point",
            "Export Result",
            "Servo On/Off",
            "Auto",
        ]
        found_parts: list[str] = []
        for label in labels:
            marker = f"{label}:"
            if marker not in cleaned:
                continue
            tail = cleaned.split(marker, 1)[1]
            next_positions = [
                tail.find(f"{next_label}:")
                for next_label in labels
                if next_label != label and f"{next_label}:" in tail
            ]
            next_positions = [pos for pos in next_positions if pos > 0]
            detail = tail[: min(next_positions)] if next_positions else tail
            detail = detail.strip(" ;,.")
            found_parts.append(f"{label}: {detail}")
        if len(found_parts) >= 2:
            return "Các nút/chức năng chính gồm: " + "; ".join(found_parts) + "."
    return cleaned


def _limit_answer_length(answer: str, question: str) -> str:
    cleaned = " ".join((answer or "").split()).strip()
    if not cleaned:
        return FALLBACK_ANSWER
    normalized_question = normalize_text(question)
    if "nut" in normalized_question or "nút" in normalized_question:
        return cleaned
    if ";" in cleaned and len(cleaned) <= 420:
        return cleaned
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    max_sentences = 3
    if _contains_any(normalized_question, OVERVIEW_MARKERS):
        max_sentences = 4
    if len(sentences) > max_sentences:
        cleaned = " ".join(sentences[:max_sentences]).strip()
    if len(cleaned) > 420:
        cleaned = cleaned[:417].rstrip(" ,;:") + "..."
    return cleaned


def _session_turns(session_context: dict | None) -> list[dict]:
    if not isinstance(session_context, dict):
        return []
    turns = session_context.get("conversation_json") or []
    if not isinstance(turns, list):
        return []
    return [turn for turn in turns if isinstance(turn, dict)]


def _looks_like_followup(question: str) -> bool:
    normalized = normalize_text(question)
    if not normalized:
        return False
    tokens = set(normalized.split())
    for marker in FOLLOW_UP_MARKERS:
        if " " in marker:
            if marker in normalized:
                return True
            continue
        if marker in tokens:
            return True
    return False


def _build_effective_question(question: str, session_context: dict | None) -> str:
    original = (question or "").strip()
    if not original:
        return original
    turns = _session_turns(session_context)
    if not turns or not _looks_like_followup(original):
        return original
    last_turn = turns[-1]
    last_question = str(last_turn.get("question") or "").strip()
    last_answer = str(last_turn.get("answer") or "").strip()
    if not last_question:
        return original
    answer_hint = " ".join(last_answer.split()[:24]).strip()
    if answer_hint:
        return f"{original}. Ngữ cảnh trước: {last_question}. Trả lời trước: {answer_hint}"
    return f"{original}. Ngữ cảnh trước: {last_question}"


def correct_phonetic_typos(question: str) -> str:
    if not question:
        return question
    replacements = {
        "ecosip": "ecosave",
        "eco xếp": "ecosave",
        "eco save": "ecosave",
        "kiot": "kiosk",
        "isg": "ssg",
        "hoa mai": "sao mai",
    }
    corrected = question
    for typo, correction in replacements.items():
        # Dùng regex để thay thế trọn vẹn từ khóa (không phân biệt chữ hoa chữ thường)
        corrected = re.sub(rf'\b{typo}\b', correction, corrected, flags=re.IGNORECASE)
    return corrected



def _is_fallback_like(answer: str) -> bool:
    lowered = (answer or "").strip().casefold()
    return (
        lowered.startswith(FALLBACK_ANSWER.casefold())
        or lowered.startswith(FALLBACK_ANSWER_JA.casefold()[:10])
        or lowered in {"không rõ", "khong ro", ""}
    )


def _extractive_answer(question: str, items: list[dict]) -> str:
    multi_fact_answer = _build_multi_fact_answer(question, items)
    if multi_fact_answer:
        return multi_fact_answer
    best_item = _select_best_extractive_item(question, items)
    if not best_item:
        return FALLBACK_ANSWER
    best_text = " ".join(str(best_item.get("text") or "").split()).strip()
    if best_text.startswith("Câu hỏi:") and "Trả lời:" in best_text:
        return best_text.split("Trả lời:", 1)[1].strip()
    return best_text or FALLBACK_ANSWER


def _split_qa_text(text: str) -> tuple[str, str]:
    cleaned = " ".join((text or "").split()).strip()
    if cleaned.startswith("Câu hỏi:") and "Trả lời:" in cleaned:
        question_part, answer_part = cleaned.split("Trả lời:", 1)
        question_part = question_part.replace("Câu hỏi:", "", 1).strip()
        return question_part, answer_part.strip()
    return "", cleaned


def _extract_qa_pairs(text: str) -> list[tuple[str, str]]:
    cleaned = " ".join((text or "").split()).strip()
    if not cleaned.startswith("Câu hỏi:") or "Trả lời:" not in cleaned:
        return []
    parts = cleaned.split("Câu hỏi:")
    pairs: list[tuple[str, str]] = []
    for raw_part in parts:
        part = raw_part.strip()
        if not part or "Trả lời:" not in part:
            continue
        q_part, a_part = part.split("Trả lời:", 1)
        question_part = q_part.strip(" :*-")
        answer_part = a_part.strip()
        if question_part and answer_part:
            pairs.append((question_part, answer_part))
    return pairs


def _faq_question_similarity(question: str, item: dict) -> float:
    text = str(item.get("text") or "")
    qa_pairs = _extract_qa_pairs(text)
    if not qa_pairs:
        return 0.0
    user_meaningful = _meaningful_tokens(question)
    if not user_meaningful:
        return 0.0
    best_score = 0.0
    normalized_question = normalize_text(question)
    for stored_question, _ in qa_pairs:
        stored_meaningful = _meaningful_tokens(stored_question)
        if not stored_meaningful:
            continue
        overlap = len(user_meaningful & stored_meaningful)
        union = len(user_meaningful | stored_meaningful)
        score = overlap / max(1, union)
        if user_meaningful.issubset(stored_meaningful):
            score += 0.42
        elif stored_meaningful.issubset(user_meaningful):
            score += 0.28
        normalized_stored = normalize_text(stored_question)
        if _contains_any(normalized_question, SOLUTION_MARKERS) == _contains_any(normalized_stored, SOLUTION_MARKERS):
            score += 0.08
        if _contains_any(normalized_question, IDENTITY_MARKERS) == _contains_any(normalized_stored, IDENTITY_MARKERS):
            score += 0.06
        if _contains_any(normalized_question, FIELD_MARKERS) == _contains_any(normalized_stored, FIELD_MARKERS):
            score += 0.06
        best_score = max(best_score, score)
    return best_score


def _select_best_qa_pair(question: str, text: str) -> tuple[str, str] | None:
    qa_pairs = _extract_qa_pairs(text)
    if not qa_pairs:
        return None
    user_meaningful = _meaningful_tokens(question)
    normalized_question = normalize_text(question)
    best_pair: tuple[str, str] | None = None
    best_score = -1.0
    for stored_question, stored_answer in qa_pairs:
        stored_meaningful = _meaningful_tokens(stored_question)
        overlap = len(user_meaningful & stored_meaningful)
        score = float(overlap)
        if user_meaningful and stored_meaningful:
            score += overlap / max(1, len(user_meaningful | stored_meaningful))
            if user_meaningful.issubset(stored_meaningful):
                score += 1.2
            elif stored_meaningful.issubset(user_meaningful):
                score += 0.8
        normalized_stored = normalize_text(stored_question)
        if _contains_any(normalized_question, SOLUTION_MARKERS) == _contains_any(normalized_stored, SOLUTION_MARKERS):
            score += 0.2
        if _contains_any(normalized_question, IDENTITY_MARKERS) == _contains_any(normalized_stored, IDENTITY_MARKERS):
            score += 0.15
        if _contains_any(normalized_question, FIELD_MARKERS) == _contains_any(normalized_stored, FIELD_MARKERS):
            score += 0.15
        if score > best_score:
            best_score = score
            best_pair = (stored_question, stored_answer)
    return best_pair


def _looks_like_overview_question(question: str) -> bool:
    normalized_question = normalize_text(question)
    return _contains_any(normalized_question, OVERVIEW_MARKERS)


def _build_overview_answer(question: str, items: list[dict]) -> str:
    if not items:
        return FALLBACK_ANSWER
    top_texts: list[str] = []
    seen: set[str] = set()
    for item in items[:4]:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        pair = _select_best_qa_pair(question, text)
        candidate = pair[1] if pair else text
        candidate = " ".join(candidate.split()).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        top_texts.append(candidate)
    if not top_texts:
        return FALLBACK_ANSWER
    answer_parts: list[str] = []
    for candidate in top_texts:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", candidate) if part.strip()]
        if sentences:
            answer_parts.append(sentences[0])
        if len(answer_parts) >= 3:
            break
    return " ".join(answer_parts).strip() or FALLBACK_ANSWER


def _looks_like_multi_fact_question(question: str) -> bool:
    normalized_question = normalize_text(question)
    padded = f" {normalized_question} "
    return " va " in padded or " và " in padded or normalized_question.count("?") >= 2


def _build_multi_fact_answer(question: str, items: list[dict]) -> str:
    if not _looks_like_multi_fact_question(question):
        return ""
    answers: list[str] = []
    seen_answers: set[str] = set()
    for item in items[:5]:
        text = " ".join(str(item.get("text") or "").split()).strip()
        if not text:
            continue
        candidate = ""
        if text.startswith("Câu hỏi:") and "Trả lời:" in text:
            selected_pair = _select_best_qa_pair(question, text)
            if selected_pair:
                candidate = selected_pair[1].strip()
            else:
                candidate = text.split("Trả lời:", 1)[1].strip()
        else:
            candidate = text
        if not candidate:
            continue
        candidate = " ".join(candidate.split()).strip()
        if candidate in seen_answers:
            continue
        seen_answers.add(candidate)
        answers.append(candidate)
        if len(answers) >= 2:
            break
    if len(answers) < 2:
        return ""
    return " ".join(answers[:2]).strip()


def _select_best_extractive_item(question: str, items: list[dict]) -> dict | None:
    normalized_question = normalize_text(question)
    question_tokens = set(normalized_question.split())
    question_meaningful = _meaningful_tokens(question)
    best_item: dict | None = None
    best_score = -1.0
    for item in items:
        text = " ".join(str(item.get("text") or "").split()).strip()
        if not text:
            continue
        score = float(item.get("score") or 0)
        overlap = sum(1 for token in question_tokens if token and token in normalize_text(text))
        score += overlap * 0.08
        bundle_meaningful = _meaningful_tokens(text)
        if question_meaningful and bundle_meaningful:
            meaningful_overlap = len(question_meaningful & bundle_meaningful)
            score += meaningful_overlap * 0.1
            if question_meaningful.issubset(bundle_meaningful) and len(question_meaningful) >= 2:
                score += 0.24
            elif meaningful_overlap >= 2:
                score += 0.08
        if str(item.get("doc_type") or "") == "faq":
            score += 0.1
            selected_pair = _select_best_qa_pair(question, text)
            if selected_pair:
                stored_question, _ = selected_pair
                stored_meaningful = _meaningful_tokens(stored_question)
                if question_meaningful and stored_meaningful:
                    stored_overlap = len(question_meaningful & stored_meaningful)
                    score += stored_overlap * 0.12
                    if question_meaningful.issubset(stored_meaningful) and len(question_meaningful) >= 2:
                        score += 0.28
                score += _faq_question_similarity(question, item)
        if score > best_score:
            best_score = score
            best_item = item
    return best_item


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _meaningful_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in normalize_text(text).split():
        canonical = TOKEN_ALIASES.get(token, token)
        if canonical in QUESTION_STOPWORDS:
            continue
        if len(canonical) < 2:
            continue
        tokens.add(canonical)
    return tokens


def _rank_items_for_answer(question: str, items: list[dict]) -> list[dict]:
    normalized_question = normalize_text(question)
    question_meaningful = _meaningful_tokens(question)
    ranked: list[tuple[tuple[float, float, float, float], dict]] = []
    for item in items:
        score = float(item.get("score") or 0)
        keyword_score = float(item.get("keyword_score") or 0)
        lexical_score = float(item.get("lexical_score") or 0)
        faq_bonus = float(item.get("faq_match_bonus") or 0)
        doc_type = str(item.get("doc_type") or "")
        text = str(item.get("text") or "")
        bundle = normalize_text(" ".join([str(item.get("section") or ""), text, str(item.get("topic") or "")]))
        bundle_meaningful = _meaningful_tokens(bundle)
        priority = 0.0
        if doc_type in {"faq", "small_talk"}:
            priority += 0.16
        if faq_bonus > 0:
            priority += faq_bonus
        if normalized_question and text.startswith("Câu hỏi:") and "Trả lời:" in text:
            priority += 0.04
        if _contains_any(normalized_question, SOLUTION_MARKERS):
            if _contains_any(bundle, SOLUTION_MARKERS):
                priority += 0.18
            if _contains_any(bundle, IDENTITY_MARKERS):
                priority -= 0.22
        if _contains_any(normalized_question, IDENTITY_MARKERS):
            if _contains_any(bundle, IDENTITY_MARKERS):
                priority += 0.18
            if _contains_any(bundle, SOLUTION_MARKERS):
                priority -= 0.1
        if _contains_any(normalized_question, FIELD_MARKERS) and _contains_any(bundle, FIELD_MARKERS):
            priority += 0.14
        if question_meaningful and bundle_meaningful:
            overlap_count = len(question_meaningful & bundle_meaningful)
            if question_meaningful.issubset(bundle_meaningful) and len(question_meaningful) >= 2:
                priority += 0.24
            elif overlap_count >= 2:
                priority += min(0.18, overlap_count * 0.05)
        ranked.append(((score + priority, faq_bonus, keyword_score, lexical_score), item))
    ranked.sort(key=lambda row: row[0], reverse=True)
    return [item for _, item in ranked]


def _retrieval_strength(items: list[dict]) -> str:
    if not items:
        return "weak"
    top = float(items[0].get("score") or 0)
    second = float(items[1].get("score") or 0) if len(items) > 1 else 0.0
    keyword = float(items[0].get("keyword_score") or 0)
    lexical = float(items[0].get("lexical_score") or 0)
    faq_bonus = float(items[0].get("faq_match_bonus") or 0)
    same_source_top2 = len(items) > 1 and (
        str(items[0].get("source_name") or "") == str(items[1].get("source_name") or "")
    )

    if top >= 0.92:
        return "strong"
    if top >= 0.84:
        return "strong" if (top - second) >= 0.006 or same_source_top2 else "moderate"
    if top >= 0.76 and (keyword >= 0.22 or lexical >= 0.32 or faq_bonus > 0):
        return "moderate"
    if top >= 0.7 and (keyword >= 0.32 or lexical >= 0.5 or faq_bonus >= 0.18):
        return "moderate"
    return "weak"


def _should_use_extractive_fallback(items: list[dict]) -> bool:
    if not items:
        return False
    top = items[0]
    score = float(top.get("score") or 0)
    keyword = float(top.get("keyword_score") or 0)
    lexical = float(top.get("lexical_score") or 0)
    faq_bonus = float(top.get("faq_match_bonus") or 0)
    doc_type = str(top.get("doc_type") or "")
    if faq_bonus >= 0.1:
        return True
    if doc_type in {"faq", "small_talk"} and score >= 0.68:
        return True
    if doc_type in {"manual", "product_solution", "company_profile", "project_overview"} and score >= 0.74:
        return keyword >= 0.2 or lexical >= 0.28
    return False


def _should_use_direct_qa_extractive(items: list[dict]) -> bool:
    if not items:
        return False
    top = items[0]
    text = str(top.get("text") or "")
    if not (text.startswith("Câu hỏi:") and "Trả lời:" in text):
        return False
    faq_bonus = float(top.get("faq_match_bonus") or 0)
    keyword = float(top.get("keyword_score") or 0)
    lexical = float(top.get("lexical_score") or 0)
    score = float(top.get("score") or 0)
    return faq_bonus >= 0.1 or score >= 0.9 or keyword >= 0.45 or lexical >= 0.75


def _build_result(
    *,
    original_question: str,
    answer: str,
    language: str,
    channel: str,
    answer_mode: str,
    used_fallback: bool,
    matched_sources: list[str],
    matched_contexts: list[dict],
    model_name: str,
    embed_model: str,
    started_at: float,
):
    return {
        "question": original_question,
        "answer": answer,
        "language": language,
        "channel": channel,
        "answer_mode": answer_mode,
        "used_fallback": used_fallback,
        "matched_sources": [] if used_fallback else matched_sources,
        "matched_contexts": [] if used_fallback else matched_contexts,
        "model_name": model_name,
        "embed_model": embed_model,
        "response_ms": round((time.perf_counter() - started_at) * 1000),
    }


def _build_direct_result(
    *,
    original_question: str,
    answer: str,
    language: str,
    channel: str,
    answer_mode: str,
    embed_model: str,
    started_at: float,
    used_fallback: bool = False,
):
    return _build_result(
        original_question=original_question,
        answer=_postprocess_answer(answer, original_question),
        language=language,
        channel=channel,
        answer_mode=answer_mode,
        used_fallback=used_fallback,
        matched_sources=[],
        matched_contexts=[],
        model_name="",
        embed_model=embed_model,
        started_at=started_at,
    )


LEADERSHIP_ROLE_LABELS = {
    "tong_giam_doc": "Tổng Giám Đốc",
    "chu_tich": "Chủ Tịch",
    "pho_tong_giam_doc": "Phó Tổng Giám Đốc",
    "giam_doc_rd": "Giám Đốc R&D",
    "giam_doc_cong_nghe": "Giám Đốc Công Nghệ",
    "quan_ly_du_an": "Quản Lý Dự Án",
    "truong_phong_tiet_kiem_nang_luong": "Trưởng Phòng Tiết kiệm Năng Lượng",
}


def _extract_leadership_pairs(items: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    role_to_name: dict[str, str] = {}
    name_to_role: dict[str, str] = {}
    patterns = [
        ("chu_tich", r"Chủ Tịch[:\s]+([A-ZÀ-Ỵ][\wÀ-ỹ]+(?:\s+[A-ZÀ-Ỵ][\wÀ-ỹ]+){1,4})"),
        ("tong_giam_doc", r"Tổng\s*[Gg]iám\s*[Đđ]ốc[:\s]+(?:của\s+\w+\s+là\s+ông\s+)?([A-ZÀ-Ỵ][\wÀ-ỹ]+(?:\s+[A-ZÀ-Ỵ][\wÀ-ỹ]+){1,4})"),
        ("pho_tong_giam_doc", r"Phó\s*Tổng\s*[Gg]iám\s*[Đđ]ốc[:\s]+([A-ZÀ-Ỵ][\wÀ-ỹ]+(?:\s+[A-ZÀ-Ỵ][\wÀ-ỹ]+){1,4})"),
        ("giam_doc_rd", r"Giám\s*Đốc\s*R&D(?:\s*\([^)]+\))?[:\s]+(?:là\s+ông\s+)?([A-ZÀ-Ỵ][\wÀ-ỹ]+(?:\s+[A-ZÀ-Ỵ][\wÀ-ỹ]+){1,4})"),
        ("giam_doc_cong_nghe", r"Giám\s*Đốc\s*Công\s*Nghệ[:\s]+(?:là\s+ông\s+)?([A-ZÀ-Ỵ][\wÀ-ỹ]+(?:\s+[A-ZÀ-Ỵ][\wÀ-ỹ]+){1,4})"),
        ("quan_ly_du_an", r"Quản\s*lý\s*Dự\s*án[:\s]+([A-ZÀ-Ỵ][\wÀ-ỹ]+(?:\s+[A-ZÀ-Ỵ][\wÀ-ỹ]+){1,4})"),
        ("truong_phong_tiet_kiem_nang_luong", r"Trưởng\s*Phòng\s*Tiết\s*kiệm\s*Năng\s*Lượng[:\s]+([A-ZÀ-Ỵ][\wÀ-ỹ]+(?:\s+[A-ZÀ-Ỵ][\wÀ-ỹ]+){1,4})"),
    ]
    for item in items:
        text = " ".join(str(item.get("text") or "").split())
        if not text:
            continue
        for role_key, pattern in patterns:
            if role_key in role_to_name:
                continue
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            name = match.group(1).strip(" .,:;")
            if not name:
                continue
            role_to_name[role_key] = name
            name_to_role[name.casefold()] = role_key
    return role_to_name, name_to_role


def _answer_leadership_role_lookup(role_key: str, items: list[dict]) -> str:
    role_to_name, _ = _extract_leadership_pairs(items)
    name = role_to_name.get(role_key)
    label = LEADERSHIP_ROLE_LABELS.get(role_key, "Vị trí này")
    if not name:
        return FALLBACK_ANSWER
    return f"{label} của công ty là {name}."


def _answer_leadership_person_lookup(person_name: str, items: list[dict]) -> str:
    role_to_name, _ = _extract_leadership_pairs(items)
    target = (person_name or "").strip().casefold()
    if not target:
        return FALLBACK_ANSWER
    for role_key, name in role_to_name.items():
        if target in name.casefold() or name.casefold() in target:
            label = LEADERSHIP_ROLE_LABELS.get(role_key, "thành viên ban lãnh đạo")
            return f"{name} là {label} của công ty."
    return FALLBACK_ANSWER


def _extractive_result(
    *,
    original_question: str,
    language: str,
    channel: str,
    items: list[dict],
    matched_sources: list[str],
    matched_contexts: list[dict],
    embed_model: str,
    started_at: float,
    answer_mode: str,
):
    if _looks_like_overview_question(original_question):
        raw_answer = _build_overview_answer(original_question, items)
    else:
        raw_answer = _extractive_answer(original_question, items)
    answer = _postprocess_answer(raw_answer, original_question)
    used_fallback = _is_fallback_like(answer)
    return _build_result(
        original_question=original_question,
        answer=answer,
        language=language,
        channel=channel,
        answer_mode="fallback" if used_fallback else answer_mode,
        used_fallback=used_fallback,
        matched_sources=matched_sources,
        matched_contexts=matched_contexts,
        model_name="",
        embed_model=embed_model,
        started_at=started_at,
    )


def _answerability_gate(decision: IntentDecision) -> str:
    if decision.answer_policy == "unanswerable":
        return decision.direct_answer or FALLBACK_ANSWER
    return ""


def _policy_capability_meta() -> str:
    return (
        "Tôi có thể cung cấp thông tin về Sao Mai Solution Group, các giải pháp như EcoSave, Smart Box, Camera AI, "
        "dự án Bamboo Kiosk, hướng dẫn Inspection Machine và một số câu giao tiếp cơ bản."
    )


def answer_question(question: str, *, language: str = "vi", channel: str = "kiosk", session_context: dict | None = None) -> dict:
    original_question = correct_phonetic_typos((question or "").strip())
    if not original_question:
        raise ValueError("question is required")
    started_at = time.perf_counter()
    decision = classify_intent(original_question)
    retrieval_question = _build_effective_question(original_question, session_context)
    # Lấy embed_model từ index payload sau khi retrieve (tránh gọi Ollama API thừa)
    embed_model = ""

    if decision.answer_policy == "conversation_close":
        return _build_direct_result(
            original_question=original_question,
            answer=decision.direct_answer or "Vâng, nếu cần thêm thông tin tôi luôn sẵn sàng hỗ trợ.",
            language=language,
            channel=channel,
            answer_mode="conversation_close",
            embed_model=embed_model,
            started_at=started_at,
        )

    retrieval = retrieve(retrieval_question, top_k=5, filters_override=decision.filters)
    items = list(retrieval.get("items") or [])
    embed_model = str(retrieval.get("embed_model") or "")
    fallback = _get_fallback(language)

    if not items:
        return _build_result(
            original_question=original_question,
            answer=fallback,
            language=language,
            channel=channel,
            answer_mode="fallback",
            used_fallback=True,
            matched_sources=[],
            matched_contexts=[],
            model_name="",
            embed_model=embed_model,
            started_at=started_at,
        )

    matched_sources = list(dict.fromkeys(item.get("source_name") or "" for item in items if item.get("source_name")))
    matched_contexts = [
        {"source": item.get("source_name") or "", "score": item.get("score") or 0, "text": item.get("text") or ""}
        for item in items
    ]

    if _should_use_direct_qa_extractive(items):
        return _extractive_result(
            original_question=original_question,
            language=language,
            channel=channel,
            items=items,
            matched_sources=matched_sources,
            matched_contexts=matched_contexts,
            embed_model=embed_model,
            started_at=started_at,
            answer_mode="rag_v2_extractive",
        )

    prompt = build_prompt(original_question, items, language=language)
    answer_mode = "rag_v2"
    model_name = ""
    try:
        generated, model_name = call_generate(prompt)
        answer = _postprocess_answer(generated, original_question)
    except Exception:
        answer = fallback

    used_fallback = _is_fallback_like(answer)
    return _build_result(
        original_question=original_question,
        answer=answer,
        language=language,
        channel=channel,
        answer_mode="fallback" if used_fallback else answer_mode,
        used_fallback=used_fallback,
        matched_sources=matched_sources,
        matched_contexts=matched_contexts,
        model_name=model_name,
        embed_model=embed_model,
        started_at=started_at,
    )


def stream_answer_question(question: str, *, language: str = "vi", channel: str = "kiosk", session_context: dict | None = None):
    original_question = correct_phonetic_typos((question or "").strip())
    if not original_question:
        raise ValueError("question is required")
    started_at = time.perf_counter()
    decision = classify_intent(original_question)
    retrieval_question = _build_effective_question(original_question, session_context)
    embed_model = ""

    if decision.answer_policy == "conversation_close":
        result = _build_direct_result(
            original_question=original_question,
            answer=decision.direct_answer or "Vâng, nếu cần thêm thông tin tôi luôn sẵn sàng hỗ trợ.",
            language=language,
            channel=channel,
            answer_mode="conversation_close",
            embed_model=embed_model,
            started_at=started_at,
        )
        yield {"type": "answer_delta", "text": result["answer"]}
        yield {"type": "done", "item": result}
        return

    retrieval = retrieve(retrieval_question, top_k=5, filters_override=decision.filters)
    items = list(retrieval.get("items") or [])
    embed_model = str(retrieval.get("embed_model") or "")
    fallback = _get_fallback(language)

    if not items:
        result = _build_result(
            original_question=original_question,
            answer=fallback,
            language=language,
            channel=channel,
            answer_mode="fallback",
            used_fallback=True,
            matched_sources=[],
            matched_contexts=[],
            model_name="",
            embed_model=embed_model,
            started_at=started_at,
        )
        yield {"type": "answer_delta", "text": result["answer"]}
        yield {"type": "done", "item": result}
        return

    matched_sources = list(dict.fromkeys(item.get("source_name") or "" for item in items if item.get("source_name")))
    matched_contexts = [
        {"source": item.get("source_name") or "", "score": item.get("score") or 0, "text": item.get("text") or ""}
        for item in items
    ]

    if _should_use_direct_qa_extractive(items):
        result = _extractive_result(
            original_question=original_question,
            language=language,
            channel=channel,
            items=items,
            matched_sources=matched_sources,
            matched_contexts=matched_contexts,
            embed_model=embed_model,
            started_at=started_at,
            answer_mode="rag_v2_extractive",
        )
        yield {"type": "answer_delta", "text": result["answer"]}
        yield {"type": "done", "item": result}
        return

    prompt = build_prompt(original_question, items, language=language)
    answer_buffer = ""
    model_name = ""
    answer_mode = "rag_v2"

    try:
        for event in iter_generate(prompt):
            if event.get("type") == "delta":
                model_name = str(event.get("model_name") or model_name)
                delta = str(event.get("text") or "")
                answer_buffer += delta
                yield {"type": "answer_delta", "text": delta}
    except Exception:
        answer_buffer = fallback

    answer = _postprocess_answer(answer_buffer, original_question)
    used_fallback = _is_fallback_like(answer)
    result = _build_result(
        original_question=original_question,
        answer=answer,
        language=language,
        channel=channel,
        answer_mode="fallback" if used_fallback else answer_mode,
        used_fallback=used_fallback,
        matched_sources=matched_sources,
        matched_contexts=matched_contexts,
        model_name=model_name,
        embed_model=embed_model,
        started_at=started_at,
    )
    yield {"type": "done", "item": result}
