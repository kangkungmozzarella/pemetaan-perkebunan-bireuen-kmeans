# Pemetaan Geospasial Hasil Perkebunan Kabupaten Bireuen

Sistem pemetaan geospasial hasil perkebunan di Kabupaten Bireuen menggunakan algoritma **K-Means Clustering**. Setiap kecamatan dikelompokkan ke dalam tiga cluster tingkat produksi: **Rendah**, **Sedang**, dan **Tinggi**.

## Data
- `DATA DONE.xlsx` — data sumber: produksi & produktivitas 17 kecamatan, komoditas **Karet, Kelapa, Pinang**, tahun **2020–2024**.
- `perkebunan_bireuen.csv` — hasil cleaning dari `DATA DONE.xlsx` oleh notebook (255 baris).
- `Bireuen.shp` / `.dbf` / `.shx` — shapefile batas wilayah Kabupaten Bireuen.

Variabel clustering: `Produksi_Ton` dan `Produktivitas_KgHa` (dinormalisasi Min-Max).

## Metode
1. Data cleaning: baris total dibuang, nama kecamatan diseragamkan, nilai teks diubah menjadi angka.
2. Clustering dijalankan terpisah untuk setiap kombinasi komoditas × tahun dengan `KMeans(n_clusters=3, random_state=42)`.
3. Label cluster diurutkan berdasarkan rata-rata `Produksi_Ton` (1 = Rendah, 2 = Sedang, 3 = Tinggi).
4. Evaluasi menggunakan **Silhouette Score** dan **Davies-Bouldin Index (DBI)**.

## Struktur Proyek
```
kmeans.ipynb                 Notebook analisis K-Means (menghasilkan file untuk Flask)
app.py                       Aplikasi web Flask
flask_app/static/data/       Hasil notebook (JSON/CSV) yang dibaca app.py
flask_app/static/models/     kmeans_results.pkl
static/images/maps/          Peta cluster per komoditas per tahun (PNG)
templates/                   Template HTML
```

## Cara Menjalankan
1. Install dependensi:
   ```
   pip install -r requirements.txt
   ```
2. Jalankan `kmeans.ipynb` untuk membuat ulang file hasil dan peta (wajib setiap kali `DATA DONE.xlsx` berubah).
3. Jalankan aplikasi:
   ```
   python app.py
   ```
4. Buka `http://localhost:5000`. Login admin: `admin` / `admin123`.

## Halaman & API
| Route | Keterangan |
|---|---|
| `/` | Beranda publik |
| `/dashboard` | Ringkasan clustering (login) |
| `/dataset` | Tabel dataset (login) |
| `/dataset/download` | Download CSV dataset bersih (login) |
| `/hasil-analisis` | Hasil & evaluasi K-Means (login) |
| `/users` | Manajemen user (login) |
| `/tentang` | Tentang penelitian |
| `/api/summary` | Ringkasan semua komoditas & tahun |
| `/api/clustering/<komoditas>/<tahun>` | Hasil clustering, misal `/api/clustering/Karet/2024` |
| `/api/evaluasi` | Tabel evaluasi Silhouette & DBI |
| `/api/peta/<komoditas>/<tahun>` | URL gambar peta |
| `/api/status` | Status ketersediaan file hasil notebook |
