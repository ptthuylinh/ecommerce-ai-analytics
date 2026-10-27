"""
Module AI Agent Text-to-SQL cho dự án E-Commerce Analytics.
Sử dụng chính thức Google GenAI SDK (google-genai), không dùng LangChain.

Các tính năng nâng cao:
1. Cache truy vấn: Lưu SQL thành công vào data/agent_cache.db, tái sử dụng không cần gọi LLM.
2. Danh sách câu hỏi mẫu (SAMPLE_QUESTIONS) & ask_sample(index) chạy trực tiếp SQL đã kiểm chứng.
3. Diễn giải bằng f-string template khi kết quả <= 1 dòng hoặc <= 2 cột, hỗ trợ interpret_with_llm=False.
4. Quản lý hạn mức ngày (DAILY_LLM_LIMIT = 18), get_quota_status() và xử lý lỗi 429 thân thiện (QUOTA_EXHAUSTED).
5. Kiểm định an toàn và trích xuất chart_spec tự động.
"""

import json
import os
import re
import sqlite3
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv

from src.ai.cache import get_cached_sql, set_cached_sql, DEFAULT_CACHE_DB_PATH
from src.ai.schema_context import FEW_SHOTS, build_schema_prompt
from src.ai.sql_guard import execute_safe, validate_sql

# Nạp file .env nếu có
load_dotenv()

# ==============================================================================
# HẰNG SỐ CẤU HÌNH
# ==============================================================================

# Model Gemini mặc định (hỗ trợ đọc từ biến môi trường)
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# Đường dẫn CSDL Audit Log riêng biệt (không ghi vào data/ecommerce.db)
AUDIT_DB_PATH: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/audit_log.db")
)

# Hạn mức số lượt gọi LLM tối đa trong một ngày (mặc định 18 < 20 để an toàn)
DAILY_LLM_LIMIT: int = int(os.getenv("DAILY_LLM_LIMIT", "18"))

# Số lần thử lại tối đa khi truy vấn SQL bị lỗi hoặc rỗng dòng
MAX_RETRIES: int = 2

# Số dòng tối đa gửi cho LLM diễn giải
MAX_ROWS_FOR_INTERPRETATION: int = 20

# Thông báo từ chối câu hỏi ngoài phạm vi
OUT_OF_SCOPE_MSG: str = (
    "Xin lỗi, tôi là trợ lý AI chuyên về phân tích số liệu kinh doanh E-Commerce Olist. "
    "Tôi không thể trả lời các câu hỏi ngoài phạm vi nghiệp vụ, thông tin cá nhân nhạy cảm "
    "hoặc thực hiện các yêu cầu sửa đổi, xóa dữ liệu trong hệ thống."
)

# Thông báo khi thiếu API Key
MISSING_KEY_MSG: str = (
    "Chưa cấu hình GEMINI_API_KEY. Vui lòng thêm khóa API vào file .env "
    "(theo mẫu .env.example) hoặc cài đặt trong Streamlit secrets để sử dụng tính năng AI Agent."
)

# Thông báo khi chạm hạn mức ngày
QUOTA_EXHAUSTED_MSG: str = (
    f"Đã đạt hạn mức truy vấn AI trong ngày ({DAILY_LLM_LIMIT}/{DAILY_LLM_LIMIT} lượt gọi). "
    "Vui lòng thử lại vào ngày mai khi hạn mức được làm mới, hoặc sử dụng danh sách câu hỏi mẫu có sẵn trong hệ thống."
)

# ==============================================================================
# DANH SÁCH CÂU HỎI MẪU (LẤY TỪ FEW_SHOTS ĐÃ KIỂM CHỨNG)
# ==============================================================================

SAMPLE_QUESTIONS: List[Dict[str, Any]] = [
    {
        "index": i,
        "question": shot["question"],
        "sql": shot["sql"],
    }
    for i, shot in enumerate(FEW_SHOTS)
]


