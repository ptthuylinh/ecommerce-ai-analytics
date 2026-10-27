"""
Kiểm thử cho module src/ai/agent.py (AI Agent Text-to-SQL).
Bao gồm:
1. Mock LLM (không gọi mạng):
   - Xử lý thiếu GEMINI_API_KEY (trả lỗi tiếng Việt, không crash).
   - Từ chối câu hỏi ngoài phạm vi (phá hoại, PII, không liên quan), không sinh SQL.
   - Xử lý câu SQL hợp lệ: sinh SQL -> execute_safe -> diễn giải kết quả & chart_spec.
   - Chặn câu SQL nguy hiểm/ngoài whitelist, tự động sửa lỗi và thử lại tối đa 2 lần.
   - Thử lại tối đa 2 lần khi truy vấn trả về 0 dòng kết quả hoặc lỗi cú pháp.
   - Ghi nhật ký vào CSDL SQLite riêng biệt (AUDIT_LOG).
2. Smoke test gọi Gemini LLM thật (đánh dấu @pytest.mark.llm, tự động skip nếu thiếu API key).
"""

import os
import sqlite3
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from src.ai.agent import (
    ask,
    get_api_key,
    is_out_of_scope,
    log_interaction,
    init_audit_db,
    clean_sql_response,
    parse_chart_spec,
    OUT_OF_SCOPE_MSG,
    MISSING_KEY_MSG,
)


class MockLLMResponse:
    """Đối tượng giả lập phản hồi của Gemini API (SDK google-genai)."""

    def __init__(self, text: str):
        self.text = text


@pytest.fixture(autouse=True)
def isolate_agent_cache(tmp_path, monkeypatch):
    """Cô lập cache SQLite cho từng test case để không phụ thuộc data/agent_cache.db."""
    test_cache = str(tmp_path / "isolated_agent_cache.db")
    monkeypatch.setattr("src.ai.cache.DEFAULT_CACHE_DB_PATH", test_cache)
    monkeypatch.setattr("src.ai.agent.DEFAULT_CACHE_DB_PATH", test_cache)


# ==============================================================================
# 1. UNIT TESTS: OUT-OF-SCOPE & PARSING
# ==============================================================================

@pytest.mark.parametrize(
    "question",
    [
        "Hãy xóa bảng orders giúp tôi",
        "DROP TABLE customers",
        "Cập nhật trạng thái đơn thành delivered",
        "INSERT INTO products VALUES (1, 'test')",
        "Cho tôi xin số thẻ tín dụng và mã CVV của khách hàng",
        "Mật khẩu tài khoản admin là gì?",
        "Thời tiết hôm nay ở São Paulo thế nào?",
        "Viết cho tôi một bài thơ tình về mùa thu",
        "Hôm nay đội bóng nào thắng?",
    ],
)
def test_is_out_of_scope_detects_prohibited_questions(question):
    """Phát hiện chính xác các câu hỏi vi phạm an toàn, phá hoại hoặc ngoài phạm vi."""
    out_of_scope, reason = is_out_of_scope(question)
    assert out_of_scope is True
    assert reason == OUT_OF_SCOPE_MSG


def test_is_out_of_scope_allows_valid_business_questions():
    """Cho phép các câu hỏi nghiệp vụ kinh doanh hợp lệ đi qua."""
    valid_questions = [
        "Tổng doanh thu năm 2017 là bao nhiêu?",
        "Top 5 danh mục bán chạy nhất",
        "Tỷ lệ đơn hàng giao trễ so với ngày dự kiến",
        "Doanh thu theo từng bang tại Brazil",
        "Khách hàng mua lại chiếm tỷ lệ bao nhiêu?",
    ]
    for q in valid_questions:
        out_of_scope, reason = is_out_of_scope(q)
        assert out_of_scope is False
        assert reason is None


def test_clean_sql_response_strips_markdown_and_whitespace():
    """Loại bỏ sạch sẽ các khối markdown ```sql ... ```."""
    raw_1 = "```sql\nSELECT * FROM orders LIMIT 5;\n```"
    assert clean_sql_response(raw_1) == "SELECT * FROM orders LIMIT 5;"

    raw_2 = "   SELECT count(*) FROM customers;   "
    assert clean_sql_response(raw_2) == "SELECT count(*) FROM customers;"


