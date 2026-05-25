from pathlib import Path
from typing import Optional


def save_cccd_to_sqlite(
    reg_id: str,
    cccd_fields: dict,
    *,
    normalize_fields,
    setup_database,
    get_connection,
    db_write_lock,
    table_name: str,
    qr_raw: str = "",
    ocr_text: str = "",
    reg_folder: Optional[Path] = None,
    face_link: str = "",
):
    normalized = normalize_fields(cccd_fields)
    reg_folder = reg_folder or (Path.cwd() / "registrations" / reg_id)
    init_conn = setup_database()
    if init_conn is not None:
        init_conn.close()

    def pick_image_url(stem: str) -> str:
        for ext in ("jpeg", "jpg", "png", "webp"):
            p = reg_folder / f"{stem}.{ext}"
            if p.exists():
                return f"/registrations/{reg_id}/{p.name}"
        return ""

    conn = get_connection()
    try:
        with db_write_lock:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO {table_name} (
                    registration_id, id_number, old_id, full_name, dob, gender, address,
                    issued, expiry, cccd_qr_raw, cccd_ocr_text, cccd_front_link,
                    cccd_back_link, face_link, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))
                ON CONFLICT(registration_id) DO UPDATE SET
                    id_number = CASE WHEN excluded.id_number <> '' THEN excluded.id_number ELSE {table_name}.id_number END,
                    old_id = CASE WHEN excluded.old_id <> '' THEN excluded.old_id ELSE {table_name}.old_id END,
                    full_name = CASE WHEN excluded.full_name <> '' THEN excluded.full_name ELSE {table_name}.full_name END,
                    dob = CASE WHEN excluded.dob <> '' THEN excluded.dob ELSE {table_name}.dob END,
                    gender = CASE WHEN excluded.gender <> '' THEN excluded.gender ELSE {table_name}.gender END,
                    address = CASE WHEN excluded.address <> '' THEN excluded.address ELSE {table_name}.address END,
                    issued = CASE WHEN excluded.issued <> '' THEN excluded.issued ELSE {table_name}.issued END,
                    expiry = CASE WHEN excluded.expiry <> '' THEN excluded.expiry ELSE {table_name}.expiry END,
                    cccd_qr_raw = CASE WHEN excluded.cccd_qr_raw <> '' THEN excluded.cccd_qr_raw ELSE {table_name}.cccd_qr_raw END,
                    cccd_ocr_text = CASE WHEN excluded.cccd_ocr_text <> '' THEN excluded.cccd_ocr_text ELSE {table_name}.cccd_ocr_text END,
                    cccd_front_link = CASE WHEN excluded.cccd_front_link <> '' THEN excluded.cccd_front_link ELSE {table_name}.cccd_front_link END,
                    cccd_back_link = CASE WHEN excluded.cccd_back_link <> '' THEN excluded.cccd_back_link ELSE {table_name}.cccd_back_link END,
                    face_link = CASE WHEN excluded.face_link <> '' THEN excluded.face_link ELSE {table_name}.face_link END,
                    updated_at = datetime('now', 'localtime')
                """,
                (
                    reg_id,
                    normalized["id_number"],
                    normalized["old_id"],
                    normalized["full_name"],
                    normalized["dob"],
                    normalized["gender"],
                    normalized["address"],
                    normalized["issued"],
                    normalized["expiry"],
                    (qr_raw or "").strip(),
                    (ocr_text or "").strip(),
                    pick_image_url("cccd_front"),
                    pick_image_url("cccd_back"),
                    (face_link or "").strip() or pick_image_url("face"),
                ),
            )
            conn.commit()
        return True
    finally:
        conn.close()


def list_cccd_registrations(
    *,
    get_connection,
    table_name: str,
    search: str = "",
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
):
    page = max(1, int(page))
    page_size = max(1, min(10000, int(page_size)))
    offset = (page - 1) * page_size
    allowed = {"created_at", "full_name", "id_number", "dob", "gender", "registration_id"}
    sort_col = sort_by if sort_by in allowed else "created_at"
    direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"
    kw = f"%{(search or '').strip()}%"
    where_sql = """
        WHERE (? = '' OR
            lower(registration_id) LIKE lower(?) OR
            lower(full_name) LIKE lower(?) OR
            lower(id_number) LIKE lower(?) OR
            lower(address) LIKE lower(?) OR
            lower(cccd_qr_raw) LIKE lower(?) OR
            lower(cccd_ocr_text) LIKE lower(?))
    """
    params = [search.strip(), kw, kw, kw, kw, kw, kw]
    conn = get_connection()
    try:
        cur = conn.cursor()
        total = cur.execute(
            f"SELECT COUNT(*) AS c FROM {table_name} {where_sql}",
            params,
        ).fetchone()["c"]
        rows = cur.execute(
            f"""
            SELECT registration_id, id_number, old_id, full_name, dob, gender, address,
                   issued, expiry, cccd_qr_raw, cccd_ocr_text, cccd_front_link,
                   cccd_back_link, face_link, created_at, updated_at
            FROM {table_name}
            {where_sql}
            ORDER BY {sort_col} {direction}
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
        return {
            "items": [dict(r) for r in rows],
            "page": page,
            "page_size": page_size,
            "total": int(total),
            "total_pages": (int(total) + page_size - 1) // page_size,
            "sort_by": sort_col,
            "sort_dir": direction.lower(),
            "search": search.strip(),
        }
    finally:
        conn.close()


def get_cccd_registration(*, get_connection, table_name: str, registration_id: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        row = cur.execute(
            f"""
            SELECT registration_id, id_number, old_id, full_name, dob, gender, address,
                   issued, expiry, cccd_qr_raw, cccd_ocr_text, cccd_front_link,
                   cccd_back_link, face_link, created_at, updated_at
            FROM {table_name}
            WHERE registration_id = ?
            """,
            (registration_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_cccd_registration(*, get_connection, db_write_lock, table_name: str, registration_id: str) -> bool:
    conn = get_connection()
    try:
        with db_write_lock:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {table_name} WHERE registration_id = ?", (registration_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def delete_cccd_registrations(*, get_connection, db_write_lock, table_name: str, registration_ids: list[str]) -> int:
    ids = [str(reg_id or "").strip() for reg_id in registration_ids if str(reg_id or "").strip()]
    if not ids:
        return 0
    conn = get_connection()
    try:
        with db_write_lock:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in ids)
            cur.execute(f"DELETE FROM {table_name} WHERE registration_id IN ({placeholders})", ids)
            conn.commit()
            return int(cur.rowcount or 0)
    finally:
        conn.close()


def update_cccd_registration(
    *,
    get_connection,
    db_write_lock,
    table_name: str,
    registration_id: str,
    updates: dict,
) -> bool:
    allowed = {"id_number", "old_id", "full_name", "dob", "gender", "address", "issued", "expiry"}
    payload = {k: updates[k] for k in updates if k in allowed}
    if not payload:
        return False
    set_sql = ", ".join([f"{k} = ?" for k in payload.keys()])
    values = list(payload.values()) + [registration_id]
    conn = get_connection()
    try:
        with db_write_lock:
            cur = conn.cursor()
            exists = cur.execute(
                f"SELECT 1 FROM {table_name} WHERE registration_id = ?",
                (registration_id,),
            ).fetchone()
            if not exists:
                return False
            cur.execute(
                f"UPDATE {table_name} SET {set_sql}, updated_at = datetime('now', 'localtime') WHERE registration_id = ?",
                values,
            )
            conn.commit()
            return True
    finally:
        conn.close()
