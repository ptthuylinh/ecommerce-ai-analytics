"""
Bộ kiểm thử đơn vị cho module nhãn và bản địa hóa src/ui/labels.py.
Kiểm tra tính chính xác của state_label, category_label, định dạng KPI và delta.
"""

import pytest
from src.ui.labels import (
    STATE_NAMES,
    STATE_ORDER,
    CATEGORY_VI,
    CATEGORY_ORDER,
    state_label,
    category_label,
    format_kpi_value,
    format_kpi_delta,
    check_prev_period_valid,
    format_currency_full,
)


def test_state_label_standard():
    """Kiểm tra state_label('SP') trả về đúng định dạng 'São Paulo (SP)'."""
    assert state_label("SP") == "São Paulo (SP)"
    assert state_label("RJ") == "Rio de Janeiro (RJ)"
    assert state_label("MG") == "Minas Gerais (MG)"
    assert state_label("sp") == "São Paulo (SP)"


def test_state_label_unknown_code_no_error():
    """Kiểm tra mã bang lạ hoặc rỗng không gây lỗi và trả về fallback hợp lý."""
    assert state_label("XX") == "XX"
    assert state_label("UNKNOWN") == "UNKNOWN"
    assert state_label("123") == "123"
    assert state_label("") == ""
    assert state_label(None) == ""


def test_state_names_all_27_brazil_states():
    """Đảm bảo định nghĩa đầy đủ 27 bang/khu vực của Brazil."""
    assert len(STATE_NAMES) == 27
    expected_states = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA",
        "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO",
    }
    assert set(STATE_NAMES.keys()) == expected_states
    assert len(STATE_ORDER) == 27
    assert set(STATE_ORDER) == expected_states


def test_category_label_known():
    """Kiểm tra category_label cho các danh mục phổ biến có bản dịch tiếng Việt."""
    assert category_label("health_beauty") == "Sức khỏe & Làm đẹp"
    assert category_label("watches_gifts") == "Đồng hồ & Quà tặng"
    assert category_label("bed_bath_table") == "Đồ dùng phòng ngủ & phòng tắm"
    assert category_label("sports_leisure") == "Thể thao & Dã ngoại"
    assert category_label("computers_accessories") == "Máy tính & Phụ kiện"


def test_category_label_fallback():
    """
    Kiểm tra fallback của category_label:
    Khi gặp mã danh mục chưa có trong từ điển tiếng Việt, hiển thị 'Khác (<mã>)'.
    Khi gặp mã rỗng hoặc None, hiển thị 'Chưa phân loại'.
    """
    assert category_label("unknown_category") == "Khác (unknown_category)"
    assert category_label("fashion_special_accessories") == "Khác (fashion_special_accessories)"
    assert category_label("my_new_product") == "Khác (my_new_product)"
    assert category_label("") == "Chưa phân loại"
    assert category_label(None) == "Chưa phân loại"
    assert category_label("nan") == "Chưa phân loại"


def test_category_vi_contains_at_least_30_categories():
    """Đảm bảo CATEGORY_VI có ít nhất 30 danh mục có doanh thu dẫn đầu từ CSDL."""
    assert len(CATEGORY_VI) >= 30
    for key, val in CATEGORY_VI.items():
        assert isinstance(key, str) and len(key) > 0
        assert isinstance(val, str) and len(val) > 0


def test_portuguese_category_fallback_or_mapping():
    """Kiểm tra category_label xử lý an toàn khi truyền mã gốc tiếng Bồ Đào Nha."""
    assert category_label("beleza_saude") == "Sức khỏe & Làm đẹp"
    res = category_label("categoria_desconhecida")
    assert res == "Khác (categoria_desconhecida)"


# ==============================================================================
# KIỂM THỬ ĐỊNH DẠNG GIÁ TRỊ KPI VÀ DELTA
# ==============================================================================

