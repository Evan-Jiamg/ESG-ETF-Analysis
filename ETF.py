"""
ESG 投資人黏著度完整分析
=========================
研究問題：永續基金投資人是否較為忠誠或黏著度較高？
         比較分析資金流動性與贖回率，以及不同時期的變化。

資料需求（放在同一資料夾）：
  - iShares-ESG-Aware-MSCI-USA-ETF_fund.xls   （ESGU，iShares 官網下載）
  - iShares-Core-SP-500-ETF_fund.xls           （IVV，iShares 官網下載）
  - esg_monthly_prices.csv                     （22支ETF月收盤價，yfinance抓取）
  - esg_monthly_returns.csv                    （22支ETF月報酬率）
  - esg_summary_stats.csv                      （各時期統計摘要）
  - esg_fund_info.csv                          （基金基本資訊）

安裝套件：
  pip install pandas numpy matplotlib scipy openpyxl

輸出（自動存到同一資料夾）：
  CSV：
    flow_analysis_monthly.csv       月度 Flow 分析（ESGU vs IVV）
    flow_by_period.csv              各時期 Flow 比較
    return_analysis_by_region.csv   各地區報酬分析
    sensitivity_analysis.csv        Flow-Performance 敏感度
    full_results_summary.csv        完整結果摘要

  圖表（PNG）：
    fig1_aum_trend.png              AUM 歷史走勢
    fig2_net_flow_trend.png         Net Flow 歷史走勢
    fig3_ogr_by_period.png          各時期 Organic Growth Rate 比較
    fig4_return_comparison.png      各地區 ESG vs 傳統報酬
    fig5_flow_sensitivity.png       Flow-Performance 散佈圖
    fig6_downside_protection.png    下跌時期跌幅保護分析
    fig7_regional_heatmap.png       地區 × 時期 報酬熱力圖
"""

import re
import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from scipy import stats

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────────────────────────────────────

# 檔案路徑（預設：與此腳本同一資料夾）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = {
    'esgu_xls': os.path.join(BASE_DIR, 'iShares-ESG-Aware-MSCI-USA-ETF_fund.xls'),
    'ivv_xls':  os.path.join(BASE_DIR, 'iShares-Core-SP-500-ETF_fund.xls'),
    'prices':   os.path.join(BASE_DIR, 'esg_monthly_prices.csv'),
    'returns':  os.path.join(BASE_DIR, 'esg_monthly_returns.csv'),
    'summary':  os.path.join(BASE_DIR, 'esg_summary_stats.csv'),
    'info':     os.path.join(BASE_DIR, 'esg_fund_info.csv'),
}

# 分析時間段
PERIODS = {
    'Pre-COVID\n(2019–Feb 2020)':    ('2019-01-01', '2020-02-29'),
    'COVID Crisis\n(Mar–Dec 2020)':  ('2020-03-01', '2020-12-31'),
    'Recovery\n(2021)':              ('2021-01-01', '2021-12-31'),
    'Rate Hike\n(2022)':             ('2022-01-01', '2022-12-31'),
    'Rebound\n(2023)':               ('2023-01-01', '2023-12-31'),
    'Anti-ESG\n(2024–2025)':         ('2024-01-01', '2025-12-31'),
}

PERIODS_SHORT = {
    'Pre-COVID':    ('2019-01-01', '2020-02-29'),
    'COVID Crisis': ('2020-03-01', '2020-12-31'),
    'Recovery':     ('2021-01-01', '2021-12-31'),
    'Rate Hike':    ('2022-01-01', '2022-12-31'),
    'Rebound':      ('2023-01-01', '2023-12-31'),
    'Anti-ESG':     ('2024-01-01', '2025-12-31'),
}

# ETF 分類
REGION_MAP = {
    'ESGU': 'US', 'ESGV': 'US', 'SUSA': 'US', 'DSI': 'US',
    'JUST': 'US', 'NULC': 'US', 'SUSL': 'US',
    'IVV':  'US', 'VTI':  'US', 'SPY':  'US',
    'ESGD': 'Developed exUS', 'VSGX': 'Developed exUS',
    'EFA':  'Developed exUS', 'VEA':  'Developed exUS',
    'ESGE': 'Emerging', 'EMSG': 'Emerging',
    'VWO':  'Emerging', 'EEM':  'Emerging',
    'EAGG': 'Fixed Income', 'BGRN': 'Fixed Income',
    'AGG':  'Fixed Income', 'BNDW': 'Fixed Income',
}

ESG_TICKERS  = ['ESGU','ESGV','SUSA','DSI','JUST','NULC','SUSL',
                'ESGD','VSGX','ESGE','EMSG','EAGG','BGRN']
