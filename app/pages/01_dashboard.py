"""
E-Commerce Executive Performance Dashboard.
Được cấu trúc theo phong cách giao diện mặc định Streamlit Dark, không CSS tùy biến.
Gồm 4 Tabs chức năng:
1. 📊 Tổng quan (6 thẻ st.metric bố cục 2x3, highlights st.info/st.success, Doanh thu MoM & Cơ cấu danh mục)
2. 🚚 Giao hàng & trải nghiệm (Phân tích mức trễ, Phân bố Review, Tỷ lệ trễ theo bang & Nhận định vận hành)
3. 🛍️ Sản phẩm (Top 10 danh mục theo doanh thu / số lượng, Độ tập trung ngành hàng)
4. 👥 Khách hàng & khu vực (Phân bố bang, Cơ cấu thanh toán Donut, Heatmap giờ vàng đặt hàng, Repeat Rate)

Sử dụng src/analytics.py với bảng Fact in-memory siêu tốc, tải trang dưới 2 giây.
"""

import sys
import os
import io
import math
from datetime import datetime
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Thêm thư mục gốc vào path để import các module từ src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.ui.filters import render_sidebar_filters  # noqa: E402
from src.ui.labels import (  # noqa: E402
    state_label,
    category_label,
    format_kpi_value,
    format_kpi_delta,
    check_prev_period_valid,
    format_currency_full,
)
from src.analytics import (  # noqa: E402
    load_orders_fact,
    load_items_fact,
    apply_filters,
    kpi_extended,
    kpi_previous_period,
    monthly_revenue,
    delay_vs_review,
    review_distribution,
    revenue_by_state,
    payment_mix,
    repeat_customer_rate,
    orders_heatmap,
    top_categories,
)

# 1. Cấu hình trang Streamlit
st.set_page_config(
    page_title="E-Commerce Executive Dashboard",
    page_icon="📊",
    layout="wide",
)

# 2. Bảng màu giao diện chuẩn bản main
PRIMARY_COLOR = "#1E88E5"      # Xanh dương chính
ALERT_COLOR = "#E53935"        # Đỏ cảnh báo
SECONDARY_COLOR = "#00897B"    # Xanh ngọc phụ trợ
DONUT_COLORS = ["#1E88E5", "#00897B", "#FB8C00", "#D81B60", "#8E24AA"]


