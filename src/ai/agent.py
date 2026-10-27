"""
Module AI Agent Text-to-SQL cho dự án E-Commerce Analytics.
Sử dụng chính thức Google GenAI SDK (google-genai), không dùng LangChain.

Quy trình hoạt động:
1. Nhận câu hỏi kinh doanh bằng tiếng Việt.
2. Kiểm tra câu hỏi ngoài phạm vi (out-of-scope, phá hoại, hỏi thông tin cá nhân).
3. Đọc GEMINI_API_KEY từ biến môi trường (.env) hoặc st.secrets an toàn.
4. LLM sinh mã SQL chuẩn SQLite dựa trên schema context và few-shot examples.
5. Kiểm định và thực thi an toàn qua sql_guard.execute_safe (chế độ chỉ đọc, whitelist, timeout).
6. Tự động sửa lỗi và thử lại tối đa 2 lần nếu câu SQL gặp lỗi cú pháp hoặc trả về 0 dòng.
7. Diễn giải kết quả bằng tiếng Việt súc tích, chỉ gửi tối đa 20 dòng dữ liệu cho LLM.
8. Ghi nhật ký tương tác vào CSDL SQLite riêng biệt (data/audit_log.db).
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

from src.ai.schema_context import build_schema_prompt
from src.ai.sql_guard import execute_safe, validate_sql

# Nạp file .env nếu có
load_dotenv()

# ==============================================================================
# HẰNG SỐ CẤU HÌNH
# ==============================================================================

# Model Gemini mặc định (dễ dàng cấu hình hoặc thay đổi)
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Đường dẫn CSDL Audit Log riêng biệt (không ghi vào data/ecommerce.db)
AUDIT_DB_PATH: str = os.path.join(os.path.dirname(__file__), "../../data/audit_log.db")

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


# ==============================================================================
# 1. QUẢN LÝ KHÓA API & KHỞI TẠO CLIENT
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
    except Exception as e:
        return None


# ==============================================================================
# 2. KIỂM TRA PHẠM VI CÂU HỎI (OUT-OF-SCOPE & AN TOÀN)
# ==============================================================================

OUT_OF_SCOPE_PATTERNS = [
    # Yêu cầu phá hoại / sửa đổi / xóa dữ liệu
    r"\b(xóa|xoa|drop|delete|update|cập nhật|chỉnh sửa|insert|thêm vào|create table|alter table|truncate)\b",
    # Thông tin cá nhân nhạy cảm / PII
    r"\b(mật khẩu|password|thẻ tín dụng|credit card|cvv|số thẻ|cmnd|căn cước|sđt|số điện thoại)\b",
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
# 3. GHI NHẬT KÝ TƯƠNG TÁC (AUDIT LOG VÀO FILE RIÊNG)
# ==============================================================================

def init_audit_db(db_path: str = AUDIT_DB_PATH) -> None:
    """Tạo bảng AUDIT_LOG trong file SQLite riêng biệt nếu chưa có."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS AUDIT_LOG (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            question TEXT NOT NULL,
            sql TEXT,
            status TEXT NOT NULL,
            row_count INTEGER,
            attempts INTEGER NOT NULL,
            latency_s REAL NOT NULL,
            error TEXT
        );
        """)
        conn.commit()


def log_interaction(
    question: str,
    sql: Optional[str],
    status: str,
    row_count: Optional[int],
    attempts: int,
    latency_s: float,
    error: Optional[str] = None,
    db_path: Optional[str] = None,
) -> None:
    """Ghi một bản ghi nhật ký truy vấn vào CSDL AUDIT_LOG."""
    target_path = db_path or AUDIT_DB_PATH
    try:
        init_audit_db(target_path)
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(target_path) as conn:
            conn.execute(
                """
                INSERT INTO AUDIT_LOG (timestamp, question, sql, status, row_count, attempts, latency_s, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
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
                ),
            )
            conn.commit()
    except Exception:
        # Ghi log phụ trợ không được làm gián đoạn phản hồi của ứng dụng
        pass


# ==============================================================================
# 4. TRÍCH XUẤT CÂU LỆNH SQL VÀ CHART SPEC TỪ PHẢN HỒI CỦA LLM
# ==============================================================================

def clean_sql_response(raw_text: str) -> str:
    """Trích xuất chuỗi SQL sạch từ phản hồi của LLM (loại bỏ markdown block)."""
    text = raw_text.strip()
    if text.startswith("```"):
        # Tìm block ```sql ... ``` hoặc ``` ... ```
        match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
    return text.strip()


