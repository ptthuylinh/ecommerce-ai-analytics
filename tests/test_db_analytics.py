"""
Kiểm thử 9 hàm phân tích số liệu mới trên mini_db:
1. get_kpi_extended
2. get_kpi_previous_period
3. get_monthly_revenue (kèm orders và mom_growth_pct)
4. get_delay_vs_review
5. get_review_distribution
6. get_revenue_by_state
7. get_payment_mix
8. get_repeat_customer_rate
9. get_orders_heatmap
Bao gồm kiểm tra tính đúng đắn trên mini_db và xử lý an toàn khi bộ lọc ra 0 dòng.
"""

import pytest
import pandas as pd
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
)

ZERO_FILTER = {"states": ["ZZ"]}  # Bang không tồn tại để test trường hợp 0 dòng


# 1. get_kpi_extended
def test_get_kpi_extended_normal(mini_db):
    """Kiểm tra get_kpi_extended trên mini_db: đủ 7 chỉ số, đúng giá trị tính tay."""
    kpi = get_kpi_extended()
    assert kpi["total_orders"] == 6
    assert kpi["total_revenue"] == 1050.0
    assert kpi["total_customers"] == 5
    assert kpi["avg_order_value"] == round(1050.0 / 6, 2)  # 175.0
    # (julianday(delivered 00:00:00) - julianday(purchase HH:00:00)):
    # order_1: 4.58d, order_2: 4.54d, order_3: 5.50d, order_4: 6.46d, order_5: 5.42d, order_6: 6.38d -> TB = 5.48 ngày
    assert round(kpi["avg_delivery_days"], 2) == 5.48


def test_get_kpi_extended_zero_rows(mini_db):
    """Kiểm tra get_kpi_extended khi bộ lọc trả về 0 dòng."""
    kpi = get_kpi_extended(ZERO_FILTER)
    assert kpi["total_orders"] == 0
    assert kpi["total_revenue"] == 0.0
    assert kpi["total_customers"] == 0
    assert kpi["avg_order_value"] == 0.0
    assert kpi["on_time_rate"] == 0.0
    assert kpi["avg_delivery_days"] == 0.0


# 2. get_kpi_previous_period
def test_get_kpi_previous_period_normal(mini_db):
    """Kiểm tra get_kpi_previous_period cho kỳ liền trước."""
    # Kỳ hiện tại: tháng 2/2017 (2017-02-01 -> 2017-02-28 = 28 ngày)
    # Kỳ liền trước: 28 ngày trước đó (tháng 1/2017)
    filters = {"start_date": "2017-02-01", "end_date": "2017-02-28"}
    prev_kpi = get_kpi_previous_period(filters)
    assert isinstance(prev_kpi, pd.Series)
    # Kỳ trước rơi vào tháng 1/2017, có order_1 (110.0)
    assert prev_kpi["total_orders"] >= 1
    assert prev_kpi["total_revenue"] >= 110.0


def test_get_kpi_previous_period_zero_rows(mini_db):
    """Kiểm tra get_kpi_previous_period khi lọc ra 0 dòng không gây lỗi."""
    prev_kpi = get_kpi_previous_period(ZERO_FILTER)
    assert isinstance(prev_kpi, pd.Series)
    assert prev_kpi["total_orders"] == 0
    assert prev_kpi["total_revenue"] == 0.0


# 3. get_monthly_revenue
def test_get_monthly_revenue_normal(mini_db):
    """Kiểm tra get_monthly_revenue có đầy đủ cột month, revenue, orders, mom_growth_pct."""
    df = get_monthly_revenue()
    assert isinstance(df, pd.DataFrame)
    for col in ["month", "revenue", "orders", "mom_growth_pct"]:
        assert col in df.columns, f"Thiếu cột {col} trong get_monthly_revenue"

    assert len(df) == 6  # 6 tháng từ 2017-01 đến 2017-06
    # Kiểm tra tháng 2 tăng trưởng so với tháng 1: revenue tháng 1=110, tháng 2=220 -> tăng 100%
    row_feb = df[df["month"] == "2017-02"].iloc[0]
    assert row_feb["revenue"] == 220.0
    assert row_feb["orders"] == 1
    assert row_feb["mom_growth_pct"] == 100.0


def test_get_monthly_revenue_zero_rows(mini_db):
    """Kiểm tra get_monthly_revenue khi lọc 0 dòng trả về DataFrame rỗng đúng cột."""
    df = get_monthly_revenue(ZERO_FILTER)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    for col in ["month", "revenue", "orders", "mom_growth_pct"]:
        assert col in df.columns


