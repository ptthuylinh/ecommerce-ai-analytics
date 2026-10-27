"""
Bộ kiểm thử đơn vị và tích hợp cho module bảo vệ SQL src/ai/sql_guard.py.
Kiểm tra tính an toàn của validate_sql, execute_safe, kết nối chỉ đọc và cơ chế timeout.
"""

import os
import sqlite3
import pytest
import pandas as pd

from src.ai.sql_guard import (
    validate_sql,
    execute_safe,
    get_readonly_connection,
    ALLOWED_TABLES,
    BLOCKED_KEYWORDS,
    QUERY_TIMEOUT_S,
    DB_PATH,
)


# ==============================================================================
# 1. KIỂM THỬ VALIDATE_SQL: CÁC TRƯỜNG HỢP HỢP LỆ (Unit Tests - Not Integration)
# ==============================================================================

VALID_SQL_CASES = [
    # 1. SELECT đơn giản
    "SELECT * FROM orders",
    "SELECT order_id, order_status FROM orders",
    # 2. SELECT có JOIN giữa các bảng whitelist
    (
        "SELECT o.order_id, c.customer_city "
        "FROM orders o "
        "JOIN customers c ON o.customer_id = c.customer_id"
    ),
    (
        "SELECT o.order_id, i.price, p.product_category_name "
        "FROM orders o "
        "INNER JOIN order_items i ON o.order_id = i.order_id "
        "LEFT JOIN products p ON i.product_id = p.product_id"
    ),
    # 3. WITH ... SELECT (CTE)
    "WITH top_orders AS (SELECT order_id FROM orders) SELECT * FROM top_orders",
    (
        "WITH o AS (SELECT order_id FROM orders), "
        "     i AS (SELECT order_id, price FROM order_items) "
        "SELECT o.order_id, i.price FROM o JOIN i ON o.order_id = i.order_id"
    ),
    # 4. Có alias (AS alias hoặc alias trực tiếp)
    (
        "SELECT o.order_id AS id, p.payment_value AS val "
        "FROM orders AS o "
        "JOIN order_payments AS p ON o.order_id = p.order_id"
    ),
    # 5. Có dấu chấm phẩy ; ở cuối câu lệnh
    "SELECT * FROM products;",
    "SELECT order_id FROM orders WHERE order_status = 'delivered';   ",
    # 6. Viết hoa / viết thường lẫn lộn
    "sElEcT order_id, order_status fRoM OrDeRs;",
    "wItH cTe As (SeLeCt * FrOm CuStOmErS) sElEcT * fRoM cTe",
    # 7. Tên cột chứa từ khóa như 'created_at' hoặc 'order_status_update' không bị chặn nhầm
    "SELECT order_id, created_at FROM orders",
    "SELECT order_status_update, create_date FROM orders",
    "SELECT product_id, replacement_cost FROM products",
    # 8. Chuỗi chứa chữ 'drop', 'delete', 'update' trong dấu nháy đơn không bị chặn nhầm
    "SELECT * FROM order_reviews WHERE review_comment_message = 'drop'",
    "SELECT * FROM products WHERE product_category_name = 'delete'",
    "SELECT * FROM order_reviews WHERE review_comment_title = 'please update my order'",
    # 9. Dấu phẩy phân tách bảng trong FROM (Comma Join)
    "SELECT * FROM orders o, customers c WHERE o.customer_id = c.customer_id",
    # 10. SELECT có GROUP BY, ORDER BY, LIMIT
    (
        "SELECT customer_state, COUNT(*) AS cnt "
        "FROM customers "
        "GROUP BY customer_state "
        "ORDER BY cnt DESC "
        "LIMIT 10"
    ),
    # 11. SELECT hằng số không cần FROM
    "SELECT 1",
    "SELECT 1 + 1 AS result",
    # 12. Subquery lồng nhau trong FROM
    "SELECT * FROM (SELECT order_id FROM orders) sub",
]


@pytest.mark.parametrize("sql", VALID_SQL_CASES)
def test_validate_sql_valid_cases(sql: str):
    """Kiểm tra các câu truy vấn SQL hợp lệ phải được validate_sql thông qua."""
    ok, reason = validate_sql(sql)
    assert ok is True, f"Câu lệnh hợp lệ bị chặn: '{sql}'. Lý do: '{reason}'"
    assert reason == "", f"Lý do phải rỗng khi hợp lệ: '{reason}'"


# ==============================================================================
# 2. KIỂM THỬ VALIDATE_SQL: CÁC TRƯỜNG HỢP BỊ CHẶN (Unit Tests - Not Integration)
# ==============================================================================