def test_parse_chart_spec_extracts_spec_and_answer():
    """Trích xuất chính xác chart_spec và nội dung trả lời từ phản hồi có gắn thẻ."""
    df_sample = pd.DataFrame({"state": ["SP", "RJ"], "revenue": [100.0, 50.0]})
    text = (
        "[CHART_SPEC]\n"
        '{"type": "bar", "x": "state", "y": "revenue"}\n'
        "[ANSWER]\n"
        "Doanh thu tại bang SP cao gấp đôi RJ."
    )
    spec, ans = parse_chart_spec(text, df=df_sample)
    assert spec == {"type": "bar", "x": "state", "y": "revenue"}
    assert ans == "Doanh thu tại bang SP cao gấp đôi RJ."


def test_parse_chart_spec_handles_null_or_invalid_column():
    """Nếu chart_spec là null hoặc tên cột không khớp với df thì trả về None."""
    df_sample = pd.DataFrame({"col_a": [1, 2]})
    text_null = "[CHART_SPEC]\nnull\n[ANSWER]\nChỉ có một số KPI."
    spec, ans = parse_chart_spec(text_null, df=df_sample)
    assert spec is None
    assert ans == "Chỉ có một số KPI."

    text_invalid_col = (
        "[CHART_SPEC]\n"
        '{"type": "bar", "x": "non_existing", "y": "col_a"}\n'
        "[ANSWER]\n"
        "Nội dung..."
    )
    spec, _ = parse_chart_spec(text_invalid_col, df=df_sample)
    assert spec is None


# ==============================================================================
# 2. UNIT TESTS: MOCK LLM ASK()
# ==============================================================================

def test_ask_missing_api_key_returns_clear_error(tmp_path):
    """Khi thiếu GEMINI_API_KEY, hàm ask trả thông điệp tiếng Việt rõ ràng, không crash."""
    audit_db = str(tmp_path / "test_audit.db")

    with patch("src.ai.agent.get_api_key", return_value=None):
        res = ask(
            question="Top 10 danh mục bán chạy",
            client=None,
            audit_db_path=audit_db,
        )

    assert res["sql"] is None
    assert res["df"] is None
    assert res["error"] == "MISSING_API_KEY"
    assert res["attempts"] == 0
    assert "Chưa cấu hình GEMINI_API_KEY" in res["answer"]
    assert res["latency_s"] >= 0


def test_ask_out_of_scope_question_refuses_politely_without_calling_llm(tmp_path):
    """Câu hỏi ngoài phạm vi bị chặn ngay lập tức, không gọi LLM, attempts=0."""
    audit_db = str(tmp_path / "test_audit.db")
    mock_client = MagicMock()

    res = ask(
        question="Hãy DROP TABLE orders",
        client=mock_client,
        audit_db_path=audit_db,
    )

    assert res["sql"] is None
    assert res["df"] is None
    assert res["attempts"] == 0
    assert "Xin lỗi" in res["answer"]
    # Không được gọi API của LLM
    mock_client.models.generate_content.assert_not_called()


def test_ask_llm_reports_out_of_scope_keyword(tmp_path):
    """Nếu LLM phân loại câu hỏi là OUT_OF_SCOPE thì trả về từ chối lịch sự."""
    audit_db = str(tmp_path / "test_audit.db")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = MockLLMResponse("OUT_OF_SCOPE")

    res = ask(
        question="Bạn có thể giúp tôi việc này không?",
        client=mock_client,
        audit_db_path=audit_db,
    )

    assert res["sql"] is None
    assert res["df"] is None
    assert "Xin lỗi" in res["answer"]


def test_ask_valid_sql_executes_and_interprets_successfully(tmp_path):
    """LLM sinh SQL hợp lệ, execute_safe chạy thành công và diễn giải phức tạp (> 2 cột) qua LLM kèm chart_spec."""
    audit_db = str(tmp_path / "test_audit.db")
    mock_client = MagicMock()

    valid_sql = (
        "SELECT customer_city, customer_state, COUNT(DISTINCT customer_id) AS total_customers "
        "FROM customers GROUP BY customer_city, customer_state ORDER BY total_customers DESC LIMIT 5;"
    )
    interpret_text = (
        "[CHART_SPEC]\n"
        '{"type": "bar", "x": "customer_state", "y": "total_customers"}\n'
        "[ANSWER]\n"
        "Top 5 bang có số lượng khách hàng lớn nhất dẫn đầu là São Paulo (SP) trong khoảng thời gian từ 2017-01-01 đến 2018-08-31."
    )

    mock_client.models.generate_content.side_effect = [
        MockLLMResponse(f"```sql\n{valid_sql}\n```"),  # Bước 1: Sinh SQL
        MockLLMResponse(interpret_text),                # Bước 2: Diễn giải (gọi LLM vì > 2 cột)
    ]

    res = ask(
        question="Top 5 thành phố và bang có nhiều khách hàng nhất?",
        client=mock_client,
        audit_db_path=audit_db,
    )

    assert res["error"] is None
    assert res["sql"] == valid_sql
    assert res["df"] is not None
    assert len(res["df"]) == 5
    assert res["attempts"] == 1
    assert res["chart_spec"] == {"type": "bar", "x": "customer_state", "y": "total_customers"}
    assert "São Paulo (SP)" in res["answer"]
    assert res["latency_s"] >= 0


