"""
backend.py — MONITORING CRS KONSUMER
Semua LOGIKA (bukan tampilan): koneksi Google Sheets, baca/tulis data,
perhitungan PSI/Bad Rate, dan konstanta bisnis (baseline, cut-off, dll).

app.py (front-end) tinggal import dari sini, ga perlu tau detail
implementasinya -- kalau nanti misal Google Sheets diganti database lain,
cukup ubah file ini doang, app.py ga perlu disentuh.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import gspread
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ----------------------------------------------------------------------------
# GOOGLE SHEETS -- koneksi buat nyimpen "Data Bulanan". Setiap Posisi Data
# (bulan) punya WORKSHEET/TAB SENDIRI dalam 1 spreadsheet yang sama, contoh:
# "Juli_26", "September_26". Sheet baru dibikin otomatis kalau belum ada.
#
# Butuh 2 hal di secrets.toml:
#   [gcp_service_account]  -> isi JSON key service account (semua field-nya)
#   [sheet]                -> sheet_id (worksheet_name UDAH GA DIPAKAI lagi,
#                              karena nama sheet sekarang otomatis per-periode)
# ----------------------------------------------------------------------------

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

"""
Fungsi pembersih data upload -- TAMBAHKAN ke backend.py, dipanggil di
dalam save_data_to_sheets() SEBELUM data ditulis ke worksheet.

Kolom mentah yang DIOLAH jadi nama/format standar dashboard:
  posisi -> Posisi Data | region -> Regional Office | tgl_realisasi_int -> Realisasi
  rating_score -> Risk Grade | acctno -> Jumlah Rekening
  cbal_base -> Outstanding (Rp Juta) | plafond -> Plafon (Rp Juta)
  produk -> Produk | Kualitas Kredit -> Kualitas Kredit (apa adanya)

Kolom mentah yang IKUT MASUK ke spreadsheet APA ADANYA (ga dipakai
tampilan dashboard, tapi tetap disimpan): start_date, bikole

Kolom mentah yang DIBUANG total (lihat KOLOM_DIBUANG di bawah):
  cifno, cfssno, fksegmen, segmen, rating_score_description, score,
  ds, tgl_realisasi, kol_adk, cst_ktp, is_bad
