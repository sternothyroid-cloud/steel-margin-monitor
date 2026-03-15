import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 页面配置 ---
st.set_page_config(page_title="黑色系套利看板", layout="wide")
st.title("🏗️ 黑色系产业链利润统计套利看板")

# 公式展示
st.latex(r'''
\text{Profit} = \text{Price}_{RB} - (1.6 \times \text{Price}_{I} + 0.5 \times \text{Price}_{J} + \text{Cost})
''')

# --- 2. 侧边栏参数 ---
st.sidebar.header("策略参数配置")
ratio_i = st.sidebar.slider("铁矿石配比", 1.4, 1.8, 1.6)
ratio_j = st.sidebar.slider("焦炭配比", 0.4, 0.6, 0.5)
cost = st.sidebar.number_input("综合加工成本", value=900)
window = st.sidebar.selectbox("统计窗口(天)", [60, 120, 250], index=1)

# --- 3. 数据加载 (带容错处理) ---
@st.cache_data
def load_data():
    # 生成 500 天数据确保窗口足够
    dates = pd.date_range(start="2024-01-01", periods=800, freq="D")
    n = len(dates)
    # 模拟利润均值回归逻辑
    margin = np.zeros(n)
    margin[0] = 300
    mu, theta, sigma = 350, 0.05, 40
    for i in range(1, n):
        margin[i] = margin[i-1] + theta * (mu - margin[i-1]) + np.random.normal(0, sigma)
    
    return pd.DataFrame({'date': dates, 'Margin': margin})

# 核心：确保 df 被正确赋值
try:
    df_raw = load_data()
    df = df_raw.copy()

    # --- 4. 统计指标计算 ---
    df['mean'] = df['Margin'].rolling(window=window, min_periods=1).mean()
    df['std'] = df['Margin'].rolling(window=window, min_periods=1).std()
    df['z_score'] = (df['Margin'] - df['mean']) / df['std']
    df['upper'] = df['mean'] + 2 * df['std']
    df['lower'] = df['mean'] - 2 * df['std']

    # --- 5. 提取最新数据 (解决 iloc 报错) ---
    if not df.empty:
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        z = latest['z_score']

        # --- 6. 核心指标显示 ---
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("实时利润", f"{latest['Margin']:.1f} ¥", f"{latest['Margin']-prev['Margin']:.1f} ¥")
        with col2:
            st.metric("Z-Score", f"{z:.2f}", f"{z-prev['z_score']:.2f}", delta_color="inverse")
        with col3:
            advice = "🔴 强力买入利润" if z < -2 else "🟢 强力卖出利润" if z > 2 else "⚪ 观望/持有"
            st.subheader(advice)

        # --- 7. 绘图 ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['upper'], line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=df['date'], y=df['lower'], fill='tonexty', 
                                 fillcolor='rgba(255, 0, 0, 0.1)', line=dict(width=0), name="±2σ 统计区间"))
        fig.add_trace(go.Scatter(x=df['date'], y=df['mean'], name="均值", line=dict(dash='dash', color='gray')))
        fig.add_trace(go.Scatter(x=df['date'], y=df['Margin'], name="实时利润", line=dict(color='#1f77b4', width=2)))
        
        fig.update_layout(hovermode="x unified", template="plotly_dark", height=500)
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"发生错误: {e}")
    st.info("提示：请检查数据加载逻辑或清除 Streamlit 缓存重新运行。")
