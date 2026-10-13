import pandas as pd
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator as MySqlOperator
from airflow.operators.python import PythonOperator
from airflow.hooks.base import BaseHook
import mysql.connector
import subprocess
import sys

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def extract_and_transform():
    # Pastikan yfinance terinstall
    try:
        import yfinance as yf
    except ImportError:
        print("Menginstall yfinance...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance"])
        import yfinance as yf

    print("Mengekstrak data historis Saham Big 4 Bank Indonesia...")
    
    tickers = {
        'BBCA.JK': 'Bank Central Asia',
        'BBRI.JK': 'Bank Rakyat Indonesia',
        'BMRI.JK': 'Bank Mandiri',
        'BBNI.JK': 'Bank Negara Indonesia'
    }
    
    fact_data = []
    dim_waktu_set = set()
    
    for symbol, nama in tickers.items():
        print(f"Mengambil data {symbol}...")
        stock = yf.Ticker(symbol)
        df = stock.history(start="2010-01-01")
        df = df.reset_index()
        
        for index, row in df.iterrows():
            date_val = row['Date'].strftime('%Y-%m-%d')
            dim_waktu_set.add(date_val)
            
            # Format Long (Entity-Attribute-Value) agar masuk ke 4 Tabel Star Schema
            fact_data.append({'waktu_id': date_val, 'emiten_id': symbol, 'indikator_id': 1, 'nilai': round(row['Open'], 2)})
            fact_data.append({'waktu_id': date_val, 'emiten_id': symbol, 'indikator_id': 2, 'nilai': round(row['High'], 2)})
            fact_data.append({'waktu_id': date_val, 'emiten_id': symbol, 'indikator_id': 3, 'nilai': round(row['Low'], 2)})
            fact_data.append({'waktu_id': date_val, 'emiten_id': symbol, 'indikator_id': 4, 'nilai': round(row['Close'], 2)})
            fact_data.append({'waktu_id': date_val, 'emiten_id': symbol, 'indikator_id': 5, 'nilai': int(row['Volume'])})
            
    # Siapkan DataFrame
    dim_waktu_data = []
    for d in sorted(list(dim_waktu_set)):
        date_obj = datetime.strptime(d, '%Y-%m-%d')
        dim_waktu_data.append({
            'waktu_id': d,
            'hari': date_obj.strftime('%A'),
            'bulan': date_obj.strftime('%B'),
            'tahun': date_obj.year
        })
    
    dim_emiten_data = [
        {'emiten_id': 'BBCA.JK', 'nama_emiten': 'Bank Central Asia', 'sektor': 'Keuangan Swasta'},
        {'emiten_id': 'BBRI.JK', 'nama_emiten': 'Bank Rakyat Indonesia', 'sektor': 'Keuangan BUMN'},
        {'emiten_id': 'BMRI.JK', 'nama_emiten': 'Bank Mandiri', 'sektor': 'Keuangan BUMN'},
        {'emiten_id': 'BBNI.JK', 'nama_emiten': 'Bank Negara Indonesia', 'sektor': 'Keuangan BUMN'}
    ]
    
    dim_indikator_data = [
        {'indikator_id': 1, 'nama_indikator': 'Open Price', 'satuan': 'Rupiah (IDR)'},
        {'indikator_id': 2, 'nama_indikator': 'High Price', 'satuan': 'Rupiah (IDR)'},
        {'indikator_id': 3, 'nama_indikator': 'Low Price', 'satuan': 'Rupiah (IDR)'},
        {'indikator_id': 4, 'nama_indikator': 'Close Price', 'satuan': 'Rupiah (IDR)'},
        {'indikator_id': 5, 'nama_indikator': 'Volume', 'satuan': 'Lembar Saham'}
    ]
    
    # Save to CSV
    pd.DataFrame(dim_waktu_data).to_csv("/opt/airflow/dags/data/dim_waktu_saham.csv", index=False)
    pd.DataFrame(dim_emiten_data).to_csv("/opt/airflow/dags/data/dim_emiten.csv", index=False)
    pd.DataFrame(dim_indikator_data).to_csv("/opt/airflow/dags/data/dim_indikator_saham.csv", index=False)
    pd.DataFrame(fact_data).to_csv("/opt/airflow/dags/data/fact_trading_saham.csv", index=False)
    
    print(f"Sukses! {len(fact_data)} baris data historis saham berhasil diekstrak.")

