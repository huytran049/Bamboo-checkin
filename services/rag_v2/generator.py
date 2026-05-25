from __future__ import annotations

import json
import time
from urllib import request

from .indexer import OLLAMA_HOST, OLLAMA_TIMEOUT_SEC, detect_generate_model


def build_prompt(question: str, contexts: list[dict], language: str = "vi") -> str:
    """Xây dựng prompt từ câu hỏi và danh sách context chunks."""
    selected = contexts[:5]
    context_blocks: list[str] = []
    for idx, item in enumerate(selected, start=1):
        text = str(item.get("text") or "").strip()
        section = str(item.get("section") or "").strip()
        source = str(item.get("source_name") or "").strip()
        header = f"[{idx}] {source}" + (f" — {section}" if section else "")
        context_blocks.append(f"{header}\n{text}")
    joined_context = "\n\n---\n\n".join(context_blocks)
    if language == "vi":
        return (
            "Bạn là trợ lý Q&A cho kiosk Bamboo của SaoMai Solution Group.\n"
            "Chỉ trả lời dựa trên thông tin được cung cấp bên dưới.\n"
            "Nếu thông tin không đủ, trả lời: \"Tôi chưa có đủ thông tin, vui lòng liên hệ lễ tân\".\n"
            "Trả lời ngắn gọn, rõ ràng, tối đa 3 câu. Không bịa thêm thông tin.\n\n"
            f"THÔNG TIN:\n{joined_context}\n\n"
            f"CÂU HỎI: {question}\n\n"
            "TRẢ LỜI:"
        )
    if language == "ja":
        return (
            "あなたはSaoMai Solution Group（SSG）のBambooキオスク向けQ&Aアシスタントです。\n"
            "以下に提供された情報のみに基づいて回答してください。\n"
            "情報が不十分な場合は「申し訳ございませんが、詳細については受付スタッフにお問い合わせください」と答えてください。\n"
            "簡潔かつ明確に、最大3文で回答してください。情報を作り上げないでください。\n\n"
            f"情報:\n{joined_context}\n\n"
            f"質問: {question}\n\n"
            "回答:"
        )
    return (
        "Answer only from the supplied context. "
        "If insufficient, say you do not have enough information.\n\n"
        f"CONTEXT:\n{joined_context}\n\n"
        f"QUESTION: {question}\n\n"
        "ANSWER:"
    )


def _build_chat_body(prompt: str, model: str, stream: bool) -> bytes:
    """Tạo request body cho /api/chat với think=False để tắt thinking mode của Qwen3."""
    return json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "think": False,          # Tắt thinking mode — tăng tốc 8-10x, tránh empty response
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "repeat_penalty": 1.05,
                "num_predict": 256,
                "num_ctx": 2048,
                "num_thread": 8,
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")


def call_generate(prompt: str, model: str = "") -> tuple[str, str]:
    """Gọi LLM non-streaming, trả về (answer_text, model_name)."""
    generate_model, _ = detect_generate_model()
    chosen_model = (model or generate_model).strip() or generate_model

    body = _build_chat_body(prompt, chosen_model, stream=False)
    req = request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=OLLAMA_TIMEOUT_SEC) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    # /api/chat trả về message.content
    content = str(payload.get("message", {}).get("content") or "").strip()
    return content, chosen_model


def iter_generate(prompt: str, model: str = ""):
    """Gọi LLM streaming, yield từng delta event."""
    generate_model, _ = detect_generate_model()
    chosen_model = (model or generate_model).strip() or generate_model

    body = _build_chat_body(prompt, chosen_model, stream=True)
    req = request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started_at = time.perf_counter()
    with request.urlopen(req, timeout=OLLAMA_TIMEOUT_SEC) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            payload = json.loads(line)
            # /api/chat streaming: message.content chứa delta
            delta = str(payload.get("message", {}).get("content") or "")
            if delta:
                yield {"type": "delta", "text": delta, "model_name": chosen_model}
            if payload.get("done"):
                yield {
                    "type": "done_meta",
                    "model_name": chosen_model,
                    "response_ms": round((time.perf_counter() - started_at) * 1000),
                }
                break
