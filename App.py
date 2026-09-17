"""
MONITORING CRS KONSUMER — Dashboard (FRONT-END)
Grand design skeleton berdasarkan sketsa wireframe (BRI x Danantara).

Semua LOGIKA (koneksi Google Sheets, hitung PSI, filter data, dll) ada di
backend.py -- file ini fokus ke TAMPILAN doang (CSS, layout, render UI).
"""

import os
import io
import base64
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import backend as be

# ----------------------------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Monitoring CRS Konsumer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------------
# BRI DESIGN TOKENS
# ----------------------------------------------------------------------------
COLORS = {
    "navy": "#012A5E",
    "nusantara_blue": "#0857C3",
    "cakrawala_blue": "#307FE2",
    "mentari_blue": "#71C5EB",
    "orange": "#F36F21",
    "bg": "#F4F7FB",
    "card": "#FFFFFF",
    "border": "#E1E8F2",
    "text": "#1A2B4C",
    "text_muted": "#6B7A99",
}

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

/* 1. KUNCI BACKGROUND UTAMA HALAMAN */
.stApp, 
[data-testid="stAppViewContainer"], 
[data-testid="stMain"],
section.main {{
    background-color: {COLORS['bg']} !important;
    color: {COLORS['text']} !important;
}}

/* 2. BATASI LEBAR AGAR UKURAN KARTU PRESISI SEPERTI DI LOCALHOST */
div[data-testid="stMain"] .block-container,
section[data-testid="stMain"] .block-container,
div[data-testid="stAppViewContainer"] .block-container,
div[data-testid="stMainBlockContainer"],
.main .block-container,
.block-container {{
    padding-top: 1rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
}}

div[data-testid="stDecoration"] {{
    display: none !important;
    height: 0 !important;
}}
div[data-testid="stAppViewContainer"] > .main,
div[data-testid="stAppViewContainer"] section.main {{
    padding-top: 0 !important;
}}

div[data-testid="stAlert"], div[data-testid="stAlert"] *,
div[data-testid="stException"], div[data-testid="stException"] * {{
    color: unset !important;
}}

code {{
    background-color: #EDF1F7 !important;
    color: {COLORS['text']} !important;
    padding: 1px 5px;
    border-radius: 4px;
}}

#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{
    display: none !important;
    height: 0 !important;
}}

/* 3. HEADER */
.dash-header {{
    background: linear-gradient(90deg, {COLORS['navy']} 0%, {COLORS['nusantara_blue']} 100%);
    border-radius: 12px;
    padding: 12px 22px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    box-shadow: 0 4px 14px rgba(1, 42, 94, 0.18);
}}
.dash-title {{ font-family: 'Poppins', sans-serif; color: white; text-align: center; flex-grow: 1; }}
.dash-title h1 {{ font-size: 18px; font-weight: 700; letter-spacing: 0.5px; margin: 0; }}
.dash-title p {{ font-size: 11px; color: {COLORS['mentari_blue']}; margin: 2px 0 0 0; font-weight: 500; }}
.logo-box {{
    background: rgba(255,255,255,0.08);
    border: 1px dashed rgba(255,255,255,0.5);
    border-radius: 8px;
    width: 140px; height: 64px;
    display: flex; align-items: center; justify-content: center;
    color: rgba(255,255,255,0.75);
    font-size: 10px; font-weight: 600; text-align: center; line-height: 1.2;
}}
.logo-img {{ height: 56px; object-fit: contain; }}

/* 4. PERBAIKAN UTAMA: SEMUA KARTU/CONTAINER BERWARNA PUTIH TEGAS + SHADOW */
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stVerticalBlockBorderWrapper"]),
div[data-testid="stExpander"] {{
    background: #FFFFFF !important;
    background-color: #FFFFFF !important;
    border: 1px solid {COLORS['border']} !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 14px rgba(1, 42, 94, 0.08) !important;
    margin-bottom: 10px;
}}

/* Menjaga elemen internal kartu tetap rapi */
div[data-testid="stVerticalBlockBorderWrapper"] > div {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
}}

/* Judul Section */
.section-label {{
    font-family: 'Poppins', sans-serif;
    font-size: 13px; font-weight: 600; color: {COLORS['navy']};
    text-transform: uppercase; letter-spacing: 0.6px;
    margin-bottom: 12px; display: flex; align-items: center; gap: 8px;
}}
.section-label .bar {{ width: 4px; height: 14px; background: {COLORS['orange']}; border-radius: 2px; display: inline-block; }}

/* Input Selectbox & Button */
div[data-baseweb="select"] > div {{
    background-color: #FFFFFF !important;
    border: 1px solid {COLORS['border']} !important;
    color: {COLORS['text']} !important;
    border-radius: 8px !important;
}}
div[data-baseweb="select"] span, div[data-baseweb="select"] div {{
    color: {COLORS['text']} !important;
}}

button[kind="secondary"], div[data-testid="stDownloadButton"] button {{
    background-color: #FFFFFF !important;
    color: {COLORS['text']} !important;
    border: 1px solid {COLORS['border']} !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}}
button[kind="secondary"]:hover, div[data-testid="stDownloadButton"] button:hover {{
    border-color: {COLORS['nusantara_blue']} !important;
    color: {COLORS['nusantara_blue']} !important;
}}

button[kind="primary"] {{
    background-color: {COLORS['navy']} !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
    border-radius: 30px !important;
}}
button[kind="primary"]:hover {{
    background-color: {COLORS['nusantara_blue']} !important;
}}
button[kind="primary"] p {{
    color: white !important;
}}

div[data-testid="stFormSubmitButton"] button {{
    background-color: {COLORS['navy']} !important;
    color: white !important;
    border: none !important;
    border-radius: 30px !important;
    font-weight: 600 !important;
}}
div[data-testid="stFormSubmitButton"] button:hover {{
    background-color: {COLORS['nusantara_blue']} !important;
}}
div[data-testid="stFormSubmitButton"] button p {{
    color: white !important;
}}

ul[data-testid="stSelectboxVirtualDropdown"] {{
    background-color: #FFFFFF !important;
}}
ul[data-testid="stSelectboxVirtualDropdown"] li {{
    background-color: #FFFFFF !important;
}}
ul[data-testid="stSelectboxVirtualDropdown"] li * {{
    color: {COLORS['text']} !important;
}}
ul[data-testid="stSelectboxVirtualDropdown"] li:hover {{
    background-color: {COLORS['bg']} !important;
}}
ul[data-testid="stSelectboxVirtualDropdown"] li[aria-selected="true"] {{
    background-color: {COLORS['nusantara_blue']} !important;
}}
ul[data-testid="stSelectboxVirtualDropdown"] li[aria-selected="true"] * {{
    color: #FFFFFF !important;
}}

