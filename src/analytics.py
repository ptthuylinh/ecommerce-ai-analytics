"""
Module Analytics xử lý dữ liệu in-memory bằng Pandas DataFrame.
Thực hiện nạp 2 bảng Fact (orders_fact và items_fact) duy nhất một lần và cache lại,
cho phép áp dụng bộ lọc đa chiều (Pandas mask) và tính toán toàn bộ KPI, biểu đồ
trong thời gian dưới 50ms (tăng tốc độ tải trang Dashboard dưới 2 giây).
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import streamlit as st

# Đường dẫn CSDL mặc định
DEFAULT_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/ecommerce.db"))


def _get_db_path(db_path=None):
    if db_path is not None:
        return db_path
    return os.getenv("ECOMMERCE_DB_PATH") or os.getenv("DB_PATH") or DEFAULT_DB_PATH


@st.cache_data(show_spinner=False)
def load_orders_fact(db_path=None) -> pd.DataFrame:
    """
    Nạp toàn bộ bảng Fact đơn hàng (orders_fact) với MỘT truy vấn SQL duy nhất.
    Gộp payments và reviews theo order_id bằng CTE để triệt tiêu nhân dòng (fan-out).
    Trả về DataFrame một dòng/đơn với các cột:
    order_id, customer_unique_id, customer_state, order_status, purchase_ts,
    purchase_month, dow, hour, payment_total, payment_type, review_score,
    sum_review, count_review, delivery_days, delay_days, is_delayed, is_on_time.
    """
    path = _get_db_path(db_path)
    conn = sqlite3.connect(path)

    query = """
    WITH p_agg AS (
        SELECT order_id, SUM(payment_value) AS payment_total
        FROM order_payments
        GROUP BY order_id
    ),
    p_top AS (
        SELECT order_id, payment_type
        FROM (
            SELECT order_id, payment_type, SUM(payment_value) AS val
            FROM order_payments
            GROUP BY order_id, payment_type
            ORDER BY val DESC
        )
        GROUP BY order_id
    ),
    r_agg AS (
        SELECT 
            order_id, 
            AVG(review_score) AS review_score, 
            SUM(review_score) AS sum_review, 
            COUNT(review_score) AS count_review
        FROM order_reviews
        GROUP BY order_id
    )
    SELECT 
        o.order_id,
        c.customer_unique_id,
        c.customer_state,
        o.order_status,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        COALESCE(p.payment_total, 0.0) AS payment_total,
        COALESCE(pt.payment_type, 'not_defined') AS payment_type,
        r.review_score,
        COALESCE(r.sum_review, 0) AS sum_review,
        COALESCE(r.count_review, 0) AS count_review
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN p_agg p ON o.order_id = p.order_id
    LEFT JOIN p_top pt ON o.order_id = pt.order_id
    LEFT JOIN r_agg r ON o.order_id = r.order_id;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Parse datetime một lần duy nhất
    df["purchase_ts"] = pd.to_datetime(df["order_purchase_timestamp"])
    df["delivered_ts"] = pd.to_datetime(df["order_delivered_customer_date"])
    df["estimated_ts"] = pd.to_datetime(df["order_estimated_delivery_date"])

    df["purchase_month"] = df["purchase_ts"].dt.strftime("%Y-%m")
    # dow: 0=Chủ nhật đến 6=Thứ bảy (tương ứng strftime('%w', ...))
    df["dow"] = ((df["purchase_ts"].dt.dayofweek + 1) % 7).astype("int64")
    df["hour"] = df["purchase_ts"].dt.hour.astype("int64")

    # delivery_days: thời gian từ khi đặt đến khi giao (ngày)
    df["delivery_days"] = (df["delivered_ts"] - df["purchase_ts"]).dt.total_seconds() / 86400.0

    # delay_days: chênh lệch giữa ngày giao thực tế và ngày dự kiến (ngày)
    deliv_d = df["delivered_ts"].dt.date
    est_d = df["estimated_ts"].dt.date
    has_both = df["delivered_ts"].notna() & df["estimated_ts"].notna()

    df["delay_days"] = np.where(
        has_both,
        (df["delivered_ts"] - df["estimated_ts"]).dt.total_seconds() / 86400.0,
        np.nan,
    )
    df["is_delayed"] = np.where(has_both & (deliv_d > est_d), 1, 0)
    df["is_on_time"] = np.where(has_both & (deliv_d <= est_d), 1, 0)

    # Phân nhóm mức trễ giao hàng
    diff_days = df["delay_days"]
    conditions = [
        has_both & (deliv_d < est_d),
        has_both & (deliv_d == est_d),
        has_both & (diff_days <= 3),
        has_both & (diff_days <= 7),
    ]
    choices = ["Sớm", "Đúng hạn", "Trễ 1-3 ngày", "Trễ 4-7 ngày"]
    df["delay_status"] = np.select(conditions, choices, default="Trễ >7 ngày")

    return df