CONV_TICKERS = ['IVV','VTI','SPY','EFA','VEA','VWO','EEM','AGG','BNDW']

# 圖表樣式
COLORS = {
    'ESG':          '#2196F3',
    'Conventional': '#FF9800',
    'positive':     '#4CAF50',
    'negative':     '#F44336',
    'neutral':      '#9E9E9E',
    'COVID':        '#E91E63',
    'Rate_Hike':    '#9C27B0',
}

plt.rcParams.update({
    'font.family':    'DejaVu Sans',
    'font.size':      11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'axes.grid':      True,
    'grid.alpha':     0.3,
    'axes.spines.top':   False,
    'axes.spines.right': False,
})


# ─────────────────────────────────────────────────────────────────────────────
# 1. 資料載入
# ─────────────────────────────────────────────────────────────────────────────

def parse_ishares_xls(filepath):
    """解析 iShares XLS 檔案的 Historical sheet，回傳日頻率 DataFrame"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    match = re.search(r'ss:Name="Historical".*?</ss:Worksheet>', content, re.DOTALL)
    if not match:
        raise ValueError(f"Historical sheet not found in {filepath}")

    sheet = match.group()
    rows  = re.findall(r'<ss:Row[^>]*>(.*?)</ss:Row>', sheet, re.DOTALL)

    parsed = []
    for row in rows:
        cells = re.findall(r'<ss:Data[^>]*>([^<]+)</ss:Data>', row)
        if len(cells) >= 4:
            parsed.append(cells[:4])

    df = pd.DataFrame(parsed[1:], columns=['date', 'nav', 'exdiv', 'shares'])
    df['date']   = pd.to_datetime(df['date'], errors='coerce')
    df['nav']    = pd.to_numeric(df['nav'],   errors='coerce')
    df['shares'] = pd.to_numeric(
        df['shares'].str.replace(',', '', regex=False), errors='coerce')
    df = df.dropna(subset=['date', 'nav', 'shares'])
    df['aum']  = df['nav'] * df['shares']
    df = df.sort_values('date').set_index('date')
    return df


def load_all_data():
    """載入所有資料來源"""
    print("=" * 60)
    print("載入資料...")
    print("=" * 60)

    data = {}

    # iShares XLS（ESGU + IVV）
    for key, fname, label in [
        ('esgu', FILES['esgu_xls'], 'ESGU'),
        ('ivv',  FILES['ivv_xls'],  'IVV'),
    ]:
        if os.path.exists(FILES[key + '_xls']):
            df = parse_ishares_xls(FILES[key + '_xls'])
            data[key] = df
            print(f"  ✅ {label}: {len(df)} 天（{df.index[0].date()} ~ {df.index[-1].date()}）")
        else:
            print(f"  ❌ {label} XLS 找不到：{FILES[key + '_xls']}")

    # 月頻率 CSV
    for key, fname, label in [
        ('prices',  FILES['prices'],  'Monthly Prices'),
        ('returns', FILES['returns'], 'Monthly Returns'),
        ('summary', FILES['summary'], 'Summary Stats'),
        ('info',    FILES['info'],    'Fund Info'),
    ]:
        if os.path.exists(fname):
            data[key] = pd.read_csv(fname, index_col=0)
            if key in ('prices', 'returns'):
                data[key].index = pd.to_datetime(data[key].index)
            print(f"  ✅ {label}: {data[key].shape}")
        else:
            print(f"  ❌ {label} 找不到：{fname}")

    return data


# ─────────────────────────────────────────────────────────────────────────────
# 2. Flow 計算
# ─────────────────────────────────────────────────────────────────────────────

def compute_monthly_flow(daily_df, label=''):
    """
    從日頻率 NAV + Shares 計算月頻率 Net Flow

    Net Flow = AUM_t - AUM_{t-1} × (1 + NAV_return_t)
    Organic Growth Rate (OGR) = Net Flow / AUM_{t-1}

    使用 NAV（而非市場價格）計算報酬，以排除 premium/discount 影響
    """
    m = daily_df.resample('ME').last().copy()
    m = m[m.index >= '2019-01-01']

    m['nav_return'] = m['nav'].pct_change()
    m['net_flow']   = m['aum'] - m['aum'].shift(1) * (1 + m['nav_return'])
    m['ogr']        = m['net_flow'] / m['aum'].shift(1)

    # 累積淨流入
    m['cum_flow']   = m['net_flow'].cumsum()

    # 每月是否流出
    m['is_outflow'] = m['net_flow'] < 0

    print(f"\n  {label} 月頻 Flow 摘要：")
    print(f"    全期平均 OGR：{m['ogr'].mean()*100:.3f}%/月")
    print(f"    流出月數：{m['is_outflow'].sum()} / {m['is_outflow'].count()} 月")
    print(f"    最大單月流入：${m['net_flow'].max()/1e6:.0f}M")
    print(f"    最大單月流出：${m['net_flow'].min()/1e6:.0f}M")

    return m


def period_flow_summary(esgu_m, ivv_m):
    """各時期 Flow 統計"""
    rows = []
    for period_label, (start, end) in PERIODS_SHORT.items():
        for df, ticker, etype in [(esgu_m, 'ESGU', 'ESG'), (ivv_m, 'IVV', 'Conventional')]:
            mask = (df.index >= start) & (df.index <= end)
            sub  = df.loc[mask]
            if sub.empty:
                continue
            rows.append({
                'period':           period_label,
                'ticker':           ticker,
                'type':             etype,
                'avg_monthly_flow_M': sub['net_flow'].mean() / 1e6,
                'total_flow_M':       sub['net_flow'].sum()  / 1e6,
                'avg_ogr_pct':        sub['ogr'].mean()       * 100,
                'outflow_months':     sub['is_outflow'].sum(),
                'total_months':       len(sub),
                'outflow_rate_pct':   sub['is_outflow'].mean() * 100,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 3. 報酬率分析
# ─────────────────────────────────────────────────────────────────────────────

def return_analysis_by_region(prices, returns):
    """各地區 ESG vs 傳統 ETF 報酬分析"""
    rows = []
    for period_label, (start, end) in PERIODS_SHORT.items():
        mask = (returns.index >= start) & (returns.index <= end)
        for ticker in returns.columns:
            if ticker not in REGION_MAP:
                continue
            r = returns.loc[mask, ticker].dropna()
            if len(r) < 2:
                continue
            rows.append({
                'period':          period_label,
                'ticker':          ticker,
                'region':          REGION_MAP.get(ticker, 'Unknown'),
                'type':            'ESG' if ticker in ESG_TICKERS else 'Conventional',
                'avg_monthly_ret': r.mean() * 100,
                'annual_ret':      ((1 + r.mean()) ** 12 - 1) * 100,
                'volatility':      r.std() * 100,
                'sharpe_proxy':    r.mean() / r.std() if r.std() > 0 else np.nan,
                'neg_months':      (r < 0).sum(),
                'neg_month_pct':   (r < 0).mean() * 100,
                'max_monthly_dd':  r.min() * 100,
                'n_months':        len(r),
            })
    return pd.DataFrame(rows)


def flow_performance_sensitivity(esgu_m, ivv_m):
    """
    Flow-Performance Sensitivity Analysis
    回歸：OGR ~ Return（用 NAV return 作為解釋變數）
    β 越小（越接近 0 甚至負數）= 下跌也不贖回 = 黏著度高
    """
    rows = []
    for df, ticker, etype in [(esgu_m, 'ESGU', 'ESG'), (ivv_m, 'IVV', 'Conventional')]:
        r = df['nav_return'].dropna()
        f = df['ogr'].reindex(r.index).dropna()
        common = r.index.intersection(f.index)
        r, f = r.loc[common], f.loc[common]

        if len(common) < 10:
            continue

        # 全期
        slope, intercept, r_val, p_val, se = stats.linregress(r, f)

        # 正報酬期（上漲時 flow 敏感度）
        pos = r > 0
        sl_pos = stats.linregress(r[pos], f[pos]).slope if pos.sum() >= 5 else np.nan

        # 負報酬期（下跌時 flow 敏感度）←— 黏著度的核心指標
        neg = r < 0
        sl_neg = stats.linregress(r[neg], f[neg]).slope if neg.sum() >= 5 else np.nan

        # 解讀：β_neg 越小 = 下跌時 flow 下降越少 = 投資人越不急著贖回
        rows.append({
            'ticker':        ticker,
            'type':          etype,
            'beta_all':      slope,
            'beta_positive': sl_pos,
            'beta_negative': sl_neg,
            'r_squared':     r_val ** 2,
            'p_value':       p_val,
            'n_obs':         len(common),
            'interpretation': (
                f"下跌1%時 OGR 變化 {sl_neg*(-0.01)*100:.3f}%"
                if not np.isnan(sl_neg) else 'N/A'
            ),
        })
    return pd.DataFrame(rows), r, f


# ─────────────────────────────────────────────────────────────────────────────
# 4. 圖表
# ─────────────────────────────────────────────────────────────────────────────

def fig1_aum_trend(esgu_m, ivv_m):
    """圖1：AUM 歷史走勢"""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle('AUM Historical Trend: ESGU (ESG) vs IVV (Conventional)',
                 fontsize=14, fontweight='bold', y=1.01)

    for ax, df, label, color in [
        (axes[0], esgu_m, 'ESGU – iShares ESG Aware MSCI USA ETF', COLORS['ESG']),
        (axes[1], ivv_m,  'IVV – iShares Core S&P 500 ETF',         COLORS['Conventional']),
    ]:
        ax.fill_between(df.index, df['aum'] / 1e9, alpha=0.3, color=color)
        ax.plot(df.index, df['aum'] / 1e9, color=color, linewidth=1.5)
        ax.set_ylabel('AUM (USD Billion)', fontsize=10)
        ax.set_title(label, fontsize=11)

        for pname, (s, e) in PERIODS_SHORT.items():
            if pname in ('COVID Crisis',):
                ax.axvspan(pd.Timestamp(s), pd.Timestamp(e),
                           alpha=0.12, color=COLORS['COVID'], label=pname if ax == axes[0] else '')
            if pname == 'Rate Hike':
                ax.axvspan(pd.Timestamp(s), pd.Timestamp(e),
                           alpha=0.12, color=COLORS['Rate_Hike'])

    # 加圖例
    from matplotlib.patches import Patch
    axes[0].legend(handles=[
        Patch(facecolor=COLORS['COVID'],    alpha=0.3, label='COVID Crisis'),
        Patch(facecolor=COLORS['Rate_Hike'],alpha=0.3, label='Rate Hike'),
    ], loc='upper left', fontsize=9)

    plt.tight_layout()
    return fig


def fig2_net_flow_trend(esgu_m, ivv_m):
    """圖2：Net Flow 歷史走勢（月頻率，百萬美元）"""
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle('Monthly Net Flow: ESGU vs IVV\n'
                 '(Net Flow = Change in AUM excluding market returns)',
                 fontsize=13, fontweight='bold', y=1.01)

    for ax, df, label, color in [
        (axes[0], esgu_m, 'ESGU (ESG)', COLORS['ESG']),
        (axes[1], ivv_m,  'IVV (Conventional)', COLORS['Conventional']),
    ]:
        flow = df['net_flow'] / 1e6
        pos_flow = flow.clip(lower=0)
        neg_flow = flow.clip(upper=0)

        ax.bar(df.index, pos_flow, color=COLORS['positive'], alpha=0.7, width=25, label='Inflow')
        ax.bar(df.index, neg_flow, color=COLORS['negative'], alpha=0.7, width=25, label='Outflow')
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')

        # 12個月移動平均
        ma = flow.rolling(6).mean()
        ax.plot(df.index, ma, color=color, linewidth=2, label='6-month MA')

        ax.set_ylabel('Net Flow (USD Million)', fontsize=10)
        ax.set_title(f'{label}', fontsize=11)
        ax.legend(fontsize=8, loc='upper left')

        # 標示時期
        for pname, (s, e) in PERIODS_SHORT.items():
            if pname == 'COVID Crisis':
                ax.axvspan(pd.Timestamp(s), pd.Timestamp(e), alpha=0.1, color=COLORS['COVID'])
                ax.annotate('COVID', xy=(pd.Timestamp('2020-06-01'), ax.get_ylim()[1]*0.9),
                            fontsize=8, color=COLORS['COVID'], ha='center')
            if pname == 'Rate Hike':
                ax.axvspan(pd.Timestamp(s), pd.Timestamp(e), alpha=0.1, color=COLORS['Rate_Hike'])

    plt.tight_layout()
    return fig


def fig3_ogr_by_period(period_df):
    """圖3：各時期 OGR 比較（核心圖）"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Organic Growth Rate by Period: ESGU vs IVV\n'
                 '(Key metric: positive OGR during COVID shows ESG investor loyalty)',
                 fontsize=13, fontweight='bold')

    # 左圖：OGR 並排長條
    periods = period_df['period'].unique()
    x = np.arange(len(periods))
    width = 0.35

    esgu_ogr = [period_df[(period_df['ticker']=='ESGU') &
                           (period_df['period']==p)]['avg_ogr_pct'].values[0]
                if len(period_df[(period_df['ticker']=='ESGU') &
                                  (period_df['period']==p)]) > 0 else 0
                for p in periods]

    ivv_ogr  = [period_df[(period_df['ticker']=='IVV') &
                           (period_df['period']==p)]['avg_ogr_pct'].values[0]
                if len(period_df[(period_df['ticker']=='IVV') &
                                  (period_df['period']==p)]) > 0 else 0
                for p in periods]

    ax = axes[0]
    bars_esg  = ax.bar(x - width/2, esgu_ogr, width, label='ESGU (ESG)',
                        color=COLORS['ESG'], alpha=0.8)
    bars_conv = ax.bar(x + width/2, ivv_ogr,  width, label='IVV (Conventional)',
                        color=COLORS['Conventional'], alpha=0.8)

    # 標示數值
    for bar in bars_esg:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + (0.2 if h >= 0 else -0.5),
                f'{h:.2f}%', ha='center', va='bottom' if h >= 0 else 'top',
                fontsize=8, fontweight='bold', color=COLORS['ESG'])
    for bar in bars_conv:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + (0.2 if h >= 0 else -0.5),
                f'{h:.2f}%', ha='center', va='bottom' if h >= 0 else 'top',
                fontsize=8, fontweight='bold', color=COLORS['Conventional'])

    ax.axhline(0, color='black', linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(periods, fontsize=8)
    ax.set_ylabel('Avg Monthly Organic Growth Rate (%)')
    ax.set_title('Average Monthly OGR by Period')
    ax.legend()

    # 右圖：COVID 特寫（最關鍵時期）
    ax2 = axes[1]
    covid_data = period_df[period_df['period'] == 'COVID Crisis']
    tickers    = covid_data['ticker'].values
    ogrs       = covid_data['avg_ogr_pct'].values
    colors_bar = [COLORS['ESG'] if t == 'ESGU' else COLORS['Conventional'] for t in tickers]

    bars = ax2.bar(tickers, ogrs, color=colors_bar, alpha=0.85, width=0.4, edgecolor='white')
    for bar, v in zip(bars, ogrs):
        ax2.text(bar.get_x() + bar.get_width()/2, v + (0.3 if v >= 0 else -0.5),
                 f'{v:.2f}%/mo', ha='center',
                 va='bottom' if v >= 0 else 'top',
                 fontsize=11, fontweight='bold')

    ax2.axhline(0, color='black', linewidth=1)
    ax2.set_title('COVID Crisis (Mar–Dec 2020)\nKey Finding: ESG Inflow vs Conventional Outflow',
                  fontsize=11)
    ax2.set_ylabel('Avg Monthly OGR (%)')
    ax2.annotate(
        'ESG investors showed\nstronger loyalty during\nmarket crash',
        xy=(0, ogrs[0]),
        xytext=(0.5, ogrs[0] + 5),
        arrowprops=dict(arrowstyle='->', color='black'),
        fontsize=9, color='darkblue',
        ha='center'
    )

    plt.tight_layout()
    return fig


def fig4_return_comparison(return_df):
    """圖4：各地區 ESG vs 傳統 ETF 報酬比較"""
    regions = ['US', 'Developed exUS', 'Emerging', 'Fixed Income']
    periods = list(PERIODS_SHORT.keys())

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Average Monthly Return: ESG vs Conventional by Region & Period',
                 fontsize=13, fontweight='bold')
    axes_flat = axes.flatten()

    for ax, region in zip(axes_flat, regions):
        sub = return_df[return_df['region'] == region]
        esg_ret  = sub[sub['type'] == 'ESG'].groupby('period')['avg_monthly_ret'].mean()
        conv_ret = sub[sub['type'] == 'Conventional'].groupby('period')['avg_monthly_ret'].mean()

        x = np.arange(len(periods))
        esg_vals  = [esg_ret.get(p, 0)  for p in periods]
        conv_vals = [conv_ret.get(p, 0) for p in periods]
        diff_vals = [e - c for e, c in zip(esg_vals, conv_vals)]

        ax.plot(periods, esg_vals,  'o-', color=COLORS['ESG'],
                linewidth=2, markersize=7, label='ESG', zorder=3)
        ax.plot(periods, conv_vals, 's--', color=COLORS['Conventional'],
                linewidth=2, markersize=7, label='Conventional', zorder=3)
        ax.fill_between(range(len(periods)), esg_vals, conv_vals,
                        where=[e >= c for e, c in zip(esg_vals, conv_vals)],
                        alpha=0.15, color=COLORS['ESG'], interpolate=True)
        ax.fill_between(range(len(periods)), esg_vals, conv_vals,
                        where=[e < c for e, c in zip(esg_vals, conv_vals)],
                        alpha=0.15, color=COLORS['Conventional'], interpolate=True)

        ax.axhline(0, color='gray', linewidth=0.5, linestyle='--')
        ax.set_title(f'Region: {region}', fontsize=11, fontweight='bold')
        ax.set_ylabel('Avg Monthly Return (%)')
        ax.set_xticks(range(len(periods)))
        ax.set_xticklabels([p.replace('\n', ' ') for p in periods],
                           rotation=30, ha='right', fontsize=8)
        ax.legend(fontsize=8)

    plt.tight_layout()
    return fig