def show_chart(fig):
    """Hiển thị biểu đồ Plotly tương thích giao diện mặc định của Streamlit (System, Dark, Light)."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")


# ==============================================================================
# HÀM HIỂN THỊ KPI CARDS & HIGHLIGHTS (TAB 1)
# ==============================================================================

def render_kpi_cards(kpi_curr, kpi_prev, filters=None):
    """
    Hiển thị 6 thẻ KPI chuẩn Streamlit st.metric theo bố cục 2 hàng x 3 thẻ.
    - Hàng 1 (Quy mô): Doanh thu, Đơn hàng, Khách hàng
    - Hàng 2 (Hiệu quả & Vận hành): AOV (TB/đơn), Đánh giá TB (/5), Giao đúng hạn
    Delta chỉ hiển thị khi kỳ trước nằm trọn trong khoảng dữ liệu (>= 2017-01-01) và có >= 100 đơn.
    """
    is_valid_prev = check_prev_period_valid(filters, kpi_prev)
    help_no_prev = "Chưa có kỳ trước để so sánh"

    # Trích xuất số liệu hiện tại và kỳ trước
    rev_curr = kpi_curr["total_revenue"]
    rev_prev = kpi_prev["total_revenue"]

    ord_curr = int(kpi_curr["total_orders"])
    ord_prev = int(kpi_prev["total_orders"])

    cust_curr = int(kpi_curr["total_customers"])
    cust_prev = int(kpi_prev["total_customers"])

    aov_curr = kpi_curr["avg_order_value"]
    aov_prev = kpi_prev["avg_order_value"]

    score_curr = kpi_curr["avg_review_score"]
    score_prev = kpi_prev["avg_review_score"]

    ontime_curr = kpi_curr["on_time_rate"]
    ontime_prev = kpi_prev["on_time_rate"]

    # Xác định nội dung help cho từng thẻ
    rev_full = format_currency_full(rev_curr)
    if not is_valid_prev:
        rev_help = f"{help_no_prev} (Số đầy đủ: {rev_full})"
        ord_help = help_no_prev
        cust_help = help_no_prev
        aov_help = help_no_prev
        score_help = help_no_prev
        ontime_help = help_no_prev
    else:
        rev_help = f"Số đầy đủ: {rev_full}"
        ord_help = f"Số đầy đủ: {ord_curr:,} đơn thành công"
        cust_help = f"Số đầy đủ: {cust_curr:,} khách hàng duy nhất"
        aov_help = f"Giá trị trung bình mỗi đơn: {format_currency_full(aov_curr)}"
        score_help = f"Điểm đánh giá trung bình: {score_curr:.2f}".replace(".", ",") + " / 5,0 sao"
        ontime_help = f"Tỷ lệ giao đúng hạn: {ontime_curr:.1f}%".replace(".", ",")

    # ------------------ HÀNG 1: QUY MÔ KINH DOANH (3 THẺ) ------------------
    r1_col1, r1_col2, r1_col3 = st.columns(3)

    # 1. Doanh thu
    with r1_col1:
        with st.container(border=True):
            st.metric(
                label="Doanh thu",
                value=format_kpi_value("total_revenue", rev_curr),
                delta=format_kpi_delta("total_revenue", rev_curr, rev_prev, is_valid_prev),
                delta_color="normal",
                help=rev_help,
            )

    # 2. Đơn hàng
    with r1_col2:
        with st.container(border=True):
            st.metric(
                label="Đơn hàng",
                value=format_kpi_value("total_orders", ord_curr),
                delta=format_kpi_delta("total_orders", ord_curr, ord_prev, is_valid_prev),
                delta_color="normal",
                help=ord_help,
            )

    # 3. Khách hàng
    with r1_col3:
        with st.container(border=True):
            st.metric(
                label="Khách hàng",
                value=format_kpi_value("total_customers", cust_curr),
                delta=format_kpi_delta("total_customers", cust_curr, cust_prev, is_valid_prev),
                delta_color="normal",
                help=cust_help,
            )

    # ------------------ HÀNG 2: HIỆU QUẢ & VẬN HÀNH (3 THẺ) ------------------
    r2_col1, r2_col2, r2_col3 = st.columns(3)

    # 4. AOV (TB/đơn)
    with r2_col1:
        with st.container(border=True):
            st.metric(
                label="AOV (TB/đơn)",
                value=format_kpi_value("avg_order_value", aov_curr),
                delta=format_kpi_delta("avg_order_value", aov_curr, aov_prev, is_valid_prev),
                delta_color="normal",
                help=aov_help,
            )

    # 5. Đánh giá TB (/5)
    with r2_col2:
        with st.container(border=True):
            st.metric(
                label="Đánh giá TB (/5)",
                value=format_kpi_value("avg_review_score", score_curr),
                delta=format_kpi_delta("avg_review_score", score_curr, score_prev, is_valid_prev),
                delta_color="normal",
                help=score_help,
            )

    # 6. Giao đúng hạn
    with r2_col3:
        with st.container(border=True):
            st.metric(
                label="Giao đúng hạn",
                value=format_kpi_value("on_time_rate", ontime_curr),
                delta=format_kpi_delta("on_time_rate", ontime_curr, ontime_prev, is_valid_prev),
                delta_color="normal",
                help=ontime_help,
            )


def render_highlights_container(kpi_curr, df_monthly, df_top_cat):
    """Hiển thị các nhận định chính từ số liệu thực tế qua st.info/st.success."""
    # 1. Tháng cao nhất & tăng trưởng gần nhất
    if not df_monthly.empty:
        max_rev_idx = df_monthly["revenue"].idxmax()
        peak_month = df_monthly.loc[max_rev_idx, "month"]
        peak_rev = df_monthly.loc[max_rev_idx, "revenue"]
        peak_orders = df_monthly.loc[max_rev_idx, "orders"]

        valid_growth = df_monthly["mom_growth_pct"].dropna()
        latest_growth = valid_growth.iloc[-1] if not valid_growth.empty else 0.0
    else:
        peak_month, peak_rev, peak_orders, latest_growth = "N/A", 0.0, 0, 0.0

    # 2. Danh mục dẫn đầu
    if not df_top_cat.empty:
        raw_top_cat = df_top_cat.iloc[0]["category"]
        top_cat_name = category_label(raw_top_cat)
        top_cat_sales = df_top_cat.iloc[0]["total_sales"]
    else:
        top_cat_name, top_cat_sales = "N/A", 0.0

    # 3. Hiệu quả giao vận
    on_time = kpi_curr["on_time_rate"]
    delay_rate = round(100.0 - on_time, 1)
    avg_delivery = kpi_curr["avg_delivery_days"]
    cust_int = int(kpi_curr["total_customers"])

    i1, i2, i3 = st.columns(3)
    with i1:
        st.success(
            f"🏆 **Kỷ lục doanh thu tháng {peak_month}**\n\n"
            f"Đạt đỉnh **R$ {peak_rev:,.0f}** ({peak_orders:,} đơn). Tốc độ tăng trưởng MoM gần nhất: **{latest_growth:+.2f}%**."
        )
    with i2:
        if delay_rate <= 10.0:
            st.success(
                f"🚚 **Giao đúng hạn đạt {on_time:.1f}%**\n\n"
                f"Thời gian giao TB: **{avg_delivery:.1f} ngày**. Tỷ lệ đơn trễ hạn ở mức an toàn: **{delay_rate:.1f}%**."
            )
        else:
            st.warning(
                f"🚚 **Giao đúng hạn đạt {on_time:.1f}%**\n\n"
                f"Thời gian giao TB: **{avg_delivery:.1f} ngày**. Tỷ lệ trễ hạn cần kiểm soát: **{delay_rate:.1f}%**."
            )
    with i3:
        st.info(
            f"🛍️ **Danh mục chủ lực: {top_cat_name}**\n\n"
            f"Dẫn đầu doanh số với hơn **R$ {top_cat_sales:,.0f}**, phục vụ cơ sở {cust_int:,} khách hàng thực tế."
        )


def render_monthly_revenue_chart(df_monthly):
    """Biểu đồ kết hợp: Cột doanh thu và Đường tăng trưởng MoM."""
    if df_monthly.empty:
        st.subheader("📈 Xu hướng doanh thu theo tháng & tăng trưởng MoM")
        st.info("Không có dữ liệu doanh thu cho khoảng thời gian đã chọn.")
        return

    # Xác định tháng đỉnh và tăng trưởng tổng giai đoạn để sinh tiêu đề động
    peak_row = df_monthly.sort_values("revenue", ascending=False).iloc[0]
    p_parts = peak_row["month"].split("-")
    peak_label = f"T{int(p_parts[1])}/{p_parts[0]}"
    peak_rev_str = f"R$ {int(round(peak_row['revenue'])):,}".replace(",", ".")

    first_row = df_monthly.iloc[0]
    last_row = df_monthly.iloc[-1]
    f_parts = first_row["month"].split("-")
    l_parts = last_row["month"].split("-")
    first_label = f"T{int(f_parts[1])}/{f_parts[0]}"
    last_label = f"T{int(l_parts[1])}/{l_parts[0]}"

    if len(df_monthly) > 1 and first_row["revenue"] > 0:
        tot_growth = (last_row["revenue"] - first_row["revenue"]) / first_row["revenue"] * 100.0
        tot_growth_sign = "+" if tot_growth >= 0 else ""
        tot_growth_str = f"{tot_growth_sign}{tot_growth:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")
        chart_title = f"📈 Doanh thu theo tháng: Đỉnh {peak_label} ({peak_rev_str}) | Tăng trưởng {first_label}–{last_label}: {tot_growth_str}"
    else:
        chart_title = f"📈 Doanh thu tháng {peak_label}: {peak_rev_str}"

    st.subheader(chart_title)

    # Xử lý lọc bỏ điểm MoM tháng đầu và các tháng có doanh thu kỳ trước dưới 5% tháng lớn nhất
    df_plot = df_monthly.copy()
    max_rev = df_plot["revenue"].max()
    threshold = 0.05 * max_rev if max_rev > 0 else 0.0

    mom_clean = []
    has_omitted_low_base = False
    for i in range(len(df_plot)):
        if i == 0:
            mom_clean.append(None)
        elif df_plot.iloc[i - 1]["revenue"] < threshold:
            mom_clean.append(None)
            has_omitted_low_base = True
        else:
            val = df_plot.iloc[i]["mom_growth_pct"]
            mom_clean.append(val if pd.notna(val) else None)

    df_plot["mom_clean"] = mom_clean

    def _fmt_x(m_str):
        parts = m_str.split("-")
        return f"T{int(parts[1])}/{parts[0]}"

    def _fmt_hover(m_str):
        parts = m_str.split("-")
        return f"Tháng {int(parts[1])}/{parts[0]}"

    df_plot["x_label"] = df_plot["month"].apply(_fmt_x)
    df_plot["hover_month"] = df_plot["month"].apply(_fmt_hover)
    df_plot["revenue_formatted"] = df_plot["revenue"].apply(lambda r: f"{int(round(r)):,}".replace(",", "."))
    df_plot["mom_formatted"] = df_plot["mom_clean"].apply(
        lambda x: f"{x:+.1f}%".replace(".", ",") if pd.notna(x) else ""
    )

    # Trục phải (MoM %): đối xứng quanh 0 (range = [-m, m] với m = max(|MoM|) làm tròn lên bội của 10), tick đều
    valid_moms = df_plot["mom_clean"].dropna()
    raw_max = valid_moms.abs().max() if not valid_moms.empty else 10.0
    m = math.ceil(raw_max / 10.0) * 10 if pd.notna(raw_max) and raw_max > 0 else 10
    candidates = [5, 10, 15, 20, 25, 30, 40, 50, 100, 200]
    dtick = min(candidates, key=lambda c: abs(c - (m / 4)))

    fig = go.Figure()

    # Cột doanh thu: màu xanh dương chính #1E88E5
    fig.add_trace(
        go.Bar(
            x=df_plot["x_label"],
            y=df_plot["revenue"],
            name="Doanh thu (BRL)",
            marker_color=PRIMARY_COLOR,
            customdata=df_plot[["hover_month", "revenue_formatted"]],
            hovertemplate="%{customdata[0]}: R$ %{customdata[1]}<extra></extra>",
            yaxis="y1",
        )
    )

    # Đường MoM: màu đỏ #E53935 cả line và marker
    fig.add_trace(
        go.Scatter(
            x=df_plot["x_label"],
            y=df_plot["mom_clean"],
            name="Tăng trưởng MoM (%)",
            mode="lines+markers",
            marker=dict(size=6, color="#E53935"),
            line=dict(color="#E53935", width=2.5),
            customdata=df_plot[["hover_month", "mom_formatted"]],
            hovertemplate="%{customdata[0]}<br>Tăng trưởng MoM: %{customdata[1]}<extra></extra>",
            yaxis="y2",
            connectgaps=False,
        )
    )

    # Thêm đường ngang đứt nét tại 0% bằng add_hline trên yaxis2
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#888888",
        line_width=1.2,
        yref="y2",
    )

    fig.update_layout(
        xaxis=dict(showgrid=False, tickangle=-45),
        yaxis=dict(
            title="Doanh thu thực tế (BRL)",
            showgrid=True,
            tickformat=",.0f",
        ),
        yaxis2=dict(
            title="Tốc độ tăng trưởng MoM (%)",
            overlaying="y",
            side="right",
            showgrid=False,
            ticksuffix="%",
            range=[-m, m],
            dtick=dtick,
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=30, r=40, t=10, b=60),
        height=440,
    )
    show_chart(fig)

    if has_omitted_low_base:
        st.caption("💡 *MoM bỏ qua các tháng đầu do nền doanh thu thấp.*")


def render_overview_tab(kpi_curr, kpi_prev, df_monthly, df_top_cat, filters=None):
    """Render Tab 1: Tổng quan hiệu suất kinh doanh."""
    st.subheader("📊 Tổng quan hiệu suất kinh doanh")
    render_kpi_cards(kpi_curr, kpi_prev, filters)

    st.write("")
    render_highlights_container(kpi_curr, df_monthly, df_top_cat)
    st.write("")

    col_chart, col_side = st.columns([3, 2])

    with col_chart:
        with st.container(border=True):
            render_monthly_revenue_chart(df_monthly)

    with col_side:
        with st.container(border=True):
            st.subheader("📦 Cơ cấu doanh thu theo danh mục (top 5)")
            if df_top_cat.empty:
                st.info("Không có dữ liệu danh mục sản phẩm.")
            else:
                top5_cat = df_top_cat.head(5).sort_values("total_sales", ascending=True).copy()
                top5_cat["category_name"] = top5_cat["category"].map(category_label)
                fig_top5 = px.bar(
                    top5_cat,
                    x="total_sales",
                    y="category_name",
                    orientation="h",
                    text="total_sales",
                    labels={"total_sales": "Doanh số (BRL)", "category_name": "Danh mục"},
                    color="total_sales",
                    color_continuous_scale="Teal",
                )
                fig_top5.update_traces(
                    texttemplate="R$ %{text:,.0f}",
                    textposition="outside",
                )
                fig_top5.update_layout(
                    xaxis=dict(showgrid=False, showticklabels=False),
                    yaxis=dict(showgrid=False),
                    height=345,
                    margin=dict(l=10, r=40, t=20, b=10),
                )
                show_chart(fig_top5)


# ==============================================================================
# HÀM HIỂN THỊ GIAO HÀNG & TRẢI NGHIỆM (TAB 2)
# ==============================================================================

def render_delivery_tab(df_delay, df_reviews, df_states):
    """Render Tab 2: Vận hành giao hàng và trải nghiệm khách hàng."""
    st.subheader("🚚 Vận hành giao hàng & trải nghiệm khách hàng")

    c1, c2 = st.columns([3, 2])

    # Tính toán động điểm đánh giá của đơn đúng hạn vs trễ hạn
    severe_score = None
    on_time_score = None
    if not df_delay.empty:
        sev = df_delay[df_delay["delay_status"].isin(["Trễ 4-7 ngày", "Trễ >7 ngày"])]
        if not sev.empty and sev["orders"].sum() > 0:
            severe_score = (sev["avg_review_score"] * sev["orders"]).sum() / sev["orders"].sum()
        ont = df_delay[df_delay["delay_status"].isin(["Sớm", "Đúng hạn"])]
        if not ont.empty and ont["orders"].sum() > 0:
            on_time_score = (ont["avg_review_score"] * ont["orders"]).sum() / ont["orders"].sum()

    with c1:
        with st.container(border=True):
            st.subheader("⏱️ Tác động của độ trễ giao hàng đến điểm đánh giá")
            if df_delay.empty:
                st.info("Không có dữ liệu thời gian giao hàng.")
            else:
                delay_colors = {
                    "Sớm": "#00897B",
                    "Đúng hạn": "#1E88E5",
                    "Trễ 1-3 ngày": "#FB8C00",
                    "Trễ 4-7 ngày": "#E53935",
                    "Trễ >7 ngày": "#B71C1C",
                }
                colors = [delay_colors.get(s, "#1E88E5") for s in df_delay["delay_status"]]
                fig_delay = px.bar(
                    df_delay,
                    x="delay_status",
                    y="avg_review_score",
                    text="avg_review_score",
                    labels={"delay_status": "Mức độ giao hàng", "avg_review_score": "Điểm đánh giá TB"},
                )
                fig_delay.update_traces(marker_color=colors, texttemplate="%{text:.2f} ⭐", textposition="outside")
                fig_delay.update_layout(
                    yaxis=dict(range=[0, 5.5]),
                    height=380,
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                show_chart(fig_delay)

    with c2:
        with st.container(border=True):
            st.subheader("⭐ Phân bố điểm đánh giá đơn hàng")
            if df_reviews.empty:
                st.info("Không có dữ liệu đánh giá.")
            else:
                fig_dist = px.bar(
                    df_reviews,
                    x="review_score",
                    y="orders",
                    text="orders",
                    labels={"review_score": "Số sao đánh giá", "orders": "Số lượng đơn hàng"},
                )
                fig_dist.update_traces(
                    marker_color=PRIMARY_COLOR,
                    texttemplate="%{text:,}",
                    textposition="outside",
                )
                fig_dist.update_layout(
                    height=380,
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                show_chart(fig_dist)

    st.write("")

    col_state, col_insight = st.columns([3, 2])

    worst_states_str = None
    if not df_states.empty and len(df_states) > 2:
        # Lọc các bang đủ điều kiện (từ 500 đơn trở lên, có fallback nếu ít đơn)
        df_eligible = df_states[df_states["orders"] >= 500].copy()
        if len(df_eligible) < 3:
            df_eligible = df_states[df_states["orders"] >= 10].copy()
            if len(df_eligible) < 3:
                df_eligible = df_states.copy()

        worst_states = df_eligible.sort_values("delayed_rate", ascending=False).head(2)
        if len(worst_states) >= 2:
            s1 = worst_states.iloc[0]
            s2 = worst_states.iloc[1]
            s1_rate = f"{s1['delayed_rate']:.1f}%".replace(".", ",")
            s2_rate = f"{s2['delayed_rate']:.1f}%".replace(".", ",")
            worst_states_str = f"{state_label(s1['customer_state'])} ({s1_rate}) và {state_label(s2['customer_state'])} ({s2_rate})"
        elif len(worst_states) == 1:
            s1 = worst_states.iloc[0]
            s1_rate = f"{s1['delayed_rate']:.1f}%".replace(".", ",")
            worst_states_str = f"{state_label(s1['customer_state'])} ({s1_rate})"

    with col_state:
        with st.container(border=True):
            if df_states.empty:
                st.subheader("🗺️ Tỷ lệ giao hàng trễ theo bang")
                st.info("Không có dữ liệu bang/khu vực cho khoảng thời gian này.")
            elif len(df_states) <= 2:
                st.subheader("🗺️ Tỷ lệ giao hàng trễ theo bang")
                # Ẩn khung so sánh bang khi bộ lọc chỉ còn 1-2 bang
                selected_names = ", ".join([state_label(s) for s in df_states["customer_state"]])
                st.info(
                    f"ℹ️ Bộ lọc hiện tại chỉ chọn {len(df_states)} bang ({selected_names}). "
                    f"Vui lòng chọn từ 3 bang trở lên để hiển thị biểu đồ so sánh tỷ lệ giao trễ giữa các khu vực."
                )
            else:
                # 1. Lọc tất cả bang đủ điều kiện (từ 500 đơn trở lên, fallback nếu ít đơn)
                df_plot_states = df_states[df_states["orders"] >= 500].copy()
                caption_text = "💡 *Chỉ hiển thị các bang có từ 500 đơn hàng trở lên để đảm bảo độ tin cậy thống kê.*"
                if len(df_plot_states) < 3:
                    df_plot_states = df_states[df_states["orders"] >= 10].copy()
                    caption_text = "💡 *Hiển thị các bang có từ 10 đơn hàng trở lên do tập dữ liệu ít.*"
                    if len(df_plot_states) < 3:
                        df_plot_states = df_states.copy()
                        caption_text = "💡 *Hiển thị toàn bộ các bang ghi nhận trong khoảng thời gian lọc.*"

                if len(df_plot_states) <= 2:
                    st.subheader("🗺️ Tỷ lệ giao hàng trễ theo bang")
                    selected_names = ", ".join([state_label(s) for s in df_plot_states["customer_state"]])
                    st.info(
                        f"ℹ️ Chỉ có {len(df_plot_states)} bang đủ điều kiện đơn hàng ({selected_names}). "
                        f"Vui lòng mở rộng khoảng thời gian hoặc chọn thêm bang để thực hiện so sánh khu vực."
                    )
                else:
                    # Tính tỷ lệ trễ trung bình toàn sàn (có trọng số theo số đơn)
                    total_st_orders = df_states["orders"].sum()
                    weighted_avg = (
                        (df_states["delayed_rate"] * df_states["orders"]).sum() / total_st_orders
                        if total_st_orders > 0 else 0.0
                    )
                    weighted_avg_str = f"{weighted_avg:.1f}%".replace(".", ",")

                    # 2. Nhãn trục dùng state_label, tooltip dùng custom_data
                    df_plot_states["state_name"] = df_plot_states["customer_state"].map(state_label)
                    df_plot_states["text_label"] = df_plot_states["delayed_rate"].apply(lambda x: f"{x:.1f}%".replace(".", ","))
                    df_plot_states["orders_formatted"] = df_plot_states["orders"].apply(lambda x: f"{x:,}")

                    # 3. Tiêu đề sinh động sinh từ dữ liệu bằng f-string (nêu bang cao nhất và thấp nhất)
                    sorted_desc = df_plot_states.sort_values("delayed_rate", ascending=False)
                    highest_row = sorted_desc.iloc[0]
                    lowest_row = sorted_desc.iloc[-1]
                    high_label = highest_row["state_name"]
                    high_rate = f"{highest_row['delayed_rate']:.1f}%".replace(".", ",")
                    low_label = lowest_row["state_name"]
                    low_rate = f"{lowest_row['delayed_rate']:.1f}%".replace(".", ",")
                    chart_title = f"🗺️ Tỷ lệ giao trễ: {high_label} cao nhất ({high_rate}), {low_label} thấp nhất ({low_rate})"

                    st.subheader(chart_title)

                    # 4. Sắp xếp từ cao xuống thấp (trên biểu đồ ngang, ascending=True để giá trị cao nhất nằm ở đỉnh cột)
                    df_plot_states = df_plot_states.sort_values("delayed_rate", ascending=True)

                    # 5. Thang màu đỏ rõ nét trên nền tối: [[0, "#FFCDD2"], [0.5, "#EF5350"], [1, "#B71C1C"]]
                    fig_state_delay = px.bar(
                        df_plot_states,
                        x="delayed_rate",
                        y="state_name",
                        orientation="h",
                        text="text_label",
                        custom_data=["text_label", "orders_formatted"],
                        labels={"delayed_rate": "Tỷ lệ trễ (%)", "state_name": "Bang"},
                        color="delayed_rate",
                        color_continuous_scale=[[0, "#FFCDD2"], [0.5, "#EF5350"], [1, "#B71C1C"]],
                    )
                    # Tooltip hiện: tên bang, tỷ lệ trễ, số đơn
                    fig_state_delay.update_traces(
                        textposition="outside",
                        hovertemplate="<b>%{y}</b><br>Tỷ lệ trễ: %{customdata[0]}<br>Số đơn: %{customdata[1]}<extra></extra>",
                    )
                    chart_height = max(400, len(df_plot_states) * 26 + 60)
                    fig_state_delay.update_layout(
                        height=chart_height,
                        coloraxis_showscale=False,
                        xaxis=dict(showgrid=True, zeroline=False),
                        margin=dict(l=10, r=45, t=10, b=10),
                    )

                    # 6. Thêm đường dọc đứt nét tại tỷ lệ trễ trung bình toàn sàn (có trọng số)
                    fig_state_delay.add_vline(
                        x=weighted_avg,
                        line_dash="dash",
                        line_color="#757575",
                        annotation_text=f"Trung bình: {weighted_avg_str}",
                        annotation_position="top right",
                        annotation_font=dict(size=12, color="#FFFFFF"),
                        annotation_bgcolor="rgba(33, 37, 41, 0.85)",
                    )

                    show_chart(fig_state_delay)
                    st.caption(caption_text)

    with col_insight:
        with st.container(border=True):
            st.subheader("💡 Nhận định vận hành giao vận")

            if severe_score is not None and on_time_score is not None:
                on_time_str = f"{on_time_score:.2f}".replace(".", ",")
                severe_str = f"{severe_score:.2f}".replace(".", ",")
                st.warning(
                    f"⏱️ **Tác động quyết định của độ trễ:**\n\n"
                    f"Đơn hàng giao đúng hạn đạt điểm số trung bình **{on_time_str} sao**. "
                    f"Khi đơn hàng bị trễ trên 3 ngày, điểm số đánh giá giảm sâu xuống chỉ còn **{severe_str} sao**."
                )
            elif on_time_score is not None:
                on_time_str = f"{on_time_score:.2f}".replace(".", ",")
                st.success(
                    f"⏱️ **Chất lượng giao hàng ổn định:**\n\n"
                    f"Đơn hàng đúng hạn duy trì mức đánh giá cao **{on_time_str} sao** trên toàn hệ thống."
                )

            st.write("")

            if len(df_states) <= 2:
                st.info(
                    "🗺️ **So sánh khu vực:**\n\n"
                    "Bộ lọc hiện tại chỉ chọn 1-2 bang nên không áp dụng so sánh tương đối giữa các khu vực. "
                    "Hãy chọn thêm bang nếu bạn muốn đối chiếu hiệu quả giao vận."
                )
            elif worst_states_str:
                st.info(
                    f"🗺️ **Đặc thù giao hàng theo khu vực:**\n\n"
                    f"Tỷ lệ giao trễ ghi nhận cao nhất tại các bang **{worst_states_str}**. "
                    f"Do tập dữ liệu hiện tại chưa xác định chi tiết nguyên nhân trễ (như thời gian xử lý kho bãi, đối tác vận chuyển hay đặc thù khoảng cách địa lý), "
                    f"doanh nghiệp có thể cân nhắc khảo sát thêm quy trình xử lý đơn hàng chặng cuối hoặc phối hợp với các đơn vị giao vận tại địa phương."
                )
            else:
                st.success(
                    "🗺️ **Vùng giao nhận cân bằng:**\n\n"
                    "Không ghi nhận bang nào có tỷ lệ chậm trễ bất thường trong tập dữ liệu đã lọc."
                )


# ==============================================================================
# HÀM HIỂN THỊ DANH MỤC SẢN PHẨM (TAB 3)
# ==============================================================================

def render_products_tab(top_n_choice, df_items):
    """Render Tab 3: Phân tích danh mục sản phẩm."""
    st.subheader("🛍️ Phân tích danh mục sản phẩm")

    col_ctrl, _ = st.columns([1, 2])
    with col_ctrl:
        metric_mode = st.radio(
            "Xếp hạng danh mục theo:",
            options=["Doanh thu (BRL)", "Số lượng sản phẩm bán (Items)"],
            horizontal=True,
        )

    if isinstance(df_items, pd.DataFrame):
        df_cat = top_categories(df_items, top_n=top_n_choice)
    else:
        items_fact = load_items_fact()
        df_cat = top_categories(apply_filters(items_fact, df_items), top_n=top_n_choice)

    if df_cat.empty:
        st.info("Không tìm thấy sản phẩm nào khớp với bộ lọc.")
        return

    is_revenue = metric_mode.startswith("Doanh thu")
    sort_col = "total_sales" if is_revenue else "items_sold"
    col_label = "Doanh thu (BRL)" if is_revenue else "Số lượng bán (Items)"

    df_cat_sorted = df_cat.sort_values(sort_col, ascending=True).copy()
    df_cat_sorted["category_name"] = df_cat_sorted["category"].map(category_label)

    col_chart, col_side = st.columns([3, 2])

    with col_chart:
        with st.container(border=True):
            st.subheader(f"🏆 Top 10 danh mục dẫn đầu theo {col_label.lower()}")
            fig_cat = px.bar(
                df_cat_sorted,
                x=sort_col,
                y="category_name",
                orientation="h",
                labels={sort_col: col_label, "category_name": "Danh mục"},
                color=sort_col,
                color_continuous_scale="Teal",
                text=sort_col,
            )
            fig_cat.update_traces(
                texttemplate="R$ %{text:,.0f}" if is_revenue else "%{text:,}",
                textposition="outside",
            )
            fig_cat.update_layout(
                height=480,
                xaxis=dict(showgrid=False, showticklabels=False),
                margin=dict(l=10, r=50, t=20, b=10),
            )
            show_chart(fig_cat)

    with col_side:
        with st.container(border=True):
            st.subheader("💡 Nhận định danh mục hàng hóa")

            top_cat = df_cat.iloc[0]
            top_name = category_label(top_cat["category"])
            top_sales = top_cat["total_sales"]
            top_items = top_cat["items_sold"]
            total_top10_sales = df_cat["total_sales"].sum()
            top1_share = (top_sales / total_top10_sales * 100) if total_top10_sales > 0 else 0
            top3_share = (df_cat.head(3)["total_sales"].sum() / total_top10_sales * 100) if total_top10_sales > 0 else 0

            st.success(
                f"🏆 **Ngành hàng chủ lực: {top_name}**\n\n"
                f"Chiếm **{top1_share:.1f}%** tổng doanh thu trong top 10 với giá trị **R$ {top_sales:,.0f}** "
                f"({top_items:,} sản phẩm bán ra). Đây là nhóm sản phẩm xương sống của sàn."
            )

            st.write("")

            st.info(
                f"📦 **Độ tập trung thị phần danh mục:**\n\n"
                f"Top 3 ngành hàng lớn nhất chiếm **{top3_share:.1f}%** toàn bộ doanh thu nhóm dẫn đầu. "
                f"Cần duy trì chính sách tồn kho và hợp tác với nhà bán hàng uy tín trong nhóm này."
            )


# ==============================================================================
# HÀM HIỂN THỊ KHÁCH HÀNG & THANH TOÁN (TAB 4)
# ==============================================================================

def render_customers_tab(df_states, repeat_rate, df_payment, df_heatmap):
    """Render Tab 4: Khách hàng, phương thức thanh toán và địa lý."""
    st.subheader("👥 Phân tích khách hàng & khu vực địa lý")

    col1, col2 = st.columns([3, 2])

    total_state_rev = df_states["revenue"].sum() if not df_states.empty else 0
    if not df_states.empty and total_state_rev > 0:
        top_state_row = df_states.iloc[0]
        top_state_code = top_state_row["customer_state"]
        top_state_name = state_label(top_state_code)
        top_state_rev = top_state_row["revenue"]
        top_state_pct = (top_state_rev / total_state_rev) * 100
        state_title = f"{top_state_name} dẫn đầu thị phần ({top_state_pct:.1f}% doanh thu)"
    else:
        top_state_name, top_state_rev, top_state_pct = "N/A", 0, 0
        state_title = "Doanh thu theo bang"

    total_pay_rev = df_payment["revenue"].sum() if not df_payment.empty else 0
    if not df_payment.empty and total_pay_rev > 0:
        top_pay = df_payment.sort_values("revenue", ascending=False).iloc[0]
        top_pay_name = top_pay["payment_type"].replace("_", " ").title()
        top_pay_pct = (top_pay["revenue"] / total_pay_rev) * 100
        pay_title = f"{top_pay_name} chiếm {top_pay_pct:.1f}% tổng thanh toán"
    else:
        top_pay_name, top_pay_pct = "N/A", 0
        pay_title = "Cơ cấu phương thức thanh toán"

    with col1:
        with st.container(border=True):
            st.subheader(f"🗺️ {state_title}")
            if df_states.empty:
                st.info("Không có dữ liệu bang.")
            else:
                top_states_rev = df_states.head(10).sort_values("revenue", ascending=True).copy()
                top_states_rev["state_name"] = top_states_rev["customer_state"].map(state_label)

                fig_state_rev = px.bar(
                    top_states_rev,
                    x="revenue",
                    y="state_name",
                    orientation="h",
                    text="revenue",
                    labels={"revenue": "Doanh thu (BRL)", "state_name": "Bang"},
                    color="revenue",
                    color_continuous_scale="Blues",
                )
                fig_state_rev.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
                fig_state_rev.update_layout(
                    height=380,
                    xaxis=dict(showgrid=False, showticklabels=False),
                    margin=dict(l=10, r=50, t=20, b=10),
                )
                show_chart(fig_state_rev)

    with col2:
        with st.container(border=True):
            st.subheader(f"💳 {pay_title}")
            if df_payment.empty:
                st.info("Không có dữ liệu thanh toán.")
            else:
                fig_donut = px.pie(
                    df_payment,
                    names="payment_type",
                    values="revenue",
                    hole=0.45,
                    color_discrete_sequence=DONUT_COLORS,
                )
                fig_donut.update_traces(
                    textinfo="percent+label",
                    hoverinfo="label+value+percent",
                )
                fig_donut.update_layout(
                    showlegend=False,
                    height=380,
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                show_chart(fig_donut)

    st.write("")

    col_heat, col_side = st.columns([3, 2])

    with col_heat:
        with st.container(border=True):
            if df_heatmap.empty:
                st.info("Không có dữ liệu khung giờ đặt hàng.")
            else:
                day_map = {
                    0: "Chủ nhật",
                    1: "Thứ hai",
                    2: "Thứ ba",
                    3: "Thứ tư",
                    4: "Thứ năm",
                    5: "Thứ sáu",
                    6: "Thứ bảy",
                }
                df_heat_display = df_heatmap.copy()
                df_heat_display["day_name"] = df_heat_display["day_of_week"].map(day_map)

                matrix = df_heat_display.pivot(index="day_name", columns="hour", values="orders").fillna(0)
                day_order = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
                matrix = matrix.reindex([d for d in day_order if d in matrix.index])

                orders_by_hour = df_heatmap.groupby("hour")["orders"].sum()
                series_24 = orders_by_hour.reindex(range(24), fill_value=0)
                rolling_4 = [series_24.iloc[i:i+4].sum() for i in range(21)]
                best_start = int(pd.Series(rolling_4).idxmax()) if rolling_4 else 10
                best_end = best_start + 4
                window_pct = (rolling_4[best_start] / series_24.sum() * 100) if series_24.sum() > 0 else 0

                heat_title = f"🔥 Khung giờ cao điểm: {best_start}h - {best_end}h (chiếm {window_pct:.1f}% lượng đơn)"
                st.subheader(heat_title)

                fig_heat = px.imshow(
                    matrix,
                    labels=dict(x="Khung giờ trong ngày (0 - 23h)", y="Thứ trong tuần", color="Số đơn"),
                    x=matrix.columns,
                    y=matrix.index,
                    color_continuous_scale="Viridis",
                )
                fig_heat.update_layout(
                    height=360,
                    margin=dict(l=10, r=10, t=20, b=10),
                )
                show_chart(fig_heat)

    with col_side:
        with st.container(border=True):
            st.subheader("🔁 Khách hàng quay lại & thanh toán")

            st.metric(
                label="Tỷ lệ khách mua lại (Repeat Rate)",
                value=f"{repeat_rate:.2f}%".replace(".", ","),
                help="Tỷ lệ khách hàng (customer_unique_id) có từ 2 đơn hàng thành công trở lên trong tập dữ liệu lọc.",
            )

            st.caption(
                "💡 *Đặc thù thị trường TMĐT Brazil có tỷ lệ khách hàng quay lại khoảng 3-5%, "
                "phần lớn khách hàng mua các sản phẩm giá trị lớn theo chu kỳ dài.*"
            )

            st.write("")

            st.info(
                f"💳 **Thói quen thanh toán bằng {top_pay_name}:**\n\n"
                f"Phương thức {top_pay_name} chiếm ưu thế (**{top_pay_pct:.1f}%**), "
                "khẳng định thị hiếu sử dụng thẻ và các chương trình trả góp tại thị trường Brazil."
            )


# ==============================================================================
# HÀM RENDER KHU VỰC XUẤT BÁO CÁO (UC04)
# ==============================================================================

EXPORT_ORDERS_COLS = [
    "order_id",
    "customer_unique_id",
    "customer_state",
    "order_status",
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "payment_total",
    "payment_type",
    "review_score",
    "delivery_days",
    "delay_days",
    "delay_status",
]
MAX_EXPORT_ROWS = 50_000


def render_export_section(kpi_curr, df_orders):
    """
    Khu vực xuất báo cáo (UC04) cuối trang dashboard:
    - Nút tải CSV (encoding utf-8-sig)
    - Nút tải Excel (.xlsx qua BytesIO + openpyxl gồm 2 sheets: 'KPI' và 'Don hang')
    - Giới hạn 50.000 dòng; nếu vượt hiển thị st.warning và cắt lấy 50.000 dòng
    - Tên file kèm timestamp: YYYYMMDD_HHMMSS
    - Vô hiệu hóa nút nếu dữ liệu trống
    """
    st.subheader("📥 Xuất báo cáo dữ liệu (UC04)")

    with st.container(border=True):
        is_empty = df_orders is None or df_orders.empty
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"ecommerce_report_{now_str}.csv"
        excel_filename = f"ecommerce_report_{now_str}.xlsx"

        csv_bytes = b""
        excel_bytes = b""

        if not is_empty:
            available_cols = [c for c in EXPORT_ORDERS_COLS if c in df_orders.columns]
            df_export = df_orders[available_cols].copy()
            total_rows = len(df_export)

            if total_rows > MAX_EXPORT_ROWS:
                st.warning(
                    f"⚠️ Dữ liệu hiện có **{total_rows:,}** dòng, vượt quá giới hạn **{MAX_EXPORT_ROWS:,}** dòng xuất. "
                    f"Hệ thống tự động cắt lấy **{MAX_EXPORT_ROWS:,}** dòng đầu tiên cho tệp xuất."
                )
                df_export = df_export.iloc[:MAX_EXPORT_ROWS]

            csv_bytes = df_export.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

            if kpi_curr is not None:
                kpi_data = [
                    {"Chỉ số": "Tổng doanh thu", "Giá trị": f"R$ {kpi_curr.get('total_revenue', 0):,.2f}"},
                    {"Chỉ số": "Số đơn hàng thành công", "Giá trị": f"{int(kpi_curr.get('total_orders', 0)):,}"},
                    {"Chỉ số": "Giá trị trung bình đơn (AOV)", "Giá trị": f"R$ {kpi_curr.get('avg_order_value', 0):,.2f}"},
                    {"Chỉ số": "Điểm đánh giá trung bình", "Giá trị": f"{kpi_curr.get('avg_review_score', 0):.2f} / 5,0"},
                    {"Chỉ số": "Tỷ lệ giao đúng hạn", "Giá trị": f"{kpi_curr.get('on_time_rate', 0):.2f}%"},
                    {"Chỉ số": "Số khách hàng thực tế", "Giá trị": f"{int(kpi_curr.get('total_customers', 0)):,}"},
                    {"Chỉ số": "Thời gian giao hàng TB (ngày)", "Giá trị": f"{kpi_curr.get('avg_delivery_days', 0):.2f}"},
                ]
                df_kpi_sheet = pd.DataFrame(kpi_data)
            else:
                df_kpi_sheet = pd.DataFrame(columns=["Chỉ số", "Giá trị"])

            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                df_kpi_sheet.to_excel(writer, sheet_name="KPI", index=False)
                df_export.to_excel(writer, sheet_name="Don hang", index=False)
            excel_bytes = excel_buffer.getvalue()

            st.caption(
                f"Sẵn sàng xuất **{len(df_export):,}** đơn hàng theo bộ lọc hiện tại. "
                "Tệp Excel gồm 2 sheet: **KPI** (chỉ số hiển thị) và **Don hang** (chi tiết các đơn hàng)."
            )
        else:
            st.info("Không có dữ liệu đơn hàng nào theo bộ lọc hiện tại để xuất.")

        col_csv, col_excel = st.columns(2)
        with col_csv:
            st.download_button(
                label="📥 Tải báo cáo CSV (.csv)",
                data=csv_bytes,
                file_name=csv_filename,
                mime="text/csv",
                disabled=is_empty,
                use_container_width=True,
            )
        with col_excel:
            st.download_button(
                label="📊 Tải báo cáo Excel (.xlsx)",
                data=excel_bytes,
                file_name=excel_filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                disabled=is_empty,
                use_container_width=True,
            )


# ==============================================================================
# HÀM MAIN ĐIỀU PHỐI CHÍNH
# ==============================================================================

def main():
    # 1. Render Sidebar bộ lọc và lấy điều kiện
    filters = render_sidebar_filters()

    # 2. Tiêu đề ứng dụng
    start_date = filters["start_date"]
    end_date = filters["end_date"]
    st.title("🛍️ E-commerce executive analytics dashboard")
    st.markdown(
        f"**Khoảng thời gian:** `{start_date} → {end_date}` | "
        "Nền tảng giám sát sức khỏe kinh doanh, vận hành giao vận và phân tích chân dung khách hàng sàn Olist."
    )
    st.divider()

    # 3. Nạp dữ liệu Facts (Chỉ hiển thị spinner trong lần nạp dữ liệu đầu)
    if "facts_loaded" not in st.session_state:
        with st.spinner("⏳ Đang nạp dữ liệu toàn sàn vào bộ nhớ (chỉ chạy lần đầu)..."):
            orders_fact = load_orders_fact()
            items_fact = load_items_fact()
            st.session_state["facts_loaded"] = True
    else:
        orders_fact = load_orders_fact()
        items_fact = load_items_fact()

    # 4. Áp dụng bộ lọc in-memory siêu tốc bằng Pandas mask (<15ms)
    df_orders = apply_filters(orders_fact, filters)
    df_items = apply_filters(items_fact, filters)

    # 5. Kiểm tra trường hợp lọc ra 0 dòng dữ liệu
    if df_orders.empty:
        st.info(
            "ℹ️ **Không tìm thấy đơn hàng nào khớp với bộ lọc hiện tại!** "
            "Vui lòng mở rộng khoảng ngày hoặc chọn lại Bang / Danh mục trên thanh Sidebar."
        )
        render_export_section(None, df_orders)
        return

    # 6. Tính toán toàn bộ chỉ số phân tích trực tiếp từ bộ nhớ RAM
    kpi_curr = kpi_extended(df_orders)
    kpi_prev = kpi_previous_period(orders_fact, filters)

    df_monthly = monthly_revenue(df_orders)
    df_delay = delay_vs_review(df_orders)
    df_reviews = review_distribution(df_orders)
    df_states = revenue_by_state(df_orders)
    df_payment = payment_mix(df_orders)
    repeat_rate = repeat_customer_rate(df_orders)
    df_heatmap = orders_heatmap(df_orders)
    df_top_cat = top_categories(df_items, top_n=10)

    # 7. Phân chia 4 Tabs chức năng chuyên sâu với tiêu đề chữ thường (chỉ viết hoa chữ đầu)
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Tổng quan",
        "🚚 Giao hàng & trải nghiệm",
        "🛍️ Sản phẩm",
        "👥 Khách hàng & khu vực",
    ])

    with tab1:
        render_overview_tab(kpi_curr, kpi_prev, df_monthly, df_top_cat, filters)

    with tab2:
        render_delivery_tab(df_delay, df_reviews, df_states)

    with tab3:
        render_products_tab(10, df_items)

    with tab4:
        render_customers_tab(df_states, repeat_rate, df_payment, df_heatmap)

    # 8. Khu vực xuất báo cáo (UC04)
    st.write("")
    st.divider()
    render_export_section(kpi_curr, df_orders)


if __name__ == "__main__":
    main()