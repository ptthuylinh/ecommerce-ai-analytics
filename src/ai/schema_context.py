"""
Module định nghĩa ngữ cảnh CSDL (Schema Context) và các ví dụ mẫu (Few-shot Examples)
phục vụ AI Agent Text-to-SQL trong dự án E-Commerce Analytics.

Tuân thủ nghiêm ngặt:
1. Thông tin 6 bảng whitelist lấy từ schema thật (PRAGMA table_info). Không bịa cột.
2. Quy tắc nghiệp vụ Olist E-Commerce (doanh thu chỉ tính delivered, CTE gộp tránh nhân dòng,
   đếm khách bằng customer_unique_id, định dạng ngày text, tiền tệ Real Brazil - BRL).
3. Tập Few-shot chuẩn hóa, mọi câu SQL đều vượt qua sql_guard.validate_sql và thực thi
   thành công trên SQLite DB.
"""

from typing import Any, Dict, List

# ==============================================================================
# 1. METADATA CHI TIẾT 6 BẢNG WHITELIST TRONG CƠ SỞ DỮ LIỆU
# ==============================================================================

SCHEMA_TABLES: Dict[str, Dict[str, Any]] = {
    "orders": {
        "description": "Bảng quản lý thông tin vòng đời, trạng thái và mốc thời gian của từng đơn hàng.",
        "primary_key": ["order_id"],
        "foreign_keys": [
            {"from": "customer_id", "to": "customers.customer_id", "description": "Liên kết tới phiên khách hàng đặt đơn"},
        ],
        "columns": {
            "order_id": {"type": "TEXT", "description": "Mã định danh duy nhất của đơn hàng (Primary Key)."},
            "customer_id": {"type": "TEXT", "description": "Mã phiên khách hàng (Foreign Key -> customers.customer_id). Mỗi đơn có 1 customer_id mới."},
            "order_status": {"type": "TEXT", "description": "Trạng thái đơn hàng. Quan trọng: chỉ tính 'delivered' khi tính doanh thu thực tế."},
            "order_purchase_timestamp": {"type": "TIMESTAMP", "description": "Thời điểm khách đặt mua (dạng text 'YYYY-MM-DD HH:MM:SS'). Dùng strftime/substr."},
            "order_approved_at": {"type": "TIMESTAMP", "description": "Thời điểm thanh toán được phê duyệt thành công."},
            "order_delivered_carrier_date": {"type": "TIMESTAMP", "description": "Thời điểm bàn giao đơn hàng cho đơn vị vận chuyển/bưu cục."},
            "order_delivered_customer_date": {"type": "TIMESTAMP", "description": "Thời điểm khách hàng nhận được kiện hàng thực tế. Dùng tính ngày trễ/sớm."},
            "order_estimated_delivery_date": {"type": "TIMESTAMP", "description": "Ngày dự kiến giao hàng ban đầu cam kết với khách hàng."},
        },
    },
    "order_items": {
        "description": "Bảng chi tiết các sản phẩm (mục hàng) trong từng đơn hàng, giá bán và cước vận chuyển.",
        "primary_key": ["order_id", "order_item_id"],
        "foreign_keys": [
            {"from": "order_id", "to": "orders.order_id", "description": "Liên kết tới đơn hàng chứa sản phẩm này"},
            {"from": "product_id", "to": "products.product_id", "description": "Liên kết tới thông tin sản phẩm"},
        ],
        "columns": {
            "order_id": {"type": "TEXT", "description": "Mã đơn hàng (Foreign Key -> orders.order_id)."},
            "order_item_id": {"type": "INTEGER", "description": "Số thứ tự mục hàng trong cùng một đơn hàng (1, 2, 3...)."},
            "product_id": {"type": "TEXT", "description": "Mã định danh sản phẩm (Foreign Key -> products.product_id)."},
            "seller_id": {"type": "TEXT", "description": "Mã người bán cung cấp sản phẩm này."},
            "shipping_limit_date": {"type": "TEXT", "description": "Thời hạn người bán phải bàn giao gói hàng cho bưu cục."},
            "price": {"type": "REAL", "description": "Giá bán của từng sản phẩm (Real Brazil - BRL)."},
            "freight_value": {"type": "REAL", "description": "Cước phí vận chuyển cho sản phẩm này (Real Brazil - BRL)."},
        },
    },
    "order_payments": {
        "description": "Bảng chi tiết các giao dịch và hình thức thanh toán cho đơn hàng.",
        "primary_key": ["order_id", "payment_sequential"],
        "foreign_keys": [
            {"from": "order_id", "to": "orders.order_id", "description": "Liên kết tới đơn hàng được thanh toán"},
        ],
        "columns": {
            "order_id": {"type": "TEXT", "description": "Mã đơn hàng (Foreign Key -> orders.order_id). Một đơn có thể có nhiều dòng thanh toán."},
            "payment_sequential": {"type": "INTEGER", "description": "Số thứ tự lượt giao dịch thanh toán trong đơn (1, 2...)."},
            "payment_type": {"type": "TEXT", "description": "Phương thức thanh toán: 'credit_card', 'boleto', 'voucher', 'debit_card'."},
            "payment_installments": {"type": "INTEGER", "description": "Số đợt trả góp đã đăng ký (1 = thanh toán 1 lần, >1 = trả góp)."},
            "payment_value": {"type": "REAL", "description": "Giá trị giao dịch thanh toán (Real Brazil - BRL)."},
        },
    },
    "products": {
        "description": "Bảng danh mục và thông tin vật lý của sản phẩm.",
        "primary_key": ["product_id"],
        "foreign_keys": [],
        "columns": {
            "product_id": {"type": "TEXT", "description": "Mã định danh duy nhất của sản phẩm (Primary Key)."},
            "product_category_name": {"type": "TEXT", "description": "Tên danh mục gốc tiếng Bồ Đào Nha."},
            "product_category_name_english": {"type": "TEXT", "description": "Tên danh mục tiếng Anh chuẩn hóa. LUÔN DÙNG CỘT NÀY CHO TRUY VẤN & BỘ LỌC."},
            "product_weight_g": {"type": "REAL", "description": "Trọng lượng sản phẩm tính theo gram (g)."},
            "product_length_cm": {"type": "REAL", "description": "Chiều dài sản phẩm (cm)."},
            "product_height_cm": {"type": "REAL", "description": "Chiều cao sản phẩm (cm)."},
            "product_width_cm": {"type": "REAL", "description": "Chiều rộng sản phẩm (cm)."},
        },
    },
    "customers": {
        "description": "Bảng thông tin khách hàng và vị trí địa lý sinh sống tại Brazil.",
        "primary_key": ["customer_id"],
        "foreign_keys": [],
        "columns": {
            "customer_id": {"type": "TEXT", "description": "Mã phiên đơn hàng của khách (Primary Key). Cùng 1 khách mua 2 lần sẽ có 2 customer_id khác nhau."},
            "customer_unique_id": {"type": "TEXT", "description": "Mã định danh DUY NHẤT của khách hàng thực tế. LUÔN DÙNG CỘT NÀY ĐỂ ĐẾM KHÁCH HÀNG & TÍNH MUA LẠI."},
            "customer_zip_code_prefix": {"type": "INTEGER", "description": "5 chữ số đầu của mã bưu điện (Zip Code prefix)."},
            "customer_city": {"type": "TEXT", "description": "Tên thành phố sinh sống của khách hàng."},
            "customer_state": {"type": "TEXT", "description": "Mã 2 ký tự viết tắt của Bang tại Brazil (ví dụ: 'SP', 'RJ', 'MG', 'RS', 'PR'...)."},
        },
    },
    "order_reviews": {
        "description": "Bảng lưu trữ điểm số đánh giá và nhận xét của khách hàng sau khi nhận hàng.",
        "primary_key": ["review_id"],
        "foreign_keys": [
            {"from": "order_id", "to": "orders.order_id", "description": "Liên kết tới đơn hàng nhận được đánh giá"},
        ],
        "columns": {
            "review_id": {"type": "TEXT", "description": "Mã định danh duy nhất của bản ghi đánh giá (Primary Key)."},
            "order_id": {"type": "TEXT", "description": "Mã đơn hàng được đánh giá (Foreign Key -> orders.order_id)."},
            "review_score": {"type": "INTEGER", "description": "Điểm số đánh giá mức độ hài lòng của khách hàng (thang điểm nguyên từ 1 đến 5 sao)."},
            "review_comment_title": {"type": "TEXT", "description": "Tiêu đề nhận xét của khách hàng."},
            "review_comment_message": {"type": "TEXT", "description": "Nội dung phản hồi chi tiết từ khách hàng."},
            "review_creation_date": {"type": "TEXT", "description": "Ngày hệ thống gửi khảo sát đánh giá tới khách hàng."},
            "review_answer_timestamp": {"type": "TEXT", "description": "Thời điểm khách hàng hoàn tất gửi câu trả lời đánh giá."},
        },
    },
}