def test_ask_simple_result_uses_template_interpret_and_avoids_llm_step2(tmp_path):
    """Khi kết quả <= 2 cột, ask() dùng template_interpret và không gọi LLM lần 2."""
    audit_db = str(tmp_path / "test_audit.db")
    mock_client = MagicMock()
    valid_sql = (
        "SELECT customer_state, COUNT(DISTINCT customer_id) AS total_customers "
        "FROM customers GROUP BY customer_state ORDER BY total_customers DESC LIMIT 3;"
    )

    mock_client.models.generate_content.side_effect = [
        MockLLMResponse(f"```sql\n{valid_sql}\n```"),  # Chỉ cần 1 mock vì bước 2 dùng template
    ]

    res = ask(
        question="Số khách hàng theo bang",
        client=mock_client,
        audit_db_path=audit_db,
    )

    assert res["error"] is None
    assert res["sql"] == valid_sql
    assert res["llm_calls"] == 1  # Chỉ 1 lần gọi LLM sinh SQL
    assert "Tìm thấy **3 bản ghi**" in res["answer"]
    assert mock_client.models.generate_content.call_count == 1


def test_ask_blocked_sql_is_rejected_and_retries_successfully(tmp_path):
    """Lần 1 sinh SQL cấm (DROP/bảng ngoài whitelist) bị chặn -> Thử lại lần 2 sinh SQL hợp lệ (>2 cột gọi diễn giải)."""
    audit_db = str(tmp_path / "test_audit.db")
    mock_client = MagicMock()

    bad_sql = "SELECT * FROM users;"  # Bảng ngoài whitelist
    good_sql = "SELECT order_id, customer_id, order_status FROM orders LIMIT 3;"
    interpret_text = (
        "[CHART_SPEC]\nnull\n[ANSWER]\n"
        "Đã tìm thấy 3 đơn hàng hợp lệ trong hệ thống."
    )

    mock_client.models.generate_content.side_effect = [
        MockLLMResponse(bad_sql),        # Lần thử 1 (fail)
        MockLLMResponse(good_sql),       # Lần thử 2 (sửa thành công)
        MockLLMResponse(interpret_text), # Diễn giải (gọi LLM vì > 2 cột)
    ]

    res = ask(
        question="Lấy thông tin đơn hàng",
        client=mock_client,
        audit_db_path=audit_db,
    )

    assert res["error"] is None
    assert res["sql"] == good_sql
    assert res["df"] is not None
    assert len(res["df"]) == 3
    assert res["attempts"] == 2
    assert "3 đơn hàng" in res["answer"]


def test_ask_retries_up_to_max_retries_on_continuous_errors(tmp_path):
    """Thử lại tối đa 2 lần (tổng 3 lần) khi các câu SQL liên tục gặp lỗi cú pháp."""
    audit_db = str(tmp_path / "test_audit.db")
    mock_client = MagicMock()

    # Cả 3 lần đều sinh SQL sai cú pháp
    mock_client.models.generate_content.side_effect = [
        MockLLMResponse("SELECT * FORM orders"),  # Cú pháp sai 'FORM'
        MockLLMResponse("SELECT * FROM invalid_table"),  # Bảng cấm
        MockLLMResponse("SELECT WHERE 1=1"),  # Cú pháp sai
    ]

    res = ask(
        question="Lấy báo cáo tổng hợp",
        client=mock_client,
        audit_db_path=audit_db,
    )

    assert res["df"] is None
    assert res["attempts"] == 3
    assert res["error"] is not None
    assert "Không thể lấy được dữ liệu sau 3 lần thử" in res["answer"]


