"""
Design System, Theme Tokens and UI Components for Dark Analytics + Bento Grid.
"""

import re
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# 1. Theme Tokens (Bảng màu, typography, góc bo)
TOKENS = {
    "bg": "#0B1220",
    "surface": "#131C31",
    "border": "#22304F",
    "primary": "#6366F1",
    "secondary": "#22D3EE",
    "positive": "#34D399",
    "alert": "#F87171",
    "warning": "#FBBF24",
    "text": "#E6EAF2",
    "muted": "#8B97B1",
}

SEQUENCE = [TOKENS["primary"], TOKENS["secondary"], "#A78BFA", "#38BDF8"]


# 2. Đăng ký Plotly Template thống nhất
def register_plotly_template():
    """Đăng ký template 'olist' vào Plotly và đặt làm mặc định."""
    t = TOKENS
    pio.templates["olist"] = go.layout.Template(
        layout=dict(
            font=dict(family="Inter, sans-serif", color=t["text"], size=13),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=SEQUENCE,
            xaxis=dict(
                showgrid=False,
                linecolor=t["border"],
                tickcolor=t["border"],
                tickfont=dict(color=t["muted"], size=11),
                title=dict(font=dict(color=t["muted"], size=12)),
            ),
            yaxis=dict(
                gridcolor=t["border"],
                zeroline=False,
                tickfont=dict(color=t["muted"], size=11),
                title=dict(font=dict(color=t["muted"], size=12)),
            ),
            title=dict(
                font=dict(family="Plus Jakarta Sans, Inter, sans-serif", size=15, color=t["text"]),
                x=0,
                xanchor="left",
            ),
            margin=dict(l=8, r=8, t=44, b=8),
            hoverlabel=dict(
                bgcolor=t["surface"],
                bordercolor=t["border"],
                font=dict(family="Inter, sans-serif", color=t["text"], size=12),
            ),
        )
    )
    pio.templates.default = "olist"


# 3. Inject CSS toàn cục
def inject_css():
    """Chèn CSS tùy biến: Google Fonts, Bento containers, ẩn header/footer, giảm padding."""
    t = TOKENS
    css = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');