# ==============================================================================
# 2. QUY TẮC NGHIỆP VỤ & BẢO MẬT (BUSINESS RULES)
# ==============================================================================

BUSINESS_RULES: List[str] = [
    "DOANH THU & ĐƠN HÀNG THÀNH CÔNG: Khi tính toán doanh thu (Revenue / GMV) hoặc số đơn hàng thực tế, LUÔN thêm điều kiện `o.order_status = 'delivered'`, trừ khi người dùng chỉ định rõ trạng thái khác (ví dụ: 'canceled').",
    "CHỐNG NHÂN DÒNG (FAN-OUT TRONG JOIN): Vì một đơn hàng có thể có nhiều dòng thanh toán (order_payments) và nhiều đánh giá (order_reviews), TUYỆT ĐỐI KHÔNG JOIN trực tiếp orders với order_payments và order_reviews trong cùng một truy vấn phẳng. Hãy dùng CTE (WITH) hoặc Subquery để SUM(payment_value) hoặc AVG/SUM(review_score) theo order_id trước khi JOIN.",
    "ĐẾM KHÁCH HÀNG: Luôn dùng `COUNT(DISTINCT c.customer_unique_id)` để đếm số khách hàng thực tế và xác định khách hàng mua lại (repeat customers: khách có từ 2 đơn hàng thành công trở lên). Không dùng `customer_id` vì mã này thay đổi theo từng đơn.",
    "ĐỊNH DẠNG NGÀY THÁNG: Mọi trường ngày tháng (order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date) được lưu dưới dạng chuỗi text 'YYYY-MM-DD HH:MM:SS'. Sử dụng `strftime('%Y-%m', col)` để nhóm theo tháng, `strftime('%Y-%m-%d', col)` hoặc `date(col)` để so sánh ngày, và `julianday(d2) - julianday(d1)` để tính số ngày chênh lệch.",
    "GIAO HÀNG TRỄ HẠN: Một đơn hàng được xem là giao trễ hạn khi ngày khách nhận thực tế lớn hơn ngày dự kiến: `date(o.order_delivered_customer_date) > date(o.order_estimated_delivery_date)`.",
    "TÊN DANH MỤC SẢN PHẨM: Luôn sử dụng cột `product_category_name_english` trong bảng `products` để lọc và hiển thị danh mục sản phẩm (ví dụ: 'bed_bath_table', 'health_beauty', 'sports_leisure').",
    "ĐƠN VỊ TIỀN TỆ: Mọi giá trị tiền tệ trong CSDL được tính bằng đồng Real Brazil (BRL, R$). Làm tròn số tiền 2 chữ số thập phân bằng `ROUND(..., 2)`.",
    "KHOẢNG THỜI GIAN MẶC ĐỊNH: Nếu câu hỏi của người dùng không nêu rõ mốc thời gian cụ thể, mặc định áp dụng khoảng thời gian dữ liệu đầy đủ từ 2017-01-01 đến 2018-08-31 (`o.order_purchase_timestamp >= '2017-01-01 00:00:00' AND o.order_purchase_timestamp <= '2018-08-31 23:59:59'`) và phải nêu rõ khoảng thời gian mặc định này trong câu trả lời.",
    "BẢO MẬT SQL GUARD: Chỉ tạo ĐÚNG 1 câu lệnh bắt đầu bằng `SELECT` hoặc `WITH ... SELECT`. Không viết comment (-- hoặc /* */). Không dùng dấu chấm phẩy ở giữa câu lệnh. Không sử dụng từ khóa thay đổi dữ liệu (DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, v.v.). Chỉ sử dụng 6 bảng trong whitelist (orders, order_items, order_payments, products, customers, order_reviews).",
]