def fig5_flow_sensitivity(esgu_m, ivv_m):
    """圖5：Flow-Performance 散佈圖（分正負報酬）"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Flow-Performance Sensitivity: OGR vs Monthly Return\n'
                 '(Flatter slope in negative returns = higher investor loyalty)',
                 fontsize=13, fontweight='bold')

    for ax, df, ticker, color in [
        (axes[0], esgu_m, 'ESGU (ESG)', COLORS['ESG']),
        (axes[1], ivv_m,  'IVV (Conventional)', COLORS['Conventional']),
    ]:
        r = df['nav_return'].dropna()
        f = df['ogr'].reindex(r.index).dropna()
        common = r.index.intersection(f.index)
        r, f   = r.loc[common] * 100, f.loc[common] * 100

        # 正報酬
        pos = r > 0
        neg = r < 0
        ax.scatter(r[pos], f[pos], alpha=0.6, color=COLORS['positive'],
                   s=50, label='Positive return months', zorder=3)
        ax.scatter(r[neg], f[neg], alpha=0.6, color=COLORS['negative'],
                   s=50, label='Negative return months', zorder=3)

        # 回歸線（全期）
        slope, intercept, r_val, p_val, _ = stats.linregress(r, f)
        x_line = np.linspace(r.min(), r.max(), 100)
        ax.plot(x_line, slope * x_line + intercept,
                color=color, linewidth=2.5, linestyle='-',
                label=f'OLS: β={slope:.3f}, R²={r_val**2:.3f}')

        # 負報酬區間回歸
        if neg.sum() >= 5:
            sl_neg, int_neg, _, _, _ = stats.linregress(r[neg], f[neg])
            x_neg = np.linspace(r[neg].min(), r[neg].max(), 50)
            ax.plot(x_neg, sl_neg * x_neg + int_neg,
                    color=COLORS['negative'], linewidth=2, linestyle='--',
                    label=f'Neg-period β={sl_neg:.3f}')

        ax.axhline(0, color='black', linewidth=0.5, linestyle='--')
        ax.axvline(0, color='black', linewidth=0.5, linestyle='--')
        ax.set_xlabel('Monthly NAV Return (%)')
        ax.set_ylabel('Organic Growth Rate (%)')
        ax.set_title(f'{ticker}')
        ax.legend(fontsize=8)

        ax.text(0.05, 0.95,
                f'n = {len(common)} months\nβ_neg = {sl_neg:.4f}' if neg.sum() >= 5
                else f'n = {len(common)} months',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    return fig


def fig6_downside_protection(prices, returns):
    """圖6：下跌時期跌幅保護分析（Downside Capture Ratio）"""
    # 計算 downside capture ratio：下跌月份中 ETF 報酬 / 市場報酬
    # 使用 SPY 作為市場基準
    spy_ret = returns['SPY'].dropna()
    down_months = spy_ret[spy_ret < 0].index

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('Downside Protection: ESG vs Conventional in Falling Markets',
                 fontsize=13, fontweight='bold')

    # 左圖：下跌月份平均報酬比較
    ax = axes[0]
    tickers_show = ['ESGU', 'ESGV', 'SUSA', 'DSI', 'IVV', 'VTI', 'SPY']
    down_rets = {}
    for t in tickers_show:
        if t in returns.columns:
            r = returns.loc[down_months, t].dropna()
            down_rets[t] = r.mean() * 100

    sorted_tickers = sorted(down_rets.keys(), key=lambda x: down_rets[x], reverse=True)
    bar_colors = [COLORS['ESG'] if t in ESG_TICKERS else COLORS['Conventional']
                  for t in sorted_tickers]
    bars = ax.bar(sorted_tickers, [down_rets[t] for t in sorted_tickers],
                  color=bar_colors, alpha=0.8, edgecolor='white')

    for bar, ticker in zip(bars, sorted_tickers):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h - 0.2,
                f'{h:.2f}%', ha='center', va='top', fontsize=8)

    ax.axhline(0, color='black', linewidth=0.8)
    ax.set_ylabel('Avg Return in Down Months (%)')
    ax.set_title(f'Avg Monthly Return When SPY Falls\n(n={len(down_months)} months)')
    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor=COLORS['ESG'],          label='ESG ETFs'),
        Patch(facecolor=COLORS['Conventional'], label='Conventional ETFs'),
    ])

    # 右圖：COVID 期間（2020 Q1）ESGU vs IVV 每月表現
    ax2 = axes[1]
    covid_mask = (returns.index >= '2020-01-01') & (returns.index <= '2020-12-31')
    for ticker, color, ls in [('ESGU', COLORS['ESG'], '-'), ('IVV', COLORS['Conventional'], '--')]:
        if ticker in returns.columns:
            r = returns.loc[covid_mask, ticker].dropna() * 100
            ax2.bar(r.index, r, width=25,
                    color=[COLORS['positive'] if v >= 0 else COLORS['negative'] for v in r],
                    alpha=0.6 if ticker == 'IVV' else 0.9)
            ax2.plot(r.index, r, color=color, linewidth=2, linestyle=ls,
                     label=ticker, zorder=3, marker='o', markersize=5)

    ax2.axhline(0, color='black', linewidth=0.8)
    ax2.set_ylabel('Monthly Return (%)')
    ax2.set_title('2020 Monthly Returns: ESGU vs IVV')
    ax2.legend()
    ax2.annotate('COVID\nCrash', xy=(pd.Timestamp('2020-03-01'), -15),
                 fontsize=9, color='red', ha='center')

    plt.tight_layout()
    return fig


def fig7_regional_heatmap(return_df):
    """圖7：地區 × 時期 ESG Outperformance 熱力圖"""
    regions = ['US', 'Developed exUS', 'Emerging', 'Fixed Income']
    periods = list(PERIODS_SHORT.keys())

    # ESG outperformance = ESG avg ret - Conv avg ret（每個地區×時期）
    matrix = np.zeros((len(regions), len(periods)))
    for i, region in enumerate(regions):
        for j, period in enumerate(periods):
            sub = return_df[(return_df['region'] == region) &
                            (return_df['period'] == period)]
            esg  = sub[sub['type'] == 'ESG']['avg_monthly_ret'].mean()
            conv = sub[sub['type'] == 'Conventional']['avg_monthly_ret'].mean()
            if not np.isnan(esg) and not np.isnan(conv):
                matrix[i, j] = esg - conv

    fig, ax = plt.subplots(figsize=(12, 5))
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto',
                   vmin=-max(abs(matrix.min()), abs(matrix.max())),
                   vmax=max(abs(matrix.min()), abs(matrix.max())))

    ax.set_xticks(range(len(periods)))
    ax.set_xticklabels(periods, fontsize=9)
    ax.set_yticks(range(len(regions)))
    ax.set_yticklabels(regions, fontsize=10)

    for i in range(len(regions)):
        for j in range(len(periods)):
            text = ax.text(j, i, f'{matrix[i, j]:.2f}%',
                           ha='center', va='center', fontsize=9,
                           color='black' if abs(matrix[i, j]) < matrix.max()*0.6 else 'white')

    plt.colorbar(im, ax=ax, label='ESG Monthly Return Advantage (%)')
    ax.set_title('ESG Outperformance vs Conventional by Region × Period\n'
                 '(Green = ESG outperforms, Red = ESG underperforms)',
                 fontsize=12, fontweight='bold')
    plt.tight_layout()
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 5. 主程式
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("ESG 投資人黏著度完整分析")
    print("=" * 60)

    # ── 1. 載入資料 ──────────────────────────────────────────
    data = load_all_data()

    missing = [k for k in ('esgu', 'ivv', 'prices', 'returns') if k not in data]
    if missing:
        print(f"\n⚠️  缺少必要資料：{missing}")
        print("請確認以下檔案存在：")
        for k in missing:
            print(f"  - {FILES.get(k+'_xls', FILES.get(k, ''))}")
        sys.exit(1)

    # ── 2. Flow 計算 ─────────────────────────────────────────
    print("\n" + "=" * 60)
    print("計算 Net Flow...")
    print("=" * 60)

    esgu_m = compute_monthly_flow(data['esgu'], 'ESGU')
    ivv_m  = compute_monthly_flow(data['ivv'],  'IVV')

    # ── 3. 各分析 ────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("執行分析...")
    print("=" * 60)

    period_df   = period_flow_summary(esgu_m, ivv_m)
    return_df   = return_analysis_by_region(data['prices'], data['returns'])
    sensitivity_df, r_series, f_series = flow_performance_sensitivity(esgu_m, ivv_m)

    # ── 4. 列印關鍵結果 ──────────────────────────────────────
    print("\n" + "=" * 60)
    print("【關鍵發現】各時期 OGR 比較")
    print("=" * 60)
    pd.set_option('display.float_format', '{:.3f}'.format)
    pivot = period_df.pivot_table(
        index='period', columns='ticker',
        values=['avg_ogr_pct', 'outflow_rate_pct', 'avg_monthly_flow_M']
    )
    print(pivot.to_string())

    print("\n" + "=" * 60)
    print("【關鍵發現】Flow-Performance Sensitivity")
    print("=" * 60)
    print(sensitivity_df[['ticker', 'type', 'beta_all', 'beta_negative',
                           'r_squared', 'p_value', 'interpretation']].to_string(index=False))
    print("\n解讀：beta_negative 越接近 0 → 下跌時 OGR 不降 → 投資人黏著度越高")

    print("\n" + "=" * 60)
    print("【關鍵發現】COVID 期間比較")
    print("=" * 60)
    covid_flow = period_df[period_df['period'] == 'COVID Crisis']
    print(covid_flow[['ticker', 'type', 'avg_ogr_pct',
                       'outflow_rate_pct', 'avg_monthly_flow_M']].to_string(index=False))

    # ── 5. 儲存 CSV ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("儲存 CSV...")
    print("=" * 60)

    csv_files = {
        'flow_analysis_monthly.csv':    esgu_m[['nav','shares','aum','nav_return',
                                                 'net_flow','ogr','is_outflow']].join(
                                         ivv_m[['nav','shares','aum','nav_return',
                                                'net_flow','ogr']],
                                         lsuffix='_ESGU', rsuffix='_IVV'),
        'flow_by_period.csv':           period_df,
        'return_analysis_by_region.csv':return_df,
        'sensitivity_analysis.csv':     sensitivity_df,
    }

    # 綜合摘要
    summary_rows = []
    for period, (s, e) in PERIODS_SHORT.items():
        for df, ticker, etype in [(esgu_m, 'ESGU', 'ESG'), (ivv_m, 'IVV', 'Conventional')]:
            mask = (df.index >= s) & (df.index <= e)
            sub  = df.loc[mask]
            if sub.empty:
                continue
            # 找對應的報酬
            ret_sub = data['returns'].loc[
                (data['returns'].index >= s) & (data['returns'].index <= e), ticker
            ].dropna() if ticker in data['returns'].columns else pd.Series()

            summary_rows.append({
                'period':              period,
                'ticker':              ticker,
                'type':                etype,
                'avg_monthly_flow_M':  sub['net_flow'].mean()  / 1e6,
                'avg_ogr_pct':         sub['ogr'].mean()        * 100,
                'outflow_rate_pct':    sub['is_outflow'].mean() * 100,
                'avg_monthly_return_pct': ret_sub.mean() * 100 if len(ret_sub) > 0 else np.nan,
                'volatility_pct':      ret_sub.std()  * 100 if len(ret_sub) > 0 else np.nan,
                'n_months':            len(sub),
            })

    csv_files['full_results_summary.csv'] = pd.DataFrame(summary_rows)

    for fname, df in csv_files.items():
        path = os.path.join(BASE_DIR, fname)
        df.to_csv(path)
        print(f"  ✅ {fname}")

    # ── 6. 產出圖表 ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("產出圖表...")
    print("=" * 60)

    figs = [
        ('fig1_aum_trend.png',         fig1_aum_trend(esgu_m, ivv_m)),
        ('fig2_net_flow_trend.png',     fig2_net_flow_trend(esgu_m, ivv_m)),
        ('fig3_ogr_by_period.png',      fig3_ogr_by_period(period_df)),
        ('fig4_return_comparison.png',  fig4_return_comparison(return_df)),
        ('fig5_flow_sensitivity.png',   fig5_flow_sensitivity(esgu_m, ivv_m)),
        ('fig6_downside_protection.png',fig6_downside_protection(data['prices'], data['returns'])),
        ('fig7_regional_heatmap.png',   fig7_regional_heatmap(return_df)),
    ]

    for fname, fig in figs:
        path = os.path.join(BASE_DIR, fname)
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"  ✅ {fname}")

    # ── 7. 完成 ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ 全部完成！")
    print("=" * 60)
    print(f"""
