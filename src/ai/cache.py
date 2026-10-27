"""
Module bộ nhớ đệm (Cache) cho AI Agent Text-to-SQL.
Lưu trữ câu lệnh SQL đã chạy thành công trong file SQLite riêng (data/agent_cache.db).

Nguyên tắc:
1. Khóa (query_key) = câu hỏi chuẩn hóa (chữ thường, bỏ khoảng trắng thừa).
2. Khi Cache Hit: lấy SQL đã lưu và thực thi lại bằng execute_safe (dữ liệu luôn mới),
   hoàn toàn không gọi LLM sinh SQL.
3. Chỉ lưu SQL của các lượt truy vấn thành công.
"""

import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

# Đường dẫn mặc định tới database cache SQLite riêng biệt
DEFAULT_CACHE_DB_PATH: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/agent_cache.db")
)


def normalize_question(question: str) -> str:
    """
    Chuẩn hóa câu hỏi làm khóa tra cứu cache:
    - Chuyển thành chữ thường.
    - Loại bỏ dấu khoảng trắng thừa ở đầu, cuối và giữa các từ.
    - Bỏ dấu chấm hỏi/dấu chấm cuối câu nếu có.
    """
    if not question:
        return ""
    q = question.strip().lower()
    # Loại bỏ dấu câu ở cuối (? ! .)
    q = re.sub(r"[?!.]+$", "", q).strip()
    # Gộp khoảng trắng thừa
    q = re.sub(r"\s+", " ", q)
    return q


def init_cache_db(db_path: Optional[str] = None) -> str:
    """Khởi tạo bảng AGENT_CACHE trong SQLite nếu chưa tồn tại."""
    target_path = db_path or DEFAULT_CACHE_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    with sqlite3.connect(target_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS AGENT_CACHE (
                query_key TEXT PRIMARY KEY,
                raw_question TEXT NOT NULL,
                sql TEXT NOT NULL,
                created_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 1
            );
            """
        )
        conn.commit()
    return target_path


def get_cached_sql(question: str, db_path: Optional[str] = None) -> Optional[str]:
    """
    Tra cứu SQL trong cache theo câu hỏi.
    Nếu tìm thấy (Cache Hit): Tăng hit_count lên 1 và trả về SQL.
    Nếu không tìm thấy (Cache Miss): Trả về None.
    """
    key = normalize_question(question)
    if not key:
        return None

    target_path = db_path or DEFAULT_CACHE_DB_PATH
    init_cache_db(target_path)

    try:
        with sqlite3.connect(target_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sql, hit_count FROM AGENT_CACHE WHERE query_key = ?;",
                (key,),
            )
            row = cursor.fetchone()
            if row:
                sql, hits = row[0], row[1]
                # Cập nhật số lượt hit
                conn.execute(
                    "UPDATE AGENT_CACHE SET hit_count = ? WHERE query_key = ?;",
                    (hits + 1, key),
                )
                conn.commit()
                return sql
    except Exception:
        # Cache lỗi không được làm dừng ứng dụng
        return None

    return None


def set_cached_sql(question: str, sql: str, db_path: Optional[str] = None) -> None:
    """
    Lưu câu SQL đã thực thi thành công vào cache.
    Chỉ lưu khi cả câu hỏi và SQL đều hợp lệ.
    """
    key = normalize_question(question)
    if not key or not sql or not sql.strip():
        return

    target_path = db_path or DEFAULT_CACHE_DB_PATH
    init_cache_db(target_path)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with sqlite3.connect(target_path) as conn:
            conn.execute(
                """
                INSERT INTO AGENT_CACHE (query_key, raw_question, sql, created_at, hit_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(query_key) DO UPDATE SET
                    sql = excluded.sql,
                    raw_question = excluded.raw_question,
                    created_at = excluded.created_at;
                """,
                (key, question.strip(), sql.strip(), now_str),
            )
            conn.commit()
    except Exception:
        pass


def clear_cache(db_path: Optional[str] = None) -> None:
    """Xóa sạch bộ nhớ đệm (dùng trong test hoặc quản trị)."""
    target_path = db_path or DEFAULT_CACHE_DB_PATH
    if os.path.exists(target_path):
        with sqlite3.connect(target_path) as conn:
            conn.execute("DELETE FROM AGENT_CACHE;")
            conn.commit()


def get_cache_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Lấy số lượng câu hỏi đã cache và tổng số lượt cache hit."""
    target_path = db_path or DEFAULT_CACHE_DB_PATH
    init_cache_db(target_path)
    try:
        with sqlite3.connect(target_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(hit_count), 0) FROM AGENT_CACHE;")
            total_keys, total_hits = cursor.fetchone()
            return {
                "total_cached_queries": int(total_keys or 0),
                "total_cache_hits": int(total_hits or 0),
            }
    except Exception:
        return {"total_cached_queries": 0, "total_cache_hits": 0}
