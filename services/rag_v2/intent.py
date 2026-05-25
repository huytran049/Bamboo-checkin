from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata

def normalize_text(text: str) -> str:
    lowered = (text or "").strip().casefold()
    lowered = lowered.replace("đ", "d")
    lowered = unicodedata.normalize("NFD", lowered)
    lowered = "".join(ch for ch in lowered if unicodedata.category(ch) != "Mn")
    lowered = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
    lowered = re.sub(r"\s{2,}", " ", lowered).strip()
    return lowered

def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)

SMALL_TALK_MARKERS = ("xin chao", "chao", "cam on", "tam biet", "hen gap lai", "ban la ai", "ban ten gi")
CAPABILITY_MARKERS = ("cung cap thong tin gi", "cung cap nhung thong tin gi", "ban co the cung cap nhung thong tin gi", "ban biet gi", "ban co the giup gi", "ban ho tro gi")
CONVERSATION_CLOSE_MARKERS = ("thoi duoc roi", "thoi duoc", "duoc roi", "ok roi", "thoi nhe")

@dataclass
class IntentDecision:
    intent: str
    answer_policy: str = "default"
    retriever_group: str = "default"
    filters: dict[str, set[str]] = field(default_factory=lambda: {"doc_types": set(), "products": set(), "source_groups": set()})
    clarify_answer: str = ""
    direct_answer: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

def _empty_filters() -> dict[str, set[str]]:
    return {"doc_types": set(), "products": set(), "source_groups": set()}

def classify_intent(question: str) -> IntentDecision:
    normalized = normalize_text(question)
    if not normalized:
        return IntentDecision(intent="empty", answer_policy="fallback")

    if _contains_any(normalized, CONVERSATION_CLOSE_MARKERS):
        return IntentDecision(
            intent="conversation_close",
            answer_policy="conversation_close",
            direct_answer="Vâng, nếu cần thêm thông tin tôi luôn sẵn sàng hỗ trợ.",
        )

    if _contains_any(normalized, SMALL_TALK_MARKERS):
        filters = _empty_filters()
        filters["doc_types"].add("small_talk")
        return IntentDecision(intent="small_talk", answer_policy="small_talk", retriever_group="small_talk", filters=filters)

    if _contains_any(normalized, CAPABILITY_MARKERS):
        return IntentDecision(
            intent="capability_meta",
            answer_policy="capability_meta",
            retriever_group="capability_meta",
            filters=_empty_filters(),
        )

    # Let Vector DB handle everything else!
    return IntentDecision(intent="default", answer_policy="default", retriever_group="default", filters=_empty_filters())
