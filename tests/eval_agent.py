"""
Đánh giá độ chính xác thực tế (Evaluation Benchmark) của AI Agent Text-to-SQL.
Thực thi 25 câu hỏi từ tests/eval_cases.py, so sánh kết quả thực tế với ground truth,
hỗ trợ Resume, dừng sớm khi hết hạn mức ngày, phân loại 3 trạng thái và ghi tests/eval_results.json.

Đánh dấu: @pytest.mark.llm (không chạy trong CI).
"""

import io
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
import pytest

from src.ai.agent import ask, get_api_key, get_quota_status
from src.ai.sql_guard import execute_safe
from tests.eval_cases import EVAL_CASES

# Đường dẫn file lưu kết quả đánh giá (đã được thêm vào .gitignore)
RESULTS_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "eval_results.json"))

# Khoảng nghỉ giữa các câu hỏi (giây) để tránh chạm rate limit RPM
SLEEP_BETWEEN_CALLS_S = 4.5

# Dung sai so sánh số thực
NUMERICAL_TOLERANCE = 0.01


# ==============================================================================
# 1. HÀM SO SÁNH KẾT QUẢ ĐỘC LẬP VỚI TÊN CỘT / THỨ TỰ CỘT
# ==============================================================================

def _is_numeric(val: Any) -> bool:
    """Kiểm tra một giá trị có phải là dạng số hay không."""
    if val is None or pd.isna(val):
        return False
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False


def compare_results(
    agent_res: Dict[str, Any],
    case: Dict[str, Any],
    tolerance: float = NUMERICAL_TOLERANCE,
) -> Tuple[str, str]:
    """
    So sánh kết quả của Agent với Ground Truth:
    Trả về: (status, reason)
    - status: 'ĐÚNG' | 'SAI' | 'KHÔNG ĐÁNH GIÁ ĐƯỢC'
    - reason: lý do chi tiết (kèm ghi rõ nguồn chặn nếu ngoài phạm vi)
    """
    is_out_of_scope = case.get("is_out_of_scope", False)
    error_code = agent_res.get("error")

    # Kiểm tra các ca không đánh giá được do lỗi hạ tầng / hạn mức / timeout
    if error_code in {"QUOTA_EXHAUSTED", "MISSING_API_KEY", "DAILY_QUOTA_EXHAUSTED", "TIMEOUT"}:
        return "KHÔNG ĐÁNH GIÁ ĐƯỢC", f"Lỗi hạn mức hoặc cấu hình API: {error_code}"

    # 1. Kiểm tra ca ngoài phạm vi
    if is_out_of_scope:
        blocked_source = agent_res.get("blocked_by", "unknown")
        if agent_res.get("sql") is None and (
            agent_res.get("df") is None or getattr(agent_res.get("df"), "empty", True)
        ):
            source_desc = "từ khóa" if blocked_source == "pattern" else ("LLM" if blocked_source == "llm" else "bộ lọc")
            return "ĐÚNG", f"Từ chối đúng câu hỏi ngoài phạm vi (chặn bằng {source_desc})"
        return "SAI", "Không từ chối câu hỏi ngoài phạm vi"

    # 2. Ca hợp lệ: kiểm tra xem Agent có sinh kết quả hay không
    df_agent = agent_res.get("df")
    if df_agent is None or getattr(df_agent, "empty", True):
        err = agent_res.get("error") or "Agent không trả về bảng dữ liệu (df is None/empty)"
        return "SAI", f"Không có dữ liệu: {err}"

    # 3. Lấy kết quả Ground Truth
    gt_sql = case.get("ground_truth_sql")
    if not gt_sql:
        return "KHÔNG ĐÁNH GIÁ ĐƯỢC", "Thiếu ground_truth_sql trong test case"

    gt_exec = execute_safe(gt_sql)
    if not gt_exec.get("ok") or gt_exec.get("df") is None:
        return "KHÔNG ĐÁNH GIÁ ĐƯỢC", f"Lỗi chạy ground truth SQL: {gt_exec.get('error')}"

    df_gt = gt_exec["df"]

    # 4. So sánh số lượng dòng
    if len(df_agent) != len(df_gt):
        return "SAI", f"Lệch số dòng: Agent={len(df_agent)}, GT={len(df_gt)}"

    # 5. So sánh nội dung giá trị:
    # Trường hợp 1 dòng:
    if len(df_gt) == 1:
        vals_agent = list(df_agent.iloc[0].values)
        vals_gt = list(df_gt.iloc[0].values)

        num_agent = sorted([float(v) for v in vals_agent if _is_numeric(v)])
        num_gt = sorted([float(v) for v in vals_gt if _is_numeric(v)])

        if len(num_agent) != len(num_gt):
            return "SAI", f"Số lượng chỉ số số học không khớp: agent={num_agent}, gt={num_gt}"

        for na, ng in zip(num_agent, num_gt):
            diff = abs(na - ng)
            rel_diff = diff / max(abs(ng), 1e-6)
            if diff > tolerance and rel_diff > tolerance:
                return "SAI", f"Sai lệch giá trị: Agent={na}, GT={ng} (chênh lệch {diff:.4f})"

        str_agent = sorted([str(v).strip().lower() for v in vals_agent if not _is_numeric(v)])
        str_gt = sorted([str(v).strip().lower() for v in vals_gt if not _is_numeric(v)])
        if str_agent != str_gt:
            return "SAI", f"Chuỗi không khớp: agent={str_agent}, gt={str_gt}"

        return "ĐÚNG", "Khớp giá trị số liệu 100%"

    # Trường hợp nhiều dòng (bảng danh sách, top N):
    numeric_cols_agent = [c for c in df_agent.columns if pd.api.types.is_numeric_dtype(df_agent[c])]
    numeric_cols_gt = [c for c in df_gt.columns if pd.api.types.is_numeric_dtype(df_gt[c])]

    if numeric_cols_agent and numeric_cols_gt:
        sort_col_agent = numeric_cols_agent[-1]
        sort_col_gt = numeric_cols_gt[-1]
        sorted_agent = df_agent.sort_values(sort_col_agent, ascending=False).reset_index(drop=True)
        sorted_gt = df_gt.sort_values(sort_col_gt, ascending=False).reset_index(drop=True)
    else:
        sorted_agent = df_agent.reset_index(drop=True)
        sorted_gt = df_gt.reset_index(drop=True)

    for i in range(len(sorted_gt)):
        row_agent = sorted_agent.iloc[i].values
        row_gt = sorted_gt.iloc[i].values

        num_a = sorted([float(v) for v in row_agent if _is_numeric(v)])
        num_g = sorted([float(v) for v in row_gt if _is_numeric(v)])

        for na, ng in zip(num_a, num_g):
            diff = abs(na - ng)
            rel_diff = diff / max(abs(ng), 1e-6)
            if diff > tolerance and rel_diff > tolerance:
                return "SAI", f"Dòng {i+1} sai số: Agent={na}, GT={ng}"

    return "ĐÚNG", "Khớp toàn bộ bảng dữ liệu"