BLOCKED_SQL_CASES = [
    # Nhiều câu lệnh / Dấu chấm phẩy ở giữa
    ("SELECT 1; DROP TABLE orders", "nhiều câu lệnh"),
    ("SELECT * FROM orders; SELECT * FROM customers", "nhiều câu lệnh"),
    ("SELECT * FROM orders;;", "nhiều câu lệnh"),
    # Bảng hệ thống bị chặn
    ("select * from sqlite_master", "sqlite_master"),
    ("SELECT * FROM sqlite_schema", "sqlite_schema"),
    ("SELECT * FROM (SELECT * FROM sqlite_master)", "sqlite_master lồng"),
    # Từ khóa DDL / DML / Quản trị bị cấm
    ("ATTACH DATABASE 'hack.db' AS hack", "ATTACH"),
    ("DETACH DATABASE hack", "DETACH"),
    ("PRAGMA table_info(orders)", "PRAGMA"),
    ("DELETE FROM orders WHERE order_id = '123'", "DELETE"),
    ("UPDATE orders SET order_status = 'test'", "UPDATE"),
    ("INSERT INTO customers VALUES ('c1', 'u1', 12345, 'city', 'SP')", "INSERT"),
    ("CREATE TABLE hack (id INT)", "CREATE"),
    ("ALTER TABLE orders ADD COLUMN hacked TEXT", "ALTER"),
    ("DROP TABLE customers", "DROP"),
    ("VACUUM", "VACUUM"),
    ("REINDEX", "REINDEX"),
    ("REPLACE INTO orders (order_id) VALUES ('123')", "REPLACE"),
    # Viết hoa / thường lẫn lộn cho lệnh cấm
    ("dRoP tAbLe orders", "dRoP"),
    ("dElEtE fRoM customers", "dElEtE"),
    # Chặn comment
    ("SELECT * FROM orders -- comment che lệnh", "comment --"),
    ("SELECT /* comment */ * FROM orders", "comment /* */"),
    ("SELECT * FROM orders\n-- comment dòng tiếp theo", "comment dòng mới"),
    # Bảng ngoài whitelist
    ("SELECT * FROM users", "bảng ngoài whitelist"),
    ("SELECT * FROM admin_accounts", "bảng ngoài whitelist"),
    ("SELECT o.order_id, u.secret FROM orders o JOIN users u ON o.customer_id = u.id", "JOIN bảng ngoài whitelist"),
    ("WITH bad AS (SELECT * FROM users) SELECT * FROM bad", "CTE truy vấn bảng ngoài whitelist"),
    # Chuỗi rỗng hoặc chỉ khoảng trắng
    ("", "chuỗi rỗng"),
    ("   \n\t  ", "chỉ khoảng trắng"),
    # Dấu nháy chuỗi chưa đóng
    ("SELECT * FROM orders WHERE order_status = 'delivered", "nháy đơn chưa đóng"),
    # WITH không có SELECT
    ("WITH cte AS (SELECT 1) INSERT INTO orders VALUES (1)", "WITH không có SELECT"),
]


@pytest.mark.parametrize("sql,case_desc", BLOCKED_SQL_CASES)
def test_validate_sql_blocked_cases(sql: str, case_desc: str):
    """Kiểm tra các câu truy vấn vi phạm quy tắc an toàn phải bị validate_sql từ chối."""
    ok, reason = validate_sql(sql)
    assert ok is False, f"Ca '{case_desc}' với SQL: '{sql}' không bị chặn!"
    assert len(reason) > 0, f"Phải có lý do từ chối cho ca '{case_desc}'"


def test_execute_safe_rejects_invalid_sql_without_db():
    """Kiểm tra execute_safe từ chối ngay lập tức khi validate_sql thất bại mà không cần chạm vào DB."""
    res = execute_safe("DROP TABLE orders")
    assert res["ok"] is False
    assert "Từ khóa bị cấm: 'DROP'" in res["error"]
    assert res["df"] is None

    res_comment = execute_safe("SELECT * FROM orders -- hack")
    assert res_comment["ok"] is False
    assert "comment" in res_comment["error"].lower()
    assert res_comment["df"] is None


# ==============================================================================
# 3. KIỂM THỬ EXECUTE_SAFE TRÊN DB THẬT (Integration Tests)
# ==============================================================================

