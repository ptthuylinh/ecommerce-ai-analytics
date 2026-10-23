# 📝 Nhật Ký Phát Triển (Development Log)

Tài liệu ghi lại toàn bộ quá trình thử nghiệm kỹ thuật, các quyết định kiến trúc và bài học rút ra trong suốt dự án.
Mục tiêu là phản ánh trung thực, khách quan diễn biến phát triển (bao gồm cả các thử nghiệm không hiệu quả) để phục vụ việc tối ưu hóa và tra cứu sau này.

---

## 📑 Mục lục
- [2026-10-23: Tối ưu tốc độ dashboard (10 truy vấn JOIN -> bảng phẳng + pandas)](#2026-10-23-tối-ưu-tốc-độ-dashboard-10-truy-vấn-join---bảng-phẳng--pandas)
- [2026-10-23: Thiết kế lại dashboard (v1 -> v2)](#2026-10-23-thiết-kế-lại-dashboard-v1---v2)
- [[Ngày]: Viết lại truy vấn KPI (điền sau khi làm xong)](#ngày-viết-lại-truy-vấn-kpi-điền-sau-khi-làm-xong)
- [2026-10-22: Thử tối ưu get_kpi_metrics bằng index](#2026-10-22-thử-tối-ưu-get_kpi_metrics-bằng-index)
- [2026-10-22: Thiết lập CI và kiểm thử](#2026-10-22-thiết-lập-ci-và-kiểm-thử)
- [💡 Bài học chung](#-bài-học-chung)

---

## 2026-10-23: Tối ưu tốc độ dashboard (10 truy vấn JOIN -> bảng phẳng + pandas)
- Bối cảnh: mỗi lần mở trang hoặc đổi bộ lọc, dashboard chạy 10 truy vấn JOIN trên SQLite, tổng ~40,8s. @st.cache_data chỉ giúp khi lặp lại đúng bộ lọc cũ.
- Giả thuyết đã loại: thêm index (mục 2026-10-22, không cải thiện: 4,74s -> 5,08s).
- Chẩn đoán (bộ lọc 2017-01-01..2018-08-31, status delivered): hàm chậm nhất là kpi_extended 7,18s; delay_vs_review 4,77s; review_distribution 4,88s; revenue_by_state 4,86s; payment_mix 4,30s.
- Giải pháp: nạp 2 bảng phẳng một lần (orders_fact 99.441 dòng, items_fact 112.650 dòng), gộp payments/reviews theo order_id, lọc và group-by bằng pandas (src/analytics.py). Giữ nguyên src/db.py làm "đáp án chuẩn".
- Kiểm chứng: 21 test đối chiếu analytics vs SQL (7 hàm x 3 bộ lọc) + 3 test trên DB thật, tổng 24/24 pass. Chưa phủ: kpi_previous_period, review_distribution, payment_mix.
- Kết quả:

| Tình huống | Trước | Sau |
|---|---|---|
| Nạp dữ liệu lần đầu (1 lần) | không có | 14,76 s |
| Mỗi lần đổi bộ lọc (lọc + 10 hàm) | 40,77 s | 0,586 s |
| Tăng tốc | | 69,5x |

- Đánh đổi: tốn RAM giữ DataFrame; dữ liệu nạp một lần nên không tự cập nhật khi DB đổi; lần khởi động đầu vẫn ~15s.
- Hướng tiếp: lưu bảng phẳng ra parquet để giảm thời gian nạp đầu.
- Bài học: đo trước khi tối ưu (index không giúp, tính lại mỗi lần mới là nút thắt); với dữ liệu ~100k dòng thì tính một lần rồi lọc trong bộ nhớ là phù hợp; luôn có test đối chiếu khi viết lại logic.

---

## 2026-10-23: Thiết kế lại dashboard (v1 -> v2)

* **Ngày:** 2026-10-23
* **Bối cảnh:** Phiên bản v1 chỉ có 4 thẻ KPI tĩnh và 2 biểu đồ, không có mốc so sánh, không chỉ ra được nguyên nhân và vấn đề cốt lõi nên ít mang lại giá trị thực tế cho người ra quyết định.
* **Vấn đề đã xác định:**
  1. KPI không có mốc so sánh (không biết tăng hay giảm, tốt hay xấu).
  2. Dữ liệu sàn Olist bị thưa thớt ở giai đoạn cuối năm 2016 và cuối năm 2018, dẫn đến biểu đồ xu hướng doanh thu bị sụt giảm giả tạo và gây hiểu nhầm.
  3. Thiếu góc nhìn vận hành quan trọng (độ trễ giao hàng, trải nghiệm đánh giá, phân bổ thanh toán và khách hàng).
* **Quyết định:**
  * Chia lại cấu trúc Dashboard thành 4 tabs chuyên sâu (*Tổng quan, Giao hàng & Trải nghiệm, Sản phẩm, Khách hàng & Khu vực*).
  * Mặc định lọc khoảng thời gian chuẩn từ `2017-01-01` đến `2018-08-31` kèm ghi chú giải thích.
  * Bổ sung chỉ số delta so với kỳ liền trước cho các thẻ KPI.
  * Bổ sung biểu đồ phân tích tương quan điểm đánh giá theo từng mức độ trễ giao hàng.
* **Kết quả:** [điền: ảnh trước/sau, số lượng biểu đồ, thời gian tải trang trước/sau khi dùng cache].
* **Phát hiện từ dữ liệu:** [điền sau khi chạy: ví dụ điểm đánh giá TB khi giao trễ so với giao đúng hạn là bao nhiêu].
* **Bài học:** Dashboard không chỉ để trưng bày số liệu mà cần trả lời rõ 3 câu hỏi cho người quản trị: "Đang tốt hay xấu, vấn đề nằm ở đâu, và cần hành động gì?".
* **Liên hệ tiếp theo:** Các phát hiện và số liệu định lượng về rủi ro giao hàng trễ hạn chính là tiền đề và động lực cốt lõi để xây dựng mô hình AI dự báo ở Giai đoạn 3.

---

## [Ngày]: Viết lại truy vấn KPI (điền sau khi làm xong)

* **Ngày:** [điền sau]
* **Bối cảnh:** [điền sau]
* **Giả thuyết:** [điền sau]
* **Thử nghiệm:** [điền sau]
* **Kết quả:**
  * KPI cũ: [điền] | KPI mới: [điền]
  * Thời gian cũ: [điền] | Mới: [điền]
  * Giải thích chênh lệch: [điền]
* **Quyết định / Bài học:** [điền sau]

---

## 2026-10-22: Thử tối ưu get_kpi_metrics bằng index

* **Ngày:** 2026-10-22
* **Bối cảnh:** Bộ kiểm thử test mất ~27.7s, hàm `get_kpi_metrics()` mất ~4.7s khi chạy.
* **Giả thuyết:** Cơ sở dữ liệu SQLite chưa có index trên các cột phục vụ JOIN và lọc điều kiện.
* **Thử nghiệm:** Tạo 9 index thông qua script `scripts/create_indexes.py` (`orders`: `customer_id`, `order_status`, `order_purchase_timestamp`; `order_items`: `order_id`, `product_id`; `order_payments`: `order_id`; `order_reviews`: `order_id`; `customers`: `customer_state`; `products`: `product_category_name`), chạy lệnh `ANALYZE;` và đo lại thời gian thực thi.
* **Kết quả:**
  * Thời gian chạy: 4.74s -> 5.08s (không cải thiện).
  * Số liệu KPI không đổi: 96,477 đơn; doanh thu R$ 15,492,353.59; điểm TB 4.15.
  * *Phân tích:* Khoảng 97% đơn hàng có `order_status = 'delivered'` nên điều kiện lọc không thu hẹp phạm vi quét bảng; chi phí lớn nhất nằm ở thao tác JOIN nhiều bảng lớn và tính toán `COUNT(DISTINCT)`.
  * *Phát hiện:* Cột `total_customers` hiện đang đếm `customer_id` (trùng bằng số lượng đơn) thay vì `customer_unique_id`; việc JOIN đồng thời giữa `order_payments` và `order_reviews` có nguy cơ gây nhân dòng (fan-out) làm sai lệch tính toán.
* **Quyết định / Bài học:** Chưa commit file DB có chứa index; chuyển hướng sang viết lại câu truy vấn bằng kỹ thuật CTE để tách riêng việc tổng hợp từng bảng trước khi ghép nối.

---

## 2026-10-22: Thiết lập CI và kiểm thử

* **Ngày:** 2026-10-22
* **Bối cảnh:** Cần đảm bảo pipeline CI chạy kiểm thử thật, không gặp tình trạng "xanh giả".
* **Giả thuyết:** Cấu hình đường dẫn import và công cụ test cần được đồng bộ giữa môi trường máy cục bộ và GitHub Actions.
* **Thực nghiệm:**
  * Xác nhận pytest collect được 2 test và cả 2 đều PASSED trên máy cục bộ.
  * Thêm file `pytest.ini` (cấu hình `pythonpath`, `testpaths`).
  * Thêm file `.flake8` (loại trừ thư mục `.venv`).
  * Đổi bước chạy test trong `.github/workflows/ci.yml` thành `python -m pytest -v`.
  * Thêm thư viện `openpyxl` vào `requirements.txt`.
  * Xác nhận file `data/ecommerce.db` có trong Git để pipeline CI có dữ liệu chạy test.
* **Kết quả:** Bộ kiểm thử chạy ổn định trên CI, kiểm tra chính xác cả kết nối database và tính hợp lệ của số liệu KPI.
* **Quyết định / Bài học:** Lệnh `pytest` trơn và `python -m pytest` khác nhau về đường dẫn import (`sys.path`); sử dụng `python -m pytest` giúp tự động nhận diện root module của project trên CI.

---

## 💡 Bài học chung

* **Đo lường trước khi tối ưu:** Luôn thực hiện đo đạc định lượng với số liệu thực tế trước và sau khi thay đổi; không giả định rằng việc thêm index luôn luôn làm tăng tốc truy vấn.
* **Kiểm tra tính đúng đắn của số liệu:** Tối ưu hóa hiệu năng phải đi kèm với việc đối soát ngữ nghĩa nghiệp vụ của dữ liệu (như việc phân biệt giữa `customer_id` và `customer_unique_id`).
* **Tránh rủi ro nhân dòng (fan-out) khi JOIN:** Khi một thực thể có quan hệ 1-N với nhiều bảng độc lập (như payments và reviews), JOIN trực tiếp sẽ nhân số dòng theo tích Đề-các, gây chậm đột biến do `COUNT(DISTINCT)` và làm sai lệch hàm tổng hợp `SUM`. Ưu tiên sử dụng CTE hoặc sub-queries để tổng hợp trước.