html, body, p, label, input, textarea, li,
[data-testid="stMarkdownContainer"], [data-testid="stMetric"] {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }}
[data-testid="stIconMaterial"], .material-symbols-rounded, .material-symbols-outlined, [class*="material-symbols"], [data-testid*="Icon"] {{
    font-family: 'Material Symbols Rounded', 'Material Symbols Outlined' !important;
    font-weight: normal;
    font-style: normal;
    display: inline-block;
    white-space: nowrap;
    text-transform: none;
    -webkit-font-smoothing: antialiased;
    font-feature-settings: 'liga';
}}
h1, h2, h3, h4, h5, h6 {{ font-family: 'Plus Jakarta Sans', sans-serif !important; font-weight: 700 !important; letter-spacing: -0.02em; color: {t['text']} !important; }}
header[data-testid="stHeader"] {{
    background: transparent !important;
    z-index: 999999 !important;
    pointer-events: none !important;
}}
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] a,
[data-testid="stToolbar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"] {{
    pointer-events: auto !important;
}}
[data-testid="stToolbar"] {{
    visibility: visible !important;
    display: flex !important;
    background: transparent !important;
}}
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"] {{
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    color: #FFFFFF !important;
}}
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button {{
    background-color: {t['surface']} !important;
    border: 1px solid {t['primary']} !important;
    border-radius: 8px !important;
    padding: 5px 8px !important;
    box-shadow: 0 2px 10px rgba(99, 102, 241, 0.35) !important;
    transition: all 0.2s ease !important;
    color: #FFFFFF !important;
}}
[data-testid="stExpandSidebarButton"]:hover,
[data-testid="stSidebarCollapsedControl"] button:hover,
[data-testid="stSidebarCollapseButton"] button:hover {{
    background-color: {t['primary']} !important;
    border-color: {t['secondary']} !important;
    color: #FFFFFF !important;
    transform: scale(1.05) !important;
}}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stExpandSidebarButton"] span,
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] span,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="stSidebarCollapseButton"] span {{
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
}}
footer, #MainMenu, [data-testid="stDeployButton"] {{
    visibility: hidden !important;
    display: none !important;
}}
.block-container {{ padding-top: 2.5rem !important; padding-bottom: 2rem !important; max-width: 96% !important; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ background-color: {t['surface']} !important; border: 1px solid {t['border']} !important; border-radius: 16px !important; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.45) !important; padding: 1.25rem !important; transition: border-color 0.2s ease, box-shadow 0.2s ease; }}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {{ border-color: rgba(99, 102, 241, 0.4) !important; box-shadow: 0 6px 24px -2px rgba(0, 0, 0, 0.55) !important; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 8px; background-color: {t['bg']}; padding: 5px; border-radius: 14px; border: 1px solid {t['border']}; }}
.stTabs [data-baseweb="tab"] {{ height: 42px; background-color: transparent; border-radius: 10px; color: {t['muted']}; font-size: 14px; font-weight: 500; padding: 8px 18px; border: none; transition: all 0.2s ease; }}
.stTabs [aria-selected="true"] {{ background-color: {t['surface']} !important; color: {t['primary']} !important; font-weight: 700 !important; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35); }}
.stTabs [data-baseweb="tab-highlight"] {{ display: none; }}
div[role="radiogroup"] {{ background-color: {t['surface']}; border: 1px solid {t['border']}; padding: 4px; border-radius: 12px; }}
section[data-testid="stSidebar"] {{ background-color: {t['surface']} !important; border-right: 1px solid {t['border']} !important; }}
</style>"""
    st.markdown(css, unsafe_allow_html=True)


# 4. Hero Banner đầu trang
def hero_banner(title: str, subtitle: str, date_range: str = None):
    """Hiển thị hero banner đầu trang chuẩn Dark Analytics với gradient và badge ngày."""
    date_badge = ""
    if date_range:
        date_badge = f"""<div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 9999px; padding: 5px 14px; font-size: 12.5px; font-weight: 500; color: {TOKENS['secondary']};"><span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: {TOKENS['secondary']}; box-shadow: 0 0 8px {TOKENS['secondary']};"></span><span>{date_range}</span></div>"""

    raw_html = f"""<div style="background: linear-gradient(135deg, rgba(19, 28, 49, 0.98) 0%, rgba(15, 23, 42, 0.92) 100%); border: 1px solid {TOKENS['border']}; border-radius: 20px; padding: 22px 26px; margin-bottom: 20px; box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5); display: flex; flex-direction: column; gap: 8px; position: relative; overflow: hidden;"><div style="position: absolute; top: -40px; right: -40px; width: 180px; height: 180px; background: radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0) 70%); border-radius: 50%; pointer-events: none;"></div><div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;"><h1 style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 24px; font-weight: 800; color: {TOKENS['text']}; margin: 0; letter-spacing: -0.02em;">{title}</h1>{date_badge}</div><p style="font-size: 13.5px; color: {TOKENS['muted']}; margin: 0; line-height: 1.5; max-width: 850px;">{subtitle}</p></div>"""
    st.markdown(raw_html, unsafe_allow_html=True)


# 5. Helper tạo sparkline SVG
def _generate_sparkline_svg(values, stroke_color="#6366F1", width=64, height=24):
    """Tạo inline SVG sparkline nhỏ từ danh sách giá trị số."""
    if not values or len(values) < 2:
        return ""
    try:
        clean_vals = [float(v) for v in values if v is not None]
        if len(clean_vals) < 2:
            return ""
        min_v = min(clean_vals)
        max_v = max(clean_vals)
        v_range = max_v - min_v if max_v != min_v else 1.0

        pad = 2.0
        w = float(width)
        h = float(height)

        pts = []
        n = len(clean_vals)
        for i, val in enumerate(clean_vals):
            x = pad + (i / (n - 1)) * (w - 2 * pad)
            y = (h - pad) - ((val - min_v) / v_range) * (h - 2 * pad)
            pts.append(f"{x:.1f},{y:.1f}")

        points_str = " ".join(pts)
        return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="overflow: visible;"><polyline fill="none" stroke="{stroke_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="{points_str}"/></svg>"""
    except Exception:
        return ""


