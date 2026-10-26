"""
Module định nghĩa nhãn hiển thị và ánh xạ bản địa hóa tiếng Việt (Localization & Labels)
cho các chiều phân tích cốt lõi (Bang Brazil và Danh mục sản phẩm Olist).
"""

from typing import Any, Dict, List, Optional

# ==============================================================================
# 1. 27 BANG BRAZIL (ISO 3166-2:BR / UF)
# ==============================================================================

STATE_NAMES: Dict[str, str] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

# Danh sách 27 bang sắp xếp theo số lượng đơn hàng thực tế giảm dần (Olist Brazil)
STATE_ORDER: List[str] = [
    "SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF", "ES", "GO",
    "PE", "CE", "PA", "MT", "MA", "MS", "PB", "PI", "RN", "AL",
    "SE", "TO", "RO", "AM", "AC", "AP", "RR",
]


def state_label(code: Any) -> str:
    """
    Chuyển mã bang 2 ký tự (SP, RJ) thành định dạng chuẩn: "Tên đầy đủ (Mã)".
    Ví dụ: state_label("SP") -> "São Paulo (SP)".
    Nếu mã không thuộc 27 bang hoặc rỗng/lạ thì fallback an toàn, không báo lỗi.
    """
    if code is None:
        return ""
    code_str = str(code).strip()
    if not code_str:
        return ""
    code_upper = code_str.upper()
    if code_upper in STATE_NAMES:
        return f"{STATE_NAMES[code_upper]} ({code_upper})"
    return code_str


# ==============================================================================
# 2. BẢN DỊCH TIẾNG VIỆT CHO CÁC DANH MỤC SẢN PHẨM (product_category_name_english)
# ==============================================================================