# ==============================================================================
# 3. DANH SÁCH FEW-SHOT EXAMPLES (CÂU HỎI TIẾNG VIỆT -> SQL CHUẨN)
# ==============================================================================

FEW_SHOTS: List[Dict[str, str]] = [
    {
        "question": "Top 5 danh mục sản phẩm có doanh thu cao nhất trong tháng 01/2018 là gì?",
        "sql": """SELECT 
    p.product_category_name_english AS category,
    ROUND(SUM(i.price), 2) AS total_revenue,
    COUNT(i.order_item_id) AS items_sold
FROM order_items i
JOIN products p ON i.product_id = p.product_id
JOIN orders o ON i.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND strftime('%Y-%m', o.order_purchase_timestamp) = '2018-01'
  AND p.product_category_name_english IS NOT NULL
GROUP BY category
ORDER BY total_revenue DESC
LIMIT 5;""",
    },
    {
        "question": "Tổng doanh thu và số đơn hàng theo từng bang tại Brazil là bao nhiêu?",
        "sql": """WITH p AS (
    SELECT order_id, SUM(payment_value) AS order_payment
    FROM order_payments
    GROUP BY order_id
)
SELECT 
    c.customer_state,
    ROUND(SUM(p.order_payment), 2) AS revenue,
    COUNT(DISTINCT o.order_id) AS orders
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN p ON o.order_id = p.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY revenue DESC;""",
    },
    {
        "question": "Tỷ lệ đơn hàng giao trễ so với ngày dự kiến là bao nhiêu phần trăm?",
        "sql": """SELECT 
    COUNT(DISTINCT o.order_id) AS total_delivered_orders,
    SUM(CASE WHEN date(o.order_delivered_customer_date) > date(o.order_estimated_delivery_date) THEN 1 ELSE 0 END) AS delayed_orders,
    ROUND(SUM(CASE WHEN date(o.order_delivered_customer_date) > date(o.order_estimated_delivery_date) THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT o.order_id), 2) AS delay_rate_pct
FROM orders o
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL;""",
    },
    {
        "question": "Điểm đánh giá trung bình theo từng mức độ giao hàng (sớm, đúng hạn, trễ) là bao nhiêu?",
        "sql": """WITH r AS (
    SELECT order_id, AVG(review_score) AS avg_review
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
    ROUND(AVG(r.avg_review), 2) AS avg_review_score
FROM orders o
JOIN r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
GROUP BY delay_status
ORDER BY orders DESC;""",
    },
    {
        "question": "Có bao nhiêu khách hàng mua lại từ 2 lần trở lên và tỷ lệ mua lại là bao nhiêu?",
        "sql": """WITH customer_orders AS (
    SELECT 
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT 
    COUNT(*) AS total_customers,
    SUM(CASE WHEN order_count >= 2 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(SUM(CASE WHEN order_count >= 2 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS repeat_rate_pct
FROM customer_orders;""",
    },
    {
        "question": "Cơ cấu doanh thu và số lượng đơn hàng theo từng hình thức thanh toán là gì?",
        "sql": """SELECT 
    p.payment_type,
    ROUND(SUM(p.payment_value), 2) AS total_revenue,
    COUNT(DISTINCT o.order_id) AS orders
FROM orders o
JOIN order_payments p ON o.order_id = p.order_id
WHERE o.order_status = 'delivered'
GROUP BY p.payment_type
ORDER BY total_revenue DESC;""",
    },
    {
        "question": "Tổng doanh thu, tổng số đơn hàng, điểm đánh giá trung bình và tổng số khách hàng thành công là bao nhiêu?",
        "sql": """WITH p AS (
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
    ROUND(SUM(p.order_payment), 2) AS total_revenue,
    ROUND(SUM(r.sum_review) * 1.0 / SUM(r.count_review), 2) AS avg_review_score,
    COUNT(DISTINCT c.customer_unique_id) AS total_customers
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
LEFT JOIN p ON o.order_id = p.order_id
LEFT JOIN r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered';""",
    },
    {
        "question": "Doanh thu và số lượng đơn hàng theo từng tháng là bao nhiêu?",
        "sql": """WITH p AS (
    SELECT order_id, SUM(payment_value) AS order_payment
    FROM order_payments
    GROUP BY order_id
)
SELECT 
    strftime('%Y-%m', o.order_purchase_timestamp) AS month,
    ROUND(SUM(p.order_payment), 2) AS revenue,
    COUNT(DISTINCT o.order_id) AS orders
FROM orders o
JOIN p ON o.order_id = p.order_id
WHERE o.order_status = 'delivered'
GROUP BY month
ORDER BY month;""",
    },
    {
        "question": "Số lượng đơn hàng phân bố theo từng thang điểm đánh giá từ 1 đến 5 sao là bao nhiêu?",
        "sql": """SELECT 
    r.review_score,
    COUNT(DISTINCT o.order_id) AS orders
FROM orders o
JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY r.review_score
ORDER BY r.review_score;""",
    },
    {
        "question": "Giá trị đơn hàng trung bình và thời gian giao hàng trung bình là bao nhiêu?",
        "sql": """WITH p AS (
    SELECT order_id, SUM(payment_value) AS order_payment
    FROM order_payments
    GROUP BY order_id
)
SELECT 
    ROUND(SUM(p.order_payment) / COUNT(DISTINCT o.order_id), 2) AS avg_order_value,
    ROUND(AVG(julianday(o.order_delivered_customer_date) - julianday(o.order_purchase_timestamp)), 2) AS avg_delivery_days
FROM orders o
JOIN p ON o.order_id = p.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_purchase_timestamp IS NOT NULL;""",
    },
]

