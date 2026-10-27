"""
Kiểm thử cho module src/ai/schema_context.py:
1. Unit tests:
   - Prompt sinh ra chứa đầy đủ 6 bảng trong whitelist.
   - Prompt chứa các cột quan trọng và quy tắc nghiệp vụ cốt lõi.
   - Mọi câu lệnh SQL trong FEW_SHOTS đều vượt qua sql_guard.validate_sql.
   - Danh sách FEW_SHOTS bao phủ đầy đủ các chủ đề nghiệp vụ yêu cầu.
2. Integration tests (chạy trên DB thật):
   - Mọi câu lệnh SQL trong FEW_SHOTS đều thực thi an toàn bằng execute_safe, trả về df hợp lệ.
   - Kết quả vài câu SQL khớp chính xác với hàm tương ứng trong src/db.py (KPI, repeat rate, payment mix).
"""

import pytest
import pandas as pd

from src.ai.schema_context import (
    SCHEMA_TABLES,
    BUSINESS_RULES,
    FEW_SHOTS,
    build_schema_prompt,
    get_few_shots,
)
from src.ai.sql_guard import validate_sql, execute_safe, WHITELIST_TABLES


# ==============================================================================
# PHẦN 1: UNIT TESTS (Không cần kết nối DB)
# ==============================================================================

def test_schema_prompt_contains_all_six_whitelist_tables():
    """Prompt phải chứa đầy đủ 6 bảng whitelist."""
    prompt = build_schema_prompt()
    for table in WHITELIST_TABLES:
        assert f"`{table}`" in prompt, f"Bảng `{table}` không có trong schema prompt"
        assert table in SCHEMA_TABLES


def test_schema_prompt_contains_important_columns():
    """Prompt phải chứa mô tả tiếng Việt cho từng cột quan trọng."""
    prompt = build_schema_prompt()
    important_columns = [
        "order_status",
        "order_purchase_timestamp",
        "payment_value",
        "review_score",
        "customer_unique_id",
        "customer_state",
        "product_category_name_english",
    ]
    for col in important_columns:
        assert f"`{col}`" in prompt, f"Cột quan trọng `{col}` không xuất hiện trong prompt"


def test_schema_prompt_contains_business_rules():
    """Prompt phải nêu rõ các quy tắc nghiệp vụ then chốt."""
    prompt = build_schema_prompt()
    assert "delivered" in prompt
    assert "customer_unique_id" in prompt
    assert "order_payments" in prompt
    assert "order_reviews" in prompt
    assert "strftime" in prompt
    assert "product_category_name_english" in prompt
    assert "BRL" in prompt or "Real Brazil" in prompt


def test_few_shots_count_and_topics():
    """Phải có từ 8 đến 10 ví dụ few-shot bao phủ các chủ đề nghiệp vụ."""
    shots = get_few_shots()
    assert 8 <= len(shots) <= 10

    questions = " ".join([s["question"] for s in shots]).lower()
    # Kiểm tra bao phủ các chủ đề
    assert "danh mục" in questions or "sản phẩm" in questions
    assert "bang" in questions
    assert "trễ" in questions
    assert "đánh giá" in questions
    assert "mua lại" in questions
    assert "thanh toán" in questions


@pytest.mark.parametrize("shot", FEW_SHOTS, ids=[f"shot_{i+1}" for i in range(len(FEW_SHOTS))])
def test_all_few_shots_pass_validate_sql(shot):
    """Mọi câu lệnh SQL trong FEW_SHOTS phải vượt qua bộ lọc an toàn validate_sql."""
    sql = shot["sql"]
    is_valid, error = validate_sql(sql)
    assert is_valid is True, f"Few-shot SQL bị validate_sql từ chối: {error} | SQL: {sql}"
    assert error == ""


def test_build_schema_prompt_optional_few_shots():
    """Có thể bật/tắt chèn few-shots vào prompt."""
    prompt_with = build_schema_prompt(include_few_shots=True)
    prompt_without = build_schema_prompt(include_few_shots=False)

    assert "=== 3. CÁC VÍ DỤ MẪU (FEW-SHOT EXAMPLES) ===" in prompt_with
    assert "=== 3. CÁC VÍ DỤ MẪU (FEW-SHOT EXAMPLES) ===" not in prompt_without
    assert len(prompt_with) > len(prompt_without)


