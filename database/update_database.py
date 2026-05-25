import os
import json
import time
import sqlite3
import logging
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from werkzeug.security import check_password_hash, generate_password_hash
from database.repositories.cccd_repo import (
    delete_cccd_registration as cccd_repo_delete_cccd_registration,
    delete_cccd_registrations as cccd_repo_delete_cccd_registrations,
    get_cccd_registration as cccd_repo_get_cccd_registration,
    list_cccd_registrations as cccd_repo_list_cccd_registrations,
    save_cccd_to_sqlite as cccd_repo_save_cccd_to_sqlite,
    update_cccd_registration as cccd_repo_update_cccd_registration,
)
from database.repositories.qa_history_repo import (
    create_qa_history as qa_repo_create_qa_history,
    delete_qa_history_entry as qa_repo_delete_qa_history_entry,
    get_latest_qa_session_context as qa_repo_get_latest_qa_session_context,
    list_qa_history as qa_repo_list_qa_history,
    wipe_qa_history as qa_repo_wipe_qa_history,
)

# ログの設定
logger = logging.getLogger("kiosk.db")
DB_WRITE_LOCK = threading.RLock()
SQLITE_TIMEOUT_SEC = float(os.getenv("SQLITE_TIMEOUT_SEC", "10"))
SQLITE_BUSY_TIMEOUT_MS = int(float(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "10000")))
_FACE_EMBEDDINGS_CACHE: Optional[list[dict]] = None
_FACE_EMBEDDINGS_CACHE_LOCK = threading.RLock()

_ALLOWED_SORT_COLUMNS = {
    "created_at",
    "full_name",
    "company",
    "email",
    "phone",
    "title",
    "address",
    "registration_id",
}

_REQUIRED_REGISTRATION_FIELDS = (
    "full_name",
    "company",
    "email",
    "phone",
)

BCARD_TABLE = "bcard_registrations"
CCCD_TABLE = "cccd_registrations"
APPOINTMENT_TABLE = "appointments"
QA_HISTORY_TABLE = "qa_history"
QA_RAG_CHUNKS_TABLE = "qa_rag_chunks"
QA_RAG_INDEX_TABLE = "qa_rag_index_state"
APPOINTMENT_OPEN_TIME = (os.getenv("APPOINTMENT_OPEN_TIME", "08:00") or "08:00").strip()
APPOINTMENT_CLOSE_TIME = (os.getenv("APPOINTMENT_CLOSE_TIME", "17:00") or "17:00").strip()
APPOINTMENT_SLOT_MINUTES = max(1, int((os.getenv("APPOINTMENT_SLOT_MINUTES", "10") or "10").strip() or "10"))
APPOINTMENT_MIN_DURATION_MINUTES = max(
    1,
    int((os.getenv("APPOINTMENT_MIN_DURATION_MINUTES", "10") or "10").strip() or "10"),
)
APPOINTMENT_MAX_DURATION_MINUTES = max(
    APPOINTMENT_MIN_DURATION_MINUTES,
    int((os.getenv("APPOINTMENT_MAX_DURATION_MINUTES", "180") or "180").strip() or "180"),
)
APPOINTMENT_ALLOWED_STATUS = {
    "pending",
    "confirmed",
    "cancelled",
    "done",
    "no_show",
}
APPOINTMENT_SELECT_FIELDS = """
    id, appointment_date, start_time, end_time, title, description, contact_name,
    appointment_type, appointment_reason, registration_id, person_id, meeting_id,
    source, status, assignee, created_by, updated_by, confirmed_at, confirmed_by,
    created_at, updated_at
"""

def _normalize_bcard_fields(fields: Optional[dict]) -> dict:
    src = fields or {}
    return {
        "full_name": (src.get("full_name") or src.get("name") or "").strip(),
        "email": (src.get("email") or "").strip(),
        "phone": (src.get("phone") or src.get("tel") or "").strip(),
        "title": (src.get("title") or src.get("position") or src.get("role") or "").strip(),
        "company": (src.get("company") or src.get("org") or "").strip(),
        "address": (src.get("address") or "").strip(),
    }


def _normalize_cccd_fields(fields: Optional[dict]) -> dict:
    src = fields or {}
    return {
        "id_number": (src.get("id_number") or src.get("idNumber") or "").strip(),
        "old_id": (src.get("old_id") or src.get("oldId") or "").strip(),
        "full_name": (src.get("full_name") or src.get("fullName") or "").strip(),
        "dob": (src.get("dob") or "").strip(),
        "gender": (src.get("gender") or "").strip(),
        "address": (src.get("address") or "").strip(),
        "issued": (src.get("issued") or "").strip(),
        "expiry": (src.get("expiry") or "").strip(),
    }
def get_db_path():
    """
    database フォルダ内の registrations.db への絶対パスを返します。
    """
    # このファイルは database/update_database.py にあるため、
    # .db ファイルは同じディレクトリにある必要があります。
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'registrations.db')


def get_connection(db_path=None):
    if db_path is None:
        db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=SQLITE_TIMEOUT_SEC)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

def setup_database(db_path=None):
    """
    SQLite データベースを初期化し、存在しない場合は registrations テーブルを作成します。
    """
    if db_path is None:
        db_path = get_db_path()
        
    try:
        # ディレクトリが存在することを確認
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        conn = get_connection(db_path)
        with DB_WRITE_LOCK:
            cursor = conn.cursor()
            
            # テーブルを作成
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_id TEXT UNIQUE,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                title TEXT,
                company TEXT,
                address TEXT,
                last_bcard_text TEXT,
                bcard_link TEXT,
                face_link TEXT,
                qr_link TEXT,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
            ''')
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {BCARD_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_id TEXT UNIQUE,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                title TEXT,
                company TEXT,
                address TEXT,
                last_bcard_text TEXT,
                bcard_link TEXT,
                face_link TEXT,
                qr_link TEXT,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
            ''')
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {CCCD_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_id TEXT UNIQUE,
                id_number TEXT,
                old_id TEXT,
                full_name TEXT,
                dob TEXT,
                gender TEXT,
                address TEXT,
                issued TEXT,
                expiry TEXT,
                cccd_qr_raw TEXT,
                cccd_ocr_text TEXT,
                cccd_front_link TEXT,
                cccd_back_link TEXT,
                face_link TEXT,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
            ''')
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {APPOINTMENT_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                title TEXT NOT NULL,
                description TEXT,
                contact_name TEXT,
                appointment_type TEXT,
                appointment_reason TEXT,
                registration_id TEXT,
                person_id TEXT,
                meeting_id TEXT,
                source TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                assignee TEXT,
                created_by TEXT,
                updated_by TEXT,
                confirmed_at TEXT,
                confirmed_by TEXT,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
            ''')
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {QA_HISTORY_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'vi',
                channel TEXT NOT NULL DEFAULT 'kiosk',
                answer_mode TEXT NOT NULL DEFAULT 'fallback',
                used_fallback INTEGER NOT NULL DEFAULT 0,
                model_name TEXT,
                matched_sources TEXT,
                matched_contexts TEXT,
                conversation_json TEXT,
                turn_count INTEGER NOT NULL DEFAULT 1,
                response_ms INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
            ''')
            qa_history_columns = {
                row["name"]
                for row in cursor.execute(f"PRAGMA table_info({QA_HISTORY_TABLE})").fetchall()
            }
            if "session_key" not in qa_history_columns:
                cursor.execute(f"ALTER TABLE {QA_HISTORY_TABLE} ADD COLUMN session_key TEXT")
            if "conversation_json" not in qa_history_columns:
                cursor.execute(f"ALTER TABLE {QA_HISTORY_TABLE} ADD COLUMN conversation_json TEXT")
            if "turn_count" not in qa_history_columns:
                cursor.execute(f"ALTER TABLE {QA_HISTORY_TABLE} ADD COLUMN turn_count INTEGER NOT NULL DEFAULT 1")
            if "updated_at" not in qa_history_columns:
                cursor.execute(f"ALTER TABLE {QA_HISTORY_TABLE} ADD COLUMN updated_at TEXT")
            cursor.execute(
                f"""
                UPDATE {QA_HISTORY_TABLE}
                SET updated_at = coalesce(updated_at, created_at, datetime('now', 'localtime'))
                WHERE updated_at IS NULL OR trim(updated_at) = ''
                """
            )
            cursor.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{QA_HISTORY_TABLE}_session_key
                ON {QA_HISTORY_TABLE} (session_key)
                """
            )
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {QA_RAG_CHUNKS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                index_name TEXT NOT NULL DEFAULT 'default',
                source_path TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'text',
                chunk_index INTEGER NOT NULL DEFAULT 0,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                metadata_json TEXT,
                embed_model TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
            ''')
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {QA_RAG_INDEX_TABLE} (
                name TEXT PRIMARY KEY,
                source_signature TEXT NOT NULL,
                embed_model TEXT NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            )
            ''')
            qa_rag_chunk_columns = {
                row["name"]
                for row in cursor.execute(f"PRAGMA table_info({QA_RAG_CHUNKS_TABLE})").fetchall()
            }
            if "index_name" not in qa_rag_chunk_columns:
                cursor.execute(
                    f"ALTER TABLE {QA_RAG_CHUNKS_TABLE} ADD COLUMN index_name TEXT NOT NULL DEFAULT 'default'"
                )
            cursor.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{QA_RAG_CHUNKS_TABLE}_index_embed
                ON {QA_RAG_CHUNKS_TABLE} (index_name, embed_model)
                """
            )
            cursor.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{QA_RAG_CHUNKS_TABLE}_source_chunk
                ON {QA_RAG_CHUNKS_TABLE} (source_name, chunk_index)
                """
            )
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                role TEXT NOT NULL DEFAULT 'admin',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_id TEXT UNIQUE,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id INTEGER NOT NULL,
                embedding TEXT NOT NULL,
                quality_score REAL,
                source_image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(visitor_id) REFERENCES visitors(id)
            )
            ''')            
            conn.commit()
            _ensure_default_admin(conn)
        return conn
    except Exception as e:
        print(f"Database setup error: {e}")
        return None


