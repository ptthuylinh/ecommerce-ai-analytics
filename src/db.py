"""
Module kết nối cơ sở dữ liệu SQLite và cung cấp các hàm phân tích số liệu E-Commerce.
Sử dụng CTE (Common Table Expressions) để tổng hợp độc lập payments và reviews
tránh hiện tượng nhân dòng (fan-out), hỗ trợ bộ lọc đa chiều tham số hóa an toàn.
"""

import os
import sqlite3
import pandas as pd
import numpy as np

# Đường dẫn tự động tìm tới file database ecommerce.db
DB_PATH = os.path.join(os.path.dirname(__file__), "../data/ecommerce.db")


def get_connection(db_path=None):
    """
    Tạo kết nối tới SQLite Database.
    Ưu tiên tham số db_path, sau đó đến biến môi trường ECOMMERCE_DB_PATH / DB_PATH,
    cuối cùng fallback về biến module DB_PATH.
    """
    if db_path is None:
        db_path = os.getenv("ECOMMERCE_DB_PATH") or os.getenv("DB_PATH") or DB_PATH
    return sqlite3.connect(db_path)


def _build_filter_clause(filters=None, default_status="delivered"):
    """
    Hàm phụ trợ xây dựng mệnh đề WHERE tham số hóa từ dictionary filters.
    Trả về: (where_clause_str, params_list)
    """
    if filters is None:
        filters = {}

    conditions = []
    params = []

    # 1. Trạng thái đơn hàng (order_status)
    statuses = filters.get("statuses")
    if statuses is not None:
        if isinstance(statuses, str):
            statuses = [statuses]
        if len(statuses) > 0:
            placeholders = ", ".join(["?"] * len(statuses))
            conditions.append(f"o.order_status IN ({placeholders})")
            params.extend(statuses)
    elif default_status is not None:
        conditions.append("o.order_status = ?")
        params.append(default_status)

    # 2. Khoảng thời gian đặt hàng (order_purchase_timestamp)
    start_date = filters.get("start_date")
    if start_date:
        start_str = str(start_date)
        if len(start_str) == 10:
            start_str = f"{start_str} 00:00:00"
        conditions.append("o.order_purchase_timestamp >= ?")
        params.append(start_str)

    end_date = filters.get("end_date")
    if end_date:
        end_str = str(end_date)
        if len(end_str) == 10:
            end_str = f"{end_str} 23:59:59"
        conditions.append("o.order_purchase_timestamp <= ?")
        params.append(end_str)

    # 3. Bang / Khu vực (customer_state)
    states = filters.get("states")
    if states is not None:
        if isinstance(states, str):
            states = [states]
        if len(states) > 0:
            placeholders = ", ".join(["?"] * len(states))
            conditions.append(f"c.customer_state IN ({placeholders})")
            params.extend(states)

    # 4. Danh mục sản phẩm (categories)
    categories = filters.get("categories")
    if categories is not None:
        if isinstance(categories, str):
            categories = [categories]
        if len(categories) > 0:
            placeholders = ", ".join(["?"] * len(categories))
            subquery = f"""
            o.order_id IN (
                SELECT DISTINCT i.order_id
                FROM order_items i
                JOIN products pr ON i.product_id = pr.product_id
                WHERE pr.product_category_name IN ({placeholders})
                   OR pr.product_category_name_english IN ({placeholders})
            )
            """
            conditions.append(subquery)
            params.extend(categories)
            params.extend(categories)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    return where_clause, params


