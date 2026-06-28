# crawler/muasamcong_api.py
# Gọi API muasamcong.mpi.gov.vn để lấy danh sách gói thầu
# Dựa trên phân tích repo github.com/anhpdv/muasamcong

import requests
import time
import logging
from datetime import date
from typing import Optional
from config import BASE_URL, SEARCH_ENDPOINT, PAGE_SIZE, MAX_PAGES

logger = logging.getLogger(__name__)

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": f"{BASE_URL}/web/guest/home",
    "Origin": BASE_URL,
}


def build_payload(
    prov_code: str,
    invest_fields: list[str],
    page: int = 1,
    page_size: int = PAGE_SIZE,
    only_today: bool = True,
) -> dict:
    """
    Xây dựng payload POST cho API muasamcong.
    Tương đương với filter trong config.json của repo anhpdv.
    """
    today = date.today().strftime("%d/%m/%Y")
    payload = {
        "pageNumber": page,
        "pageSize": page_size,
        "sortBy": "publicDate",
        "sortType": "DESC",
        "provCodes": prov_code,
        "investFields": ",".join(invest_fields),
    }
    if only_today:
        payload["publicDateFrom"] = today
        payload["publicDateTo"] = today
    return payload


def fetch_page(
    prov_code: str,
    invest_fields: list[str],
    page: int,
    session: requests.Session,
    only_today: bool = True,
) -> Optional[dict]:
    """Lấy 1 trang kết quả từ API."""
    url = BASE_URL + SEARCH_ENDPOINT
    payload = build_payload(prov_code, invest_fields, page, PAGE_SIZE, only_today)

    try:
        resp = session.post(url, data=payload, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP {e.response.status_code} khi lấy trang {page} tỉnh {prov_code}")
        return None
    except requests.exceptions.SSLError as e:
        logger.error(f"Lỗi SSL khi kết nối muasamcong (trang {page}, tỉnh {prov_code}): {e}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout khi kết nối muasamcong (trang {page}, tỉnh {prov_code}): {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Không kết nối được muasamcong.mpi.gov.vn (trang {page}, tỉnh {prov_code}): {e}")
        return None
    except Exception as e:
        logger.error(f"Lỗi không xác định (trang {page}, tỉnh {prov_code}): {type(e).__name__}: {e}")
        return None


def fetch_tenders_for_province(
    prov_code: str,
    prov_name: str,
    invest_fields: list[str],
    only_today: bool = True,
    max_pages: int = MAX_PAGES,
) -> list[dict]:
    """
    Lấy toàn bộ gói thầu của 1 tỉnh (phân trang tự động).
    Trả về list các gói thầu đã chuẩn hóa.
    """
    all_tenders = []
    session = requests.Session()

    logger.info(f"📡 Đang crawl tỉnh {prov_name} (mã {prov_code})...")

    for page in range(1, max_pages + 1):
        data = fetch_page(prov_code, invest_fields, page, session, only_today)

        if not data:
            break

        # API muasamcong trả về dạng {"data": {"items": [...], "total": N}}
        items = (
            data.get("data", {}).get("items")
            or data.get("items")
            or data.get("result", {}).get("items")
            or []
        )

        if not items:
            logger.info(f"  Hết dữ liệu ở trang {page}")
            break

        for item in items:
            tender = normalize_tender(item, prov_name, prov_code)
            all_tenders.append(tender)

        logger.info(f"  Trang {page}: {len(items)} gói → tổng {len(all_tenders)}")

        # Nếu ít hơn pageSize thì đã hết
        if len(items) < PAGE_SIZE:
            break

        time.sleep(1.5)  # Tránh spam server

    return all_tenders


def normalize_tender(raw: dict, prov_name: str, prov_code: str) -> dict:
    """
    Chuẩn hóa 1 record gói thầu thành format thống nhất
    để ghi vào Google Sheets.
    """
    # Lấy giá trị gói thầu (đơn vị: đồng → chuyển sang triệu)
    raw_value = raw.get("contractValue") or raw.get("estimatedValue") or 0
    try:
        value_million = round(float(raw_value) / 1_000_000, 1)
    except (ValueError, TypeError):
        value_million = 0

    return {
        "id":            raw.get("noticeId") or raw.get("id") or "",
        "ten_goi_thau":  raw.get("tenderTitle") or raw.get("name") or "",
        "chu_dau_tu":    raw.get("procuringEntity") or raw.get("ownerName") or "",
        "tinh":          prov_name,
        "ma_tinh":       prov_code,
        "linh_vuc":      raw.get("investField") or raw.get("tenderType") or "",
        "hinh_thuc":     raw.get("procurementMethod") or "",
        "gia_tri_trieu": value_million,
        "ngay_dang":     raw.get("publicDate") or raw.get("publishDate") or "",
        "han_nop_ho_so": raw.get("submissionDeadline") or raw.get("closingDate") or "",
        "trang_thai":    raw.get("tenderStatus") or raw.get("status") or "",
        "link":          f"{BASE_URL}/web/guest/tim-kiem-nha-thau?noticeId={raw.get('noticeId', '')}",
        "nguon":         "muasamcong.mpi.gov.vn",
    }
