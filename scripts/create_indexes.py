"""
Script tao Index cho co so du lieu SQLite data/ecommerce.db.
Toi uu hoa toc do truy van va join bang cho ung dung E-Commerce Analytics.
"""

import os
import sys
import time
import sqlite3

# Dam bao terminal Windows ho tro in ky tu an toan
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Them thu muc goc cua project vao sys.path de import module tu src
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.db import get_kpi_metrics  # noqa: E402

DB_PATH = os.path.join(PROJECT_ROOT, "data", "ecommerce.db")

# Danh sach cac index can tao theo dung schema that
INDEX_DEFINITIONS = [
    # orders: customer_id, order_status, order_purchase_timestamp
    ("idx_orders_customer_id", "orders", "customer_id"),
    ("idx_orders_order_status", "orders", "order_status"),
    ("idx_orders_order_purchase_timestamp", "orders", "order_purchase_timestamp"),

    # order_items: order_id, product_id
    ("idx_order_items_order_id", "order_items", "order_id"),
    ("idx_order_items_product_id", "order_items", "product_id"),

    # order_payments: order_id
    ("idx_order_payments_order_id", "order_payments", "order_id"),

    # order_reviews: order_id
    ("idx_order_reviews_order_id", "order_reviews", "order_id"),

    # customers: customer_state
    ("idx_customers_customer_state", "customers", "customer_state"),

    # products: product_category_name
    ("idx_products_product_category_name", "products", "product_category_name"),
]


def drop_indexes_if_exist():
    """Tam thoi go bo index neu da ton tai de do luong chinh xac trang thai truoc index."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Khong tim thay file database tai: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for idx_name, _, _ in INDEX_DEFINITIONS:
        cursor.execute(f"DROP INDEX IF EXISTS {idx_name};")
    conn.commit()
    cursor.execute("ANALYZE;")
    conn.commit()
    conn.close()


def measure_kpi_performance(label: str):
    """Do thoi gian thuc thi cua ham get_kpi_metrics() va in ket qua."""
    print(f"\n[*] Dang do thoi gian thuc thi get_kpi_metrics() [{label}]...")
    start_time = time.perf_counter()
    kpi_result = get_kpi_metrics()
    duration = time.perf_counter() - start_time
    print(f"    -> Thoi gian thuc thi: {duration:.4f} giay")
    return duration, kpi_result


def create_indexes():
    """Tao cac Index neu chua ton tai va chay ANALYZE cap nhat Query Planner."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Khong tim thay file database tai: {DB_PATH}")

    print(f"\n[+] Ket noi toi CSDL: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n[+] Bat dau tao cac Index (CREATE INDEX IF NOT EXISTS):")
    for idx_name, table_name, column_name in INDEX_DEFINITIONS:
        sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({column_name});"
        cursor.execute(sql)
        print(f"    [OK] {idx_name} -> {table_name}({column_name})")

    conn.commit()

    print("\n[*] Dang thuc thi ANALYZE de toi uu hoa bo lap lich truy van (Query Planner)...")
    cursor.execute("ANALYZE;")
    conn.commit()
    print("    [OK] ANALYZE hoan tat!")

    conn.close()


def main():
    print("=" * 65)
    print("BAT DAU QUY TRINH TOI UU HOA INDEX CHO ECOMMERCE DATABASE")
    print("=" * 65)

    # 1. Chuan bi do luong truoc khi co index (go bo index neu co de so sanh chuan xac)
    drop_indexes_if_exist()
    time_before, kpi_before = measure_kpi_performance("TRUOC KHI TAO INDEX")

    # 2. Tao index va chay ANALYZE
    create_indexes()

    # 3. Do thoi gian sau khi tao index
    time_after, kpi_after = measure_kpi_performance("SAU KHI TAO INDEX")

    # 4. Hien thi bang tong ket so sanh
    speedup = time_before / time_after if time_after > 0 else 0
    percent_reduction = ((time_before - time_after) / time_before * 100) if time_before > 0 else 0

    print("\n" + "=" * 65)
    print("BAO CAO KET QUA TOI UU HOA HIEU NANG")
    print("=" * 65)
    print(f"Thoi gian TRUOC khi co Index : {time_before:.4f} giay")
    print(f"Thoi gian SAU khi co Index    : {time_after:.4f} giay")
    print(f"Toc do cai thien             : nhanh hon {speedup:.2f}x (giam {percent_reduction:.1f}% thoi gian)")
    print("-" * 65)
    print("Xac thuc tinh toan ven du lieu (KPI Metrics):")
    print(f"    - Tong don hang thanh cong : {int(kpi_after['total_orders']):,} (Khop: {kpi_before['total_orders'] == kpi_after['total_orders']})")
    print(f"    - Tong doanh thu           : R$ {kpi_after['total_revenue']:,.2f} (Khop: {kpi_before['total_revenue'] == kpi_after['total_revenue']})")
    print(f"    - Diem danh gia trung binh : {kpi_after['avg_review_score']} (Khop: {kpi_before['avg_review_score'] == kpi_after['avg_review_score']})")
    print(f"    - Tong khach hang mua sam  : {int(kpi_after['total_customers']):,} (Khop: {kpi_before['total_customers'] == kpi_after['total_customers']})")
    print("=" * 65)


if __name__ == "__main__":
    main()
