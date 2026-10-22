"""
Bộ kiểm thử tích hợp (Integration Test) chạy trên cơ sở dữ liệu thật data/ecommerce.db.
Được đánh dấu bằng marker @pytest.mark.integration.
"""

import os
import sqlite3
import pytest
import pandas as pd
import src.db
from src.db import get_kpi_metrics, get_monthly_revenue

pytestmark = pytest.mark.integration

REAL_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/ecommerce.db"))


@pytest.fixture(autouse=True)
def ensure_real_db():
    """Đảm bảo src.db sử dụng database thật và bỏ qua test nếu file không tồn tại."""
    if not os.path.exists(REAL_DB_PATH):
        pytest.skip(f"Bỏ qua integration test: Không tìm thấy file {REAL_DB_PATH}")

    old_path = getattr(src.db, "DB_PATH", None)
    old_env_db = os.environ.get("DB_PATH")
    old_env_eco = os.environ.get("ECOMMERCE_DB_PATH")

    src.db.DB_PATH = REAL_DB_PATH
    os.environ["DB_PATH"] = REAL_DB_PATH
    os.environ["ECOMMERCE_DB_PATH"] = REAL_DB_PATH

    yield

    if old_path is not None:
        src.db.DB_PATH = old_path
    if old_env_db is not None:
        os.environ["DB_PATH"] = old_env_db
    else:
        os.environ.pop("DB_PATH", None)
    if old_env_eco is not None:
        os.environ["ECOMMERCE_DB_PATH"] = old_env_eco
    else:
        os.environ.pop("ECOMMERCE_DB_PATH", None)


def test_compare_kpi_with_independent_subquery():
    """
    Đối chiếu get_kpi_metrics() với một truy vấn SQL độc lập (viết bằng CTE/subquery
    gộp payments và reviews trước khi JOIN). Hai kết quả phải khớp nhau hoàn toàn.
    """
    conn = sqlite3.connect(REAL_DB_PATH)
    independent_query = """
    WITH p AS (
        SELECT order_id, SUM(payment_value) as order_payment
        FROM order_payments
        GROUP BY order_id
    ),
    r AS (
        SELECT order_id, SUM(review_score) as sum_review, COUNT(review_score) as count_review
        FROM order_reviews
        GROUP BY order_id
    )
    SELECT
        COUNT(DISTINCT o.order_id) as total_orders,
        ROUND(SUM(p.order_payment), 2) as total_revenue,
        ROUND(SUM(r.sum_review) * 1.0 / NULLIF(SUM(r.count_review), 0), 2) as avg_review_score,
        COUNT(DISTINCT c.customer_unique_id) as total_customers
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN p ON o.order_id = p.order_id
    LEFT JOIN r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered';
    """
    df_expected = pd.read_sql_query(independent_query, conn)
    conn.close()
    expected = df_expected.iloc[0]

    kpi = get_kpi_metrics()

    assert kpi["total_orders"] == expected["total_orders"], "Lệch tổng số đơn hàng"
    assert abs(kpi["total_revenue"] - expected["total_revenue"]) < 0.01, (
        f"Doanh thu bị lệch! KPI trả về {kpi['total_revenue']:,.2f}, "
        f"nhưng truy vấn độc lập ra {expected['total_revenue']:,.2f}."
    )
    assert abs(kpi["avg_review_score"] - expected["avg_review_score"]) < 0.01, "Lệch điểm review trung bình"
    assert kpi["total_customers"] == expected["total_customers"], "Lệch tổng số khách hàng"


def test_total_customers_less_than_total_orders():
    """
    Trên tập dữ liệu thương mại điện tử thật, luôn có tỷ lệ khách hàng mua lại (repeat customers).
    Do đó tổng số khách hàng duy nhất (customer_unique_id) bắt buộc phải NHỎ HƠN tổng số đơn hàng.
    """
    kpi = get_kpi_metrics()
    assert kpi["total_customers"] < kpi["total_orders"], (
        f"Kỳ vọng total_customers < total_orders, nhưng thực tế: "
        f"total_customers={kpi['total_customers']} và total_orders={kpi['total_orders']}."
    )


def test_monthly_revenue_sum_matches_kpi_total():
    """
    Tổng doanh thu lũy kế các tháng từ get_monthly_revenue() phải khớp với total_revenue của KPI.
    """
    df_monthly = get_monthly_revenue()
    monthly_sum = round(df_monthly["revenue"].sum(), 2)
    kpi = get_kpi_metrics()

    assert abs(monthly_sum - kpi["total_revenue"]) < 0.01, (
        f"Tổng doanh thu theo tháng ({monthly_sum:,.2f}) không khớp với KPI total_revenue ({kpi['total_revenue']:,.2f})."
    )
