"""
Module bảo vệ an toàn SQL (SQL Guard & Validation) cho phân hệ AI Agent Text-to-SQL.
Thực thi truy vấn ở chế độ chỉ đọc (Read-only), xác thực cú pháp, kiểm tra whitelist bảng,
chặn từ khóa nguy hại/comment/nhiều câu lệnh và áp đặt giới hạn thời gian (Timeout).
"""

import os
import re
import time
import sqlite3
from typing import Tuple, Dict, Any, Optional, Set
import pandas as pd

# Đường dẫn mặc định tới cơ sở dữ liệu SQLite
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/ecommerce.db")

# Hằng số thời gian timeout tối đa cho một truy vấn (giây)
QUERY_TIMEOUT_S: float = 10.0

# Danh sách bảng được phép truy vấn (Whitelist)
ALLOWED_TABLES: Set[str] = {
    "orders",
    "order_items",
    "order_payments",
    "products",
    "customers",
    "order_reviews",
}
WHITELIST_TABLES = ALLOWED_TABLES

# Danh sách từ khóa DDL / DML / Quản trị bị cấm hoàn toàn
BLOCKED_KEYWORDS: Set[str] = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "CREATE",
    "REPLACE",
    "VACUUM",
    "REINDEX",
    "TRIGGER",
}


class ReadOnlyTimeoutConnection(sqlite3.Connection):
    """
    Lớp kết nối SQLite tùy biến kế thừa từ sqlite3.Connection:
    - Tự động thiết lập và làm mới mốc thời gian bắt đầu truy vấn.
    - Sử dụng progress handler để ngắt (interrupt) bất kỳ truy vấn nào chạy quá timeout_seconds.
    """

    def __init__(self, *args, timeout_s: float = QUERY_TIMEOUT_S, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_start_time: float = time.time()
        self.timeout_seconds: float = timeout_s
        self.set_progress_handler(self._progress_handler, 1000)

    def _progress_handler(self) -> int:
        if time.time() - self.query_start_time > self.timeout_seconds:
            return 1  # Trả về khác 0 khiến SQLite hủy truy vấn và báo lỗi 'interrupted'
        return 0

    def cursor(self, *args, **kwargs):
        self.query_start_time = time.time()
        return super().cursor(*args, **kwargs)

    def execute(self, *args, **kwargs):
        self.query_start_time = time.time()
        return super().execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        self.query_start_time = time.time()
        return super().executemany(*args, **kwargs)

    def executescript(self, *args, **kwargs):
        self.query_start_time = time.time()
        return super().executescript(*args, **kwargs)


def get_readonly_connection(
    db_path: Optional[str] = None,
    timeout_s: float = QUERY_TIMEOUT_S
) -> sqlite3.Connection:
    """
    Mở kết nối tới SQLite Database ở chế độ chỉ đọc (Read-only):
    - Sử dụng URI file:<path>?mode=ro và tham số uri=True.
    - Mặc định lấy đường dẫn DB theo thứ tự: tham số db_path -> ECOMMERCE_DB_PATH -> DB_PATH.
    - Tự động áp dụng progress handler để hủy truy vấn chạy quá timeout_s giây.
    """
    if db_path is None:
        db_path = os.getenv("ECOMMERCE_DB_PATH") or os.getenv("DB_PATH") or DB_PATH

    abs_path = os.path.abspath(db_path)
    norm_path = abs_path.replace("\\", "/")
    uri = f"file:{norm_path}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=timeout_s,
        factory=lambda *a, **kw: ReadOnlyTimeoutConnection(*a, timeout_s=timeout_s, **kw)
    )


def _strip_literals_and_check_quotes(sql: str) -> Tuple[str, bool]:
    """
    Thay thế toàn bộ chuỗi ký tự bên trong cặp nháy đơn '...' bằng '__STR__',
    xử lý đúng dấu nháy kép '' bên trong chuỗi.
    Trả về (clean_sql, quotes_valid). Nếu có dấu nháy chưa đóng, quotes_valid = False.
    """
    result = []
    i = 0
    n = len(sql)
    in_quote = False

    while i < n:
        char = sql[i]
        if char == "'":
            if in_quote:
                # Kiểm tra dấu nháy thoát '' trong SQL
                if i + 1 < n and sql[i + 1] == "'":
                    i += 2
                    continue
                else:
                    in_quote = False
                    result.append("'__STR__'")
                    i += 1
                    continue
            else:
                in_quote = True
                i += 1
                continue
        if not in_quote:
            result.append(char)
        i += 1

    if in_quote:
        return "", False
    return "".join(result), True


