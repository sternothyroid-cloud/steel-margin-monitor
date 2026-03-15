import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import akshare as ak

# --- 1. 页面配置 ---
st.set_page_config(page_title="黄金内外盘套利看板", layout="wide")
st.title("🏆 黄金内外盘价差统计套利看板")

st.latex(r'''
\text{Spread} = \text{Price}_{CN} - (\frac{\text{Price}_{Global}}{31.1035} \times \text{ExchangeRate})
''')

# --- 2. 侧边栏配置 ---
st.sidebar.header("参数配置")
window = st.sidebar.slider("统计窗口 (天)", 30, 500, 120)

# --- 3. 数据抓取与对齐 ---
@st.cache_data(ttl=3600)
def load_gold_arb_data():
    try:
        # 抓取国内沪金主力行情 (AU0)
        df_au = ak.futures_main_history_em(symbol="AU0")
        df_au = df_au[['日期', '收盘']].rename(columns={'日期': 'date', '收盘': 'AU_CN'})
        
        # 抓取国际 COMEX 黄金 (GC)
        df_gc = ak.futures_foreign_hist_em(symbol="GC")
        df_gc = df_gc[['日期', '收盘']].rename(columns={'日期': 'date', '收盘': 'AU_Global'})
        
        # 抓取美元汇率 (简单起见使用 7.2 固定或实时接口)
        # 这里为了稳健使用固定汇率模拟，实战建议接入 ak.fx_spot_quote()
        fx_rate = 7.24 
        
        # 合并数据
        df_au['date'] = pd.to_datetime(df_au['date'])
        df_gc['date'] = pd.to_datetime(df_gc['date'])
        df = pd.merge(df_au, df_gc, on='date', how='inner').sort_values('date')
        
        # 换算逻辑：1盎司=31.1035克
        df['AU_Global_CNY'] = (df['AU_Global'] / 31.1035) * fx_rate
        
        # 计算价差 (单位：元/克)
        df['Margin'] = df['AU_CN'] - df['AU_Global_CNY']
        
        return df[df['date'] >= '2022-01-01']
    except Exception as e:
        st.error(f"数据获取失败: {e}")
        return pd.DataFrame()

# --- 4. 统计逻辑与绘图 ---
df_data = load_gold_arb_data()

if not df_data.empty:
    df = df_data.copy()
    df['mean'] = df['Margin'].rolling(window=window).mean()
    df['std'] = df['Margin'].rolling(window=window).std()
    df['z_score'] = (df['Margin'] - df['mean']) / df['std']
    df['upper'] = df['mean'] + 2 * df['std']
    df['lower'] = df['mean'] - 2 * df['std']
    
    # 仪表盘
    latest = df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("内外价差 (元/克)", f"{latest['Margin']:.2f} ¥")
    col2.metric("Z-Score", f"{latest['z_score']:.2f}")
    
    with col3:
        z = latest['z_score']
        if z > 2: st.success("🟢 建议：卖国内/买国际")
        elif z < -2: st.error("🔴 建议：买国内/卖国际")
        else: st.info("⚪ 建议：价差波动正常")

    # 绘图
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['upper'], line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=df['date'], y=df['lower'], fill='tonexty', 
                             fillcolor='rgba(255, 215, 0, 0.1)', line=dict(width=0), name="±2σ 统计通道"))
    fig.add_trace(go.Scatter(x=df['date'], y=df['Margin'], name="内外价差", line=dict(color='gold', width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['mean'], name="均值", line=dict(dash='dash', color='gray')))
    
    fig.update_layout(hovermode="x unified", template="plotly_dark", height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("暂无数据，请检查网络连接或接口。")