def test_format_kpi_value():
    """Kiểm tra định dạng giá trị hiển thị: số tiền triệu, điểm đánh giá, % đúng hạn."""
    # Doanh thu >= 1 triệu hiển thị 'R$ 15,4 triệu' (dấu phẩy)
    assert format_kpi_value("total_revenue", 15_400_000) == "R$ 15,4 triệu"
    assert format_kpi_value("total_revenue", 15_329_289) == "R$ 15,3 triệu"
    assert format_kpi_value("total_revenue", 500_000) == "R$ 500,000"

    # Điểm đánh giá hiển thị '4,16'
    assert format_kpi_value("avg_review_score", 4.156) == "4,16"
    assert format_kpi_value("avg_review_score", 4.0) == "4,00"

    # Tỷ lệ đúng hạn
    assert format_kpi_value("on_time_rate", 93.2) == "93,2%"

    # AOV
    assert format_kpi_value("avg_order_value", 159.8) == "R$ 159,8"

    # Đơn hàng và khách hàng
    assert format_kpi_value("total_orders", 96211) == "96,211"
    assert format_kpi_value("total_customers", 93104) == "93,104"


def test_format_currency_full():
    """Kiểm tra định dạng số tiền đầy đủ (help tooltip) theo chuẩn Việt Nam/Brazil."""
    assert format_currency_full(15_329_289.43) == "R$ 15.329.289,43"
    assert format_currency_full(159.8) == "R$ 159,80"
    assert format_currency_full(0) == "R$ 0,00"
    assert format_currency_full(None) == "—"


def test_format_kpi_delta_positive():
    """Kiểm tra delta dương: doanh thu/đơn/khách/AOV theo %, điểm số tuyệt đối, đúng hạn điểm %."""
    # Doanh thu / Đơn / Khách / AOV: %
    assert format_kpi_delta("total_revenue", 120_000, 100_000) == "+20,0%"
    assert format_kpi_delta("total_orders", 1500, 1000) == "+50,0%"
    assert format_kpi_delta("total_customers", 1050, 1000) == "+5,0%"
    assert format_kpi_delta("avg_order_value", 165.0, 150.0) == "+10,0%"

    # Điểm đánh giá: Điểm tuyệt đối
    assert format_kpi_delta("avg_review_score", 4.16, 4.01) == "+0,15"

    # Tỷ lệ đúng hạn: Điểm phần trăm
    assert format_kpi_delta("on_time_rate", 95.5, 93.2) == "+2,3 %p"


def test_format_kpi_delta_negative():
    """Kiểm tra delta âm: có dấu trừ '-' rõ ràng."""
    # Doanh thu / Đơn: % âm
    assert format_kpi_delta("total_revenue", 80_000, 100_000) == "-20,0%"
    assert format_kpi_delta("total_orders", 900, 1000) == "-10,0%"

    # Điểm đánh giá: Điểm tuyệt đối âm
    assert format_kpi_delta("avg_review_score", 3.90, 4.10) == "-0,20"

    # Tỷ lệ đúng hạn: Điểm phần trăm âm
    assert format_kpi_delta("on_time_rate", 90.0, 93.5) == "-3,5 %p"


def test_format_kpi_delta_prev_zero():
    """Kiểm tra kỳ trước = 0 trả về '—' để tránh chia cho 0."""
    assert format_kpi_delta("total_revenue", 100_000, 0) == "—"
    assert format_kpi_delta("total_orders", 50, 0) == "—"
    assert format_kpi_delta("avg_review_score", 4.0, 0) == "—"


def test_format_kpi_delta_invalid_prev():
    """Kiểm tra khi kỳ trước không đủ dữ liệu (is_valid_prev=False) thì trả về '—'."""
    assert format_kpi_delta("total_revenue", 120_000, 100_000, is_valid_prev=False) == "—"
    assert format_kpi_delta("avg_review_score", 4.16, 4.01, is_valid_prev=False) == "—"
    assert format_kpi_delta("on_time_rate", 95.0, 93.0, is_valid_prev=False) == "—"


