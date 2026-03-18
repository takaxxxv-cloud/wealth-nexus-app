import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(page_title="Wealth Nexus", page_icon="🏛️", layout="wide")

# ==========================================
# 💎 カスタムCSS（config.tomlで設定できない部分）
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Serif JP', serif !important; }
    div[data-testid="stMetricValue"] { color: #C5A059 !important; font-weight: 600; }
    div[data-testid="stMetricDelta"] svg { fill: #C5A059 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { color: #8C8C8C; border-bottom-color: transparent !important; background-color: transparent !important; }
    .stTabs [aria-selected="true"] { color: #C5A059 !important; border-bottom-color: #C5A059 !important; font-weight: 600; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 🛠️ 無敵のCSV読み込み関数
# ==========================================
def load_csv_safe(file):
    encodings = ['cp932', 'shift_jis', 'utf-8', 'utf-8-sig']
    for enc in encodings:
        try:
            file.seek(0)
            return pd.read_csv(file, encoding=enc)
        except:
            continue
    file.seek(0)
    return pd.read_csv(file, encoding='cp932', encoding_errors='replace')

# ==========================================
# UI: サイドバー（CSVアップロード）
# ==========================================
with st.sidebar:
    st.markdown("<h3 style='color: #C5A059; font-weight: 400;'>データ連携</h3>", unsafe_allow_html=True)
    st.write("SBI証券の「保有証券一覧」CSVをアップロードしてください。")
    uploaded_file = st.file_uploader("📥 保有資産CSV", type="csv")
    
    st.divider()
    # 現金入力欄（SBIのCSVには買付余力などの現金が含まれないことがあるため手入力で補完）
    cash_amount = st.number_input("💰 現金・預金（手入力）", min_value=0, value=5000000, step=100000)

# ==========================================
# 📊 データ処理ロジック
# ==========================================
if uploaded_file is not None:
    # アップロードされたSBIのCSVを読み込む
    raw_df = load_csv_safe(uploaded_file)
    
    # ⚠️ SBI証券の列名を、アプリ用の列名にマッピング（変換）する
    # ※もし実際のCSVの列名と違う場合は、ここを修正します
    try:
        # 文字列のカンマを取り除いて数値化する処理
        for col in ['保有数量', '取得単価', '現在値', '評価額']:
            if col in raw_df.columns:
                raw_df[col] = raw_df[col].astype(str).str.replace(',', '', regex=False).str.replace('円', '', regex=False)
                raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)

        df_assets = pd.DataFrame({
            'アセットクラス': '証券口座資産', # 後で判別ロジックを入れることも可能
            '銘柄名': raw_df['銘柄（ファンド名）'] if '銘柄（ファンド名）' in raw_df.columns else raw_df.iloc[:, 0], # 見つからなければ1列目を銘柄名とする
            '保有数量': raw_df['保有数量'] if '保有数量' in raw_df.columns else 0,
            '平均取得単価': raw_df['取得単価'] if '取得単価' in raw_df.columns else 0,
            '現在値': raw_df['現在値'] if '現在値' in raw_df.columns else 0,
            '評価額': raw_df['評価額'] if '評価額' in raw_df.columns else 0,
        })
        
        # 評価損益と取得金額の計算
        df_assets['取得金額'] = df_assets['保有数量'] * df_assets['平均取得単価']
        # 評価額がCSVにない場合は 現在値×数量 で計算
        df_assets['評価額'] = np.where(df_assets['評価額'] > 0, df_assets['評価額'], df_assets['保有数量'] * df_assets['現在値'])
        df_assets['評価損益'] = df_assets['評価額'] - df_assets['取得金額']
        df_assets['損益率(%)'] = np.where(df_assets['取得金額'] > 0, (df_assets['評価損益'] / df_assets['取得金額']) * 100, 0)
        
    except Exception as e:
        st.error(f"データの読み込みに失敗しました。CSVのフォーマットが予想と異なる可能性があります。（エラー詳細: {e}）")
        st.stop()
        
else:
    # ファイルがアップロードされていない時はダミーデータを表示
    st.info("👈 左側のメニューからSBI証券のCSVをアップロードすると、実際のデータに切り替わります。")
    data = {
        'アセットクラス': ['国内株式', '米国株式', '投資信託'],
        '銘柄名': ['ダミー銘柄A', 'ダミー銘柄B', 'ダミーファンドC'],
        '保有数量': [1000, 200, 500000],
        '平均取得単価': [1500, 200, 12000],
        '現在値': [1800, 250, 15000]
    }
    df_assets = pd.DataFrame(data)
    df_assets['取得金額'] = df_assets['保有数量'] * df_assets['平均取得単価']
    df_assets['評価額'] = df_assets['保有数量'] * df_assets['現在値']
    df_assets['評価損益'] = df_assets['評価額'] - df_assets['取得金額']
    df_assets['損益率(%)'] = (df_assets['評価損益'] / df_assets['取得金額']) * 100

# 手入力の現金をデータフレームに追加
cash_df = pd.DataFrame({
    'アセットクラス': ['現金・預金'], '銘柄名': ['日本円'], '保有数量': [1], '平均取得単価': [cash_amount], 
    '現在値': [cash_amount], '取得金額': [cash_amount], '評価額': [cash_amount], '評価損益': [0], '損益率(%)': [0.0]
})
df_assets = pd.concat([df_assets, cash_df], ignore_index=True)


# ==========================================
# UI: ヘッダー
# ==========================================
st.markdown("<h1 style='color: #C5A059; font-weight: 300; letter-spacing: 2px;'>Wealth Nexus</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #8C8C8C; font-size: 1.1rem; letter-spacing: 1px;'>プライベート・ポートフォリオ管理</p>", unsafe_allow_html=True)
st.divider()

# ==========================================
# UI: サマリーKPI
# ==========================================
total_assets = df_assets['評価額'].sum()
total_profit = df_assets['評価損益'].sum()
profit_rate = (total_profit / df_assets['取得金額'].sum()) * 100 if df_assets['取得金額'].sum() > 0 else 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="総資産額", value=f"¥ {total_assets:,.0f}")
with col2:
    st.metric(label="トータルリターン（評価損益）", value=f"¥ {total_profit:,.0f}", delta=f"{profit_rate:.2f} %")
with col3:
    st.metric(label="現金比率", value=f"{(cash_amount / total_assets)*100:.1f} %" if total_assets > 0 else "0 %")

st.write("")
st.write("")

# ==========================================
# UI: グラフエリア（Plotly）
# ==========================================
g1, g2 = st.columns(2)

with g1:
    # ドーナツグラフ
    allocation = df_assets.groupby('アセットクラス')['評価額'].sum().reset_index()
    fig_pie = px.pie(allocation, names='アセットクラス', values='評価額', hole=0.75)
    fig_pie.update_layout(
        title=dict(text='アセットアロケーション', font=dict(color='#C5A059', size=20)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#8C8C8C'),
        margin=dict(t=50, b=20, l=0, r=0), showlegend=True
    )
    gold_palette = ['#C5A059', '#A67C00', '#BF953F', '#FCF6BA', '#B38728', '#FBF5B7']
    fig_pie.update_traces(marker=dict(colors=gold_palette, line=dict(color='#0A0A0A', width=2)))
    st.plotly_chart(fig_pie, use_container_width=True)

with g2:
    # SBIのCSVには過去の推移データがないため、今回は各銘柄の「評価額」の棒グラフを表示します
    fig_bar = px.bar(df_assets[df_assets['評価額'] > 0].sort_values('評価額', ascending=False), 
                     x='銘柄名', y='評価額', text_auto='.2s')
    fig_bar.update_layout(
        title=dict(text='保有銘柄別 評価額', font=dict(color='#C5A059', size=20)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#8C8C8C'),
        xaxis=dict(showgrid=False, color='#8C8C8C'),
        yaxis=dict(showgrid=True, gridcolor='#332918', color='#8C8C8C'),
        margin=dict(t=50, b=20, l=0, r=0)
    )
    fig_bar.update_traces(marker_color='#C5A059', textfont_color='#0A0A0A', textposition='outside')
    st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# ==========================================
# UI: ポートフォリオ詳細表
# ==========================================
st.markdown("<h3 style='color: #F2F2F2; font-weight: 300;'>📋 保有銘柄詳細</h3>", unsafe_allow_html=True)

display_df = df_assets.copy()
display_df['保有数量'] = display_df.apply(lambda x: '-' if x['アセットクラス'] == '現金・預金' else f"{x['保有数量']}", axis=1)
display_df['平均取得単価'] = display_df.apply(lambda x: '-' if x['アセットクラス'] == '現金・預金' else f"¥ {x['平均取得単価']:,.0f}", axis=1)
display_df['現在値'] = display_df.apply(lambda x: '-' if x['アセットクラス'] == '現金・預金' else f"¥ {x['現在値']:,.0f}", axis=1)
display_df['評価額'] = display_df['評価額'].apply(lambda x: f"¥ {x:,.0f}")
display_df['評価損益'] = display_df['評価損益'].apply(lambda x: f"¥ {x:,.0f}")
display_df['損益率(%)'] = display_df['損益率(%)'].apply(lambda x: f"{x:+.2f} %" if x != 0 else "-")

st.dataframe(display_df.drop(columns=['取得金額']), use_container_width=True)