def get_filter_options(filters=None):
    """
    Lấy danh sách các lựa chọn phục vụ Sidebar lọc dữ liệu:
    - min_date, max_date
    - danh sách categories
    - danh sách states
    - danh sách statuses
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM orders;")
    min_date, max_date = cur.fetchone()
    min_date_str = str(min_date)[:10] if min_date else "2016-01-01"
    max_date_str = str(max_date)[:10] if max_date else "2018-12-31"

    cur.execute("""
    SELECT DISTINCT product_category_name
    FROM products
    WHERE product_category_name IS NOT NULL AND product_category_name != ''
    ORDER BY product_category_name;
    """)
    categories = [row[0] for row in cur.fetchall()]

    cur.execute("""
    SELECT DISTINCT customer_state
    FROM customers
    WHERE customer_state IS NOT NULL
    ORDER BY customer_state;
    """)
    states = [row[0] for row in cur.fetchall()]

    cur.execute("""
    SELECT DISTINCT order_status
    FROM orders
    WHERE order_status IS NOT NULL
    ORDER BY order_status;
    """)
    statuses = [row[0] for row in cur.fetchall()]

    conn.close()
    return {
        "min_date": min_date_str,
        "max_date": max_date_str,
        "categories": categories,
        "states": states,
        "statuses": statuses,
    }


def get_filtered_orders(filters=None, **kwargs):
    """
    Trả về DataFrame danh sách đơn hàng đã được lọc theo các tiêu chí.
    Hỗ trợ nhận tham số qua dict filters hoặc kwargs.
    """
    combined_filters = {}
    if filters:
        combined_filters.update(filters)
    if kwargs:
        combined_filters.update(kwargs)

    where_clause, params = _build_filter_clause(combined_filters, default_status=None)

    query = f"""
    WITH p AS (
        SELECT order_id, SUM(payment_value) as total_payment
        FROM order_payments
        GROUP BY order_id
    ),
    r AS (
        SELECT order_id, AVG(review_score) as review_score
        FROM order_reviews
        GROUP BY order_id
    )
    SELECT 
        o.order_id,
        o.customer_id,
        c.customer_unique_id,
        c.customer_state,
        c.customer_city,
        o.order_status,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        ROUND(COALESCE(p.total_payment, 0.0), 2) as payment_value,
        ROUND(r.review_score, 2) as review_score
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN p ON o.order_id = p.order_id
    LEFT JOIN r ON o.order_id = r.order_id
    {where_clause}
    ORDER BY o.order_purchase_timestamp DESC;
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_kpi_metrics(filters=None):
    """
    Lấy 4 chỉ số KPI tổng quan cơ bản cho Dashboard (giữ nguyên tương thích ngược).
    Sử dụng CTE để gom nhóm payments và reviews theo order_id trước khi JOIN,
    và đếm đúng customer_unique_id.
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    query = f"""
    WITH p AS (
        SELECT order_id, SUM(payment_value) AS order_payment
        FROM order_payments
        GROUP BY order_id
    ),
    r AS (
        SELECT order_id, SUM(review_score) AS sum_review, COUNT(review_score) AS count_review
        FROM order_reviews
        GROUP BY order_id
    )
    SELECT 
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(COALESCE(SUM(p.order_payment), 0.0), 2) AS total_revenue,
        ROUND(COALESCE(SUM(r.sum_review) * 1.0 / NULLIF(SUM(r.count_review), 0), 0.0), 2) AS avg_review_score,
        COUNT(DISTINCT c.customer_unique_id) AS total_customers
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN p ON o.order_id = p.order_id
    LEFT JOIN r ON o.order_id = r.order_id
    {where_clause};
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty or df.iloc[0]["total_orders"] == 0:
        return pd.Series({
            "total_orders": 0,
            "total_revenue": 0.0,
            "avg_review_score": 0.0,
            "total_customers": 0,
        })
    return df.iloc[0]