# Dịch cho ít nhất 30 danh mục có doanh thu dẫn đầu từ CSDL thật (sắp theo doanh thu)
CATEGORY_VI: Dict[str, str] = {
    # Top 1 - 10
    "health_beauty": "Sức khỏe & Làm đẹp",
    "watches_gifts": "Đồng hồ & Quà tặng",
    "bed_bath_table": "Đồ dùng phòng ngủ & phòng tắm",
    "sports_leisure": "Thể thao & Dã ngoại",
    "computers_accessories": "Máy tính & Phụ kiện",
    "furniture_decor": "Nội thất & Trang trí",
    "cool_stuff": "Đồ công nghệ & Quà độc đáo",
    "housewares": "Đồ gia dụng",
    "auto": "Ô tô & Xe máy",
    "garden_tools": "Dụng cụ làm vườn",
    # Top 11 - 20
    "toys": "Đồ chơi",
    "baby": "Mẹ & Bé",
    "perfumery": "Nước hoa",
    "telephony": "Điện thoại & Thiết bị di động",
    "office_furniture": "Nội thất văn phòng",
    "stationery": "Văn phòng phẩm",
    "computers": "Máy vi tính",
    "pet_shop": "Thú cưng",
    "musical_instruments": "Nhạc cụ",
    "small_appliances": "Thiết bị điện gia dụng nhỏ",
    # Top 21 - 30
    "others": "Khác",
    "electronics": "Thiết bị điện tử",
    "consoles_games": "Máy chơi game & Trò chơi",
    "fashion_bags_accessories": "Túi xách & Phụ kiện thời trang",
    "construction_tools_construction": "Công cụ xây dựng",
    "luggage_accessories": "Vali & Phụ kiện du lịch",
    "home_appliances_2": "Thiết bị gia dụng lớn",
    "home_construction": "Vật liệu xây dựng nhà cửa",
    "home_appliances": "Thiết bị điện gia đình",
    "agro_industry_and_commerce": "Nông nghiệp & Công thương nghiệp",
    # Top 31 - 45 (Bổ sung thêm danh mục doanh thu cao)
    "furniture_living_room": "Nội thất phòng khách",
    "fixed_telephony": "Điện thoại cố định",
    "home_confort": "Tiện nghi nhà cửa",
    "air_conditioning": "Điều hòa & Máy lạnh",
    "audio": "Thiết bị âm thanh",
    "small_appliances_home_oven_and_coffee": "Lò nướng & Máy pha cà phê",
    "books_general_interest": "Sách đại chúng",
    "kitchen_dining_laundry_garden_furniture": "Nội thất nhà bếp & Sân vườn",
    "construction_tools_lights": "Thiết bị chiếu sáng xây dựng",
    "construction_tools_safety": "Thiết bị bảo hộ lao động",
    "industry_commerce_and_business": "Công nghiệp & Thương mại",
    "food": "Thực phẩm",
    "market_place": "Sàn thương mại",
    "costruction_tools_garden": "Dụng cụ làm vườn & Xây dựng",
    "art": "Nghệ thuật & Hội họa",
    # Top 46 - 72 (Bổ sung toàn bộ danh mục còn lại trong DB Olist)
    "fashion_shoes": "Giày dép thời trang",
    "drinks": "Đồ uống",
    "signaling_and_security": "Biển báo & An ninh",
    "furniture_bedroom": "Nội thất phòng ngủ",
    "books_technical": "Sách kỹ thuật",
    "costruction_tools_tools": "Dụng cụ & Đồ nghề cầm tay",
    "food_drink": "Đồ ăn & Thức uống",
    "fashion_male_clothing": "Thời trang nam",
    "fashion_underwear_beach": "Đồ lót & Đồ bơi",
    "christmas_supplies": "Đồ Giáng sinh",
    "tablets_printing_image": "Máy tính bảng & Máy in",
    "cine_photo": "Phim & Nhiếp ảnh",
    "music": "Âm nhạc",
    "dvds_blu_ray": "Đĩa DVD & Blu-ray",
    "books_imported": "Sách ngoại văn",
    "party_supplies": "Phụ kiện tiệc tùng",
    "furniture_mattress_and_upholstery": "Đệm & Ghế nệm",
    "fashio_female_clothing": "Thời trang nữ",
    "fashion_sport": "Thời trang thể thao",
    "la_cuisine": "Dụng cụ nhà bếp cao cấp",
    "arts_and_craftmanship": "Thủ công mỹ nghệ",
    "diapers_and_hygiene": "Tã bỉm & Vệ sinh",
    "flowers": "Hoa tươi & Cây cảnh",
    "home_comfort_2": "Tiện nghi nhà cửa 2",
    "cds_dvds_musicals": "Đĩa CD & DVD ca nhạc",
    "fashion_childrens_clothes": "Thời trang trẻ em",
    "security_and_services": "Dịch vụ & An ninh",

    # ==========================================================================
    # Bổ sung toàn bộ mã danh mục gốc tiếng Bồ Đào Nha có trong CSDL (products)
    # ==========================================================================
    "agro_industria_e_comercio": "Nông nghiệp & Công thương nghiệp",
    "alimentos": "Thực phẩm",
    "alimentos_bebidas": "Đồ ăn & Thức uống",
    "artes": "Nghệ thuật & Hội họa",
    "artes_e_artesanato": "Thủ công mỹ nghệ",
    "artigos_de_festas": "Phụ kiện tiệc tùng",
    "artigos_de_natal": "Đồ Giáng sinh",
    "automotivo": "Ô tô & Xe máy",
    "bebes": "Mẹ & Bé",
    "bebidas": "Đồ uống",
    "beleza_saude": "Sức khỏe & Làm đẹp",
    "brinquedos": "Đồ chơi",
    "cama_mesa_banho": "Đồ dùng phòng ngủ & phòng tắm",
    "casa_conforto": "Tiện nghi nhà cửa",
    "casa_conforto_2": "Nhà cửa & Tiện nghi 2",
    "casa_construcao": "Vật liệu xây dựng nhà cửa",
    "cds_dvds_musicais": "Đĩa CD & DVD ca nhạc",
    "cine_foto": "Phim & Nhiếp ảnh",
    "climatizacao": "Điều hòa & Máy lạnh",
    "construcao_ferramentas_construcao": "Công cụ xây dựng",
    "construcao_ferramentas_ferramentas": "Dụng cụ xây dựng",
    "construcao_ferramentas_iluminacao": "Thiết bị chiếu sáng xây dựng",
    "construcao_ferramentas_jardim": "Dụng cụ làm vườn & Xây dựng",
    "construcao_ferramentas_seguranca": "Thiết bị bảo hộ lao động",
    "eletrodomesticos": "Thiết bị điện gia đình",
    "eletrodomesticos_2": "Thiết bị gia dụng lớn",
    "eletronicos": "Thiết bị điện tử",
    "eletroportateis": "Thiết bị điện gia dụng nhỏ",
    "esporte_lazer": "Thể thao & Dã ngoại",
    "fashion_bolsas_e_acessorios": "Túi xách & Phụ kiện thời trang",
    "fashion_calcados": "Giày dép",
    "fashion_esporte": "Thời trang thể thao",
    "fashion_roupa_feminina": "Thời trang nữ",
    "fashion_roupa_infanto_juvenil": "Thời trang trẻ em",
    "fashion_roupa_masculina": "Thời trang nam",
    "fashion_underwear_e_moda_praia": "Đồ lót & Đồ đi biển",
    "ferramentas_jardim": "Dụng cụ làm vườn",
    "flores": "Hoa tươi & Cây cảnh",
    "fraldas_higiene": "Tã bỉm & Vệ sinh",
    "industria_comercio_e_negocios": "Công nghiệp & Thương mại",
    "informatica_acessorios": "Máy tính & Phụ kiện",
    "instrumentos_musicais": "Nhạc cụ",
    "livros_importados": "Sách ngoại văn",
    "livros_interesse_geral": "Sách đại chúng",
    "livros_tecnicos": "Sách kỹ thuật",
    "malas_acessorios": "Vali & Phụ kiện du lịch",
    "moveis_colchao_e_estofado": "Đệm & Ghế nệm",
    "moveis_cozinha_area_de_servico_jantar_e_jardim": "Nội thất nhà bếp & Sân vườn",
    "moveis_decoracao": "Nội thất & Trang trí",
    "moveis_escritorio": "Nội thất văn phòng",
    "moveis_quarto": "Nội thất phòng ngủ",
    "moveis_sala": "Nội thất phòng khách",
    "musica": "Âm nhạc",
    "papelaria": "Văn phòng phẩm",
    "pc_gamer": "Máy tính chơi game",
    "pcs": "Máy vi tính",
    "perfumaria": "Nước hoa",
    "portateis_casa_forno_e_cafe": "Lò nướng & Máy pha cà phê",
    "portateis_cozinha_e_preparadores_de_alimentos": "Thiết bị bếp & Chế biến thực phẩm",
    "relogios_presentes": "Đồng hồ & Quà tặng",
    "seguros_e_servicos": "Dịch vụ & An ninh",
    "sinalizacao_e_seguranca": "Biển báo & An ninh",
    "tablets_impressao_imagem": "Máy tính bảng & Máy in",
    "telefonia": "Điện thoại & Thiết bị di động",
    "telefonia_fixa": "Điện thoại cố định",
    "utilidades_domesticas": "Đồ gia dụng",
}