def _tokenize(sql: str):
    """Tokenize chuỗi SQL thành danh sách các từ định danh, số và ký tự dấu câu."""
    token_pattern = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*|\(|\)|,|;|!=|<=|>=|[<>=+\-*/])")
    for match in token_pattern.finditer(sql):
        yield match.group(0)


def _extract_tables_and_ctes(clean_sql: str) -> Set[str]:
    """
    Trích xuất danh sách tất cả các bảng được tham chiếu sau FROM hoặc JOIN,
    đồng thời phát hiện và loại bỏ các tên CTE tự định nghĩa trong mệnh đề WITH.
    """
    tokens = list(_tokenize(clean_sql))
    n = len(tokens)
    cte_names: Set[str] = set()
    referenced_tables: Set[str] = set()

    # 1. Trích xuất tên CTE: WITH cte1 AS (...), cte2 AS (...)
    i = 0
    while i < n:
        if tokens[i].upper() == 'WITH':
            i += 1
            while i < n:
                if tokens[i] == '(':
                    break
                cte_candidate = tokens[i]
                if i + 2 < n and tokens[i + 1].upper() == 'AS' and tokens[i + 2] == '(':
                    cte_names.add(cte_candidate.lower())
                    i += 3
                    depth = 1
                    while i < n and depth > 0:
                        if tokens[i] == '(':
                            depth += 1
                        elif tokens[i] == ')':
                            depth -= 1
                        i += 1
                    if i < n and tokens[i] == ',':
                        i += 1
                        continue
                    else:
                        break
                else:
                    break
        else:
            i += 1

    # 2. Trích xuất tên bảng sau FROM và JOIN
    sql_clause_keywords = {
        'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS', 'OUTER', 'NATURAL',
        'GROUP', 'HAVING', 'ORDER', 'LIMIT', 'OFFSET', 'UNION', 'EXCEPT', 'INTERSECT',
        'WINDOW', 'ON', 'USING', 'AS', 'SET', 'SELECT', 'WITH'
    }

    i = 0
    in_from_clause = False
    paren_depth_at_from = 0
    current_paren_depth = 0

    while i < n:
        tok = tokens[i]
        tok_upper = tok.upper()

        if tok == '(':
            current_paren_depth += 1
            i += 1
            continue
        elif tok == ')':
            current_paren_depth -= 1
            if in_from_clause and current_paren_depth < paren_depth_at_from:
                in_from_clause = False
            i += 1
            continue

        if tok_upper in ('WHERE', 'GROUP', 'HAVING', 'ORDER', 'LIMIT', 'UNION', 'EXCEPT', 'INTERSECT'):
            in_from_clause = False

        if tok_upper in ('JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS', 'OUTER', 'NATURAL'):
            in_from_clause = False
            while i < n and tokens[i].upper() in ('INNER', 'LEFT', 'RIGHT', 'FULL', 'CROSS', 'OUTER', 'NATURAL'):
                i += 1
            if i < n and tokens[i].upper() == 'JOIN':
                i += 1
                if i < n and tokens[i] != '(':
                    table_name = tokens[i]
                    if table_name.upper() not in sql_clause_keywords:
                        referenced_tables.add(table_name.lower())
                continue

        if tok_upper == 'FROM':
            in_from_clause = True
            paren_depth_at_from = current_paren_depth
            i += 1
            if i < n and tokens[i] != '(':
                table_name = tokens[i]
                if table_name.upper() not in sql_clause_keywords:
                    referenced_tables.add(table_name.lower())
            continue

        if in_from_clause and current_paren_depth == paren_depth_at_from and tok == ',':
            i += 1
            if i < n and tokens[i] != '(':
                table_name = tokens[i]
                if table_name.upper() not in sql_clause_keywords:
                    referenced_tables.add(table_name.lower())
            continue

        i += 1

    # Loại bỏ tên CTE tự định nghĩa, chỉ giữ lại bảng bên ngoài
    external_tables = {t for t in referenced_tables if t not in cte_names}
    return external_tables


