# config.py — Cấu hình cho Radar Khách Hàng VietinBank Hải Phòng
# Chỉnh sửa PROV_TARGETS để theo dõi các tỉnh mong muốn

# ---------------------------------------------------------------
# DANH SÁCH TỈNH THEO DÕI
# Mã tỉnh lấy từ muasamcong.mpi.gov.vn (2 chữ số)
# ---------------------------------------------------------------
PROV_TARGETS = [
    {"code": "31", "name": "Thành phố Hải Phòng"},
    {"code": "14", "name": "Tỉnh Quảng Ninh"},
    {"code": "30", "name": "Tỉnh Hải Dương"},
    {"code": "22", "name": "Tỉnh Bắc Ninh"},
    {"code": "35", "name": "Tỉnh Thái Bình"},
]

# ---------------------------------------------------------------
# BỘ LỌC LĨNH VỰC ĐẦU TƯ
# HH = Hàng hóa | PT = Phi tư vấn | TV = Tư vấn | XL = Xây lắp
# ---------------------------------------------------------------
INVEST_FIELDS = ["HH", "PT", "TV", "XL"]

# ---------------------------------------------------------------
# API MUASAMCONG
# ---------------------------------------------------------------
BASE_URL = "https://muasamcong.mpi.gov.vn"
SEARCH_ENDPOINT = "/o/egp-portal-home/services/smart/search"
PAGE_SIZE = 10
MAX_PAGES = 5       # Tối đa 50 gói/tỉnh/lần chạy

# ---------------------------------------------------------------
# GOOGLE SHEETS
# ---------------------------------------------------------------
SHEET_NAME_DATA   = "RAW_DATA"      # Sheet chứa dữ liệu thô
SHEET_NAME_LEADS  = "LEADS"         # Sheet RM theo dõi
SHEET_NAME_LOG    = "LOG"           # Sheet log lịch sử chạy

# ---------------------------------------------------------------
# NGƯỠNG LỌC LEAD CHO CLAUDE PHÂN TÍCH
# ---------------------------------------------------------------
MIN_VALUE_BILLION = 0.5   # Chỉ phân tích gói >= 500 triệu VND
PRIORITY_FIELDS   = ["HH", "XL"]  # Ưu tiên hàng hóa & xây lắp
