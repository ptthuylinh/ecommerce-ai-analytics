"""
E-Commerce Executive Performance Dashboard.
Được cấu trúc thành 4 Tabs chuyên sâu:
1. Tổng quan (KPIs, Doanh thu MoM, Khung Điểm nhấn tự động)
2. Giao hàng & Trải nghiệm (Phân tích mức trễ, Review score, Tỷ lệ trễ theo bang)
3. Sản phẩm (Top 10 danh mục theo doanh thu hoặc số lượng)
4. Khách hàng & Khu vực (Phân bố bang, Repeat customer rate, Payment mix donut, Heatmap đặt hàng)
"""

import sys
import os
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Thêm thư mục gốc vào path để import các module từ src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.ui.filters import render_sidebar_filters  # noqa: E402
from src.db import (  # noqa: E402
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

# 1. Bảng màu thống nhất (Design System)
PRIMARY_COLOR = "#1E88E5"      # Xanh dương đậm chủ đạo
PRIMARY_LIGHT = "#90CAF9"      # Xanh dương nhạt
ALERT_COLOR = "#E53935"        # Đỏ cam cảnh báo
SUCCESS_COLOR = "#2E7D32"      # Xanh lá tích cực
ACCENT_COLOR = "#FB8C00"       # Cam nhấn
BACKGROUND_TEMPLATE = "plotly_white"

# 2. Cấu hình trang Streamlit
st.set_page_config(
    page_title="E-Commerce Analytics Executive Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# 3. Hàm hiển thị biểu đồ tương thích phiên bản Streamlit
def show_chart(fig):
    """Hiển thị biểu đồ Plotly co giãn theo khung chứa với width='stretch'."""
    st.plotly_chart(fig, width="stretch")


# 4. Các hàm truy vấn được bọc cache bằng @st.cache_data
# Chuyển đổi tham số thành các kiểu hashable (string / tuple)
@st.cache_data(ttl=3600)
def cached_kpi_extended(start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_kpi_extended(f)


@st.cache_data(ttl=3600)
def cached_kpi_previous_period(start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_kpi_previous_period(f)


@st.cache_data(ttl=3600)
def cached_monthly_revenue(start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_monthly_revenue(f)


@st.cache_data(ttl=3600)
def cached_delay_vs_review(start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_delay_vs_review(f)


@st.cache_data(ttl=3600)
def cached_review_distribution(start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_review_distribution(f)


@st.cache_data(ttl=3600)
def cached_revenue_by_state(start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_revenue_by_state(f)


@st.cache_data(ttl=3600)
def cached_payment_mix(start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_payment_mix(f)


@st.cache_data(ttl=3600)
def cached_repeat_customer_rate(start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_repeat_customer_rate(f)


@st.cache_data(ttl=3600)
def cached_orders_heatmap(start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_orders_heatmap(f)


@st.cache_data(ttl=3600)
def cached_top_categories(top_n, start_date, end_date, states, categories, statuses):
    f = {"start_date": start_date, "end_date": end_date, "states": states, "categories": categories, "statuses": statuses}
    return get_top_categories(top_n=top_n, filters=f)


# ==============================================================================
# HÀM RENDER TỪNG PHẦN GIAO DIỆN VÀ BIỂU ĐỒ
# ==============================================================================

def render_kpi_cards(kpi_curr, kpi_prev):
    """Hiển thị 6 thẻ KPI kèm delta so sánh với kỳ liền trước."""
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    # 1. Doanh thu
    rev_curr = kpi_curr["total_revenue"]
    rev_prev = kpi_prev["total_revenue"]
    rev_delta = rev_curr - rev_prev if rev_prev > 0 else None
    with c1:
        st.metric(
            label="💰 Tổng doanh thu",
            value=f"R$ {rev_curr:,.0f}",
            delta=f"R$ {rev_delta:+,.0f}" if rev_delta is not None else None,
            delta_color="normal",
            help="Tổng giá trị thanh toán thực tế của các đơn hàng thành công.",
        )

    # 2. Đơn thành công
    ord_curr = int(kpi_curr["total_orders"])
    ord_prev = int(kpi_prev["total_orders"])
    ord_delta = ord_curr - ord_prev if ord_prev > 0 else None
    with c2:
        st.metric(
            label="📦 Đơn thành công",
            value=f"{ord_curr:,}",
            delta=f"{ord_delta:+,}" if ord_delta is not None else None,
            delta_color="normal",
            help="Số lượng đơn hàng có trạng thái delivered.",
        )

    # 3. Giá trị trung bình đơn hàng (AOV)
    aov_curr = kpi_curr["avg_order_value"]
    aov_prev = kpi_prev["avg_order_value"]
    aov_delta = aov_curr - aov_prev if aov_prev > 0 else None
    with c3:
        st.metric(
            label="🏷️ AOV (Giá trị ĐH)",
            value=f"R$ {aov_curr:,.1f}",
            delta=f"R$ {aov_delta:+,.1f}" if aov_delta is not None else None,
            delta_color="normal",
            help="Giá trị trung bình của mỗi đơn hàng (Average Order Value).",
        )

    # 4. Điểm đánh giá trung bình
    rev_score_curr = kpi_curr["avg_review_score"]
    rev_score_prev = kpi_prev["avg_review_score"]
    rev_score_delta = rev_score_curr - rev_score_prev if rev_score_prev > 0 else None
    with c4:
        st.metric(
            label="⭐ Điểm đánh giá TB",
            value=f"{rev_score_curr:.2f} / 5.0",
            delta=f"{rev_score_delta:+.2f}" if rev_score_delta is not None else None,
            delta_color="normal",
            help="Điểm số đánh giá trung bình từ khách hàng (1 đến 5 sao).",
        )

    # 5. Tỷ lệ giao đúng hạn
    ontime_curr = kpi_curr["on_time_rate"]
    ontime_prev = kpi_prev["on_time_rate"]
    ontime_delta = ontime_curr - ontime_prev if ontime_prev > 0 else None
    with c5:
        st.metric(
            label="⏱️ Giao đúng hạn",
            value=f"{ontime_curr:.1f}%",
            delta=f"{ontime_delta:+.1f}%" if ontime_delta is not None else None,
            delta_color="normal",
            help="Tỷ lệ đơn hàng giao thành công trước hoặc đúng ngày giao dự kiến.",
        )

    # 6. Khách hàng duy nhất
    cust_curr = int(kpi_curr["total_customers"])
    cust_prev = int(kpi_prev["total_customers"])
    cust_delta = cust_curr - cust_prev if cust_prev > 0 else None
    with c6:
        st.metric(
            label="👥 Khách hàng thực",
            value=f"{cust_curr:,}",
            delta=f"{cust_delta:+,}" if cust_delta is not None else None,
            delta_color="normal",
            help="Số lượng cá nhân khách hàng duy nhất (theo customer_unique_id).",
        )


def render_highlights_container(kpi_curr, df_monthly, df_top_cat):
    """Tự động sinh 3-4 câu nhận định kinh doanh từ dữ liệu bằng f-string (không dùng LLM)."""
    # 1. Tháng cao nhất
    if not df_monthly.empty:
        max_rev_idx = df_monthly["revenue"].idxmax()
        peak_month = df_monthly.loc[max_rev_idx, "month"]
        peak_rev = df_monthly.loc[max_rev_idx, "revenue"]
        peak_orders = df_monthly.loc[max_rev_idx, "orders"]

        # Tăng trưởng tháng gần nhất
        valid_growth = df_monthly["mom_growth_pct"].dropna()
        latest_growth = valid_growth.iloc[-1] if not valid_growth.empty else 0.0
    else:
        peak_month, peak_rev, peak_orders, latest_growth = "N/A", 0.0, 0, 0.0

    # 2. Danh mục dẫn đầu
    if not df_top_cat.empty:
        top_cat_name = df_top_cat.iloc[0]["category"]
        top_cat_sales = df_top_cat.iloc[0]["total_sales"]
    else:
        top_cat_name, top_cat_sales = "N/A", 0.0

    # 3. Tỷ lệ giao trễ
    on_time = kpi_curr["on_time_rate"]
    delay_rate = round(100.0 - on_time, 1)
    avg_delivery = kpi_curr["avg_delivery_days"]

    with st.container(border=True):
        st.subheader("💡 Điểm Nhấn Sức Khỏe Kinh Doanh (Tự động tổng hợp)")
        st.markdown(
            f"""
            * 🏆 **Tháng đạt đỉnh doanh thu:** Tháng **{peak_month}** thiết lập kỷ lục doanh thu **R$ {peak_rev:,.0f}** với tổng cộng **{peak_orders:,} đơn hàng** thành công.
            * 📈 **Tăng trưởng MoM gần nhất:** Tốc độ tăng trưởng doanh thu tháng gần nhất đạt **{latest_growth:+.2f}%** so với tháng liền trước.
            * 🛍️ **Danh mục sản phẩm chủ lực:** Nhóm **'{top_cat_name}'** giữ vị trí số 1 toàn sàn với doanh số vượt **R$ {top_cat_sales:,.0f}**.
            * 🚚 **Hiệu quả giao vận:** Tỷ lệ đơn trễ hẹn là **{delay_rate:.1f}%**, với thời gian vận chuyển trung bình từ khi đặt đến khi nhận là **{avg_delivery:.1f} ngày**.
            """
        )


def render_monthly_revenue_chart(df_monthly):
    """Biểu đồ kết hợp (Combo Chart): Cột doanh thu (BRL) và Đường tăng trưởng MoM (%)."""
    st.subheader("📈 Doanh thu theo Tháng & Tốc độ Tăng trưởng MoM")

    if df_monthly.empty:
        st.info("ℹ️ Không có dữ liệu doanh thu cho khoảng thời gian đã chọn.")
        return

    fig = go.Figure()

    # Cột doanh thu
    fig.add_trace(
        go.Bar(
            x=df_monthly["month"],
            y=df_monthly["revenue"],
            name="Doanh thu (BRL)",
            marker_color=PRIMARY_COLOR,
            hovertemplate="Tháng %{x}<br>Doanh thu: R$ %{y:,.2f}<extra></extra>",
            yaxis="y1",
        )
    )

    # Đường MoM %
    fig.add_trace(
        go.Scatter(
            x=df_monthly["month"],
            y=df_monthly["mom_growth_pct"],
            name="Tăng trưởng MoM (%)",
            mode="lines+markers",
            marker=dict(size=7, color=ALERT_COLOR),
            line=dict(color=ALERT_COLOR, width=2.5),
            hovertemplate="Tháng %{x}<br>Tăng trưởng MoM: %{y:+.2f}%<extra></extra>",
            yaxis="y2",
        )
    )

    fig.update_layout(
        template=BACKGROUND_TEMPLATE,
        title="Xu hướng Doanh thu hàng tháng phản ánh quy mô kinh doanh mở rộng ổn định",
        xaxis=dict(title="Tháng đặt hàng", tickangle=-45),
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
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=60, b=40),
        height=450,
    )
    show_chart(fig)


def render_overview_tab(kpi_curr, kpi_prev, df_monthly, df_top_cat):
    """Render Tab 1: Tổng quan kinh doanh."""
    st.markdown("### 📊 Tổng Quan Hiệu Suất Kinh Doanh")
    render_kpi_cards(kpi_curr, kpi_prev)
    st.divider()

    col_chart, col_highlights = st.columns([2, 1])
    with col_chart:
        render_monthly_revenue_chart(df_monthly)
    with col_highlights:
        render_highlights_container(kpi_curr, df_monthly, df_top_cat)


def render_delivery_tab(df_delay, df_reviews, df_states):
    """Render Tab 2: Vận hành Giao hàng & Trải nghiệm khách hàng."""
    st.markdown("### 🚚 Vận Hành Giao Hàng & Trải Nghiệm Khách Hàng")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("⏱️ Tác động của Độ trễ Giao hàng đến Điểm đánh giá TB")
        if df_delay.empty:
            st.info("ℹ️ Không có dữ liệu mức trễ giao hàng.")
        else:
            # Gán màu: Giao sớm/Đúng hạn màu xanh, Trễ màu đỏ cam
            colors = [
                PRIMARY_COLOR if "Sớm" in s or "Đúng hạn" in s else ALERT_COLOR
                for s in df_delay["delay_status"]
            ]
            fig_delay = px.bar(
                df_delay,
                x="delay_status",
                y="avg_review_score",
                text="avg_review_score",
                labels={"delay_status": "Mức độ giao hàng", "avg_review_score": "Điểm đánh giá TB (Sao)"},
                title="Khách hàng chấm điểm dưới 3.0 khi đơn hàng bị giao trễ quá 3 ngày",
            )
            fig_delay.update_traces(marker_color=colors, texttemplate="%{text:.2f}", textposition="outside")
            fig_delay.update_layout(template=BACKGROUND_TEMPLATE, yaxis_range=[1, 5.2], height=400)
            show_chart(fig_delay)

    with c2:
        st.subheader("⭐ Phân bố Điểm số Đánh giá (1 đến 5 sao)")
        if df_reviews.empty or df_reviews["orders"].sum() == 0:
            st.info("ℹ️ Không có dữ liệu đánh giá.")
        else:
            fig_dist = px.bar(
                df_reviews,
                x="review_score",
                y="orders",
                labels={"review_score": "Số sao đánh giá", "orders": "Số lượng đơn hàng"},
                title="Đánh giá 5 sao chiếm đa số, khẳng định chất lượng sàn thương mại",
                color="review_score",
                color_continuous_scale=["#EF5350", "#FFB74D", "#FFF176", "#81C784", "#2E7D32"],
            )
            fig_dist.update_layout(template=BACKGROUND_TEMPLATE, height=400, coloraxis_showscale=False)
            show_chart(fig_dist)

    st.divider()

    st.subheader("🗺️ Tỷ lệ Giao Hàng Trễ Hạn theo Từng Bang (%)")
    if df_states.empty:
        st.info("ℹ️ Không có dữ liệu bang/khu vực.")
    else:
        # Lấy top 15 bang có đơn hàng lớn nhất để so sánh tỷ lệ trễ
        df_top_states = df_states.sort_values("orders", ascending=False).head(15).copy()
        df_top_states = df_top_states.sort_values("delayed_rate", ascending=True)

        fig_state_delay = px.bar(
            df_top_states,
            x="delayed_rate",
            y="customer_state",
            orientation="h",
            text="delayed_rate",
            labels={"delayed_rate": "Tỷ lệ trễ hạn (%)", "customer_state": "Bang"},
            title="Tỷ lệ trễ hạn tập trung cao ở các bang xa trung tâm phân phối chính",
            color="delayed_rate",
            color_continuous_scale="Reds",
        )
        fig_state_delay.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_state_delay.update_layout(template=BACKGROUND_TEMPLATE, height=450)
        show_chart(fig_state_delay)

    st.info(
        "📌 **Kết luận vận hành:** Thời gian vận chuyển là yếu tố then chốt quyết định sự hài lòng của khách hàng. "
        "Các đơn hàng giao trễ trên 3 ngày ghi nhận điểm đánh giá sụt giảm sâu xuống dưới mức trung bình (dưới 2.5 sao). "
        "Cần ưu tiên tối ưu hóa tuyến vận chuyển và đặt kho trung chuyển tại các bang có tỷ lệ giao trễ cao như Alagoas (AL) hay Maranhão (MA)."
    )


def render_products_tab(top_n_choice, filters_args):
    """Render Tab 3: Phân tích Sản phẩm & Danh mục bán chạy."""
    st.markdown("### 🛍️ Phân Tích Danh Mục Sản Phẩm")

    col_ctrl, _ = st.columns([1, 2])
    with col_ctrl:
        metric_mode = st.radio(
            "Xếp hạng danh mục theo:",
            options=["Doanh thu (BRL)", "Số lượng sản phẩm bán (Items)"],
            horizontal=True,
        )

    # Truy vấn top 10
    start_date, end_date, states, categories, statuses = filters_args
    df_cat = cached_top_categories(10, start_date, end_date, states, categories, statuses)

    if df_cat.empty:
        st.info("ℹ️ Không tìm thấy sản phẩm nào khớp với bộ lọc.")
        return

    is_revenue = metric_mode.startswith("Doanh thu")
    sort_col = "total_sales" if is_revenue else "items_sold"
    col_label = "Doanh thu (BRL)" if is_revenue else "Số lượng bán (Items)"

    df_cat = df_cat.sort_values(sort_col, ascending=True)

    fig_cat = px.bar(
        df_cat,
        x=sort_col,
        y="category",
        orientation="h",
        labels={sort_col: col_label, "category": "Danh mục sản phẩm"},
        title=f"Top 10 Danh mục dẫn đầu theo {col_label}",
        color=sort_col,
        color_continuous_scale="Teal",
        text=sort_col,
    )
    if is_revenue:
        fig_cat.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
    else:
        fig_cat.update_traces(texttemplate="%{text:,}", textposition="outside")

    fig_cat.update_layout(template=BACKGROUND_TEMPLATE, height=500)
    show_chart(fig_cat)


def render_customers_tab(df_states, repeat_rate, df_payment, df_heatmap):
    """Render Tab 4: Phân tích Khách hàng, Phương thức thanh toán & Địa lý."""
    st.markdown("### 👥 Phân Tích Khách Hàng & Khu Vực Địa Lý")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("🗺️ Doanh thu theo Bang (Top 10 Thị Trường)")
        if df_states.empty:
            st.info("ℹ️ Không có dữ liệu bang.")
        else:
            top_states_rev = df_states.head(10).sort_values("revenue", ascending=True)
            fig_state_rev = px.bar(
                top_states_rev,
                x="revenue",
                y="customer_state",
                orientation="h",
                text="revenue",
                labels={"revenue": "Doanh thu (BRL)", "customer_state": "Bang"},
                title="Bang São Paulo (SP) chiếm thị phần doanh thu vượt trội",
                color="revenue",
                color_continuous_scale="Blues",
            )
            fig_state_rev.update_traces(texttemplate="R$ %{text:,.0f}", textposition="outside")
            fig_state_rev.update_layout(template=BACKGROUND_TEMPLATE, height=400)
            show_chart(fig_state_rev)

    with col2:
        st.subheader("💳 Cơ cấu Phương thức Thanh toán (Payment Mix)")
        if df_payment.empty:
            st.info("ℹ️ Không có dữ liệu thanh toán.")
        else:
            fig_donut = px.pie(
                df_payment,
                names="payment_type",
                values="revenue",
                hole=0.45,
                title="Credit card chiếm hơn 75% tổng giá trị giao dịch toàn sàn",
                color_discrete_sequence=[PRIMARY_COLOR, "#00897B", "#FB8C00", "#D81B60"],
            )
            fig_donut.update_traces(textinfo="percent+label", hoverinfo="label+value+percent")
            fig_donut.update_layout(template=BACKGROUND_TEMPLATE, height=400)
            show_chart(fig_donut)

    st.divider()

    col_repeat, col_heat = st.columns([1, 3])

    with col_repeat:
        st.subheader("🔁 Khách hàng quay lại")
        st.metric(
            label="Tỷ lệ khách mua lại (Repeat Rate)",
            value=f"{repeat_rate:.2f}%",
            help="Tỷ lệ khách hàng (customer_unique_id) có từ 2 đơn hàng thành công trở lên trong tập dữ liệu lọc.",
        )
        st.caption(
            "💡 *Đặc thù thị trường TMĐT Brazil có tỷ lệ khách hàng quay lại khoảng 3-5%, "
            "phần lớn khách hàng mua các sản phẩm giá trị lớn theo chu kỳ dài.*"
        )

    with col_heat:
        st.subheader("🔥 Khung Giờ Vàng Đặt Hàng (Thứ trong tuần x Giờ)")
        if df_heatmap.empty:
            st.info("ℹ️ Không có dữ liệu khung giờ đặt hàng.")
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

            # Pivot ma trận 7x24
            matrix = df_heat_display.pivot(index="day_name", columns="hour", values="orders").fillna(0)
            day_order = ["Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy", "Chủ nhật"]
            matrix = matrix.reindex([d for d in day_order if d in matrix.index])

            fig_heat = px.imshow(
                matrix,
                labels=dict(x="Khung giờ trong ngày (0 - 23h)", y="Thứ trong tuần", color="Số đơn"),
                x=matrix.columns,
                y=matrix.index,
                color_continuous_scale="Viridis",
                title="Khách hàng tập trung chốt đơn nhiều nhất từ 10h đến 16h và 20h đến 21h",
            )
            fig_heat.update_layout(template=BACKGROUND_TEMPLATE, height=350)
            show_chart(fig_heat)


# ==============================================================================
# HÀM MAIN ĐIỀU PHỐI CHÍNH
# ==============================================================================

def main():
    # 1. Tiêu đề ứng dụng
    st.title("🛍️ E-Commerce Executive Analytics Dashboard")
    st.markdown(
        "Nền tảng giám sát sức khỏe kinh doanh, vận hành giao vận và phân tích chân dung khách hàng sàn Olist."
    )
    st.divider()

    # 2. Render Sidebar bộ lọc và lấy điều kiện
    filters = render_sidebar_filters()

    # Chuyển đổi tham số thành các biến hashable để truyền vào hàm cache
    start_date = filters["start_date"]
    end_date = filters["end_date"]
    states = filters["states"]
    categories = filters["categories"]
    statuses = filters["statuses"]
    filters_args = (start_date, end_date, states, categories, statuses)

    # 3. Nạp dữ liệu đồng thời với Cache
    with st.spinner("⏳ Đang tính toán và kết xuất số liệu..."):
        kpi_curr = cached_kpi_extended(*filters_args)
        kpi_prev = cached_kpi_previous_period(*filters_args)

        # 4. Kiểm tra trường hợp lọc ra 0 dòng dữ liệu
        if kpi_curr["total_orders"] == 0:
            st.info(
                "ℹ️ **Không tìm thấy đơn hàng nào khớp với bộ lọc hiện tại!** "
                "Vui lòng mở rộng khoảng ngày hoặc chọn lại Bang / Danh mục trên thanh Sidebar."
            )
            return

        df_monthly = cached_monthly_revenue(*filters_args)
        df_delay = cached_delay_vs_review(*filters_args)
        df_reviews = cached_review_distribution(*filters_args)
        df_states = cached_revenue_by_state(*filters_args)
        df_payment = cached_payment_mix(*filters_args)
        repeat_rate = cached_repeat_customer_rate(*filters_args)
        df_heatmap = cached_orders_heatmap(*filters_args)
        df_top_cat = cached_top_categories(10, *filters_args)

    # 5. Phân chia 4 Tabs chức năng chuyên sâu
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Tổng quan",
        "🚚 Giao hàng & Trải nghiệm",
        "🛍️ Sản phẩm",
        "👥 Khách hàng & Khu vực",
    ])

    with tab1:
        render_overview_tab(kpi_curr, kpi_prev, df_monthly, df_top_cat)

    with tab2:
        render_delivery_tab(df_delay, df_reviews, df_states)

    with tab3:
        render_products_tab(10, filters_args)

    with tab4:
        render_customers_tab(df_states, repeat_rate, df_payment, df_heatmap)


if __name__ == "__main__":
    main()