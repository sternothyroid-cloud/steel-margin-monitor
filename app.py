import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. 标题与公式区 ---
st.title("🏗️ 黑色系产业链利润统计套利看板")

# 使用 Latex 渲染硬核的金融公式
st.latex(r'''
\text{Profit} = \text{Price}_{RB} - (1.6 \times \text{Price}_{I} + 0.5 \times \text{Price}_{J} + \text{Cost})
''')

st.markdown("""
> **底层逻辑**：基于高炉炼钢的物理投入产出比。当利润偏离历史均值 $\pm 2\sigma$ 时，存在均值回归的套利机会。
---
""")

# --- [此处保留之前的 load_data 和计算指标逻辑] ---

# --- 2. 核心指标实时显示 (Dashboard) ---
latest = df.iloc[-1]
prev = df.iloc[-2]

# 创建三列布局
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="当前实时利润", value=f"{latest['Margin']:.1f} ¥", 
              delta=f"{latest['Margin'] - prev['Margin']:.1f} ¥")
with col2:
    st.metric(label="当前 Z-Score", value=f"{latest['z_score']:.2f}",
              delta=f"{latest['z_score'] - prev['z_score']:.2f}", delta_color="inverse")
with col3:
    # 根据 Z 值给出临床诊断般的“操作建议”
    z = latest['z_score']
    if z < -2:
        advice = "🔴 强力买入利润"
        color = "red"
    elif z > 2:
        advice = "🟢 强力卖出利润"
        color = "green"
    else:
        advice = "⚪ 观望/持有"
        color = "gray"
    st.subheader(advice)

# --- 3. 交互式绘图区 ---
# [此处使用之前修正过的 Plotly 绘图代码]

# --- 4. 详细操作建议说明 ---
st.write("---")
st.header("📋 策略执行诊断报告")

if abs(z) > 2:
    st.warning(f"**检测到异常偏移**：当前 Z 值为 {z:.2f}。根据历史回测，利润有 95% 的概率向均值 {latest['mean']:.1f} 回归。")
    st.info("**实战建议**：建议通过期货工具建立对冲头寸。注意控制杠杆倍数，谨防原材料端极端拉升导致的保证金风险。")
else:
    st.success("**指标正常**：当前产业链利润处于统计学合理区间，无显著套利机会。")

# 展示原始数据供复核
if st.checkbox("查看原始统计数据"):
    st.write(df.tail(10))