# Thứ tự danh mục theo tổng doanh thu giảm dần từ CSDL thật
CATEGORY_ORDER: List[str] = [
    "health_beauty",
    "watches_gifts",
    "bed_bath_table",
    "sports_leisure",
    "computers_accessories",
    "furniture_decor",
    "cool_stuff",
    "housewares",
    "auto",
    "garden_tools",
    "toys",
    "baby",
    "perfumery",
    "telephony",
    "office_furniture",
    "stationery",
    "computers",
    "pet_shop",
    "musical_instruments",
    "small_appliances",
    "others",
    "electronics",
    "consoles_games",
    "fashion_bags_accessories",
    "construction_tools_construction",
    "luggage_accessories",
    "home_appliances_2",
    "home_construction",
    "home_appliances",
    "agro_industry_and_commerce",
    "furniture_living_room",
    "fixed_telephony",
    "home_confort",
    "air_conditioning",
    "audio",
    "small_appliances_home_oven_and_coffee",
    "books_general_interest",
    "kitchen_dining_laundry_garden_furniture",
    "construction_tools_lights",
    "construction_tools_safety",
    "industry_commerce_and_business",
    "food",
    "market_place",
    "costruction_tools_garden",
    "art",
    "fashion_shoes",
    "drinks",
    "signaling_and_security",
    "furniture_bedroom",
    "books_technical",
    "costruction_tools_tools",
    "food_drink",
    "fashion_male_clothing",
    "fashion_underwear_beach",
    "christmas_supplies",
    "tablets_printing_image",
    "cine_photo",
    "music",
    "dvds_blu_ray",
    "books_imported",
    "party_supplies",
    "furniture_mattress_and_upholstery",
    "fashio_female_clothing",
    "fashion_sport",
    "la_cuisine",
    "arts_and_craftmanship",
    "diapers_and_hygiene",
    "flowers",
    "home_comfort_2",
    "cds_dvds_musicals",
    "fashion_childrens_clothes",
    "security_and_services",
]