# ==============================================================================
# 1. QUẢN LÝ KHÓA API, HẠN MỨC & KHỞI TẠO CLIENT
# ==============================================================================

def get_api_key() -> Optional[str]:
    """
    Lấy GEMINI_API_KEY từ biến môi trường (.env) hoặc st.secrets nếu có.
    Không làm sập ứng dụng nếu thiếu key.
    """
    key = os.getenv("GEMINI_API_KEY")
    if key and key.strip() and key.strip() != "your_key_here":
        return key.strip()

    try:
        import streamlit as st

        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            secret_key = str(st.secrets["GEMINI_API_KEY"]).strip()
            if secret_key and secret_key != "your_key_here":
                return secret_key
    except Exception:
        pass

    return None


def get_gemini_client(api_key: Optional[str] = None):
    """Khởi tạo Client của google-genai SDK."""
    if api_key is None:
        api_key = get_api_key()

    if not api_key:
        return None

    try:
        from google import genai

        return genai.Client(api_key=api_key)
    except Exception:
        return None


def get_quota_status(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Đếm số lượt gọi LLM trong ngày hôm nay từ bảng AUDIT_LOG.
    Trả về: {"used": int, "limit": int, "remaining": int, "is_exhausted": bool}.
    """
    target_path = db_path or AUDIT_DB_PATH
    init_audit_db(target_path)
    today_prefix = datetime.now().strftime("%Y-%m-%d")

    try:
        with sqlite3.connect(target_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(SUM(llm_calls), 0) 
                FROM AUDIT_LOG 
                WHERE substr(timestamp, 1, 10) = ?;
                """,
                (today_prefix,),
            )
            used_calls = int(cursor.fetchone()[0] or 0)
    except Exception:
        used_calls = 0

    remaining = max(0, DAILY_LLM_LIMIT - used_calls)
    return {
        "used": used_calls,
        "limit": DAILY_LLM_LIMIT,
        "remaining": remaining,
        "is_exhausted": used_calls >= DAILY_LLM_LIMIT,
    }


# ==============================================================================
# 2. KIỂM TRA PHẠM VI CÂU HỎI (OUT-OF-SCOPE & AN TOÀN)
# ==============================================================================

OUT_OF_SCOPE_PATTERNS = [
    # Yêu cầu phá hoại / sửa đổi / xóa dữ liệu
    r"\b(xóa|xoa|drop|delete|update|cập nhật|chỉnh sửa|insert|thêm vào|create table|alter table|truncate)\b",
    # Thông tin cá nhân nhạy cảm / PII (Lưu ý: "thẻ tín dụng" là payment_type hợp lệ; chỉ chặn khi hỏi số thẻ, mã cvv, mật khẩu)
    r"\b(mật khẩu|password|số thẻ|mã thẻ|cvv|cmnd|căn cước|sđt|số điện thoại)\b",
    # Các chủ đề không liên quan
    r"\b(thời tiết|làm thơ|bài thơ|hát|bài hát|viết code python|viết code java|lập trình|công thức nấu ăn|bóng đá|đội bóng|chính trị|tổng thống)\b",
]