def load_to_mysql():
    mysql_conn = BaseHook.get_connection('mysql-local')
    conn = mysql.connector.connect(
        host=mysql_conn.host,
        user=mysql_conn.login,
        password=mysql_conn.password,
        database=mysql_conn.schema,
        port=mysql_conn.port
    )
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
    
    for _, row in pd.read_csv("/opt/airflow/dags/data/dim_waktu_saham.csv").iterrows():
        cursor.execute("INSERT IGNORE INTO dim_waktu (waktu_id, hari, bulan, tahun) VALUES (%s, %s, %s, %s)", 
                       (str(row['waktu_id']), str(row['hari']), str(row['bulan']), int(row['tahun'])))
                       
    for _, row in pd.read_csv("/opt/airflow/dags/data/dim_emiten.csv").iterrows():
        cursor.execute("INSERT IGNORE INTO dim_emiten (emiten_id, nama_emiten, sektor) VALUES (%s, %s, %s)", 
                       (str(row['emiten_id']), str(row['nama_emiten']), str(row['sektor'])))
                       
    for _, row in pd.read_csv("/opt/airflow/dags/data/dim_indikator_saham.csv").iterrows():
        cursor.execute("INSERT IGNORE INTO dim_indikator_saham (indikator_id, nama_indikator, satuan) VALUES (%s, %s, %s)", 
                       (int(row['indikator_id']), str(row['nama_indikator']), str(row['satuan'])))
                       
    for _, row in pd.read_csv("/opt/airflow/dags/data/fact_trading_saham.csv").iterrows():
        cursor.execute("""
            INSERT IGNORE INTO fact_trading_saham 
            (waktu_id, emiten_id, indikator_id, nilai) 
            VALUES (%s, %s, %s, %s)
        """, (
            str(row['waktu_id']), str(row['emiten_id']), int(row['indikator_id']), float(row['nilai'])
        ))
                       
    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
    conn.commit()
    cursor.close()
    conn.close()

def drop_old_tables():
    mysql_conn = BaseHook.get_connection('mysql-local')
    conn = mysql.connector.connect(
        host=mysql_conn.host,
        user=mysql_conn.login,
        password=mysql_conn.password,
        database=mysql_conn.schema,
        port=mysql_conn.port
    )
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
    cursor.execute("DROP TABLE IF EXISTS fact_trading_saham;")
    cursor.execute("DROP TABLE IF EXISTS dim_waktu;")
    cursor.execute("DROP TABLE IF EXISTS dim_emiten;")
    cursor.execute("DROP TABLE IF EXISTS dim_indikator_saham;")
    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
    conn.commit()
    cursor.close()
    conn.close()

with DAG(
    dag_id='etl_saham_big4_indonesia',
    default_args=default_args,
    schedule='@daily',
    catchup=False,
    tags=['indonesia', 'saham', 'trading', 'mysql', 'star-schema'],
) as dag:
    
    clean_old_schema = PythonOperator(
        task_id='drop_old_tables',
        python_callable=drop_old_tables,
    )

    create_dim_waktu = MySqlOperator(
        task_id='create_dim_waktu',
        conn_id='mysql-local',
        sql="CREATE TABLE IF NOT EXISTS dim_waktu (waktu_id DATE PRIMARY KEY, hari VARCHAR(20), bulan VARCHAR(20), tahun INT);"
    )
    
    create_dim_emiten = MySqlOperator(
        task_id='create_dim_emiten',
        conn_id='mysql-local',
        sql="CREATE TABLE IF NOT EXISTS dim_emiten (emiten_id VARCHAR(10) PRIMARY KEY, nama_emiten VARCHAR(100), sektor VARCHAR(50));"
    )
    
    create_dim_indikator = MySqlOperator(
        task_id='create_dim_indikator',
        conn_id='mysql-local',
        sql="CREATE TABLE IF NOT EXISTS dim_indikator_saham (indikator_id INT PRIMARY KEY, nama_indikator VARCHAR(100), satuan VARCHAR(50));"
    )
    
    create_fact = MySqlOperator(
        task_id='create_fact_trading_saham',
        conn_id='mysql-local',
        sql="""
        CREATE TABLE IF NOT EXISTS fact_trading_saham (
            id INT AUTO_INCREMENT PRIMARY KEY,
            waktu_id DATE,
            emiten_id VARCHAR(10),
            indikator_id INT,
            nilai DECIMAL(20,2),
            UNIQUE KEY unique_fact (waktu_id, emiten_id, indikator_id),
            FOREIGN KEY (waktu_id) REFERENCES dim_waktu(waktu_id),
            FOREIGN KEY (emiten_id) REFERENCES dim_emiten(emiten_id),
            FOREIGN KEY (indikator_id) REFERENCES dim_indikator_saham(indikator_id)
        );
        """,
    )

    extract_transform_task = PythonOperator(
        task_id='extract_and_transform_api',
        python_callable=extract_and_transform,
    )

    load_task = PythonOperator(
        task_id='load_to_mysql',
        python_callable=load_to_mysql,
    )

    clean_old_schema >> [create_dim_waktu, create_dim_emiten, create_dim_indikator] >> create_fact >> extract_transform_task >> load_task