# 6. KPI Card HTML Component
def kpi_card(label: str, value: str, delta: str = None, good_when_up: bool = True, spark_values: list = None):
    """
    Hiển thị thẻ KPI với phong cách Dark Analytics:
    - Label uppercase tinh gọn
    - Giá trị đậm nét với Plus Jakarta Sans
    - Delta pill (xanh khi tích cực, đỏ khi tiêu cực)
    - Sparkline SVG nhỏ biểu diễn xu hướng
    """
    pill_html = ""
    spark_color = TOKENS["primary"]

    if delta:
        delta_str = str(delta).strip()
        is_positive = delta_str.startswith("+")
        is_negative = delta_str.startswith("-")

        if is_positive:
            is_good = good_when_up
            arrow = "↑"
        elif is_negative:
            is_good = not good_when_up
            arrow = "↓"
        else:
            is_good = True
            arrow = ""

        if is_good:
            pill_color = TOKENS["positive"]
            pill_bg = "rgba(52, 211, 153, 0.12)"
            pill_border = "rgba(52, 211, 153, 0.25)"
            spark_color = TOKENS["positive"]
        else:
            pill_color = TOKENS["alert"]
            pill_bg = "rgba(248, 113, 113, 0.12)"
            pill_border = "rgba(248, 113, 113, 0.25)"
            spark_color = TOKENS["alert"]

        pill_html = f"""<div style="display: inline-flex; align-items: center; gap: 3px; background: {pill_bg}; border: 1px solid {pill_border}; color: {pill_color}; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; line-height: 1.2;"><span>{arrow}</span><span>{delta_str}</span></div>"""

    spark_svg = _generate_sparkline_svg(spark_values, stroke_color=spark_color) if spark_values else ""

    raw_html = f"""<div style="background: {TOKENS['surface']}; border: 1px solid {TOKENS['border']}; border-radius: 16px; padding: 16px 18px; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.35); display: flex; flex-direction: column; justify-content: space-between; min-height: 115px; transition: transform 0.2s ease, border-color 0.2s ease;"><div style="font-size: 11.5px; font-weight: 600; color: {TOKENS['muted']}; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;">{label}</div><div style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 21px; font-weight: 700; color: {TOKENS['text']}; letter-spacing: -0.02em; margin-bottom: 10px;">{value}</div><div style="display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-top: auto;">{pill_html}{spark_svg}</div></div>"""
    st.markdown(raw_html, unsafe_allow_html=True)


# 7. Insight Card HTML Component
def insight_card(icon: str, headline: str, detail: str, tone: str = "info"):
    """
    Hiển thị thẻ nhận định (Insight Card) với 3 sắc thái:
    - good (tích cực, viền xanh)
    - warn (cảnh báo, viền đỏ)
    - info (thông tin, viền tím/xanh dương)
    """
    tone_map = {
        "good": {
            "border": "rgba(52, 211, 153, 0.35)",
            "bg": "linear-gradient(135deg, rgba(19, 28, 49, 0.95) 0%, rgba(52, 211, 153, 0.08) 100%)",
            "badge_bg": "rgba(52, 211, 153, 0.18)",
            "accent": TOKENS["positive"],
        },
        "warn": {
            "border": "rgba(248, 113, 113, 0.35)",
            "bg": "linear-gradient(135deg, rgba(19, 28, 49, 0.95) 0%, rgba(248, 113, 113, 0.08) 100%)",
            "badge_bg": "rgba(248, 113, 113, 0.18)",
            "accent": TOKENS["alert"],
        },
        "info": {
            "border": "rgba(99, 102, 241, 0.35)",
            "bg": "linear-gradient(135deg, rgba(19, 28, 49, 0.95) 0%, rgba(99, 102, 241, 0.08) 100%)",
            "badge_bg": "rgba(99, 102, 241, 0.18)",
            "accent": TOKENS["primary"],
        },
    }
    cfg = tone_map.get(tone, tone_map["info"])
    raw_html = f"""<div style="background: {cfg['bg']}; border: 1px solid {cfg['border']}; border-radius: 16px; padding: 16px 18px; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.35); display: flex; flex-direction: column; gap: 8px; height: 100%;"><div style="display: flex; align-items: center; gap: 10px;"><span style="display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 8px; background: {cfg['badge_bg']}; font-size: 15px;">{icon}</span><span style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 14px; font-weight: 700; color: {TOKENS['text']};">{headline}</span></div><div style="font-size: 12.5px; color: {TOKENS['muted']}; line-height: 1.55;">{detail}</div></div>"""
    st.markdown(raw_html, unsafe_allow_html=True)


# 8. Section Header tinh gọn (không emoji)
def section_header(title: str, caption: str = None):
    """Tiêu đề phân đoạn chuẩn Dark Bento Grid, loại bỏ emoji ở tiêu đề chính."""
    clean_title = re.sub(r"^[^\w\s]+\s*", "", title).strip()
    caption_html = (
        f'<div style="font-size: 13px; color: {TOKENS["muted"]}; margin-top: 3px;">{caption}</div>'
        if caption
        else ""
    )
    raw_html = f"""<div style="margin: 18px 0 12px 0;"><h3 style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 17px; font-weight: 700; color: {TOKENS['text']}; margin: 0; letter-spacing: -0.01em;">{clean_title}</h3>{caption_html}</div>"""
    st.markdown(raw_html, unsafe_allow_html=True)