# OEE Dashboard (Streamlit) - PROMED (template)

Ini adalah template dashboard OEE berbasis Streamlit yang mengambil data dari Google Sheets (CSV export).
Cocok untuk pilot digitalisasi OEE / modul pelatihan.

## Langkah cepat deploy (Streamlit Cloud)

1. **Buat repository baru** di GitHub, mis. `oee-dashboard-streamlit`.
2. Tambahkan file:
   - `app.py` (isi sesuai file di repo ini)
   - `requirements.txt`
   - `README.md`
3. Commit & push ke GitHub.
4. Buka https://share.streamlit.io → login dengan GitHub → New app → pilih repo dan branch → pilih `app.py` → Deploy.
5. Setelah deploy, buka halaman Streamlit yang diberikan.

## Konfigurasi Google Sheet
- Buka Google Sheet kamu → **File → Share → Get link** → ubah menjadi **Anyone with the link — Viewer**.
- Ambil **Sheet ID** dari URL Google Sheet (bagian setelah `/d/`).
  Contoh:
  `https://docs.google.com/spreadsheets/d/1qMtaUtEgb2ei64NTzpr_dksoxjSm2TCWX1vqgDusGYs/edit#gid=0`
  → Sheet ID = `1qMtaUtEgb2ei64NTzpr_dksoxjSm2TCWX1vqgDusGYs`
- Masukkan ID tersebut di sidebar aplikasi Streamlit (field "Google Sheet ID") lalu klik `Load data`.

## Catatan penting
- Untuk menghitung **Performance** dengan benar, sediakan **Ideal rate** (pcs per minute) di sheet (kolom Speed / Ideal Rate) atau isi di sidebar.
- Pastikan header kolom konsisten (tanggal, shift, mesin, good, reject, planned, actual, downtime). Aplikasi sudah mencoba mendeteksi beberapa variasi nama kolom otomatis (Indonesia/English).
- Jika data besar, pertimbangkan pindah ke Supabase / database agar query lebih cepat.

## Pengembangan selanjutnya
- Menambahkan autentikasi dan role (operator vs manager).
- Menyimpan data melalui API (Supabase / Firebase) daripada mengandalkan public CSV.
- Menambahkan modul AI untuk insight otomatis (anomaly detection / rekomendasi tindakan).