# ==============================================================================
# PHẦN 2: INTEGRATION TESTS (Chạy trên CSDL SQLite thật)
# ==============================================================================

@pytest.mark.integration
@pytest.mark.parametrize("shot", FEW_SHOTS, ids=[f"exec_shot_{i+1}" for i in range(len(FEW_SHOTS))])
def test_all_few_shots_execute_safe_on_real_db(shot):
    """Tất cả câu SQL trong FEW_SHOTS phải chạy thành công trên DB thật qua execute_safe."""
    sql = shot["sql"]
    result = execute_safe(sql)
    assert result["ok"] is True, f"Lỗi khi thực thi few-shot: {result.get('error')}"
    assert result["df"] is not None
    assert isinstance(result["df"], pd.DataFrame)
    assert len(result["df"]) > 0, f"Truy vấn không trả về dòng nào: {sql}"
    assert result["rows"] == len(result["df"])


@pytest.mark.integration
def test_few_shot_kpi_matches_db_metrics():
    """Kết quả câu SQL KPI (Ví dụ 7) phải khớp chính xác với hàm get_kpi_metrics() trong src/db.py."""
    from src.db import get_kpi_metrics

    # Tìm câu SQL KPI trong FEW_SHOTS
    kpi_shot = None
    for shot in FEW_SHOTS:
        if "tổng doanh thu" in shot["question"].lower() and "tổng số khách hàng" in shot["question"].lower():
            kpi_shot = shot
            break
    assert kpi_shot is not None, "Không tìm thấy câu few-shot về KPI metrics"

    res = execute_safe(kpi_shot["sql"])
    assert res["ok"] is True
    sql_row = res["df"].iloc[0]

    db_metrics = get_kpi_metrics()

    # So sánh các chỉ số
    assert int(sql_row["total_orders"]) == int(db_metrics["total_orders"])
    assert round(float(sql_row["total_revenue"]), 2) == round(float(db_metrics["total_revenue"]), 2)
    assert round(float(sql_row["avg_review_score"]), 2) == round(float(db_metrics["avg_review_score"]), 2)
    assert int(sql_row["total_customers"]) == int(db_metrics["total_customers"])


@pytest.mark.integration
def test_few_shot_repeat_rate_matches_db():
    """Kết quả câu SQL tỷ lệ mua lại (Ví dụ 5) phải khớp với hàm get_repeat_customer_rate() trong src/db.py."""
    from src.db import get_repeat_customer_rate

    repeat_shot = None
    for shot in FEW_SHOTS:
        if "mua lại" in shot["question"].lower():
            repeat_shot = shot
            break
    assert repeat_shot is not None, "Không tìm thấy câu few-shot về khách mua lại"

    res = execute_safe(repeat_shot["sql"])
    assert res["ok"] is True
    sql_row = res["df"].iloc[0]

    db_repeat_rate = get_repeat_customer_rate()
    assert round(float(sql_row["repeat_rate_pct"]), 2) == round(float(db_repeat_rate), 2)


@pytest.mark.integration
def test_few_shot_payment_mix_matches_db():
    """Kết quả câu SQL cơ cấu thanh toán (Ví dụ 6) phải khớp với hàm get_payment_mix() trong src/db.py."""
    from src.db import get_payment_mix

    pay_shot = None
    for shot in FEW_SHOTS:
        if "hình thức thanh toán" in shot["question"].lower():
            pay_shot = shot
            break
    assert pay_shot is not None, "Không tìm thấy câu few-shot về payment mix"

    res = execute_safe(pay_shot["sql"])
    assert res["ok"] is True
    df_sql = res["df"].sort_values("total_revenue", ascending=False).reset_index(drop=True)

    df_db = get_payment_mix().sort_values("revenue", ascending=False).reset_index(drop=True)

    assert len(df_sql) == len(df_db)
    for i in range(len(df_sql)):
        assert df_sql.iloc[i]["payment_type"] == df_db.iloc[i]["payment_type"]
        assert round(float(df_sql.iloc[i]["total_revenue"]), 2) == round(float(df_db.iloc[i]["revenue"]), 2)
        assert int(df_sql.iloc[i]["orders"]) == int(df_db.iloc[i]["orders"])
