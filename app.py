import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import csv

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
    
    [data-testid="stDataFrame"] { background-color: transparent !important; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ==========================================
# 🛠️ SBI証券専用 CSV解析関数
# ==========================================
def parse_sbi_csv(file):
    content = file.getvalue().decode('cp932', errors='replace')
    lines = content.split('\n')
    
    parsed_data = []
    header_map = {}
    mode = None
    
    reader = csv.reader(lines)
    for row in reader:
        if not row or len(row) == 0: continue
        
        if '銘柄名称' in row:
            mode = 'stock'
            header_map = {col.strip(): i for i, col in enumerate(row) if col.strip()}
            continue
        elif 'ファンド名' in row:
            mode = 'fund'
            header_map = {col.strip(): i for i, col in enumerate(row) if col.strip()}
            continue
        elif '評価損益合計' in row or '評価額合計' in row or (len(row) > 0 and '合計' in str(row[0])):
            mode = None 
            continue
        
        if mode == 'stock':
            if '銘柄名称' not in header_map: continue
            name = row[header_map['銘柄名称']]
            if not name or name.startswith('評価') or name.startswith('株式'): continue
            
            try:
                qty = float(str(row[header_map['保有株数']]).replace(',', ''))
                cost = float(str(row[header_map['取得単価']]).replace(',', ''))
                price = float(str(row[header_map['現在値']]).replace(',', ''))
                value = float(str(row[header_map['評価額']]).replace(',', ''))
                parsed_data.append({'アセットクラス': '国内株式', '銘柄名': name, '保有数量': qty, '平均取得単価': cost, '現在値': price, '評価額': value})
            except: pass
                
        elif mode == 'fund':
            if 'ファンド名' not in header_map: continue
            name = row[header_map['ファンド名']]
            if not name or name.startswith('評価') or name.startswith('投資信託'): continue
            
            try:
                qty = float(str(row[header_map['保有口数']]).replace(',', '').replace('口', ''))
                cost = float(str(row[header_map['取得単価']]).replace(',', ''))
                price = float(str(row[header_map['基準価額']]).replace(',', ''))
                value = float(str(row[header_map['評価額']]).replace(',', ''))
                parsed_data.append({'アセットクラス': '投資信託', '銘柄名': name, '保有数量': qty, '平均取得単価': cost, '現在値': price, '評価額': value})
            except: pass

    return pd.DataFrame(parsed_data)

# ==========================================
# UI: サイドバー（データ入力パネル）
# ==========================================
with st.sidebar:
    st.markdown("<h3 style='color: #C5A059; font-weight: 400;'>データ連携</h3>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("📥 SBI証券 CSV (国内株・投信)", type="csv")
    
    st.divider()
    
    # 💰 現金入力
    cash_amount = st.number_input("💰 現金・預金（円）", min_value=0, value=5000000, step=100000)
    
    st.divider()
    
    # 🌍 外国株式入力エリア
    st.markdown("<h4 style='color: #C5A059; font-weight: 400;'>🌍 外国株式（手入力）</h4>", unsafe_allow_html=True)
    exchange_rate = st.number_input("💵 現在の為替レート (円/ドル)", min_value=100.0, value=150.0, step=0.5)
    
    if 'foreign_data' not in st.session_state:
        st.session_state.foreign_data = pd.DataFrame(
            [{"銘柄名": "AAPL", "数量": 10.0, "平均取得単価($)": 150.0, "現在値($)": 170.0}]
        )
    edited_foreign = st.data_editor(
        st.session_state.foreign_data, num_rows="dynamic", use_container_width=True, hide_index=True
    )
    
    st.divider()
    
    # 🏢 不動産クラウドファンディング入力エリア（💡 新規追加！）
    st.markdown("<h4 style='color: #C5A059; font-weight: 400;'>🏢 不動産CF（手入力）</h4>", unsafe_allow_html=True)
    
    if 'real_estate_data' not in st.session_state:
        st.session_state.real_estate_data = pd.DataFrame(
            [{"ファンド名": "〇〇レジデンス第1号", "出資金額(円)": 500000, "現在評価額(円)": 500000}]
        )
    
    st.caption("※行の一番下をクリックして新しいファンドを追加できます。")
    edited_re = st.data_editor(
        st.session_state.real_estate_data, num_rows="dynamic", use_container_width=True, hide_index=True
    )

# ==========================================
# 📊 データ処理・結合ロジック
# ==========================================
df_list = []

# 1. SBI証券のデータ
if uploaded_file is not None:
    sbi_df = parse_sbi_csv(uploaded_file)
    if len(sbi_df) > 0:
        # 💡 修正：投資信託は「1万口あたり」の単価なので、計算時に10000で割る
        sbi_df['取得金額'] = np.where(
            sbi_df['アセットクラス'] == '投資信託',
            (sbi_df['保有数量'] / 10000) * sbi_df['平均取得単価'],
            sbi_df['保有数量'] * sbi_df['平均取得単価']
        )
        sbi_df['評価損益'] = sbi_df['評価額'] - sbi_df['取得金額']
        df_list.append(sbi_df)

# 2. 外国株式のデータ
f_df = edited_foreign.copy()
f_df = f_df[f_df['銘柄名'].str.strip() != ""] 
if len(f_df) > 0:
    f_df['保有数量'] = pd.to_numeric(f_df['数量'], errors='coerce').fillna(0)
    f_df['平均取得単価'] = pd.to_numeric(f_df['平均取得単価($)'], errors='coerce').fillna(0) * exchange_rate
    f_df['現在値'] = pd.to_numeric(f_df['現在値($)'], errors='coerce').fillna(0) * exchange_rate
    f_df['アセットクラス'] = '米国株式'
    f_df['取得金額'] = f_df['保有数量'] * f_df['平均取得単価']
    f_df['評価額'] = f_df['保有数量'] * f_df['現在値']
    f_df['評価損益'] = f_df['評価額'] - f_df['取得金額']
    df_list.append(f_df[['アセットクラス', '銘柄名', '保有数量', '平均取得単価', '現在値', '取得金額', '評価額', '評価損益']])

# 3. 不動産クラウドファンディングのデータ（💡 新規追加！）
re_df = edited_re.copy()
re_df = re_df[re_df['ファンド名'].str.strip() != ""] 
if len(re_df) > 0:
    # 数量の概念がないため「1」として扱い、単価＝出資額として計算します
    re_df['保有数量'] = 1
    re_df['平均取得単価'] = pd.to_numeric(re_df['出資金額(円)'], errors='coerce').fillna(0)
    re_df['現在値'] = pd.to_numeric(re_df['現在評価額(円)'], errors='coerce').fillna(0)
    re_df['アセットクラス'] = '不動産CF'
    re_df['銘柄名'] = re_df['ファンド名']
    re_df['取得金額'] = re_df['平均取得単価']
    re_df['評価額'] = re_df['現在値']
    re_df['評価損益'] = re_df['評価額'] - re_df['取得金額']
    df_list.append(re_df[['アセットクラス', '銘柄名', '保有数量', '平均取得単価', '現在値', '取得金額', '評価額', '評価損益']])

# 4. 現金データ
cash_df = pd.DataFrame({
    'アセットクラス': ['現金・預金'], '銘柄名': ['日本円'], '保有数量': [1], '平均取得単価': [cash_amount], 
    '現在値': [cash_amount], '取得金額': [cash_amount], '評価額': [cash_amount], '評価損益': [0]
})
df_list.append(cash_df)

# 🚀 全データをガッチャンコ（結合）
if len(df_list) > 0:
    df_assets = pd.concat(df_list, ignore_index=True)
else:
    df_assets = pd.DataFrame(columns=['アセットクラス', '銘柄名', '保有数量', '平均取得単価', '現在値', '取得金額', '評価額', '評価損益'])

df_assets['損益率(%)'] = np.where(df_assets['取得金額'] > 0, (df_assets['評価損益'] / df_assets['取得金額']) * 100, 0)


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
    # 色を少し多めに用意しておきます
    gold_palette = ['#C5A059', '#A67C00', '#BF953F', '#FCF6BA', '#B38728', '#FBF5B7', '#8B6914', '#EEDC82']
    fig_pie.update_traces(marker=dict(colors=gold_palette, line=dict(color='#0A0A0A', width=2)))
    st.plotly_chart(fig_pie, use_container_width=True)

with g2:
    top_assets = df_assets[df_assets['評価額'] > 0].sort_values('評価額', ascending=False).head(10)
    fig_bar = px.bar(top_assets, x='銘柄名', y='評価額', text_auto='.2s')
    fig_bar.update_layout(
        title=dict(text='保有銘柄 トップ10', font=dict(color='#C5A059', size=20)),
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
# 現金や不動産CFは「数量」の概念がないため「-」で表示し、それ以外は数値を表示します
display_df['保有数量'] = display_df.apply(lambda x: '-' if x['アセットクラス'] in ['現金・預金', '不動産CF'] else f"{x['保有数量']:,.2f}", axis=1)
display_df['平均取得単価'] = display_df.apply(lambda x: '-' if x['アセットクラス'] in ['現金・預金', '不動産CF'] else f"¥ {x['平均取得単価']:,.0f}", axis=1)
display_df['現在値'] = display_df.apply(lambda x: '-' if x['アセットクラス'] in ['現金・預金', '不動産CF'] else f"¥ {x['現在値']:,.0f}", axis=1)
display_df['評価額'] = display_df['評価額'].apply(lambda x: f"¥ {x:,.0f}")
display_df['評価損益'] = display_df['評価損益'].apply(lambda x: f"¥ {x:,.0f}")
display_df['損益率(%)'] = display_df['損益率(%)'].apply(lambda x: f"{x:+.2f} %" if x != 0 else "-")

st.dataframe(display_df.drop(columns=['取得金額']), use_container_width=True)
