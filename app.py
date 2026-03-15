import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 优化模拟数据逻辑 ---
@st.cache_data
def load_data():
    dates = pd.date_range(start="2024-01-01", end="2026-03-15", freq="D")
    n = len(dates)
    # 使用 Ornstein-Uhlenbeck 过程模拟利润，确保它在 [ -200, 1000 ] 之间均值回归
    margin = np.zeros(n)
    margin[0] = 300 # 起始利润
    mu, theta, sigma = 350, 0.05, 40 # 均值350，回归强度0.05
    for i in range(1, n):
        margin[i] = margin[i-1] + theta * (mu - margin[i-1]) + np.random.normal(0, sigma)
    
    df = pd.DataFrame({'date': dates, 'Margin': margin})
    return df

df = load_data()

# --- 2. 统计指标计算 ---
window = 120 # 缩短窗口，让信号更灵敏
df['mean'] = df['Margin'].rolling(window=window, min_periods=1).mean() # min_periods=1 解决冷启动没图的问题
df['std'] = df['Margin'].rolling(window=window, min_periods=1).std()
df['upper'] = df['mean'] + 2 * df['std']
df['lower'] = df['mean'] - 2 * df['std']

# --- 3. 修正 Plotly 绘图顺序 ---
fig = go.Figure()

# 先画上轨线 (不显示)
fig.add_trace(go.Scatter(x=df['date'], y=df['upper'], line=dict(width=0), showlegend=False))

# 再画下轨线并填充至上轨 (形成阴影带)
fig.add_trace(go.Scatter(
    x=df['date'], y=df['lower'], 
    fill='tonexty', 
    fillcolor='rgba(255, 0, 0, 0.1)', # 淡淡的红色阴影
    line=dict(width=0),
    name="±2σ 统计区间"
))

# 画均值线
fig.add_trace(go.Scatter(x=df['date'], y=df['mean'], name="均值 (MA)", line=dict(dash='dash', color='gray')))

# 最后画实时利润线（确保它在最上层）
fig.add_trace(go.Scatter(x=df['date'], y=df['Margin'], name="实时炼钢利润", line=dict(color='#1f77b4', width=2)))

fig.update_layout(hovermode="x unified", yaxis_title="利润 (元/吨)", template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)