def is_out_of_scope(question: str) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra xem câu hỏi có thuộc diện ngoài phạm vi hoặc vi phạm an toàn không.
    Trả về: (True, thông_báo_từ_chối) nếu ngoài phạm vi; (False, None) nếu hợp lệ.
    """
    q_clean = question.strip().lower()
    if not q_clean:
        return True, "Vui lòng nhập câu hỏi phân tích dữ liệu kinh doanh."

    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, q_clean):
            return True, OUT_OF_SCOPE_MSG

    return False, None


# ==============================================================================
# 3. GHI NHẬT KÝ TƯƠNG TÁC (AUDIT LOG VÀO FILE RIÊNG data/audit_log.db)
# ==============================================================================

def init_audit_db(db_path: str = AUDIT_DB_PATH) -> None:
    """Tạo bảng AUDIT_LOG trong file SQLite riêng biệt và tự động thêm cột llm_calls nếu thiếu."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS AUDIT_LOG (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                question TEXT NOT NULL,
                sql TEXT,
                status TEXT NOT NULL,
                row_count INTEGER,
                attempts INTEGER NOT NULL,
                latency_s REAL NOT NULL,
                error TEXT,
                llm_calls INTEGER DEFAULT 0
            );
            """
        )
        # Migration: nếu bảng đã có từ trước mà thiếu cột llm_calls
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(AUDIT_LOG);")
        columns = [row[1] for row in cursor.fetchall()]
        if "llm_calls" not in columns:
            cursor.execute("ALTER TABLE AUDIT_LOG ADD COLUMN llm_calls INTEGER DEFAULT 0;")
        conn.commit()

def log_interaction(
    question: str,
    sql: Optional[str],
    status: str,
    row_count: Optional[int],
    attempts: int,
    latency_s: float,
    error: Optional[str] = None,
    llm_calls: int = 0,
    db_path: Optional[str] = None,
) -> None:
    """Ghi một bản ghi nhật ký truy vấn vào CSDL AUDIT_LOG kèm số lượt gọi LLM."""
    target_path = db_path or AUDIT_DB_PATH
    try:
        init_audit_db(target_path)
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(target_path) as conn:
            conn.execute(
                """
                INSERT INTO AUDIT_LOG (timestamp, question, sql, status, row_count, attempts, latency_s, error, llm_calls)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    timestamp_str,
                    question,
                    sql,
                    status,
                    row_count,
                    attempts,
                    round(float(latency_s), 3),
                    error,
                    llm_calls,
                ),
            )
            conn.commit()
    except Exception:
        # Ghi log phụ trợ không được làm gián đoạn phản hồi của ứng dụng
        pass


# ==============================================================================
# 4. DIỄN GIẢI KẾT QUẢ BẰNG MẪU F-STRING (TEMPLATE INTERPRETATION)
# ==============================================================================

def format_number(val: Any) -> str:
    """Định dạng số theo chuẩn hiển thị dễ đọc."""
    if val is None or pd.isna(val):
        return "N/A"
    try:
        import numpy as np

        if isinstance(val, (int, float, np.integer, np.floating)):
            f_val = float(val)
            if f_val.is_integer():
                return f"{int(f_val):,}"
            return f"{f_val:,.2f}"
    except (ValueError, TypeError):
        pass
    return str(val)


def template_interpret(
    question: str,
    df: pd.DataFrame,
) -> Tuple[Optional[Dict[str, str]], str]:
    """
    Diễn giải kết quả bằng mẫu f-string (không tốn lượt gọi LLM).
    Áp dụng khi kết quả <= 1 dòng hoặc <= 2 cột.
    Tự động suy luận chart_spec phù hợp nếu có 2 cột (nhãn & giá trị).
    """
    if df is None or df.empty:
        return None, "Không tìm thấy dữ liệu phù hợp với câu hỏi trong hệ thống."

    n_rows, n_cols = len(df), len(df.columns)
    chart_spec: Optional[Dict[str, str]] = None

    # Trường hợp 1: Chỉ có 1 dòng kết quả (KPI tổng hợp hoặc giá trị đơn lẻ)
    if n_rows == 1:
        if n_cols == 1:
            col_name = df.columns[0]
            val_str = format_number(df.iloc[0, 0])
            ans = f"Kết quả phân tích: **{col_name}** đạt **{val_str}**."
        else:
            items_str = []
            for col in df.columns:
                val_str = format_number(df.iloc[0][col])
                items_str.append(f"- **{col}**: {val_str}")
            ans = "Kết quả phân tích số liệu tổng hợp:\n" + "\n".join(items_str)
        return None, ans

    # Trường hợp 2: Có nhiều dòng nhưng <= 2 cột (ví dụ: top danh mục, doanh thu theo bang/tháng)
    col_x = df.columns[0]
    col_y = df.columns[1] if n_cols >= 2 else df.columns[0]

    # Kiểm tra xem có thể vẽ biểu đồ không
    is_col_y_numeric = pd.api.types.is_numeric_dtype(df[col_y])
    if is_col_y_numeric and n_cols == 2:
        col_x_lower = str(col_x).lower()
        if "month" in col_x_lower or "date" in col_x_lower or "year" in col_x_lower:
            chart_type = "line"
        elif "payment" in col_x_lower and n_rows <= 5:
            chart_type = "pie"
        else:
            chart_type = "bar"
        chart_spec = {"type": chart_type, "x": str(col_x), "y": str(col_y)}

    # Tạo tóm tắt dạng danh sách top tối đa 5 mục đầu
    top_items = []
    for idx in range(min(5, n_rows)):
        row = df.iloc[idx]
        x_val = str(row[col_x])
        y_val = format_number(row[col_y]) if n_cols >= 2 else ""
        if y_val:
            top_items.append(f"{idx+1}. **{x_val}**: {y_val}")
        else:
            top_items.append(f"{idx+1}. **{x_val}**")

    ans = f"Tìm thấy **{n_rows} bản ghi** kết quả. Dưới đây là các mục dẫn đầu:\n" + "\n".join(top_items)
    if n_rows > 5:
        ans += f"\n*(Và còn {n_rows - 5} bản ghi khác trong bảng dữ liệu chi tiết bên dưới)*"

    return chart_spec, ans


