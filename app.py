import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
import datetime
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_percentage_error, mean_absolute_error, root_mean_squared_error, r2_score

# ================= KONFIGURASI HALAMAN =================
st.set_page_config(page_title="AI Trading Terminal", page_icon="💹", layout="wide", initial_sidebar_state="expanded")

# ================= CUSTOM CSS =================
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .title-text {
        font-size: 3.5rem; font-weight: 900; text-align: center;
        background: linear-gradient(90deg, #F9D423 0%, #FF4E50 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px;
    }
    .subtitle-text { text-align: center; font-size: 1.2rem; color: #A0AEC0; margin-bottom: 40px; }
    .signal-card-buy { background: linear-gradient(135deg, #0ba360 0%, #3cba92 100%); padding: 20px; border-radius: 12px; color: white; text-align: center; box-shadow: 0px 4px 15px rgba(11, 163, 96, 0.4); }
    .signal-card-sell { background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%); padding: 20px; border-radius: 12px; color: white; text-align: center; box-shadow: 0px 4px 15px rgba(255, 65, 108, 0.4); }
    div[data-testid="metric-container"] { background-color: #1A1C23; border: 1px solid #2D3748; padding: 15px; border-radius: 10px; border-top: 4px solid #F9D423; }
</style>
""", unsafe_allow_html=True)

# ================= FUNGSI BACKEND =================
@st.cache_data(show_spinner=False)
def load_data():
    csv_file = os.path.join(os.path.dirname(__file__), "data_clean_stock.csv")
    try:
        # 1. Coba koneksi langsung ke MySQL (aktif saat di laptop lokal)
        engine = create_engine('mysql+mysqlconnector://root:@localhost:3306/airflow_db')
        query = """
        SELECT f.waktu_id, w.tahun, e.emiten_id, e.nama_emiten, i.nama_indikator, f.nilai
        FROM fact_trading_saham f
        INNER JOIN dim_waktu w ON f.waktu_id = w.waktu_id
        INNER JOIN dim_emiten e ON f.emiten_id = e.emiten_id
        INNER JOIN dim_indikator_saham i ON f.indikator_id = i.indikator_id
        """
        df_raw = pd.read_sql(query, engine)
        df_eda = df_raw.pivot_table(index=['waktu_id', 'emiten_id', 'tahun', 'nama_emiten'], columns='nama_indikator', values='nilai').reset_index()
        df_eda.columns.name = None
        df_eda['waktu_id'] = pd.to_datetime(df_eda['waktu_id'])
        df_eda = df_eda.sort_values(by='waktu_id')
        # Sinkronkan data terbaru ke cadangan CSV
        df_eda.to_csv(csv_file, index=False)
        return df_eda
    except Exception:
        # 2. Fallback cerdas: jika dideploy ke Streamlit Cloud di internet tanpa MySQL lokal
        if os.path.exists(csv_file):
            df_eda = pd.read_csv(csv_file)
            df_eda['waktu_id'] = pd.to_datetime(df_eda['waktu_id'])
            df_eda = df_eda.sort_values(by='waktu_id')
            return df_eda
        else:
            raise RuntimeError("Database MySQL lokal tidak terdeteksi dan file data_clean_stock.csv tidak ditemukan.")

@st.cache_resource(show_spinner=False)
def train_ai_models(df_eda):
    banks = df_eda['emiten_id'].unique()
    models = {}
    dict_df_ml = {}
    features = ['Open Price', 'High Price', 'Low Price', 'Volume', 'Lag_1', 'Lag_2', 'Lag_3', 'MA_7', 'MA_30']
    eval_metrics = {}

    for bank in banks:
        df_ml = df_eda[df_eda['emiten_id'] == bank].copy()
        for i in range(1, 4): df_ml[f'Lag_{i}'] = df_ml['Close Price'].shift(i)
        df_ml['MA_7'] = df_ml['Close Price'].rolling(window=7).mean()
        df_ml['MA_30'] = df_ml['Close Price'].rolling(window=30).mean()
        df_ml = df_ml.dropna()
        
        dict_df_ml[bank] = df_ml
        
        X = df_ml[features]
        y = df_ml['Close Price']
        split = int(len(df_ml) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]
        
        model = Ridge(alpha=1.0)
        model.fit(X_train, y_train)
        models[bank] = model
        
        pred_test = model.predict(X_test)
        eval_metrics[bank] = {
            'R² Score': r2_score(y_test, pred_test),
            'MAPE': mean_absolute_percentage_error(y_test, pred_test) * 100,
            'MAE': mean_absolute_error(y_test, pred_test),
            'RMSE': root_mean_squared_error(y_test, pred_test),
            'y_test': y_test,
            'pred_test': pred_test,
            'test_dates': df_ml.iloc[split:]['waktu_id']
        }
    return models, dict_df_ml, features, eval_metrics

# ================= INISIALISASI =================
with st.spinner("🚀 Booting AI Engine..."):
    df_eda = load_data()
    models, dict_df_ml, features, eval_metrics = train_ai_models(df_eda)

# ================= HEADER =================
st.markdown('<div class="title-text">AI TRADING TERMINAL 2.0</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-text">Platform Analisis Saham Big 4 Bank Menggunakan Machine Learning & Geospasial</div>', unsafe_allow_html=True)

# ================= SIDEBAR =================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2635/2635293.png", width=60)
    st.markdown("## 🎛️ Control Panel")
    pilih_bank = st.selectbox("Pilih Emiten Bank:", df_eda['emiten_id'].unique())
    st.markdown("---")
    rentang = st.radio("Zoom Data (Candlestick):", ["1 Tahun Terakhir", "3 Tahun Terakhir", "Semua Data"])
    st.markdown("---")
    st.markdown("💡 *Dashboard ini menampilkan Analisis Teknikal, Makro, Prediksi AI, dan Evaluasi Model Machine Learning.*")

df_bank = dict_df_ml[pilih_bank]
if rentang == "1 Tahun Terakhir": df_bank_filtered = df_bank.tail(252)
elif rentang == "3 Tahun Terakhir": df_bank_filtered = df_bank.tail(252*3)
else: df_bank_filtered = df_bank

# ================= KPI ATAS =================
latest = df_bank.iloc[-1]
prev = df_bank.iloc[-2]
harga_sekarang = latest['Close Price']
perubahan = harga_sekarang - prev['Close Price']
persen_perubahan = (perubahan / prev['Close Price']) * 100

ma7 = latest['MA_7']
ma30 = latest['MA_30']
sinyal = "BUY (BULLISH)" if ma7 > ma30 else "SELL (BEARISH)"
css_sinyal = "signal-card-buy" if sinyal == "BUY (BULLISH)" else "signal-card-sell"

st.markdown(f"### ⚡ Sinyal Trading & Indikator Utama: {pilih_bank}")
colA, colB, colC = st.columns([1, 1, 2])
colA.metric("Harga Penutupan", f"Rp {harga_sekarang:,.0f}", f"{perubahan:,.0f} ({persen_perubahan:.2f}%)")
colB.metric("Volume Transaksi", f"{latest['Volume']/1_000_000:,.1f} Juta", "Lembar Saham", delta_color="off")
with colC:
    st.markdown(f"""
        <div class="{css_sinyal}">
            <h3 style="margin:0; color:white;">Rekomendasi AI: {sinyal}</h3>
            <p style="margin:0; opacity:0.8;">Berdasarkan perpotongan Moving Average (MA7 & MA30)</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ================= TABS NAVIGATION =================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Teknikal (Candlestick)", "📈 Analisis Makro & Volatilitas", "🤖 Prediksi AI (30 Hari)", "🎯 Evaluasi Model AI"])

# ----------------- TAB 1: CANDLESTICK -----------------
with tab1:
    fig_candle = go.Figure()
    fig_candle.add_trace(go.Candlestick(
        x=df_bank_filtered['waktu_id'].dt.strftime('%Y-%m-%d'),
        open=df_bank_filtered['Open Price'], high=df_bank_filtered['High Price'],
        low=df_bank_filtered['Low Price'], close=df_bank_filtered['Close Price'],
        name='Candlestick', increasing_line_color='#00ff88', decreasing_line_color='#ff0055'
    ))
    fig_candle.add_trace(go.Scatter(x=df_bank_filtered['waktu_id'].dt.strftime('%Y-%m-%d'), y=df_bank_filtered['MA_7'], mode='lines', line=dict(color='yellow', width=1.5), name='MA 7'))
    fig_candle.add_trace(go.Scatter(x=df_bank_filtered['waktu_id'].dt.strftime('%Y-%m-%d'), y=df_bank_filtered['MA_30'], mode='lines', line=dict(color='cyan', width=1.5), name='MA 30'))
    
    fig_candle.update_layout(
        template='plotly_dark', height=550, margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified", dragmode='pan', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)',
        xaxis=dict(type='category', nticks=10, showgrid=True, gridcolor='#2D3748'),
        yaxis=dict(showgrid=True, gridcolor='#2D3748')
    )
    st.plotly_chart(fig_candle, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

# ----------------- TAB 2: PERBANDINGAN MAKRO -----------------
with tab2:
    st.markdown("### 🔍 Analisis Komparatif Big 4 Bank")
    st.markdown("Menampilkan seluruh wawasan *Exploratory Data Analysis* (EDA) dari algoritma kita, mulai dari tren, volatilitas, dominasi pasar, hingga korelasi variabel.")
    
    df_eda_recent = df_eda.tail(252*4*3) # 3 tahun terakhir
    
    # Baris 1: Line & Boxplot
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Tren Harga Penutupan (Semua Bank)**")
        fig_line = px.line(df_eda_recent, x='waktu_id', y='Close Price', color='emiten_id', template='plotly_dark')
        fig_line.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)', margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_line, use_container_width=True)
    with col2:
        st.markdown("**Distribusi Volatilitas / Risiko Ayunan Harga (Boxplot)**")
        fig_box = px.box(df_eda_recent, x='emiten_id', y='Close Price', color='emiten_id', template='plotly_dark')
        fig_box.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)', margin=dict(t=10, b=10, l=10, r=10), showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)
        
    # Baris 2: Pie/Donut & Scatter Plot
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**Pangsa Pasar (Dominasi Volume Transaksi)**")
        df_pie = df_eda_recent.groupby('nama_emiten')['Volume'].sum().reset_index()
        # Membuat diagram Donut (Pie Chart dengan lubang di tengah agar terlihat modern)
        fig_pie = px.pie(
            df_pie, values='Volume', names='nama_emiten', hole=0.5, 
            template='plotly_dark', color_discrete_sequence=["#00529C", "#F37021", "#F2C80F", "#005E6A"]
        )
        fig_pie.update_traces(textposition='outside', textinfo='percent+label', pull=[0.05, 0.05, 0.05, 0.05])
        fig_pie.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)', showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col4:
        st.markdown("**Pola Sebaran Harga vs Volume Transaksi (Scatter Plot)**")
        fig_scatter = px.scatter(
            df_eda_recent, x='Volume', y='Close Price', color='emiten_id', 
            template='plotly_dark', opacity=0.7, size_max=10
        )
        fig_scatter.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)', margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    st.markdown("---")
    st.markdown("**Peta Suhu Korelasi Antar Indikator Pasar (Heatmap)**")
    korelasi = df_eda[['Open Price', 'High Price', 'Low Price', 'Close Price', 'Volume']].corr()
    fig_heat = px.imshow(korelasi, text_auto=".2f", aspect="auto", color_continuous_scale='Magma', template='plotly_dark')
    fig_heat.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)', margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_heat, use_container_width=True)

