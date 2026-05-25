import json
from datetime import datetime
from typing import Optional


def create_qa_history(
    *,
    get_connection,
    db_write_lock,
    table_name: str,
    session_key: str = "",
    question: str,
    answer: str,
    language: str = "vi",
    channel: str = "kiosk",
    answer_mode: str = "fallback",
    used_fallback: bool = False,
    model_name: str = "",
    matched_sources: Optional[list[str]] = None,
    matched_contexts: Optional[list[dict]] = None,
    response_ms: int = 0,
    db_path: Optional[str] = None,
):
    conn = get_connection(db_path)
    try:
        with db_write_lock:
            cur = conn.cursor()
            clean_session_key = (session_key or "").strip()
            clean_question = (question or "").strip()
            clean_answer = (answer or "").strip()
            clean_language = (language or "vi").strip() or "vi"
            clean_channel = (channel or "kiosk").strip() or "kiosk"
            clean_answer_mode = (answer_mode or "fallback").strip() or "fallback"
            clean_model_name = (model_name or "").strip()
            clean_matched_sources = list(matched_sources or [])
            clean_matched_contexts = list(matched_contexts or [])
            clean_response_ms = max(0, int(response_ms or 0))
            turn_entry = {
                "question": clean_question,
                "answer": clean_answer,
                "answer_mode": clean_answer_mode,
                "used_fallback": bool(used_fallback),
                "model_name": clean_model_name,
                "matched_sources": clean_matched_sources,
                "response_ms": clean_response_ms,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            if clean_session_key:
                existing = cur.execute(
                    f"""
                    SELECT id, question, matched_sources, conversation_json, turn_count
                    FROM {table_name}
                    WHERE session_key = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (clean_session_key,),
                ).fetchone()
                if existing:
                    existing_item = dict(existing)
                    try:
                        conversation = json.loads(existing_item.get("conversation_json") or "[]")
                    except Exception:
                        conversation = []
                    if not isinstance(conversation, list):
                        conversation = []
                    conversation.append(turn_entry)
                    try:
                        existing_sources = json.loads(existing_item.get("matched_sources") or "[]")
                    except Exception:
                        existing_sources = []
                    merged_sources = list(dict.fromkeys([*(existing_sources or []), *clean_matched_sources]))
                    turn_count = max(1, len(conversation))
                    cur.execute(
                        f"""
                        UPDATE {table_name}
                        SET answer = ?,
                            language = ?,
                            channel = ?,
                            answer_mode = ?,
                            used_fallback = ?,
                            model_name = ?,
                            matched_sources = ?,
                            matched_contexts = ?,
                            conversation_json = ?,
                            turn_count = ?,
                            response_ms = ?,
                            updated_at = datetime('now', 'localtime')
                        WHERE id = ?
                        """,
                        (
                            clean_answer,
                            clean_language,
                            clean_channel,
                            clean_answer_mode,
                            1 if used_fallback else 0,
                            clean_model_name,
                            json.dumps(merged_sources, ensure_ascii=False),
                            json.dumps(clean_matched_contexts, ensure_ascii=False),
                            json.dumps(conversation, ensure_ascii=False),
                            turn_count,
                            clean_response_ms,
                            int(existing_item["id"]),
                        ),
                    )
                    conn.commit()
                    return int(existing_item["id"])

            cur.execute(
                f"""
                INSERT INTO {table_name} (
                    session_key, question, answer, language, channel, answer_mode, used_fallback,
                    model_name, matched_sources, matched_contexts, conversation_json, turn_count, response_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_session_key or None,
                    clean_question,
                    clean_answer,
                    clean_language,
                    clean_channel,
                    clean_answer_mode,
                    1 if used_fallback else 0,
                    clean_model_name,
                    json.dumps(clean_matched_sources, ensure_ascii=False),
                    json.dumps(clean_matched_contexts, ensure_ascii=False),
                    json.dumps([turn_entry], ensure_ascii=False),
                    1,
                    clean_response_ms,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
    finally:
        conn.close()


def list_qa_history(
    *,
    get_connection,
    table_name: str,
    limit: int = 100,
    search: str = "",
    db_path: Optional[str] = None,
):
    limit = max(1, min(500, int(limit or 100)))
    kw = f"%{(search or '').strip()}%"
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        rows = cur.execute(
            f"""
            SELECT id, session_key, question, answer, language, channel, answer_mode, used_fallback,
                   model_name, matched_sources, matched_contexts, conversation_json, turn_count,
                   response_ms, created_at, updated_at
            FROM {table_name}
            WHERE (? = '' OR
                   lower(question) LIKE lower(?) OR
                   lower(answer) LIKE lower(?) OR
                   lower(channel) LIKE lower(?) OR
                   lower(model_name) LIKE lower(?) OR
                   lower(coalesce(conversation_json, '')) LIKE lower(?))
            ORDER BY coalesce(updated_at, created_at) DESC, id DESC
            LIMIT ?
            """,
            [search.strip(), kw, kw, kw, kw, kw, limit],
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            for key in ("matched_sources", "matched_contexts", "conversation_json"):
                raw = item.get(key) or ""
                try:
                    item[key] = json.loads(raw) if raw else []
                except Exception:
                    item[key] = []
            item["used_fallback"] = bool(item.get("used_fallback"))
            if not item["conversation_json"]:
                item["conversation_json"] = [
                    {
                        "question": item.get("question") or "",
                        "answer": item.get("answer") or "",
                        "answer_mode": item.get("answer_mode") or "",
                        "used_fallback": bool(item.get("used_fallback")),
                        "model_name": item.get("model_name") or "",
                        "matched_sources": item.get("matched_sources") or [],
                        "response_ms": int(item.get("response_ms") or 0),
                        "created_at": item.get("created_at") or "",
                    }
                ]
            item["turn_count"] = max(1, int(item.get("turn_count") or len(item["conversation_json"]) or 1))
            items.append(item)
        return items
    finally:
        conn.close()


def get_latest_qa_session_context(
    *,
    get_connection,
    table_name: str,
    session_key: str,
    db_path: Optional[str] = None,
):
    clean_session_key = (session_key or "").strip()
    if not clean_session_key:
        return None
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        row = cur.execute(
            f"""
            SELECT id, session_key, question, answer, answer_mode, model_name,
                   matched_sources, matched_contexts, conversation_json,
                   created_at, updated_at
            FROM {table_name}
            WHERE session_key = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (clean_session_key,),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        for key in ("matched_sources", "matched_contexts", "conversation_json"):
            raw = item.get(key) or ""
            try:
                item[key] = json.loads(raw) if raw else []
            except Exception:
                item[key] = []
        if not item["conversation_json"]:
            item["conversation_json"] = [
                {
                    "question": item.get("question") or "",
                    "answer": item.get("answer") or "",
                    "answer_mode": item.get("answer_mode") or "",
                    "model_name": item.get("model_name") or "",
                    "matched_sources": item.get("matched_sources") or [],
                    "created_at": item.get("updated_at") or item.get("created_at") or "",
                }
            ]
        return item
    finally:
        conn.close()


def delete_qa_history_entry(
    *,
    get_connection,
    db_write_lock,
    table_name: str,
    history_id: int,
    db_path: Optional[str] = None,
) -> bool:
    record_id = int(history_id or 0)
    if record_id <= 0:
        return False
    conn = get_connection(db_path)
    try:
        with db_write_lock:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {table_name} WHERE id = ?", (record_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def wipe_qa_history(
    *,
    get_connection,
    db_write_lock,
    table_name: str,
    db_path: Optional[str] = None,
) -> int:
    conn = get_connection(db_path)
    try:
        with db_write_lock:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) AS total FROM {table_name}")
            row = cur.fetchone()
            total = int(row["total"] or 0) if row else 0
            cur.execute(f"DELETE FROM {table_name}")
            conn.commit()
            return total
    finally:
        conn.close()