def test_ask_empty_result_triggers_retry(tmp_path):
    """Nếu câu SQL ban đầu trả về 0 dòng, LLM nhận feedback và sửa đổi điều kiện lọc."""
    audit_db = str(tmp_path / "test_audit.db")
    mock_client = MagicMock()

    empty_sql = "SELECT * FROM orders WHERE order_purchase_timestamp > '2099-01-01' LIMIT 5;"
    valid_sql = "SELECT * FROM orders LIMIT 2;"
    interpret_text = "[CHART_SPEC]\nnull\n[ANSWER]\nTìm thấy 2 đơn hàng."

    mock_client.models.generate_content.side_effect = [
        MockLLMResponse(empty_sql),      # Lần 1: 0 dòng
        MockLLMResponse(valid_sql),      # Lần 2: sửa lại -> có dòng
        MockLLMResponse(interpret_text), # Diễn giải
    ]

    res = ask(
        question="Kiểm tra đơn hàng",
        client=mock_client,
        audit_db_path=audit_db,
    )

    assert res["sql"] == valid_sql
    assert res["df"] is not None
    assert len(res["df"]) == 2
    assert res["attempts"] == 2


# ==============================================================================
# 3. UNIT TESTS: AUDIT LOG RIÊNG BIỆT (data/audit_log.db)
# ==============================================================================

