import os
import sys
import pytest

# Thêm thư mục gốc vào path để import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.db import get_connection, get_kpi_metrics

def test_database_connection():
    """Kiểm tra kết nối tới cơ sở dữ liệu SQLite"""
    conn = get_connection()
    assert conn is not None
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # Kiểm tra xem các bảng quan trọng có tồn tại không
    assert 'orders' in tables
    assert 'order_payments' in tables

def test_kpi_metrics_output():
    """Kiểm tra hàm get_kpi_metrics có trả về số liệu hợp lệ không"""
    kpi = get_kpi_metrics()
    assert kpi['total_orders'] > 0
    assert kpi['total_revenue'] > 0
    assert 1.0 <= kpi['avg_review_score'] <= 5.0