def get_kpi_extended(filters=None):
    """
    1. get_kpi_extended: Ngoài các KPI cũ, bổ sung:
       - avg_order_value: Giá trị đơn hàng trung bình (total_revenue / total_orders)
       - on_time_rate: Tỷ lệ % đơn giao đúng hạn (delivered <= estimated)
       - avg_delivery_days: Số ngày giao hàng trung bình (delivered - purchase)
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    query = f"""
    WITH p AS (
        SELECT order_id, SUM(payment_value) AS order_payment
        FROM order_payments
        GROUP BY order_id
    ),
    r AS (
        SELECT order_id, SUM(review_score) AS sum_review, COUNT(review_score) AS count_review
        FROM order_reviews
        GROUP BY order_id
    )
    SELECT 
        COUNT(DISTINCT o.order_id) AS total_orders,
        ROUND(COALESCE(SUM(p.order_payment), 0.0), 2) AS total_revenue,
        ROUND(COALESCE(SUM(r.sum_review) * 1.0 / NULLIF(SUM(r.count_review), 0), 0.0), 2) AS avg_review_score,
        COUNT(DISTINCT c.customer_unique_id) AS total_customers,
        SUM(
            CASE 
                WHEN o.order_delivered_customer_date IS NOT NULL 
                 AND o.order_estimated_delivery_date IS NOT NULL
                 AND date(o.order_delivered_customer_date) <= date(o.order_estimated_delivery_date) 
                THEN 1 ELSE 0 
            END
        ) AS on_time_orders,
        COUNT(
            CASE 
                WHEN o.order_delivered_customer_date IS NOT NULL 
                 AND o.order_estimated_delivery_date IS NOT NULL 
                THEN 1 ELSE NULL 
            END
        ) AS delivered_with_estimates,
        ROUND(
            AVG(
                CASE 
                    WHEN o.order_delivered_customer_date IS NOT NULL 
                     AND o.order_purchase_timestamp IS NOT NULL
                    THEN julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)
                    ELSE NULL 
                END
            ), 2
        ) AS avg_delivery_days
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN p ON o.order_id = p.order_id
    LEFT JOIN r ON o.order_id = r.order_id
    {where_clause};
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty or df.iloc[0]["total_orders"] == 0:
        return pd.Series({
            "total_orders": 0,
            "total_revenue": 0.0,
            "avg_review_score": 0.0,
            "total_customers": 0,
            "avg_order_value": 0.0,
            "on_time_rate": 0.0,
            "avg_delivery_days": 0.0,
        })

    row = df.iloc[0]
    total_orders = int(row["total_orders"])
    total_revenue = float(row["total_revenue"])
    avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0

    delivered_with_est = int(row["delivered_with_estimates"] or 0)
    on_time_orders = int(row["on_time_orders"] or 0)
    on_time_rate = round((on_time_orders / delivered_with_est) * 100.0, 2) if delivered_with_est > 0 else 0.0

    avg_delivery_days = float(row["avg_delivery_days"]) if pd.notnull(row["avg_delivery_days"]) else 0.0

    return pd.Series({
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "avg_review_score": float(row["avg_review_score"]),
        "total_customers": int(row["total_customers"]),
        "avg_order_value": avg_order_value,
        "on_time_rate": on_time_rate,
        "avg_delivery_days": avg_delivery_days,
    })


def get_kpi_previous_period(filters=None):
    """
    2. get_kpi_previous_period: Tính cùng KPI cho kỳ liền trước có độ dài
       bằng khoảng ngày đang lọc, phục vụ Dashboard tính toán Delta (chênh lệch).
    """
    if filters is None:
        filters = {}

    start_date = filters.get("start_date")
    end_date = filters.get("end_date")

    # Nếu không truyền khoảng ngày cụ thể, tìm mốc min/max từ dữ liệu
    if not start_date or not end_date:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM orders WHERE order_status='delivered';")
        db_min, db_max = cur.fetchone()
        conn.close()
        if not db_min or not db_max:
            return get_kpi_extended({"start_date": "1970-01-01", "end_date": "1970-01-01"})
        start_date = str(db_min)[:10]
        end_date = str(db_max)[:10]

    try:
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
    except Exception:
        return get_kpi_extended({"start_date": "1970-01-01", "end_date": "1970-01-01"})

    delta_days = (end_dt - start_dt).days
    if delta_days < 0:
        return get_kpi_extended({"start_date": "1970-01-01", "end_date": "1970-01-01"})

    prev_end_dt = start_dt - pd.Timedelta(days=1)
    prev_start_dt = prev_end_dt - pd.Timedelta(days=delta_days)

    prev_filters = dict(filters)
    prev_filters["start_date"] = prev_start_dt.strftime("%Y-%m-%d")
    prev_filters["end_date"] = prev_end_dt.strftime("%Y-%m-%d")

    return get_kpi_extended(prev_filters)


