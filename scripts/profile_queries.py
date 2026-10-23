"""
Script đo thời gian thực thi (profiling) từng hàm truy vấn SQL trong src/db.py
với bộ lọc mặc định của Dashboard (2017-01-01 đến 2018-08-31, status='delivered').
Sắp xếp từ hàm chậm nhất đến nhanh nhất.
"""

import sys
import os
import time

# Đảm bảo in UTF-8 không lỗi trên Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db import (
    get_kpi_extended,
    get_kpi_previous_period,
    get_monthly_revenue,
    get_delay_vs_review,
    get_review_distribution,
    get_revenue_by_state,
    get_payment_mix,
    get_repeat_customer_rate,
    get_orders_heatmap,
    get_top_categories,
)


def profile_all_queries():
    filters = {
        "start_date": "2017-01-01",
        "end_date": "2018-08-31",
        "statuses": ["delivered"],
    }

    queries = [
        ("get_kpi_extended", lambda: get_kpi_extended(filters)),
        ("get_kpi_previous_period", lambda: get_kpi_previous_period(filters)),
        ("get_monthly_revenue", lambda: get_monthly_revenue(filters)),
        ("get_delay_vs_review", lambda: get_delay_vs_review(filters)),
        ("get_review_distribution", lambda: get_review_distribution(filters)),
        ("get_revenue_by_state", lambda: get_revenue_by_state(filters)),
        ("get_payment_mix", lambda: get_payment_mix(filters)),
        ("get_repeat_customer_rate", lambda: get_repeat_customer_rate(filters)),
        ("get_orders_heatmap", lambda: get_orders_heatmap(filters)),
        ("get_top_categories", lambda: get_top_categories(10, filters)),
    ]

    results = []
    print("\n" + "=" * 65)
    print("PROFILING 10 SQL QUERIES IN src/db.py (DEFAULT FILTERS)")
    print("=" * 65)
    print(f"Filters: {filters}\n")

    total_start = time.perf_counter()
    for name, func in queries:
        t0 = time.perf_counter()
        func()
        t1 = time.perf_counter()
        elapsed = t1 - t0
        results.append((name, elapsed))
    total_elapsed = time.perf_counter() - total_start

    # Sắp xếp từ chậm nhất đến nhanh nhất
    results.sort(key=lambda x: x[1], reverse=True)

    print(f"{'Query Function':<32} | {'Time (s)':<14} | {'Share (%)':<10}")
    print("-" * 65)
    for name, elapsed in results:
        pct = (elapsed / total_elapsed) * 100.0 if total_elapsed > 0 else 0.0
        print(f"{name:<32} | {elapsed:>10.4f} s    | {pct:>8.1f}%")
    print("-" * 65)
    print(f"{'TOTAL (10 SQL QUERIES)':<32} | {total_elapsed:>10.4f} s    | 100.0%")
    print("=" * 65 + "\n")
    return results, total_elapsed


if __name__ == "__main__":
    profile_all_queries()
