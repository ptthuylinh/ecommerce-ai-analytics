"""
Fixture cấu hình và tạo cơ sở dữ liệu SQLite mini_db cho kiểm thử.
"""

import os
import sys
import sqlite3
import pytest

# Đảm bảo import được module từ src
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import src.db  # noqa: E402


@pytest.fixture(scope="session")
def mini_db(tmp_path_factory):
    """
    Tạo SQLite DB tạm thời với schema đầy đủ 6 bảng thật và 8 đơn hàng mẫu tính tay.
    - 1 đơn có 2 dòng thanh toán (trả góp): order_2 (50.0 + 170.0 = 220.0)
    - 1 đơn có 2 review: order_3 (score 4 và 2)
    - 2 đơn cùng 1 customer_unique_id: order_1 và order_3 đều thuộc u1
    - Các đơn có status khác 'delivered': order_7 (canceled), order_8 (shipped)
    - Trải đều qua các tháng (2017-01 đến 2017-08), các bang (SP, RJ, MG, BA, PR, SC, RS)
      và 4 danh mục sản phẩm khác nhau.
    """
    db_dir = tmp_path_factory.mktemp("data")
    db_file = db_dir / "mini_ecommerce.db"
    db_path_str = str(db_file)

    conn = sqlite3.connect(db_path_str)
    cur = conn.cursor()

    # 1. Tạo 6 bảng với schema khớp 100% CSDL thật
    cur.execute("""
    CREATE TABLE orders (
        order_id TEXT,
        customer_id TEXT,
        order_status TEXT,
        order_purchase_timestamp TIMESTAMP,
        order_approved_at TIMESTAMP,
        order_delivered_carrier_date TIMESTAMP,
        order_delivered_customer_date TIMESTAMP,
        order_estimated_delivery_date TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE order_items (
        order_id TEXT,
        order_item_id INTEGER,
        product_id TEXT,
        seller_id TEXT,
        shipping_limit_date TEXT,
        price REAL,
        freight_value REAL
    );
    """)

    cur.execute("""
    CREATE TABLE order_payments (
        order_id TEXT,
        payment_sequential INTEGER,
        payment_type TEXT,
        payment_installments INTEGER,
        payment_value REAL
    );
    """)

    cur.execute("""
    CREATE TABLE products (
        product_id TEXT,
        product_category_name TEXT,
        product_weight_g REAL,
        product_length_cm REAL,
        product_height_cm REAL,
        product_width_cm REAL,
        product_category_name_english TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE customers (
        customer_id TEXT,
        customer_unique_id TEXT,
        customer_zip_code_prefix INTEGER,
        customer_city TEXT,
        customer_state TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE order_reviews (
        review_id TEXT,
        order_id TEXT,
        review_score INTEGER,
        review_comment_title TEXT,
        review_comment_message TEXT,
        review_creation_date TEXT,
        review_answer_timestamp TEXT
    );
    """)

    # 2. Chèn Products
    products_data = [
        ("p1", "telefonia", 200, 15, 5, 10, "telephony"),
        ("p2", "beleza_saude", 350, 20, 10, 15, "health_beauty"),
        ("p3", "informatica_acessorios", 500, 30, 15, 20, "computers_accessories"),
        ("p4", "cama_mesa_banho", 800, 40, 20, 30, "bed_bath_table"),
    ]
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", products_data)

    # 3. Chèn Customers (chú ý: c1 và c3 có chung customer_unique_id = u1)
    customers_data = [
        ("c1", "u1", 10001, "sao paulo", "SP"),
        ("c2", "u2", 20002, "rio de janeiro", "RJ"),
        ("c3", "u1", 10001, "sao paulo", "SP"),  # Cùng u1 với c1
        ("c4", "u3", 30003, "belo horizonte", "MG"),
        ("c5", "u4", 40004, "salvador", "BA"),
        ("c6", "u5", 50005, "curitiba", "PR"),
        ("c7", "u6", 60006, "florianopolis", "SC"),
        ("c8", "u7", 70007, "porto alegre", "RS"),
    ]
    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", customers_data)

    # 4. Chèn Orders (6 delivered, 1 canceled, 1 shipped)
    orders_data = [
        ("order_1", "c1", "delivered", "2017-01-10 10:00:00", "2017-01-10 10:30:00", "2017-01-11", "2017-01-15", "2017-01-25"),
        ("order_2", "c2", "delivered", "2017-02-15 11:00:00", "2017-02-15 11:30:00", "2017-02-16", "2017-02-20", "2017-03-01"),
        ("order_3", "c3", "delivered", "2017-03-20 12:00:00", "2017-03-20 12:30:00", "2017-03-21", "2017-03-26", "2017-04-05"),
        ("order_4", "c4", "delivered", "2017-04-05 13:00:00", "2017-04-05 13:30:00", "2017-04-06", "2017-04-12", "2017-04-20"),
        ("order_5", "c5", "delivered", "2017-05-12 14:00:00", "2017-05-12 14:30:00", "2017-05-13", "2017-05-18", "2017-05-28"),
        ("order_6", "c6", "delivered", "2017-06-18 15:00:00", "2017-06-18 15:30:00", "2017-06-19", "2017-06-25", "2017-07-05"),
        ("order_7", "c7", "canceled", "2017-07-22 16:00:00", "2017-07-22 16:30:00", None, None, "2017-08-05"),
        ("order_8", "c8", "shipped", "2017-08-30 17:00:00", "2017-08-30 17:30:00", "2017-08-31", None, "2017-09-10"),
    ]
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)", orders_data)

    # 5. Chèn Order Items
    items_data = [
        ("order_1", 1, "p1", "s1", "2017-01-16", 100.0, 10.0),
        ("order_2", 1, "p2", "s2", "2017-02-21", 200.0, 20.0),
        ("order_3", 1, "p3", "s3", "2017-03-26", 150.0, 15.0),
        ("order_4", 1, "p4", "s4", "2017-04-11", 300.0, 30.0),
        ("order_5", 1, "p1", "s1", "2017-05-18", 80.0, 10.0),
        ("order_6", 1, "p2", "s2", "2017-06-24", 120.0, 15.0),
        ("order_7", 1, "p3", "s3", "2017-07-28", 250.0, 25.0),
        ("order_8", 1, "p4", "s4", "2017-09-05", 400.0, 40.0),
    ]
    cur.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?, ?)", items_data)

    # 6. Chèn Order Payments (chú ý: order_2 có 2 payment: 50.0 + 170.0 = 220.0)
    payments_data = [
        ("order_1", 1, "credit_card", 1, 110.0),
        ("order_2", 1, "voucher", 1, 50.0),
        ("order_2", 2, "credit_card", 3, 170.0),  # order_2 tổng thanh toán: 220.0
        ("order_3", 1, "credit_card", 1, 165.0),
        ("order_4", 1, "boleto", 1, 330.0),
        ("order_5", 1, "credit_card", 1, 90.0),
        ("order_6", 1, "debit_card", 1, 135.0),
        ("order_7", 1, "credit_card", 1, 275.0),
        ("order_8", 1, "credit_card", 1, 440.0),
    ]
    cur.executemany("INSERT INTO order_payments VALUES (?, ?, ?, ?, ?)", payments_data)

    # 7. Chèn Order Reviews (chú ý: order_3 có 2 reviews: score 4 và 2)
    reviews_data = [
        ("r1", "order_1", 5, "Tot", "Giao nhanh", "2017-01-16", "2017-01-17"),
        ("r2", "order_2", 4, "Hai long", "San pham dep", "2017-02-21", "2017-02-22"),
        ("r3a", "order_3", 4, "On dinh", "Dung tot", "2017-03-27", "2017-03-28"),
        ("r3b", "order_3", 2, "Dong goi kem", "Hop bi mop", "2017-03-28", "2017-03-29"),  # Review thứ 2 của order_3
        ("r4", "order_4", 3, "Binh thuong", "Tam on", "2017-04-13", "2017-04-14"),
        ("r5", "order_5", 5, "Xuat sac", "Rat ung y", "2017-05-19", "2017-05-20"),
        # order_6 không có review (để kiểm tra LEFT JOIN)
        ("r7", "order_7", 1, "Te", "Don bi huy", "2017-07-23", "2017-07-24"),
    ]
    cur.executemany("INSERT INTO order_reviews VALUES (?, ?, ?, ?, ?, ?, ?)", reviews_data)

    conn.commit()
    conn.close()

    # Cấu hình để src.db kết nối tới mini_db này
    old_db_path = getattr(src.db, "DB_PATH", None)
    src.db.DB_PATH = db_path_str
    os.environ["DB_PATH"] = db_path_str
    os.environ["ECOMMERCE_DB_PATH"] = db_path_str

    yield db_path_str

    # Khôi phục DB_PATH sau session test
    if old_db_path is not None:
        src.db.DB_PATH = old_db_path
    os.environ.pop("DB_PATH", None)
    os.environ.pop("ECOMMERCE_DB_PATH", None)