# ==============================================================================
# 5. TRÍCH XUẤT CÂU LỆNH SQL VÀ CHART SPEC TỪ PHẢN HỒI CỦA LLM
# ==============================================================================

def clean_sql_response(raw_text: str) -> str:
    """Trích xuất chuỗi SQL sạch từ phản hồi của LLM (loại bỏ markdown block)."""
    text = raw_text.strip()
    if text.startswith("```"):
        match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
    return text.strip()


def parse_chart_spec(text: str, df: Optional[pd.DataFrame] = None) -> Tuple[Optional[Dict[str, str]], str]:
    """Trích xuất chart_spec và câu trả lời giải thích từ text của LLM."""
    chart_spec = None
    answer = text

    chart_match = re.search(r"\[CHART_SPEC\]\s*([\s\S]*?)\s*\[ANSWER\]", text, re.IGNORECASE)
    if chart_match:
        spec_str = chart_match.group(1).strip()
        answer = text.split("[ANSWER]")[-1].strip()
        if spec_str and spec_str.lower() != "none" and spec_str.lower() != "null":
            try:
                parsed = json.loads(spec_str)
                if isinstance(parsed, dict) and "type" in parsed and "x" in parsed and "y" in parsed:
                    c_type = str(parsed["type"]).lower()
                    if c_type in {"bar", "line", "pie"}:
                        chart_spec = {
                            "type": c_type,
                            "x": str(parsed["x"]),
                            "y": str(parsed["y"]),
                        }
            except Exception:
                pass

    if chart_spec and df is not None and not df.empty:
        cols = set(df.columns)
        if chart_spec["x"] not in cols or chart_spec["y"] not in cols:
            chart_spec = None

    return chart_spec, answer.strip()


# ==============================================================================
# 6. TRUY VẤN CÂU HỎI MẪU (ASK_SAMPLE - 0 LƯỢT GỌI LLM)
# ==============================================================================