# ----------------- TAB 3: AI FORECASTING -----------------
with tab3:
    st.subheader(f"Proyeksi Harga AI: 30 Hari Bursa Mendatang ({pilih_bank})")
    
    model = models[pilih_bank]
    current_date = latest['waktu_id']
    current_features = latest[features].values.reshape(1, -1)
    
    f_dates, f_preds = [], []
    for _ in range(30):
        next_pred = model.predict(current_features)[0]
        current_date += datetime.timedelta(days=1)
        while current_date.weekday() >= 5: current_date += datetime.timedelta(days=1)
        f_dates.append(current_date)
        f_preds.append(next_pred)
        current_features[0][6] = current_features[0][5]
        current_features[0][5] = current_features[0][4]
        current_features[0][4] = next_pred
        
    df_future = pd.DataFrame({'Tanggal': f_dates, 'Target Harga': f_preds})
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Skor Error AI (MAPE)", f"{eval_metrics[pilih_bank]['MAPE']:.2f}%", delta="Rendah = Sangat Akurat", delta_color="normal")
    c2.metric("Target Harga Tertinggi (30H)", f"Rp {df_future['Target Harga'].max():,.0f}")
    c3.metric("Target Harga Terendah (30H)", f"Rp {df_future['Target Harga'].min():,.0f}")
    
    fig_proj = go.Figure()
    df_hist_zoom = df_bank.tail(120) 
    
    fig_proj.add_trace(go.Scatter(x=df_hist_zoom['waktu_id'].dt.strftime('%Y-%m-%d'), y=df_hist_zoom['Close Price'], mode='lines', name='Harga Asli', line=dict(color='#00C9FF', width=3)))
    fig_proj.add_trace(go.Scatter(x=df_future['Tanggal'].dt.strftime('%Y-%m-%d'), y=df_future['Target Harga'], mode='lines+markers', name='Proyeksi AI', line=dict(color='#F9D423', width=3, dash='dash'), fill='tozeroy', fillcolor='rgba(249, 212, 35, 0.1)'))
    
    fig_proj.update_layout(
        template='plotly_dark', height=450, hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)',
        xaxis=dict(type='category', nticks=10, showgrid=False), yaxis=dict(showgrid=True, gridcolor='#2D3748')
    )
    st.plotly_chart(fig_proj, use_container_width=True)

