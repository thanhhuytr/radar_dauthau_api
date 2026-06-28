# crawler/sheets_writer.py
# Ghi dữ liệu gói thầu vào Google Sheets
# Dùng Service Account (phù hợp với GitHub Actions)

import os
import json
import logging
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from .config import SHEET_NAME_DATA, SHEET_NAME_LOG

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Header cho sheet RAW_DATA — phải khớp với normalize_tender()
RAW_HEADERS = [
    "ID", "Tên gói thầu", "Chủ đầu tư", "Tỉnh/Thành", "Mã tỉnh",
    "Lĩnh vực", "Hình thức", "Giá trị (triệu VND)",
    "Ngày đăng", "Hạn nộp hồ sơ", "Trạng thái", "Link", "Nguồn",
    "Thời gian crawl",
]

# Thứ tự field tương ứng với RAW_HEADERS
RAW_FIELDS = [
    "id", "ten_goi_thau", "chu_dau_tu", "tinh", "ma_tinh",
    "linh_vuc", "hinh_thuc", "gia_tri_trieu",
    "ngay_dang", "han_nop_ho_so", "trang_thai", "link", "nguon",
]


def get_sheet_client(sheet_id: str) -> gspread.Spreadsheet:
    """Kết nối Google Sheets qua Service Account."""
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("Thiếu biến môi trường GOOGLE_CREDENTIALS_JSON")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(sheet_id)


def ensure_sheet(spreadsheet: gspread.Spreadsheet, name: str, headers: list) -> gspread.Worksheet:
    """Tạo sheet nếu chưa có, thêm header nếu trống."""
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=5000, cols=len(headers))
        logger.info(f"Đã tạo sheet mới: {name}")

    # Kiểm tra header
    existing = ws.row_values(1)
    if not existing:
        ws.insert_row(headers, index=1)
        # Format header: bold + màu nền
        ws.format("1:1", {
            "backgroundColor": {"red": 0.18, "green": 0.38, "blue": 0.62},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER",
        })
        logger.info(f"Đã thêm header cho sheet: {name}")

    return ws


def get_existing_ids(ws: gspread.Worksheet) -> set:
    """Lấy tất cả ID đã có trong sheet để tránh ghi trùng."""
    try:
        col_a = ws.col_values(1)  # Cột ID
        return set(col_a[1:])     # Bỏ qua header
    except Exception:
        return set()


def write_tenders(tenders: list[dict], sheet_id: str) -> dict:
    """
    Ghi danh sách gói thầu vào Google Sheets.
    - Bỏ qua record đã tồn tại (dedup theo ID)
    - Trả về thống kê: mới / bỏ qua / lỗi
    """
    if not tenders:
        return {"new": 0, "skipped": 0, "error": 0}

    spreadsheet = get_sheet_client(sheet_id)
    ws = ensure_sheet(spreadsheet, SHEET_NAME_DATA, RAW_HEADERS)
    existing_ids = get_existing_ids(ws)

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    rows_to_add = []
    skipped = 0

    for t in tenders:
        tid = str(t.get("id", ""))
        if tid and tid in existing_ids:
            skipped += 1
            continue

        row = [str(t.get(f, "")) for f in RAW_FIELDS] + [now_str]
        rows_to_add.append(row)
        if tid:
            existing_ids.add(tid)

    if rows_to_add:
        ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
        logger.info(f"✅ Đã ghi {len(rows_to_add)} gói mới vào sheet {SHEET_NAME_DATA}")

    return {"new": len(rows_to_add), "skipped": skipped, "error": 0}


def write_log(sheet_id: str, stats: dict, provinces: list):
    """Ghi log lịch sử vào sheet LOG."""
    spreadsheet = get_sheet_client(sheet_id)
    log_headers = [
        "Thời gian", "Tỉnh theo dõi", "Tổng crawl",
        "Gói mới", "Bỏ qua (trùng)", "Trạng thái",
    ]
    ws = ensure_sheet(spreadsheet, SHEET_NAME_LOG, log_headers)

    prov_names = ", ".join(p["name"] for p in provinces)
    row = [
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        prov_names,
        stats.get("total_crawled", 0),
        stats.get("new", 0),
        stats.get("skipped", 0),
        "✅ Thành công" if stats.get("error", 0) == 0 else "⚠️ Có lỗi",
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