"""

import pandas as pd

# ----------------------------------------------------------------------------
# ISI SENDIRI di sini -- kode huruf (B sampai Y) -> nama Regional Office
# lengkap. Kode yang TIDAK kamu isi (dibiarin string kosong "") tetap
# tersimpan sebagai kode mentahnya (ga bikin error, cuma ga diterjemahin).
# ----------------------------------------------------------------------------
REGION_MAPPING = {
    "B": "Region 1 Medan",  # <- isi manual, misal: "Region 6 Jakarta 1"
    "C": "Region 3 Padang",
    "D": "Region 4 Palembang",
    "E": "Region 6 Jakarta 1",
    "F": "Region 9 Bandung",
    "G": "Region 10 Semarang",
    "H": "Region 11 Yogyakarta",
    "I": "Region 7 Jakarta 2",
    "J": "Region 5 Bandar Lampung",
    "K": "Region 12 Surabaya",
    "L": "Region 14 Banjarmasin",
    "M": "Region 17 Denpasar",
    "N": "Region 16 Manado",
    "O": "Region 18 Jayapura",
    "P": "Region 15 Makassar",
    "Q": "Region 8 Jakarta 3",
    "R": "Region 13 Malang",
    "X": "Region 2 Pekanbaru",
    
}

# Kolom mentah yang DIBUANG total, ga ikut ke spreadsheet sama sekali.
# 6 kolom pertama = ga dipakai dashboard sama sekali.
# 5 kolom berikutnya = "kembar"/duplikat info yang udah kepake di kolom lain
# (ds & tgl_realisasi & kol_adk & cst_ktp punya versi lain yang udah
# dipakai jadi salah satu dari 9 kolom standar di bawah).
# 3 kolom terakhir (bikole, start_date, cut_off) DIBUANG karena datanya
# UNIK per rekening (nggak bisa diringkas/di-pivot ke 1 nilai wakil buat
# sekelompok rekening) -- karena data sekarang di-PIVOT (lihat
# agregasi_untuk_dashboard), kolom kayak gini ga punya tempat lagi.
KOLOM_DIBUANG = [
    "cifno",
    "cfssno",
    "fksegmen",
    "segmen",
    "rating_score_description",
    "score",
    "ds",          # kembar sama 'posisi' (sama-sama Posisi Data)
    "tgl_realisasi",   # kembar sama 'tgl_realisasi_int' (sama-sama Realisasi)
    "kol_adk",     # kembar sama 'Kualitas Kredit' (kode vs teks)
    "cst_ktp",     # kembar sama 'cfssno' (sama-sama No. KTP, dua-duanya dibuang)
    "is_bad",
    "bikole",      # unik per rekening, ga bisa di-pivot -- redundan sama 'Kualitas Kredit'
    "start_date",  # unik per rekening, ga bisa di-pivot, ga penting buat dashboard
    "cut_off",     # unik per rekening, ga bisa di-pivot
]

BULAN_LIST = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def _format_posisi_data(nilai) -> str:
    """'202608' (YYYYMM, 6 digit) -> 'Agustus 2026'."""
    teks = str(nilai).strip().replace(".0", "")
    if teks.isdigit() and len(teks) == 6:
        tahun = int(teks[:4])
        bulan = int(teks[4:6])
        if 1 <= bulan <= 12:
            return f"{BULAN_LIST[bulan - 1]} {tahun}"
    return teks


def _format_realisasi(nilai) -> str:
    """'20220426' (YYYYMMDD, 8 digit) -> 'April 2022'."""
    teks = str(nilai).strip().replace(".0", "")
    if teks.isdigit() and len(teks) == 8:
        try:
            tanggal = pd.to_datetime(teks, format="%Y%m%d")
            return f"{BULAN_LIST[tanggal.month - 1]} {tanggal.year}"
        except ValueError:
            return teks
    return teks


def _format_region(kode) -> str:
    """'B' -> nama lengkap sesuai REGION_MAPPING. Kalau kodenya ga ada
    di kamus (belum diisi/ga dikenal), dibalikin apa adanya (bukan error)."""
    kode_bersih = str(kode).strip()
    hasil = REGION_MAPPING.get(kode_bersih, "")
    return hasil if hasil else kode_bersih


def _format_kualitas_kredit(bikole) -> str:
    """'bikole' (kode angka 1-5) -> 'Kualitas Kredit' (teks), sesuai
    aturan: 1 = Lancar, 2 = DPK, 3/4/5 = NPL. Data mentah TERNYATA ga
    punya kolom 'Kualitas Kredit' siap pakai -- harus diturunin dari
    bikole (kolom mentah aslinya angka)."""
    try:
        angka = int(float(str(bikole).strip()))
    except (ValueError, TypeError):
        return str(bikole).strip()  # nilai ga dikenal, dibalikin apa adanya (bukan error)

    if angka == 1:
        return "Lancar"
    elif angka == 2:
        return "DPK"
    elif angka in (3, 4, 5):
        return "NPL"
    else:
        return str(bikole).strip()


def siapkan_data_upload(df_mentah: pd.DataFrame) -> pd.DataFrame:
    """
    File Excel/export mentah (per-rekening) -> DataFrame 9 kolom standar
    dashboard, SEBELUM di-pivot. Kolom di luar 9 ini (termasuk yang di
    KOLOM_DIBUANG) otomatis ga ikut -- ga perlu loop pass-through lagi,
    soalnya abis ini data bakal di-pivot lewat agregasi_untuk_dashboard(),
    dan kolom yang ga jadi bagian GROUP BY/agregasi otomatis kebuang di
    situ juga.
    """
    df = df_mentah.copy()
    df.columns = df.columns.astype(str).str.strip()

    hasil = pd.DataFrame()
    hasil["Posisi Data"] = df["posisi"].apply(_format_posisi_data)
    hasil["Regional Office"] = df["region"].apply(_format_region)
    hasil["Kualitas Kredit"] = df["bikole"].apply(_format_kualitas_kredit)
    hasil["Produk"] = df["produk"].astype(str).str.strip()
    hasil["Realisasi"] = df["tgl_realisasi_int"].apply(_format_realisasi)
    hasil["Risk Grade"] = pd.to_numeric(df["rating_score"], errors="coerce")
    hasil["Jumlah Rekening"] = df["acctno"].astype(str).str.strip()
    hasil["Outstanding (Rp Juta)"] = pd.to_numeric(df["cbal_base"], errors="coerce") / 1_000_000
    hasil["Plafon (Rp Juta)"] = pd.to_numeric(df["plafond"], errors="coerce") / 1_000_000

    return hasil


def agregasi_untuk_dashboard(df: pd.DataFrame) -> pd.DataFrame:
    """PIVOT: dari data per-rekening (bisa jutaan baris) jadi RINGKASAN
    per kombinasi Posisi Data x Produk x Regional Office x Kualitas
    Kredit x Realisasi x Risk Grade. Ini yang bikin data muat di Google
    Sheets (dari jutaan baris jadi paling banyak beberapa ribu baris),
    tanpa kehilangan kemampuan filter dashboard (RO/Kualitas
    Kredit/Realisasi tetap tersimpan sebagai kolom, bukan ilang)."""
    hasil = df.groupby(
        ["Posisi Data", "Produk", "Regional Office", "Kualitas Kredit", "Realisasi", "Risk Grade"],
        as_index=False,
        dropna=False,
    ).agg(
        **{
            "Jumlah Rekening": ("Jumlah Rekening", "count"),
            "Outstanding (Rp Juta)": ("Outstanding (Rp Juta)", "sum"),
            "Plafon (Rp Juta)": ("Plafon (Rp Juta)", "sum"),
        }
    )
    return hasil

@st.cache_resource
def _get_sheets_client():
    """Bikin koneksi ke Google Sheets pakai service account dari secrets.
    @st.cache_resource -> koneksinya dibikin SEKALI doang, dipakai ulang
    terus (bukan connect baru tiap rerun -- itu bikin lambat)."""
    kredensial = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SHEETS_SCOPES
    )
    return gspread.authorize(kredensial)


def period_to_sheet_name(posisi_data: str) -> str:
    """Ubah 'Juli 2026' -> 'Juli_26' (Bulan_YY) -- ini yang dipakai sebagai
    nama tab/worksheet di Google Sheets, satu tab per Posisi Data."""
    bulan, tahun = split_period(posisi_data)
    return f"{bulan}_{str(tahun)[-2:]}"


def _get_or_create_worksheet(sheet_name: str):
    """Buka tab dengan nama sheet_name -- kalau belum ada, bikin baru
    otomatis (kosong)."""
    client = _get_sheets_client()
    spreadsheet = client.open_by_key(st.secrets["sheet"]["sheet_id"])
    try:
        return spreadsheet.worksheet(sheet_name)
    except WorksheetNotFound:
        return spreadsheet.add_worksheet(title=sheet_name, rows=2000, cols=20)
def _normalisasi_kolom(df: pd.DataFrame) -> pd.DataFrame:
    """Bersihin nama KOLOM (bukan isi datanya) -- buang spasi nyempil di
    awal/akhir nama kolom (mis. 'Kualitas Kredit ' -> 'Kualitas Kredit'),
    dan samain beberapa typo/variasi nama yang umum kejadian di file
    Excel (mis. 'Plafond (Rp Juta)' -> 'Plafon (Rp Juta)'). Dipanggil pas
    SIMPAN (save_data_to_sheets) DAN pas BACA (read_data_upload_cached)
    -- biar data yang UDAH kepalang ke-upload dengan nama kolom berantakan
    juga ikut kebenerin begitu dibaca ulang, ga perlu re-upload."""
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()
    rename_map = {
        "Plafond (Rp Juta)": "Plafon (Rp Juta)",
    }
    df = df.rename(columns=rename_map)
    return df


def format_kolom_realisasi(df: pd.DataFrame) -> pd.DataFrame:
    """Ubah kolom 'Realisasi' dari format tanggal YYYYMMDD (misal 20251017)
    jadi format 'Bulan Tahun' (misal 'Oktober 2025') yang dipakai buat
    filter & perhitungan MOB di seluruh app. Kalau kolom 'Realisasi' udah
    berupa string 'Bulan Tahun', dibiarin apa adanya (idempotent, aman
    dipanggil berkali-kali)."""
    df = df.copy()
    if "Realisasi" not in df.columns:
        return df

    def _konversi(nilai):
        teks = str(nilai).strip()
        if teks.isdigit() and len(teks) == 8:
            try:
                tanggal = pd.to_datetime(teks, format="%Y%m%d")
                return f"{BULAN_LIST[tanggal.month - 1]} {tanggal.year}"
            except ValueError:
                return teks
        return teks

    df["Realisasi"] = df["Realisasi"].apply(_konversi)
    return df

def save_data_to_sheets(new_df: pd.DataFrame, posisi_data: str) -> int:
    """Simpan data upload ke tab sesuai Posisi Data, dalam bentuk
    RINGKASAN hasil pivot (bukan data mentah -- lihat
    agregasi_untuk_dashboard). Cuma nimpa baris ringkasan Produk yang
    SAMA kayak yang baru diupload -- Produk lain (diupload Admin lain,
    di waktu yang beda) tetap aman, ga ikut kehapus. Return jumlah baris
    MENTAH yang diproses (buat info ke Admin, bukan jumlah baris ringkasan)."""
    new_df = siapkan_data_upload(new_df)
    jumlah_baris_mentah = len(new_df)
    new_df_ringkasan = agregasi_untuk_dashboard(new_df)

    sheet_name = period_to_sheet_name(posisi_data)
    worksheet = _get_or_create_worksheet(sheet_name)

    existing_df = get_as_dataframe(worksheet, evaluate_formulas=True).dropna(how="all")
    existing_df = _normalisasi_kolom(existing_df) if not existing_df.empty else existing_df

    produk_yang_diupload = new_df_ringkasan["Produk"].dropna().unique().tolist()

    if not existing_df.empty and "Produk" in existing_df.columns:
        sisa_data_lama = existing_df[~existing_df["Produk"].isin(produk_yang_diupload)]
        gabungan = pd.concat([sisa_data_lama, new_df_ringkasan], ignore_index=True)
    else:
        gabungan = new_df_ringkasan

    worksheet.clear()
    set_with_dataframe(worksheet, gabungan)
    st.cache_data.clear()
    return jumlah_baris_mentah


def agregasi_bad_rate_dari_mentah(df_mentah: pd.DataFrame, performance_window_bulan: int) -> pd.DataFrame:
    """
    Olah data vintage mentah (Tabel 2: REKENING, RATING_SCORE, KOL_1...
    KOL_48, dst) LANGSUNG jadi ringkasan Bad Rate per Risk Grade, TANPA
    butuh kolom 'Klasifikasi'/'is_bad' yang dihitung manual di Excel.
    Window observasinya OTOMATIS nyesuain Produk (lihat
    PERFORMANCE_WINDOW_MONTHS), replikasi PERSIS 3 rumus Excel:
      1. Eligible = KOL_{window} PUNYA ISI (rekening udah cukup umur)
      2. Count    = berapa BULAN dari KOL_1..KOL_{window} yang >= 3
      3. is_bad   = 1 kalau Count > 0 (minimal 1 bulan NPL), else 0
    """
    df = df_mentah.copy()
    df.columns = df.columns.astype(str).str.strip()

    kolom_kol_window = f"KOL_{performance_window_bulan}"
    if kolom_kol_window not in df.columns:
        raise ValueError(f"Kolom '{kolom_kol_window}' tidak ditemukan (window {performance_window_bulan} bulan).")

    kolom_window_bersih = df[kolom_kol_window].astype(str).str.strip()
    eligible_mask = df[kolom_kol_window].notna() & (kolom_window_bersih != "")
    df_eligible = df[eligible_mask].copy()

    if df_eligible.empty:
        return pd.DataFrame(columns=["Risk Grade", "Jumlah Bad", "Jumlah Rekening", "Bad Rate (%)"])

    kolom_kol_range = [f"KOL_{i}" for i in range(1, performance_window_bulan + 1) if f"KOL_{i}" in df_eligible.columns]
    nilai_kol = df_eligible[kolom_kol_range].apply(pd.to_numeric, errors="coerce")
    jumlah_bulan_bad = (nilai_kol >= 3).sum(axis=1)

    df_eligible["is_bad_hitung"] = (jumlah_bulan_bad > 0).astype(int)

    hasil = df_eligible.groupby("RATING_SCORE", as_index=False).agg(
        **{
            "Jumlah Bad": ("is_bad_hitung", "sum"),
            "Jumlah Rekening": ("REKENING", "count"),
        }
    )
    hasil = hasil.rename(columns={"RATING_SCORE": "Risk Grade"})
    hasil["Bad Rate (%)"] = (hasil["Jumlah Bad"] / hasil["Jumlah Rekening"] * 100).round(2)
    hasil = hasil.sort_values("Risk Grade").reset_index(drop=True)

    return hasil


def period_to_badrate_sheet_name(posisi_data: str) -> str:
    """'Juli 2026' -> 'Juli_26_BadRate' -- tab TERPISAH dari tab data
    Sebaran Risk Grade utama, khusus nyimpen ringkasan Bad Rate."""
    return f"{period_to_sheet_name(posisi_data)}_BadRate"


def save_bad_rate_to_sheets(df_mentah: pd.DataFrame, posisi_data: str, produk: str) -> int:
    """Olah data vintage mentah (KOL_1...KOL_48, dst) jadi ringkasan Bad
    Rate per Risk Grade (lewat agregasi_bad_rate_dari_mentah), simpan ke
    tab '..._BadRate'. Cuma nimpa baris ringkasan Produk yang SAMA kayak
    yang baru diupload -- Produk lain tetap aman, sama pola-nya kayak
    save_data_to_sheets()."""
    window = get_product_performance_window(produk)
    hasil_ringkasan = agregasi_bad_rate_dari_mentah(df_mentah, window)
    jumlah_baris_mentah = len(df_mentah)

    if hasil_ringkasan.empty:
        return 0

    hasil_ringkasan["Posisi Data"] = posisi_data
    hasil_ringkasan["Produk"] = produk
    hasil_ringkasan["Performance Window"] = f"{window} Bulan"
    hasil_ringkasan = hasil_ringkasan[[
        "Posisi Data", "Produk", "Performance Window",
        "Risk Grade", "Jumlah Bad", "Jumlah Rekening", "Bad Rate (%)",
    ]]

    sheet_name = period_to_badrate_sheet_name(posisi_data)
    worksheet = _get_or_create_worksheet(sheet_name)

    existing_df = get_as_dataframe(worksheet, evaluate_formulas=True).dropna(how="all")
    existing_df = _normalisasi_kolom(existing_df) if not existing_df.empty else existing_df

    if not existing_df.empty and "Produk" in existing_df.columns:
        sisa_data_lama = existing_df[existing_df["Produk"] != produk]
        gabungan = pd.concat([sisa_data_lama, hasil_ringkasan], ignore_index=True)
    else:
        gabungan = hasil_ringkasan

    worksheet.clear()
    set_with_dataframe(worksheet, gabungan)
    st.cache_data.clear()
    return jumlah_baris_mentah


@st.cache_data(show_spinner=False, ttl=60)
def read_data_upload_cached(posisi_data: str):
    """Baca data dari TAB Google Sheets yang sesuai Posisi Data, di-cache 60
    detik per periode (dibersihin manual pas ada upload baru lewat
    save_data_to_sheets). Return None kalau tab buat periode itu belum ada
    sama sekali (belum pernah di-upload) atau gagal konek."""
    try:
        sheet_name = period_to_sheet_name(posisi_data)
        client = _get_sheets_client()
        spreadsheet = client.open_by_key(st.secrets["sheet"]["sheet_id"])
        worksheet = spreadsheet.worksheet(sheet_name)  # raise kalau belum ada

        df = get_as_dataframe(worksheet, evaluate_formulas=True)
        df = _normalisasi_kolom(df)  # <-- baris baru: bersihin nama kolom pas dibaca (fix data lama yang udah kepalang ke-upload)
        df = df.dropna(how="all")  # buang baris kosong sisa dari sheet
        if df.empty:
            return None

        # Sheets kadang balikin angka sebagai teks -- pastikan kolom numerik
        # beneran numerik biar perhitungan (PSI, Bad Rate, dll) ga error.
        for kolom in ["Risk Grade", "Jumlah Rekening", "Outstanding (Rp Juta)", "Plafon (Rp Juta)", "Jumlah Bad"]:
            if kolom in df.columns:
                df[kolom] = pd.to_numeric(df[kolom], errors="coerce")

        return df
    except Exception:
        return None


def period_has_data(posisi_data: str) -> bool:
    """Cek cepat apakah suatu Posisi Data udah ada datanya (tab-nya ada &
    isinya ga kosong) -- dipakai buat notifikasi peringatan di atas
    dashboard, biar Admin/User langsung tau tanpa perlu scroll ke bawah."""
    return read_data_upload_cached(posisi_data) is not None


# ----------------------------------------------------------------------------
# POSISI DATA GLOBAL -- masih file lokal (disengaja, lihat obrolan
# sebelumnya: risikonya kecil kalau ilang pas restart, ga separah Data
# Bulanan, jadi ga perlu ikut pindah ke Sheets).
# ----------------------------------------------------------------------------
BULAN_LIST = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ACTIVE_PERIOD_PATH = DATA_DIR / "active_period.txt"
DEFAULT_ACTIVE_PERIOD = "Juli 2026"


def get_active_period() -> str:
    try:
        if ACTIVE_PERIOD_PATH.exists():
            value = ACTIVE_PERIOD_PATH.read_text(encoding="utf-8").strip()
            if value:
                return value
    except Exception:
        pass

    # Belum pernah di-set sama sekali -> default ke Posisi Data TERAKHIR
    # yang beneran ada datanya di spreadsheet (bukan tanggal hardcode).
    try:
        available = list_available_periods()  # udah terurut kronologis
        if available:
            return available[-1]
    except Exception:
        pass

    return DEFAULT_ACTIVE_PERIOD


def save_active_period(period: str) -> None:
    ACTIVE_PERIOD_PATH.write_text(str(period), encoding="utf-8")


def split_period(period: str):
    parts = str(period).rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0], int(parts[1])
    return "Juli", 2026

@st.cache_data(show_spinner = False, ttl=60)
def list_available_periods() -> list:
    try:
        client =_get_sheets_client()
        spreadsheet = client.open_by_key(st.secrets["sheet"]["sheet_id"])
    except Exception:
        return []

    hasil = []
    for ws in spreadsheet.worksheets():
        parts = ws.title.split("_")
        if len(parts) == 2 and parts [0] in BULAN_LIST and parts[1].isdigit() and len(parts[1])==2:
            bulan = parts[0]
            tahun = 2000 + int(parts[1])
            hasil.append((tahun, BULAN_LIST.index(bulan),f"{bulan} {tahun}"))
        hasil.sort()
        return [p[2] for p in hasil]

@st.cache_data(show_spinner=False, ttl=60)
def list_available_periods() -> list:
    """Scan semua tab di spreadsheet, balikin list Posisi Data (string
    'Bulan Tahun') yang tab-nya ADA, diurutin KRONOLOGIS. Dipakai buat
    chart MOB (perlu tau semua Posisi Data yang pernah di-upload)."""
    try:
        client = _get_sheets_client()
        spreadsheet = client.open_by_key(st.secrets["sheet"]["sheet_id"])
    except Exception:
        return []

    hasil = []
    for ws in spreadsheet.worksheets():
        parts = ws.title.split("_")
        if len(parts) == 2 and parts[0] in BULAN_LIST and parts[1].isdigit() and len(parts[1]) == 2:
            bulan = parts[0]
            tahun = 2000 + int(parts[1])
            hasil.append((tahun, BULAN_LIST.index(bulan), f"{bulan} {tahun}"))
    hasil.sort()
    return [p[2] for p in hasil]


def _hitung_mob(realisasi: str, posisi_data: str) -> int:
    """MOB (Month on Book) = jarak bulan antara Realisasi (bulan pinjaman
    dicairkan) dan Posisi Data (snapshot observasi). MOB 0 = bulan yang
    sama, MOB 3 = 3 bulan setelah realisasi, dst."""
    r_bulan, r_tahun = split_period(realisasi)
    p_bulan, p_tahun = split_period(posisi_data)
    r_idx = BULAN_LIST.index(r_bulan)
    p_idx = BULAN_LIST.index(p_bulan)
    return (p_tahun - r_tahun) * 12 + (p_idx - r_idx)


def _period_sort_key(period: str):
    """Buat bandingin 2 Posisi Data secara kronologis (tahun, urutan
    bulan) -- dipakai buat batesin MOB chart cuma sampai Posisi Data yang
    lagi AKTIF, ga ikut nampilin periode "masa depan" yang udah di-upload
    tapi belum jadi Posisi Data aktif saat ini."""
    bulan, tahun = split_period(period)
    return (tahun, BULAN_LIST.index(bulan))


@st.cache_data(show_spinner=False, ttl=60)
def get_mob_bad_rate(produk: str, realisasi_target: str, regional_office: str, posisi_data_aktif: str, basis: str = "Jumlah Rekening") -> pd.DataFrame:
    """Vintage curve: buat 1 cohort Realisasi tertentu, scan Posisi Data
    yang ada -- TAPI cuma sampai posisi_data_aktif (ga ikut Posisi Data
    "masa depan" yang udah di-upload tapi belum jadi Posisi Data aktif
    saat ini). Bad Rate (NPL%) dihitung tiap snapshot. MOB dihitung
    otomatis dari Realisasi vs Posisi Data (ga perlu kolom baru di Excel
    upload). MOB negatif (Posisi Data sebelum Realisasi) dilewatin."""
    periods = list_available_periods()
    batas = _period_sort_key(posisi_data_aktif)

    rows = []
    for posisi_data in periods:
        if _period_sort_key(posisi_data) > batas:
            continue  # lewatin Posisi Data yang lebih baru dari yang lagi aktif
        mob = _hitung_mob(realisasi_target, posisi_data)
        if mob < 0:
            continue
        df = read_data_upload_cached(posisi_data)
        if df is None:
            continue
        try:
            mask = pd.Series(True, index=df.index)
            if produk != "All" and "Produk" in df.columns:
                mask &= df["Produk"] == produk
            if regional_office != "All" and "Regional Office" in df.columns:
                mask &= df["Regional Office"] == regional_office
            if "Realisasi" in df.columns:
                mask &= df["Realisasi"] == realisasi_target
            sub = df[mask]
            if sub.empty or basis not in sub.columns:
                continue
            # SUM buat basis apa pun -- data yang dibaca UDAH hasil pivot.
            agg_func = "sum"
            total = sub[basis].agg(agg_func)
            if total <= 0:
                continue
            npl = sub[sub["Kualitas Kredit"] == "NPL"][basis].agg(agg_func)
            rows.append({"MOB": mob, "Posisi Data": posisi_data, "Bad Rate (%)": npl / total * 100})
        except Exception:
            continue

    if not rows:
        return pd.DataFrame(columns=["MOB", "Posisi Data", "Bad Rate (%)"])
    return pd.DataFrame(rows).sort_values("MOB").reset_index(drop=True)


def get_mob_gaps(mob_df: pd.DataFrame) -> list:
    """Balikin list angka MOB yang HILANG (bolong) di antara MOB
    terkecil & terbesar yang ada di mob_df -- artinya ada Posisi Data
    yang belum di-upload buat cohort Realisasi ini, jadi trajectory-nya
    ga utuh/berurutan. Balikin list kosong kalau udah lengkap/berurutan."""
    if mob_df.empty or len(mob_df) < 2:
        return []
    existing = set(int(m) for m in mob_df["MOB"])
    full_range = set(range(min(existing), max(existing) + 1))
    return sorted(full_range - existing)


# ----------------------------------------------------------------------------
# ADMIN AUTH
# ----------------------------------------------------------------------------
def get_admin_code():
    try:
        return st.secrets["admin"]["code"]
    except Exception:
        return None


# ----------------------------------------------------------------------------
# KONSTANTA BISNIS -- baseline PSI, rentang Risk Grade, cut-off, Performance
# Window & warna chart per produk, Gini dummy.
# ----------------------------------------------------------------------------
SEBARAN_MODEL_BASELINE = {
    "KPP": {1: 18.92, 2: 18.62, 3: 24.43, 4: 16.43, 5: 9.23, 6: 6.42, 7: 5.96},
    "Briguna Karya": {1: 23.35, 2: 27.88, 3: 25.43, 4: 12.86, 5: 5.91, 6: 2.96, 7: 1.61},
    "Briguna Purna": {1: 28.11, 2: 10.93, 3: 25.61, 4: 4.09, 5: 6.33, 6: 6.39, 7: 11.76, 8: 3.52, 9: 3.26},
    "Briguna Prapurna": {1: 9.51, 2: 21.08, 3: 28.92, 4: 19.78, 5: 13.88, 6: 6.29, 7: 0.48, 8: 0.06},
    "KKB": {1: 16.13, 2: 21.51, 3: 25.81, 4: 19.35, 5: 10.75, 6: 6.45},
    "Kartu Kredit": {1: 0.03, 2: 0.47, 3: 9.43, 4: 26.23, 5: 10.11, 6: 21.39, 7: 16.19, 8: 11.80, 9: 2.91, 10: 1.45},
    "All": {1: 6, 2: 12, 3: 15, 4: 17, 5: 16, 6: 12, 7: 9, 8: 6, 9: 4, 10: 3},
}

RISK_GRADE_RANGE = {
    "KPP": list(range(1, 8)),
    "Briguna Karya": list(range(1, 8)),
    "Briguna Purna": list(range(1, 10)),
    "Briguna Prapurna": list(range(1, 9)),
    "KKB": list(range(1, 7)),
    "Kartu Kredit": list(range(1, 11)),
    "All": list(range(1, 11)),
}

CUT_OFF_GRADE = {
    "KPP": 7,
    "Briguna Karya": 6,
    "Briguna Purna": 8,
    "Briguna Prapurna": 7,
    "KKB": 6,
    "Kartu Kredit": 8,
    "All": 10,
}

# Batas Risk Grade Approve (auto-approve) vs Override (butuh keputusan
# manual) -- DITURUNIN OTOMATIS dari CUT_OFF_GRADE (bukan angka terpisah).
# Override = Risk Grade >= CUT_OFF_GRADE, Approve = di bawahnya.
# Contoh: KPP cut off = 7 -> Approve = 1-6, Override = 7 ke atas.
APPROVE_MAX_GRADE = {produk: cut_off - 1 for produk, cut_off in CUT_OFF_GRADE.items()}

PERFORMANCE_WINDOW_MONTHS = {
    "KPP": 24,
    "Kartu Kredit": 36,
    "Briguna Karya": 36,
    "Briguna Purna": 36,
    "Briguna Prapurna": 12,
    "KKB": 24,
}

PRODUCT_CHART_COLORS = {
    "KPP": "#E67E22",
    "Kartu Kredit": "#1565C0",
    "Briguna Karya": "#B8860B",
    "Briguna Purna": "#1B8A4B",
    "Briguna Prapurna": "#6A3D9A",
    "KKB": "#C0392B",
}

DUMMY_GINI_BY_PRODUK = {
    "All": 0,
    "KPP": 0.4800,
    "Briguna Karya": 0.3591,
    "Briguna Purna": 0.3512,
    "Briguna Prapurna": 0.2988,
    "KKB": 0.4216,
    "Kartu Kredit": 0.3241,
}


def get_product_performance_window(produk: str) -> int:
    return PERFORMANCE_WINDOW_MONTHS.get(produk, 12)


# ----------------------------------------------------------------------------
# DATA: dummy fallback + baca/filter dari Google Sheets
# ----------------------------------------------------------------------------
def get_dummy_data(produk: str, realisasi_mode: str, regional_office: str, kualitas_kredit: str, posisi_data: str) -> pd.DataFrame:
    seed = abs(hash((produk, realisasi_mode, regional_office, kualitas_kredit, posisi_data))) % (2**32)
    rng = np.random.default_rng(seed)
    risk_grades = list(range(1, 11))
    base = np.array([2, 9, 14, 22, 30, 38, 34, 26, 12, 4], dtype=float)
    jumlah_rekening = (base * rng.uniform(80, 120, size=10)).astype(int)
    outstanding = (jumlah_rekening * rng.uniform(3.5, 6.5, size=10)).round(1)
    return pd.DataFrame(
        {
            "Risk Grade": risk_grades,
            "Jumlah Rekening": jumlah_rekening,
            "Outstanding (Rp Juta)": outstanding,
        }
    )


def get_dummy_bad_rate(produk: str, grade_range: list, seed_extra: str) -> pd.DataFrame:
    performance_months = get_product_performance_window(produk)
    performance_label = f"{performance_months} Bulan"

    seed = abs(hash((produk, seed_extra, "bad_rate"))) % (2**32)
    rng = np.random.default_rng(seed)

    n = len(grade_range)
    base_curve = np.linspace(0.3, 22, n) ** 1.15
    noise = rng.uniform(0.85, 1.15, size=n)
    bad_rate = np.clip(base_curve * noise, 0.1, 40)

    rows = []
    for grade, br in zip(grade_range, bad_rate):
        rows.append({"Risk Grade": grade, "Performance Window": performance_label, "Bad Rate (%)": round(br, 2)})

    return pd.DataFrame(rows)


def load_uploaded_table(produk, realisasi_mode, regional_office, kualitas_kredit, posisi_data):
    data_raw = read_data_upload_cached(posisi_data)
    if data_raw is None:
        return None
    try:
        mask = pd.Series(True, index=data_raw.index)
        if produk != "All":
            mask &= data_raw["Produk"] == produk
        if regional_office != "All":
            mask &= data_raw["Regional Office"] == regional_office
        if kualitas_kredit != "All":
            mask &= data_raw["Kualitas Kredit"] == kualitas_kredit
        if realisasi_mode != "All":
            mask &= data_raw["Realisasi"] == realisasi_mode
        if "Posisi Data" in data_raw.columns:
            mask &= data_raw["Posisi Data"] == posisi_data

        filtered = data_raw[mask]

        has_plafon = "Plafon (Rp Juta)" in filtered.columns
        agg_dict = {
            # SUM (bukan count) -- data yang dibaca di sini UDAH hasil pivot
            # (1 baris = 1 kombinasi RO/Kualitas/Realisasi/RiskGrade, dan
            # "Jumlah Rekening" udah berupa ANGKA HASIL HITUNGAN, bukan
            # nomor rekening mentah lagi).
            "Jumlah Rekening": "sum",
            "Outstanding (Rp Juta)": "sum",
        }
        if has_plafon:
            agg_dict["Plafon (Rp Juta)"] = "sum"

        table_df = (
            filtered.groupby("Risk Grade", as_index=False)
            .agg(agg_dict)
            .sort_values("Risk Grade")
        )
        if not has_plafon:
            table_df["Plafon (Rp Juta)"] = None  # kolom opsional -- data lama yang belum ada Plafon tetep jalan
        return table_df
    except Exception as e:
        st.error("Gagal baca file Data, pakai data dummy dulu. Detail error lengkap:")
        st.exception(e)
        return None


def load_uploaded_bad_rate(produk, realisasi_mode, regional_office, kualitas_kredit, posisi_data):
    """Baca data Bad Rate hasil upload dari tab TERPISAH '..._BadRate'
    (BUKAN dari tab utama data_raw). Data di tab ini UDAH berupa ringkasan
    per Risk Grade (bukan mentah), jadi tinggal difilter Posisi Data &
    Produk -- ga perlu filter Regional Office/Kualitas Kredit/Realisasi
    (data Bad Rate ga dipecah sampai level itu, cuma per Produk+Posisi
    Data)."""
    sheet_name = period_to_badrate_sheet_name(posisi_data)
    try:
        worksheet = _get_or_create_worksheet(sheet_name)
        df = get_as_dataframe(worksheet, evaluate_formulas=True).dropna(how="all")
    except Exception:
        return None

    if df.empty:
        return None

    df = _normalisasi_kolom(df)

    if "Produk" not in df.columns:
        return None

    df = df[df["Produk"] == produk].copy()
    if df.empty:
        return None

    for kolom in ["Risk Grade", "Jumlah Bad", "Jumlah Rekening", "Bad Rate (%)"]:
        if kolom in df.columns:
            df[kolom] = pd.to_numeric(df[kolom], errors="coerce")

    return df


def get_quality_percentages(produk, realisasi_mode, regional_office, posisi_data, basis="Jumlah Rekening"):
    """basis: 'Jumlah Rekening' (default, hitung berdasarkan JUMLAH nasabah)
    atau 'Outstanding (Rp Juta)' (hitung berdasarkan NOMINAL Rp yang
    berisiko -- bisa beda jauh dari basis Jumlah Rekening kalau nasabah
    NPL kebetulan pinjemannya lebih besar/kecil dari rata-rata)."""
    data_raw = read_data_upload_cached(posisi_data)
    if data_raw is not None:
        try:
            required_cols = {"Kualitas Kredit", basis}

            if required_cols.issubset(data_raw.columns):
                mask = pd.Series(True, index=data_raw.index)

                if produk != "All" and "Produk" in data_raw.columns:
                    mask &= data_raw["Produk"] == produk
                if regional_office != "All" and "Regional Office" in data_raw.columns:
                    mask &= data_raw["Regional Office"] == regional_office
                if realisasi_mode != "All" and "Realisasi" in data_raw.columns:
                    mask &= data_raw["Realisasi"] == realisasi_mode
                if "Posisi Data" in data_raw.columns:
                    mask &= data_raw["Posisi Data"] == posisi_data

                filtered = data_raw[mask]

                if not filtered.empty:
                    # SUM buat basis apa pun -- data yang dibaca UDAH hasil
                    # pivot, "Jumlah Rekening" di sini udah angka hasil
                    # hitungan (bukan nomor rekening mentah lagi).
                    agg_func = "sum"
                    total = filtered[basis].agg(agg_func)
                    if total > 0:
                        kualitas = filtered.groupby("Kualitas Kredit")[basis].agg(agg_func)
                        lancar = kualitas.get("Lancar", 0)
                        dpk = kualitas.get("DPK", kualitas.get("Dalam Perhatian Khusus", 0))
                        npl = kualitas.get("NPL", 0)
                        npl += kualitas.get("Kurang Lancar", 0)
                        npl += kualitas.get("Macet", 0)
                        return {
                            "Lancar": lancar / total * 100,
                            "DPK": dpk / total * 100,
                            "NPL": npl / total * 100,
                            "ALL": 100.0,
                        }
        except Exception:
            pass

    return None


def get_approve_override_pct(produk, realisasi_mode, regional_office, posisi_data, basis="Jumlah Rekening"):
    """Persentase Risk Grade yang masuk kategori Approve (auto-approve,
    grade rendah) vs Override (butuh keputusan manual, grade tinggi),
    berdasarkan basis (Jumlah Rekening / Outstanding). Batasnya beda per
    produk (lihat APPROVE_MAX_GRADE) -- makanya tiap BARIS dibandingin ke
    batas PRODUKNYA SENDIRI (bukan 1 angka global), penting banget pas
    Produk = "All" (data campuran banyak produk sekaligus)."""
    data_raw = read_data_upload_cached(posisi_data)
    if data_raw is None:
        return None
    try:
        required_cols = {"Risk Grade", "Produk", basis}
        if not required_cols.issubset(data_raw.columns):
            return None

        mask = pd.Series(True, index=data_raw.index)
        if produk != "All" and "Produk" in data_raw.columns:
            mask &= data_raw["Produk"] == produk
        if regional_office != "All" and "Regional Office" in data_raw.columns:
            mask &= data_raw["Regional Office"] == regional_office
        if realisasi_mode != "All" and "Realisasi" in data_raw.columns:
            mask &= data_raw["Realisasi"] == realisasi_mode
        if "Posisi Data" in data_raw.columns:
            mask &= data_raw["Posisi Data"] == posisi_data

        filtered = data_raw[mask].copy()
        if filtered.empty:
            return None

        # SUM buat basis apa pun -- data yang dibaca UDAH hasil pivot,
        # "Jumlah Rekening" di sini udah angka hasil hitungan (bukan
        # nomor rekening mentah lagi).
        agg_func = "sum"
        total = filtered[basis].agg(agg_func)
        if total <= 0:
            return None

        # Batas Approve/Override PER BARIS, sesuai Produk baris itu sendiri.
        filtered["_approve_max"] = filtered["Produk"].map(APPROVE_MAX_GRADE).fillna(APPROVE_MAX_GRADE["All"])
        approve_row_mask = filtered["Risk Grade"] <= filtered["_approve_max"]

        approve_sum = filtered[approve_row_mask][basis].agg(agg_func)
        override_sum = filtered[~approve_row_mask][basis].agg(agg_func)

        return {
            "Approve": approve_sum / total * 100,
            "Override": override_sum / total * 100,
        }
    except Exception:
        return None


def compute_psi_vs_baseline(df_current: pd.DataFrame, produk_target: str, grade_range: list) -> float:
    baseline_dict = SEBARAN_MODEL_BASELINE.get(produk_target)
    if baseline_dict is None:
        return None

    baseline_arr = np.array([float(baseline_dict.get(g, 0)) for g in grade_range]) / 100.0

    current_series = df_current.set_index("Risk Grade")["Jumlah Rekening"].reindex(grade_range, fill_value=0)
    current_arr = current_series.to_numpy().astype(float)

    if current_arr.sum() == 0:
        return None
    current_pct = current_arr / current_arr.sum()

    eps = 1e-4
    baseline_safe = np.clip(baseline_arr, eps, None)
    current_safe = np.clip(current_pct, eps, None)

    diff = baseline_arr - current_pct
    ln_ratio = np.log(baseline_safe / current_safe)
    return float((diff * ln_ratio).sum())


# ----------------------------------------------------------------------------
# EXPORT CHART -> JPG (di-cache biar ga render ulang lewat kaleido tiap rerun)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def fig_to_jpg_cached(fig_json: str, width: int, height: int, scale: int) -> bytes:
    import plotly.io as pio
    fig = pio.from_json(fig_json)
    return fig.to_image(format="jpg", width=width, height=height, scale=scale)