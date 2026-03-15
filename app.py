import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import akshare as ak
from datetime import datetime

# --- 1. 页面配置 ---
st.set_page_config(page_title="黑色系真实利润看板", layout="wide")
st.title("🏗️ 黑色系产业链利润实战看板 (实时数据版)")

# --- 2. 侧边栏参数 ---
st.sidebar.header("策略参数配置")
window = st.sidebar.slider("统计窗口周期 (天)", 30, 750, 250)
cost = st.sidebar.number_input("综合加工成本 (¥)", value=900)
ratio_i = 1.6
ratio_j = 0.5

# --- 3. 真实数据抓取逻辑 ---
@st.cache_data(ttl=3600) # 缓存1小时，避免频繁请求封IP
@st.cache_data(ttl=3600)
def load_real_data():
    try:
        # 使用更稳健的 get_futures_daily 或替代逻辑获取数据
        # 标的代码：RB0, I0, J0 分别代表螺纹、铁矿、焦炭的主力连续合约
        
        # 抓取数据（这里使用东财或新浪的通用期货接口）
        def fetch_commodity(symbol):
            # 尝试使用最新的主力连续合约接口
            data = ak.futures_main_history_em(symbol=symbol)
            return data

        # 如果你的版本确实没有 futures_main_history_em，尝试 fallback 到另一个常用接口
        try:
            rb_df = ak.futures_main_history_em(symbol="RB0")
            i_df = ak.futures_main_history_em(symbol="I0")
            j_df = ak.futures_main_history_em(symbol="J0")
        except AttributeError:
            # Fallback 方案：使用新浪财经的主力合约接口
            st.warning("正在尝试备用数据源...")
            rb_df = ak.futures_zh_daily_sina(symbol="RB0")
            i_df = ak.futures_zh_daily_sina(symbol="I0")
            j_df = ak.futures_zh_daily_sina(symbol="J0")

        # 数据清洗函数
        def clean_df(df, name):
            # 不同接口返回的列名可能不同，这里做适配
            if '日期' in df.columns:
                df = df[['日期', '收盘']]
            elif 'date' in df.columns:
                df = df[['date', 'close']]
            
            df.columns = ['date', name]
            df['date'] = pd.to_datetime(df['date'])
            df[name] = pd.to_numeric(df[name], errors='coerce')
            return df

        rb = clean_df(rb_df, 'RB')
        i = clean_df(i_df, 'I')
        j = clean_df(j_df, 'J')
        
        # 合并
        final_df = rb.merge(i, on='date').merge(j, on='date')
        final_df = final_df[final_df['date'] >= '2021-01-01'].sort_values('date')
        return final_df.dropna()

    except Exception as e:
        st.error(f"行情获取失败，请尝试在本地运行 'pip install akshare --upgrade'。详情: {e}")
        return pd.DataFrame()
# --- 4. 执行计算 ---
df_raw = load_real_data()

if not df_raw.empty:
    df = df_raw.copy()
    # 计算实时利润
    df['Margin'] = df['RB'] - (ratio_i * df['I'] + ratio_j * df['J'] + cost)
    
    # 计算统计指标
    df['mean'] = df['Margin'].rolling(window=window, min_periods=1).mean()
    df['std'] = df['Margin'].rolling(window=window, min_periods=1).std()
    df['z_score'] = (df['Margin'] - df['mean']) / df['std']
    df['upper'] = df['mean'] + 2 * df['std']
    df['lower'] = df['mean'] - 2 * df['std']

    # --- 5. 仪表盘看板 ---
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    z = latest['z_score']

    col1, col2, col3 = st.columns(3)
    col1.metric("实时炼钢利润", f"{latest['Margin']:.1f} ¥", f"{latest['Margin']-prev['Margin']:.1f} ¥")
    col2.metric("当前 Z-Score", f"{z:.2f}", f"{z-prev['z_score']:.2f}", delta_color="inverse")
    
    with col3:
        if z < -2: st.error("🔴 极端低估：做多利润")
        elif z > 2: st.success("🟢 极端高估：做空利润")
        else: st.info("⚪ 正常区间：观望")

    # --- 6. 交互式绘图 ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['upper'], line=dict(width=0), showlegend=False))
    fig.add_trace(go.Scatter(x=df['date'], y=df['lower'], fill='tonexty', 
                             fillcolor='rgba(100, 100, 100, 0.2)', line=dict(width=0), name="±2σ 统计区间"))
    fig.add_trace(go.Scatter(x=df['date'], y=df['mean'], name="均值线", line=dict(dash='dash', color='gray')))
    fig.add_trace(go.Scatter(x=df['date'], y=df['Margin'], name="真实利润", line=dict(color='#1f77b4', width=1.5)))
    
    fig.update_layout(hovermode="x unified", template="plotly_dark", height=600, xaxis_title="日期", yaxis_title="利润 (¥/吨)")
    st.plotly_chart(fig, use_container_width=True)

    # 导出按钮
    st.download_button("下载真实利润数据 (CSV)", df.to_csv(index=False), "real_steel_margin.csv", "text/csv")