def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Xác thực câu truy vấn SQL trước khi thực thi:
    1. Kiểm tra câu lệnh không rỗng và không chứa nháy chuỗi chưa đóng.
    2. Chặn comment (-- hoặc /* */).
    3. Chặn nhiều câu lệnh (phát hiện dấu chấm phẩy ở giữa).
    4. Chỉ cho phép đúng 1 câu lệnh bắt đầu bằng SELECT hoặc WITH (có SELECT).
    5. Chặn từ khóa DDL/DML/quản trị nguy hại theo token (không nhầm với tên cột).
    6. Kiểm tra mọi bảng tham chiếu phải thuộc danh sách Whitelist cho phép.
    Trả về (True, "") nếu hợp lệ, hoặc (False, "lý do tiếng Việt") nếu bị chặn.
    """
    if not sql or not isinstance(sql, str) or not sql.strip():
        return False, "Câu lệnh SQL rỗng."

    # 1. Tách chuỗi ký tự '...' và kiểm tra nháy đơn hợp lệ
    clean_sql, quotes_ok = _strip_literals_and_check_quotes(sql)
    if not quotes_ok:
        return False, "Dấu nháy chuỗi không hợp lệ (chưa đóng dấu nháy đơn)."

    # 2. Chặn comment
    if "--" in clean_sql or "/*" in clean_sql or "*/" in clean_sql:
        return False, "Không cho phép sử dụng comment trong câu lệnh SQL."

    # 3. Kiểm tra dấu chấm phẩy ; (chỉ cho phép tối đa 1 dấu ở cuối câu lệnh)
    stripped = clean_sql.strip()
    if stripped.endswith(";"):
        stripped = stripped[:-1].strip()
    if ";" in stripped:
        return False, "Chỉ cho phép thực thi một câu lệnh SQL duy nhất (phát hiện dấu ';')."

    tokens = list(_tokenize(stripped))
    if not tokens:
        return False, "Câu lệnh SQL rỗng."

    # 4. Chặn từ khóa nguy hiểm theo token (không phân biệt hoa thường)
    for tok in tokens:
        tok_upper = tok.upper()
        if tok_upper in BLOCKED_KEYWORDS:
            return False, f"Từ khóa bị cấm: '{tok_upper}'."

    # 5. Kiểm tra từ bắt đầu (phải là SELECT hoặc WITH)
    first_word = tokens[0].upper()
    if first_word not in ("SELECT", "WITH"):
        return False, f"Câu lệnh phải bắt đầu bằng SELECT hoặc WITH (bắt đầu bằng '{tokens[0]}')."

    # Nếu là câu lệnh WITH, kiểm tra phải chứa SELECT
    if first_word == "WITH":
        has_select = any(t.upper() == "SELECT" for t in tokens)
        if not has_select:
            return False, "Câu lệnh WITH phải kết thúc bằng một truy vấn SELECT."

    # 6. Kiểm tra whitelist bảng
    tables = _extract_tables_and_ctes(clean_sql)
    for table in tables:
        t_clean = table.split('.')[-1]
        if t_clean not in ALLOWED_TABLES:
            return False, f"Bảng '{table}' không nằm trong danh sách cho phép (whitelist)."

    return True, ""


def execute_safe(
    sql: str,
    max_rows: int = 500,
    db_path: Optional[str] = None,
    timeout_s: float = QUERY_TIMEOUT_S
) -> Dict[str, Any]:
    """
    Thực thi an toàn một câu truy vấn SQL:
    1. Kiểm tra tính hợp lệ qua validate_sql(). Nếu vi phạm, trả ngay ok=False kèm lỗi.
    2. Tự động áp đặt LIMIT an toàn bằng cách bọc: SELECT * FROM (<sql>) LIMIT max_rows.
    3. Mở kết nối Read-only với SQLite.
    4. Bắt mọi ngoại lệ (cú pháp, timeout, cột thiếu) và trả về thông điệp súc tích, không stack trace.
    5. Đóng kết nối an toàn trong khối try/finally.
    """
    valid, err_msg = validate_sql(sql)
    if not valid:
        return {
            "ok": False,
            "error": err_msg,
            "df": None,
        }

    # Loại bỏ dấu chấm phẩy ở cuối câu lệnh con trước khi bọc
    clean_inner = sql.strip().rstrip(";").strip()
    wrapped_sql = f"SELECT * FROM ({clean_inner}) LIMIT {max_rows}"

    conn = None
    try:
        conn = get_readonly_connection(db_path=db_path, timeout_s=timeout_s)
        df = pd.read_sql_query(wrapped_sql, conn)
        n_rows = len(df)
        truncated = n_rows >= max_rows

        return {
            "ok": True,
            "df": df,
            "rows": n_rows,
            "truncated": truncated,
            "sql_executed": wrapped_sql,
        }
    except Exception as e:
        err_str = str(e)
        if "interrupted" in err_str.lower():
            return {
                "ok": False,
                "error": f"Truy vấn bị hủy do vượt quá thời gian cho phép ({int(timeout_s)} giây).",
                "df": None,
            }
        clean_msg = re.sub(r"^Execution failed on sql '[^']+':\s*", "", err_str)
        return {
            "ok": False,
            "error": f"Lỗi thực thi SQL: {clean_msg}",
            "df": None,
        }
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
