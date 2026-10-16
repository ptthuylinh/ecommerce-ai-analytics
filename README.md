# 🛍️ AI-Powered E-Commerce Analytics & Conversational Assistant

> Một nền tảng phân tích dữ liệu thương mại điện tử toàn diện: Kết hợp trực quan hóa số liệu trực quan (Interactive BI), mô hình học máy dự báo rủi ro (Predictive ML) và trợ lý tương tác thông minh (Conversational GenAI).

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B.svg)](https://streamlit.io/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-F7931E.svg)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 1. Giới thiệu dự án (Overview & Problem Statement)

Trong kỷ nguyên thương mại điện tử, các báo cáo kinh doanh truyền thống (Excel, PDF tĩnh) bộc lộ nhiều hạn chế:
1. **Chỉ nhìn về quá khứ:** Cho biết doanh thu đã đạt được nhưng không dự báo được rủi ro vận hành sắp tới.
2. **Thiếu tính tương tác:** Ban quản trị hoặc phòng ban nghiệp vụ muốn đào sâu một chỉ số phải đợi đội ngũ kỹ thuật viết truy vấn SQL mất nhiều thời gian.
3. **Trải nghiệm rời rạc:** Thiếu một giao diện trực quan, đồng bộ giữa báo cáo quản trị và công cụ dự báo.

**Giải pháp:** Dự án xây dựng một Web Data Application tích hợp toàn diện theo quy trình **ETL -> EDA -> Predictive Modeling -> Conversational AI**, cho phép theo dõi sức khỏe sàn TMĐT, dự báo nguy cơ đơn hàng trễ hạn và trò chuyện trực tiếp với dữ liệu bằng ngôn ngữ tự nhiên.

---

## ✨ 2. Các tính năng cốt lõi (Key Features)

Dự án được cấu trúc thành 3 phân hệ tương tác chính:

* 📊 **Phân hệ 1: Descriptive Analytics (Báo cáo tổng quan & Thẩm mỹ UI/UX)**
  * Dashboard hiển thị các chỉ số trọng yếu (Revenue, Total Orders, Average Review Score, Delivery SLA).
  * Biểu đồ động đa chiều (Plotly): Bản đồ mật độ đơn hàng theo vùng miền, xu hướng doanh thu theo mùa vụ, cơ cấu sản phẩm bán chạy.
  * Bộ lọc dữ liệu thời gian thực (Real-time Filtering) theo khoảng thời gian, trạng thái và khu vực.

* 🔮 **Phân hệ 2: Predictive Analytics (AI Dự báo rủi ro đơn hàng)**
  * Tích hợp mô hình học máy (`XGBoost` / `Random Forest`) đã được tối ưu hóa.
  * Nhận tham số đơn hàng mới (quãng đường, cước phí, loại hàng) và dự báo:
    * Xác suất đơn hàng bị giao trễ so với hạn dự kiến (Delivery Delay Risk).
    * Dự báo mức độ hài lòng của khách hàng (Review Score Estimation).

* 💬 **Phân hệ 3: Conversational AI (Trợ lý trò chuyện với dữ liệu)**
  * Tích hợp API mô hình ngôn ngữ lớn (LLM - Google Gemini / OpenAI).
  * Tính năng **Text-to-Insight**: Người dùng nhập câu hỏi tự nhiên bằng tiếng Việt (Ví dụ: *"Top 3 danh mục có tỷ lệ đánh giá 1 sao cao nhất là gì?"*).
  * Hệ thống tự động phân tích ngữ cảnh, truy vấn số liệu và giải thích ngắn gọn kèm đề xuất hành động.

---

## 🛠️ 3. Công nghệ sử dụng (Tech Stack)

| Lĩnh vực | Công nghệ | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Ngôn ngữ** | `Python 3.10+`, `SQL` | Xử lý dữ liệu và xây dựng logic ứng dụng |
| **Lưu trữ dữ liệu** | `SQLite` / `PostgreSQL` | Quản lý cơ sở dữ liệu quan hệ (Relational DB) |
| **Xử lý số liệu** | `Pandas`, `NumPy` | Làm sạch, chuẩn hóa và biến đổi dữ liệu (ETL/Data Wrangling) |
| **Mô hình học máy** | `Scikit-learn`, `XGBoost` | Huấn luyện mô hình phân loại và dự đoán rủi ro |
| **Trực quan hóa (BI)** | `Plotly Express`, `Altair` | Thiết kế các biểu đồ vector tương tác động |
| **Frontend & UI App** | `Streamlit`, Custom CSS | Xây dựng giao diện Web theo chuẩn Design System tối giản |
| **Trí tuệ nhân tạo (LLM)**| `Google Gemini API` / `OpenAI` | Xử lý ngôn ngữ tự nhiên và phân tích thông minh |
| **Quản lý phiên bản** | `Git`, `GitHub` | Quản lý mã nguồn theo mô hình Gitflow (`main`, `develop`, `features`) |

---

## 📐 4. Cấu trúc thư mục (Project Architecture)

Dự án áp dụng kiến trúc Module hóa tách biệt giữa Tầng dữ liệu, Nghiệp vụ lõi và Giao diện:

```text
ecommerce-ai-analytics/
├── .streamlit/               # Cấu hình Theme & Secrets bảo mật
├── data/                     # Quản lý vòng đời dữ liệu (raw, processed, sqlite db)
├── notebooks/                # Nghiên cứu, làm sạch & thử nghiệm mô hình
├── src/                      # Source code lõi (db, ml, ai service, helpers)
├── models/                   # Lưu trữ mô hình AI (.pkl)
├── app/                      # Mã nguồn giao diện Web App (Multi-page)
│   ├── main.py               # Trang chủ
│   └── pages/                # Các trang chức năng (Dashboard, AI, Chatbot)
├── assets/                   # Tài nguyên CSS và hình ảnh giao diện
├── docs/                     # Đặc tả Use Cases, Functional & Non-Functional
├── requirements.txt          # Danh sách thư viện phụ thuộc
└── README.md
```

---

## 🚀 5. Hướng dẫn cài đặt & Chạy ứng dụng (Getting Started)

### Yêu cầu tiên quyết
* Đã cài đặt **Python 3.10+** và **Git** trên máy.

### Các bước thực hiện:

1. **Clone repository về máy:**
   ```bash
   git clone https://github.com/[your-username]/ecommerce-ai-analytics.git
   cd ecommerce-ai-analytics
   ```

2. **Tạo và kích hoạt môi trường ảo:**
   * *Trên Windows (PowerShell):*
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   * *Trên macOS/Linux:*
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Cài đặt các thư viện phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Cấu hình biến môi trường (API Key):**
   * Sao chép file `.env.example` thành `.env`:
     ```bash
     cp .env.example .env
     ```
   * Điền mã khóa API của bạn vào file `.env` (ví dụ: `GEMINI_API_KEY=your_key_here`).

5. **Khởi chạy ứng dụng Web:**
   ```bash
   streamlit run app/main.py
   ```
   Ứng dụng sẽ tự động mở trên trình duyệt tại địa chỉ: `http://localhost:8501`.