@st.cache_data(show_spinner=False)
def load_items_fact(db_path=None) -> pd.DataFrame:
    """
    Nạp bảng Fact sản phẩm (items_fact) với MỘT truy vấn SQL duy nhất.
    Trả về DataFrame một dòng/sản phẩm: order_id, category, price,
    order_status, purchase_ts, customer_state.
    """
    path = _get_db_path(db_path)
    conn = sqlite3.connect(path)

    query = """
    SELECT 
        i.order_id,
        COALESCE(pr.product_category_name_english, pr.product_category_name, 'Unknown') AS category,
        i.price,
        o.order_status,
        o.order_purchase_timestamp,
        c.customer_state
    FROM order_items i
    JOIN products pr ON i.product_id = pr.product_id
    JOIN orders o ON i.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id;
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    df["purchase_ts"] = pd.to_datetime(df["order_purchase_timestamp"])
    return df


def apply_filters(df: pd.DataFrame, filters: dict = None, db_path=None) -> pd.DataFrame:
    """
    Lọc DataFrame in-memory cực nhanh bằng mask Pandas.
    Hỗ trợ lọc theo: start_date, end_date, statuses, states, categories.
    """
    if df.empty or not filters:
        return df

    mask = pd.Series(True, index=df.index)

    # 1. Trạng thái đơn hàng (order_status)
    statuses = filters.get("statuses")
    if statuses is not None:
        if isinstance(statuses, str):
            statuses = [statuses]
        if len(statuses) > 0:
            mask &= df["order_status"].isin(statuses)
    elif "order_status" in df.columns:
        mask &= (df["order_status"] == "delivered")

    # 2. Khoảng thời gian đặt hàng (purchase_ts)
    start_date = filters.get("start_date")
    if start_date:
        start_str = str(start_date)[:10]
        start_ts = pd.to_datetime(f"{start_str} 00:00:00")
        mask &= (df["purchase_ts"] >= start_ts)

    end_date = filters.get("end_date")
    if end_date:
        end_str = str(end_date)[:10]
        end_ts = pd.to_datetime(f"{end_str} 23:59:59")
        mask &= (df["purchase_ts"] <= end_ts)

    # 3. Bang / Khu vực (customer_state)
    states = filters.get("states")
    if states:
        if isinstance(states, str):
            states = [states]
        if len(states) > 0:
            mask &= df["customer_state"].isin(states)

    # 4. Danh mục sản phẩm (categories)
    categories = filters.get("categories")
    if categories:
        if isinstance(categories, str):
            categories = [categories]
        if len(categories) > 0 and "order_id" in df.columns:
            items_df = load_items_fact(db_path)
            matching_orders = set(items_df.loc[items_df["category"].isin(categories), "order_id"])
            mask &= df["order_id"].isin(matching_orders)

    return df[mask]


# ==============================================================================
# CÁC HÀM PHÂN TÍCH TÍNH TOÁN TRÊN PANDAS DATAFRAME
# ==============================================================================

def kpi_extended(df: pd.DataFrame) -> pd.Series:
    """Tính 7 chỉ số KPI chính từ DataFrame orders đã lọc."""
    if df.empty:
        return pd.Series({
            "total_orders": 0,
            "total_revenue": 0.0,
            "avg_review_score": 0.0,
            "total_customers": 0,
            "avg_order_value": 0.0,
            "on_time_rate": 0.0,
            "avg_delivery_days": 0.0,
        })

    total_orders = int(df["order_id"].nunique())
    total_revenue = round(float(df["payment_total"].sum()), 2)
    total_customers = int(df["customer_unique_id"].nunique())

    tot_review_sum = df["sum_review"].sum()
    tot_review_cnt = df["count_review"].sum()
    avg_review_score = round(float(tot_review_sum / tot_review_cnt), 2) if tot_review_cnt > 0 else 0.0

    avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0

    delivered_with_est = (df["delivered_ts"].notna() & df["estimated_ts"].notna()).sum()
    on_time_orders = df["is_on_time"].sum()
    on_time_rate = (
        round((on_time_orders / delivered_with_est) * 100.0, 2) if delivered_with_est > 0 else 0.0
    )

    valid_delivery = df.loc[df["delivery_days"].notna(), "delivery_days"]
    avg_delivery_days = round(float(valid_delivery.mean()), 2) if not valid_delivery.empty else 0.0

    return pd.Series({
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "avg_review_score": avg_review_score,
        "total_customers": total_customers,
        "avg_order_value": avg_order_value,
        "on_time_rate": on_time_rate,
        "avg_delivery_days": avg_delivery_days,
    })


def kpi_previous_period(df_all_orders: pd.DataFrame, filters: dict = None, db_path=None) -> pd.Series:
    """Tính KPI cho chu kỳ liền trước có cùng độ dài ngày."""
    if filters is None:
        filters = {}

    start_date = filters.get("start_date")
    end_date = filters.get("end_date")

    if not start_date or not end_date:
        if df_all_orders.empty:
            return kpi_extended(pd.DataFrame())
        start_date = df_all_orders["purchase_ts"].min().strftime("%Y-%m-%d")
        end_date = df_all_orders["purchase_ts"].max().strftime("%Y-%m-%d")

    try:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
    except Exception:
        return kpi_extended(pd.DataFrame())

    delta_days = (end_dt - start_dt).days
    if delta_days < 0:
        return kpi_extended(pd.DataFrame())

    prev_end_dt = start_dt - pd.Timedelta(days=1)
    prev_start_dt = prev_end_dt - pd.Timedelta(days=delta_days)

    prev_filters = dict(filters)
    prev_filters["start_date"] = prev_start_dt.strftime("%Y-%m-%d")
    prev_filters["end_date"] = prev_end_dt.strftime("%Y-%m-%d")

    df_prev = apply_filters(df_all_orders, prev_filters, db_path=db_path)
    return kpi_extended(df_prev)


def monthly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Tổng hợp doanh thu theo tháng kèm cột orders và mom_growth_pct."""
    if df.empty:
        return pd.DataFrame(columns=["month", "revenue", "orders", "mom_growth_pct"])

    grouped = (
        df.groupby("purchase_month")
        .agg(
            revenue=("payment_total", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
        .rename(columns={"purchase_month": "month"})
    )
    grouped["revenue"] = grouped["revenue"].round(2)
    grouped = grouped.sort_values("month").reset_index(drop=True)
    grouped["mom_growth_pct"] = (grouped["revenue"].pct_change() * 100.0).round(2)
    grouped["mom_growth_pct"] = grouped["mom_growth_pct"].replace({np.nan: None})
    return grouped


def delay_vs_review(df: pd.DataFrame) -> pd.DataFrame:
    """Phân nhóm đơn hàng theo mức trễ hạn và trả về số đơn + điểm đánh giá TB."""
    expected_order = ["Sớm", "Đúng hạn", "Trễ 1-3 ngày", "Trễ 4-7 ngày", "Trễ >7 ngày"]
    if df.empty:
        return pd.DataFrame(columns=["delay_status", "orders", "avg_review_score"])

    valid = df[df["delivered_ts"].notna() & df["estimated_ts"].notna()].copy()
    if valid.empty:
        return pd.DataFrame(columns=["delay_status", "orders", "avg_review_score"])

    grouped = (
        valid.groupby("delay_status")
        .agg(
            orders=("order_id", "nunique"),
            avg_review_score=("review_score", "mean"),
        )
        .reset_index()
    )
    grouped["avg_review_score"] = grouped["avg_review_score"].round(2)
    grouped["cat"] = pd.Categorical(grouped["delay_status"], categories=expected_order, ordered=True)
    grouped = grouped.sort_values("cat").drop(columns=["cat"]).reset_index(drop=True)
    return grouped


def review_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Phân bố số lượng đơn hàng theo số sao đánh giá từ 1 đến 5."""
    template = pd.DataFrame({"review_score": [1, 2, 3, 4, 5]})
    if df.empty or df["review_score"].isna().all():
        template["orders"] = 0
        return template

    valid = df.dropna(subset=["review_score"]).copy()
    valid["review_score_int"] = valid["review_score"].round().astype(int)

    dist = (
        valid.groupby("review_score_int")
        .agg(orders=("order_id", "nunique"))
        .reset_index()
        .rename(columns={"review_score_int": "review_score"})
    )

    merged = pd.merge(template, dist, on="review_score", how="left").fillna(0)
    merged["orders"] = merged["orders"].astype(int)
    return merged


def revenue_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Doanh thu, số đơn và tỷ lệ giao trễ theo từng Bang."""
    if df.empty:
        return pd.DataFrame(columns=["customer_state", "revenue", "orders", "delayed_rate"])

    grouped = (
        df.groupby("customer_state")
        .agg(
            revenue=("payment_total", "sum"),
            orders=("order_id", "nunique"),
            delayed_cnt=("is_delayed", "sum"),
        )
        .reset_index()
    )
    grouped["revenue"] = grouped["revenue"].round(2)
    grouped["delayed_rate"] = (grouped["delayed_cnt"] * 100.0 / grouped["orders"]).round(2)
    grouped = (
        grouped.drop(columns=["delayed_cnt"])
        .sort_values("revenue", ascending=False)
        .reset_index(drop=True)
    )
    return grouped


def payment_mix(df: pd.DataFrame) -> pd.DataFrame:
    """Cơ cấu thanh toán theo payment_type chính của từng đơn."""
    if df.empty:
        return pd.DataFrame(columns=["payment_type", "revenue", "orders", "percentage"])

    grouped = (
        df.groupby("payment_type")
        .agg(
            revenue=("payment_total", "sum"),
            orders=("order_id", "nunique"),
        )
        .reset_index()
    )
    grouped["revenue"] = grouped["revenue"].round(2)
    grouped = grouped.sort_values("revenue", ascending=False).reset_index(drop=True)
    total_rev = grouped["revenue"].sum()
    grouped["percentage"] = (
        (grouped["revenue"] / total_rev * 100.0).round(2) if total_rev > 0 else 0.0
    )
    return grouped


def repeat_customer_rate(df: pd.DataFrame) -> float:
    """Tỷ lệ khách hàng mua lại (% customer_unique_id có từ 2 đơn trở lên)."""
    if df.empty:
        return 0.0

    order_counts = df.groupby("customer_unique_id")["order_id"].nunique()
    total_unique = len(order_counts)
    if total_unique == 0:
        return 0.0

    repeat_count = (order_counts >= 2).sum()
    return round(float(repeat_count / total_unique) * 100.0, 2)


def orders_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Ma trận đơn hàng theo Thứ trong tuần (day_of_week) x Khung giờ (hour)."""
    if df.empty:
        return pd.DataFrame(columns=["day_of_week", "hour", "orders"])

    grouped = (
        df.groupby(["dow", "hour"])
        .agg(orders=("order_id", "nunique"))
        .reset_index()
        .rename(columns={"dow": "day_of_week"})
    )
    grouped["day_of_week"] = grouped["day_of_week"].astype("int64")
    grouped["hour"] = grouped["hour"].astype("int64")
    grouped = grouped.sort_values(["day_of_week", "hour"]).reset_index(drop=True)
    return grouped


def top_categories(df_items: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Top N danh mục sản phẩm dẫn đầu theo doanh thu và số lượng bán."""
    if df_items.empty:
        return pd.DataFrame(columns=["category", "total_sales", "items_sold"])

    grouped = (
        df_items.groupby("category")
        .agg(
            total_sales=("price", "sum"),
            items_sold=("order_id", "count"),
        )
        .reset_index()
    )
    grouped["total_sales"] = grouped["total_sales"].round(2)
    grouped = (
        grouped.sort_values("total_sales", ascending=False)
        .head(int(top_n))
        .reset_index(drop=True)
    )
    return grouped
