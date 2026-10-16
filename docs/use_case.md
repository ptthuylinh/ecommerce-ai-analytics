# 📋 System Specifications: Use Cases, F & NF Requirements

Tài liệu đặc tả các yêu cầu nghiệp vụ và kỹ thuật cho dự án **E-Commerce Smart Analytics & Conversational AI Assistant**.

---

## 1. Actors (Tác nhân hệ thống)
* **Business Manager (Nhà quản trị kinh doanh):** Theo dõi tổng quan hiệu suất, doanh thu và xu hướng thị trường.
* **Operations/CSKH Specialist (Chuyên viên vận hành):** Giám sát các đơn hàng có rủi ro trễ hạn để kịp thời can thiệp.

---

## 2. Use Cases (UC)

| Mã UC | Tên Use Case | Mô tả chi tiết | Tác nhân chính |
| :--- | :--- | :--- | :--- |
| **UC01** | Khám phá dữ liệu (Explore Dashboard) | Xem biểu đồ doanh số, đơn hàng, bản đồ khu vực; lọc theo ngày tháng và danh mục. | Manager, Operations |
| **UC02** | Dự báo rủi ro đơn hàng (Predict Risk) | Nhập thông tin đơn hàng mới để mô hình AI dự đoán nguy cơ trễ hạn và điểm đánh giá. | Operations |
| **UC03** | Trò chuyện với dữ liệu (Ask AI Assistant) | Đặt câu hỏi bằng ngôn ngữ tự nhiên để AI tự phân tích và trả về câu trả lời kèm biểu đồ. | Manager, Operations |
| **UC04** | Xuất báo cáo (Export Report) | Tải dữ liệu sau khi lọc hoặc biểu đồ phân tích về máy tính. | Manager |

---

## 3. Functional Requirements (F - Yêu cầu chức năng)
* **F01 - Data Ingestion:** Hệ thống kết nối và đọc dữ liệu từ cơ sở dữ liệu SQLite đã được chuẩn hóa.
* **F02 - Dynamic Filtering:** Cho phép lọc đồng thời theo nhiều chiều (Khoảng thời gian, Bang/Khu vực, Trạng thái đơn).
* **F03 - ML Inference:** Nhận dữ liệu đầu vào từ form, gọi mô hình Machine Learning (.pkl) và trả về xác suất rủi ro trong thời gian thực.
* **F04 - Natural Language Query:** Nhận câu hỏi tiếng Việt từ khung chat, gọi API LLM xử lý và trả về phản hồi súc tích.

---

## 4. Non-Functional Requirements (NF - Yêu cầu phi chức năng)
* **NF01 - Usability & Aesthetics:** Giao diện nhất quán theo bảng màu hiện đại, bo góc mềm mại, hiển thị tối ưu trên màn hình máy tính phổ thông.
* **NF02 - Performance:** Thời gian tải dữ liệu lần đầu dưới 3 giây (sử dụng cache); phản hồi dự đoán AI dưới 0.5 giây; phản hồi chatbot dưới 5 giây.
* **NF03 - Security:** Toàn bộ API Key và thông tin bảo mật được lưu trong biến môi trường `.env`, tuyệt đối không lưu vết trên GitHub.
* **NF04 - Model Quality:** Mô hình AI dự đoán đạt độ chính xác (Accuracy / F1-score) tối thiểu 75% trên tập dữ liệu kiểm thử.