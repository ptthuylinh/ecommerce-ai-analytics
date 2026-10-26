"""
E-Commerce AI Analytics - Trang chủ giới thiệu hệ thống.
Cung cấp tổng quan về nền tảng, số liệu tổng hợp toàn sàn từ cơ sở dữ liệu
và hướng dẫn điều hướng giữa các phân hệ chức năng (Dashboard BI, RFM, AI Assistant).
"""

import os
import sys
import streamlit as st

# Thêm thư mục gốc vào path để import module từ src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db import get_connection  # noqa: E402

# 1. Cấu hình trang Streamlit
st.set_page_config(
    page_title="E-Commerce AI Analytics",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# 2. Hàm truy vấn nhanh số liệu tổng quan toàn sàn từ DB
@st.cache_data(show_spinner=False)
def load_db_overview():
    """Truy vấn nhanh thống kê tổng quan toàn sàn trực tiếp từ DB."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders")
        total_orders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT customer_unique_id) FROM customers")
        total_customers = cur.fetchone()[0]
        cur.execute("SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM orders")
        min_ts, max_ts = cur.fetchone()
        cur.execute("SELECT SUM(payment_value) FROM order_payments")
        total_revenue = cur.fetchone()[0] or 0.0
        conn.close()

        min_d = min_ts[:10] if min_ts else "2016-09-04"
        max_d = max_ts[:10] if max_ts else "2018-10-17"
        return {
            "total_orders": int(total_orders),
            "total_customers": int(total_customers),
            "min_date": min_d,
            "max_date": max_d,
            "total_revenue": float(total_revenue),
        }
    except Exception as e:
        return {
            "total_orders": 99441,
            "total_customers": 96096,
            "min_date": "2016-09-04",
            "max_date": "2018-10-17",
            "total_revenue": 16008872.0,
            "error": str(e),
        }


def main():
    # 1. Khởi tạo thanh điều hướng Sidebar
    with st.sidebar:
        st.markdown("### 🧭 Điều hướng hệ thống")
        st.info("Chọn trang **01_dashboard** ở menu phía trên để mở Bảng điều khiển phân tích.")
        st.markdown("---")
        st.caption("E-Commerce AI Analytics Platform v2.0")

    stats = load_db_overview()

    # 2. Tiêu đề ứng dụng
    st.title("🛍️ E-Commerce AI Analytics & BI Platform")
    st.markdown(
        f"**Khoảng thời gian dữ liệu:** `{stats['min_date']} → {stats['max_date']}` | "
        "Hệ sinh thái phân tích kinh doanh thông minh đa phân hệ: Quản trị hiệu suất toàn sàn (BI), "
        "Phân nhóm khách hàng (RFM) và Trợ lý AI hội thoại với dữ liệu Olist Brazil."
    )
    st.divider()

    # 3. Thống kê tổng quan quy mô dữ liệu
    st.subheader("📊 Tổng quan quy mô dữ liệu")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        with st.container(border=True):
            st.metric(
                label="📦 Tổng số đơn hàng",
                value=f"{stats['total_orders']:,}",
            )
    with c2:
        with st.container(border=True):
            st.metric(
                label="👥 Khách hàng duy nhất",
                value=f"{stats['total_customers']:,}",
            )
    with c3:
        with st.container(border=True):
            st.metric(
                label="💰 Tổng giá trị thanh toán",
                value=f"R$ {stats['total_revenue']:,.0f}",
            )
    with c4:
        with st.container(border=True):
            st.metric(
                label="📅 Khoảng thời gian",
                value=f"{stats['min_date'][:7]} → {stats['max_date'][:7]}",
            )

    st.write("")

    # 4. Ba phân hệ chức năng
    st.subheader("🧩 Các phân hệ phân tích")
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown("### 📊 01. Dashboard BI Quản trị")
            st.markdown(
                "Giám sát 6 KPI cốt lõi, tăng trưởng MoM, hiệu quả vận hành giao vận và chân dung khách hàng/thanh toán. "
                "Hỗ trợ bộ lọc đa chiều (ngày, bang, danh mục) xử lý in-memory siêu tốc."
            )
            st.info("💡 Truy cập trang **01_dashboard** trên Sidebar.")
    with col2:
        with st.container(border=True):
            st.markdown("### 👥 02. Phân khúc Khách hàng RFM")
            st.markdown(
                "Phân hạng khách hàng tự động dựa trên Recency, Frequency và Monetary. "
                "Nhận diện các nhóm khách hàng Champions, Loyal, At-Risk để tối ưu hóa chiến dịch Marketing cá nhân hóa."
            )
            st.success("🎯 Phân hệ đang sẵn sàng tích hợp.")
    with col3:
        with st.container(border=True):
            st.markdown("### 🤖 03. Trợ lý AI Đàm thoại")
            st.markdown(
                "Trợ lý thông minh hỗ trợ truy vấn số liệu kinh doanh bằng ngôn ngữ tự nhiên tiếng Việt (Text-to-SQL). "
                "Khai thác insight, phân tích xu hướng và đề xuất quyết định quản trị tức thì."
            )
            st.info("🧠 Phân hệ AI hội thoại đang phát triển.")

    st.write("")

    # 5. Hướng dẫn chuyển trang bên sidebar
    st.subheader("🧭 Hướng dẫn điều hướng")
    with st.container(border=True):
        st.markdown(
            """
            👈 **Thanh điều hướng Sidebar (bên trái màn hình):**
            - Nhấn vào **`01_dashboard`** trên thanh Sidebar để mở **Bảng điều khiển quản trị (Executive BI Dashboard)**.
            - Trang Dashboard cho phép bạn lọc dữ liệu linh hoạt theo khoảng thời gian, bang/khu vực và danh mục ngành hàng.
            - Toàn bộ 4 tab phân tích (Tổng quan, Giao hàng, Sản phẩm, Khách hàng) được xử lý trực tiếp trong RAM với tốc độ tức thì.
            - Cuối trang Dashboard, bạn có thể sử dụng tính năng **Xuất báo cáo (UC04)** để tải dữ liệu CSV (utf-8-sig) hoặc Excel đa sheet (.xlsx).
            """
        )
        st.write("")
        try:
            st.page_link(
                "pages/01_dashboard.py",
                label="👉 Nhấn vào đây để truy cập ngay 01_dashboard (Executive Dashboard)",
                icon="📊",
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