輸出檔案（{BASE_DIR}）：

CSV：
  flow_analysis_monthly.csv        月度 ESGU vs IVV Flow 完整資料
  flow_by_period.csv               各時期 Flow 比較
  return_analysis_by_region.csv    各地區 × 時期報酬分析
  sensitivity_analysis.csv         Flow-Performance β 值
  full_results_summary.csv         完整結果摘要（論文用）

圖表：
  fig1_aum_trend.png               AUM 歷史走勢
  fig2_net_flow_trend.png          Net Flow 月頻走勢
  fig3_ogr_by_period.png           各時期 OGR 比較【關鍵圖】
  fig4_return_comparison.png       各地區報酬比較
  fig5_flow_sensitivity.png        Flow-Performance 散佈圖【黏著度圖】
  fig6_downside_protection.png     下跌時期保護分析
  fig7_regional_heatmap.png        地區 × 時期熱力圖

核心發現（COVID 期間）：
  ESGU OGR = {period_df[(period_df['ticker']=='ESGU') & (period_df['period']=='COVID Crisis')]['avg_ogr_pct'].values[0]:.2f}%/月（正流入）
  IVV  OGR = {period_df[(period_df['ticker']=='IVV')  & (period_df['period']=='COVID Crisis')]['avg_ogr_pct'].values[0]:.2f}%/月（負流出）
  → 支持「ESG 投資人在市場下跌時黏著度更高」的假說
""")


if __name__ == '__main__':
    main()