# Ánh xạ từ mã Bồ Đào Nha sang Tiếng Anh (nếu DB hoặc code cũ trả về mã Bồ Đào Nha)
PORTUGUESE_TO_ENGLISH: Dict[str, str] = {
    "agro_industria_e_comercio": "agro_industry_and_commerce",
    "alimentos": "food",
    "alimentos_bebidas": "food_drink",
    "artes": "art",
    "artes_e_artesanato": "arts_and_craftmanship",
    "artigos_de_festas": "party_supplies",
    "artigos_de_natal": "christmas_supplies",
    "audio": "audio",
    "automotivo": "auto",
    "bebes": "baby",
    "bebidas": "drinks",
    "beleza_saude": "health_beauty",
    "brinquedos": "toys",
    "calcados": "fashion_shoes",
    "cama_mesa_banho": "bed_bath_table",
    "casa_conforto": "home_confort",
    "casa_conforto_2": "home_comfort_2",
    "casa_construcao": "home_construction",
    "cds_dvds_musicais": "cds_dvds_musicals",
    "cine_foto": "cine_photo",
    "climatizacao": "air_conditioning",
    "consoles_games": "consoles_games",
    "construcao_ferramentas_construcao": "construction_tools_construction",
    "construcao_ferramentas_ferramentas": "costruction_tools_tools",
    "construcao_ferramentas_iluminacao": "construction_tools_lights",
    "construcao_ferramentas_jardim": "costruction_tools_garden",
    "construcao_ferramentas_seguranca": "construction_tools_safety",
    "cool_stuff": "cool_stuff",
    "dvds_blu_ray": "dvds_blu_ray",
    "eletrodomesticos": "home_appliances",
    "eletrodomesticos_2": "home_appliances_2",
    "eletronicos": "electronics",
    "eletroportateis": "small_appliances",
    "esporte_lazer": "sports_leisure",
    "fashion_bolsas_e_acessorios": "fashion_bags_accessories",
    "fashion_calcados": "fashion_shoes",
    "fashion_esporte": "fashion_sport",
    "fashion_roupa_feminina": "fashio_female_clothing",
    "fashion_roupa_infanto_juvenil": "fashion_childrens_clothes",
    "fashion_roupa_intima": "fashion_underwear_beach",
    "fashion_roupa_masculina": "fashion_male_clothing",
    "fashion_underwear_e_moda_praia": "fashion_underwear_beach",
    "ferramentas_ferramentas": "costruction_tools_tools",
    "ferramentas_jardim": "garden_tools",
    "flores": "flowers",
    "fraldas_higiene": "diapers_and_hygiene",
    "industria_comercio_e_negocios": "industry_commerce_and_business",
    "informatica_acessorios": "computers_accessories",
    "instrumentos_musicais": "musical_instruments",
    "la_cuisine": "la_cuisine",
    "livros_importados": "books_imported",
    "livros_interesse_geral": "books_general_interest",
    "livros_tecnicos": "books_technical",
    "malas_acessorios": "luggage_accessories",
    "market_place": "market_place",
    "moveis_colchao_e_estofado": "furniture_mattress_and_upholstery",
    "moveis_cozinha_area_de_servico_jantar_e_jardim": "kitchen_dining_laundry_garden_furniture",
    "moveis_decoracao": "furniture_decor",
    "moveis_escritorio": "office_furniture",
    "moveis_quarto": "furniture_bedroom",
    "moveis_sala": "furniture_living_room",
    "musica": "music",
    "papelaria": "stationery",
    "pc_gamer": "others",
    "pcs": "computers",
    "perfumaria": "perfumery",
    "pet_shop": "pet_shop",
    "portateis_casa_forno_e_cafe": "small_appliances_home_oven_and_coffee",
    "portateis_cozinha_e_preparadores_de_alimentos": "others",
    "relogios_presentes": "watches_gifts",
    "seguros_e_servicos": "security_and_services",
    "sinalizacao_e_seguranca": "signaling_and_security",
    "tablets_impressao_imagem": "tablets_printing_image",
    "telefonia": "telephony",
    "telefonia_fixa": "fixed_telephony",
    "utilidades_domesticas": "housewares",
}