label[data-testid="stWidgetLabel"] {{
    display: flex; justify-content: center;
}}
label[data-testid="stWidgetLabel"] p {{
    font-size: 12px !important; font-weight: 600 !important;
    color: {COLORS['text_muted']} !important;
    text-transform: uppercase; letter-spacing: 0.4px;
    text-align: center; width: 100%;
}}

[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{
    color: #000000 !important;
}}

/* Tabel CRS */
.crs-table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }}
.crs-table th {{
    text-align: right; color: {COLORS['text_muted']}; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.4px;
    border-bottom: 2px solid {COLORS['border']}; padding: 8px 6px;
}}
.crs-table td {{ padding: 7px 6px; border-bottom: 1px solid {COLORS['border']}; color: {COLORS['text']}; text-align: right; }}
.crs-table tr.total-row td {{
    font-weight: 700; background: {COLORS['bg']};
    border-top: 2px solid {COLORS['border']}; border-bottom: none;
}}
.crs-table tr.cutoff-row td {{
    background: #FDEDED; color: #9A1E22; font-weight: 600;
}}

/* KPI Card */
.kpi-card-full {{
    background: #FFFFFF;
    border: 1px solid {COLORS['border']};
    border-left: 5px solid {COLORS['nusantara_blue']};
    border-radius: 12px;
    padding: 16px 16px 16px 18px;
    box-shadow: 0 2px 8px rgba(1,42,94,0.05);
}}
.kpi-card-full.orange {{ border-left-color: {COLORS['orange']}; }}
.kpi-label {{ font-size: 12px; font-weight: 600; color: {COLORS['text_muted']}; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
.kpi-value {{ font-family: 'Poppins', sans-serif; font-size: 30px; font-weight: 700; color: {COLORS['navy']}; }}
.kpi-note {{ font-size: 11.5px; color: {COLORS['text_muted']}; margin-top: 6px; line-height: 1.4; }}

/* ROW ALIGNMENT & STRETCH */
div[class*="st-key-risk_grade_row"] > div[data-testid="stHorizontalBlock"],
div[class*="st-key-model_performance_row"] > div[data-testid="stHorizontalBlock"] {{
    align-items: stretch !important;
}}

div[class*="st-key-risk_grade_row"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
div[class*="st-key-model_performance_row"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
    display: flex !important;
    flex-direction: column !important;
}}

div[class*="st-key-risk_grade_row"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] > div,
div[class*="st-key-model_performance_row"] > div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] > div {{
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
}}

div[class*="st-key-risk_grade_row"] div[data-testid="stVerticalBlockBorderWrapper"],
div[class*="st-key-model_performance_row"] div[data-testid="stVerticalBlockBorderWrapper"] {{
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
    height: 100% !important;
}}

div[data-testid="stElementContainer"]:has(#table-dl-spacer),
div[data-testid="stElementContainer"]:has(#chart-dl-spacer),
div[data-testid="stElementContainer"]:has(#perf-bottom-spacer),
div[data-testid="stElementContainer"]:has(#badrate-dl-spacer) {{
    flex: 1 1 auto !important;
    min-height: 0 !important;
}}

/* SPINNER OVERLAY */
div[data-testid="stSpinner"] {{
    position: fixed !important;
    top: 0 !important; left: 0 !important;
    width: 100vw !important; height: 100vh !important;
    background: rgba(1, 42, 94, 0.55) !important;
    backdrop-filter: blur(2px);
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    z-index: 9999 !important;
}}
div[data-testid="stSpinner"] > div {{
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 18px;
}}
div[data-testid="stSpinner"] svg {{
    width: 64px !important;
    height: 64px !important;
    color: white !important;
}}
div[data-testid="stSpinner"] p {{
    color: white !important;
    font-family: 'Poppins', sans-serif;
    font-size: 18px !important;
    font-weight: 600 !important;
    text-align: center;
}}
</style>
"""

# ----------------------------------------------------------------------------
# GATE — session_state buat role HARUS di-init SEBELUM CSS diinject, biar
# CSS gradient buat layar pembuka bisa digabung jadi SATU blok <style>.
# ----------------------------------------------------------------------------
if "role" not in st.session_state:
    st.session_state.role = None
if "show_admin_login" not in st.session_state:
    st.session_state.show_admin_login = False

if st.session_state.role is None:
    CUSTOM_CSS += f"""
<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
background: linear-gradient(160deg, {COLORS['navy']} 0%, {COLORS['nusantara_blue']} 100%) !important;
}}
div[data-testid="stVerticalBlockBorderWrapper"][class*="st-key-gate_card"] {{
max-width: 380px !important;
margin: 100px auto !important;
background: white !important;
border: 1px solid {COLORS['border']} !important;
border-radius: 20px !important;
box-shadow: 0 12px 30px rgba(1,42,94,0.25) !important;
padding: 8px 12px !important;
}}
div[data-testid="stVerticalBlock"][class*="st-key-gate_card"] {{
background: transparent !important;
border: none !important;
box-shadow: none !important;
max-width: none !important;
margin: 0 !important;
padding: 0 !important;
}}
#gate-card-marker ~ h2 {{
color: #012A5E !important;
}}
#gate-card-marker ~ div .logo-box {{
width: 170px !important;
height: 90px !important;
}}
#gate-card-marker ~ div .logo-img {{
height: 84px !important;
}}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def logo_html(path: str, alt: str) -> str:
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<div class="logo-box" style="background:white; border:1px solid {COLORS["border"]};"><img class="logo-img" src="data:image/png;base64,{b64}" alt="{alt}"/></div>'
    return f'<div class="logo-box" style="border-color: rgba(1,42,94,0.35); color: {COLORS["navy"]}; background: rgba(1,42,94,0.06);">LOGO<br/>{alt}</div>'


def logo_html_plain(path: str, alt: str) -> str:
    """Sama kayak logo_html, tapi TANPA kotak putih -- buat logo versi
    putih yang emang didesain nempel langsung di background gelap
    (dipakai di HEADER, bukan di GATE)."""
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img class="logo-img" src="data:image/png;base64,{b64}" alt="{alt}"/>'
    return f'<div class="logo-box" style="border-color: rgba(255,255,255,0.35); color: white; background: rgba(255,255,255,0.06);">LOGO<br/>{alt}</div>'


