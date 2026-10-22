# 📝 Nhật Ký Phát Triển (Development Log)

Tài liệu ghi lại toàn bộ quá trình thử nghiệm kỹ thuật, các quyết định kiến trúc và bài học rút ra trong suốt dự án.
Mục tiêu là phản ánh trung thực, khách quan diễn biến phát triển (bao gồm cả các thử nghiệm không hiệu quả) để phục vụ việc tối ưu hóa và tra cứu sau này.

---

## 📑 Mục lục
- [[Ngày]: Viết lại truy vấn KPI (điền sau khi làm xong)](#ngày-viết-lại-truy-vấn-kpi-điền-sau-khi-làm-xong)
- [2026-10-22: Thử tối ưu get_kpi_metrics bằng index](#2026-10-22-thử-tối-ưu-get_kpi_metrics-bằng-index)
- [2026-10-22: Thiết lập CI và kiểm thử](#2026-10-22-thiết-lập-ci-và-kiểm-thử)
- [💡 Bài học chung](#-bài-học-chung)

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