def category_label(code: Any) -> str:
    """
    Chuyển mã danh mục thành nhãn hiển thị tiếng Việt thân thiện.
    Ví dụ: category_label("health_beauty") -> "Sức khỏe & Làm đẹp".
    Nếu mã rỗng hoặc None: trả về "Chưa phân loại".
    Nếu mã chưa được định nghĩa trong CATEGORY_VI:
    Fallback về 'Khác (<mã>)' để dễ phát hiện, không title-case tiếng Bồ.
    """
    if code is None:
        return "Chưa phân loại"
    code_str = str(code).strip()
    if not code_str or code_str.lower() in ("nan", "none", "null"):
        return "Chưa phân loại"

    # 1. Tìm trực tiếp trong từ điển tiếng Việt
    if code_str in CATEGORY_VI:
        return CATEGORY_VI[code_str]

    # 2. Nếu là mã tiếng Bồ Đào Nha, tra qua mã tiếng Anh tương ứng
    if code_str in PORTUGUESE_TO_ENGLISH:
        en_code = PORTUGUESE_TO_ENGLISH[code_str]
        if en_code in CATEGORY_VI:
            return CATEGORY_VI[en_code]

    # 3. Fallback: mã chưa dịch hiện "Khác (<mã>)" để dễ phát hiện
    return f"Khác ({code_str})"


# ==============================================================================
# 3. ĐỊNH DẠNG GIÁ TRỊ VÀ DELTA KPI (THEO CHUẨN TIẾNG VIỆT)
# ==============================================================================

def format_kpi_value(metric_key: str, value: Any) -> str:
    """
    Định dạng giá trị hiển thị cho thẻ KPI:
    - Số tiền >= 1 triệu: 'R$ 15,4 triệu' (dùng dấu phẩy theo tiếng Việt)
    - Điểm đánh giá: '4,16' (2 chữ số thập phân)
    - Tỷ lệ đúng hạn: '93,2%' (1 chữ số thập phân)
    - AOV: 'R$ 159,8'
    - Số đơn / khách: định dạng số nguyên phân cách dấu phẩy (ví dụ 96,211)
    """
    if value is None:
        return "—"
    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return str(value)

    if metric_key in ("total_revenue", "revenue"):
        if val_float >= 1_000_000:
            return f"R$ {val_float / 1_000_000:.1f} triệu".replace(".", ",")
        return f"R$ {val_float:,.0f}"

    if metric_key in ("avg_review_score", "review_score", "score"):
        return f"{val_float:.2f}".replace(".", ",")

    if metric_key in ("on_time_rate", "ontime_rate", "ontime"):
        return f"{val_float:.1f}%".replace(".", ",")

    if metric_key in ("avg_order_value", "aov"):
        return f"R$ {val_float:.1f}".replace(".", ",")

    if metric_key in ("total_orders", "orders", "total_customers", "customers"):
        return f"{int(val_float):,}"

    return str(value)