def _ensure_default_admin(conn):
    cursor = conn.cursor()
    row = cursor.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    if int(row["c"]) > 0:
        return

    default_username = os.getenv("ADMIN_USERNAME", "admin").strip() or "admin"
    default_password = os.getenv("ADMIN_PASSWORD", "admin123")
    default_display_name = os.getenv("ADMIN_DISPLAY_NAME", "Administrator").strip() or "Administrator"

    cursor.execute(
        """
        INSERT INTO users (username, password_hash, display_name, role, is_active)
        VALUES (?, ?, ?, 'admin', 1)
        """,
        (default_username, generate_password_hash(default_password), default_display_name),
    )
    conn.commit()
    logger.warning(
        "Default admin user was created. username=%s password=%s. Change ADMIN_PASSWORD in environment for production.",
        default_username,
        default_password,
    )


def create_user(
    username: str,
    password: str,
    *,
    display_name: Optional[str] = None,
    role: str = "admin",
    is_active: int = 1,
    db_path=None,
):
    username = (username or "").strip().lower()
    if not username:
        raise ValueError("username is required")
    if not password:
        raise ValueError("password is required")

    conn = get_connection(db_path)
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO users (username, password_hash, display_name, role, is_active)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    generate_password_hash(password),
                    (display_name or "").strip() or username,
                    (role or "admin").strip() or "admin",
                    int(is_active),
                ),
            )
            conn.commit()
            return {"id": int(cur.lastrowid), "username": username}
    finally:
        conn.close()


def get_user_by_username(username: str, db_path=None):
    username = (username or "").strip().lower()
    if not username:
        return None
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT id, username, password_hash, display_name, role, is_active, created_at, last_login
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def authenticate_user(username: str, password: str, db_path=None):
    user = get_user_by_username(username, db_path=db_path)
    if not user:
        return None
    if int(user.get("is_active") or 0) != 1:
        return None
    if not check_password_hash(user.get("password_hash", ""), password or ""):
        return None

    conn = get_connection(db_path)
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user["id"],),
            )
            conn.commit()
    finally:
        conn.close()

    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user.get("display_name") or user["username"],
        "role": user.get("role") or "admin",
    }


def _upsert_registration_row(
    cursor,
    *,
    reg_id: str,
    full_name: str = "",
    email: str = "",
    phone: str = "",
    title: str = "",
    company: str = "",
    address: str = "",
    last_bcard_text: str = "",
    bcard_link: str = "",
    face_link: str = "",
    qr_link: str = "",
):
    cursor.execute(
        f'''
        INSERT INTO {BCARD_TABLE} (
            registration_id, full_name, email, phone, title, company, address,
            last_bcard_text, bcard_link, face_link, qr_link, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
        ON CONFLICT(registration_id) DO UPDATE SET
            full_name = CASE WHEN excluded.full_name <> '' THEN excluded.full_name ELSE {BCARD_TABLE}.full_name END,
            email = CASE WHEN excluded.email <> '' THEN excluded.email ELSE {BCARD_TABLE}.email END,
            phone = CASE WHEN excluded.phone <> '' THEN excluded.phone ELSE {BCARD_TABLE}.phone END,
            title = CASE WHEN excluded.title <> '' THEN excluded.title ELSE {BCARD_TABLE}.title END,
            company = CASE WHEN excluded.company <> '' THEN excluded.company ELSE {BCARD_TABLE}.company END,
            address = CASE WHEN excluded.address <> '' THEN excluded.address ELSE {BCARD_TABLE}.address END,
            last_bcard_text = CASE WHEN excluded.last_bcard_text <> '' THEN excluded.last_bcard_text ELSE {BCARD_TABLE}.last_bcard_text END,
            bcard_link = CASE WHEN excluded.bcard_link <> '' THEN excluded.bcard_link ELSE {BCARD_TABLE}.bcard_link END,
            face_link = CASE WHEN excluded.face_link <> '' THEN excluded.face_link ELSE {BCARD_TABLE}.face_link END,
            qr_link = CASE WHEN excluded.qr_link <> '' THEN excluded.qr_link ELSE {BCARD_TABLE}.qr_link END,
            updated_at = datetime('now', 'localtime'),
            created_at = datetime('now', 'localtime')
        ''',
        (
            reg_id,
            full_name,
            email,
            phone,
            title,
            company,
            address,
            last_bcard_text,
            bcard_link,
            face_link,
            qr_link,
        ),
    )

def save_to_sqlite(reg_id, payload, data, bcard_fields, reg_folder):
    """
    単一の登録情報を SQLite データベースに保存します。
    application.py から呼び出されます。
    """
    logger.info("save_to_sqlite called for reg_id: %s", reg_id)
    conn = None
    try:
        db_path = get_db_path()
        conn = get_connection(db_path)
        
        # 画像パスを決定 (絶対パスではなく、ポータブルな URL パス)
        def pick_image_url(stem: str) -> str:
            for ext in ("jpeg", "jpg", "png", "webp"):
                p = reg_folder / f"{stem}.{ext}"
                if p.exists():
                    return f"/registrations/{reg_id}/{p.name}"
            return f"/registrations/{reg_id}/{stem}.jpeg"

        bcard_link = pick_image_url("bcard")
        face_link = pick_image_url("face")
        qr_link = str((reg_folder / 'registration_qr.png').absolute())
        
        normalized_fields = _normalize_bcard_fields(bcard_fields)
        # Safe upsert: keep existing non-empty values when new payload fields are blank.
        logger.info("DEBUG_DB: Executing safe upsert for %s", reg_id)
        with DB_WRITE_LOCK:
            cursor = conn.cursor()
            _upsert_registration_row(
                cursor,
                reg_id=reg_id,
                full_name=normalized_fields.get('full_name', ''),
                email=normalized_fields.get('email', ''),
                phone=normalized_fields.get('phone', ''),
                title=normalized_fields.get('title', ''),
                company=normalized_fields.get('company', ''),
                address=normalized_fields.get('address', ''),
                last_bcard_text=payload.get('last_bcard_text', ''),
                bcard_link=bcard_link,
                face_link=face_link,
                qr_link=qr_link,
            )
            conn.commit()
        logger.info(f"DEBUG_DB: Successfully saved {reg_id} to SQLite.")
    except Exception as db_err:
        logger.error(f"DEBUG_DB: {reg_id} の SQLite データベース更新に失敗しました: {db_err}", exc_info=True)
    finally:
        if conn is not None:
            conn.close()


