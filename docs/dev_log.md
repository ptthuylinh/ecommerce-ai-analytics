# 📝 Nhật Ký Phát Triển (Development Log)

Tài liệu ghi lại toàn bộ quá trình thử nghiệm kỹ thuật, các quyết định kiến trúc và bài học rút ra trong suốt dự án.
Mục tiêu là phản ánh trung thực, khách quan diễn biến phát triển (bao gồm cả các thử nghiệm không hiệu quả) để phục vụ việc tối ưu hóa và tra cứu sau này.

---

## 📑 Mục lục
- [2026-10-26: Cải thiện trải nghiệm người dùng, trực quan hóa biểu đồ và xuất báo cáo (UC04)](#2026-10-26-cải-thiện-trải-nghiệm-người-dùng-trực-quan-hóa-biểu-đồ-và-xuất-báo-cáo-uc04)
  - [1. Cải thiện UX bộ lọc (Bang & Danh mục sản phẩm)](#1-cải-thiện-ux-bộ-lọc-bang--danh-mục-sản-phẩm)
  - [2. Thống nhất màu biểu đồ và chỉnh sửa biểu đồ](#2-thống-nhất-màu-biểu-đồ-và-chỉnh-sửa-biểu-đồ)
  - [3. Sửa thẻ KPI và chuẩn hóa Delta](#3-sửa-thẻ-kpi-và-chuẩn-hóa-delta)
  - [4. Xuất báo cáo UC04 và trang chủ điều hướng](#4-xuất-báo-cáo-uc04-và-trang-chủ-điều-hướng)
  - [5. Quan sát về triển khai và chiến lược nhánh](#5-quan-sát-về-triển-khai-và-chiến-lược-nhánh)
- [2026-10-23: Tối ưu tốc độ dashboard (10 truy vấn JOIN -> bảng phẳng + pandas)](#2026-10-23-tối-ưu-tốc-độ-dashboard-10-truy-vấn-join---bảng-phẳng--pandas)
- [2026-10-23: Thiết kế lại dashboard (v1 -> v2)](#2026-10-23-thiết-kế-lại-dashboard-v1---v2)
- [[Ngày]: Viết lại truy vấn KPI (điền sau khi làm xong)](#ngày-viết-lại-truy-vấn-kpi-điền-sau-khi-làm-xong)
- [2026-10-22: Thử tối ưu get_kpi_metrics bằng index](#2026-10-22-thử-tối-ưu-get_kpi_metrics-bằng-index)
- [2026-10-22: Thiết lập CI và kiểm thử](#2026-10-22-thiết-lập-ci-và-kiểm-thử)
- [💡 Bài học chung](#-bài-học-chung)

---

## 2026-10-26: Cải thiện trải nghiệm người dùng, trực quan hóa biểu đồ và xuất báo cáo (UC04)

### 1. Cải thiện UX bộ lọc (Bang & Danh mục sản phẩm)
- **Bối cảnh:** Bộ lọc trên sidebar cung cấp 2 chiều phân tích chính: Bang của khách hàng (`customer_state`) và Danh mục sản phẩm (`product_category_name_english`).
- **Vấn đề:**
  - Bang chỉ hiển thị mã 2 ký tự (SP, RJ, MG...), gây khó tiếp cận cho người dùng không am hiểu địa lý Brazil.
  - Danh mục hiển thị tên gốc tiếng Anh hoặc slug tiếng Bồ Đào Nha (`bed_bath_table`, `agro_industry_and_commerce`...), chưa có bản địa hóa tiếng Việt.
  - Nếu thay đổi trực tiếp giá trị option trong multiselect sang tiếng Việt sẽ phá vỡ logic lọc trong DB và DataFrame pandas (vốn khớp theo mã gốc).
- **Quyết định:**
  - Tách bạch giá trị dữ liệu bên dưới (mã gốc) khỏi nhãn hiển thị trực quan thông qua `format_func` của Streamlit multiselect và module mới `src/ui/labels.py`.
  - Tạo từ điển `STATE_NAMES` (27 bang Brazil theo ISO 3166-2:BR) và hàm `state_label()` hiển thị dạng `"São Paulo (SP)"`.
  - Tạo từ điển `CATEGORY_VI` dịch tự nhiên, chuẩn hóa toàn bộ danh mục sản phẩm từ CSDL. Đã dịch: **72 / 72 danh mục (100%)**, số danh mục còn fallback: **0**.
  - Giá trị NULL / rỗng / nan chuẩn hóa hiển thị thành `"Chưa phân loại"`.
  - Sắp xếp bang theo số lượng đơn hàng thực tế giảm dần (`STATE_ORDER`), danh mục theo doanh thu thực tế giảm dần (`CATEGORY_ORDER`), thêm placeholder và help tooltip.
- **Thực hiện:** Tạo mới `src/ui/labels.py`, cập nhật `src/ui/filters.py` (chuẩn hóa mã qua `PORTUGUESE_TO_ENGLISH`), xuất nhãn qua `src/ui/__init__.py`.
- **Kiểm chứng:** Bộ unit test `tests/test_labels.py` và integration test `test_all_db_categories_translated` kết nối trực tiếp `data/ecommerce.db`: xác nhận 72/72 danh mục DISTINCT trong DB đều có trong `CATEGORY_VI` và `category_label(x)` không chứa dấu gạch dưới (`_`).
- **Đánh đổi:** Cần duy trì từ điển dịch khi DB xuất hiện thêm danh mục mới; giải quyết bằng cơ chế fallback `.replace("_", " ").title()`.
- **Bài học:** Tách lớp trình bày khỏi dữ liệu giúp giao diện thân thiện với người dùng bản địa mà không làm ảnh hưởng tính ổn định của hệ thống truy vấn backend.

### 2. Thống nhất màu biểu đồ và chỉnh sửa biểu đồ
- **Bối cảnh:** Nhánh `main` (bản deploy live) sử dụng giao diện mặc định Streamlit Dark với bảng màu xanh dương (`#1E88E5`), đỏ (`#E53935`) và xanh ngọc (`#00897B`) được đánh giá cao về độ rõ ràng. Trong khi đó, nhánh `develop` trước đó đưa vào màu tím `#6366F1` và CSS can thiệp sâu, tạo sự bất nhất.
- **Vấn đề:**
  - Biểu đồ doanh thu hàng tháng: Đường MoM màu xanh ngọc trùng tông, trục MoM % bị lệch tâm; các tháng đầu (T9/2016..T1/2017) có doanh thu quá nhỏ (R$ 19 - 252) khiến MoM vọt lên +705.751%, bẹp dí toàn bộ biến động của các tháng thông thường; tồn tại 2 tiêu đề trùng lặp và legend đè nội dung.
  - Biểu đồ tỷ lệ giao trễ theo bang: Chưa có mốc tham chiếu toàn sàn; phân nhóm 2 màu xanh/đỏ nhị phân cứng nhắc dễ gây hiểu lầm tiêu cực khi sự chênh lệch giữa các bang là nhỏ.
- **Quyết định:**
  - Đồng bộ diện mạo về giao diện mặc định Streamlit Dark (`base = "dark"` trong `.streamlit/config.toml`), bỏ CSS tùy biến thừa thãi.
  - **Biểu đồ doanh thu & MoM:**
    - Cột doanh thu giữ màu xanh `#1E88E5`, đường MoM chuyển sang màu đỏ `#E53935` (cả line và marker).
    - Trục phải MoM đối xứng quanh 0: `range = [-m, m]` với $m = \max(|\text{MoM}|)$ làm tròn lên bội của 10 ($m = 120\%$), tick chia đều và thêm đường ngang đứt nét tại 0% bằng `add_hline` trên `yaxis2`.
    - Bỏ điểm MoM của tháng đầu tiên và các tháng có doanh thu kỳ trước $< 5\%$ doanh thu tháng lớn nhất (loại bỏ méo mó nền thấp), kèm chú thích nhỏ: *"MoM bỏ qua các tháng đầu do nền doanh thu thấp"*.
    - Đặt legend dưới đáy biểu đồ (`orientation="h", y=-0.25`), bỏ title trong figure, chỉ giữ một `st.subheader` sinh động sinh từ dữ liệu bằng f-string (nêu tháng đỉnh và tăng trưởng tổng giai đoạn).
    - Trục x định dạng `"T1/2017"`, hover hiển thị dạng `"Tháng 1/2017: R$ 138.488"`.
  - **Biểu đồ tỷ lệ trễ theo bang:**
    - Giữ thang màu liên tục Reds (`[[0, "#FFCDD2"], [0.5, "#EF5350"], [1, "#B71C1C"]]`) vì trực quan hóa sắc thái mức độ trễ tốt hơn phân nhóm xanh/đỏ nhị phân.
    - Thêm đường dọc đứt nét tại tỷ lệ trễ trung bình toàn sàn có trọng số theo số đơn ($\approx 6,6\%$, phản ánh sát thực tế so với trung bình cộng số học $8,8\%$) kèm annotation `"Trung bình: 6,6%"`.
    - Tooltip hiển thị: Tên bang, Tỷ lệ trễ, Số đơn.
    - Lọc bang có $\ge 500$ đơn để đảm bảo ý nghĩa thống kê; khi bộ lọc chỉ còn 1–2 bang, ẩn khung so sánh và hiện `st.info` tránh lỗi logic so sánh.
    - Khung nhận định: Điểm đánh giá (4,30 sao vs 1,94 sao) sinh động từ DataFrame; chuyển khuyến nghị sang giọng gợi ý (*"Có thể cân nhắc..."*) và nêu rõ dữ liệu chưa xác định nguyên nhân trễ.
- **Thực hiện:** Cập nhật `.streamlit/config.toml` và hàm `render_monthly_revenue_chart`, `render_delivery_tab` trong `app/pages/01_dashboard.py`.
- **Kiểm chứng:** Kiểm tra trực quan trên trình duyệt và tự động hóa qua pytest (49/49 non-integration, 34/34 integration pass).
- **Đánh đổi:** Chuỗi đường MoM bắt đầu hiển thị từ T2/2017 nhưng đổi lại biểu đồ không bị kéo giãn cực đoan bởi các điểm dị biệt ban đầu.
- **Bài học:** Biểu đồ kết hợp hai trục cần xử lý ngoại lai của chuỗi % và căn đối xứng trục 0 để bảo đảm tính trung thực của trực quan hóa dữ liệu.

### 3. Sửa thẻ KPI và chuẩn hóa Delta
- **Bối cảnh:** 6 thẻ `st.metric` ở Tab 1 theo dõi Doanh thu, Đơn hàng, Khách hàng, AOV, Đánh giá TB và Tỷ lệ giao đúng hạn.
- **Vấn đề:**
  - Giá trị doanh thu $\ge 1$ triệu bị tràn khung thẻ metric trên giao diện.
  - Chỉ số so sánh Delta với kỳ liền trước bị âm bất thường khi lọc toàn bộ giai đoạn mặc định (2017-01-01 .. 2018-08-31), do chu kỳ đối ứng cùng độ dài rơi vào 2015–2016 (ngoài phạm vi hoạt động chính của Olist).
  - Màu sắc và hướng mũi tên delta bị ngược ở một số chỉ số.
- **Quyết định:**
  - Định dạng số tiền $\ge 1$ triệu dạng rút gọn tiếng Việt `"R$ 15,4 triệu"`, hiển thị số đầy đủ trong tooltip `help`. Điểm đánh giá hiển thị `"4,16"` kèm nhãn `"Đánh giá TB (/5)"`. Bố cục 2 hàng $\times$ 3 cột cân đối.
  - Tạo hàm `check_prev_period_valid`: Delta chỉ hiển thị khi kỳ trước nằm trọn trong khoảng dữ liệu ($\ge 2017\text{-}01\text{-}01$) và có $\ge 100$ đơn hàng; ngược lại hiển thị `"—”` kèm help `"Chưa có kỳ trước để so sánh"`.
  - Delta doanh thu/đơn/khách/AOV theo `%`; đánh giá theo điểm tuyệt đối; đúng hạn theo điểm phần trăm; màu và mũi tên theo đúng dấu dương xanh / âm đỏ (`delta_color="normal"`).
- **Thực hiện:** Cấu hình các hàm định dạng trong `src/ui/labels.py` và tích hợp vào `render_kpi_cards` trong `app/pages/01_dashboard.py`.
- **Kiểm chứng:** 9 unit tests cho định dạng giá trị, delta và điều kiện hợp lệ kỳ trước trong `tests/test_labels.py` đều PASSED.
- **Đánh đổi:** Không hiển thị số delta khi chọn mốc 20 tháng mặc định, nhưng loại bỏ hoàn toàn các con số so sánh gây hiểu nhầm.
- **Bài học:** Không đưa ra dữ liệu so sánh khi kỳ đối ứng không đủ điều kiện tin cậy thống kê; hiển thị trạng thái thiếu dữ liệu rõ ràng tốt hơn hiển thị số liệu sai ngữ cảnh.

### 4. Xuất báo cáo UC04 và trang chủ điều hướng
- **Bối cảnh:** Phân hệ UC04 cho phép trích xuất dữ liệu chi tiết của các đơn hàng và chỉ số KPI theo bộ lọc hiện tại ra file ngoại tuyến (CSV/Excel).
- **Vấn đề:**
  - Khi dữ liệu lớn ($> 50.000$ dòng), xuất toàn bộ có thể gây tràn RAM trình duyệt; phiên bản trước có nguy cơ ẩn nút hoặc gặp lỗi khi vượt ngưỡng.
  - Thiếu trang chủ tổng quan định hướng toàn hệ sinh thái (BI Dashboard, RFM, AI Assistant).
- **Quyết định:**
  - Thêm khu vực xuất báo cáo `render_export_section` ở cuối dashboard: hỗ trợ xuất CSV (`utf-8-sig`) và Excel (`.xlsx` 2 sheet `KPI` và `Don hang`).
  - Đặt giới hạn `MAX_EXPORT_ROWS = 50_000`: khi vượt ngưỡng, hiển thị `st.warning` thông báo và tự động cắt 50.000 dòng đầu, đảm bảo nút tải luôn hiển thị và hoạt động thông suốt.
  - Tên file xuất kèm timestamp: `ecommerce_report_YYYYMMDD_HHMMSS`.
  - Bổ sung `openpyxl>=3.1.0` vào `requirements.txt`.
  - Viết mới `app/main.py`: Trang chủ giới thiệu nền tảng E-Commerce AI Analytics, hiển thị 4 KPI quy mô toàn sàn (99.441 đơn, 96.096 khách hàng, R$ 16,0 triệu doanh thu), giới thiệu 3 phân hệ và nút điều hướng chuyển sang `01_dashboard.py`.
- **Thực hiện:** Cập nhật `app/pages/01_dashboard.py`, viết `app/main.py`, cập nhật `requirements.txt`.
- **Kiểm chứng:** Thử nghiệm xuất file thực tế trên trình duyệt; tải thành công cả CSV và Excel đa sheet; khi vượt 50.000 dòng, cảnh báo hiển thị đúng và dữ liệu được cắt an toàn.
- **Đánh đổi:** Tệp Excel bị giới hạn 50.000 dòng đầu tiên thay vì toàn bộ dữ liệu để bảo vệ bộ nhớ máy chủ.
- **Bài học:** Nguyên tắc thiết kế suy giảm có kiểm soát (Graceful Degradation): khi gặp giới hạn tài nguyên, ưu tiên trả về tập dữ liệu tối đa an toàn kèm thông báo thay vì để phát sinh lỗi ngắt quãng trải nghiệm.

### 5. Quan sát về triển khai và chiến lược nhánh
- **Bối cảnh:** Đối soát giữa môi trường phát triển cục bộ và bản ứng dụng đã triển khai trực tiếp trên Streamlit Cloud.
- **Vấn đề:** Ứng dụng deploy trên Streamlit Cloud đang cấu hình theo dõi nhánh `main`. Do đó, diện mạo live mang phong cách Streamlit Dark cổ điển, trong khi nhánh `develop` trước đó có các can thiệp CSS khác biệt.
- **Quyết định:**
  - Đồng bộ toàn bộ diện mạo của nhánh làm việc (`feature/classic-ui`) về đúng tiêu chuẩn giao diện của bản deploy trên `main` (nền tối mặc định Streamlit, bảng màu gốc, không inject CSS phức tạp), trong khi giữ nguyên toàn bộ logic in-memory pandas mới và tính năng xuất báo cáo.
  - Chưa merge vào `main` vì: đang hoàn thiện kiểm thử toàn diện (unit test, integration test, visual test), chuẩn hóa nhãn tiếng Việt và cần nghiệm thu trước khi mở Pull Request chính thức.
- **Thực hiện & Kiểm chứng:** Ứng dụng chạy mượt mà, sidebar điều hướng hoạt động hoàn hảo, kiểm thử 100% xanh.
- **Bài học:** Việc phân tách rõ ràng giữa nhánh tính năng và nhánh triển khai giúp đảm bảo tính an toàn cho hệ thống live trong khi vẫn duy trì tốc độ phát triển các tính năng mới.

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
* **Tách biệt dữ liệu lõi và lớp hiển thị:** Giữ nguyên mã gốc trong cơ sở dữ liệu làm khóa định danh duy nhất cho các phép tính toán và chỉ định dạng, dịch thuật ở tầng trình bày giao diện (Presentation Layer) để nâng cao trải nghiệm người dùng mà không tạo rủi ro sai lệch dữ liệu.
* **Kiểm soát trực quan hóa dữ liệu hai trục (Dual-axis):** Khi biểu diễn đồng thời chuỗi giá trị tuyệt đối và chuỗi tỷ lệ phần trăm (%), cần kiểm soát các mốc dữ liệu nền cực thấp để tránh méo mó tỷ lệ, đồng thời căn chỉnh đối xứng trục gốc để đảm bảo tính trung thực thị giác.
* **Thiết kế suy giảm có kiểm soát (Graceful Degradation):** Khi dữ liệu vượt ngưỡng tải an toàn hoặc thiếu dữ liệu đối chiếu kỳ trước, ưu tiên hiển thị cảnh báo hướng dẫn và trạng thái trung tính thay vì làm gián đoạn luồng sử dụng hoặc phát sinh lỗi ngoại lệ.
