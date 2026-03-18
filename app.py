import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import csv # 💡 追加：CSVを細かく解析するためのライブラリ

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(page_title="Wealth Nexus", page_icon="🏛️", layout="wide")

# ==========================================
# 💎 カスタムCSS
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
# 🛠️ SBI証券専用 CSV解析関数（多段フォーマット対応）
# ==========================================
def parse_sbi_csv(file):
    # ファイルの文字列を読み込む
    content = file.getvalue().decode('cp932', errors='replace')
    lines = content.split('\n')
    
    parsed_data = []
    header_map = {}
    mode = None # 今「株式」を読んでいるか「投資信託」を読んでいるかの状態
    
    reader = csv.reader(lines)
    for row in reader:
        if not row or len(row) == 0: continue
        
        # 1. 見出し行の検知（ブロックの始まり）
        if '銘柄名称' in row:
            mode = 'stock'
            header_map = {col.strip(): i for i, col in enumerate(row) if col.strip()}
            continue
        elif 'ファンド名' in row:
            mode = 'fund'
            header_map = {col.strip(): i for i, col in enumerate(row) if col.strip()}
            continue
        # ブロックの終わり（合計行など）
        elif '評価損益合計' in row or '評価額合計' in row or (len(row) > 0 and '合計' in str(row[0])):
            mode = None 
            continue
        
        # 2. データの抽出
        if mode == 'stock':
            if '銘柄名称' not in header_map: continue
            name = row[header_map['銘柄名称']]
            if not name or name.startswith('評価') or name.startswith('株式'): continue
            
            try:
                qty = float(str(row[header_map['保有株数']]).replace(',', ''))
                cost = float(str(row[header_map['取得単価']]).replace(',', ''))
                price = float(str(row[header_map['現在値']]).replace(',', ''))
                value = float(str(row[header_map['評価額']]).replace(',', ''))
                parsed_data.append({'アセットクラス': '株式', '銘柄名': name, '保有数量': qty, '平均取得単価': cost, '現在値': price, '評価額': value})
            except:
                pass # 数値に変換できないエラー行は無視
                
        elif mode == 'fund':
            if 'ファンド名' not in header_map: continue
            name = row[header_map['ファンド名']]
            if not name or name.startswith('評価') or name.startswith('投資信託'): continue
            
            try:
                # 投資信託の「口」の文字を取り除いて数値化
                qty = float(str(row[header_map['保有口数']]).replace(',', '').replace('口', ''))
                cost = float(str(row[header_map['取得単価']]).replace(',', ''))
                price = float(str(row[header_map['基準価額']]).replace(',', ''))
                value = float(str(row[header_map['評価額']]).replace(',', ''))
                parsed_data.append({'アセットクラス': '投資信託', '銘柄名': name, '保有数量': qty, '平均取得単価': cost, '現在値': price, '評価額': value})
            except:
                pass

    return pd.DataFrame(parsed_data)

# ==========================================
# UI: サイドバー（CSVアップロード）
# ==========================================
with st.sidebar:
    st.markdown("<h3 style='color: #C5A059; font-weight: 400;'>データ連携</h3>", unsafe_allow_html=True)
    st.write("SBI証券の「保有証券一覧」CSVをアップロードしてください。")
    uploaded_file = st.file_uploader("📥 保有資産CSV", type="csv")
    
    st.divider()
    cash_amount = st.number_input("💰 現金・預金（手入力）", min_value=0, value=5000000, step=100000)

# ==========================================
# 📊 データ処理ロジック
# ==========================================
if uploaded_file is not None:
    # 🎯 ここで先ほど作った専用関数を呼び出す
    df_assets = parse_sbi_csv(uploaded_file)
    
    if len(df_assets) == 0:
        st.error("データを抽出できませんでした。SBI証券のCSVファイルか確認してください。")
        st.stop()
        
    # 評価損益と取得金額の計算
    df_assets['取得金額'] = df_assets['保有数量'] * df_assets['平均取得単価']
    df_assets['評価損益'] = df_assets['評価額'] - df_assets['取得金額']
    df_assets['損益率(%)'] = np.where(df_assets['取得金額'] > 0, (df_assets['評価損益'] / df_assets['取得金額']) * 100, 0)
        
else:
    # ファイルがない時のダミーデータ
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

# 手入力の現金を合算
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

# ==========================================
# UI: グラフエリア（Plotly）
# ==========================================
g1, g2 = st.columns(2)

with g1:
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
display_df['保有数量'] = display_df.apply(lambda x: '-' if x['アセットクラス'] == '現金・預金' else f"{x['保有数量']:,.0f}", axis=1)
display_df['平均取得単価'] = display_df.apply(lambda x: '-' if x['アセットクラス'] == '現金・預金' else f"¥ {x['平均取得単価']:,.0f}", axis=1)
display_df['現在値'] = display_df.apply(lambda x: '-' if x['アセットクラス'] == '現金・預金' else f"¥ {x['現在値']:,.0f}", axis=1)
display_df['評価額'] = display_df['評価額'].apply(lambda x: f"¥ {x:,.0f}")
display_df['評価損益'] = display_df['評価損益'].apply(lambda x: f"¥ {x:,.0f}")
display_df['損益率(%)'] = display_df['損益率(%)'].apply(lambda x: f"{x:+.2f} %" if x != 0 else "-")

st.dataframe(display_df.drop(columns=['取得金額']), use_container_width=True)