def test_audit_log_records_interaction_in_separate_sqlite_file(tmp_path):
    """Kiểm tra ghi log tương tác đầy đủ vào file SQLite audit_log.db riêng."""
    audit_db = str(tmp_path / "custom_audit.db")

    log_interaction(
        question="Doanh thu theo bang",
        sql="SELECT customer_state, SUM(payment_value) FROM ...",
        status="success",
        row_count=27,
        attempts=1,
        latency_s=0.456,
        error=None,
        db_path=audit_db,
    )

    assert os.path.exists(audit_db)

    with sqlite3.connect(audit_db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT question, sql, status, row_count, attempts, latency_s, error FROM AUDIT_LOG;")
        rows = cur.fetchall()

    assert len(rows) == 1
    q, sql, status, r_cnt, att, lat, err = rows[0]
    assert q == "Doanh thu theo bang"
    assert "SELECT" in sql
    assert status == "success"
    assert r_cnt == 27
    assert att == 1
    assert lat == 0.456
    assert err is None


def test_ask_automatically_persists_audit_log(tmp_path):
    """Khi gọi ask(), tương tác tự động được lưu vào AUDIT_LOG."""
    audit_db = str(tmp_path / "auto_audit.db")
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        MockLLMResponse("SELECT 1 AS test;"),
        MockLLMResponse("[CHART_SPEC]\nnull\n[ANSWER]\nKết quả là 1."),
    ]

    ask(
        question="Thử nghiệm audit",
        client=mock_client,
        audit_db_path=audit_db,
    )

    with sqlite3.connect(audit_db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT question, status, attempts FROM AUDIT_LOG WHERE question='Thử nghiệm audit';")
        rows = cur.fetchall()

    assert len(rows) == 1
    assert rows[0][0] == "Thử nghiệm audit"
    assert rows[0][1] == "success"
    assert rows[0][2] == 1


# ==============================================================================
# 4. UNIT TESTS: CACHE, SAMPLE QUESTIONS, QUOTA & TEMPLATE INTERPRETATION
# ==============================================================================

def test_cache_hit_does_not_call_llm(tmp_path):
    """Khi Cache Hit, SQL được lấy từ cache và chạy lại, hoàn toàn không gọi LLM."""
    cache_db = str(tmp_path / "test_cache.db")
    audit_db = str(tmp_path / "test_audit.db")

    from src.ai.cache import set_cached_sql

    question = "Top 5 sản phẩm bán chạy nhất"
    sql = "SELECT product_id FROM products LIMIT 5;"
    set_cached_sql(question, sql, db_path=cache_db)

    mock_client = MagicMock()

    res = ask(
        question=question,
        client=mock_client,
        cache_db_path=cache_db,
        audit_db_path=audit_db,
    )

    assert res["cached"] is True
    assert res["sql"] == sql
    assert res["df"] is not None
    assert len(res["df"]) == 5
    assert res["llm_calls"] == 0
    # Đảm bảo LLM hoàn toàn không bị gọi
    mock_client.models.generate_content.assert_not_called()


def test_ask_sample_executes_directly_without_llm(tmp_path):
    """ask_sample(index) chạy trực tiếp câu SQL đã kiểm chứng, 0 lượt gọi LLM."""
    audit_db = str(tmp_path / "test_sample_audit.db")

    from src.ai.agent import ask_sample, SAMPLE_QUESTIONS

    assert len(SAMPLE_QUESTIONS) >= 10
    res = ask_sample(0, audit_db_path=audit_db)

    assert res["from_sample"] is True
    assert res["error"] is None
    assert res["sql"] is not None
    assert res["df"] is not None
    assert len(res["df"]) > 0
    assert res["llm_calls"] == 0
    assert res["attempts"] == 0


def test_ask_sample_invalid_index():
    """ask_sample với chỉ số vượt quá phạm vi trả về thông báo lỗi thân thiện."""
    from src.ai.agent import ask_sample

    res = ask_sample(999)
    assert res["error"] == "INVALID_SAMPLE_INDEX"
    assert res["sql"] is None


def test_daily_llm_limit_exhausted_returns_quota_exhausted(tmp_path):
    """Khi hạn mức lượt gọi trong ngày đạt giới hạn, trả về QUOTA_EXHAUSTED mà không gọi LLM."""
    audit_db = str(tmp_path / "exhausted_audit.db")
    mock_client = MagicMock()

    with patch("src.ai.agent.get_quota_status", return_value={"used": 18, "limit": 18, "remaining": 0, "is_exhausted": True}):
        res = ask(
            question="Tổng doanh thu năm 2017",
            client=mock_client,
            audit_db_path=audit_db,
            use_cache=False,
        )

    assert res["error"] == "QUOTA_EXHAUSTED"
    assert res["sql"] is None
    assert res["df"] is None
    assert "Đã đạt hạn mức truy vấn AI trong ngày" in res["answer"]
    mock_client.models.generate_content.assert_not_called()


def test_429_error_handled_returns_quota_exhausted_no_crash(tmp_path):
    """Khi LLM ném lỗi 429 RESOURCE_EXHAUSTED, hệ thống bắt lại và trả về QUOTA_EXHAUSTED không crash."""
    audit_db = str(tmp_path / "rate_limit_audit.db")
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: quota exceeded on free tier")

    res = ask(
        question="Số lượng khách hàng tại São Paulo",
        client=mock_client,
        audit_db_path=audit_db,
        use_cache=False,
    )

    assert res["error"] == "QUOTA_EXHAUSTED"
    assert "Đã đạt hạn mức truy vấn AI trong ngày" in res["answer"]
    assert res["sql"] is None


def test_template_interpret_formats_numbers_correctly():
    """Hàm template_interpret định dạng số liệu chính xác từ DataFrame."""
    from src.ai.agent import template_interpret

    # Test 1 dòng, 1 cột
    df_single = pd.DataFrame({"total_revenue": [15422461.77]})
    spec_1, ans_1 = template_interpret("Tổng doanh thu là bao nhiêu?", df_single)
    assert spec_1 is None
    assert "15,422,461.77" in ans_1

    # Test 2 cột (suy luận chart_spec dạng bar)
    df_two_cols = pd.DataFrame({
        "customer_state": ["SP", "RJ", "MG"],
        "orders": [40000, 12000, 11000]
    })
    spec_2, ans_2 = template_interpret("Đơn hàng theo bang", df_two_cols)
    assert spec_2 == {"type": "bar", "x": "customer_state", "y": "orders"}
    assert "SP" in ans_2
    assert "40,000" in ans_2



# ==============================================================================
# 4. SMOKE TEST VỚI GEMINI THẬT (@pytest.mark.llm)
# ==============================================================================

@pytest.mark.llm
def test_smoke_call_real_gemini_api():
    """Smoke test gọi trực tiếp Gemini API thật (chỉ chạy khi có GEMINI_API_KEY hợp lệ)."""
    api_key = get_api_key()
    if not api_key or api_key == "your_key_here":
        pytest.skip("Thiếu GEMINI_API_KEY hợp lệ trong môi trường, bỏ qua smoke test LLM thật.")

    res = ask(question="Tổng số đơn hàng thành công trong hệ thống là bao nhiêu?")

    # Nếu tài khoản / key chưa đăng ký quota hoặc model cụ thể không khả dụng trên cloud
    if res.get("error"):
        err_msg = str(res["error"]).lower()
        if any(term in err_msg for term in ["404", "quota", "unavailable", "not_found", "not found", "permission"]):
            pytest.skip(f"Môi trường API chưa khả dụng: {res.get('error')}")

    assert res["error"] is None, f"Lỗi gọi Gemini thật: {res.get('error')}"
    assert res["sql"] is not None
    assert "orders" in res["sql"].lower()
    assert res["df"] is not None
    assert len(res["df"]) > 0
    assert len(res["answer"]) > 0
    assert res["latency_s"] > 0
