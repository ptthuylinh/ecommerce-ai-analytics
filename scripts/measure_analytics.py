"""
Script đo thời gian nạp dữ liệu lần đầu và thời gian mỗi lần đổi bộ lọc
của src/analytics.py, lấy trung bình 5 lần chạy.
"""

import sys
import os
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Tắt cache của Streamlit khi đo cold load thực tế nếu cần, hoặc gọi hàm gốc không cache
import src.analytics as an

def measure():
    filters = {
        "start_date": "2017-01-01",
        "end_date": "2018-08-31",
        "statuses": ["delivered"],
    }

    print("\n--- 1. Đo thời gian nạp dữ liệu lần đầu (cold load từ SQLite vào DataFrame) ---")
    cold_load_times = []
    # Đo 5 lần nạp từ database (bằng cách xóa cache hoặc unwrap function)
    for i in range(5):
        # Streamlit cached func has .clear()
        if hasattr(an.load_orders_fact, "clear"):
            an.load_orders_fact.clear()
        if hasattr(an.load_items_fact, "clear"):
            an.load_items_fact.clear()
        
        t0 = time.perf_counter()
        orders_df = an.load_orders_fact()
        items_df = an.load_items_fact()
        t1 = time.perf_counter()
        elapsed = t1 - t0
        cold_load_times.append(elapsed)
        print(f"Lần {i+1}: {elapsed:.4f} s (orders: {len(orders_df):,}, items: {len(items_df):,})")

    avg_cold_load = sum(cold_load_times) / len(cold_load_times)
    print(f"Trung bình 5 lần nạp lần đầu: {avg_cold_load:.4f} s\n")

    print("--- 2. Đo thời gian mỗi lần đổi bộ lọc (apply_filters + 10 hàm tính toán) ---")
    # Dữ liệu đã có trong RAM (orders_df, items_df)
    filter_run_times = []
    individual_times = {
        "apply_filters": [],
        "kpi_extended": [],
        "kpi_previous_period": [],
        "monthly_revenue": [],
        "delay_vs_review": [],
        "review_distribution": [],
        "revenue_by_state": [],
        "payment_mix": [],
        "repeat_customer_rate": [],
        "orders_heatmap": [],
        "top_categories": [],
    }

    for i in range(5):
        t_start = time.perf_counter()
        
        t0 = time.perf_counter()
        f_orders = an.apply_filters(orders_df, filters)
        f_items = an.apply_filters(items_df, filters)
        individual_times["apply_filters"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.kpi_extended(f_orders)
        individual_times["kpi_extended"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.kpi_previous_period(orders_df, filters)
        individual_times["kpi_previous_period"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.monthly_revenue(f_orders)
        individual_times["monthly_revenue"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.delay_vs_review(f_orders)
        individual_times["delay_vs_review"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.review_distribution(f_orders)
        individual_times["review_distribution"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.revenue_by_state(f_orders)
        individual_times["revenue_by_state"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.payment_mix(f_orders)
        individual_times["payment_mix"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.repeat_customer_rate(f_orders)
        individual_times["repeat_customer_rate"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.orders_heatmap(f_orders)
        individual_times["orders_heatmap"].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        an.top_categories(f_items, 10)
        individual_times["top_categories"].append(time.perf_counter() - t0)

        t_total = time.perf_counter() - t_start
        filter_run_times.append(t_total)
        print(f"Lần {i+1}: {t_total*1000:.2f} ms ({t_total:.4f} s)")

    avg_filter_run = sum(filter_run_times) / len(filter_run_times)
    print(f"\nTrung bình 5 lần đổi bộ lọc: {avg_filter_run*1000:.2f} ms ({avg_filter_run:.4f} s)")

    print("\nChi tiết trung bình từng hàm (ms):")
    for k, v in individual_times.items():
        avg_k = (sum(v) / len(v)) * 1000
        print(f"  - {k:<24}: {avg_k:>7.2f} ms")

if __name__ == "__main__":
    measure()
