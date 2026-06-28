# 🎯 Radar Khách Hàng — Hướng dẫn Setup

## Kiến trúc hệ thống

```
muasamcong.mpi.gov.vn  →  GitHub Actions (crawl 3x/ngày)
                                    ↓
                           Google Sheets (lưu trữ)
                                    ↓
                           Streamlit Cloud (giao diện RM)
                                    ↑
                           Claude API (phân tích leads)
```

---

## BƯỚC 1 — Chuẩn bị Google Sheets

1. Tạo Google Sheet mới, đặt tên: **"Radar Khách Hàng - VietinBank"**
2. Copy **Sheet ID** từ URL:
   `https://docs.google.com/spreadsheets/d/**[SHEET_ID_Ở_ĐÂY]**/edit`

---

## BƯỚC 2 — Tạo Service Account (Google)

1. Vào [console.cloud.google.com](https://console.cloud.google.com)
2. Tạo project mới hoặc chọn project có sẵn
3. Bật API: **Google Sheets API** + **Google Drive API**
4. **IAM & Admin → Service Accounts → Create Service Account**
   - Tên: `radar-vietinbank`
5. **Tạo Key JSON** → Tải về → Giữ bảo mật
6. Copy email service account (dạng `...@...gserviceaccount.com`)
7. **Vào Google Sheet → Share → Paste email service account → Editor**

---

## BƯỚC 3 — Push code lên GitHub

```bash
# Clone hoặc tạo repo mới
git init radar-khachhang-vietinbank
cd radar-khachhang-vietinbank

# Copy toàn bộ file vào đây, sau đó:
git add .
git commit -m "feat: Radar Khách Hàng initial setup"
git remote add origin https://github.com/[USERNAME]/radar-khachhang-vietinbank.git
git push -u origin main
```

---

## BƯỚC 4 — Cấu hình GitHub Secrets

Vào repo GitHub → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Giá trị |
|---|---|
| `GOOGLE_CREDENTIALS_JSON` | Toàn bộ nội dung file JSON service account (copy & paste) |
| `SHEET_ID` | ID của Google Sheet (bước 1) |
| `CLAUDE_API_KEY` | API key từ console.anthropic.com (tùy chọn) |

---

## BƯỚC 5 — Chỉnh tỉnh theo dõi

Mở file `crawler/config.py`, sửa `PROV_TARGETS`:

```python
PROV_TARGETS = [
    {"code": "31", "name": "Thành phố Hải Phòng"},   # ← ưu tiên
    {"code": "14", "name": "Tỉnh Quảng Ninh"},
    {"code": "30", "name": "Tỉnh Hải Dương"},
    # Thêm tỉnh khác theo nhu cầu...
]
```

**Mã tỉnh thường dùng:**
- 31 = Hải Phòng | 14 = Quảng Ninh | 30 = Hải Dương
- 22 = Bắc Ninh | 27 = Hưng Yên | 35 = Thái Bình
- 01 = Hà Nội | 79 = TP.HCM

---

## BƯỚC 6 — Deploy Streamlit Cloud

1. Vào [share.streamlit.io](https://share.streamlit.io) → **New app**
2. Chọn repo GitHub của bạn, file: `streamlit_app.py`
3. Vào **Advanced settings → Secrets**, thêm:

```toml
SHEET_ID = "your_sheet_id_here"

[google_credentials]
type = "service_account"
project_id = "your_project_id"
private_key_id = "..."
private_key = "-----BEGIN RSA PRIVATE KEY-----\n..."
client_email = "radar-vietinbank@....gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
```

*(Copy từng trường trong file JSON service account)*

---

## BƯỚC 7 — Chạy thử lần đầu

```bash
# Test local trước khi push
export GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'
export SHEET_ID='your_sheet_id'
export CLAUDE_API_KEY='sk-ant-...'  # Tùy chọn

pip install -r requirements.txt
python crawler/main.py
```

Hoặc trigger thủ công trên GitHub:
**Actions → Radar Khách Hàng → Run workflow**

---

## Cấu trúc Google Sheets sau khi chạy

| Sheet | Nội dung |
|---|---|
| **RAW_DATA** | Toàn bộ gói thầu crawl được |
| **LEADS** | Gói thầu được Claude chấm điểm cao |
| **LOG** | Lịch sử các lần crawl |

---

## Lịch tự động

| Giờ (VN) | Cron UTC |
|---|---|
| 08:00 | `0 1 * * *` |
| 12:00 | `0 5 * * *` |
| 17:00 | `0 10 * * *` |

---

## Câu hỏi thường gặp

**Q: API muasamcong có cần đăng nhập không?**
A: Endpoint search là public, không cần auth cho việc xem danh sách gói thầu.

**Q: Nếu muasamcong thay đổi API?**
A: Sửa `BASE_URL` và `SEARCH_ENDPOINT` trong `config.py`. Kiểm tra lại tên field trong `normalize_tender()`.

**Q: Claude API có tốn tiền không?**
A: Mỗi lần chạy phân tích ~20-50 gói × ~200 tokens = ~10,000 tokens ≈ $0.03. Rất rẻ.

**Q: Nếu không có CLAUDE_API_KEY?**
A: Hệ thống vẫn chạy bình thường, chỉ bỏ qua bước phân tích, sheet LEADS sẽ trống.