if st.session_state.role is None:
    with st.container(key="gate_card"):
        st.markdown(
            f"""
            <span id="gate-card-marker" style="display:none;"></span>
            <div style="display:flex; justify-content:center; gap:14px; padding-top:20px; max-width:100%; flex-wrap:wrap;">
                {logo_html(os.path.join(os.path.dirname(__file__), "assets", "logo_danantara.png"), "DANANTARA")}
                {logo_html(os.path.join(os.path.dirname(__file__), "assets", "logo_BRI.png"), "BRI")}
            </div>
            <h2 style="color:#012A5E; text-align:center; margin:12px 0 20px 0; max-width:100%; word-wrap:break-word; overflow-wrap:break-word;">MONITORING CRS KONSUMER</h2>
            """,
            unsafe_allow_html=True,
        )

        if not st.session_state.show_admin_login:
            if st.button("🔑 Masuk sebagai Admin", use_container_width=True, type="primary"):
                st.session_state.show_admin_login = True
                st.rerun()
            if st.button("👤 Masuk sebagai User", use_container_width=True):
                st.session_state.role = "user"
                st.rerun()
        else:
            st.caption("Masukkan kode admin buat lanjut.")
            code_input = st.text_input(
                "Kode Admin", type="password", label_visibility="collapsed", placeholder="Masukkan kode..."
            )
            if st.button("Masuk", use_container_width=True, type="primary"):
                admin_code = be.get_admin_code()
                if admin_code is not None and code_input == admin_code:
                    st.session_state.role = "admin"
                    st.rerun()
                elif admin_code is None:
                    st.error("Kode admin belum di-setup di secrets.toml.")
                else:
                    st.error("Kode salah, coba lagi.")
            if st.button("← Balik, masuk sebagai User aja", use_container_width=True):
                st.session_state.show_admin_login = False
                st.session_state.role = "user"
                st.rerun()
    st.stop()

IS_ADMIN = st.session_state.role == "admin"
if "posisi_data_session" not in st.session_state:
    _periode_terbaru = be.list_available_periods()
    st.session_state.posisi_data_session = _periode_terbaru[-1] if _periode_terbaru else be.DEFAULT_ACTIVE_PERIOD

POSISI_DATA = st.session_state.posisi_data_session
active_bulan, active_tahun = be.split_period(POSISI_DATA)

# ----------------------------------------------------------------------------
# POSISI DATA -- PER-SESI (per browser/tab), BUKAN lagi 1 setting global
# bersama. Jadi kalau ada orang lain buka tab baru, punya lu di tab ini
# GA IKUT KERESET -- masing-masing independen. Defaultnya tetep sama:
# session baru = otomatis ke Posisi Data TERBARU yang ada di spreadsheet.
# ----------------------------------------------------------------------------
if "posisi_data_session" not in st.session_state:
    _periode_terbaru = be.list_available_periods()
    st.session_state.posisi_data_session = _periode_terbaru[-1] if _periode_terbaru else be.DEFAULT_ACTIVE_PERIOD

