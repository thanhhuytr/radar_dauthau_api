# crawler/main.py — Điểm vào chính, chạy bởi GitHub Actions
# Luồng: Crawl API → Lọc leads → Claude phân tích → Ghi Google Sheets

import os
import logging
import sys

# Thêm thư mục hiện tại vào path để import được các module cùng cấp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PROV_TARGETS, INVEST_FIELDS
from muasamcong_api import fetch_tenders_for_province
from sheets_writer import write_tenders, write_log
from claude_analyzer import filter_and_analyze

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_active_provinces() -> list[dict]:
    """
    Lấy danh sách tỉnh cần crawl.
    Ưu tiên biến môi trường PROV_CODES_OVERRIDE (dùng khi chạy thủ công).
    """
    override = os.environ.get("PROV_CODES_OVERRIDE", "").strip()
    if override:
        codes = [c.strip() for c in override.split(",")]
        # Lọc từ PROV_TARGETS hoặc dùng code thô nếu không có tên
        result = []
        for code in codes:
            match = next((p for p in PROV_TARGETS if p["code"] == code), None)
            result.append(match or {"code": code, "name": f"Tỉnh mã {code}"})
        logger.info(f"🎯 Override: crawl {len(result)} tỉnh từ tham số thủ công")
        return result
    return PROV_TARGETS


def main():
    sheet_id = os.environ.get("SHEET_ID")
    if not sheet_id:
        logger.error("❌ Thiếu biến môi trường SHEET_ID")
        sys.exit(1)

    provinces = get_active_provinces()
    all_tenders = []

    # ── Bước 1: Crawl tất cả tỉnh ────────────────────────────────
    logger.info(f"🚀 Bắt đầu crawl {len(provinces)} tỉnh...")
    for prov in provinces:
        tenders = fetch_tenders_for_province(
            prov_code=prov["code"],
            prov_name=prov["name"],
            invest_fields=INVEST_FIELDS,
            only_today=True,
        )
        all_tenders.extend(tenders)

    logger.info(f"📦 Tổng crawl được: {len(all_tenders)} gói thầu")

    if not all_tenders:
        logger.info("ℹ️ Không có gói thầu mới hôm nay.")
        write_log(sheet_id, {"total_crawled": 0, "new": 0, "skipped": 0}, provinces)
        return

    # ── Bước 2: Ghi RAW DATA vào Sheets ──────────────────────────
    write_stats = write_tenders(all_tenders, sheet_id)
    logger.info(f"📊 Sheets: {write_stats['new']} mới, {write_stats['skipped']} trùng")

    # ── Bước 3: Claude phân tích leads (nếu có API key) ──────────
    if os.environ.get("CLAUDE_API_KEY"):
        leads = filter_and_analyze(all_tenders)
        if leads:
            logger.info(f"🎯 Tìm được {len(leads)} leads tiềm năng (điểm >= 5)")
            high_value_leads = [l for l in leads if l.get("diem_tiem_nang", 0) >= 5]
            write_leads(high_value_leads, sheet_id)
    else:
        logger.info("⏭️ Bỏ qua phân tích Claude (chưa cấu hình CLAUDE_API_KEY)")

    # ── Bước 4: Ghi log ──────────────────────────────────────────
    stats = {**write_stats, "total_crawled": len(all_tenders)}
    write_log(sheet_id, stats, provinces)
    logger.info("✅ Hoàn tất!")


def write_leads(leads: list[dict], sheet_id: str):
    """Ghi leads đã phân tích vào sheet LEADS."""
    from sheets_writer import get_sheet_client, ensure_sheet

    LEADS_HEADERS = [
        "ID", "Tên gói thầu", "Chủ đầu tư", "Tỉnh", "Lĩnh vực",
        "Giá trị (triệu)", "Ngày đăng", "Hạn nộp",
        "⭐ Điểm tiềm năng", "Sản phẩm phù hợp", "Gợi ý tiếp cận", "Link",
    ]
    spreadsheet = get_sheet_client(sheet_id)
    ws = ensure_sheet(spreadsheet, "LEADS", LEADS_HEADERS)

    rows = []
    for l in leads:
        rows.append([
            l.get("id", ""),
            l.get("ten_goi_thau", ""),
            l.get("chu_dau_tu", ""),
            l.get("tinh", ""),
            l.get("linh_vuc", ""),
            l.get("gia_tri_trieu", ""),
            l.get("ngay_dang", ""),
            l.get("han_nop_ho_so", ""),
            l.get("diem_tiem_nang", ""),
            ", ".join(l.get("loai_san_pham", [])),
            l.get("goi_y_tiep_can", ""),
            l.get("link", ""),
        ])

    if rows:
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        logger.info(f"🎯 Đã ghi {len(rows)} leads vào sheet LEADS")


if __name__ == "__main__":
    main()
