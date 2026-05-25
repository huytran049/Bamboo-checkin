"""Public and dashboard QA routes."""
from io import BytesIO
import json

from flask import Blueprint, Response, jsonify, request, send_file, stream_with_context

from app_config import logger
from database.update_database import (
    create_qa_history,
    get_latest_qa_session_context,
    list_qa_history,
    delete_qa_history_entry,
    wipe_qa_history,
)
from routes.helpers import login_required
from services.rag_v2.qa import answer_question as answer_question_v2
from services.rag_v2.qa import stream_answer_question as stream_answer_question_v2
from services.rag_v2.service import (
    get_index_status as get_rag_v2_index_status,
    get_sample_questions,
    rebuild_index as rebuild_rag_v2_index,
)
from services.qa_tts_service import get_qa_tts_mime_type, get_qa_tts_status, synthesize_answer_audio_bytes

bp = Blueprint("qa", __name__)


def _dispatch_answer(question: str, *, language: str, channel: str, session_context: dict | None = None) -> dict:
    return answer_question_v2(question, language=language, channel=channel, session_context=session_context)


def _dispatch_stream_answer(question: str, *, language: str, channel: str, session_context: dict | None = None):
    yield from stream_answer_question_v2(question, language=language, channel=channel, session_context=session_context)


@bp.get("/api/qa/suggestions")
def api_qa_suggestions():
    try:
        return jsonify({"ok": True, "items": get_sample_questions()})
    except Exception as exc:
        logger.exception("api_qa_suggestions error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {exc}"}), 500


@bp.post("/api/qa/ask")
def api_qa_ask():
    js = request.get_json(silent=True) or {}
    question = (js.get("question") or "").strip()
    language = (js.get("language") or "vi").strip() or "vi"
    channel = (js.get("channel") or "kiosk").strip() or "kiosk"
    session_key = (js.get("session_key") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Câu hỏi không được để trống"}), 400

    try:
        session_context = get_latest_qa_session_context(session_key) if session_key else None
        result = _dispatch_answer(question, language=language, channel=channel, session_context=session_context)
        create_qa_history(
            session_key=session_key,
            question=result["question"],
            answer=result["answer"],
            language=result["language"],
            channel=result["channel"],
            answer_mode=result["answer_mode"],
            used_fallback=result["used_fallback"],
            model_name=result["model_name"],
            matched_sources=result["matched_sources"],
            matched_contexts=result["matched_contexts"],
            response_ms=result["response_ms"],
        )
        return jsonify({"ok": True, "item": result})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("api_qa_ask error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {exc}"}), 500


@bp.post("/api/qa/ask-stream")
def api_qa_ask_stream():
    js = request.get_json(silent=True) or {}
    question = (js.get("question") or "").strip()
    language = (js.get("language") or "vi").strip() or "vi"
    channel = (js.get("channel") or "kiosk").strip() or "kiosk"
    session_key = (js.get("session_key") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Câu hỏi không được để trống"}), 400

    def generate():
        try:
            session_context = get_latest_qa_session_context(session_key) if session_key else None
            for event in _dispatch_stream_answer(question, language=language, channel=channel, session_context=session_context):
                if event.get("type") == "done" and event.get("item"):
                    item = event["item"]
                    create_qa_history(
                        session_key=session_key,
                        question=item["question"],
                        answer=item["answer"],
                        language=item["language"],
                        channel=item["channel"],
                        answer_mode=item["answer_mode"],
                        used_fallback=item["used_fallback"],
                        model_name=item["model_name"],
                        matched_sources=item["matched_sources"],
                        matched_contexts=item["matched_contexts"],
                        response_ms=item["response_ms"],
                    )
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except ValueError as exc:
            yield json.dumps({"type": "error", "error": str(exc)}, ensure_ascii=False) + "\n"
        except Exception as exc:
            logger.exception("api_qa_ask_stream error")
            yield json.dumps({"type": "error", "error": f"Lỗi máy chủ: {exc}"}, ensure_ascii=False) + "\n"

    return Response(stream_with_context(generate()), mimetype="application/x-ndjson")


@bp.post("/api/qa/tts")
def api_qa_tts():
    js = request.get_json(silent=True) or {}
    text = (js.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Nội dung voice không được để trống"}), 400

    try:
        payload = synthesize_answer_audio_bytes(text)
        if not payload:
            raise RuntimeError("Không tạo được audio từ nội dung trả lời")
        mime_type = get_qa_tts_mime_type()
        file_name = "qa-answer.mp3" if mime_type == "audio/mpeg" else "qa-answer.wav"
        return send_file(
            BytesIO(payload),
            mimetype=mime_type,
            as_attachment=False,
            download_name=file_name,
            max_age=0,
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("api_qa_tts error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {exc}"}), 500


@bp.get("/api/qa/tts-status")
def api_qa_tts_status():
    try:
        return jsonify({"ok": True, "item": get_qa_tts_status()})
    except Exception as exc:
        logger.exception("api_qa_tts_status error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {exc}"}), 500


@bp.get("/api/dashboard/qa/history")
@login_required
def api_dashboard_qa_history():
    search = (request.args.get("search") or "").strip()
    limit = request.args.get("limit", default=100, type=int)
    try:
        items = list_qa_history(limit=limit, search=search)
        return jsonify({"ok": True, "items": items})
    except Exception as exc:
        logger.exception("api_dashboard_qa_history error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {exc}"}), 500


@bp.get("/api/dashboard/qa/rag-status")
@login_required
def api_dashboard_qa_rag_status():
    try:
        return jsonify(
            {
                "ok": True,
                "item": get_rag_v2_index_status(),
                "active_engine": "rag_v2",
            }
        )
    except Exception as exc:
        logger.exception("api_dashboard_qa_rag_status error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {exc}"}), 500


@bp.post("/api/dashboard/qa/rag-rebuild")
@login_required
def api_dashboard_qa_rag_rebuild():
    force = bool((request.get_json(silent=True) or {}).get("force", True))
    try:
        item = rebuild_rag_v2_index(force=force)
        status = get_rag_v2_index_status()
        return jsonify({"ok": True, "item": item, "status": status})
    except Exception as exc:
        logger.exception("api_dashboard_qa_rag_rebuild error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {exc}"}), 500


@bp.delete("/api/dashboard/qa/history")
@login_required
def api_dashboard_qa_history_wipe():
    try:
        deleted_count = wipe_qa_history()
        return jsonify({"ok": True, "deleted_count": deleted_count})
    except Exception as exc:
        logger.exception("api_dashboard_qa_history_wipe error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {exc}"}), 500


@bp.delete("/api/dashboard/qa/history/<int:history_id>")
@login_required
def api_dashboard_qa_history_delete(history_id):
    try:
        deleted = delete_qa_history_entry(history_id)
        if not deleted:
            return jsonify({"ok": False, "error": "Không tìm thấy lịch sử chat"}), 404
        return jsonify({"ok": True, "deleted": history_id})
    except Exception as exc:
        logger.exception("api_dashboard_qa_history_delete error")
        return jsonify({"ok": False, "error": f"Lỗi máy chủ: {exc}"}), 500