def parse_chart_spec(text: str, df: Optional[pd.DataFrame] = None) -> Tuple[Optional[Dict[str, str]], str]:
    """
    Trích xuất chart_spec và câu trả lời giải thích từ text của LLM.
    Hỗ trợ định dạng:
    [CHART_SPEC]
    {"type": "bar", "x": "col1", "y": "col2"}
    [ANSWER]
    Nội dung trả lời...
    """
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

    # Nếu có df, kiểm tra tính hợp lệ của các cột trong chart_spec
    if chart_spec and df is not None and not df.empty:
        cols = set(df.columns)
        if chart_spec["x"] not in cols or chart_spec["y"] not in cols:
            chart_spec = None

    return chart_spec, answer.strip()


# ==============================================================================
# 5. HÀM CHÍNH: ASK (HỎI ĐÁP TEXT-TO-SQL)
# ==============================================================================

def ask(
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
    client: Any = None,
    db_path: Optional[str] = None,
    audit_db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Hàm xử lý câu hỏi của người dùng, sinh SQL an toàn, thực thi và diễn giải số liệu.

    Trả về dict chuẩn hóa:
        - sql: Câu SQL đã thực thi (hoặc None nếu ngoài phạm vi/thiếu key)
        - df: DataFrame kết quả (hoặc None)
        - answer: Câu trả lời tiếng Việt ngắn gọn, trung thực theo dữ liệu
        - chart_spec: Cấu hình biểu đồ gợi ý (None hoặc {type: 'bar'|'line'|'pie', x, y})
        - error: Thông điệp lỗi nếu có (hoặc None)
        - attempts: Số lần LLM đã sinh/sửa SQL
        - latency_s: Thời gian xử lý tổng cộng (giây)
    """
    start_time = time.time()
    attempts = 0
    executed_sql: Optional[str] = None
    df_result: Optional[pd.DataFrame] = None
    last_error: Optional[str] = None

    # 1. Kiểm tra câu hỏi ngoài phạm vi
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
        }

    # 2. Kiểm tra API Key & Khởi tạo LLM Client
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
        }

    # 3. Chuẩn bị System Prompt & Schema Context
    schema_prompt = build_schema_prompt(include_few_shots=True)

    # 4. Vòng lặp Sinh SQL và Thử lại (tối đa 1 lần đầu + MAX_RETRIES lần sửa)
    total_allowed_attempts = 1 + MAX_RETRIES
    retry_feedback: Optional[str] = None

    for attempt_idx in range(1, total_allowed_attempts + 1):
        attempts = attempt_idx

        # Xây dựng prompt sinh SQL
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
            last_error = f"Lỗi kết nối Gemini API: {str(e)}"
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
            }

        executed_sql = current_sql

        # Kiểm định và thực thi an toàn với execute_safe
        exec_result = execute_safe(executed_sql, db_path=db_path)

        if not exec_result["ok"]:
            last_error = exec_result.get("error", "Lỗi cú pháp hoặc truy vấn SQL")
            retry_feedback = f"Truy vấn bị lỗi: {last_error}"
            continue

        df_candidate = exec_result.get("df")
        if df_candidate is None or df_candidate.empty:
            # 0 dòng kết quả -> yêu cầu sửa
            last_error = "Truy vấn thực thi thành công nhưng trả về 0 dòng kết quả (DataFrame rỗng)."
            retry_feedback = (
                "Truy vấn trả về 0 dòng kết quả. Vui lòng kiểm tra lại điều kiện lọc "
                "(ví dụ: trạng thái đơn, khoảng ngày mặc định 2017-01-01 đến 2018-08-31, "
                "hoặc tên danh mục sản phẩm)."
            )
            continue

        # Thành công! Có dữ liệu > 0 dòng
        df_result = df_candidate
        last_error = None
        break

    # 5. Diễn giải kết quả bằng tiếng Việt & Đề xuất Chart Spec
    chart_spec = None
    final_answer = ""

    if df_result is not None and not df_result.empty:
        # Gửi tối đa MAX_ROWS_FOR_INTERPRETATION dòng kết quả cho LLM
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

            resp_interpret = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=interpret_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                ),
            )
            raw_text = getattr(resp_interpret, "text", "") or ""
            chart_spec, final_answer = parse_chart_spec(raw_text, df=df_result)
        except Exception as e:
            # Fallback diễn giải đơn giản nếu LLM gặp lỗi mạng ở bước trả lời
            final_answer = (
                f"Đã truy vấn thành công {total_rows} dòng kết quả phù hợp với câu hỏi của bạn. "
                f"Vui lòng xem chi tiết ở bảng dữ liệu bên dưới."
            )
    elif df_result is not None and df_result.empty:
        final_answer = (
            "Truy vấn SQL đã thực thi thành công nhưng hệ thống không tìm thấy bản ghi nào "
            "phù hợp với tiêu chí lọc hoặc khoảng thời gian yêu cầu."
        )
    else:
        final_answer = f"Không thể lấy được dữ liệu sau {attempts} lần thử do lỗi: {last_error}"

    # 6. Tính toán thời gian và Ghi Audit Log
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
    }