# ==============================================================================
# 4. HÀM XÂY DỰNG SCHEMA PROMPT CHO LLM
# ==============================================================================

def build_schema_prompt(include_few_shots: bool = True) -> str:
    """
    Tạo chuỗi System Prompt hoàn chỉnh mô tả cấu trúc 6 bảng CSDL Olist E-Commerce,
    các quy tắc nghiệp vụ cốt lõi, cùng các ví dụ Few-Shot mẫu.

    Parameters:
        include_few_shots: Có kèm danh sách các ví dụ Few-shot vào prompt hay không.
    """
    lines: List[str] = [
        "Bạn là Chuyên gia Dữ liệu & AI Text-to-SQL cho nền tảng E-Commerce Analytics (CSDL SQLite).",
        "Nhiệm vụ của bạn là chuyển đổi câu hỏi kinh doanh bằng tiếng Việt thành ĐÚNG 1 câu lệnh SQL SQLite an toàn và chính xác.",
        "",
        "=== 1. CẤU TRÚC 6 BẢNG DỮ LIỆU ĐƯỢC PHÉP TRUY VẤN (WHITELIST TABLES) ===",
    ]

    for table_name, info in SCHEMA_TABLES.items():
        lines.append(f"\nBảng: `{table_name}`")
        lines.append(f"Mô tả: {info['description']}")
        lines.append(f"Khóa chính (PK): {', '.join(info['primary_key'])}")
        
        if info["foreign_keys"]:
            fk_strs = [f"`{fk['from']}` -> `{fk['to']}` ({fk['description']})" for fk in info["foreign_keys"]]
            lines.append("Khóa ngoại (FK): " + "; ".join(fk_strs))
        else:
            lines.append("Khóa ngoại (FK): Không có")

        lines.append("Danh sách các cột:")
        for col_name, col_info in info["columns"].items():
            lines.append(f"  - `{col_name}` ({col_info['type']}): {col_info['description']}")

    lines.append("\n=== 2. CÁC QUY TẮC NGHIỆP VỤ & BẢO MẬT BẮT BUỘC ===")
    for idx, rule in enumerate(BUSINESS_RULES, 1):
        lines.append(f"{idx}. {rule}")

    if include_few_shots and FEW_SHOTS:
        lines.append("\n=== 3. CÁC VÍ DỤ MẪU (FEW-SHOT EXAMPLES) ===")
        for idx, shot in enumerate(FEW_SHOTS, 1):
            lines.append(f"\n[Ví dụ {idx}]")
            lines.append(f"Câu hỏi: {shot['question']}")
            lines.append("SQL:")
            lines.append(shot["sql"])

    lines.append("\n=== 4. ĐỊNH DẠNG ĐẦU RA ===")
    lines.append("Chỉ trả về ĐÚNG 1 câu lệnh SQL chuẩn SQLite (bắt đầu bằng SELECT hoặc WITH). Không kèm giải thích, không bọc markdown ```sql nếu không yêu cầu, không ghi chú.")

    return "\n".join(lines)


def get_few_shots() -> List[Dict[str, str]]:
    """Trả về bản sao danh sách các ví dụ Few-Shot chuẩn hóa."""
    return list(FEW_SHOTS)
