"""
Module giao diện Sidebar chứa các bộ lọc đa chiều cho Dashboard.
"""

import datetime
import streamlit as st
from src.db import get_filter_options
from src.ui.labels import (
    state_label,
    category_label,
    STATE_ORDER,
    CATEGORY_ORDER,
    PORTUGUESE_TO_ENGLISH,
)


def render_sidebar_filters():
    """
    Hiển thị các bộ lọc tương tác trên Sidebar:
    - Khoảng thời gian (mặc định 2017-01-01 đến 2018-08-31)
    - Bang / Khu vực (sắp theo số đơn giảm dần, nhãn Tên đầy đủ (Mã))
    - Danh mục sản phẩm (sắp theo doanh thu giảm dần, nhãn Tiếng Việt)
    - Trạng thái đơn hàng
    Trả về dict filters chuẩn hóa (dùng tuple cho các danh sách để tương thích cache).
    """
    st.sidebar.header("🔍 Bộ Lọc Phân Tích")

    # Lấy danh sách options từ CSDL
    try:
        options = get_filter_options()
    except Exception:
        options = {
            "min_date": "2016-09-04",
            "max_date": "2018-10-17",
            "categories": [],
            "states": [],
            "statuses": ["delivered"],
        }

    # 1. Bộ lọc khoảng thời gian
    st.sidebar.subheader("📅 Khoảng thời gian")
    default_start = datetime.date(2017, 1, 1)
    default_end = datetime.date(2018, 8, 31)

    min_limit = datetime.date(2016, 1, 1)
    max_limit = datetime.date(2018, 12, 31)

    date_range = st.sidebar.date_input(
        "Chọn ngày bắt đầu và kết thúc:",
        value=(default_start, default_end),
        min_value=min_limit,
        max_value=max_limit,
    )

    st.sidebar.caption(
        "💡 *Mặc định từ 2017-01-01 đến 2018-08-31 vì dữ liệu các mốc ngoài khoảng này chưa đầy đủ.*"
    )

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
        start_date = end_date = date_range[0]
    else:
        start_date = default_start
        end_date = default_end

    st.sidebar.divider()

    # 2. Bộ lọc Bang / Khu vực (sắp theo số đơn giảm dần, hiển thị qua state_label)
    st.sidebar.subheader("🗺️ Khu vực")
    all_states = list(options.get("states", []))
    state_rank = {s: i for i, s in enumerate(STATE_ORDER)}
    sorted_states = sorted(all_states, key=lambda s: state_rank.get(s, 999))

    selected_states = st.sidebar.multiselect(
        "Chọn Bang (State):",
        options=sorted_states,
        default=[],
        format_func=state_label,
        placeholder="Tất cả các bang",
        help="Lọc đơn hàng theo một hoặc nhiều bang của khách hàng (sắp theo số lượng đơn giảm dần).",
    )

    # 3. Bộ lọc Danh mục sản phẩm (sắp theo doanh thu giảm dần, hiển thị qua category_label)
    st.sidebar.subheader("📦 Sản phẩm")
    raw_categories = options.get("categories", [])
    # Chuẩn hóa về mã tiếng Anh nếu DB trả về mã tiếng Bồ Đào Nha
    all_categories = [PORTUGUESE_TO_ENGLISH.get(c, c) for c in raw_categories]
    all_categories = list(dict.fromkeys(all_categories))

    cat_rank = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    sorted_categories = sorted(all_categories, key=lambda c: cat_rank.get(c, 999))

    selected_categories = st.sidebar.multiselect(
        "Chọn Danh mục:",
        options=sorted_categories,
        default=[],
        format_func=category_label,
        placeholder="Tất cả danh mục",
        help="Lọc đơn hàng theo một hoặc nhiều danh mục sản phẩm (sắp theo doanh thu giảm dần).",
    )

    # 4. Bộ lọc Trạng thái đơn hàng
    all_statuses = options.get("statuses", ["delivered"])
    default_status = ["delivered"] if "delivered" in all_statuses else all_statuses[:1]
    selected_statuses = st.sidebar.multiselect(
        "Trạng thái đơn hàng:",
        options=all_statuses,
        default=default_status,
        placeholder="Mặc định: delivered",
    )

    # Đóng gói filters thành tuple để hỗ trợ Streamlit hashing
    filters = {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "states": tuple(selected_states) if selected_states else None,
        "categories": tuple(selected_categories) if selected_categories else None,
        "statuses": tuple(selected_statuses) if selected_statuses else ("delivered",),
    }

    return filters