POSISI_DATA = st.session_state.posisi_data_session
active_bulan, active_tahun = be.split_period(POSISI_DATA)

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="dash-header">
        {logo_html_plain(os.path.join(os.path.dirname(__file__), "assets", "logo_Danantara_putih.png"), "DANANTARA")}
        <div class="dash-title">
            <h1>MONITORING CRS KONSUMER</h1>
            <p>Posisi data bulan {POSISI_DATA}</p>
        </div>
        {logo_html_plain(os.path.join(os.path.dirname(__file__), "assets", "logo_BRI_Putih.png"), "BRI")}
    </div>
    """,
    unsafe_allow_html=True,
)



# ----------------------------------------------------------------------------
# POSISI DATA + FILTER -- DIGABUNG jadi 1 st.form() + 1 tombol "Terapkan".
# Pilih Bulan/Tahun Posisi Data DAN semua filter (Produk/Realisasi/RO/
# Kualitas Kredit) dulu, baru sekali klik semuanya keupdate bareng. Abis
# submit, langsung dicek: Posisi Data-nya ada datanya ga, terus kombinasi
# filternya ketemu data ga -- dikasih notifikasi sesuai hasilnya.
# ----------------------------------------------------------------------------
filter_section_placeholder = st.empty()
with filter_section_placeholder.container():
    with st.container(border=True):
        st.markdown(
            '<div class="section-label"><span class="bar"></span>Posisi Data & Filter</div>',
            unsafe_allow_html=True
        )

        with st.form(key="filter_form"):
            st.markdown(
                f'<div style="font-size:11px; font-weight:700; color:{COLORS["text_muted"]}; text-transform:uppercase; margin-bottom:8px;">Posisi Data</div>',
                unsafe_allow_html=True,
            )
            pd_col1, pd_col2 = st.columns(2)
            with pd_col1:
                admin_bulan_input = st.selectbox(
                    "Posisi Data — Bulan",
                    be.BULAN_LIST,
                    index=be.BULAN_LIST.index(active_bulan) if active_bulan in be.BULAN_LIST else 6,
                )
            with pd_col2:
                tahun_options = [2024, 2025, 2026, 2027]
                admin_tahun_input = st.selectbox(
                    "Posisi Data — Tahun",
                    tahun_options,
                    index=tahun_options.index(active_tahun) if active_tahun in tahun_options else 2,
                )

            st.markdown(
                f'<div style="font-size:11px; font-weight:700; color:{COLORS["text_muted"]}; text-transform:uppercase; margin:16px 0 8px;">Filter</div>',
                unsafe_allow_html=True,
            )
            f1, f2, f3, f4 = st.columns(4)

            with f1:
                produk_input = st.selectbox("Produk", ["KPP", "Briguna Karya", "Briguna Purna", "Briguna Prapurna", "KKB", "Kartu Kredit"])
            with f2:
                # Toggle All/Pilih Bulan + dropdown Bulan-Tahun -- 2 dropdown
                # terakhir SELALU ditampilin (ga nunggu toggle "Pilih Bulan"
                # dulu, soalnya di dalam st.form() dropdown susulan ga bisa
                # "muncul" sebelum Submit). Nilainya cuma DIPAKAI kalau
                # toggle-nya "Pilih Bulan" -- kalau "All", diabaikan.
                realisasi_toggle_input = st.selectbox("Realisasi", ["All", "Pilih Bulan"])
                rb1, rb2 = st.columns(2)
                with rb1:
                    bulan_pilihan_input = st.selectbox("Bulan", be.BULAN_LIST, index=6, label_visibility="collapsed")
                with rb2:
                    tahun_pilihan_input = st.selectbox("Tahun", [2024, 2025, 2026], index=2, label_visibility="collapsed")
                realisasi_mode_input = f"{bulan_pilihan_input} {tahun_pilihan_input}" if realisasi_toggle_input == "Pilih Bulan" else "All"
            with f3:
                regional_office_input = st.selectbox(
                    "Regional Office",
                    [
                        "All",
                        "Region 1 Medan", "Region 2 Pekanbaru", "Region 3 Padang", "Region 4 Palembang",
                        "Region 5 Bandar Lampung", "Region 6 Jakarta 1", "Region 7 Jakarta 2", "Region 8 Jakarta 3",
                        "Region 9 Bandung", "Region 10 Semarang", "Region 11 Yogyakarta", "Region 12 Surabaya",
                        "Region 13 Malang", "Region 14 Banjarmasin", "Region 15 Makassar", "Region 16 Manado",
                        "Region 17 Denpasar", "Region 18 Jayapura",
                    ],
                )
            with f4:
                kualitas_kredit_input = st.selectbox("Kualitas Kredit", ["All", "Lancar", "DPK", "NPL"])

            submitted = st.form_submit_button("🔍 Terapkan Posisi Data & Filter", type="primary", use_container_width=True)

        if submitted:
            new_posisi_data = f"{admin_bulan_input} {admin_tahun_input}"
            st.session_state.posisi_data_session = new_posisi_data
            st.session_state.filter_terapan = {
                "produk": produk_input,
                "realisasi_mode": realisasi_mode_input,
                "regional_office": regional_office_input,
                "kualitas_kredit": kualitas_kredit_input,
            }

            # Loading/jam pasir muncul selama proses cek data ke Google Sheets
            # (yang paling makan waktu) -- st.spinner otomatis nampilin ikon
            # berputar + teks di bawah tombol Submit selama block ini jalan.
            with st.spinner("⏳ Menerapkan Posisi Data & Filter..."):
                st.cache_data.clear()  # biar data langsung fresh, ga kena cache 60 detik yang basi

                # Cek ketersediaan data buat kombinasi yang baru diterapkan. Pesannya
                # disimpen ke session_state dulu (bukan langsung st.success/warning
                # di sini) karena abis ini kita st.rerun() -- biar HEADER di atas
                # (yang nunjukin "Posisi data bulan X") ikut ke-update ke Posisi
                # Data yang baru juga, bukan cuma bagian filter doang.
                if not be.period_has_data(new_posisi_data):
                    st.session_state.filter_notif = ("warning", f"⚠️ Posisi Data **{new_posisi_data}** belum tersedia.")
                else:
                    cek_data = be.load_uploaded_table(produk_input, realisasi_mode_input, regional_office_input, kualitas_kredit_input, new_posisi_data)
                    if cek_data is None or cek_data.empty:
                        st.session_state.filter_notif = ("warning", (
                            f"⚠️ Data untuk kombinasi filter ini (Produk: **{produk_input}**, Realisasi: **{realisasi_mode_input}**, "
                            f"RO: **{regional_office_input}**, Kualitas Kredit: **{kualitas_kredit_input}**) tidak ditemukan "
                            f"di Posisi Data **{new_posisi_data}**."
                        ))
                    else:
                        st.session_state.filter_notif = ("success", "✅ Penerapan Posisi Data & Filter berhasil dilakukan.")

            st.rerun()

        elif "filter_terapan" not in st.session_state:
            # Pertama kali buka -- belum pernah submit apa-apa, pakai default.
            st.session_state.filter_terapan = {
                "produk": produk_input,
                "realisasi_mode": realisasi_mode_input,
                "regional_office": regional_office_input,
                "kualitas_kredit": kualitas_kredit_input,
            }

        # Tampilin notifikasi hasil submit sebelumnya (kalau ada), abis itu
        # dihapus lagi -- biar ga muncul TERUS di setiap rerun berikutnya.
        if "filter_notif" in st.session_state:
            _notif_type, _notif_text = st.session_state.filter_notif
            getattr(st, _notif_type)(_notif_text)
            del st.session_state.filter_notif

produk = st.session_state.filter_terapan["produk"]
realisasi_mode = st.session_state.filter_terapan["realisasi_mode"]
regional_office = st.session_state.filter_terapan["regional_office"]
kualitas_kredit = st.session_state.filter_terapan["kualitas_kredit"]

# ----------------------------------------------------------------------------
# UPLOAD DATA -- HANYA ADMIN. 2 panel (Sebaran Risk Grade & Rekening |
# Risk Grade vs Bad Rate), Posisi Data KHUSUS buat upload (independen dari
# filter tampilan di atas -- ga perlu klik "Terapkan" dulu), 1 tombol
# "UPDATE DATABASE" yang proses kedua file sekaligus. Konsep OR: boleh
# upload salah satu doang, dua-duanya, atau ga dua-duanya (kena validasi).
# ----------------------------------------------------------------------------
if IS_ADMIN:
    with st.expander("📤 Upload Data", expanded=True):

        st.markdown(
            f'<div style="font-size:11px; font-weight:700; color:{COLORS["text_muted"]}; text-transform:uppercase; margin-bottom:8px;">Posisi Data (khusus upload)</div>',
            unsafe_allow_html=True,
        )
        up_col1, up_col2 = st.columns(2)
        with up_col1:
            upload_bulan = st.selectbox(
                "Posisi Data - Bulan", be.BULAN_LIST,
                index=None, placeholder="-", key="upload_bulan_select",
            )
        with up_col2:
            upload_tahun = st.selectbox(
                "Posisi Data - Tahun", [2024, 2025, 2026, 2027],
                index=None, placeholder="-", key="upload_tahun_select",
            )

        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

        col_upload_kiri, col_upload_kanan = st.columns(2)

        with col_upload_kiri:
            with st.container(border=True):
                st.markdown(
                    '<div style="text-align:center; font-weight:700; margin-bottom:10px;">UPLOAD DATA SEBARAN RISK GRADE & REKENING</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    """
                    **Kolom Wajib:**
                    - posisi
                    - region
                    - bikole
                    - produk
                    - tgl_realisasi_int
                    - rating_score
                    - acctno
                    - cbal_base
                    - plafond
                    """
                )
                file_risk_grade = st.file_uploader(
                    "Upload file excel data", type=["xlsx"], key="upload_risk_grade_file",
                )

        with col_upload_kanan:
            with st.container(border=True):
                st.markdown(
                    '<div style="text-align:center; font-weight:700; margin-bottom:10px;">UPLOAD DATA RISK GRADE VS BAD RATE</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    """
                    **Kolom Wajib:**
                    - RATING_SCORE
                    - REKENING
                    - KOL_1 .... KOL_36
                    """
                )
                file_bad_rate = st.file_uploader(
                    "Upload file excel data", type=["xlsx"], key="upload_bad_rate_file",
                )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        if st.button("🔄 UPDATE DATABASE", type="primary", use_container_width=True):
            if upload_bulan is None or upload_tahun is None:
                st.warning("⚠️ Pilih Posisi Data (Bulan & Tahun) dulu sebelum upload.")
            elif file_risk_grade is None and file_bad_rate is None:
                st.warning("⚠️ Harap upload data terlebih dahulu (minimal salah satu file).")
            else:
                posisi_data_upload = f"{upload_bulan} {upload_tahun}"

                with st.spinner("⏳ Memproses & menyimpan data..."):
                    if file_risk_grade is not None:
                        try:
                            df_mentah_rg = pd.read_excel(file_risk_grade)
                            jumlah_baris_rg = be.save_data_to_sheets(df_mentah_rg, posisi_data_upload)
                            st.success(
                                f"✅ Data Sebaran Risk Grade & Rekening untuk Posisi Data "
                                f"**{posisi_data_upload}** tersedia ({jumlah_baris_rg:,} baris diproses)."
                            )
                        except Exception as e:
                            st.error("❌ Gagal menyimpan Data Sebaran Risk Grade & Rekening:")
                            st.exception(e)
                    else:
                        st.info("ℹ️ Data Sebaran Risk Grade & Rekening tidak tersedia (tidak diupload).")

                    if file_bad_rate is not None:
                        try:
                            df_mentah_br = pd.read_excel(file_bad_rate)
                            jumlah_baris_br = be.save_bad_rate_to_sheets(
                                df_mentah_br, posisi_data_upload, produk_input
                            )
                            st.success(
                                f"✅ Data Risk Grade vs Bad Rate untuk Posisi Data "
                                f"**{posisi_data_upload}** tersedia ({jumlah_baris_br:,} baris diproses)."
                            )
                        except Exception as e:
                            st.error("❌ Gagal menyimpan Data Risk Grade vs Bad Rate:")
                            st.exception(e)
                    else:
                        st.info("ℹ️ Data Risk Grade vs Bad Rate tidak tersedia (tidak diupload).")

    st.caption(
        f"🗄️ Data disimpan permanen di Google Sheets (tabel ringkasan hasil pivot), "
        f"terpisah per Posisi Data & jenis data (Sebaran Risk Grade vs Bad Rate). "
        f"Admin dan User membaca sumber yang sama, dan datanya TETAP ADA walau app restart."
    )

# ----------------------------------------------------------------------------
# RINGKASAN KUALITAS KREDIT -- DULU pakai 1 dropdown buat gonta-ganti basis
# hitung (Jumlah Rekening vs Outstanding), SEKARANG basisnya ga usah
# dipilih lagi -- ditampilin BARENGAN, dibagi 2 kolom: KIRI = basis
# "Jumlah Rekening", KANAN = basis "Outstanding (Rp Juta)". Keliatan buat
# Admin DAN User (ga di-gate).
# ----------------------------------------------------------------------------
def _render_kpi_tile(label: str, value_display: str, grade_note: str = None) -> str:
    """HTML 1 kartu kecil (Lancar/DPK/NPL/Approve/Override) -- dipisah jadi
    fungsi karena dipakai berkali-kali (3 + 2 kartu) x 2 kolom basis."""
    note_html = (
        f'<div style="font-size:10.5px; color:{COLORS["text_muted"]}; margin-top:4px;">{grade_note}</div>'
        if grade_note else ""
    )
    return f"""
    <div style="
        background:#FFFFFF;
        border:1px solid {COLORS['border']};
        border-radius:12px;
        padding:16px 12px;
        text-align:center;
        box-shadow:0 2px 8px rgba(1,42,94,0.05);
    ">
        <div style="
            font-size:12px;
            font-weight:700;
            color:{COLORS['text_muted']};
            text-transform:uppercase;
            letter-spacing:0.5px;
        ">{label}</div>
        <div style="
            font-family:'Poppins',sans-serif;
            font-size:28px;
            font-weight:700;
            color:{COLORS['navy']};
            margin-top:4px;
        ">{value_display}</div>
        {note_html}
    </div>
    """


approve_max = be.APPROVE_MAX_GRADE.get(produk, be.APPROVE_MAX_GRADE["All"])
max_grade_produk = be.RISK_GRADE_RANGE.get(produk, be.RISK_GRADE_RANGE["All"])[-1]
override_start = approve_max + 1
override_note = f"Risk Grade {override_start}" if override_start >= max_grade_produk else f"Risk Grade {override_start}-{max_grade_produk}"

with st.container(border=True):
    col_basis_rekening, col_basis_outstanding = st.columns(2)

    for col_basis, basis_label in [(col_basis_rekening, "Jumlah Rekening"), (col_basis_outstanding, "Outstanding (Rp Juta)")]:
        with col_basis:
            st.markdown(
                f'<div style="text-align:center; font-size:11.5px; color:{COLORS["text_muted"]}; margin-bottom:10px;">Berdasarkan: <b>{basis_label}</b></div>',
                unsafe_allow_html=True,
            )

            quality_pct = be.get_quality_percentages(produk, realisasi_mode, regional_office, POSISI_DATA, basis=basis_label)

            q1, q2, q3 = st.columns(3)
            for qcol, label in zip([q1, q2, q3], ["Lancar", "DPK", "NPL"]):
                with qcol:
                    # Kalau ga ada data sama sekali (quality_pct None) -> "-" semua.
                    # Kalau filter Kualitas Kredit "All" -> semua kartu tampil normal.
                    # Kalau filter-nya spesifik (Lancar/DPK/NPL) -> cuma kartu yang
                    # cocok sama filter itu yang tampil angka, sisanya jadi "-".
                    if quality_pct is None:
                        value_display = "-"
                    elif kualitas_kredit == "All" or kualitas_kredit == label:
                        value_display = f"{quality_pct[label]:.1f}%"
                    else:
                        value_display = "-"
                    st.markdown(_render_kpi_tile(label, value_display), unsafe_allow_html=True)

    # Approve/Override -- BEDA sama Lancar/DPK/NPL di atas: ini SENGAJA
    # nggak ikut dipisah 2 kolom basis. Cuma 1 baris aja, dihitung pakai
    # basis "Jumlah Rekening" (basis utama/default), spanning full width
    # di bawah 2 kolom Lancar/DPK/NPL. Dikasih kolom "pad" kosong di kiri
    # & kanan biar kartu Approve/Override GA melebar penuh sepanjang
    # container (yang lebarnya = gabungan 2 kolom basis di atas) -- tanpa
    # ini, kartunya jadi kepanjangan/gepeng dibanding kartu Lancar/DPK/NPL.
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    approve_override_pct = be.get_approve_override_pct(produk, realisasi_mode, regional_office, POSISI_DATA, basis="Jumlah Rekening")

    pad_left, q4, q5, pad_right = st.columns([1, 3, 3, 1])
    for qcol, label, grade_note in zip(
        [q4, q5],
        ["Approve", "Override"],
        [f"Risk Grade 1-{approve_max}", override_note],
    ):
        with qcol:
            value_display = f"{approve_override_pct[label]:.1f}%" if approve_override_pct is not None else "-"
            st.markdown(_render_kpi_tile(label, value_display, grade_note), unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# DATA: pakai file yang di-upload kalau ada, kalau ga ketemu TAMPILIN
# "Data tidak ditemukan" secara eksplisit (BUKAN dummy) -- biar ga
# disalahartiin sebagai data asli.
# ----------------------------------------------------------------------------
table_from_upload = be.load_uploaded_table(produk, realisasi_mode, regional_office, kualitas_kredit, POSISI_DATA)
if table_from_upload is not None:
    df = table_from_upload
    table_source = "upload"
else:
    df = pd.DataFrame(columns=["Risk Grade", "Jumlah Rekening", "Outstanding (Rp Juta)", "Plafon (Rp Juta)"])
    table_source = "notfound"

psi_computed = None
if table_source == "upload":
    psi_computed = be.compute_psi_vs_baseline(df, produk, be.RISK_GRADE_RANGE.get(produk, be.RISK_GRADE_RANGE["All"]))


# ----------------------------------------------------------------------------
# ROW: Tabel (kiri) + Chart bar+line (kanan)
# ----------------------------------------------------------------------------
with st.container(key="risk_grade_row"):
    col_table, col_chart = st.columns([1, 1.4])

    data_kosong = df.empty or df["Jumlah Rekening"].sum() == 0

    with col_table:
        with st.container(border=True):

            # MARKER + JUDUL
            st.markdown(
                f'''
                <div class="section-label">
                    <span class="bar"></span>
                    Sebaran Risk Grade — {POSISI_DATA}
                </div>
                ''',
                unsafe_allow_html=True
            )

            if data_kosong:
                st.markdown(
                    '''
                    <div style="text-align:center; padding:40px 10px; color:#6B7A99;">
                        <div style="font-size:15px; font-weight:600;">
                            Data can't found
                        </div>
                        <div style="font-size:12.5px; margin-top:4px;">
                            Tidak ada data untuk kombinasi filter ini.
                            Coba ubah filter di atas.
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )

            else:
                # Highlight merah = Risk Grade OVERRIDE
                approve_max = be.APPROVE_MAX_GRADE.get(
                    produk,
                    be.APPROVE_MAX_GRADE["All"]
                )

                def _fmt_plafon(v):
                    return f"{v:,.1f}" if pd.notna(v) else "-"

                rows_html = "".join(
                    f'<tr class="{"cutoff-row" if int(r["Risk Grade"]) > approve_max else ""}">'
                    f'<td>{int(r["Risk Grade"])}</td>'
                    f'<td>{r["Jumlah Rekening"]:,.0f}</td>'
                    f'<td>{r["Outstanding (Rp Juta)"]:,.1f}</td>'
                    f'<td>{_fmt_plafon(r["Plafon (Rp Juta)"])}</td>'
                    f'</tr>'
                    for _, r in df.iterrows()
                )

                total_rekening = df["Jumlah Rekening"].sum()
                total_outstanding = df["Outstanding (Rp Juta)"].sum()

                total_plafon = (
                    df["Plafon (Rp Juta)"].sum()
                    if df["Plafon (Rp Juta)"].notna().any()
                    else None
                )

                table_html = f"""<table class="crs-table">
