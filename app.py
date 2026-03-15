@st.cache_data(ttl=3600)
def load_gold_data():
    try:
        # 1. 获取沪金主力数据 (人民币/克)
        df_au = ak.futures_main_history_em(symbol="AU0")
        df_au = df_au[['日期', '收盘']]
        df_au.columns = ['date', 'AU_Domestic']
        df_au['date'] = pd.to_datetime(df_au['date'])

        # 2. 获取美元兑人民币汇率 (用于折算)
        # 实际操作中应使用实时汇率，这里取近似或历史汇率接口
        df_fx = ak.com_currency_boc_safe() # 获取最新外汇牌价作为参考
        current_fx = float(df_fx[df_fx['币种'] == '美元']['中银汇率折算价'].iloc[0]) / 100
        
        # 3. 获取国际金价 (美元/盎司) - 伦敦金
        # 注意：1盎司 = 31.1035克
        df_global = ak.futures_foreign_hist_em(symbol="GC") # COMEX黄金
        df_global = df_global[['日期', '收盘']]
        df_global.columns = ['date', 'AU_Global_USD']
        df_global['date'] = pd.to_datetime(df_global['date'])

        # 合并数据
        df = pd.merge(df_au, df_global, on='date')
        
        # 4. 核心转换公式：将国际金价折算为 人民币/克
        # 计算公式：(美元价格 / 31.1035) * 汇率
        df['AU_Global_CNY'] = (df['AU_Global_USD'] / 31.1035) * current_fx
        
        # 5. 计算价差 (Spread)
        df['Margin'] = df['AU_Domestic'] - df['AU_Global_CNY']
        
        return df[df['date'] >= '2021-01-01'].sort_values('date')
    except Exception as e:
        st.error(f"黄金数据抓取失败: {e}")
        return pd.DataFrame()