# 4. get_delay_vs_review
def test_get_delay_vs_review_normal(mini_db):
    """Kiểm tra phân nhóm trễ hạn và điểm đánh giá TB."""
    df = get_delay_vs_review()
    assert isinstance(df, pd.DataFrame)
    for col in ["delay_status", "orders", "avg_review_score"]:
        assert col in df.columns

    # Trong mini_db, toàn bộ 6 đơn delivered đều giao sớm hơn ngày hẹn
    assert len(df) >= 1
    assert "Sớm" in df["delay_status"].values


def test_get_delay_vs_review_zero_rows(mini_db):
    """Kiểm tra get_delay_vs_review khi lọc 0 dòng."""
    df = get_delay_vs_review(ZERO_FILTER)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    for col in ["delay_status", "orders", "avg_review_score"]:
        assert col in df.columns


# 5. get_review_distribution
def test_get_review_distribution_normal(mini_db):
    """Kiểm tra phân bố review trả về đủ thang điểm 1 đến 5."""
    df = get_review_distribution()
    assert isinstance(df, pd.DataFrame)
    assert list(df["review_score"]) == [1, 2, 3, 4, 5]
    # mini_db có 2 review 5 sao (r1, r5), 2 review 4 sao (r2, r3a)
    score_5_orders = df[df["review_score"] == 5]["orders"].iloc[0]
    assert score_5_orders >= 1


def test_get_review_distribution_zero_rows(mini_db):
    """Kiểm tra get_review_distribution khi lọc 0 dòng vẫn trả đủ 1-5 với orders = 0."""
    df = get_review_distribution(ZERO_FILTER)
    assert isinstance(df, pd.DataFrame)
    assert list(df["review_score"]) == [1, 2, 3, 4, 5]
    assert (df["orders"] == 0).all()


# 6. get_revenue_by_state
def test_get_revenue_by_state_normal(mini_db):
    """Kiểm tra doanh thu, số đơn và tỷ lệ trễ hạn theo bang."""
    df = get_revenue_by_state()
    assert isinstance(df, pd.DataFrame)
    for col in ["customer_state", "revenue", "orders", "delayed_rate"]:
        assert col in df.columns

    # Bang SP có 2 đơn (order_1 110.0 + order_3 165.0 = 275.0)
    sp_row = df[df["customer_state"] == "SP"].iloc[0]
    assert sp_row["orders"] == 2
    assert sp_row["revenue"] == 275.0
    assert sp_row["delayed_rate"] == 0.0  # Không có đơn trễ


def test_get_revenue_by_state_zero_rows(mini_db):
    """Kiểm tra get_revenue_by_state khi lọc 0 dòng."""
    df = get_revenue_by_state(ZERO_FILTER)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    for col in ["customer_state", "revenue", "orders", "delayed_rate"]:
        assert col in df.columns


# 7. get_payment_mix
def test_get_payment_mix_normal(mini_db):
    """Kiểm tra cơ cấu doanh thu theo payment_type."""
    df = get_payment_mix()
    assert isinstance(df, pd.DataFrame)
    for col in ["payment_type", "revenue", "orders", "percentage"]:
        assert col in df.columns

    assert "credit_card" in df["payment_type"].values
    assert round(df["percentage"].sum(), 1) == 100.0


def test_get_payment_mix_zero_rows(mini_db):
    """Kiểm tra get_payment_mix khi lọc 0 dòng."""
    df = get_payment_mix(ZERO_FILTER)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    for col in ["payment_type", "revenue", "orders", "percentage"]:
        assert col in df.columns


# 8. get_repeat_customer_rate
def test_get_repeat_customer_rate_normal(mini_db):
    """Kiểm tra tỷ lệ % khách hàng mua lại."""
    # mini_db có 5 khách unique (u1 -> u5), trong đó u1 có 2 đơn (c1 và c3) => 1 / 5 = 20.0%
    rate = get_repeat_customer_rate()
    assert rate == 20.0, f"Kỳ vọng 20.0% khách mua lại, nhận được {rate}%"


def test_get_repeat_customer_rate_zero_rows(mini_db):
    """Kiểm tra get_repeat_customer_rate khi lọc 0 dòng trả về 0.0."""
    rate = get_repeat_customer_rate(ZERO_FILTER)
    assert rate == 0.0


# 9. get_orders_heatmap
def test_get_orders_heatmap_normal(mini_db):
    """Kiểm tra heatmap số đơn theo thứ x giờ."""
    df = get_orders_heatmap()
    assert isinstance(df, pd.DataFrame)
    for col in ["day_of_week", "hour", "orders"]:
        assert col in df.columns

    assert len(df) == 6  # 6 đơn delivered tương ứng 6 khung giờ khác nhau
    assert df["orders"].sum() == 6


def test_get_orders_heatmap_zero_rows(mini_db):
    """Kiểm tra get_orders_heatmap khi lọc 0 dòng."""
    df = get_orders_heatmap(ZERO_FILTER)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    for col in ["day_of_week", "hour", "orders"]:
        assert col in df.columns