def test_check_prev_period_valid():
    """Kiểm tra hàm kiểm tra tính hợp lệ của kỳ trước."""
    # Khoảng mặc định (2017-01-01 -> 2018-08-31): kỳ trước rơi vào 2015-2016 -> Không hợp lệ
    filters_default = {"start_date": "2017-01-01", "end_date": "2018-08-31"}
    kpi_prev_mock = {"total_orders": 95000}
    assert check_prev_period_valid(filters_default, kpi_prev_mock) is False

    # Khoảng 6 tháng năm 2018 (2018-01-01 -> 2018-06-30): kỳ trước 2017-07-04 -> 2017-12-31 >= 2017-01-01
    filters_valid = {"start_date": "2018-01-01", "end_date": "2018-06-30"}
    kpi_prev_valid = {"total_orders": 15000}
    assert check_prev_period_valid(filters_valid, kpi_prev_valid) is True

    # Kỳ trước có dưới 100 đơn -> Không hợp lệ
    kpi_prev_small = {"total_orders": 99}
    assert check_prev_period_valid(filters_valid, kpi_prev_small) is False

    # Filters hoặc kpi_prev rỗng -> Không hợp lệ
    assert check_prev_period_valid(None, kpi_prev_valid) is False
    assert check_prev_period_valid(filters_valid, None) is False

    # Hỗ trợ pd.Series (thực tế từ kpi_previous_period) không bị lỗi ambiguous truth value
    import pandas as pd
    series_valid = pd.Series({"total_orders": 15000, "total_revenue": 200000.0})
    assert check_prev_period_valid(filters_valid, series_valid) is True

    series_invalid_orders = pd.Series({"total_orders": 50})
    assert check_prev_period_valid(filters_valid, series_invalid_orders) is False


@pytest.mark.integration
def test_all_db_categories_translated():
    """
    Test tích hợp: Mọi danh mục DISTINCT trong CSDL ecommerce.db (cả cột tiếng Anh
    lẫn cột gốc tiếng Bồ Đào Nha thực sự dùng làm giá trị lọc) đều có trong CATEGORY_VI,
    nếu thiếu sẽ fail và liệt kê rõ các mã còn thiếu.
    Hàm category_label(x) không chứa bất kỳ dấu gạch dưới nào và không rơi vào fallback 'Khác (...)'.
    """
    import os
    import sqlite3

    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/ecommerce.db"))
    if not os.path.exists(db_path):
        pytest.skip(f"Database không tồn tại: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # 1. Lấy DISTINCT mọi mã danh mục từ cả 2 cột (cột tiếng Anh và cột gốc tiếng Bồ Đào Nha)
    cur.execute("""
        SELECT DISTINCT product_category_name_english
        FROM products
        WHERE product_category_name_english IS NOT NULL AND product_category_name_english != ''
    """)
    en_cats = {r[0] for r in cur.fetchall() if r[0]}

    cur.execute("""
        SELECT DISTINCT product_category_name
        FROM products
        WHERE product_category_name IS NOT NULL AND product_category_name != ''
    """)
    pt_cats = {r[0] for r in cur.fetchall() if r[0]}
    conn.close()

    all_db_cats = sorted(en_cats.union(pt_cats))
    assert len(all_db_cats) > 0, "Không có danh mục nào trong CSDL"

    # 2. Mọi mã trong DB đều có trong CATEGORY_VI (test fail liệt kê mã thiếu)
    missing = [c for c in all_db_cats if c not in CATEGORY_VI]
    assert not missing, f"Các mã danh mục trong DB còn thiếu trong CATEGORY_VI ({len(missing)} mã): {missing}"

    # 3. category_label(x) không chứa dấu gạch dưới và không bị rơi vào fallback "Khác (<mã>)"
    for c in all_db_cats:
        label = category_label(c)
        assert "_" not in label, f"Nhãn vẫn chứa dấu gạch dưới: {c} -> {label}"
        assert not label.startswith("Khác ("), f"Nhãn bị rơi vào fallback: {c} -> {label}"
        assert label != "Chưa phân loại", f"Danh mục hợp lệ không được là 'Chưa phân loại': {c}"

    # 4. Giá trị rỗng và None trả về 'Chưa phân loại'
    assert category_label(None) == "Chưa phân loại"
    assert category_label("") == "Chưa phân loại"
    assert category_label("nan") == "Chưa phân loại"

    # 5. Mã không tồn tại trong từ điển phải rơi vào fallback "Khác (<mã>)"
    assert category_label("ma_chua_dich_xyz") == "Khác (ma_chua_dich_xyz)"

