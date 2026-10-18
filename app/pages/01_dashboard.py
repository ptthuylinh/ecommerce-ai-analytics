import streamlit as st
import plotly.express as px
import sys
import os

# Thêm thư mục gốc vào path để import được từ thư mục src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.db import get_kpi_metrics, get_monthly_revenue, get_top_categories

# 1. Cấu hình trang chuẩn thẩm mỹ
st.set_page_config(
    page_title="E-Commerce Executive Dashboard",
    page_icon="📊",
    layout="wide"
)

# 2. Tiêu đề chính
st.title("📊 E-Commerce Performance Dashboard")
st.markdown("Báo cáo phân tích tổng quan sức khỏe kinh doanh sàn Thương mại điện tử Olist.")
st.divider()

# 3. Hiển thị 4 thẻ KPI Cards
kpi = get_kpi_metrics()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 Tổng doanh thu",
        value=f"R$ {kpi['total_revenue']:,.0f}"
    )

with col2:
    st.metric(
        label="📦 Tổng đơn thành công",
        value=f"{int(kpi['total_orders']):,}"
    )

with col3:
    st.metric(
        label="⭐ Đánh giá trung bình",
        value=f"{kpi['avg_review_score']} / 5.0"
    )

with col4:
    st.metric(
        label="👥 Khách hàng mua sắm",
        value=f"{int(kpi['total_customers']):,}"
    )

st.divider()

# 4. Hai biểu đồ trực quan tương tác (Plotly)
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("📈 Xu hướng Doanh thu theo Tháng")
    df_revenue = get_monthly_revenue()
    fig_rev = px.line(
        df_revenue, 
        x="month", 
        y="revenue",
        markers=True,
        labels={"month": "Tháng", "revenue": "Doanh thu (BRL)"},
        color_discrete_sequence=["#1E88E5"]
    )
    fig_rev.update_layout(xaxis_tickangle=-45, template="plotly_white")
    st.plotly_chart(fig_rev, use_container_width=True)

with chart_col2:
    st.subheader("🏆 Top 10 Danh mục Doanh thu cao nhất")
    df_cat = get_top_categories(10)
    fig_cat = px.bar(
        df_cat, 
        x="total_sales", 
        y="category",
        orientation="h",
        labels={"total_sales": "Doanh thu (BRL)", "category": "Danh mục"},
        color="total_sales",
        color_continuous_scale="Teal"
    )
    fig_cat.update_layout(yaxis=dict(autorange="reversed"), template="plotly_white")
    st.plotly_chart(fig_cat, use_container_width=True)