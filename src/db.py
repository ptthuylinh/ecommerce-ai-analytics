import sqlite3
import pandas as pd
import os

# Đường dẫn tự động tìm tới file database ecommerce.db
DB_PATH = os.path.join(os.path.dirname(__file__), '../data/ecommerce.db')

def get_connection():
    """Tạo kết nối tới SQLite Database"""
    return sqlite3.connect(DB_PATH)

def get_kpi_metrics():
    """Lấy 4 chỉ số KPI tổng quan cho Dashboard"""
    conn = get_connection()
    query = """
    SELECT 
        COUNT(DISTINCT o.order_id) as total_orders,
        SUM(p.payment_value) as total_revenue,
        ROUND(AVG(r.review_score), 2) as avg_review_score,
        COUNT(DISTINCT o.customer_id) as total_customers
    FROM orders o
    JOIN order_payments p ON o.order_id = p.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered';
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.iloc[0]

def get_monthly_revenue():
    """Lấy xu hướng doanh thu theo tháng"""
    conn = get_connection()
    query = """
    SELECT 
        strftime('%Y-%m', o.order_purchase_timestamp) as month,
        ROUND(SUM(p.payment_value), 2) as revenue,
        COUNT(DISTINCT o.order_id) as orders_count
    FROM orders o
    JOIN order_payments p ON o.order_id = p.order_id
    WHERE o.order_status = 'delivered' 
      AND o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <= '2018-08-31'
    GROUP BY month
    ORDER BY month;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_top_categories(top_n=10):
    """Lấy top danh mục sản phẩm có doanh thu cao nhất"""
    conn = get_connection()
    query = f"""
    SELECT 
        pr.product_category_name_english as category,
        ROUND(SUM(i.price), 2) as total_sales,
        COUNT(i.order_item_id) as items_sold
    FROM order_items i
    JOIN products pr ON i.product_id = pr.product_id
    JOIN orders o ON i.order_id = o.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY category
    ORDER BY total_sales DESC
    LIMIT {top_n};
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df