<tr>
    <th>Risk Grade</th>
    <th>Jumlah Rekening</th>
    <th>Outstanding (Rp Juta)</th>
    <th>Total Plafon (Rp Juta)</th>
</tr>
{rows_html}
<tr class="total-row">
    <td>Total</td>
    <td>{total_rekening:,.0f}</td>
    <td>{total_outstanding:,.1f}</td>
    <td>{_fmt_plafon(total_plafon)}</td>
</tr>
</table>"""

                st.markdown(table_html, unsafe_allow_html=True)

                # Excel
                excel_buffer = io.BytesIO()

                download_df = pd.concat(
                    [
                        df,
                        pd.DataFrame([
                            {
                                "Risk Grade": "Total",
                                "Jumlah Rekening": total_rekening,
                                "Outstanding (Rp Juta)": total_outstanding,
                                "Plafon (Rp Juta)": total_plafon
                            }
                        ])
                    ],
                    ignore_index=True
                )

                with pd.ExcelWriter(
                    excel_buffer,
                    engine="openpyxl"
                ) as writer:

                    download_df.to_excel(
                        writer,
                        index=False,
                        sheet_name="Sebaran Risk Grade"
                    )

                    worksheet = writer.sheets["Sebaran Risk Grade"]

                    from openpyxl.styles import PatternFill, Font

                    red_fill = PatternFill(
                        start_color="FDEDED",
                        end_color="FDEDED",
                        fill_type="solid"
                    )

                    red_font = Font(
                        color="9A1E22",
                        bold=True
                    )

                    for row_idx, grade_val in enumerate(
                        download_df["Risk Grade"],
                        start=2
                    ):
                        if (
                            isinstance(grade_val, (int, np.integer))
                            and grade_val > approve_max
                        ):
                            for col_idx in range(
                                1,
                                len(download_df.columns) + 1
                            ):
                                cell = worksheet.cell(
                                    row=row_idx,
                                    column=col_idx
                                )
                                cell.fill = red_fill
                                cell.font = red_font

                # Spacer supaya button berada di bawah
                st.markdown(
                    '<span id="table-dl-spacer" style="display:none;"></span>',
                    unsafe_allow_html=True
                )

                st.download_button(
                    label="⬇️ Download Tabel (Excel)",
                    data=excel_buffer.getvalue(),
                    file_name=(
                        f"tabel_risk_grade_"
                        f"{produk}_"
                        f"{POSISI_DATA.replace(' ', '_')}.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    )
                )


    with col_chart:
        with st.container(border=True):

            # MARKER HARUS ADA JUGA DI KANAN
            st.markdown(
                f'''
                <div class="section-label">
                    <span class="bar"></span>
                    Sebaran Jumlah Rekening & Outstanding — {POSISI_DATA}
                </div>
                ''',
                unsafe_allow_html=True
            )

            if data_kosong:
                st.markdown(
                    '''
                    <div style="text-align:center; padding:40px 10px; color:#6B7A99;">
                        <div style="font-size:15px; font-weight:600;">
                            Data can't found
                        </div>
                        <div style="font-size:12.5px; margin-top:4px;">
                            Tidak ada data untuk kombinasi filter ini.
                            Coba ubah filter di atas.
                        </div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )

            else:
                approve_max = be.APPROVE_MAX_GRADE.get(
                    produk,
                    be.APPROVE_MAX_GRADE["All"]
                )

                bar_colors = [
                    "#E5484D"
                    if grade > approve_max
                    else COLORS["mentari_blue"]
                    for grade in df["Risk Grade"]
                ]

                fig = go.Figure()

                fig.add_trace(
                    go.Bar(
                        x=df["Risk Grade"],
                        y=df["Jumlah Rekening"],
                        name="Jumlah Rekening",
                        marker_color=bar_colors,
                        yaxis="y1"
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=df["Risk Grade"],
                        y=df["Outstanding (Rp Juta)"],
                        name="Outstanding (Rp Juta)",
                        mode="lines+markers",
                        line=dict(
                            color=COLORS["nusantara_blue"],
                            width=3
                        ),
                        marker=dict(size=7),
                        yaxis="y2"
                    )
                )

                fig.update_layout(
                    height=390,
                    margin=dict(
                        l=10,
                        r=10,
                        t=10,
                        b=10
                    ),
                    plot_bgcolor="white",
                    paper_bgcolor="white",

                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        font=dict(
                            color="#000000",
                            size=12
                        )
                    ),

                    xaxis=dict(
                        title=dict(
                            text="Risk Grade",
                            font=dict(
                                color="#000000",
                                size=12
                            )
                        ),
                        tickmode="linear",
                        gridcolor=COLORS["border"],
                        tickfont=dict(
                            color="#000000",
                            size=11
                        )
                    ),

                    yaxis=dict(
                        title=dict(
                            text="Jumlah Rekening",
                            font=dict(
                                color="#000000",
                                size=12
                            )
                        ),
                        gridcolor=COLORS["border"],
                        tickfont=dict(
                            color="#000000",
                            size=11
                        )
                    ),

                    yaxis2=dict(
                        title=dict(
                            text="Outstanding (Rp Juta)",
                            font=dict(
                                color="#000000",
                                size=12
                            )
                        ),
                        overlaying="y",
                        side="right",
                        showgrid=False,
                        tickfont=dict(
                            color="#000000",
                            size=11
                        )
                    ),

                    font=dict(
                        family="Inter, sans-serif",
                        color="#000000",
                        size=12
                    )
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={"displayModeBar": False}
                )

                # Spacer supaya button berada di bawah
                st.markdown(
                    '<span id="chart-dl-spacer" style="display:none;"></span>',
                    unsafe_allow_html=True
                )

                try:
                    export_fig = go.Figure(fig)

                    export_fig.update_layout(
                        margin=dict(
                            l=70,
                            r=70,
                            t=60,
                            b=70
                        ),
                        title=dict(
                            text=(
                                f"Sebaran Risk Grade — "
                                f"{produk} — Posisi {POSISI_DATA}"
                            ),
                            font=dict(
                                size=16,
                                color="#000000"
                            ),
                            x=0.5,
                            xanchor="center"
                        )
                    )

                    chart_jpg = be.fig_to_jpg_cached(
                        export_fig.to_json(),
                        1100,
                        650,
                        2
                    )

                    st.download_button(
                        label="⬇️ Download Grafik (JPG)",
                        data=chart_jpg,
                        file_name=(
                            f"grafik_risk_grade_"
                            f"{produk}_"
                            f"{POSISI_DATA.replace(' ', '_')}.jpg"
                        ),
                        mime="image/jpeg"
                    )

                except Exception as e:
                    st.caption(
                        "⚠️ Download grafik butuh package "
                        f"'kaleido'. Detail: {e}"
                    )

    # ----------------------------------------------------------------------------
# ROW: Model Performance (Gini + PSI, ditumpuk atas-bawah) di KIRI,
# Grafik RISK GRADE VS BAD RATE di KANAN.
# (Section "MOB vs Bad Rate" DIHAPUS sesuai permintaan -- proporsi kolom
# [1, 1.4] disamain sama row tabel/chart di atas biar rapi & sejajar.)
# ----------------------------------------------------------------------------
gini_value = be.DUMMY_GINI_BY_PRODUK.get(produk, be.DUMMY_GINI_BY_PRODUK["All"])

if table_source != "upload":
    psi_value = None
    psi_note = "Upload file Data Bulanan dulu supaya PSI bisa dihitung."
    psi_badge, psi_badge_color = "Tidak bisa dihitung", "#6B7A99"
elif psi_computed is not None:
    psi_value = psi_computed
    psi_note = "Dihitung otomatis, dibandingkan ke sebaran model (baseline tetap)."
    if psi_value <= 0.15:
        psi_badge, psi_badge_color = "Model Stabil", "#1FA97C"
    elif psi_value < 0.25:
        psi_badge, psi_badge_color = "Masih dapat diterima", "#F5B942"
    else:
        psi_badge, psi_badge_color = "Model Tidak Stabil", "#E5484D"
else:
    psi_value = None
    psi_note = f'Belum ada sebaran model (baseline) untuk produk "{produk}".'
    psi_badge, psi_badge_color = "Tidak bisa dihitung", "#6B7A99"

# PENTING: st.columns() HARUS dipanggil DI DALAM st.container(key="model_performance_row")
# -- persis kayak row Tabel/Chart di atas -- biar div stHorizontalBlock-nya beneran
# nested di dalam container ini, dan CSS align-items:stretch yang nargetin
# "st-key-model_performance_row" bisa nemplok & berfungsi.
with st.container(key="model_performance_row"):
    col_perf, col_bad_rate = st.columns([1, 1.4])

    with col_perf:
        with st.container(border=True):
            st.markdown(f'<div class="section-label"><span class="bar"></span>Model Performance — {POSISI_DATA}</div>', unsafe_allow_html=True)

            st.markdown(
                f"""
                <div class="kpi-card-full">
                    <div class="kpi-label">Gini Model</div>
                    <div class="kpi-value">{gini_value * 100:.2f}%</div>
                    <div class="kpi-note">Dihitung khusus untuk produk: <b>{produk}</b> (Gini dikunci sesuai produk yang dipilih pada filter).</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

            badge_html = (
                f'<span style="background:{psi_badge_color}22; color:{psi_badge_color}; '
                f'font-size:11px; font-weight:700; padding:2px 8px; border-radius:20px; margin-left:8px;">{psi_badge}</span>'
                if psi_badge else ""
            )
            psi_display = f"{psi_value * 100:.2f}%" if psi_value is not None else "—"
            st.markdown(
                f"""
                <div class="kpi-card-full">
                    <div class="kpi-label">PSI</div>
                    <div class="kpi-value">{psi_display}{badge_html}</div>
                    <div class="kpi-note">{psi_note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Caption status + tombol Logout, nempel natural di bawah card PSI
            # Spacer -- dorong caption + tombol Logout ke PALING BAWAH card,
            # biar sejajar sama bagian bawah card grafik di sebelahnya.
            st.markdown('<span id="perf-bottom-spacer" style="display:none;"></span>', unsafe_allow_html=True)

            table_caption = "✅ Tabel/Grafik dari file upload" if table_source == "upload" else "⚠️ Data tidak ditemukan untuk kombinasi filter/Posisi Data ini"
            role_caption = "🔑 Mode: Admin" if IS_ADMIN else "👤 Mode: User"
            st.caption(f"{table_caption} · {role_caption}")

            if st.button("🚪 Logout / Ganti Mode"):
                st.session_state.role = None
                st.session_state.show_admin_login = False
                st.rerun()

    with col_bad_rate:
        with st.container(border=True):
            st.markdown(
                f'''
                <div class="section-label">
                    <span class="bar"></span>
                    RISK GRADE VS BAD RATE — {POSISI_DATA.upper()}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.caption(
                "* Bad rate dihitung dari jumlah rekening yang memenuhi performance"
                "  window dibanding jumlah populasi rekening yang memenuhi performance window"
            )

            performance_months = be.get_product_performance_window(produk)
            selected_window = f"{performance_months} Bulan"

            grade_range_current = be.RISK_GRADE_RANGE.get(produk, be.RISK_GRADE_RANGE["All"])

            bad_rate_from_upload = be.load_uploaded_bad_rate(produk, realisasi_mode, regional_office, kualitas_kredit, POSISI_DATA)

            sub = pd.DataFrame()
            if bad_rate_from_upload is not None and not bad_rate_from_upload.empty:
                bad_rate_df = bad_rate_from_upload.copy()
                if "Performance Window" in bad_rate_df.columns:
                    sub = bad_rate_df[
                        bad_rate_df["Performance Window"].astype(str).str.strip().str.lower() == selected_window.lower()
                    ].copy()

            if sub.empty:
                st.markdown(
                    '<div style="text-align:center; padding: 40px 10px; color:#6B7A99;">'
                    '<div style="font-size:15px; font-weight:600;">Data can\'t found</div>'
                    '<div style="font-size:12.5px; margin-top:4px;">Belum ada data Bad Rate untuk kombinasi filter & Posisi Data ini. Upload Data Bulanan dengan kolom \'Performance Window\' & \'Jumlah Bad\'.</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                chart_color = be.PRODUCT_CHART_COLORS.get(produk, "#7B61FF")

                fig_bad_rate = go.Figure()
                fig_bad_rate.add_trace(
                    go.Scatter(
                        x=sub["Risk Grade"],
                        y=sub["Bad Rate (%)"],
                        name=selected_window,
                        mode="lines+markers",
                        line=dict(color=chart_color, width=3),
                        marker=dict(size=8, color=chart_color),
                        hovertemplate=(
                            "Risk Grade: %{x}<br>"
                            f"Produk: {produk}<br>"
                            f"Performance Window: {selected_window}<br>"
                            "Bad Rate: %{y:.2f}%"
                            "<extra></extra>"
                        )
                    )
                )

                fig_bad_rate.update_layout(
                    height=360,
                    margin=dict(l=10, r=10, t=20, b=10),
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    annotations=[
                        dict(
                            x=0.98, y=1.08,
                            xref="paper", yref="paper",
                            text=f"<b>━━ {selected_window}</b>",
                            showarrow=False,
                            xanchor="right", yanchor="top",
                            font=dict(color=chart_color, size=13),
                            bgcolor="rgba(255,255,255,0.90)",
                            bordercolor=chart_color,
                            borderwidth=1,
                            borderpad=5
                        )
                    ],
                    xaxis=dict(
                        title=dict(text="Risk Grade", font=dict(color="#000000", size=12)),
                        tickmode="linear",
                        gridcolor=COLORS["border"],
                        tickfont=dict(color="#000000", size=11)
                    ),
                    yaxis=dict(
                        title=dict(text="Bad rate(%)", font=dict(color="#000000", size=12)),
                        gridcolor=COLORS["border"],
                        tickfont=dict(color="#000000", size=11)
                    ),
                    font=dict(family="Inter, sans-serif", color="#000000", size=12)
                )

                st.plotly_chart(fig_bad_rate, use_container_width=True, config={"displayModeBar": False})

                st.markdown('<span id="badrate-dl-spacer" style="display:none;"></span>', unsafe_allow_html=True)
                dl_col1, dl_col2 = st.columns(2)

                with dl_col1:
                    try:
                        export_fig_br = go.Figure(fig_bad_rate)
                        export_fig_br.update_layout(
                            margin=dict(l=70, r=70, t=60, b=70),
                            title=dict(
                                text=f"Risk Grade vs Bad Rate — {produk} — {selected_window} — Posisi {POSISI_DATA}",
                                font=dict(size=16, color="#000000"),
                                x=0.5,
                                xanchor="center"
                            )
                        )
                        bad_rate_jpg = be.fig_to_jpg_cached(export_fig_br.to_json(), 1100, 650, 2)
                        st.download_button(
                            label="⬇️ Download Grafik (JPG)",
                            data=bad_rate_jpg,
                            file_name=f"bad_rate_{produk}_{selected_window.replace(' ', '_')}_{POSISI_DATA.replace(' ', '_')}.jpg",
                            mime="image/jpeg",
                            key="download_bad_rate_jpg"
                        )
                    except Exception as e:
                        st.caption(f"⚠️ Download grafik membutuhkan package 'kaleido'. Detail: {e}")

                with dl_col2:
                    bad_rate_excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(bad_rate_excel_buffer, engine="openpyxl") as writer:
                        sub.to_excel(writer, index=False, sheet_name="Bad Rate")

                    st.download_button(
                        label="⬇️ Download Tabel (Excel)",
                        data=bad_rate_excel_buffer.getvalue(),
                        file_name=f"bad_rate_{produk}_{selected_window.replace(' ', '_')}_{POSISI_DATA.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_bad_rate_excel"
                    )
