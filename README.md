# 💹 AI Trading Terminal 2.0: Analisis Komprehensif & Peramalan Saham Big 4 Bank Indonesia

Proyek Data Science hulu-ke-hilir (*End-to-End*) untuk analisis teknikal, korelasi makroekonomi, dan peramalan harga saham **Big 4 Bank Indonesia** (BBCA, BBRI, BMRI, BBNI) dengan integrasi Pipeline Data otomatis Apache Airflow, Database Relasional Star Schema, dan Machine Learning **Ridge Regression**.

---

## 👨‍💻 Identitas Peneliti / Pengembang
* **Nama:** Miqdad Asyraf Rizqullah
* **NIM:** E1E124041
* **Program Studi:** Teknik Informatika
* **Fakultas:** Teknik
* **Institusi:** Universitas Haluoleo
* **Mata Kuliah:** Data Science

---

## 📁 Struktur Direktori Proyek

```text
├── AI.ipynb                 # Notebook Eksperimen Data Science (EDA, Feature Engineering, Modeling, Evaluasi)
├── app.py                   # Aplikasi Dashboard Interaktif Web (Streamlit)
├── data_clean_stock.csv     # Dataset Bersih Hasil Olahan Pipeline (16 Tahun Bursa)
├── requirements.txt         # Daftar Dependensi Library Python
├── docker-compose.yaml      # Orkestrasi Container Apache Airflow & Database
├── dags/                    # Direktori DAG (Directed Acyclic Graph) Airflow
│   ├── etl_api_economy_wb.py# Script ETL Otomatis Yahoo Finance & World Bank
│   └── data/                # Data Dimensi dan Fakta CSV
└── config/
    └── airflow.cfg          # Konfigurasi Layanan Airflow
```

---

## 🎯 Metrik Akurasi Evaluasi Model (Data Uji)

Model dievaluasi menggunakan data testing berurutan (*Time-Series Sequential Split* 80:20 tanpa acak) untuk mencegah *Data Leakage*:

| Emiten | R-Squared ($R^2$) | MAE (Rp) | RMSE (Rp) | MAPE (%) | Status Model |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **BBCA** | **0.9974** | Rp 41.51 | Rp 53.13 | **0.53%** | Good Fit |
| **BBRI** | **0.9971** | Rp 22.02 | Rp 28.10 | **0.59%** | Good Fit |
| **BMRI** | **0.9961** | Rp 26.73 | Rp 35.05 | **0.58%** | Good Fit |
| **BBNI** | **0.9932** | Rp 23.56 | Rp 30.91 | **0.59%** | Good Fit |

---

## 🚀 Panduan Menjalankan Proyek (Quick Start)

Dosen / Penguji dapat menjalankan proyek ini dengan sangat mudah:

### 1. Menjalankan Dashboard Streamlit (Paling Cepat)
Proyek ini telah dilengkapi dataset cadangan mandiri (`data_clean_stock.csv`). Dosen **tidak diwajibkan menyalakan Docker/MySQL** hanya untuk menguji dashboard dan model AI:

```bash
# 1. Install library yang dibutuhkan
pip install -r requirements.txt

# 2. Jalankan dashboard Streamlit
streamlit run app.py
```
Aplikasi akan langsung terbuka otomatis di browser pada alamat: `http://localhost:8501`.

### 2. Membuka Eksperimen Data Science (Jupyter Notebook)
Seluruh visualisasi grafik (Line Chart Tren, Boxplot Volatilitas, Heatmap Korelasi, Grid Actual vs Predicted, dan Forecasting 30 Hari) sudah tersimpan utuh di dalam file:
```bash
jupyter notebook AI.ipynb
```

### 3. Menjalankan Pipeline ETL Apache Airflow (Opsional)
Jika ingin menguji ulang proses otomatisasi data pipeline dari API bursa ke database:
```bash
# Nyalakan kontainer Airflow
docker compose up -d
```
Buka antarmuka Airflow di `http://localhost:8080` (Username: `airflow`, Password: `airflow`).
