import pandas as pd
from sqlalchemy import create_engine
engine = create_engine('mysql+mysqlconnector://root:@localhost:3306/airflow_db')
query = """
SELECT 
    f.waktu_id, 
    w.tahun,
    e.emiten_id, 
    e.nama_emiten,
    i.nama_indikator, 
    f.nilai
FROM fact_trading_saham f
INNER JOIN dim_waktu w ON f.waktu_id = w.waktu_id
INNER JOIN dim_emiten e ON f.emiten_id = e.emiten_id
INNER JOIN dim_indikator_saham i ON f.indikator_id = i.indikator_id
"""
df_raw = pd.read_sql(query, engine)
df_eda = df_raw.pivot_table(index=['waktu_id', 'emiten_id', 'tahun', 'nama_emiten'], columns='nama_indikator', values='nilai').reset_index()
print(f"Total rows in df_eda: {len(df_eda)}")
bbca = df_eda[df_eda['emiten_id'] == 'BBCA.JK']
print(f"Total BBCA rows before dropna: {len(bbca)}")
bbca_ml = bbca.copy()
bbca_ml['Lag_1'] = bbca_ml['Close Price'].shift(1)
bbca_ml['MA_30'] = bbca_ml['Close Price'].rolling(window=30).mean()
bbca_ml = bbca_ml.dropna()
print(f"Total BBCA rows after dropna: {len(bbca_ml)}")
print("First few dates after dropna:")
print(bbca_ml['waktu_id'].head())
print("Last few dates after dropna:")
print(bbca_ml['waktu_id'].tail())
