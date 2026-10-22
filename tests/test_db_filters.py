"""
Bộ kiểm thử chức năng lọc dữ liệu đa chiều (Dynamic Filters) trên mini_db.
Kiểm tra khả năng lọc theo ngày, danh mục, bang, trạng thái, chống SQL Injection
và xử lý các trường hợp biên.
"""

import sqlite3
import pytest
import pandas as pd

# Import các hàm filter từ src.db
try:
    from src.db import get_filter_options, get_filtered_orders
except ImportError:
    get_filter_options = None
    get_filtered_orders = None


def test_get_filter_options_returns_metadata(mini_db):
    """Kiểm tra get_filter_options() trả về đầy đủ min/max date, categories, states, statuses."""
    if not callable(get_filter_options):
        pytest.fail("Hàm get_filter_options chưa được định nghĩa trong src/db.py (Lỗi Code)")

    options = get_filter_options()
    assert isinstance(options, dict), "get_filter_options() phải trả về một dictionary"
    
    # Kiểm tra sự tồn tại của các key bắt buộc
    for key in ["min_date", "max_date", "categories", "states", "statuses"]:
        assert key in options, f"Thiếu key '{key}' trong kết quả get_filter_options()"

    # Kiểm tra nội dung trên mini_db
    assert len(options["categories"]) >= 4, "Thiếu danh mục sản phẩm"
    assert "SP" in options["states"], "Thiếu bang SP trong danh sách states"
    assert "delivered" in options["statuses"], "Thiếu trạng thái delivered trong statuses"


def test_filtered_orders_by_date_range(mini_db):
    """Kiểm tra lọc đơn hàng theo khoảng ngày (start_date -> end_date)."""
    if not callable(get_filtered_orders):
        pytest.fail("Hàm get_filtered_orders chưa được định nghĩa trong src/db.py (Lỗi Code)")

    # Trong mini_db: order_1 (2017-01-10) và order_2 (2017-02-15) nằm trong tháng 1-2/2017
    df = get_filtered_orders(start_date="2017-01-01", end_date="2017-02-28")
    assert isinstance(df, pd.DataFrame), "Kết quả phải là pandas DataFrame"
    assert len(df) == 2, f"Kỳ vọng 2 đơn trong khoảng 01/2017 - 02/2017 nhưng nhận được {len(df)}"


def test_filtered_orders_by_category(mini_db):
    """Kiểm tra lọc theo danh mục sản phẩm."""
    if not callable(get_filtered_orders):
        pytest.fail("Hàm get_filtered_orders chưa được định nghĩa trong src/db.py (Lỗi Code)")

    # Trong mini_db: order_1 và order_5 chứa sản phẩm p1 (telefonia)
    df = get_filtered_orders(categories=["telefonia"])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2, f"Kỳ vọng 2 đơn có danh mục 'telefonia', nhận được {len(df)}"


def test_filtered_orders_by_state(mini_db):
    """Kiểm tra lọc theo bang/khu vực khách hàng."""
    if not callable(get_filtered_orders):
        pytest.fail("Hàm get_filtered_orders chưa được định nghĩa trong src/db.py (Lỗi Code)")

    # Trong mini_db: order_1 (c1) và order_3 (c3) đều thuộc bang SP
    df = get_filtered_orders(states=["SP"])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2, f"Kỳ vọng 2 đơn thuộc bang SP, nhận được {len(df)}"


def test_filtered_orders_by_status(mini_db):
    """Kiểm tra lọc theo trạng thái đơn hàng."""
    if not callable(get_filtered_orders):
        pytest.fail("Hàm get_filtered_orders chưa được định nghĩa trong src/db.py (Lỗi Code)")

    # Trong mini_db: order_7 có trạng thái canceled
    df = get_filtered_orders(statuses=["canceled"])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1, f"Kỳ vọng 1 đơn có status 'canceled', nhận được {len(df)}"


def test_filtered_orders_combined(mini_db):
    """Kiểm tra kết hợp đồng thời nhiều bộ lọc (Ngày + Danh mục + Bang + Trạng thái)."""
    if not callable(get_filtered_orders):
        pytest.fail("Hàm get_filtered_orders chưa được định nghĩa trong src/db.py (Lỗi Code)")

    # order_1: 2017-01-10, telefonia, SP, delivered
    df = get_filtered_orders(
        start_date="2017-01-01",
        end_date="2017-01-31",
        categories=["telefonia"],
        states=["SP"],
        statuses=["delivered"]
    )
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1, f"Kỳ vọng đúng 1 đơn khớp tất cả các bộ lọc, nhận được {len(df)}"


def test_filtered_orders_zero_results(mini_db):
    """Khi lọc ra 0 dòng: không raise ngoại lệ, trả về DataFrame rỗng hợp lệ."""
    if not callable(get_filtered_orders):
        pytest.fail("Hàm get_filtered_orders chưa được định nghĩa trong src/db.py (Lỗi Code)")

    # Bang 'ZZ' không tồn tại trong CSDL
    df = get_filtered_orders(states=["ZZ"])
    assert isinstance(df, pd.DataFrame), "Vẫn phải trả về DataFrame khi không có dữ liệu"
    assert len(df) == 0, f"Kỳ vọng 0 dòng khi lọc bang không tồn tại, nhận được {len(df)}"


def test_filter_start_date_greater_than_end_date(mini_db):
    """Trường hợp start_date > end_date phải được xử lý hợp lý (trả về 0 dòng hoặc raise ValueError)."""
    if not callable(get_filtered_orders):
        pytest.fail("Hàm get_filtered_orders chưa được định nghĩa trong src/db.py (Lỗi Code)")

    try:
        df = get_filtered_orders(start_date="2017-12-31", end_date="2017-01-01")
        assert len(df) == 0, "Nếu không raise lỗi thì phải trả về 0 dòng khi ngày bắt đầu > ngày kết thúc"
    except ValueError:
        pass  # Xử lý raise ValueError có kiểm soát là hoàn toàn hợp lệ


def test_sql_injection_prevention(mini_db):
    """
    Kiểm tra phòng chống tấn công SQL Injection:
    Truyền chuỗi độc hại qua danh mục, bảng orders vẫn phải an toàn và kết quả trả về 0 dòng.
    """
    if not callable(get_filtered_orders):
        pytest.fail("Hàm get_filtered_orders chưa được định nghĩa trong src/db.py (Lỗi Code)")

    malicious_input = "'; DROP TABLE orders; --"
    df = get_filtered_orders(categories=[malicious_input])
    assert len(df) == 0, "Dữ liệu tiêm mã độc phải trả về 0 dòng"

    # Kiểm tra bảng orders vẫn tồn tại nguyên vẹn trong CSDL
    conn = sqlite3.connect(mini_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders';")
    table = cursor.fetchone()
    conn.close()
    assert table is not None, "Bảng orders đã bị ảnh hưởng/xóa do lỗi SQL Injection!"


def test_get_filtered_orders_dataframe_structure(mini_db):
    """Kiểm tra cấu trúc các cột của DataFrame trả về từ get_filtered_orders()."""
    if not callable(get_filtered_orders):
        pytest.fail("Hàm get_filtered_orders chưa được định nghĩa trong src/db.py (Lỗi Code)")

    df = get_filtered_orders()
    assert isinstance(df, pd.DataFrame)
    required_cols = ["order_id", "order_status", "order_purchase_timestamp"]
    for col in required_cols:
        assert col in df.columns, f"DataFrame trả về thiếu cột bắt buộc '{col}'"