def get_monthly_revenue(filters=None):
    """
    3. get_monthly_revenue: Doanh thu theo tháng, bổ sung cột orders và mom_growth_pct (% tăng trưởng).
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    query = f"""
    WITH p AS (
        SELECT order_id, SUM(payment_value) as order_payment
        FROM order_payments
        GROUP BY order_id
    )
    SELECT 
        strftime('%Y-%m', o.order_purchase_timestamp) AS month,
        ROUND(COALESCE(SUM(p.order_payment), 0.0), 2) AS revenue,
        COUNT(DISTINCT o.order_id) AS orders
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN p ON o.order_id = p.order_id
    {where_clause}
    GROUP BY month
    ORDER BY month;
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty:
        return pd.DataFrame(columns=["month", "revenue", "orders", "mom_growth_pct"])

    # Tính toán mom_growth_pct = ((revenue_t - revenue_t-1) / revenue_t-1) * 100
    df["mom_growth_pct"] = (df["revenue"].pct_change() * 100.0).round(2)
    # Thay thế NaN ở tháng đầu tiên bằng 0.0 hoặc None
    df["mom_growth_pct"] = df["mom_growth_pct"].replace({np.nan: None})
    return df


def get_delay_vs_review(filters=None):
    """
    4. get_delay_vs_review: Phân nhóm đơn theo mức độ trễ hạn và trả về số đơn + điểm đánh giá TB.
    Nhóm: 'Sớm', 'Đúng hạn', 'Trễ 1-3 ngày', 'Trễ 4-7 ngày', 'Trễ >7 ngày'
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    # Bổ sung điều kiện ngày giao hàng không null
    extra_cond = "o.order_delivered_customer_date IS NOT NULL AND o.order_estimated_delivery_date IS NOT NULL"
    if where_clause:
        where_clause += f" AND {extra_cond}"
    else:
        where_clause = f"WHERE {extra_cond}"

    query = f"""
    WITH r AS (
        SELECT order_id, AVG(review_score) as order_review
        FROM order_reviews
        GROUP BY order_id
    )
    SELECT 
        CASE 
            WHEN date(o.order_delivered_customer_date) < date(o.order_estimated_delivery_date) THEN 'Sớm'
            WHEN date(o.order_delivered_customer_date) = date(o.order_estimated_delivery_date) THEN 'Đúng hạn'
            WHEN julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date) <= 3 THEN 'Trễ 1-3 ngày'
            WHEN julianday(o.order_delivered_customer_date) - julianday(o.order_estimated_delivery_date) <= 7 THEN 'Trễ 4-7 ngày'
            ELSE 'Trễ >7 ngày'
        END AS delay_status,
        COUNT(DISTINCT o.order_id) AS orders,
        ROUND(AVG(r.order_review), 2) AS avg_review_score
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN r ON o.order_id = r.order_id
    {where_clause}
    GROUP BY delay_status;
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    expected_order = ["Sớm", "Đúng hạn", "Trễ 1-3 ngày", "Trễ 4-7 ngày", "Trễ >7 ngày"]
    if df.empty:
        return pd.DataFrame(columns=["delay_status", "orders", "avg_review_score"])

    # Đảm bảo sắp xếp logic theo thứ tự thời gian trễ
    df["order_cat"] = pd.Categorical(df["delay_status"], categories=expected_order, ordered=True)
    df = df.sort_values("order_cat").drop(columns=["order_cat"]).reset_index(drop=True)
    return df


def get_review_distribution(filters=None):
    """
    5. get_review_distribution: Phân bố số lượng đơn/đánh giá theo điểm số từ 1 đến 5.
    Đảm bảo luôn trả đủ các mức từ 1 đến 5 kể cả khi số đơn bằng 0.
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    query = f"""
    SELECT 
        r.review_score,
        COUNT(DISTINCT o.order_id) AS orders
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_reviews r ON o.order_id = r.order_id
    {where_clause}
    GROUP BY r.review_score
    ORDER BY r.review_score;
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    # Chuẩn hóa đủ 5 thang điểm từ 1 đến 5
    template = pd.DataFrame({"review_score": [1, 2, 3, 4, 5]})
    if df.empty:
        template["orders"] = 0
        return template

    merged = pd.merge(template, df, on="review_score", how="left").fillna(0)
    merged["orders"] = merged["orders"].astype(int)
    return merged


