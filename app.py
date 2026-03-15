import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go # 建议使用 Plotly，支持交互缩放

# 设置页面
st.set_page_config(page_title="黑色系产业链利润监控", layout="wide")

st.title("🏗️ 黑色系虚拟炼钢利润统计套利监控")

# 侧边栏参数设置
st.sidebar.header("策略参数配置")
ratio_i = st.sidebar.slider("铁矿石配比", 1.4, 1.8, 1.6)
ratio_j = st.sidebar.slider("焦炭配比", 0.4, 0.6, 0.5)
cost = st.sidebar.number_input("综合加工成本", value=900)
window = st.sidebar.selectbox("滚动均值周期", [120, 250, 500], index=1)

# 获取数据 (实战中这里替换为 AkShare)
@st.cache_data # 缓存数据，避免重复抓取
def load_data():
    # 这里模拟抓取数据的逻辑
    dates = pd.date_range(start="2024-01-01", periods=500, freq="D")
    df = pd.DataFrame({
        'date': dates,
        'RB': np.random.normal(3800, 200, 500).cumsum() / 10 + 3500,
        'I': np.random.normal(800, 50, 500).cumsum() / 10 + 750,
        'J': np.random.normal(2200, 100, 500).cumsum() / 10 + 2100
    })
    return df

df = load_data()

# 计算逻辑
df['Margin'] = df['RB'] - (ratio_i * df['I'] + ratio_j * df['J'] + cost)
df['mean'] = df['Margin'].rolling(window=window).mean()
df['std'] = df['Margin'].rolling(window=window).std()
df['z_score'] = (df['Margin'] - df['mean']) / df['std']

# 绘制图表
fig = go.Figure()
fig.add_trace(go.Scatter(x=df['date'], y=df['Margin'], name="实时利润"))
fig.add_trace(go.Scatter(x=df['date'], y=df['mean'], name="均值线", line=dict(dash='dash')))
fig.add_trace(go.Scatter(x=df['date'], y=df['mean'] + 2*df['std'], name="上轨 (+2σ)", line=dict(width=0)))
fig.add_trace(go.Scatter(x=df['date'], y=df['mean'] - 2*df['std'], name="下轨 (-2σ)", fill='tonexty', line=dict(width=0)))

st.plotly_chart(fig, use_container_width=True)

# 实时信号预警
latest_z = df['z_score'].iloc[-1]
if latest_z < -2:
    st.error(f"⚠️ 当前 Z-Score: {latest_z:.2f} —— 利润极端低估，建议做多利润")
elif latest_z > 2:
    st.success(f"🚀 当前 Z-Score: {latest_z:.2f} —— 利润高企，建议做空利润")
else:
    st.info(f"📊 当前 Z-Score: {latest_z:.2f} —— 利润处于正常区间")