def ask_sample(
    index: int,
    db_path: Optional[str] = None,
    audit_db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Thực thi trực tiếp một câu hỏi mẫu có sẵn trong SAMPLE_QUESTIONS (lấy từ FEW_SHOTS).
    Đảm bảo 100% chuẩn xác và KHÔNG tốn bất kỳ lượt gọi LLM nào.
    """
    start_time = time.time()
    if index < 0 or index >= len(SAMPLE_QUESTIONS):
        return {
            "sql": None,
            "df": None,
            "answer": f"Chỉ số câu hỏi mẫu không hợp lệ (hợp lệ từ 0 đến {len(SAMPLE_QUESTIONS)-1}).",
            "chart_spec": None,
            "error": "INVALID_SAMPLE_INDEX",
            "attempts": 0,
            "latency_s": 0.0,
            "from_sample": True,
            "llm_calls": 0,
        }

    sample_item = SAMPLE_QUESTIONS[index]
    question = sample_item["question"]
    sql = sample_item["sql"]

    # Chạy thẳng qua execute_safe
    exec_res = execute_safe(sql, db_path=db_path)
    latency_s = round(time.time() - start_time, 3)

    if not exec_res["ok"]:
        return {
            "sql": sql,
            "df": None,
            "answer": f"Lỗi khi thực thi câu hỏi mẫu: {exec_res.get('error')}",
            "chart_spec": None,
            "error": exec_res.get("error"),
            "attempts": 0,
            "latency_s": latency_s,
            "from_sample": True,
            "llm_calls": 0,
        }

    df_result = exec_res["df"]
    chart_spec, answer = template_interpret(question, df_result)

    # Ghi log dạng sample (0 llm calls)
    log_interaction(
        question=question,
        sql=sql,
        status="sample_question",
        row_count=len(df_result),
        attempts=0,
        latency_s=latency_s,
        error=None,
        llm_calls=0,
        db_path=audit_db_path,
    )

    return {
        "sql": sql,
        "df": df_result,
        "answer": answer,
        "chart_spec": chart_spec,
        "error": None,
        "attempts": 0,
        "latency_s": latency_s,
        "from_sample": True,
        "llm_calls": 0,
    }


# ==============================================================================
# 7. HÀM CHÍNH: ASK (HỎI ĐÁP TEXT-TO-SQL VỚI CACHE & HẠN MỨC)
# ==============================================================================

def ask(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
    client: Any = None,
    interpret_with_llm: bool = True,
    use_cache: bool = True,
    db_path: Optional[str] = None,
    audit_db_path: Optional[str] = None,
    cache_db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Hàm xử lý câu hỏi Text-to-SQL toàn diện:
    1. Kiểm tra câu hỏi ngoài phạm vi (bằng từ khóa hoặc LLM).
    2. Kiểm tra Cache (nếu hit: chạy SQL đã lưu, 0 lượt gọi LLM).
    3. Kiểm tra hạn mức ngày (get_quota_status): nếu hết hạn mức trả QUOTA_EXHAUSTED.
    4. Gọi LLM sinh SQL (kèm retry tối đa 2 lần).
    5. Lưu SQL thành công vào Cache.
    6. Diễn giải kết quả: dùng template f-string nếu <=1 dòng hoặc <=2 cột (hoặc interpret_with_llm=False);
       chỉ gọi LLM diễn giải khi kết quả phức tạp.
    7. Ghi nhận chi tiết vào AUDIT_LOG.
    """
    start_time = time.time()
    attempts = 0
    llm_calls = 0
    executed_sql: Optional[str] = None
    df_result: Optional[pd.DataFrame] = None
    last_error: Optional[str] = None
    cached_hit = False

    # 1. Kiểm tra câu hỏi ngoài phạm vi bằng mẫu từ khóa
    out_of_scope, refusal_reason = is_out_of_scope(question)
    if out_of_scope:
        latency = round(time.time() - start_time, 3)
        log_interaction(
            question=question,
            sql=None,
            status="out_of_scope",
            row_count=0,
            attempts=0,
            latency_s=latency,
            error=refusal_reason,
            llm_calls=0,
            db_path=audit_db_path,
        )
        return {
            "sql": None,
            "df": None,
            "answer": refusal_reason or OUT_OF_SCOPE_MSG,
            "chart_spec": None,
            "error": None,
            "attempts": 0,
            "latency_s": latency,
            "llm_calls": 0,
            "blocked_by": "pattern",
        }

    # 2. Kiểm tra Cache SQL (nếu bật use_cache)
    if use_cache:
        cached_sql = get_cached_sql(question, db_path=cache_db_path)
        if cached_sql:
            exec_res = execute_safe(cached_sql, db_path=db_path)
            if exec_res["ok"] and exec_res["df"] is not None and not exec_res["df"].empty:
                executed_sql = cached_sql
                df_result = exec_res["df"]
                cached_hit = True

                # Diễn giải nhanh bằng template (0 lượt gọi LLM)
                chart_spec, final_answer = template_interpret(question, df_result)
                latency = round(time.time() - start_time, 3)

                log_interaction(
                    question=question,
                    sql=executed_sql,
                    status="cache_hit",
                    row_count=len(df_result),
                    attempts=0,
                    latency_s=latency,
                    error=None,
                    llm_calls=0,
                    db_path=audit_db_path,
                )
                return {
                    "sql": executed_sql,
                    "df": df_result,
                    "answer": final_answer,
                    "chart_spec": chart_spec,
                    "error": None,
                    "attempts": 0,
                    "latency_s": latency,
                    "cached": True,
                    "llm_calls": 0,
                }

    # 3. Kiểm tra Hạn mức lượt gọi LLM trong ngày
    quota = get_quota_status(db_path=audit_db_path)
    if quota["is_exhausted"]:
        latency = round(time.time() - start_time, 3)
        log_interaction(
            question=question,
            sql=None,
            status="quota_exhausted",
            row_count=0,
            attempts=0,
            latency_s=latency,
            error="QUOTA_EXHAUSTED",
            llm_calls=0,
            db_path=audit_db_path,
        )
        return {
            "sql": None,
            "df": None,
            "answer": QUOTA_EXHAUSTED_MSG,
            "chart_spec": None,
            "error": "QUOTA_EXHAUSTED",
            "attempts": 0,
            "latency_s": latency,
            "llm_calls": 0,
        }

    # 4. Kiểm tra API Key & Khởi tạo LLM Client
    if client is None:
        client = get_gemini_client()

    if client is None:
        latency = round(time.time() - start_time, 3)
        log_interaction(
            question=question,
            sql=None,
            status="missing_key",
            row_count=0,
            attempts=0,
            latency_s=latency,
            error="MISSING_API_KEY",
            llm_calls=0,
            db_path=audit_db_path,
        )
        return {
            "sql": None,
            "df": None,
            "answer": MISSING_KEY_MSG,
            "chart_spec": None,
            "error": "MISSING_API_KEY",
            "attempts": 0,
            "latency_s": latency,
            "llm_calls": 0,
        }

    # 5. Chuẩn bị System Prompt & Schema Context
    schema_prompt = build_schema_prompt(include_few_shots=True)

    # 6. Vòng lặp Sinh SQL và Thử lại (tối đa 1 lần đầu + MAX_RETRIES lần sửa)
    total_allowed_attempts = 1 + MAX_RETRIES
    retry_feedback: Optional[str] = None

    for attempt_idx in range(1, total_allowed_attempts + 1):
        attempts = attempt_idx

        if attempt_idx == 1:
            sql_prompt = (
                f"{schema_prompt}\n\n"
                f"=== NHIỆM VỤ SINH SQL ===\n"
                f"Câu hỏi của người dùng: \"{question}\"\n\n"
                "Nếu câu hỏi không liên quan đến kinh doanh Olist hoặc hỏi thông tin cá nhân, chỉ trả về chuỗi: OUT_OF_SCOPE.\n"
                "Nếu hợp lệ, hãy trả về ĐÚNG 1 câu lệnh SQL chuẩn SQLite (bắt đầu bằng SELECT hoặc WITH). "
                "Không giải thích, không kèm lời mở đầu."
            )
        else:
            sql_prompt = (
                f"{schema_prompt}\n\n"
                f"=== SỬA LỖI TRUY VẤN SQL (LẦN THỬ {attempt_idx}) ===\n"
                f"Câu hỏi gốc: \"{question}\"\n"
                f"Câu SQL bạn vừa sinh ra: \n{executed_sql}\n"
                f"Lỗi gặp phải: {retry_feedback}\n\n"
                "Vui lòng phân tích lỗi trên và trả về ĐÚNG 1 câu lệnh SQL đã sửa để khắc phục triệt để. "
                "Chỉ trả về câu SQL thuần túy."
            )

        try:
            from google.genai import types

            llm_calls += 1
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=sql_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                ),
            )
            raw_sql = getattr(response, "text", "") or ""
            current_sql = clean_sql_response(raw_sql)
        except Exception as e:
            err_msg = str(e)
            # Kiểm tra nếu là lỗi 429 quota
            if "429" in err_msg or "quota" in err_msg.lower() or "resource_exhausted" in err_msg.lower():
                latency = round(time.time() - start_time, 3)
                log_interaction(
                    question=question,
                    sql=None,
                    status="quota_exhausted",
                    row_count=0,
                    attempts=attempts,
                    latency_s=latency,
                    error="QUOTA_EXHAUSTED",
                    llm_calls=llm_calls,
                    db_path=audit_db_path,
                )
                return {
                    "sql": None,
                    "df": None,
                    "answer": QUOTA_EXHAUSTED_MSG,
                    "chart_spec": None,
                    "error": "QUOTA_EXHAUSTED",
                    "attempts": attempts,
                    "latency_s": latency,
                    "llm_calls": llm_calls,
                }
            last_error = f"Lỗi kết nối Gemini API: {err_msg}"
            break

        if not current_sql:
            last_error = "LLM không phản hồi câu lệnh SQL nào."
            retry_feedback = last_error
            continue

        if "OUT_OF_SCOPE" in current_sql.upper():
            latency = round(time.time() - start_time, 3)
            log_interaction(
                question=question,
                sql=None,
                status="out_of_scope",
                row_count=0,
                attempts=attempts,
                latency_s=latency,
                error="LLM classified as OUT_OF_SCOPE",
                llm_calls=llm_calls,
                db_path=audit_db_path,
            )
            return {
                "sql": None,
                "df": None,
                "answer": OUT_OF_SCOPE_MSG,
                "chart_spec": None,
                "error": None,
                "attempts": attempts,
                "latency_s": latency,
                "llm_calls": llm_calls,
                "blocked_by": "llm",
            }

        executed_sql = current_sql

        # Thực thi qua sql_guard.execute_safe
        exec_result = execute_safe(executed_sql, db_path=db_path)

        if not exec_result["ok"]:
            last_error = exec_result.get("error", "Lỗi cú pháp hoặc truy vấn SQL")
            retry_feedback = f"Truy vấn bị lỗi: {last_error}"
            continue

        df_candidate = exec_result.get("df")
        if df_candidate is None or df_candidate.empty:
            last_error = "Truy vấn thực thi thành công nhưng trả về 0 dòng kết quả (DataFrame rỗng)."
            retry_feedback = (
                "Truy vấn trả về 0 dòng kết quả. Vui lòng kiểm tra lại điều kiện lọc "
                "(ví dụ: trạng thái đơn, khoảng ngày mặc định 2017-01-01 đến 2018-08-31, "
                "hoặc tên danh mục sản phẩm)."
            )
            continue

        # Thành công! Lưu cache và thoát vòng lặp
        df_result = df_candidate
        last_error = None
        if use_cache:
            set_cached_sql(question, executed_sql, db_path=cache_db_path)
        break

    # 7. Diễn giải kết quả & Đề xuất Chart Spec
    chart_spec = None
    final_answer = ""

    if df_result is not None and not df_result.empty:
        n_rows, n_cols = len(df_result), len(df_result.columns)

        # Áp dụng template nếu interpret_with_llm=False hoặc kết quả <= 1 dòng hoặc <= 2 cột
        should_use_template = (not interpret_with_llm) or (n_rows <= 1) or (n_cols <= 2)

        if should_use_template:
            chart_spec, final_answer = template_interpret(question, df_result)
        else:
            # Chỉ gọi LLM diễn giải cho kết quả phức tạp (> 1 dòng và > 2 cột)
            sample_subset = df_result.head(MAX_ROWS_FOR_INTERPRETATION)
            data_text = sample_subset.to_string(index=False)
            total_rows = len(df_result)

            interpret_prompt = (
                f"Bạn là chuyên gia phân tích dữ liệu E-Commerce.\n"
                f"Câu hỏi của người dùng: \"{question}\"\n"
                f"Câu lệnh SQL đã thực thi thành công:\n{executed_sql}\n\n"
                f"Tổng số dòng kết quả tìm thấy: {total_rows}.\n"
                f"Dữ liệu mẫu (tối đa {MAX_ROWS_FOR_INTERPRETATION} dòng đầu):\n"
                f"{data_text}\n\n"
                "Hãy thực hiện 2 việc và trả về đúng định dạng sau:\n"
                "1. Nếu dữ liệu phù hợp để vẽ biểu đồ so sánh hoặc xu hướng (ví dụ: top danh mục, doanh thu theo bang, doanh thu theo tháng, cơ cấu thanh toán), "
                "hãy gợi ý một biểu đồ phù hợp (type: 'bar', 'line', hoặc 'pie', x là tên cột trục x, y là tên cột trục y). Nếu không phù hợp (ví dụ chỉ có 1 con số KPI duy nhất), hãy ghi null.\n"
                "2. Trả lời câu hỏi của người dùng bằng tiếng Việt ngắn gọn, mạch lạc, chính xác tuyệt đối theo các con số trong dữ liệu mẫu, KHÔNG tự bịa số liệu. "
                "Nếu câu hỏi không nêu rõ thời gian, hãy nhắc người dùng rằng số liệu được tính trong khoảng mặc định đầy đủ từ 2017-01-01 đến 2018-08-31.\n\n"
                "ĐỊNH DẠNG PHẢN HỒI BẮT BUỘC:\n"
                "[CHART_SPEC]\n"
                "{\"type\": \"bar\", \"x\": \"tên_cột_x\", \"y\": \"tên_cột_y\"}\n"
                "[ANSWER]\n"
                "<Nội dung câu trả lời tiếng Việt ở đây>"
            )

            try:
                from google.genai import types

                llm_calls += 1
                resp_interpret = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=interpret_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                    ),
                )
                raw_text = getattr(resp_interpret, "text", "") or ""
                chart_spec, final_answer = parse_chart_spec(raw_text, df=df_result)
            except Exception:
                chart_spec, final_answer = template_interpret(question, df_result)
    elif df_result is not None and df_result.empty:
        final_answer = (
            "Truy vấn SQL đã thực thi thành công nhưng hệ thống không tìm thấy bản ghi nào "
            "phù hợp với tiêu chí lọc hoặc khoảng thời gian yêu cầu."
        )
    else:
        final_answer = f"Không thể lấy được dữ liệu sau {attempts} lần thử do lỗi: {last_error}"

    # 8. Tính toán thời gian và Ghi Audit Log
    latency_s = round(time.time() - start_time, 3)
    status_str = "success" if (df_result is not None and not df_result.empty) else "failed"
    row_count = len(df_result) if df_result is not None else 0

    log_interaction(
        question=question,
        sql=executed_sql,
        status=status_str,
        row_count=row_count,
        attempts=attempts,
        latency_s=latency_s,
        error=last_error,
        llm_calls=llm_calls,
        db_path=audit_db_path,
    )

    return {
        "sql": executed_sql,
        "df": df_result,
        "answer": final_answer,
        "chart_spec": chart_spec,
        "error": last_error,
        "attempts": attempts,
        "latency_s": latency_s,
        "cached": cached_hit,
        "llm_calls": llm_calls,
    }
