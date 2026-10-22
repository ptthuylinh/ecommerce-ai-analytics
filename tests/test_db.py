"""
Smoke test cơ bản kiểm tra kết nối CSDL và định dạng output của get_kpi_metrics.
"""

from src.db import get_connection, get_kpi_metrics


def test_database_connection(mini_db):
    """Kiểm tra kết nối tới cơ sở dữ liệu SQLite và sự tồn tại của các bảng chính."""
    conn = get_connection()
    assert conn is not None
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "orders" in tables
    assert "order_payments" in tables
    assert "order_items" in tables
    assert "products" in tables
    assert "customers" in tables
    assert "order_reviews" in tables


def test_kpi_metrics_output(mini_db):
    """Kiểm tra hàm get_kpi_metrics trả về số liệu dương hợp lệ."""
    kpi = get_kpi_metrics()
    assert kpi["total_orders"] > 0
    assert kpi["total_revenue"] > 0
    assert 1.0 <= kpi["avg_review_score"] <= 5.0