def update_registration_with_ocr(reg_id: str, bcard_fields: dict, last_bcard_text: str = ""):
    """
    OCR フィールドを使用して既存の登録情報を更新します。
    'database is locked' に対する再試行ロジックが含まれています。
    """
    db_path = get_db_path()
    max_retries = 5
    retry_delay = 1.0
    
    normalized_fields = _normalize_bcard_fields(bcard_fields)
    for attempt in range(max_retries):
        conn = None
        try:
            conn = get_connection(db_path)
            with DB_WRITE_LOCK:
                cursor = conn.cursor()
                existing = cursor.execute(
                    f"""
                    SELECT full_name, email, phone, title, company, address, last_bcard_text
                    FROM {BCARD_TABLE}
                    WHERE registration_id = ?
                    """,
                    (reg_id,),
                ).fetchone()

                if not existing:
                    if attempt < max_retries - 1:
                        logger.warning(f"DEBUG_DB: 更新対象のレコード {reg_id} が見つかりません。{retry_delay}秒後に再試行します... (試行 {attempt+1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    logger.error(f"DEBUG_DB: すべての再試行後もレコード {reg_id} が見つかりませんでした。OCR 結果を更新できません。")
                    return False

                merged_fields = {
                    "full_name": normalized_fields.get("full_name") or str(existing["full_name"] or "").strip(),
                    "email": normalized_fields.get("email") or str(existing["email"] or "").strip(),
                    "phone": normalized_fields.get("phone") or str(existing["phone"] or "").strip(),
                    "title": normalized_fields.get("title") or str(existing["title"] or "").strip(),
                    "company": normalized_fields.get("company") or str(existing["company"] or "").strip(),
                    "address": normalized_fields.get("address") or str(existing["address"] or "").strip(),
                }
                merged_text = str(last_bcard_text or "").strip() or str(existing["last_bcard_text"] or "").strip()
                
                cursor.execute(f'''
                UPDATE {BCARD_TABLE} SET 
                    full_name = ?, email = ?, phone = ?, title = ?, company = ?, address = ?, 
                    last_bcard_text = ?, created_at = datetime('now', 'localtime'),
                    updated_at = datetime('now', 'localtime')
                WHERE registration_id = ?
                ''', (
                    merged_fields.get('full_name', ''),
                    merged_fields.get('email', ''),
                    merged_fields.get('phone', ''),
                    merged_fields.get('title', ''),
                    merged_fields.get('company', ''),
                    merged_fields.get('address', ''),
                    merged_text,
                    reg_id
                ))

                if cursor.rowcount == 0:
                    if attempt < max_retries - 1:
                        logger.warning(f"DEBUG_DB: 更新対象のレコード {reg_id} が見つかりません。{retry_delay}秒後に再試行します... (試行 {attempt+1}/{max_retries})")
                        time.sleep(retry_delay)
                        continue
                    logger.error(f"DEBUG_DB: すべての再試行後もレコード {reg_id} が見つかりませんでした。OCR 結果を更新できません。")
                    return False
                    
                conn.commit()
                logger.info(f"DEBUG_DB: Successfully updated OCR results for {reg_id} (Attempt {attempt+1})")
                return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                logger.warning(f"DEBUG_DB: Database locked, retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            logger.error(f"DEBUG_DB: 登録情報 {reg_id} の更新に失敗しました: {e}")
            break
        except Exception as e:
            logger.error(f"DEBUG_DB: 登録情報 {reg_id} の更新中に予期しないエラーが発生しました: {e}")
            break
        finally:
            if conn is not None:
                conn.close()
    return False


def save_to_sqlite_with_retry(reg_id, payload, data, bcard_fields, reg_folder):
    """
    再試行ロジックを使用して、単一の登録情報を SQLite データベースに保存します。
    """
    db_path = get_db_path()
    max_retries = 5
    retry_delay = 1.0
    
    normalized_fields = _normalize_bcard_fields(bcard_fields)
    for attempt in range(max_retries):
        conn = None
        try:
            conn = get_connection(db_path)
            
            # 画像パスを決定
            def pick_image_url(stem: str) -> str:
                for ext in ("jpeg", "jpg", "png", "webp"):
                    p = reg_folder / f"{stem}.{ext}"
                    if p.exists():
                        return f"/registrations/{reg_id}/{p.name}"
                return f"/registrations/{reg_id}/{stem}.jpeg"

            bcard_link = pick_image_url("bcard")
            face_link = pick_image_url("face")
            qr_link = str((reg_folder / 'registration_qr.png').absolute())
            
            with DB_WRITE_LOCK:
                cursor = conn.cursor()
                _upsert_registration_row(
                    cursor,
                    reg_id=reg_id,
                    full_name=normalized_fields.get('full_name', ''),
                    email=normalized_fields.get('email', ''),
                    phone=normalized_fields.get('phone', ''),
                    title=normalized_fields.get('title', ''),
                    company=normalized_fields.get('company', ''),
                    address=normalized_fields.get('address', ''),
                    last_bcard_text=payload.get('last_bcard_text', ''),
                    bcard_link=bcard_link,
                    face_link=face_link,
                    qr_link=qr_link,
                )
                conn.commit()
                logger.info(f"DEBUG_DB: Successfully saved {reg_id} to SQLite (Attempt {attempt+1}).")
                return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                logger.warning(f"DEBUG_DB: Database locked, retrying in {retry_delay}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(retry_delay)
                continue
            logger.error(f"DEBUG_DB: Failed to save {reg_id}: {e}")
            break
        except Exception as e:
            logger.error(f"DEBUG_DB: {reg_id} の保存中に予期しないエラーが発生しました: {e}")
            break
        finally:
            if conn is not None:
                conn.close()
    return False

def _sanitize_sort(sort_by: str, sort_dir: str) -> tuple[str, str]:
    sort_col = sort_by if sort_by in _ALLOWED_SORT_COLUMNS else "created_at"
    direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"
    return sort_col, direction


def _missing_fields_for_row(row: dict) -> list[str]:
    missing = []
    for field in _REQUIRED_REGISTRATION_FIELDS:
        if str(row.get(field) or "").strip() == "":
            missing.append(field)
    return missing


def list_registrations(
    *,
    search: str = "",
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    date_from: str = "",
    date_to: str = "",
    missing_only: bool = False,
):
    page = max(1, int(page))
    page_size = max(1, min(10000, int(page_size)))
    offset = (page - 1) * page_size
    sort_col, direction = _sanitize_sort(sort_by, sort_dir)
    kw = f"%{(search or '').strip()}%"

    date_from = (date_from or "").strip()
    date_to = (date_to or "").strip()
    where_sql = """
        WHERE (? = '' OR
            lower(registration_id) LIKE lower(?) OR
            lower(full_name) LIKE lower(?) OR
            lower(company) LIKE lower(?) OR
            lower(email) LIKE lower(?) OR
            lower(phone) LIKE lower(?) OR
            lower(title) LIKE lower(?) OR
            lower(address) LIKE lower(?) OR
            lower(last_bcard_text) LIKE lower(?))
          AND (? = '' OR date(created_at) >= date(?))
          AND (? = '' OR date(created_at) <= date(?))
          AND (? = 0 OR
            coalesce(trim(full_name), '') = '' OR
            coalesce(trim(company), '') = '' OR
            coalesce(trim(email), '') = '' OR
            coalesce(trim(phone), '') = '')
    """
    where_params = [
        search.strip(),
        kw, kw, kw, kw, kw, kw, kw, kw,
        date_from, date_from,
        date_to, date_to,
        1 if missing_only else 0,
    ]

    conn = get_connection()
    try:
        cur = conn.cursor()
        total = cur.execute(
            f"SELECT COUNT(*) AS c FROM {BCARD_TABLE} {where_sql}",
            where_params,
        ).fetchone()["c"]
        rows = cur.execute(
            f"""
            SELECT registration_id, full_name, company, email, phone, title, address, last_bcard_text, bcard_link, face_link, qr_link, created_at
            FROM {BCARD_TABLE}
            {where_sql}
            ORDER BY {sort_col} {direction}
            LIMIT ? OFFSET ?
            """,
            [*where_params, page_size, offset],
        ).fetchall()
        data = []
        for row in rows:
            item = dict(row)
            missing_fields = _missing_fields_for_row(item)
            item["missing_fields"] = missing_fields
            item["has_missing_fields"] = bool(missing_fields)
            data.append(item)
        return {
            "items": data,
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "total_pages": (int(total) + page_size - 1) // page_size,
            "sort_by": sort_col,
            "sort_dir": direction.lower(),
            "search": search.strip(),
            "missing_only": bool(missing_only),
        }
    finally:
        conn.close()


def get_registration(registration_id: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT registration_id, full_name, company, email, phone, title, address,
                   last_bcard_text, bcard_link, face_link, qr_link, created_at
            FROM bcard_registrations
            WHERE registration_id = ?
            """,
            (registration_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_registration(registration_id: str) -> bool:
    conn = get_connection()
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {BCARD_TABLE} WHERE registration_id = ?", (registration_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def delete_registrations(registration_ids: list[str]) -> int:
    ids = [str(reg_id or "").strip() for reg_id in registration_ids if str(reg_id or "").strip()]
    if not ids:
        return 0
    conn = get_connection()
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in ids)
            cur.execute(f"DELETE FROM {BCARD_TABLE} WHERE registration_id IN ({placeholders})", ids)
            conn.commit()
            return int(cur.rowcount or 0)
    finally:
        conn.close()


def update_registration(registration_id: str, updates: dict) -> bool:
    if not updates:
        return False
    allowed = {"full_name", "company", "email", "phone", "title", "address"}
    payload = {k: updates[k] for k in updates if k in allowed}
    if not payload:
        return False
    set_sql = ", ".join([f"{k} = ?" for k in payload.keys()])
    values = list(payload.values()) + [registration_id]
    conn = get_connection()
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            exists = cur.execute(
                f"SELECT 1 FROM {BCARD_TABLE} WHERE registration_id = ?",
                (registration_id,),
            ).fetchone()
            if not exists:
                return False
            cur.execute(
                f"UPDATE {BCARD_TABLE} SET {set_sql}, updated_at = datetime('now', 'localtime') WHERE registration_id = ?",
                values,
            )
            conn.commit()
            return True
    finally:
        conn.close()


def dashboard_stats():
    conn = get_connection()
    try:
        cur = conn.cursor()
        total = cur.execute(f"SELECT COUNT(*) AS c FROM {BCARD_TABLE}").fetchone()["c"]
        today = cur.execute(
            f"SELECT COUNT(*) AS c FROM {BCARD_TABLE} WHERE date(created_at) = date('now', 'localtime')"
        ).fetchone()["c"]
        with_email = cur.execute(
            f"SELECT COUNT(*) AS c FROM {BCARD_TABLE} WHERE coalesce(trim(email), '') <> ''"
        ).fetchone()["c"]
        with_phone = cur.execute(
            f"SELECT COUNT(*) AS c FROM {BCARD_TABLE} WHERE coalesce(trim(phone), '') <> ''"
        ).fetchone()["c"]
        return {
            "total": int(total),
            "today": int(today),
            "with_email": int(with_email),
            "with_phone": int(with_phone),
        }
    finally:
        conn.close()


def create_qa_history(
    *,
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
    return qa_repo_create_qa_history(
        get_connection=get_connection,
        db_write_lock=DB_WRITE_LOCK,
        table_name=QA_HISTORY_TABLE,
        session_key=session_key,
        question=question,
        answer=answer,
        language=language,
        channel=channel,
        answer_mode=answer_mode,
        used_fallback=used_fallback,
        model_name=model_name,
        matched_sources=matched_sources,
        matched_contexts=matched_contexts,
        response_ms=response_ms,
        db_path=db_path,
    )


def list_qa_history(*, limit: int = 100, search: str = "", db_path: Optional[str] = None):
    return qa_repo_list_qa_history(
        get_connection=get_connection,
        table_name=QA_HISTORY_TABLE,
        limit=limit,
        search=search,
        db_path=db_path,
    )


def get_latest_qa_session_context(session_key: str, db_path: Optional[str] = None):
    return qa_repo_get_latest_qa_session_context(
        get_connection=get_connection,
        table_name=QA_HISTORY_TABLE,
        session_key=session_key,
        db_path=db_path,
    )


def delete_qa_history_entry(history_id: int, db_path: Optional[str] = None) -> bool:
    return qa_repo_delete_qa_history_entry(
        get_connection=get_connection,
        db_write_lock=DB_WRITE_LOCK,
        table_name=QA_HISTORY_TABLE,
        history_id=history_id,
        db_path=db_path,
    )


def wipe_qa_history(db_path: Optional[str] = None) -> int:
    return qa_repo_wipe_qa_history(
        get_connection=get_connection,
        db_write_lock=DB_WRITE_LOCK,
        table_name=QA_HISTORY_TABLE,
        db_path=db_path,
    )


def replace_qa_rag_chunks(
    *,
    chunks: list[dict],
    embed_model: str,
    source_signature: str,
    index_name: str = "default",
    db_path: Optional[str] = None,
) -> int:
    conn = get_connection(db_path)
    clean_embed_model = (embed_model or "").strip()
    clean_signature = (source_signature or "").strip()
    clean_index_name = (index_name or "default").strip() or "default"
    normalized_chunks = chunks if isinstance(chunks, list) else []
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {QA_RAG_CHUNKS_TABLE} WHERE index_name = ?", (clean_index_name,))
            for item in normalized_chunks:
                embedding = np.asarray(item.get("embedding") or [], dtype=np.float32).reshape(-1)
                metadata = item.get("metadata") or {}
                cur.execute(
                    f"""
                    INSERT INTO {QA_RAG_CHUNKS_TABLE} (
                        index_name, source_path, source_name, source_type, chunk_index,
                        content, embedding, metadata_json, embed_model, content_hash, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                    """,
                    (
                        clean_index_name,
                        str(item.get("source_path") or "").strip(),
                        str(item.get("source_name") or "").strip(),
                        str(item.get("source_type") or "text").strip() or "text",
                        int(item.get("chunk_index") or 0),
                        str(item.get("content") or "").strip(),
                        json.dumps(embedding.tolist(), ensure_ascii=False),
                        json.dumps(metadata, ensure_ascii=False),
                        clean_embed_model,
                        str(item.get("content_hash") or "").strip(),
                    ),
                )
            cur.execute(
                f"""
                INSERT INTO {QA_RAG_INDEX_TABLE} (name, source_signature, embed_model, chunk_count, updated_at)
                VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
                ON CONFLICT(name) DO UPDATE SET
                    source_signature=excluded.source_signature,
                    embed_model=excluded.embed_model,
                    chunk_count=excluded.chunk_count,
                    updated_at=excluded.updated_at
                """,
                (clean_index_name, clean_signature, clean_embed_model, len(normalized_chunks)),
            )
            conn.commit()
            return len(normalized_chunks)
    finally:
        conn.close()


def get_qa_rag_index_state(index_name: str = "default", db_path: Optional[str] = None) -> Optional[dict]:
    conn = get_connection(db_path)
    clean_index_name = (index_name or "default").strip() or "default"
    try:
        cur = conn.cursor()
        row = cur.execute(
            f"""
            SELECT name, source_signature, embed_model, chunk_count, updated_at
            FROM {QA_RAG_INDEX_TABLE}
            WHERE name = ?
            """,
            (clean_index_name,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_qa_rag_chunks(
    *,
    index_name: str = "default",
    embed_model: str = "",
    db_path: Optional[str] = None,
) -> list[dict]:
    conn = get_connection(db_path)
    clean_embed_model = (embed_model or "").strip()
    clean_index_name = (index_name or "default").strip() or "default"
    try:
        cur = conn.cursor()
        if clean_embed_model:
            rows = cur.execute(
                f"""
                SELECT id, index_name, source_path, source_name, source_type, chunk_index,
                       content, embedding, metadata_json, embed_model, content_hash
                FROM {QA_RAG_CHUNKS_TABLE}
                WHERE index_name = ? AND embed_model = ?
                ORDER BY source_name ASC, chunk_index ASC, id ASC
                """,
                (clean_index_name, clean_embed_model),
            ).fetchall()
        else:
            rows = cur.execute(
                f"""
                SELECT id, index_name, source_path, source_name, source_type, chunk_index,
                       content, embedding, metadata_json, embed_model, content_hash
                FROM {QA_RAG_CHUNKS_TABLE}
                WHERE index_name = ?
                ORDER BY source_name ASC, chunk_index ASC, id ASC
                """,
                (clean_index_name,),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            try:
                item["embedding"] = np.asarray(json.loads(item.get("embedding") or "[]"), dtype=np.float32)
            except Exception:
                item["embedding"] = np.asarray([], dtype=np.float32)
            try:
                item["metadata"] = json.loads(item.get("metadata_json") or "{}")
            except Exception:
                item["metadata"] = {}
            items.append(item)
        return items
    finally:
        conn.close()


def wipe_all_registrations():
    """
    登録情報をすべて削除し、registrations/ フォルダ内のすべてのファイルを削除します。
    """
    db_path = get_db_path()
    conn = get_connection(db_path)
    try:
        with DB_WRITE_LOCK:
            cursor = conn.cursor()
            # 1. すべてのデータベースレコードを削除
            cursor.execute(f"DELETE FROM {BCARD_TABLE}")
            # オプション: autoincrement をリセット
            cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (BCARD_TABLE,))
            conn.commit()
            logger.warning("DATABASE FULL WIPE: All registration records deleted from SQLite.")
    except Exception as e:
        logger.error(f"Failed to wipe registrations table: {e}")
    finally:
        conn.close()

    # 2. すべての登録フォルダを削除
    # 登録フォルダはルートの 'registrations' フォルダにあると想定
    # application.py に基づき、Path("registrations")
    current_dir = Path(__file__).parent.absolute()
    reg_dir = current_dir.parent / "registrations"
    
    if reg_dir.exists():
        try:
            # ディレクトリ自体を削除すると権限の問題が発生する可能性があるため、子要素のみを削除
            for item in reg_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            logger.warning(f"DISK FULL WIPE: All contents of {reg_dir} deleted.")
        except Exception as e:
            logger.error(f"Failed to wipe registrations directory {reg_dir}: {e}")


def check_and_trigger_cleanup(limit=10000):
    """
    登録総数が制限を超えているか確認します。
    超えている場合は、一括削除を実行します。
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        count = cursor.execute(f"SELECT COUNT(*) AS c FROM {BCARD_TABLE}").fetchone()["c"]
        conn.close()

        if int(count) >= limit:
            logger.warning(f"Registration limit reached ({count}/{limit}). Triggering FULL WIPE.")
            wipe_all_registrations()
            return True
    except Exception as e:
        logger.error(f"Error in check_and_trigger_cleanup: {e}")
    return False


def list_recent_registrations(limit: int = 10):
    limit = max(1, min(100, int(limit)))
    conn = get_connection()
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT registration_id, full_name, company, email, created_at
            FROM bcard_registrations
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _normalize_appointment_date(value: str) -> str:
    parsed = datetime.strptime((value or "").strip(), "%Y-%m-%d")
    return parsed.strftime("%Y-%m-%d")


def _normalize_appointment_time(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    parsed = datetime.strptime(cleaned, "%H:%M")
    return parsed.strftime("%H:%M")


def _appointment_minutes(value: str) -> int:
    parsed = datetime.strptime((value or "").strip(), "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _normalize_appointment_status(value: str) -> str:
    status = (value or "").strip().lower()
    if not status:
        return "pending"
    if status not in APPOINTMENT_ALLOWED_STATUS:
        raise ValueError(f"status must be one of: {', '.join(sorted(APPOINTMENT_ALLOWED_STATUS))}")
    return status


def _validate_appointment_business_rules(
    *,
    normalized_date: str,
    normalized_start: str,
    normalized_end: str,
    clean_title: str,
    clean_description: str,
    clean_contact_name: str,
    clean_reason: str,
    clean_registration_id: str,
    clean_assignee: str,
    enforce_not_past: bool = True,
) -> None:
    now_local = datetime.now()
    today_key = now_local.strftime("%Y-%m-%d")
    if enforce_not_past and normalized_date < today_key:
        raise ValueError("Không thể đặt lịch cho ngày đã qua")
    if not normalized_start or not normalized_end:
        raise ValueError("Vui lòng chọn đầy đủ giờ bắt đầu và giờ kết thúc")
    if normalized_end <= normalized_start:
        raise ValueError("Giờ kết thúc phải lớn hơn giờ bắt đầu")
    if enforce_not_past and normalized_date == today_key:
        start_dt = datetime.strptime(f"{normalized_date} {normalized_start}", "%Y-%m-%d %H:%M")
        if start_dt <= now_local:
            raise ValueError("Không thể đặt lịch vào khung giờ đã qua")

    start_minutes = _appointment_minutes(normalized_start)
    end_minutes = _appointment_minutes(normalized_end)
    open_minutes = _appointment_minutes(APPOINTMENT_OPEN_TIME)
    close_minutes = _appointment_minutes(APPOINTMENT_CLOSE_TIME)
    if start_minutes < open_minutes or end_minutes > close_minutes:
        raise ValueError(
            f"Khung giờ đặt lịch phải trong khoảng {APPOINTMENT_OPEN_TIME}-{APPOINTMENT_CLOSE_TIME}"
        )

    if (start_minutes % APPOINTMENT_SLOT_MINUTES) != 0 or (end_minutes % APPOINTMENT_SLOT_MINUTES) != 0:
        raise ValueError(f"Giờ hẹn phải theo bước {APPOINTMENT_SLOT_MINUTES} phút")

    duration_minutes = end_minutes - start_minutes
    if duration_minutes < APPOINTMENT_MIN_DURATION_MINUTES:
        raise ValueError(f"Thời lượng cuộc hẹn tối thiểu {APPOINTMENT_MIN_DURATION_MINUTES} phút")
    if duration_minutes > APPOINTMENT_MAX_DURATION_MINUTES:
        raise ValueError(f"Thời lượng cuộc hẹn tối đa {APPOINTMENT_MAX_DURATION_MINUTES} phút")

    if not (clean_reason or clean_description):
        raise ValueError("Vui lòng nhập lý do hoặc mô tả cuộc hẹn")
    if len(clean_title) > 200:
        raise ValueError("Tiêu đề lịch hẹn quá dài (tối đa 200 ký tự)")
    if len(clean_contact_name) > 120:
        raise ValueError("Tên người liên hệ quá dài (tối đa 120 ký tự)")
    if len(clean_reason) > 500:
        raise ValueError("Nội dung lý do hẹn quá dài (tối đa 500 ký tự)")
    if len(clean_description) > 2000:
        raise ValueError("Mô tả cuộc hẹn quá dài (tối đa 2000 ký tự)")
    if len(clean_registration_id) > 120:
        raise ValueError("registration_id không hợp lệ")
    if len(clean_assignee) > 120:
        raise ValueError("Người phụ trách quá dài (tối đa 120 ký tự)")


def _ensure_columns(table_name: str, columns: dict[str, str], db_path: Optional[str] = None) -> None:
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        existing = {
            str(row["name"])
            for row in cur.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        with DB_WRITE_LOCK:
            changed = False
            for column_name, column_sql in columns.items():
                if column_name in existing:
                    continue
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}")
                changed = True
            if changed:
                conn.commit()
    finally:
        conn.close()


def _ensure_indexes(index_statements: list[str], db_path: Optional[str] = None) -> None:
    if not index_statements:
        return
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        with DB_WRITE_LOCK:
            for statement in index_statements:
                cur.execute(statement)
            conn.commit()
    finally:
        conn.close()


def _ensure_appointment_table(db_path: Optional[str] = None) -> None:
    init_conn = setup_database(db_path)
    if init_conn is not None:
        init_conn.close()
    _ensure_columns(
        APPOINTMENT_TABLE,
        {
            "appointment_type": "TEXT",
            "appointment_reason": "TEXT",
            "registration_id": "TEXT",
            "person_id": "TEXT",
            "meeting_id": "TEXT",
            "source": "TEXT",
            "status": "TEXT NOT NULL DEFAULT 'pending'",
            "assignee": "TEXT",
            "created_by": "TEXT",
            "updated_by": "TEXT",
            "confirmed_at": "TEXT",
            "confirmed_by": "TEXT",
        },
        db_path=db_path,
    )
    _ensure_indexes(
        [
            f"CREATE INDEX IF NOT EXISTS idx_{APPOINTMENT_TABLE}_date ON {APPOINTMENT_TABLE}(appointment_date)",
            f"CREATE INDEX IF NOT EXISTS idx_{APPOINTMENT_TABLE}_date_status ON {APPOINTMENT_TABLE}(appointment_date, status)",
            f"CREATE INDEX IF NOT EXISTS idx_{APPOINTMENT_TABLE}_month_date_start ON {APPOINTMENT_TABLE}(appointment_date, start_time)",
            f"CREATE INDEX IF NOT EXISTS idx_{APPOINTMENT_TABLE}_assignee ON {APPOINTMENT_TABLE}(assignee)",
            f"CREATE INDEX IF NOT EXISTS idx_{APPOINTMENT_TABLE}_registration_id ON {APPOINTMENT_TABLE}(registration_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{APPOINTMENT_TABLE}_person_id ON {APPOINTMENT_TABLE}(person_id)",
            f"CREATE INDEX IF NOT EXISTS idx_{APPOINTMENT_TABLE}_meeting_id ON {APPOINTMENT_TABLE}(meeting_id)",
        ],
        db_path=db_path,
    )


def create_appointment(
    *,
    appointment_date: str,
    title: str = "",
    start_time: str = "",
    end_time: str = "",
    description: str = "",
    contact_name: str = "",
    appointment_type: str = "",
    appointment_reason: str = "",
    registration_id: str = "",
    person_id: str = "",
    meeting_id: str = "",
    source: str = "",
    status: str = "pending",
    assignee: str = "",
    created_by: str = "",
    updated_by: str = "",
    db_path: Optional[str] = None,
):
    _ensure_appointment_table(db_path=db_path)
    normalized_date = _normalize_appointment_date(appointment_date)
    normalized_start = _normalize_appointment_time(start_time)
    normalized_end = _normalize_appointment_time(end_time)

    clean_contact_name = (contact_name or "").strip()
    clean_type = (appointment_type or "").strip()
    clean_reason = (appointment_reason or "").strip()
    clean_source = (source or "").strip()
    clean_registration_id = (registration_id or "").strip()
    clean_person_id = (person_id or "").strip()
    clean_meeting_id = (meeting_id or "").strip()
    clean_description = (description or "").strip()
    clean_status = _normalize_appointment_status(status)
    clean_assignee = (assignee or "").strip()
    clean_created_by = (created_by or "").strip()
    clean_updated_by = (updated_by or "").strip() or clean_created_by
    clean_title = (title or "").strip() or clean_contact_name or clean_reason or "Cuộc hẹn"
    if not clean_title:
        raise ValueError("title is required")
    _validate_appointment_business_rules(
        normalized_date=normalized_date,
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        clean_title=clean_title,
        clean_description=clean_description,
        clean_contact_name=clean_contact_name,
        clean_reason=clean_reason,
        clean_registration_id=clean_registration_id,
        clean_assignee=clean_assignee,
    )

    conn = get_connection(db_path)
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            conflict = cur.execute(
                f"""
                SELECT id
                FROM {APPOINTMENT_TABLE}
                WHERE appointment_date = ?
                  AND coalesce(start_time, '') <> ''
                  AND coalesce(end_time, '') <> ''
                  AND start_time < ?
                  AND end_time > ?
                LIMIT 1
                """,
                (normalized_date, normalized_end, normalized_start),
            ).fetchone()
            if conflict:
                raise ValueError("Khung giờ đã có lịch hẹn")
            cur.execute(
                f"""
                INSERT INTO {APPOINTMENT_TABLE} (
                    appointment_date, start_time, end_time, title, description, contact_name,
                    appointment_type, appointment_reason, registration_id, person_id, meeting_id,
                    source, status, assignee, created_by, updated_by, confirmed_at, confirmed_by,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                """,
                (
                    normalized_date,
                    normalized_start,
                    normalized_end,
                    clean_title,
                    clean_description,
                    clean_contact_name,
                    clean_type,
                    clean_reason,
                    clean_registration_id,
                    clean_person_id,
                    clean_meeting_id,
                    clean_source,
                    clean_status,
                    clean_assignee,
                    clean_created_by,
                    clean_updated_by,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S") if clean_status == "confirmed" else None,
                    clean_updated_by if clean_status == "confirmed" else "",
                ),
            )
            conn.commit()
            row = cur.execute(
                f"""
                SELECT {APPOINTMENT_SELECT_FIELDS}
                FROM {APPOINTMENT_TABLE}
                WHERE id = ?
                """,
                (cur.lastrowid,),
            ).fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def list_appointments_for_date(appointment_date: str, *, status: str = "", assignee: str = "", db_path: Optional[str] = None):
    _ensure_appointment_table(db_path=db_path)
    normalized_date = _normalize_appointment_date(appointment_date)
    clean_status = _normalize_appointment_status(status) if (status or "").strip() else ""
    clean_assignee = (assignee or "").strip().lower()
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        sql = f"""
            SELECT {APPOINTMENT_SELECT_FIELDS}
            FROM {APPOINTMENT_TABLE}
            WHERE appointment_date = ?
        """
        params = [normalized_date]
        if clean_status:
            sql += " AND coalesce(status, 'pending') = ?"
            params.append(clean_status)
        if clean_assignee:
            sql += " AND lower(coalesce(assignee, '')) LIKE ?"
            params.append(f"%{clean_assignee}%")
        sql += """
            ORDER BY
                CASE WHEN coalesce(start_time, '') = '' THEN 1 ELSE 0 END,
                start_time ASC,
                id ASC
        """
        rows = cur.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def list_appointments_for_month(*, year: int, month: int, status: str = "", assignee: str = "", db_path: Optional[str] = None):
    _ensure_appointment_table(db_path=db_path)
    year = int(year)
    month = int(month)
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    month_key = f"{year:04d}-{month:02d}"
    clean_status = _normalize_appointment_status(status) if (status or "").strip() else ""
    clean_assignee = (assignee or "").strip().lower()
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        sql = f"""
            SELECT {APPOINTMENT_SELECT_FIELDS}
            FROM {APPOINTMENT_TABLE}
            WHERE strftime('%Y-%m', appointment_date) = ?
        """
        params = [month_key]
        if clean_status:
            sql += " AND coalesce(status, 'pending') = ?"
            params.append(clean_status)
        if clean_assignee:
            sql += " AND lower(coalesce(assignee, '')) LIKE ?"
            params.append(f"%{clean_assignee}%")
        sql += """
            ORDER BY appointment_date ASC,
                CASE WHEN coalesce(start_time, '') = '' THEN 1 ELSE 0 END,
                start_time ASC,
                id ASC
        """
        rows = cur.execute(sql, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_appointment(appointment_id: int, updates: dict, db_path: Optional[str] = None):
    _ensure_appointment_table(db_path=db_path)
    conn = get_connection(db_path)
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            existing = cur.execute(
                f"""
                SELECT {APPOINTMENT_SELECT_FIELDS}
                FROM {APPOINTMENT_TABLE}
                WHERE id = ?
                """,
                (int(appointment_id),),
            ).fetchone()
            if not existing:
                return None
            current = dict(existing)
            next_date = _normalize_appointment_date(
                (updates.get("appointment_date") if "appointment_date" in updates else current.get("appointment_date")) or ""
            )
            next_start = _normalize_appointment_time(
                (updates.get("start_time") if "start_time" in updates else current.get("start_time")) or ""
            )
            next_end = _normalize_appointment_time(
                (updates.get("end_time") if "end_time" in updates else current.get("end_time")) or ""
            )
            next_contact_name = ((updates.get("contact_name") if "contact_name" in updates else current.get("contact_name")) or "").strip()
            next_reason = ((updates.get("appointment_reason") if "appointment_reason" in updates else current.get("appointment_reason")) or "").strip()
            next_registration_id = ((updates.get("registration_id") if "registration_id" in updates else current.get("registration_id")) or "").strip()
            next_person_id = ((updates.get("person_id") if "person_id" in updates else current.get("person_id")) or "").strip()
            next_meeting_id = ((updates.get("meeting_id") if "meeting_id" in updates else current.get("meeting_id")) or "").strip()
            next_description = ((updates.get("description") if "description" in updates else current.get("description")) or "").strip()
            next_assignee = ((updates.get("assignee") if "assignee" in updates else current.get("assignee")) or "").strip()
            next_status = _normalize_appointment_status(
                (updates.get("status") if "status" in updates else current.get("status")) or "pending"
            )
            next_title = ((updates.get("title") if "title" in updates else current.get("title")) or "").strip() or next_contact_name or next_reason or "Cuộc hẹn"
            next_type = ((updates.get("appointment_type") if "appointment_type" in updates else current.get("appointment_type")) or "").strip()
            next_source = ((updates.get("source") if "source" in updates else current.get("source")) or "").strip()
            next_updated_by = ((updates.get("updated_by") if "updated_by" in updates else current.get("updated_by")) or "").strip()
            current_confirmed_at = ((current.get("confirmed_at")) or "").strip()
            current_confirmed_by = ((current.get("confirmed_by")) or "").strip()
            next_confirmed_at = current_confirmed_at
            next_confirmed_by = current_confirmed_by
            if next_status == "confirmed" and not current_confirmed_at:
                next_confirmed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                next_confirmed_by = next_updated_by or current_confirmed_by
            elif next_status == "confirmed" and next_updated_by and not current_confirmed_by:
                next_confirmed_by = next_updated_by
            enforce_not_past = any(key in updates for key in ("appointment_date", "start_time", "end_time"))

            _validate_appointment_business_rules(
                normalized_date=next_date,
                normalized_start=next_start,
                normalized_end=next_end,
                clean_title=next_title,
                clean_description=next_description,
                clean_contact_name=next_contact_name,
                clean_reason=next_reason,
                clean_registration_id=next_registration_id,
                clean_assignee=next_assignee,
                enforce_not_past=enforce_not_past,
            )

            conflict = cur.execute(
                f"""
                SELECT id
                FROM {APPOINTMENT_TABLE}
                WHERE appointment_date = ?
                  AND coalesce(start_time, '') <> ''
                  AND coalesce(end_time, '') <> ''
                  AND start_time < ?
                  AND end_time > ?
                  AND id <> ?
                LIMIT 1
                """,
                (next_date, next_end, next_start, int(appointment_id)),
            ).fetchone()
            if conflict:
                raise ValueError("Khung giờ đã có lịch hẹn")

            cur.execute(
                f"""
                UPDATE {APPOINTMENT_TABLE}
                SET appointment_date = ?,
                    start_time = ?,
                    end_time = ?,
                    title = ?,
                    description = ?,
                    contact_name = ?,
                    appointment_type = ?,
                    appointment_reason = ?,
                    registration_id = ?,
                    person_id = ?,
                    meeting_id = ?,
                    source = ?,
                    status = ?,
                    assignee = ?,
                    updated_by = ?,
                    confirmed_at = ?,
                    confirmed_by = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (
                    next_date,
                    next_start,
                    next_end,
                    next_title,
                    next_description,
                    next_contact_name,
                    next_type,
                    next_reason,
                    next_registration_id,
                    next_person_id,
                    next_meeting_id,
                    next_source,
                    next_status,
                    next_assignee,
                    next_updated_by,
                    next_confirmed_at,
                    next_confirmed_by,
                    int(appointment_id),
                ),
            )
            conn.commit()
            row = cur.execute(
                f"""
                SELECT {APPOINTMENT_SELECT_FIELDS}
                FROM {APPOINTMENT_TABLE}
                WHERE id = ?
                """,
                (int(appointment_id),),
            ).fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def delete_appointment(appointment_id: int, db_path: Optional[str] = None) -> bool:
    _ensure_appointment_table(db_path=db_path)
    conn = get_connection(db_path)
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {APPOINTMENT_TABLE} WHERE id = ?", (int(appointment_id),))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def save_cccd_to_sqlite(
    reg_id: str,
    cccd_fields: dict,
    *,
    qr_raw: str = "",
    ocr_text: str = "",
    reg_folder: Optional[Path] = None,
    face_link: str = "",
):
    return cccd_repo_save_cccd_to_sqlite(
        reg_id,
        cccd_fields,
        normalize_fields=_normalize_cccd_fields,
        setup_database=setup_database,
        get_connection=get_connection,
        db_write_lock=DB_WRITE_LOCK,
        table_name=CCCD_TABLE,
        qr_raw=qr_raw,
        ocr_text=ocr_text,
        reg_folder=reg_folder,
        face_link=face_link,
    )


def list_cccd_registrations(
    *,
    search: str = "",
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
):
    return cccd_repo_list_cccd_registrations(
        get_connection=get_connection,
        table_name=CCCD_TABLE,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


def get_cccd_registration(registration_id: str):
    return cccd_repo_get_cccd_registration(
        get_connection=get_connection,
        table_name=CCCD_TABLE,
        registration_id=registration_id,
    )


def delete_cccd_registration(registration_id: str) -> bool:
    return cccd_repo_delete_cccd_registration(
        get_connection=get_connection,
        db_write_lock=DB_WRITE_LOCK,
        table_name=CCCD_TABLE,
        registration_id=registration_id,
    )


def delete_cccd_registrations(registration_ids: list[str]) -> int:
    return cccd_repo_delete_cccd_registrations(
        get_connection=get_connection,
        db_write_lock=DB_WRITE_LOCK,
        table_name=CCCD_TABLE,
        registration_ids=registration_ids,
    )


def update_cccd_registration(registration_id: str, updates: dict) -> bool:
    return cccd_repo_update_cccd_registration(
        get_connection=get_connection,
        db_write_lock=DB_WRITE_LOCK,
        table_name=CCCD_TABLE,
        registration_id=registration_id,
        updates=updates,
    )


def _serialize_embedding(embedding) -> str:
    vec = np.asarray(embedding, dtype=np.float32).reshape(-1)
    return json.dumps(vec.tolist(), ensure_ascii=False, separators=(",", ":"))


def _deserialize_embedding(raw: str) -> np.ndarray:
    return np.asarray(json.loads(raw), dtype=np.float32)


def _invalidate_face_embeddings_cache() -> None:
    global _FACE_EMBEDDINGS_CACHE
    with _FACE_EMBEDDINGS_CACHE_LOCK:
        _FACE_EMBEDDINGS_CACHE = None


def _touch_face_embeddings_cache_visitor(visitor_id: int) -> None:
    with _FACE_EMBEDDINGS_CACHE_LOCK:
        if _FACE_EMBEDDINGS_CACHE is None:
            return
        for item in _FACE_EMBEDDINGS_CACHE:
            if int(item.get("visitor_id") or -1) == int(visitor_id):
                item["last_seen_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def create_or_update_visitor(
    registration_id: str,
    *,
    display_name: Optional[str] = None,
    db_path=None,
):
    registration_id = (registration_id or "").strip()
    if not registration_id:
        raise ValueError("registration_id is required")

    conn = get_connection(db_path)
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            existing = cur.execute(
                """
                SELECT id, registration_id, display_name, created_at, last_seen_at
                FROM visitors
                WHERE registration_id = ?
                """,
                (registration_id,),
            ).fetchone()
            if existing:
                final_name = (display_name or existing["display_name"] or "").strip()
                cur.execute(
                    """
                    UPDATE visitors
                    SET display_name = ?, last_seen_at = datetime('now', 'localtime')
                    WHERE id = ?
                    """,
                    (final_name, existing["id"]),
                )
                conn.commit()
                row = cur.execute(
                    """
                    SELECT id, registration_id, display_name, created_at, last_seen_at
                    FROM visitors
                    WHERE id = ?
                    """,
                    (existing["id"],),
                ).fetchone()
                return dict(row)

            cur.execute(
                """
                INSERT INTO visitors (registration_id, display_name, created_at, last_seen_at)
                VALUES (?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                """,
                (registration_id, (display_name or "").strip()),
            )
            conn.commit()
            row = cur.execute(
                """
                SELECT id, registration_id, display_name, created_at, last_seen_at
                FROM visitors
                WHERE id = ?
                """,
                (cur.lastrowid,),
            ).fetchone()
            return dict(row)
    finally:
        conn.close()


def add_face_embedding(
    visitor_id: int,
    embedding,
    *,
    quality_score: Optional[float] = None,
    source_image: Optional[str] = None,
    db_path=None,
):
    conn = get_connection(db_path)
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO face_embeddings (visitor_id, embedding, quality_score, source_image)
                VALUES (?, ?, ?, ?)
                """,
                (
                    int(visitor_id),
                    _serialize_embedding(embedding),
                    quality_score,
                    (source_image or "").strip(),
                ),
            )
            conn.commit()
            row = cur.execute(
                """
                SELECT id, visitor_id, embedding, quality_score, source_image, created_at
                FROM face_embeddings
                WHERE id = ?
                """,
                (cur.lastrowid,),
            ).fetchone()
            result = dict(row)
            result["embedding"] = _deserialize_embedding(result["embedding"])
            _invalidate_face_embeddings_cache()
            return result
    finally:
        conn.close()


def create_face_profile(
    registration_id: str,
    embedding,
    *,
    quality_score: Optional[float] = None,
    source_image: Optional[str] = None,
    display_name: Optional[str] = None,
    db_path=None,
):
    visitor = create_or_update_visitor(
        registration_id,
        display_name=display_name,
        db_path=db_path,
    )
    record = add_face_embedding(
        visitor["id"],
        embedding,
        quality_score=quality_score,
        source_image=source_image,
        db_path=db_path,
    )
    return {"visitor": visitor, "embedding_record": record}


def list_face_embeddings(*, db_path=None, use_cache: bool = True):
    global _FACE_EMBEDDINGS_CACHE
    if db_path is None and use_cache:
        with _FACE_EMBEDDINGS_CACHE_LOCK:
            if _FACE_EMBEDDINGS_CACHE is not None:
                return list(_FACE_EMBEDDINGS_CACHE)

    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT
                fe.id,
                fe.visitor_id,
                fe.embedding,
                fe.quality_score,
                fe.source_image,
                fe.created_at,
                v.registration_id,
                v.display_name,
                v.last_seen_at
            FROM face_embeddings fe
            JOIN visitors v ON v.id = fe.visitor_id
            ORDER BY fe.created_at DESC
            """
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["embedding"] = _deserialize_embedding(item["embedding"])
            items.append(item)
        if db_path is None and use_cache:
            with _FACE_EMBEDDINGS_CACHE_LOCK:
                _FACE_EMBEDDINGS_CACHE = items
        return items
    finally:
        conn.close()


def mark_visitor_seen(visitor_id: int, *, db_path=None):
    conn = get_connection(db_path)
    try:
        with DB_WRITE_LOCK:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE visitors
                SET last_seen_at = datetime('now', 'localtime')
                WHERE id = ?
                """,
                (int(visitor_id),),
            )
            conn.commit()
            if db_path is None:
                _touch_face_embeddings_cache_visitor(int(visitor_id))
    finally:
        conn.close()


def get_face_db_stats(*, db_path=None):
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()
        visitor_count = cur.execute("SELECT COUNT(*) AS c FROM visitors").fetchone()["c"]
        embedding_count = cur.execute("SELECT COUNT(*) AS c FROM face_embeddings").fetchone()["c"]
        latest = cur.execute(
            """
            SELECT MAX(created_at) AS last_embedding_at
            FROM face_embeddings
            """
        ).fetchone()
        return {
            "visitors": int(visitor_count),
            "embeddings": int(embedding_count),
            "last_embedding_at": latest["last_embedding_at"],
        }
    finally:
        conn.close()
def process_registrations(base_dir, db_path):
    """
    registrations/ 内のすべてのフォルダをスキャンし、データベースを更新します。
    バッチ更新に使用されます。
    """
    conn = setup_database(db_path)
    if not conn: return
    cursor = conn.cursor()
    
    registrations_dir = Path(base_dir) / 'registrations'
    
    if not registrations_dir.exists():
        print(f"Directory {registrations_dir} does not exist.")
        return

    for folder in registrations_dir.iterdir():
        if folder.is_dir() and folder.name.startswith('REG_'):
            data_file = folder / 'data.json'
            if not data_file.exists():
                continue
                
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                bcard_fields = data.get('bcard_fields', {})
                
                with DB_WRITE_LOCK:
                    cursor.execute(f'''
                    INSERT OR REPLACE INTO {BCARD_TABLE} (
                        registration_id, full_name, email, phone, title, company, address, 
                        last_bcard_text, bcard_link, face_link, qr_link, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                    ''', (
                        folder.name,
                        _normalize_bcard_fields(bcard_fields).get('full_name', ''),
                        _normalize_bcard_fields(bcard_fields).get('email', ''),
                        _normalize_bcard_fields(bcard_fields).get('phone', ''),
                        _normalize_bcard_fields(bcard_fields).get('title', ''),
                        _normalize_bcard_fields(bcard_fields).get('company', ''),
                        _normalize_bcard_fields(bcard_fields).get('address', ''),
                        data.get('last_bcard_text', ''),
                        str((folder / 'bcard.jpeg').absolute()),
                        str((folder / 'face.jpeg').absolute()),
                        str((folder / 'registration_qr.png').absolute())
                    ))
                print(f"Processed {folder.name}")
            except Exception as e:
                print(f"Error processing {folder.name}: {e}")
                
    conn.commit()
    conn.close()
    print("Database batch update complete.")

if __name__ == "__main__":
    # 'database' フォルダ内から実行する場合、base_dir は1つ上の階層
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, os.pardir))
    DB_PATH = os.path.join(CURRENT_DIR, 'registrations.db')
    process_registrations(PARENT_DIR, DB_PATH)
