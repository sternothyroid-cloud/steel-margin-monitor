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
fx_rate = st.sidebar.number_input("实时美元汇率 (CNY/USD)", value=7.24, step=0.01)

# --- 3. 稳健的数据抓取逻辑 ---
@st.cache_data(ttl=3600)
def load_gold_data():
    try:
        # A. 获取国内沪金主力数据 (AU0) - 新浪接口极其稳定
        df_au = ak.futures_zh_daily_sina(symbol="AU0")
        df_au = df_au[['date', 'close']].rename(columns={'close': 'AU_CN'})
        df_au['date'] = pd.to_datetime(df_au['date'])

        # B. 获取国际黄金数据 (COMEX 黄金) 
        # 修复点：使用新的海外合约接口获取历史数据
        try:
            # 尝试最新的东财海外行情接口 (GC 为 COMEX 黄金代码)
            df_gc = ak.futures_foreign_hist_em(symbol="GC") 
        except (AttributeError, Exception):
            # 如果上面的失败，改用这个通用的全球指数/期货历史接口
            st.warning("正在切换国际行情数据源...")
            # 这是一个非常稳健的备选方案
            df_gc = ak.futures_index_gh_sina(symbol="GC") 
            
        # 统一清理国际数据格式
        if '日期' in df_gc.columns:
            df_gc = df_gc.rename(columns={'日期': 'date', '收盘': 'AU_Global'})
        elif 'date' in df_gc.columns:
            df_gc = df_gc.rename(columns={'close': 'AU_Global'})
            
        df_gc['date'] = pd.to_datetime(df_gc['date'])
        
        # C. 数据对齐与计算
        df = pd.merge(df_au, df_gc, on='date', how='inner').sort_values('date')
        
        # 换算逻辑：1盎司=31.1035克
        df['AU_Global_CNY'] = (df['AU_Global'] / 31.1035) * fx_rate
        df['Margin'] = df['AU_CN'] - df['AU_Global_CNY']
        
        return df[df['date'] >= '2023-01-01']
        
    except Exception as e:
        st.error(f"⚠️ 数据诊断失败：{str(e)}")
        st.info("💡 建议：在 GitHub 的 requirements.txt 中将 akshare 版本锁定为最新，或尝试在本地运行 pip install akshare --upgrade")
        return pd.DataFrame()

# --- 4. 统计分析与展示 ---
df_data = load_gold_data()

if not df_data.empty:
    df = df_data.copy()
    df['mean'] = df['Margin'].rolling(window=window).mean()
    df['std'] = df['Margin'].rolling(window=window).std()
    df['z_score'] = (df['Margin'] - df['mean']) / df['std']
    df['upper'] = df['mean'] + 2 * df['std']
    df['lower'] = df['mean'] - 2 * df['std']
    
    # 仪表盘
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    z = latest['z_score']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("内外价差 (元/克)", f"{latest['Margin']:.2f} ¥", f"{latest['Margin']-prev['Margin']:.2f} ¥")
    col2.metric("Z-Score", f"{z:.2f}", f"{z-prev['z_score']:.2f}", delta_color="inverse")
    
    with col3:
        if z > 2: st.success("🟢 建议：卖国内/买国际 (价差回归预期)")
        elif z < -2: st.error("🔴 建议：买国内/卖国际 (溢价处于低位)")
        else: st.info("⚪ 状态：价差波动正常")

    # 绘图
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['upper'], line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=df['date'], y=df['lower'], fill='tonexty', 
                             fillcolor='rgba(255, 215, 0, 0.15)', line=dict(width=0), name="±2σ 统计通道"))
    fig.add_trace(go.Scatter(x=df['date'], y=df['Margin'], name="内外价差", line=dict(color='gold', width=2)))
    fig.add_trace(go.Scatter(x=df['date'], y=df['mean'], name="均值", line=dict(dash='dash', color='gray')))
    
    fig.update_layout(
        hovermode="x unified", 
        template="plotly_dark", 
        height=600,
        yaxis_title="价差 (元/克)",
        xaxis_title="日期"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("正在等待接口响应，或尝试检查 requirements.txt 中 akshare 是否为最新版。")
