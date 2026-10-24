"""
Kiểm thử tích hợp (Integration Tests) đối chiếu tính chính xác giữa
các hàm phân tích in-memory của src/analytics.py và các truy vấn SQL của src/db.py
với 3 bộ lọc đa chiều khác nhau.
"""

import os
import pytest
import numpy as np
from pandas.testing import assert_frame_equal, assert_series_equal

import src.db as db
import src.analytics as an

pytestmark = pytest.mark.integration

REAL_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/ecommerce.db"))


@pytest.fixture(scope="module", autouse=True)
def setup_db_path():
    if not os.path.exists(REAL_DB_PATH):
        pytest.skip(f"Bỏ qua integration test: Không tìm thấy database thật tại {REAL_DB_PATH}")

    old_env = os.environ.get("ECOMMERCE_DB_PATH")
    os.environ["ECOMMERCE_DB_PATH"] = REAL_DB_PATH
    yield
    if old_env is not None:
        os.environ["ECOMMERCE_DB_PATH"] = old_env
    else:
        os.environ.pop("ECOMMERCE_DB_PATH", None)


@pytest.fixture(scope="module")
def loaded_facts():
    """Nạp facts một lần duy nhất cho toàn bộ module test."""
    orders_fact = an.load_orders_fact(REAL_DB_PATH)
    items_fact = an.load_items_fact(REAL_DB_PATH)
    return orders_fact, items_fact


# 3 Bộ lọc đa chiều khác nhau để đối chiếu toàn diện
FILTERS_CASES = [
    # 1. Bộ lọc mặc định (Toàn bộ 2017-01 đến 2018-08, status='delivered')
    {
        "start_date": "2017-01-01",
        "end_date": "2018-08-31",
        "statuses": ["delivered"],
    },
    # 2. Bộ lọc theo Bang và khoảng ngày trung hạn
    {
        "start_date": "2017-06-01",
        "end_date": "2018-02-28",
        "states": ["SP", "RJ", "MG"],
        "statuses": ["delivered"],
    },
    # 3. Bộ lọc theo Danh mục sản phẩm và trạng thái
    {
        "start_date": "2017-03-01",
        "end_date": "2018-05-31",
        "categories": ["health_beauty", "watches_gifts"],
        "statuses": ["delivered"],
    },
]


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_kpi_extended_vs_sql(loaded_facts, filters):
    orders_fact, _ = loaded_facts
    df_f = an.apply_filters(orders_fact, filters, db_path=REAL_DB_PATH)

    sql_kpi = db.get_kpi_extended(filters)
    pan_kpi = an.kpi_extended(df_f)

    assert_series_equal(sql_kpi, pan_kpi, check_dtype=False, check_exact=False, rtol=1e-3, atol=1e-2)


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_monthly_revenue_vs_sql(loaded_facts, filters):
    orders_fact, _ = loaded_facts
    df_f = an.apply_filters(orders_fact, filters, db_path=REAL_DB_PATH)

    sql_monthly = db.get_monthly_revenue(filters)
    pan_monthly = an.monthly_revenue(df_f)

    assert_frame_equal(sql_monthly, pan_monthly, check_dtype=False, check_exact=False, rtol=1e-3, atol=1e-2)


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_delay_vs_review_vs_sql(loaded_facts, filters):
    orders_fact, _ = loaded_facts
    df_f = an.apply_filters(orders_fact, filters, db_path=REAL_DB_PATH)

    sql_delay = db.get_delay_vs_review(filters)
    pan_delay = an.delay_vs_review(df_f)

    assert_frame_equal(sql_delay, pan_delay, check_dtype=False, check_exact=False, rtol=1e-3, atol=1e-2)


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_revenue_by_state_vs_sql(loaded_facts, filters):
    orders_fact, _ = loaded_facts
    df_f = an.apply_filters(orders_fact, filters, db_path=REAL_DB_PATH)

    sql_state = db.get_revenue_by_state(filters)
    pan_state = an.revenue_by_state(df_f)

    assert_frame_equal(sql_state, pan_state, check_dtype=False, check_exact=False, rtol=1e-3, atol=1e-2)


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_repeat_customer_rate_vs_sql(loaded_facts, filters):
    orders_fact, _ = loaded_facts
    df_f = an.apply_filters(orders_fact, filters, db_path=REAL_DB_PATH)

    sql_rep = db.get_repeat_customer_rate(filters)
    pan_rep = an.repeat_customer_rate(df_f)

    assert np.isclose(sql_rep, pan_rep, atol=0.05)


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_orders_heatmap_vs_sql(loaded_facts, filters):
    orders_fact, _ = loaded_facts
    df_f = an.apply_filters(orders_fact, filters, db_path=REAL_DB_PATH)

    sql_heat = db.get_orders_heatmap(filters)
    pan_heat = an.orders_heatmap(df_f)

    assert_frame_equal(sql_heat, pan_heat, check_dtype=False, check_exact=False)


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_top_categories_vs_sql(loaded_facts, filters):
    _, items_fact = loaded_facts
    df_if = an.apply_filters(items_fact, filters, db_path=REAL_DB_PATH)

    sql_cat = db.get_top_categories(10, filters)
    pan_cat = an.top_categories(df_if, 10)

    assert_frame_equal(sql_cat, pan_cat, check_dtype=False, check_exact=False, rtol=1e-3, atol=1e-2)


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_kpi_previous_period_vs_sql(loaded_facts, filters):
    orders_fact, _ = loaded_facts

    sql_kpi_prev = db.get_kpi_previous_period(filters)
    pan_kpi_prev = an.kpi_previous_period(orders_fact, filters, db_path=REAL_DB_PATH)

    assert_series_equal(sql_kpi_prev, pan_kpi_prev, check_dtype=False, check_exact=False, rtol=1e-3, atol=1e-2)


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_review_distribution_vs_sql(loaded_facts, filters):
    orders_fact, _ = loaded_facts
    df_f = an.apply_filters(orders_fact, filters, db_path=REAL_DB_PATH)

    sql_rev = db.get_review_distribution(filters)
    pan_rev = an.review_distribution(df_f)

    # Chênh lệch < 1.5% do orders_fact gộp review theo đơn (AVG) tránh fan-out
    assert_frame_equal(sql_rev, pan_rev, check_dtype=False, check_exact=False, rtol=0.02, atol=100)


@pytest.mark.parametrize("filters", FILTERS_CASES)
def test_payment_mix_vs_sql(loaded_facts, filters):
    orders_fact, _ = loaded_facts
    df_f = an.apply_filters(orders_fact, filters, db_path=REAL_DB_PATH)

    sql_pay = db.get_payment_mix(filters)
    pan_pay = an.payment_mix(df_f)

    # Thứ tự phương thức thanh toán phải khớp
    assert list(sql_pay["payment_type"]) == list(pan_pay["payment_type"])
    # Tỷ lệ percentage khớp trong khoảng 0.5%
    np.testing.assert_allclose(sql_pay["percentage"].values, pan_pay["percentage"].values, atol=0.5)

