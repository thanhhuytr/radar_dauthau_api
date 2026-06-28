# crawler/claude_analyzer.py
# Dùng Claude API để phân tích & chấm điểm tiềm năng lead ngân hàng
# Chỉ gọi cho các gói thầu đủ lớn (>= MIN_VALUE_BILLION tỷ)

import os
import anthropic
import logging
from config import MIN_VALUE_BILLION, PRIORITY_FIELDS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là chuyên gia phân tích tín dụng doanh nghiệp của VietinBank.
Nhiệm vụ: phân tích gói thầu đấu thầu/mua sắm công để đánh giá tiềm năng cấp tín dụng.

Với mỗi gói thầu, hãy xác định:
1. ĐIỂM TIỀM NĂNG (1-10): khả năng chủ đầu tư/nhà thầu cần vay vốn/bảo lãnh ngân hàng
2. LOẠI SẢN PHẨM phù hợp: Bảo lãnh dự thầu / Bảo lãnh thực hiện HĐ / Tín dụng đầu tư / LC nhập khẩu
3. GỢI Ý TIẾP CẬN: 1-2 câu ngắn gọn cho RM

Trả về JSON (không có markdown):
{
  "diem_tiem_nang": <số 1-10>,
  "loai_san_pham": ["..."],
  "goi_y_tiep_can": "...",
  "ly_do": "..."
}"""


def analyze_tender(tender: dict) -> dict:
    """Phân tích 1 gói thầu bằng Claude, trả về dict với các trường phân tích."""
    client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))

    prompt = f"""Phân tích gói thầu sau:
- Tên: {tender.get('ten_goi_thau')}
- Chủ đầu tư: {tender.get('chu_dau_tu')}
- Tỉnh: {tender.get('tinh')}
- Lĩnh vực: {tender.get('linh_vuc')}
- Hình thức: {tender.get('hinh_thuc')}
- Giá trị: {tender.get('gia_tri_trieu')} triệu VND
- Hạn nộp: {tender.get('han_nop_ho_so')}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        result = json.loads(message.content[0].text)
        return result
    except Exception as e:
        logger.warning(f"Claude API lỗi cho gói '{tender.get('ten_goi_thau')}': {e}")
        return {
            "diem_tiem_nang": 0,
            "loai_san_pham": [],
            "goi_y_tiep_can": "",
            "ly_do": f"Lỗi phân tích: {str(e)[:100]}",
        }


def filter_and_analyze(tenders: list[dict]) -> list[dict]:
    """
    Lọc gói thầu đủ lớn → gọi Claude phân tích → gắn kết quả vào record.
    Trả về danh sách LEADS (có thêm các trường phân tích).
    """
    leads = []
    threshold = MIN_VALUE_BILLION * 1000  # Chuyển tỷ → triệu

    eligible = [
        t for t in tenders
        if float(t.get("gia_tri_trieu") or 0) >= threshold
    ]
    logger.info(f"🤖 Claude sẽ phân tích {len(eligible)}/{len(tenders)} gói đủ ngưỡng")

    for t in eligible:
        analysis = analyze_tender(t)
        lead = {**t, **analysis}
        leads.append(lead)
        logger.info(
            f"  ⭐ {analysis.get('diem_tiem_nang', '?')}/10 — {t.get('ten_goi_thau', '')[:50]}"
        )

    # Sắp xếp theo điểm tiềm năng giảm dần
    leads.sort(key=lambda x: x.get("diem_tiem_nang", 0), reverse=True)
    return leads