def get_revenue_by_state(filters=None):
    """
    6. get_revenue_by_state: Doanh thu, số đơn và tỷ lệ trễ hạn (% delayed_rate) theo từng Bang.
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    query = f"""
    WITH p AS (
        SELECT order_id, SUM(payment_value) as order_payment
        FROM order_payments
        GROUP BY order_id
    )
    SELECT 
        c.customer_state,
        ROUND(COALESCE(SUM(p.order_payment), 0.0), 2) AS revenue,
        COUNT(DISTINCT o.order_id) AS orders,
        ROUND(
            SUM(
                CASE 
                    WHEN o.order_delivered_customer_date IS NOT NULL 
                     AND o.order_estimated_delivery_date IS NOT NULL
                     AND date(o.order_delivered_customer_date) > date(o.order_estimated_delivery_date) 
                    THEN 1 ELSE 0 
                END
            ) * 100.0 / NULLIF(COUNT(DISTINCT o.order_id), 0), 2
        ) AS delayed_rate
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN p ON o.order_id = p.order_id
    {where_clause}
    GROUP BY c.customer_state
    ORDER BY revenue DESC;
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty:
        return pd.DataFrame(columns=["customer_state", "revenue", "orders", "delayed_rate"])
    df["delayed_rate"] = df["delayed_rate"].fillna(0.0)
    return df


def get_payment_mix(filters=None):
    """
    7. get_payment_mix: Cơ cấu doanh thu theo từng hình thức thanh toán (payment_type).
    Bổ sung tỷ trọng percentage (%) trên tổng doanh thu.
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    query = f"""
    SELECT 
        p.payment_type,
        ROUND(SUM(p.payment_value), 2) AS revenue,
        COUNT(DISTINCT o.order_id) AS orders
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_payments p ON o.order_id = p.order_id
    {where_clause}
    GROUP BY p.payment_type
    ORDER BY revenue DESC;
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty:
        return pd.DataFrame(columns=["payment_type", "revenue", "orders", "percentage"])

    total_rev = df["revenue"].sum()
    if total_rev > 0:
        df["percentage"] = (df["revenue"] / total_rev * 100.0).round(2)
    else:
        df["percentage"] = 0.0
    return df


def get_repeat_customer_rate(filters=None):
    """
    8. get_repeat_customer_rate: Tỷ lệ % khách hàng mua lại
       (% customer_unique_id có từ 2 đơn hàng trở lên trong tập dữ liệu lọc).
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    query = f"""
    SELECT 
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    {where_clause}
    GROUP BY c.customer_unique_id;
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty:
        return 0.0

    total_unique = len(df)
    repeat_customers = (df["order_count"] >= 2).sum()
    return round((repeat_customers / total_unique) * 100.0, 2)


def get_orders_heatmap(filters=None):
    """
    9. get_orders_heatmap: Ma trận số lượng đơn hàng theo Thứ trong tuần x Khung giờ đặt hàng.
    Thứ: 0 (Chủ nhật) đến 6 (Thứ bảy), Giờ: 0 đến 23.
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    query = f"""
    SELECT 
        CAST(strftime('%w', o.order_purchase_timestamp) AS INTEGER) AS day_of_week,
        CAST(strftime('%H', o.order_purchase_timestamp) AS INTEGER) AS hour,
        COUNT(DISTINCT o.order_id) AS orders
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    {where_clause}
    GROUP BY day_of_week, hour
    ORDER BY day_of_week, hour;
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if df.empty:
        return pd.DataFrame(columns=["day_of_week", "hour", "orders"])
    return df


def get_top_categories(top_n=10, filters=None):
    """
    Lấy top danh mục sản phẩm có doanh thu cao nhất (giữ nguyên tương thích ngược).
    Hỗ trợ nhận thêm bộ lọc filters.
    """
    where_clause, params = _build_filter_clause(filters, default_status="delivered")

    query = f"""
    SELECT 
        pr.product_category_name_english AS category,
        ROUND(SUM(i.price), 2) AS total_sales,
        COUNT(i.order_item_id) AS items_sold
    FROM order_items i
    JOIN products pr ON i.product_id = pr.product_id
    JOIN orders o ON i.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    {where_clause}
    GROUP BY category
    ORDER BY total_sales DESC
    LIMIT {int(top_n)};
    """
    conn = get_connection()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df