def format_currency_full(value: Any) -> str:
    """Định dạng số tiền đầy đủ theo chuẩn Việt Nam/Brazil (ví dụ: R$ 15.329.289,43)."""
    if value is None:
        return "—"
    try:
        val_float = float(value)
    except (ValueError, TypeError):
        return str(value)
    formatted = f"{val_float:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {formatted}"


def format_kpi_delta(
    metric_key: str,
    curr_val: Any,
    prev_val: Any,
    is_valid_prev: bool = True,
) -> str:
    """
    Định dạng delta cho thẻ KPI:
    - Không đủ dữ liệu hoặc không có kỳ trước hợp lệ -> trả về '—'
    - Kỳ trước = 0 -> trả về '—'
    - Doanh thu, Đơn hàng, Khách hàng, AOV: hiển thị theo % (ví dụ '+12,4%', '-5,2%')
    - Điểm đánh giá: hiển thị theo điểm tuyệt đối (ví dụ '+0,15', '-0,20')
    - Tỷ lệ đúng hạn: hiển thị theo điểm phần trăm (ví dụ '+2,3 %p', '-3,5 %p')
    """
    if not is_valid_prev or curr_val is None or prev_val is None:
        return "—"

    try:
        c = float(curr_val)
        p = float(prev_val)
    except (ValueError, TypeError):
        return "—"

    if p == 0:
        return "—"

    # 1. Điểm đánh giá: Điểm tuyệt đối (2 chữ số thập phân)
    if metric_key in ("avg_review_score", "review_score", "score"):
        diff = c - p
        return f"{diff:+.2f}".replace(".", ",")

    # 2. Tỷ lệ đúng hạn: Điểm phần trăm (ví dụ '+2,3 %p')
    if metric_key in ("on_time_rate", "ontime_rate", "ontime"):
        diff = c - p
        return f"{diff:+.1f} %p".replace(".", ",")

    # 3. Doanh thu, đơn hàng, khách hàng, AOV: Tính theo %
    pct = ((c - p) / p) * 100.0
    return f"{pct:+.1f}%".replace(".", ",")


def check_prev_period_valid(filters: Optional[dict], kpi_prev: Any) -> bool:
    """
    Kiểm tra xem kỳ trước có hợp lệ để so sánh delta không:
    1. Kỳ trước phải nằm trọn trong khoảng dữ liệu từ 2017-01-01 trở đi.
    2. Kỳ trước phải có >= 100 đơn hàng.
    """
    if filters is None or kpi_prev is None:
        return False
    if hasattr(kpi_prev, "empty") and kpi_prev.empty:
        return False

    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    if not start_date or not end_date:
        return False

    try:
        import pandas as pd
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
    except Exception:
        return False

    delta_days = (end_dt - start_dt).days
    if delta_days < 0:
        return False

    prev_end_dt = start_dt - pd.Timedelta(days=1)
    prev_start_dt = prev_end_dt - pd.Timedelta(days=delta_days)

    # Phải nằm trọn trong khoảng dữ liệu từ 2017-01-01
    data_min_dt = pd.to_datetime("2017-01-01")
    if prev_start_dt < data_min_dt:
        return False

    # Phải có ít nhất 100 đơn hàng
    try:
        if hasattr(kpi_prev, "get"):
            prev_orders = int(kpi_prev.get("total_orders", 0))
        else:
            prev_orders = int(kpi_prev["total_orders"])
    except (ValueError, TypeError, KeyError):
        return False

    if prev_orders < 100:
        return False

    return True