# ==============================================================================
# 2. CƠ CHẾ RESUME & ĐỌC / GHI KẾT QUẢ ĐÁNH GIÁ
# ==============================================================================

def load_previous_results(path: str = RESULTS_JSON_PATH) -> Dict[str, Dict[str, Any]]:
    """Đọc kết quả các lần chạy trước để hỗ trợ tính năng Resume."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Tạo map theo id: {case_id: record}
            return {item["id"]: item for item in data.get("results", []) if "id" in item}
    except Exception:
        return {}


# ==============================================================================
# 3. HÀM CHẠY BENCHMARK VỚI RESUME, QUOTA GUARD & THỐNG KÊ MẪU SỐ
# ==============================================================================

def run_evaluation(
    cases: Optional[List[Dict[str, Any]]] = None,
    save_results: bool = True,
    output_path: str = RESULTS_JSON_PATH,
    resume: bool = True,
) -> Dict[str, Any]:
    """
    Chạy đánh giá 25 câu hỏi:
    - Resume: Tái sử dụng kết quả các câu đã ĐÚNG/SAI từ trước.
    - Dừng sớm: Dừng ngay khi chạm hạn mức ngày (429/QUOTA_EXHAUSTED).
    - Phân loại: ĐÚNG, SAI, KHÔNG ĐÁNH GIÁ ĐƯỢC (loại khỏi mẫu số).
    - Tiết kiệm quota: Đặt interpret_with_llm=False.
    """
    test_cases = cases or EVAL_CASES
    existing_results = load_previous_results(output_path) if resume else {}

    results_map: Dict[str, Dict[str, Any]] = {}
    quota_exhausted_triggered = False

    print(f"\n{'='*85}", flush=True)
    print(f"{'BẮT ĐẦU ĐÁNH GIÁ AI AGENT TEXT-TO-SQL (TỔNG SỐ CA: ' + str(len(test_cases)) + ')':^85}", flush=True)
    print(f"{'='*85}\n", flush=True)

    # In thông tin quota hiện tại
    quota_info = get_quota_status()
    print(f"[*] Hạn mức hôm nay: Đã dùng {quota_info['used']}/{quota_info['limit']} lượt (Còn lại: {quota_info['remaining']})", flush=True)
    if resume and existing_results:
        print(f"[*] Đã nạp {len(existing_results)} kết quả từ lần chạy trước (chế độ Resume đang bật).\n", flush=True)

    for idx, case in enumerate(test_cases, 1):
        q_id = case["id"]
        q_text = case["question"]
        q_group = case["group_name"]
        is_oos = case.get("is_out_of_scope", False)

        # 1. Kiểm tra nếu đã có kết quả xác định (ĐÚNG hoặc SAI) từ trước
        prev = existing_results.get(q_id)
        if prev and prev.get("status") in {"ĐÚNG", "SAI"}:
            results_map[q_id] = prev
            print(f"[{idx:02d}/{len(test_cases)}] {q_id} ({q_group}): [ĐÃ CÓ KẾT QUẢ - {prev['status']}] (bỏ qua chạy lại)", flush=True)
            continue

        # 2. Nếu đã kích hoạt dừng sớm do hết hạn mức ngày
        if quota_exhausted_triggered:
            results_map[q_id] = {
                "id": q_id,
                "group": case["group"],
                "group_name": q_group,
                "question": q_text,
                "is_out_of_scope": is_oos,
                "status": "KHÔNG ĐÁNH GIÁ ĐƯỢC",
                "attempts": 0,
                "latency_s": 0.0,
                "reason": "Chưa đánh giá (dừng sớm do hết hạn mức API trong ngày)",
                "sql": None,
                "answer_preview": "",
                "blocked_by": None,
            }
            print(f"[{idx:02d}/{len(test_cases)}] {q_id} ({q_group}): [BỎ QUA DO HẾT QUOTA]", flush=True)
            continue

        print(f"[{idx:02d}/{len(test_cases)}] Đang chạy {q_id} ({q_group}): \"{q_text}\" ...", flush=True)

        # 3. Gọi agent.ask với interpret_with_llm=False (tiết kiệm 50% lượt gọi LLM)
        agent_res = ask(q_text, interpret_with_llm=False)

        # 4. Kiểm tra lỗi hạn mức
        if agent_res.get("error") == "QUOTA_EXHAUSTED":
            quota_exhausted_triggered = True
            print("   [!] Đã đạt hạn mức ngày của API. Dừng sớm để bảo toàn kết quả.", flush=True)

        status, reason = compare_results(agent_res, case)

        res_record = {
            "id": q_id,
            "group": case["group"],
            "group_name": q_group,
            "question": q_text,
            "is_out_of_scope": is_oos,
            "status": status,
            "attempts": agent_res.get("attempts", 0),
            "latency_s": agent_res.get("latency_s", 0.0),
            "reason": reason,
            "sql": agent_res.get("sql"),
            "answer_preview": (agent_res.get("answer") or "")[:120],
            "blocked_by": agent_res.get("blocked_by"),
        }
        results_map[q_id] = res_record

        print(f"   -> Trạng thái: {status} | Thử: {res_record['attempts']} | Độ trễ: {res_record['latency_s']}s | Ghi chú: {reason}", flush=True)

        if not quota_exhausted_triggered and idx < len(test_cases):
            time.sleep(SLEEP_BETWEEN_CALLS_S)

    # Chuyển map thành danh sách theo đúng thứ tự test_cases
    results_list = [results_map[c["id"]] for c in test_cases if c["id"] in results_map]

    # ==========================================================================
    # 4. TÍNH TOÁN THỐNG KÊ CHI TIẾT (LOẠI CA KHÔNG ĐÁNH GIÁ ĐƯỢC KHỎI MẪU SỐ)
    # ==========================================================================
    total_cases = len(results_list)
    evaluated_cases = [r for r in results_list if r["status"] in {"ĐÚNG", "SAI"}]
    untestable_cases = [r for r in results_list if r["status"] == "KHÔNG ĐÁNH GIÁ ĐƯỢC"]

    n_eval = len(evaluated_cases)
    n_correct = sum(1 for r in evaluated_cases if r["status"] == "ĐÚNG")
    accuracy_pct = round((n_correct / n_eval) * 100.0, 2) if n_eval > 0 else 0.0

    # Phân nhóm
    group_stats: Dict[str, Dict[str, Any]] = {}
    for r in results_list:
        g = r["group"]
        g_name = r["group_name"]
        if g not in group_stats:
            group_stats[g] = {"name": g_name, "total": 0, "evaluated": 0, "correct": 0}
        group_stats[g]["total"] += 1
        if r["status"] in {"ĐÚNG", "SAI"}:
            group_stats[g]["evaluated"] += 1
            if r["status"] == "ĐÚNG":
                group_stats[g]["correct"] += 1

    for g, d in group_stats.items():
        d["accuracy_pct"] = round((d["correct"] / d["evaluated"]) * 100.0, 2) if d["evaluated"] > 0 else 0.0

    # Tỷ lệ câu hỏi cần sửa lỗi (attempts >= 2 trên các câu đã đánh giá hợp lệ)
    valid_evaluated = [r for r in evaluated_cases if not r["is_out_of_scope"]]
    retry_count = sum(1 for r in valid_evaluated if r["attempts"] >= 2)
    retry_rate_pct = round((retry_count / len(valid_evaluated)) * 100.0, 2) if valid_evaluated else 0.0

    # Độ trễ trung bình của các ca có thực thi
    latencies = [r["latency_s"] for r in results_list if r["latency_s"] > 0]
    avg_latency_s = round(float(np.mean(latencies)), 2) if latencies else 0.0

    # Câu ngoài phạm vi
    oos_evaluated = [r for r in results_list if r["is_out_of_scope"]]
    oos_correct = sum(1 for r in oos_evaluated if r["status"] == "ĐÚNG")

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_cases": total_cases,
        "evaluated_count": n_eval,
        "untestable_count": len(untestable_cases),
        "total_correct": n_correct,
        "accuracy_on_evaluated_pct": accuracy_pct,
        "group_stats": group_stats,
        "needed_retry_count": retry_count,
        "retry_rate_pct": retry_rate_pct,
        "avg_latency_s": avg_latency_s,
        "oos_total": len(oos_evaluated),
        "oos_correct": oos_correct,
        "quota_exhausted": quota_exhausted_triggered,
        "results": results_list,
    }

    if save_results:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\n[+] Đã lưu toàn bộ kết quả vào: {output_path}", flush=True)

    # ==========================================================================
    # 5. IN BẢNG BÁO CÁO TỔNG KẾT
    # ==========================================================================
    print(f"\n{'='*105}", flush=True)
    print(f"{'BẢNG KẾT QUẢ ĐÁNH GIÁ TỪNG CÂU HỎI (EVALUATION REPORT)':^105}", flush=True)
    print(f"{'='*105}", flush=True)
    print(f"{'ID':<8} | {'Nhóm':<16} | {'Kết quả':<22} | {'Số lần thử':<10} | {'Độ trễ':<8} | {'Lý do / Trạng thái'}", flush=True)
    print(f"{'-'*105}", flush=True)
    for r in results_list:
        print(f"{r['id']:<8} | {r['group_name']:<16} | {r['status']:<22} | {r['attempts']:<10} | {r['latency_s']:>5.2f}s  | {r['reason']}", flush=True)
    print(f"{'-'*105}", flush=True)

    print(f"\n{'='*65}", flush=True)
    print(f"{'THỐNG KÊ HIỆU NĂNG VÀ ĐỘ CHÍNH XÁC':^65}", flush=True)
    print(f"{'='*65}", flush=True)
    print(f"Tổng số ca trong bộ test:          {total_cases}")
    print(f"Số ca đã đánh giá:                 {n_eval}/{total_cases} (Không đánh giá được: {len(untestable_cases)})")
    print(f"Độ chính xác trên các ca đánh giá: {n_correct}/{n_eval} ({accuracy_pct}%)")
    for g, d in group_stats.items():
        eval_str = f"{d['correct']}/{d['evaluated']} ({d['accuracy_pct']}%)" if d['evaluated'] > 0 else "Chưa đánh giá"
        print(f"  - {d['name']:<24}: {eval_str} [tổng {d['total']} ca]")
    print(f"Số câu ngoài phạm vi từ chối đúng: {oos_correct}/{len(oos_evaluated)} ({(oos_correct/len(oos_evaluated)*100.0 if oos_evaluated else 0):.1f}%)")
    print(f"Tỷ lệ câu hỏi cần sửa lỗi (retry): {retry_count}/{len(valid_evaluated)} ({retry_rate_pct}%)")
    print(f"Độ trễ trung bình:                 {avg_latency_s:.2f} giây/câu")
    print(f"{'='*65}", flush=True)

    if quota_exhausted_triggered:
        print("\n[!] LƯU Ý HẠN MỨC NGÀY:")
        print("  Hạn mức Google GenAI Free Tier hôm nay đã chạm ngưỡng.")
        print("  Hệ thống đã lưu lại tiến độ. Khi hạn mức được reset (hoặc khi đổi API key),")
        print("  chỉ cần chạy lại lệnh: python tests/eval_agent.py để tự động tiếp tục các ca còn lại.\n", flush=True)

    return summary


# ==============================================================================
# 6. PYTEST MARKER LLM
# ==============================================================================

@pytest.mark.llm
def test_eval_agent_benchmark():
    """Chạy đánh giá benchmark bằng pytest -m llm."""
    api_key = get_api_key()
    if not api_key or api_key == "your_key_here":
        pytest.skip("Thiếu GEMINI_API_KEY hợp lệ, bỏ qua benchmark LLM.")

    summary = run_evaluation(save_results=True, resume=True)
    # Kiểm tra các ca ngoài phạm vi
    assert summary["oos_correct"] == summary["oos_total"], "Không từ chối đúng các ca ngoài phạm vi"


if __name__ == "__main__":
    run_evaluation(save_results=True, resume=True)