# ----------------- TAB 4: EVALUASI MODEL AI -----------------
with tab4:
    st.markdown("### 📊 Evaluasi Performa Machine Learning (Ridge Regression)")
    st.markdown("Berikut adalah hasil uji akurasi AI kita pada data *Testing*. Skor **R² (R-Squared)** menunjukkan seberapa pintar model kita mengenali pola, sedangkan **MAPE/MAE/RMSE** mengukur tingkat kesalahannya.")
    
    # Menyiapkan data evaluasi
    eval_list = []
    for b in df_eda['emiten_id'].unique():
        eval_list.append({
            'Bank': b,
            'R² Score': eval_metrics[b]['R² Score'],
            'MAPE (%)': eval_metrics[b]['MAPE'],
            'MAE': eval_metrics[b]['MAE'],
            'RMSE': eval_metrics[b]['RMSE']
        })
    df_eval = pd.DataFrame(eval_list)
    
    # Grid 2x2 untuk 4 Chart
    col_a, col_b = st.columns(2)
    
    # Fungsi pembantu untuk membuat bar chart cantik
    def make_bar(df, y_col, title, color_theme, is_higher_better=False):
        # Urutkan berdasarkan yang terbaik
        df_sorted = df.sort_values(by=y_col, ascending=is_higher_better)
        fig = px.bar(
            df_sorted, x='Bank', y=y_col, text_auto='.4f' if y_col == 'R² Score' else '.2f',
            color='Bank', template='plotly_dark', color_discrete_sequence=color_theme,
            title=title
        )
        fig.update_layout(height=350, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)', showlegend=False, title_font=dict(size=14))
        return fig
    
    with col_a:
        st.plotly_chart(make_bar(df_eval, 'R² Score', "🏆 R-Squared (Mendekati 1.0 = Sangat Akurat)", px.colors.sequential.Aggrnyl, True), use_container_width=True)
        st.plotly_chart(make_bar(df_eval, 'MAE', "📏 MAE: Rata-Rata Meleset (Dalam Rupiah, Makin Rendah Makin Baik)", px.colors.sequential.Oranges, False), use_container_width=True)
        
    with col_b:
        st.plotly_chart(make_bar(df_eval, 'MAPE (%)', "🎯 MAPE: Persentase Error (Makin Rendah Makin Baik)", px.colors.sequential.Plasma, False), use_container_width=True)
        st.plotly_chart(make_bar(df_eval, 'RMSE', "💥 RMSE: Hukuman untuk Error Ekstrem (Makin Rendah Makin Baik)", px.colors.sequential.Reds, False), use_container_width=True)
    
    st.markdown("---")
    st.markdown("#### 📋 Tabel Detail Keseluruhan")
    st.dataframe(df_eval.set_index('Bank'), use_container_width=True)

    st.markdown("---")
    st.markdown(f"### 🔬 Bukti Visual Akurasi AI: {pilih_bank}")
    st.markdown("Grafik di bawah ini membuktikan secara visual seberapa *nempel* tebakan AI dengan harga asli pada data **Testing** (data yang belum pernah dilihat AI saat latihan).")
    
    # Ambil data test untuk bank yang dipilih
    y_test_sel = eval_metrics[pilih_bank]['y_test']
    pred_test_sel = eval_metrics[pilih_bank]['pred_test']
    test_dates_sel = eval_metrics[pilih_bank]['test_dates']
    
    # --- Grafik 1: Actual vs Predicted ---
    fig_avp = go.Figure()
    fig_avp.add_trace(go.Scatter(
        x=test_dates_sel.dt.strftime('%Y-%m-%d'), y=y_test_sel,
        mode='lines', name='Harga Asli (Actual)',
        line=dict(color='#00C9FF', width=2.5)
    ))
    fig_avp.add_trace(go.Scatter(
        x=test_dates_sel.dt.strftime('%Y-%m-%d'), y=pred_test_sel,
        mode='lines', name='Tebakan AI (Predicted)',
        line=dict(color='#F9D423', width=2.5, dash='dot')
    ))
    fig_avp.update_layout(
        template='plotly_dark', height=420,
        title=dict(text=f"📈 Perbandingan Harga Asli vs Tebakan AI ({pilih_bank})", font=dict(size=14)),
        hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)',
        xaxis=dict(type='category', nticks=10, showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#2D3748', title='Harga (Rp)')
    )
    st.plotly_chart(fig_avp, use_container_width=True)
    st.caption("💡 Semakin kedua garis saling menempel, semakin akurat AI kita. Garis kuning putus-putus (AI) hampir sempurna menindih garis biru (harga asli).")
    
    # --- Grafik 2: Residual Plot ---
    residuals = y_test_sel.values - pred_test_sel
    fig_res = go.Figure()
    fig_res.add_trace(go.Scatter(
        x=test_dates_sel.dt.strftime('%Y-%m-%d'), y=residuals,
        mode='markers', name='Residual (Error)',
        marker=dict(color=residuals, colorscale='RdYlGn', size=5, opacity=0.7,
                    colorbar=dict(title='Error (Rp)', thickness=15)),
    ))
    fig_res.add_hline(y=0, line_dash='dash', line_color='white', line_width=1, opacity=0.5)
    fig_res.update_layout(
        template='plotly_dark', height=350,
        title=dict(text=f"📉 Distribusi Error Tebakan AI ({pilih_bank})", font=dict(size=14)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.1)',
        xaxis=dict(type='category', nticks=10, showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#2D3748', title='Error = Actual - Predicted (Rp)', zeroline=True)
    )
    st.plotly_chart(fig_res, use_container_width=True)
    st.caption("💡 Titik-titik yang merata di sekitar garis nol membuktikan bahwa AI tidak memiliki *bias* — tidak cenderung selalu menebak terlalu tinggi maupun terlalu rendah.")
