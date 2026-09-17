# Monitoring CRS Konsumer — Dashboard (Grand Design)

Skeleton dashboard Streamlit berdasarkan sketsa wireframe, tema warna BRI.

## Cara jalanin di VS Code

```bash
python -m venv venv
venv\Scripts\activate      # Windows
# atau: source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
streamlit run app.py
```

## Struktur file

```
crs_dashboard/
├── app.py              # seluruh logic & layout dashboard
├── requirements.txt
├── assets/
│   ├── logo_bri.png        # taruh logo BRI asli di sini (opsional, ada fallback placeholder)
│   └── logo_danantara.png  # taruh logo Danantara asli di sini
└── README.md
```

## Yang masih placeholder / menyusul (ditandai `# TODO` di app.py)

1. **Logo** — kalau `assets/logo_bri.png` & `assets/logo_danantara.png` belum ada,
   otomatis tampil kotak placeholder putus-putus supaya layout tetap rapi.
   Tinggal drop file PNG (background transparan disarankan) ke folder `assets/`.
2. **Data** — semua angka di tabel & chart masih random dummy (`get_dummy_data()`),
   siap diganti dengan query data asli begitu sumber datanya ditentukan.
3. **Relasi Regional Office ↔ Branch Office** — di sketsa, Branch Office dicoret,
   sementara ini diperlakukan sebagai "Branch Office baru aktif setelah pilih
   Regional Office tertentu". Aturan pastinya menyusul.
4. **Formula Gini & PSI** — kartu KPI sudah ada di layout (posisi kanan bawah),
   tapi rumus perhitungan aktual belum diisi (masih dummy value).
5. **Format filter "Realisasi" (yyyy-mm)** — dropdown sudah disiapkan, tinggal
   dihubungkan ke date picker / data realisasi asli.

## Palet warna yang dipakai

| Nama                | Hex       | Pemakaian                          |
|----------------------|-----------|-------------------------------------|
| Navy                 | `#012A5E`| Header gradient, teks judul         |
| Nusantara Blue       | `#0857C3`| Primary brand / header gradient     |
| Cakrawala Blue       | `#307FE2`| Aksen interaktif                    |
| Mentari Blue         | `#71C5EB`| Bar chart (jumlah rekening)         |
| Oranye risiko        | `#F36F21`| Line chart (outstanding), aksen KPI PSI |
| Background           | `#F4F7FB`| Latar halaman                       |

Warna diambil dari hasil rebranding resmi BRI (Nusantara/Cakrawala/Mentari Blue).
