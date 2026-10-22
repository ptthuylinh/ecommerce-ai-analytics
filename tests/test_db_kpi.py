"""
Bộ kiểm thử tính chính xác của các chỉ số KPI với cơ sở dữ liệu mẫu mini_db.
Đối chiếu trực tiếp với các giá trị tính tay được ghi chú trong comment.
"""

import pytest
from src.db import get_kpi_metrics


# ==============================================================================
# BẢNG TÍNH TAY CÁC GIÁ TRỊ KỲ VỌNG TRÊN mini_db:
# - Các đơn 'delivered':
#   * order_1: c1 (u1, SP), revenue = 110.0, review = 5
#   * order_2: c2 (u2, RJ), revenue = 50.0 + 170.0 = 220.0 (2 payment), review = 4
#   * order_3: c3 (u1, SP), revenue = 165.0, reviews = 4, 2 (2 reviews, cùng khách u1 với order_1)
#   * order_4: c4 (u3, MG), revenue = 330.0, review = 3
#   * order_5: c5 (u4, BA), revenue = 90.0, review = 5
#   * order_6: c6 (u5, PR), revenue = 135.0, review = None
# - Các đơn không 'delivered':
#   * order_7: c7 (u6, SC), status 'canceled', revenue = 275.0, review = 1 (LOẠI BỎ)
#   * order_8: c8 (u7, RS), status 'shipped', revenue = 440.0, review = None (LOẠI BỎ)
#
# => TỔNG HỢP KỲ VỌNG (GROUND TRUTH):
# 1. total_orders = 6 (chỉ 6 đơn delivered)
# 2. total_revenue = 110.0 + 220.0 + 165.0 + 330.0 + 90.0 + 135.0 = 1050.0
# 3. total_customers = 5 (u1, u2, u3, u4, u5 - khách u1 mua 2 đơn c1 & c3)
# 4. avg_review_score:
#    Tổng điểm 6 reviews của các đơn delivered: 5 + 4 + 4 + 2 + 3 + 5 = 23 -> 23 / 6 = 3.83
# ==============================================================================

EXPECTED_TOTAL_ORDERS = 6
EXPECTED_TOTAL_REVENUE = 1050.0
EXPECTED_TOTAL_CUSTOMERS = 5
EXPECTED_AVG_REVIEW_SCORE = 3.83


def test_kpi_total_orders(mini_db):
    """Kiểm tra tổng số đơn hàng thành công (chỉ tính status = 'delivered')."""
    kpi = get_kpi_metrics()
    # Kỳ vọng: 6 đơn (order_1 -> order_6)
    assert kpi["total_orders"] == EXPECTED_TOTAL_ORDERS, (
        f"Kỳ vọng {EXPECTED_TOTAL_ORDERS} đơn nhưng nhận được {kpi['total_orders']}"
    )


def test_kpi_total_revenue_no_fanout(mini_db):
    """
    Kiểm tra tổng doanh thu KHÔNG bị nhân đôi/nhân dòng (fan-out).
    - order_2 có 2 dòng thanh toán (50 + 170 = 220).
    - order_3 có 2 review: nếu JOIN sai sẽ làm dòng thanh toán 165 bị nhân đôi thành 330 (+165).
    """
    kpi = get_kpi_metrics()
    # Kỳ vọng: 1050.0 (Nếu bị fan-out ở order_3 sẽ thành 1215.0)
    assert kpi["total_revenue"] == EXPECTED_TOTAL_REVENUE, (
        f"Kỳ vọng doanh thu {EXPECTED_TOTAL_REVENUE} nhưng nhận được {kpi['total_revenue']}. "
        "Có thể truy vấn JOIN order_payments và order_reviews đang bị nhân dòng (fan-out)!"
    )


def test_kpi_total_customers_unique_id(mini_db):
    """
    Kiểm tra số khách hàng phải đếm theo customer_unique_id (người thực),
    không được đếm theo customer_id (mã định danh theo từng đơn).
    - u1 mua 2 đơn (c1 và c3) => Chỉ tính u1 là 1 khách hàng.
    - total_customers phải <= total_orders (cụ thể ở đây: 5 < 6).
    """
    kpi = get_kpi_metrics()
    # Kỳ vọng: 5 khách hàng thực sự (u1, u2, u3, u4, u5)
    assert kpi["total_customers"] == EXPECTED_TOTAL_CUSTOMERS, (
        f"Kỳ vọng {EXPECTED_TOTAL_CUSTOMERS} khách hàng duy nhất nhưng nhận được {kpi['total_customers']}. "
        "Đang đếm nhầm customer_id (mã đơn) thay vì customer_unique_id!"
    )
    assert kpi["total_customers"] <= kpi["total_orders"], (
        "Số lượng khách hàng duy nhất không thể lớn hơn số đơn hàng!"
    )


def test_kpi_avg_review_score(mini_db):
    """Kiểm tra điểm đánh giá trung bình của các đơn delivered."""
    kpi = get_kpi_metrics()
    assert round(kpi["avg_review_score"], 2) == EXPECTED_AVG_REVIEW_SCORE, (
        f"Kỳ vọng điểm TB {EXPECTED_AVG_REVIEW_SCORE} nhưng nhận được {kpi['avg_review_score']}"
    )


def test_kpi_excludes_non_delivered_orders(mini_db):
    """Đảm bảo các đơn 'canceled' và 'shipped' tuyệt đối không được tính vào KPI."""
    kpi = get_kpi_metrics()
    # Nếu cộng cả đơn canceled (275) và shipped (440) thì tổng = 1765.0
    assert kpi["total_revenue"] < 1765.0, "Các đơn không phải 'delivered' đang bị tính vào doanh thu!"
    assert kpi["total_orders"] < 8, "Các đơn không phải 'delivered' đang bị tính vào số lượng đơn!"