@pytest.mark.integration
def test_execute_safe_count_orders_matches_db():
    """Kiểm tra execute_safe(SELECT COUNT(*) FROM orders) trả về đúng số khớp với DB thật."""
    if not os.path.exists(DB_PATH):
        pytest.skip(f"Database không tồn tại: {DB_PATH}")

    # Truy vấn đối chiếu trực tiếp
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM orders;")
    expected_count = cur.fetchone()[0]
    conn.close()

    res = execute_safe("SELECT COUNT(*) FROM orders")
    assert res["ok"] is True
    assert res["rows"] == 1
    assert res["truncated"] is False
    assert int(res["df"].iloc[0, 0]) == expected_count


@pytest.mark.integration
def test_execute_safe_no_limit_capped_at_max_rows():
    """Kiểm tra khi câu SQL không có LIMIT, kết quả không vượt quá max_rows."""
    if not os.path.exists(DB_PATH):
        pytest.skip(f"Database không tồn tại: {DB_PATH}")

    res = execute_safe("SELECT * FROM orders", max_rows=50)
    assert res["ok"] is True
    assert res["rows"] == 50
    assert len(res["df"]) == 50
    assert res["truncated"] is True
    assert "LIMIT 50" in res["sql_executed"]


@pytest.mark.integration
def test_execute_safe_high_limit_lowered_to_max_rows():
    """Kiểm tra câu SQL có LIMIT 100000 bị hạ xuống mức max_rows an toàn."""
    if not os.path.exists(DB_PATH):
        pytest.skip(f"Database không tồn tại: {DB_PATH}")

    res = execute_safe("SELECT * FROM orders LIMIT 100000", max_rows=100)
    assert res["ok"] is True
    assert res["rows"] == 100
    assert len(res["df"]) == 100
    assert res["truncated"] is True


@pytest.mark.integration
def test_execute_safe_small_limit_respected():
    """Kiểm tra câu SQL có LIMIT nhỏ hơn max_rows được giữ nguyên."""
    if not os.path.exists(DB_PATH):
        pytest.skip(f"Database không tồn tại: {DB_PATH}")

    res = execute_safe("SELECT * FROM orders LIMIT 5", max_rows=500)
    assert res["ok"] is True
    assert res["rows"] == 5
    assert len(res["df"]) == 5
    assert res["truncated"] is False


@pytest.mark.integration
def test_readonly_connection_strictly_blocks_writes():
    """Kiểm tra kết nối get_readonly_connection thực sự là Read-only (thử INSERT phải lỗi)."""
    if not os.path.exists(DB_PATH):
        pytest.skip(f"Database không tồn tại: {DB_PATH}")

    conn = get_readonly_connection()
    try:
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            conn.execute("INSERT INTO customers (customer_id) VALUES ('fake_cust_id')")
        assert "readonly" in str(exc_info.value).lower()
    finally:
        conn.close()


@pytest.mark.integration
def test_execute_safe_invalid_column_returns_ok_false_no_raise():
    """Kiểm tra truy vấn chứa cột không tồn tại trả về ok=False kèm thông báo lỗi rõ ràng, không raise."""
    if not os.path.exists(DB_PATH):
        pytest.skip(f"Database không tồn tại: {DB_PATH}")

    res = execute_safe("SELECT non_existent_column_xyz FROM orders")
    assert res["ok"] is False
    assert res["df"] is None
    assert "no such column" in res["error"].lower()


@pytest.mark.integration
def test_execute_safe_disallowed_table_returns_ok_false():
    """Kiểm tra truy vấn bảng không có trong whitelist trả về ok=False."""
    res = execute_safe("SELECT * FROM sqlite_master")
    assert res["ok"] is False
    assert res["df"] is None
    assert "whitelist" in res["error"].lower()


@pytest.mark.integration
def test_execute_safe_timeout_heavy_query():
    """
    Kiểm tra cơ chế timeout: Một truy vấn cực nặng (CROSS JOIN giữa 2 bảng lớn)
    bị SQLite hủy và trả về ok=False kèm thông báo quá thời gian cho phép.
    """
    if not os.path.exists(DB_PATH):
        pytest.skip(f"Database không tồn tại: {DB_PATH}")

    # Chạy truy vấn nặng với timeout_s=10.0 (QUERY_TIMEOUT_S chuẩn)
    # CROSS JOIN giữa order_items (112k dòng) x order_items (112k dòng) = 12,6 tỷ dòng
    heavy_sql = "SELECT COUNT(*) FROM order_items i1 CROSS JOIN order_items i2"
    res = execute_safe(heavy_sql, timeout_s=QUERY_TIMEOUT_S)

    assert res["ok"] is False
    assert res["df"] is None
    assert "thời gian" in res["error"].lower() or "hủy" in res["error"].lower()
