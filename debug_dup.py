import pandas as pd
from sqlalchemy import create_engine
engine = create_engine('mysql+mysqlconnector://root:@localhost:3306/airflow_db')
query = """
SELECT waktu_id, COUNT(*) as count 
FROM fact_trading_saham 
WHERE emiten_id = 'BBCA.JK' AND indikator_id = 1
GROUP BY waktu_id 
ORDER BY count DESC 
LIMIT 10
"""
df = pd.read_sql(query, engine)
print("Duplicates in fact table for BBCA:")
print(df)
