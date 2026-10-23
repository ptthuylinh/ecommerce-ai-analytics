"""
E-Commerce Executive Performance Dashboard.
Được cấu trúc theo phong cách Dark Analytics + Bento Grid gồm 4 Tabs:
1. Tổng quan (6 Thẻ KPI HTML, Hero Highlights Bento, Doanh thu MoM & Cơ cấu danh mục)
2. Giao hàng & Trải nghiệm (Phân tích mức trễ, Phân bố Review, Tỷ lệ trễ theo bang & Nhận định vận hành)
3. Sản phẩm (Top 10 danh mục theo doanh thu / số lượng, Độ tập trung ngành hàng)
4. Khách hàng & Khu vực (Phân bố bang, Cơ cấu thanh toán Donut, Heatmap giờ vàng đặt hàng, Repeat Rate)

Sử dụng src/analytics.py với bảng Fact in-memory siêu tốc, tải trang dưới 2 giây.
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
from src.ui.theme import (  # noqa: E402
    TOKENS,
    SEQUENCE,
    inject_css,
    register_plotly_template,
    hero_banner,
    kpi_card,
    insight_card,
    section_header,
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
    page_title="E-Commerce Executive Analytics Dashboard",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Áp dụng Theme chuẩn Dark Analytics
inject_css()
register_plotly_template()


# 3. Hàm hiển thị biểu đồ Plotly tương thích
def show_chart(fig):
    """Hiển thị biểu đồ Plotly co giãn theo khung chứa với width='stretch'."""
    st.plotly_chart(fig, width="stretch")


# ==============================================================================
# HÀM RENDER TỪNG PHẦN GIAO DIỆN VÀ BIỂU ĐỒ THEO CHUẨN BENTO GRID
# ==============================================================================

def render_kpi_cards(kpi_curr, kpi_prev, df_monthly=None):
    """Hiển thị 6 thẻ KPI HTML cao cấp kèm delta pill và sparkline xu hướng."""
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    # Sparkline data nếu có
    rev_spark = df_monthly["revenue"].tail(6).tolist() if df_monthly is not None and not df_monthly.empty else None
    ord_spark = df_monthly["orders"].tail(6).tolist() if df_monthly is not None and not df_monthly.empty else None

    # 1. Doanh thu
    rev_curr = kpi_curr["total_revenue"]
    rev_prev = kpi_prev["total_revenue"]
    rev_delta = rev_curr - rev_prev if rev_prev > 0 else None
    with c1:
        kpi_card(
            label="Tổng doanh thu",
            value=f"R$ {rev_curr:,.0f}",
            delta=f"R$ {rev_delta:+,.0f}" if rev_delta is not None else None,
            good_when_up=True,
            spark_values=rev_spark,
        )

    # 2. Đơn thành công
    ord_curr = int(kpi_curr["total_orders"])
    ord_prev = int(kpi_prev["total_orders"])
    ord_delta = ord_curr - ord_prev if ord_prev > 0 else None
    with c2:
        kpi_card(
            label="Đơn thành công",
            value=f"{ord_curr:,}",
            delta=f"{ord_delta:+,}" if ord_delta is not None else None,
            good_when_up=True,
            spark_values=ord_spark,
        )

    # 3. Giá trị trung bình đơn hàng (AOV)
    aov_curr = kpi_curr["avg_order_value"]
    aov_prev = kpi_prev["avg_order_value"]
    aov_delta = aov_curr - aov_prev if aov_prev > 0 else None
    with c3:
        kpi_card(
            label="AOV (Giá trị ĐH)",
            value=f"R$ {aov_curr:,.1f}",
            delta=f"R$ {aov_delta:+,.1f}" if aov_delta is not None else None,
            good_when_up=True,
        )

    # 4. Điểm đánh giá trung bình
    rev_score_curr = kpi_curr["avg_review_score"]
    rev_score_prev = kpi_prev["avg_review_score"]
    rev_score_delta = rev_score_curr - rev_score_prev if rev_score_prev > 0 else None
    with c4:
        kpi_card(
            label="Điểm đánh giá TB",
            value=f"{rev_score_curr:.2f} / 5.0",
            delta=f"{rev_score_delta:+.2f}" if rev_score_delta is not None else None,
            good_when_up=True,
        )

    # 5. Tỷ lệ giao đúng hạn
    ontime_curr = kpi_curr["on_time_rate"]
    ontime_prev = kpi_prev["on_time_rate"]
    ontime_delta = ontime_curr - ontime_prev if ontime_prev > 0 else None
    with c5:
        kpi_card(
            label="Giao đúng hạn",
            value=f"{ontime_curr:.1f}%",
            delta=f"{ontime_delta:+.1f}%" if ontime_delta is not None else None,
            good_when_up=True,
        )

    # 6. Khách hàng duy nhất
    cust_curr = int(kpi_curr["total_customers"])
    cust_prev = int(kpi_prev["total_customers"])
    cust_delta = cust_curr - cust_prev if cust_prev > 0 else None
    with c6:
        kpi_card(
            label="Khách hàng thực",
            value=f"{cust_curr:,}",
            delta=f"{cust_delta:+,}" if cust_delta is not None else None,
            good_when_up=True,
        )


def render_highlights_container(kpi_curr, df_monthly, df_top_cat):
    """Hiển thị dải 3 insight_card tự sinh từ số liệu thực tế."""
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
        top_cat_name = df_top_cat.iloc[0]["category"]
        top_cat_sales = df_top_cat.iloc[0]["total_sales"]
    else:
        top_cat_name, top_cat_sales = "N/A", 0.0

    # 3. Hiệu quả giao vận
    on_time = kpi_curr["on_time_rate"]
    delay_rate = round(100.0 - on_time, 1)
    avg_delivery = kpi_curr["avg_delivery_days"]

    i1, i2, i3 = st.columns(3)
    with i1:
        growth_tone = "good" if latest_growth >= 0 else "warn"
        insight_card(
            icon="🏆",
            headline=f"Kỷ lục doanh thu tháng {peak_month}",
            detail=f"Tháng {peak_month} đạt đỉnh doanh thu R$ {peak_rev:,.0f} với {peak_orders:,} đơn hàng. Tốc độ tăng trưởng MoM gần nhất đạt {latest_growth:+.2f}%.",
            tone=growth_tone,
        )
    with i2:
        delivery_tone = "good" if delay_rate <= 10.0 else "warn"
        insight_card(
            icon="🚚",
            headline=f"Giao đúng hạn đạt {on_time:.1f}%",
            detail=f"Thời gian giao TB toàn sàn là {avg_delivery:.1f} ngày. Tỷ lệ đơn giao trễ hẹn ở mức {delay_rate:.1f}%, cần kiểm soát độ trễ để bảo toàn đánh giá sao.",
            tone=delivery_tone,
        )
    with i3:
        cust_int = int(kpi_curr["total_customers"])
        insight_card(
            icon="🛍️",
            headline=f"Danh mục chủ lực: {top_cat_name}",
            detail=f"Nhóm hàng '{top_cat_name}' dẫn đầu quy mô doanh số với hơn R$ {top_cat_sales:,.0f}, phục vụ cơ sở {cust_int:,} khách hàng thực tế.",
            tone="info",
        )


def render_monthly_revenue_chart(df_monthly):
    """Biểu đồ kết hợp (Combo Chart): Cột doanh thu và Đường tăng trưởng MoM theo template olist."""
    if df_monthly.empty:
        st.info("Không có dữ liệu doanh thu cho khoảng thời gian đã chọn.")
        return

    fig = go.Figure()

    # Cột doanh thu: màu primary
    fig.add_trace(
        go.Bar(
            x=df_monthly["month"],
            y=df_monthly["revenue"],
            name="Doanh thu (BRL)",
            marker_color=TOKENS["primary"],
            hovertemplate="Tháng %{x}<br>Doanh thu: R$ %{y:,.2f}<extra></extra>",
            yaxis="y1",
        )
    )

    # Đường MoM %: màu secondary
    fig.add_trace(
        go.Scatter(
            x=df_monthly["month"],
            y=df_monthly["mom_growth_pct"],
            name="Tăng trưởng MoM (%)",
            mode="lines+markers",
            marker=dict(size=6, color=TOKENS["secondary"]),
            line=dict(color=TOKENS["secondary"], width=2.5),
            hovertemplate="Tháng %{x}<br>Tăng trưởng MoM: %{y:+.2f}%<extra></extra>",
            yaxis="y2",
        )
    )

    fig.update_layout(
        template="olist",
        title=dict(text="Xu hướng doanh thu hàng tháng và tốc độ tăng trưởng MoM"),
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
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=30, r=30, t=50, b=30),
        height=420,
    )
    show_chart(fig)


def render_overview_tab(kpi_curr, kpi_prev, df_monthly, df_top_cat):
    """Render Tab 1: Tổng quan kinh doanh với Bento Grid 3:2."""
    section_header("Tổng quan hiệu suất kinh doanh", "Các chỉ số cốt lõi và so sánh biến động chu kỳ trước")
    render_kpi_cards(kpi_curr, kpi_prev, df_monthly)

    st.write("")
    render_highlights_container(kpi_curr, df_monthly, df_top_cat)
    st.write("")

    # Bento Grid tỉ lệ 3:2
    col_chart, col_side = st.columns([3, 2])

    with col_chart:
        with st.container(border=True):
            render_monthly_revenue_chart(df_monthly)

    with col_side:
        with st.container(border=True):
            section_header("Cơ cấu doanh thu danh mục", "Top 5 nhóm ngành hàng đóng góp doanh số lớn nhất")
            if df_top_cat.empty:
                st.info("Không có dữ liệu danh mục sản phẩm.")
            else:
                top5_cat = df_top_cat.head(5).sort_values("total_sales", ascending=True)
                fig_top5 = px.bar(
                    top5_cat,
                    x="total_sales",
                    y="category",
                    orientation="h",
                    text="total_sales",
                    labels={"total_sales": "Doanh số (BRL)", "category": "Danh mục"},
                )
                fig_top5.update_traces(
                    marker_color=TOKENS["primary"],
                    texttemplate="R$ %{text:,.0f}",
                    textposition="outside",
                )
                fig_top5.update_layout(
                    template="olist",
                    xaxis=dict(showgrid=False, showticklabels=False),
                    yaxis=dict(showgrid=False),
                    height=345,
                    margin=dict(l=10, r=40, t=20, b=10),
                )
                show_chart(fig_top5)


def render_delivery_tab(df_delay, df_reviews, df_states):
    """Render Tab 2: Vận hành giao hàng & trải nghiệm theo chuẩn Bento Grid."""
    section_header("Vận hành giao hàng và trải nghiệm khách hàng", "Phân tích tác động của thời gian giao vận đến mức độ hài lòng")

    # Bento Grid tỉ lệ 3:2
    c1, c2 = st.columns([3, 2])

    # Tính toán động điểm đánh giá của đơn đúng hạn vs trễ hạn
    on_time_score = None
    severe_score = None
    if not df_delay.empty:
        early_on_time = df_delay[df_delay["delay_status"].str.contains("Sớm|Đúng hạn", na=False)]
        if not early_on_time.empty and early_on_time["orders"].sum() > 0:
            on_time_score = (early_on_time["avg_review_score"] * early_on_time["orders"]).sum() / early_on_time["orders"].sum()

        severe_delay = df_delay[df_delay["delay_status"].str.contains("Trễ 4-7 ngày|Trễ >7 ngày", na=False)]
        if not severe_delay.empty and severe_delay["orders"].sum() > 0:
            severe_score = (severe_delay["avg_review_score"] * severe_delay["orders"]).sum() / severe_delay["orders"].sum()

    with c1:
        with st.container(border=True):
            if df_delay.empty:
                st.info("Không có dữ liệu mức trễ giao hàng.")
            else:
                colors = [
                    TOKENS["primary"] if ("Sớm" in str(s) or "Đúng hạn" in str(s)) else TOKENS["alert"]
                    for s in df_delay["delay_status"]
                ]
                fig_delay = px.bar(
                    df_delay,
                    x="delay_status",
                    y="avg_review_score",
                    text="avg_review_score",
                    labels={"delay_status": "Mức độ giao hàng", "avg_review_score": "Điểm đánh giá TB"},
                    title="Điểm đánh giá trung bình theo từng mức độ trễ hạn",
                )
                fig_delay.update_traces(marker_color=colors, texttemplate="%{text:.2f}", textposition="outside")
                fig_delay.update_layout(
                    template="olist",
                    yaxis_range=[1, 5.2],
                    height=380,
                    margin=dict(l=10, r=10, t=44, b=10),
                )
                show_chart(fig_delay)

    with c2:
        with st.container(border=True):
            if df_reviews.empty or df_reviews["orders"].sum() == 0:
                st.info("Không có dữ liệu đánh giá.")
            else:
                total_revs = df_reviews["orders"].sum()
                r5_orders = df_reviews[df_reviews["review_score"] == 5]["orders"].sum() if not df_reviews.empty else 0
                pct_5_star = (r5_orders / total_revs * 100) if total_revs > 0 else 0

                colors_rev = [
                    TOKENS["alert"] if s <= 2 else (TOKENS["warning"] if s == 3 else TOKENS["positive"])
                    for s in df_reviews["review_score"]
                ]
                fig_dist = px.bar(
                    df_reviews,
                    x="review_score",
                    y="orders",
                    text="orders",
                    labels={"review_score": "Số sao", "orders": "Số lượng đơn"},
                    title=f"Đánh giá 5 sao chiếm ưu thế ({pct_5_star:.1f}% tổng đơn)",
                )
                fig_dist.update_traces(marker_color=colors_rev, texttemplate="%{text:,}", textposition="outside")
                fig_dist.update_layout(
                    template="olist",
                    height=380,
                    margin=dict(l=10, r=10, t=44, b=10),
                )
                show_chart(fig_dist)

    st.write("")

    # Bento Grid phần 2: Tỷ lệ trễ theo bang (3) và Insight card tự sinh (2)
    col_state, col_insight = st.columns([3, 2])

    worst_states_str = None
    if not df_states.empty:
        valid_states = df_states[df_states["orders"] >= 10]
        if valid_states.empty:
            valid_states = df_states
        worst_states = valid_states.sort_values("delayed_rate", ascending=False).head(2)
        if len(worst_states) >= 2:
            s1 = worst_states.iloc[0]
            s2 = worst_states.iloc[1]
            worst_states_str = f"{s1['customer_state']} ({s1['delayed_rate']:.1f}%) và {s2['customer_state']} ({s2['delayed_rate']:.1f}%)"
        elif len(worst_states) == 1:
            s1 = worst_states.iloc[0]
            worst_states_str = f"{s1['customer_state']} ({s1['delayed_rate']:.1f}%)"

    with col_state:
        with st.container(border=True):
            if df_states.empty:
                st.info("Không có dữ liệu bang/khu vực.")
            else:
                df_top_states = df_states.sort_values("orders", ascending=False).head(12).copy()
                df_top_states = df_top_states.sort_values("delayed_rate", ascending=True)
                avg_delay = df_top_states["delayed_rate"].mean()

                bar_colors = [
                    TOKENS["alert"] if r > avg_delay else TOKENS["primary"]
                    for r in df_top_states["delayed_rate"]
                ]
                fig_state_delay = px.bar(
                    df_top_states,
                    x="delayed_rate",
                    y="customer_state",
                    orientation="h",
                    text="delayed_rate",
                    labels={"delayed_rate": "Tỷ lệ trễ (%)", "customer_state": "Bang"},
                    title="Tỷ lệ giao hàng trễ hạn theo bang (Top 12 bang quy mô lớn)",
                )
                fig_state_delay.update_traces(marker_color=bar_colors, texttemplate="%{text:.1f}%", textposition="outside")
                fig_state_delay.update_layout(
                    template="olist",
                    height=390,
                    margin=dict(l=10, r=40, t=44, b=10),
                )
                show_chart(fig_state_delay)

    with col_insight:
        with st.container(border=True):
            section_header("Nhận định vận hành giao vận", "Rút trích trực tiếp từ cơ sở dữ liệu hiện tại")

            # Insight 1: Trải nghiệm & Điểm đánh giá (sinh động từ dữ liệu)
            if severe_score is not None and on_time_score is not None:
                insight_card(
                    icon="⏱️",
                    headline="Tác động quyết định của độ trễ",
                    detail=f"Đơn hàng giao đúng hạn đạt điểm số trung bình {on_time_score:.2f} sao. Khi đơn hàng bị trễ trên 3 ngày, điểm số đánh giá giảm sâu xuống chỉ còn {severe_score:.2f} sao.",
                    tone="warn",
                )
            elif on_time_score is not None:
                insight_card(
                    icon="⏱️",
                    headline="Chất lượng giao hàng ổn định",
                    detail=f"Đơn hàng đúng hạn duy trì mức đánh giá cao {on_time_score:.2f} sao trên toàn hệ thống.",
                    tone="good",
                )

            st.write("")

            # Insight 2: Tuyến vận tải theo bang (sinh động từ dữ liệu)
            if worst_states_str:
                insight_card(
                    icon="🗺️",
                    headline="Trọng điểm cải thiện logistics",
                    detail=f"Tỷ lệ giao trễ tập trung cao nhất tại các bang {worst_states_str}. Cần ưu tiên hợp tác với đơn vị vận chuyển địa phương hoặc đặt trung tâm phân phối vệ tinh.",
                    tone="info",
                )
            else:
                insight_card(
                    icon="🗺️",
                    headline="Vùng giao nhận cân bằng",
                    detail="Không ghi nhận bang nào có tỷ lệ chậm trễ bất thường trong tập dữ liệu đã lọc.",
                    tone="good",
                )


def render_products_tab(top_n_choice, df_items):
    """Render Tab 3: Phân tích danh mục sản phẩm theo chuẩn Bento Grid 3:2."""
    section_header("Phân tích danh mục sản phẩm", "Xếp hạng doanh thu và sản lượng bán theo nhóm ngành hàng")

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
        # Tương thích ngược nếu truyền tuple filters_args
        items_fact = load_items_fact()
        df_cat = top_categories(apply_filters(items_fact, df_items), top_n=top_n_choice)

    if df_cat.empty:
        st.info("Không tìm thấy sản phẩm nào khớp với bộ lọc.")
        return

    is_revenue = metric_mode.startswith("Doanh thu")
    sort_col = "total_sales" if is_revenue else "items_sold"
    col_label = "Doanh thu (BRL)" if is_revenue else "Số lượng bán (Items)"

    df_cat_sorted = df_cat.sort_values(sort_col, ascending=True)

    # Bento Grid 3:2
    col_chart, col_side = st.columns([3, 2])

    with col_chart:
        with st.container(border=True):
            fig_cat = px.bar(
                df_cat_sorted,
                x=sort_col,
                y="category",
                orientation="h",
                labels={sort_col: col_label, "category": "Danh mục"},
                title=f"Top 10 danh mục dẫn đầu theo {col_label}",
                text=sort_col,
            )
            # Dữ liệu thường = primary, danh mục top 1 = secondary
            colors_cat = [TOKENS["primary"]] * len(df_cat_sorted)
            if len(colors_cat) > 0:
                colors_cat[-1] = TOKENS["secondary"]

            fig_cat.update_traces(
                marker_color=colors_cat,
                texttemplate="R$ %{text:,.0f}" if is_revenue else "%{text:,}",
                textposition="outside",
            )
            fig_cat.update_layout(
                template="olist",
                height=480,
                xaxis=dict(showgrid=False, showticklabels=False),
                margin=dict(l=10, r=50, t=44, b=10),
            )
            show_chart(fig_cat)

    with col_side:
        with st.container(border=True):
            section_header("Nhận định danh mục hàng hóa", "Tập trung doanh số và sản lượng tiêu thụ")

            top_cat = df_cat.iloc[0]
            top_name = top_cat["category"]
            top_sales = top_cat["total_sales"]
            top_items = top_cat["items_sold"]
            total_top10_sales = df_cat["total_sales"].sum()
            top1_share = (top_sales / total_top10_sales * 100) if total_top10_sales > 0 else 0
            top3_share = (df_cat.head(3)["total_sales"].sum() / total_top10_sales * 100) if total_top10_sales > 0 else 0

            insight_card(
                icon="🏆",
                headline=f"Ngành hàng chủ lực: {top_name}",
                detail=f"Chiếm {top1_share:.1f}% tổng doanh thu trong top 10 với giá trị R$ {top_sales:,.0f} ({top_items:,} sản phẩm bán ra). Đây là nhóm sản phẩm xương sống của sàn.",
                tone="good",
            )

            st.write("")

            insight_card(
                icon="📦",
                headline="Độ tập trung thị phần danh mục",
                detail=f"Top 3 ngành hàng lớn nhất chiếm {top3_share:.1f}% toàn bộ doanh thu nhóm dẫn đầu. Cần duy trì chính sách tồn kho và hợp tác với nhà bán hàng uy tín trong nhóm này.",
                tone="info",
            )


def render_customers_tab(df_states, repeat_rate, df_payment, df_heatmap):
    """Render Tab 4: Khách hàng, phương thức thanh toán và địa lý theo chuẩn Bento Grid."""
    section_header("Khách hàng và khu vực địa lý", "Phân tích địa bàn trọng điểm, kênh thanh toán và khung giờ chốt đơn")

    # Bento Grid Hàng 1 (3:2): Doanh thu theo bang & Cơ cấu thanh toán Donut
    col1, col2 = st.columns([3, 2])

    total_state_rev = df_states["revenue"].sum() if not df_states.empty else 0
    if not df_states.empty and total_state_rev > 0:
        top_state_row = df_states.iloc[0]
        top_state_code = top_state_row["customer_state"]
        top_state_rev = top_state_row["revenue"]
        top_state_pct = (top_state_rev / total_state_rev) * 100
        state_title = f"Bang {top_state_code} dẫn đầu thị phần ({top_state_pct:.1f}% doanh thu)"
    else:
        top_state_code, top_state_rev, top_state_pct = "N/A", 0, 0
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
            if df_states.empty:
                st.info("Không có dữ liệu bang.")
            else:
                top_states_rev = df_states.head(10).sort_values("revenue", ascending=True)
                colors_state = [TOKENS["primary"]] * len(top_states_rev)
                if len(colors_state) > 0:
                    colors_state[-1] = TOKENS["secondary"]

                fig_state_rev = px.bar(
                    top_states_rev,
                    x="revenue",
                    y="customer_state",
                    orientation="h",
                    text="revenue",
                    labels={"revenue": "Doanh thu (BRL)", "customer_state": "Bang"},
                    title=state_title,
                )
                fig_state_rev.update_traces(marker_color=colors_state, texttemplate="R$ %{text:,.0f}", textposition="outside")
                fig_state_rev.update_layout(
                    template="olist",
                    height=380,
                    xaxis=dict(showgrid=False, showticklabels=False),
                    margin=dict(l=10, r=50, t=44, b=10),
                )
                show_chart(fig_state_rev)

    with col2:
        with st.container(border=True):
            if df_payment.empty:
                st.info("Không có dữ liệu thanh toán.")
            else:
                fig_donut = px.pie(
                    df_payment,
                    names="payment_type",
                    values="revenue",
                    hole=0.55,
                    title=pay_title,
                    color_discrete_sequence=SEQUENCE,
                )
                fig_donut.update_traces(
                    textinfo="percent+label",
                    hoverinfo="label+value+percent",
                    textposition="inside",
                )
                fig_donut.update_layout(
                    template="olist",
                    showlegend=False,
                    height=380,
                    margin=dict(l=10, r=10, t=44, b=10),
                )
                show_chart(fig_donut)

    st.write("")

    # Bento Grid Hàng 2 (3:2): Heatmap giờ vàng đơn hàng (3) và Repeat Rate & Payment Insight (2)
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

                # Tính toán động khung giờ đỉnh
                orders_by_hour = df_heatmap.groupby("hour")["orders"].sum()
                peak_h = int(orders_by_hour.idxmax())
                series_24 = orders_by_hour.reindex(range(24), fill_value=0)
                rolling_4 = [series_24.iloc[i:i+4].sum() for i in range(21)]
                best_start = int(pd.Series(rolling_4).idxmax()) if rolling_4 else 10
                best_end = best_start + 4
                window_pct = (rolling_4[best_start] / series_24.sum() * 100) if series_24.sum() > 0 else 0

                heat_title = f"Khung giờ cao điểm: {best_start}h - {best_end}h (chiếm {window_pct:.1f}% lượng đơn)"

                # Thang đơn sắc Indigo chuẩn Dark Analytics
                indigo_scale = [
                    [0.0, "#0F172A"],
                    [0.25, "#1E1B4B"],
                    [0.55, "#4338CA"],
                    [0.8, "#6366F1"],
                    [1.0, "#A5B4FC"],
                ]

                fig_heat = px.imshow(
                    matrix,
                    labels=dict(x="Khung giờ trong ngày (0 - 23h)", y="Thứ trong tuần", color="Số đơn"),
                    x=matrix.columns,
                    y=matrix.index,
                    color_continuous_scale=indigo_scale,
                    title=heat_title,
                )
                fig_heat.update_layout(
                    template="olist",
                    height=360,
                    margin=dict(l=10, r=10, t=44, b=10),
                )
                show_chart(fig_heat)

    with col_side:
        with st.container(border=True):
            section_header("Chân dung khách hàng & thanh toán", "Hành vi chi tiêu và tần suất quay lại")

            kpi_card(
                label="Tỷ lệ khách mua lại (Repeat Rate)",
                value=f"{repeat_rate:.2f}%",
                delta=None,
            )

            st.write("")

            insight_card(
                icon="💳",
                headline=f"Thói quen thanh toán bằng {top_pay_name}",
                detail=f"Phương thức {top_pay_name} chiếm ưu thế áp đảo ({top_pay_pct:.1f}%), khẳng định thị hiếu sử dụng thẻ và các chương trình trả góp tại thị trường Brazil.",
                tone="info",
            )


# ==============================================================================
# HÀM MAIN ĐIỀU PHỐI CHÍNH
# ==============================================================================

def main():
    # 1. Render Sidebar bộ lọc và lấy điều kiện
    filters = render_sidebar_filters()

    # 2. Hero Banner đầu trang theo chuẩn Bento Grid
    start_date = filters["start_date"]
    end_date = filters["end_date"]
    date_range_str = f"{start_date} → {end_date}"
    hero_banner(
        title="E-Commerce Executive Analytics Dashboard",
        subtitle="Nền tảng giám sát sức khỏe kinh doanh, hiệu quả vận hành giao vận và chân dung khách hàng Olist Brazil theo chuẩn Bento Grid.",
        date_range=date_range_str,
    )

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
            "Không tìm thấy đơn hàng nào khớp với bộ lọc hiện tại. "
            "Vui lòng mở rộng khoảng ngày hoặc chọn lại Bang / Danh mục trên thanh Sidebar."
        )
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

    # 7. Phân chia 4 Tabs chức năng
    tab1, tab2, tab3, tab4 = st.tabs([
        "Tổng quan",
        "Giao hàng & Trải nghiệm",
        "Sản phẩm",
        "Khách hàng & Khu vực",
    ])

    with tab1:
        render_overview_tab(kpi_curr, kpi_prev, df_monthly, df_top_cat)

    with tab2:
        render_delivery_tab(df_delay, df_reviews, df_states)

    with tab3:
        render_products_tab(10, df_items)

    with tab4:
        render_customers_tab(df_states, repeat_rate, df_payment, df_heatmap)


if __name__ == "__main__":
    main()