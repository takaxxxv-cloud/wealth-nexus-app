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
# 💎 カスタムCSS（ブラック＆ゴールド）
# ==========================================
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@300;400;600&display=swap');

    html, body, [class*="css"] { font-family: 'Noto Serif JP', serif !important; }
    .stApp { background-color: #0A0A0A; color: #F2F2F2; }
    [data-testid="stSidebar"] { background-color: #141414 !important; border-right: 1px solid #332918; }
    
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
# 📊 ダミーデータの生成（確認用）
# ==========================================
data = {
    'アセットクラス': ['国内株式', '米国株式', '米国株式', '投資信託', '暗号資産', '現金・預金'],
    '銘柄名': ['トヨタ自動車', 'Apple Inc.', 'Microsoft Corp.', 'eMAXIS Slim 全世界株式', 'Bitcoin', '日本円'],
    '保有数量': [2000, 300, 200, 1500000, 2.5, 1],
    '平均取得単価': [2500, 150, 300, 18000, 8000000, 25000000],
    '現在値': [3500, 180, 410, 23000, 10500000, 25000000]
}
df_assets = pd.DataFrame(data)
df_assets['取得金額'] = np.where(df_assets['アセットクラス'] == '現金・預金', df_assets['平均取得単価'], df_assets['保有数量'] * df_assets['平均取得単価'])
df_assets['評価額'] = np.where(df_assets['アセットクラス'] == '現金・預金', df_assets['現在値'], df_assets['保有数量'] * df_assets['現在値'])
df_assets['評価損益'] = df_assets['評価額'] - df_assets['取得金額']
df_assets['損益率(%)'] = (df_assets['評価損益'] / df_assets['取得金額']) * 100

months = [(datetime.today() - timedelta(days=30*i)).strftime('%Y-%m') for i in range(11, -1, -1)]
trend_values = [85000000, 86000000, 84000000, 89000000, 92000000, 91000000, 95000000, 98000000, 102000000, 100000000, 105000000, df_assets['評価額'].sum()]
df_trend = pd.DataFrame({'年月': months, '総資産額': trend_values})

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
profit_rate = (total_profit / df_assets['取得金額'].sum()) * 100
last_month_assets = df_trend['総資産額'].iloc[-2]
mom_diff = total_assets - last_month_assets

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="総資産額", value=f"¥ {total_assets:,.0f}", delta=f"前月比: {mom_diff:,.0f} 円")
with col2:
    st.metric(label="トータルリターン（評価損益）", value=f"¥ {total_profit:,.0f}", delta=f"{profit_rate:.2f} %")
with col3:
    st.metric(label="現金比率", value=f"{(df_assets[df_assets['アセットクラス'] == '現金・預金']['評価額'].sum() / total_assets)*100:.1f} %")

st.write("")
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
    fig_line = px.line(df_trend, x='年月', y='総資産額', markers=True)
    fig_line.update_layout(
        title=dict(text='資産推移（過去12ヶ月）', font=dict(color='#C5A059', size=20)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#8C8C8C'),
        xaxis=dict(showgrid=False, color='#8C8C8C'),
        yaxis=dict(showgrid=True, gridcolor='#332918', color='#8C8C8C'),
        margin=dict(t=50, b=20, l=0, r=0)
    )
    fig_line.update_traces(line_color='#C5A059', line_width=3, marker=dict(size=8, color='#F2F2F2'))
    fig_line.add_trace(go.Scatter(x=df_trend['年月'], y=df_trend['総資産額'], fill='tozeroy', fillcolor='rgba(197, 160, 89, 0.1)', line=dict(color='rgba(255,255,255,0)'), showlegend=False))
    st.plotly_chart(fig_line, use_container_width=True)

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
