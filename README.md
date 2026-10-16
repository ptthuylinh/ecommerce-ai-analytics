# 🛍️ AI-Powered E-Commerce Analytics & Conversational Agent

> Nền tảng phân tích dữ liệu thương mại điện tử hiện đại: Kết hợp trực quan hóa số liệu trực quan (Interactive BI), mô hình học máy dự báo rủi ro (Predictive ML), tác tử thông minh (AI Agent / Text-to-SQL) và quy trình tự động hóa kiểm thử liên tục (CI/CD).

[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](https://github.com/pttlinh32/ecommerce-ai-analytics)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B.svg)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-AI%20Agent-green.svg)](https://www.langchain.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-F7931E.svg)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 1. Bài toán & Mục tiêu dự án (Problem Statement)

Trong các doanh nghiệp bán lẻ và thương mại điện tử, các báo cáo quản trị truyền thống (Excel / BI tĩnh) thường gặp các điểm nghẽn:
1. **Báo cáo nhìn về quá khứ:** Chỉ phản ánh số liệu đã phát sinh, không có khả năng cảnh báo sớm các rủi ro vận hành (đơn hàng bị giao trễ, khiếu nại khách hàng).
2. **Quy trình truy xuất dữ liệu thủ công:** Mỗi khi các bộ phận nghiệp vụ (Kinh doanh, CSKH, Vận hành) muốn đào sâu một chỉ số chuyên biệt, họ phải phụ thuộc vào chuyên viên dữ liệu để viết câu lệnh SQL.
3. **Thiếu tính liền mạch:** Công cụ phân tích, mô hình dự đoán và giao diện tương tác thường bị phân mảnh thành nhiều hệ thống riêng biệt.

**Mục tiêu của dự án:** Xây dựng một **Web Data Application** toàn diện theo kiến trúc module hóa:
$$\text{Relational DB (SQL)} \longrightarrow \text{Interactive BI (Streamlit)} \longrightarrow \text{Predictive AI (XGBoost)} \longrightarrow \text{AI Agent (Text-to-SQL)}$$
Hệ thống được vận hành tự động thông qua quy trình **CI/CD** với GitHub Actions.

---

## ✨ 2. Các tính năng cốt lõi (Key Features)

Ứng dụng được chia thành 3 phân hệ tương tác chính:

### 📊 Phân hệ 1: Descriptive Analytics (Báo cáo kinh doanh & UI/UX hiện đại)
* **KPI Metrics:** Theo dõi doanh thu thực tế, số lượng đơn đặt hàng, tỷ lệ giao trễ và điểm đánh giá hài lòng trung bình (Review Score).
* **Trực quan hóa đa chiều (Plotly):** Phân tích xu hướng doanh thu theo mùa vụ, cơ cấu sản phẩm bán chạy và bản đồ phân bố địa lý đơn hàng.
* **Bộ lọc động (Dynamic Filtering):** Cho phép lọc dữ liệu theo khoảng thời gian, trạng thái đơn hàng và bang/khu vực.

### 🔮 Phân hệ 2: Predictive Analytics (AI Dự báo rủi ro vận hành)
* Huấn luyện mô hình học máy (`Scikit-learn` / `XGBoost`) trên dữ liệu vận chuyển và hành vi khách hàng.
* Dự báo các chỉ số rủi ro cho từng đơn hàng mới:
  * **Xác suất trễ hạn (Delivery Delay Risk):** Dự đoán đơn hàng có khả năng trễ hẹn so với hạn cam kết hay không.
  * **Dự báo mức độ đánh giá (Review Score Prediction):** Cảnh báo sớm các đơn hàng có nguy cơ bị đánh giá 1-2 sao để bộ phận CSKH can thiệp kịp thời.

### 🤖 Phân hệ 3: AI Agent & Conversational Analytics (Tác tử dữ liệu thông minh)
* Thay vì chỉ trả lời văn bản tĩnh, hệ thống ứng dụng mô hình **AI Agent (Tool Calling / LangChain)**:
  * Tự động chuyển đổi câu hỏi tự nhiên bằng tiếng Việt thành câu lệnh SQL (`Text-to-SQL`).
  * Thực thi truy vấn trực tiếp vào cơ sở dữ liệu `SQLite`.
  * Tự động gọi công cụ sinh mã biểu đồ Plotly và phân tích giải thích kết quả cho người dùng.

---

## 🛠️ 3. Công nghệ sử dụng (Tech Stack)

| Lĩnh vực | Công nghệ | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Ngôn ngữ** | `Python 3.10+`, `SQL` | Xử lý dữ liệu và xây dựng logic ứng dụng |
| **Lưu trữ dữ liệu** | `SQLite` / `PostgreSQL` | Quản lý cơ sở dữ liệu quan hệ (Relational DB) |
| **Xử lý số liệu** | `Pandas`, `NumPy` | Làm sạch, chuẩn hóa và biến đổi dữ liệu (ETL / Data Wrangling) |
| **Mô hình học máy** | `Scikit-learn`, `XGBoost` | Huấn luyện mô hình phân loại và dự đoán rủi ro đơn hàng |
| **Trực quan hóa (BI)** | `Plotly Express`, `Altair` | Thiết kế các biểu đồ vector tương tác động |
| **Frontend & UI App** | `Streamlit`, Custom CSS | Xây dựng giao diện Web theo chuẩn Design System tối giản |
| **Tác tử AI (AI Agent)** | `LangChain`, `Gemini / OpenAI API` | Xây dựng Agent tự động lập luận, gọi tool truy vấn SQL và phân tích dữ liệu |
| **Tự động hóa (CI/CD)** | `GitHub Actions` | Tự động kiểm thử mã nguồn (`pytest`, `linting`) và hỗ trợ triển khai liên tục |
| **Quản lý phiên bản** | `Git`, `GitHub` | Quản lý mã nguồn theo mô hình Gitflow (`main`, `develop`, `features`) |

---

## 📐 4. Cấu trúc thư mục dự án (Project Architecture)

```text
ecommerce-ai-analytics/
├── .github/
│   └── workflows/
│       └── ci.yml            # Pipeline CI/CD tự động test và kiểm tra code
├── .streamlit/               # Cấu hình Theme & Secrets bảo mật của Streamlit
├── data/                     # Quản lý vòng đời dữ liệu
│   ├── raw/                  # Dữ liệu gốc Olist CSVs (Bất biến)
│   ├── processed/            # Dữ liệu sạch sau chuẩn hóa
│   └── ecommerce.db          # Cơ sở dữ liệu SQLite
├── notebooks/                # Jupyter Notebooks phục vụ EDA và thử nghiệm mô hình
│   ├── 01_eda_data_cleaning.ipynb
│   └── 02_ml_experiment.ipynb
├── src/                      # Source code lõi (Module hóa)
│   ├── db.py                 # Hàm kết nối và truy vấn SQL
│   ├── ml/                   # Module huấn luyện & suy luận Machine Learning
│   ├── ai/                   # Module AI Agent & Prompt Engineering
│   └── utils/                # Các hàm phụ trợ (Formatting, helper functions)
├── models/                   # Lưu trữ mô hình AI đã đóng gói (.pkl)
├── app/                      # Mã nguồn giao diện Web App (Multi-page Streamlit)
│   ├── main.py               # Trang chủ điều hướng
│   └── pages/                # Các trang chức năng (Dashboard, ML, AI Agent)
├── assets/                   # Tài nguyên CSS và hình ảnh giao diện
├── docs/                     # Đặc tả Use Cases, Functional & Non-Functional
├── requirements.txt          # Danh sách thư viện phụ thuộc
└── README.md
```

---

## 🚀 5. Hướng dẫn cài đặt & Chạy ứng dụng (Getting Started)

### Yêu cầu hệ thống
* Đã cài đặt **Python 3.10+** và **Git**.

### Các bước thực hiện:

1. **Clone repository về máy:**
   ```bash
   git clone https://github.com/pttlinh32/ecommerce-ai-analytics.git
   cd ecommerce-ai-analytics
   ```

2. **Khởi tạo và kích hoạt môi trường ảo:**
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

3. **Cài đặt các thư viện cần thiết:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Cấu hình biến môi trường (API Key):**
   * Tạo file `.env` từ file mẫu `.env.example`:
     ```bash
     cp .env.example .env
     ```
   * Điền API Key của bạn vào file `.env` (ví dụ: `GEMINI_API_KEY=your_key_here`).

5. **Khởi chạy ứng dụng Web:**
   ```bash
   streamlit run app/main.py
   ```
   Trình duyệt sẽ tự động mở ứng dụng tại địa chỉ: `http://localhost:8501`.

---

## 🔄 6. Quy trình Tự động hóa & CI/CD Pipeline

Dự án áp dụng quy trình kiểm thử tự động với **GitHub Actions**:
* **Continuous Integration (CI):** Khi có bất kỳ Pull Request hoặc Commit nào đẩy lên nhánh `develop` hoặc `main`, hệ thống sẽ:
  * Kiểm tra cú pháp và định dạng code với `flake8` / `black`.
  * Chạy các bài kiểm thử đơn vị (`pytest`) trên các module xử lý dữ liệu và truy vấn SQL.
* **Continuous Deployment (CD):** Tự động đồng bộ và cập nhật phiên bản mới nhất lên nền tảng **Streamlit Community Cloud**.
