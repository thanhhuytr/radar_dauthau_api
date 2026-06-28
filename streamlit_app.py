# streamlit_app.py — Giao diện Radar Khách Hàng cho VietinBank
# Deploy lên Streamlit Cloud, kết nối Google Sheets để đọc dữ liệu

import streamlit as st
import gspread
import json
import os
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime, date

# ── Cấu hình trang ───────────────────────────────────────────────
st.set_page_config(
    page_title="Radar Khách Hàng | VietinBank",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS tùy chỉnh ────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a3a6b 0%, #c8161d 100%);
        padding: 1.2rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .metric-card {
        background: #f8f9fa;
        border-left: 4px solid #1a3a6b;
        padding: 1rem;
        border-radius: 8px;
    }
    .lead-high { background-color: #fff3cd; border-left: 4px solid #ffc107; }
    .lead-med  { background-color: #d1ecf1; border-left: 4px solid #17a2b8; }
    .badge-score {
        display: inline-block;
        padding: 0.2em 0.6em;
        border-radius: 12px;
        font-weight: bold;
        font-size: 1.1em;
    }
</style>
""", unsafe_allow_html=True)


# ── Kết nối Google Sheets ────────────────────────────────────────
@st.cache_resource(ttl=300)  # Cache 5 phút
def get_spreadsheet():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    # Ưu tiên Streamlit Secrets, fallback sang biến môi trường
    try:
        creds_dict = dict(st.secrets["google_credentials"])
        sheet_id = st.secrets["SHEET_ID"]
    except Exception:
        creds_dict = json.loads(os.environ.get("GOOGLE_CREDENTIALS_JSON", "{}"))
        sheet_id = os.environ.get("SHEET_ID", "")

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(sheet_id)


@st.cache_data(ttl=300)
def load_data(sheet_name: str) -> pd.DataFrame:
    """Đọc dữ liệu từ 1 sheet, cache 5 phút."""
    try:
        spreadsheet = get_spreadsheet()
        ws = spreadsheet.worksheet(sheet_name)
        records = ws.get_all_records()
        return pd.DataFrame(records)
    except gspread.WorksheetNotFound:
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Lỗi đọc sheet {sheet_name}: {e}")
        return pd.DataFrame()


# ── Header ───────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1 style="margin:0; font-size: 1.8rem;">🎯 Radar Khách Hàng Đấu Thầu</h1>
    <p style="margin:0.3rem 0 0; opacity:0.85;">VietinBank — Chi nhánh Hải Phòng | Nguồn: muasamcong.mpi.gov.vn</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar lọc ─────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/VietinBank.svg/200px-VietinBank.svg.png", width=140)
    st.markdown("### ⚙️ Bộ lọc")

    view_mode = st.radio("Xem dữ liệu:", ["📋 Tất cả gói thầu", "⭐ Leads tiềm năng", "📊 Thống kê"])

    st.markdown("---")
    st.markdown("**🔄 Dữ liệu tự động cập nhật:**")
    st.markdown("- 08:00 sáng\n- 12:00 trưa\n- 17:00 chiều")
    st.markdown("---")

    if st.button("🔃 Làm mới dữ liệu", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── Nội dung chính ───────────────────────────────────────────────
if view_mode == "📋 Tất cả gói thầu":
    df = load_data("RAW_DATA")

    if df.empty:
        st.info("📭 Chưa có dữ liệu. Chờ GitHub Actions chạy lần đầu.")
    else:
        # Metrics tổng quan
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Tổng gói thầu", f"{len(df):,}")
        with col2:
            today = date.today().strftime("%d/%m/%Y")
            today_count = df[df.get("Ngày đăng", pd.Series(dtype=str)).str.contains(today, na=False)].shape[0] if "Ngày đăng" in df.columns else 0
            st.metric("Hôm nay", f"{today_count:,}")
        with col3:
            if "Giá trị (triệu VND)" in df.columns:
                total_val = pd.to_numeric(df["Giá trị (triệu VND)"], errors="coerce").sum()
                st.metric("Tổng giá trị", f"{total_val/1000:,.0f} tỷ")
        with col4:
            if "Tỉnh/Thành" in df.columns:
                st.metric("Số tỉnh", df["Tỉnh/Thành"].nunique())

        st.markdown("---")

        # Bộ lọc động
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            if "Tỉnh/Thành" in df.columns:
                tinh_opts = ["Tất cả"] + sorted(df["Tỉnh/Thành"].dropna().unique().tolist())
                selected_tinh = st.selectbox("Tỉnh/Thành", tinh_opts)
        with fcol2:
            if "Lĩnh vực" in df.columns:
                lv_opts = ["Tất cả"] + sorted(df["Lĩnh vực"].dropna().unique().tolist())
                selected_lv = st.selectbox("Lĩnh vực", lv_opts)
        with fcol3:
            search_kw = st.text_input("🔍 Tìm theo tên/chủ đầu tư", placeholder="Nhập từ khóa...")

        # Áp dụng lọc
        filtered = df.copy()
        if "Tỉnh/Thành" in df.columns and selected_tinh != "Tất cả":
            filtered = filtered[filtered["Tỉnh/Thành"] == selected_tinh]
        if "Lĩnh vực" in df.columns and selected_lv != "Tất cả":
            filtered = filtered[filtered["Lĩnh vực"] == selected_lv]
        if search_kw:
            mask = (
                filtered.get("Tên gói thầu", pd.Series()).str.contains(search_kw, case=False, na=False) |
                filtered.get("Chủ đầu tư", pd.Series()).str.contains(search_kw, case=False, na=False)
            )
            filtered = filtered[mask]

        st.markdown(f"**Kết quả: {len(filtered):,} gói thầu**")

        # Hiển thị bảng (ẩn cột không cần thiết)
        display_cols = [c for c in ["Tên gói thầu", "Chủ đầu tư", "Tỉnh/Thành", "Lĩnh vực",
                                     "Giá trị (triệu VND)", "Ngày đăng", "Hạn nộp hồ sơ", "Link"]
                        if c in filtered.columns]
        st.dataframe(
            filtered[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Link": st.column_config.LinkColumn("Link", display_text="🔗 Xem"),
                "Giá trị (triệu VND)": st.column_config.NumberColumn(format="%.0f triệu"),
            }
        )

elif view_mode == "⭐ Leads tiềm năng":
    df = load_data("LEADS")

    if df.empty:
        st.info("📭 Chưa có leads. Claude sẽ phân tích sau khi crawl.")
    else:
        st.markdown(f"### 🎯 {len(df)} leads tiềm năng được Claude phân tích")

        min_score = st.slider("Điểm tiềm năng tối thiểu", 1, 10, 6)
        if "⭐ Điểm tiềm năng" in df.columns:
            df_filtered = df[pd.to_numeric(df["⭐ Điểm tiềm năng"], errors="coerce") >= min_score]
        else:
            df_filtered = df

        for _, row in df_filtered.iterrows():
            score = int(row.get("⭐ Điểm tiềm năng", 0) or 0)
            color = "🔴" if score >= 8 else "🟡" if score >= 6 else "🟢"
            with st.expander(f"{color} [{score}/10] {row.get('Tên gói thầu', '')[:80]}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Chủ đầu tư:** {row.get('Chủ đầu tư', '')}")
                    st.markdown(f"**Tỉnh:** {row.get('Tỉnh', '')}")
                    st.markdown(f"**Giá trị:** {row.get('Giá trị (triệu)', '')} triệu VND")
                with c2:
                    st.markdown(f"**Ngày đăng:** {row.get('Ngày đăng', '')}")
                    st.markdown(f"**Hạn nộp:** {row.get('Hạn nộp', '')}")
                    st.markdown(f"**Sản phẩm:** {row.get('Sản phẩm phù hợp', '')}")
                st.info(f"💡 **Gợi ý RM:** {row.get('Gợi ý tiếp cận', '')}")
                if row.get("Link"):
                    st.markdown(f"[🔗 Xem chi tiết gói thầu]({row.get('Link')})")

elif view_mode == "📊 Thống kê":
    df = load_data("RAW_DATA")
    df_log = load_data("LOG")

    st.markdown("### 📊 Thống kê tổng hợp")

    if not df.empty:
        col1, col2 = st.columns(2)

        with col1:
            if "Tỉnh/Thành" in df.columns:
                st.markdown("**Gói thầu theo tỉnh**")
                prov_count = df["Tỉnh/Thành"].value_counts().reset_index()
                prov_count.columns = ["Tỉnh", "Số gói"]
                st.bar_chart(prov_count.set_index("Tỉnh"))

        with col2:
            if "Lĩnh vực" in df.columns:
                st.markdown("**Phân bổ theo lĩnh vực**")
                lv_count = df["Lĩnh vực"].value_counts()
                st.bar_chart(lv_count)

    if not df_log.empty:
        st.markdown("### 📋 Lịch sử chạy crawler")
        st.dataframe(df_log, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown(
    "<small>🤖 Dữ liệu tự động bởi GitHub Actions · Phân tích bởi Claude API · "
    f"Cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}</small>",
    unsafe_allow_html=True,
)
