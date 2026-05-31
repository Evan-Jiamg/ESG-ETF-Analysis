"""
Core analysis functions: monthly flow computation, period summaries,
flow-performance regression, and NAV-based return statistics.
"""

import numpy as np
import pandas as pd
from scipy import stats

from ETF_Config import PERIODS_SHORT, REGION_MAP, REGIONS, get_fund_type


# ─────────────────────────────────────────────────────────────────────────────
# Monthly Flow
# ─────────────────────────────────────────────────────────────────────────────

def compute_monthly_flow(daily_df):
    """
    Resample daily nav/shares to month-end and compute:
      net_flow = AUM_t - AUM_{t-1} × (1 + NAV_return_t)
      ogr      = net_flow / AUM_{t-1}   (Organic Growth Rate)

    Using NAV return (not market price) excludes premium/discount noise.
    """
    m = daily_df.resample('ME').last().copy()
    m['nav_return'] = m['nav'].pct_change()
    m['net_flow']   = m['aum'] - m['aum'].shift(1) * (1 + m['nav_return'])
    m['ogr']        = m['net_flow'] / m['aum'].shift(1)
    m['is_outflow'] = m['net_flow'] < 0
    return m


def compute_all_monthly_flows(all_data):
    """
    Apply compute_monthly_flow to every ETF in all_data.
    Returns dict of {ticker: monthly_DataFrame} for ETFs with >= 12 valid months.
    """
    print('=' * 60)
    print('Computing monthly flows...')
    print('=' * 60)

    flows = {}
    for ticker, df in all_data.items():
        m = compute_monthly_flow(df).dropna(subset=['ogr'])
        if len(m) < 12:
            print(f'  {ticker}: skipped (< 12 months after OGR calculation)')
            continue
        flows[ticker] = m
        print(f'  {ticker}: {len(m)} months  avg OGR={m["ogr"].mean()*100:.3f}%/mo'
              f'  outflow months={m["is_outflow"].sum()}')

    print(f'\nValid ETFs: {len(flows)}\n')
    return flows


# ─────────────────────────────────────────────────────────────────────────────
# Period-level Summaries
# ─────────────────────────────────────────────────────────────────────────────

def period_flow_summary(monthly_flows):
    """
    Per-period, per-ticker flow statistics.
    Returns a long-format DataFrame with columns:
      period, ticker, region, avg_monthly_flow_M, total_flow_M,
      avg_ogr_pct, outflow_months, total_months, outflow_rate_pct
    """
    rows = []
    for period_label, (start, end) in PERIODS_SHORT.items():
        for ticker, df in monthly_flows.items():
            sub = df.loc[(df.index >= start) & (df.index <= end)]
            if sub.empty:
                continue
            rows.append({
                'period':             period_label,
                'ticker':             ticker,
                'type':               get_fund_type(ticker),
                'region':             REGION_MAP.get(ticker, 'Unknown'),
                'avg_monthly_flow_M': sub['net_flow'].mean()   / 1e6,
                'total_flow_M':       sub['net_flow'].sum()    / 1e6,
                'avg_ogr_pct':        sub['ogr'].mean()        * 100,
                'outflow_months':     int(sub['is_outflow'].sum()),
                'total_months':       len(sub),
                'outflow_rate_pct':   sub['is_outflow'].mean() * 100,
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Flow-Performance Sensitivity Regression
# ─────────────────────────────────────────────────────────────────────────────

def flow_performance_sensitivity(monthly_flows):
    """
    OGR ~ NAV_return regression for each ETF, overall and split by return sign.

    Interpretation:
      beta_negative close to 0 → investors don't redeem during downturns → high loyalty
      beta_negative strongly positive → OGR falls sharply when returns are negative → low loyalty
    """
    rows = []
    for ticker, df in monthly_flows.items():
        r   = df['nav_return'].dropna()
        ogr = df['ogr'].reindex(r.index).dropna()
        idx = r.index.intersection(ogr.index)
        r, ogr = r.loc[idx], ogr.loc[idx]

        if len(idx) < 10:
            continue

        slope, _, rval, pval, _ = stats.linregress(r, ogr)

        neg_mask = r < 0
        slope_neg = (stats.linregress(r[neg_mask], ogr[neg_mask]).slope
                     if neg_mask.sum() >= 5 else np.nan)

        pos_mask = r > 0
        slope_pos = (stats.linregress(r[pos_mask], ogr[pos_mask]).slope
                     if pos_mask.sum() >= 5 else np.nan)

        rows.append({
            'ticker':        ticker,
            'type':          get_fund_type(ticker),
            'region':        REGION_MAP.get(ticker, 'Unknown'),
            'n_months':      len(idx),
            'beta_all':      round(slope,     3),
            'beta_negative': round(slope_neg, 3) if not np.isnan(slope_neg) else np.nan,
            'beta_positive': round(slope_pos, 3) if not np.isnan(slope_pos) else np.nan,
            'r_squared':     round(rval ** 2, 4),
            'p_value':       round(pval,      4),
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# NAV-based Return Analysis
# ─────────────────────────────────────────────────────────────────────────────

def nav_return_by_region(monthly_flows):
    """
    Per-period, per-ticker NAV return statistics (replaces the price-CSV-based
    return_analysis_by_region from the original ETF.py).
    """
    rows = []
    for period_label, (start, end) in PERIODS_SHORT.items():
        for ticker, df in monthly_flows.items():
            sub = df.loc[(df.index >= start) & (df.index <= end), 'nav_return'].dropna()
            if len(sub) < 2:
                continue
            rows.append({
                'period':          period_label,
                'ticker':          ticker,
                'type':            get_fund_type(ticker),
                'region':          REGION_MAP.get(ticker, 'Unknown'),
                'avg_monthly_ret': sub.mean()  * 100,
                'annual_ret':      ((1 + sub.mean()) ** 12 - 1) * 100,
                'volatility':      sub.std()   * 100,
                'sharpe_proxy':    sub.mean() / sub.std() if sub.std() > 0 else np.nan,
                'neg_months':      int((sub < 0).sum()),
                'neg_month_pct':   (sub < 0).mean() * 100,
                'max_monthly_dd':  sub.min()   * 100,
                'n_months':        len(sub),
            })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# CSV export helpers
# ─────────────────────────────────────────────────────────────────────────────

def build_monthly_long(monthly_flows):
    """Long-format monthly flow table (one row per ticker × month)."""
    frames = []
    for ticker, df in monthly_flows.items():
        tmp = df[['nav', 'shares', 'aum', 'nav_return', 'net_flow', 'ogr', 'is_outflow']].copy()
        tmp['ticker'] = ticker
        tmp['type']   = get_fund_type(ticker)
        tmp['region'] = REGION_MAP.get(ticker, 'Unknown')
        frames.append(tmp)
    return pd.concat(frames).reset_index().rename(columns={'index': 'date'})


def build_monthly_nav_wide(monthly_flows):
    """Wide-format monthly NAV prices: rows = date, columns = ticker."""
    return pd.DataFrame(
        {t: df['nav'] for t, df in monthly_flows.items()}
    ).sort_index()


def build_monthly_returns_wide(monthly_flows):
    """Wide-format monthly NAV returns: rows = date, columns = ticker."""
    return pd.DataFrame(
        {t: df['nav_return'] for t, df in monthly_flows.items()}
    ).sort_index()


def build_fund_info(all_data, monthly_flows):
    """One row per ETF with metadata derived from the loaded XLS data."""
    rows = []
    for ticker in sorted(all_data):
        daily   = all_data[ticker]
        monthly = monthly_flows.get(ticker)
        rows.append({
            'ticker':        ticker,
            'type':          get_fund_type(ticker),
            'region':        REGION_MAP.get(ticker, 'Unknown'),
            'first_date':    daily.index[0].date(),
            'last_date':     daily.index[-1].date(),
            'n_days':        len(daily),
            'n_months':      len(monthly) if monthly is not None else 0,
            'avg_nav':       round(daily['nav'].mean(), 4),
            'latest_nav':    round(daily['nav'].iloc[-1], 4),
            'latest_aum_B':  round(daily['aum'].iloc[-1] / 1e9, 4),
            'peak_aum_B':    round(daily['aum'].max() / 1e9, 4),
        })
    return pd.DataFrame(rows)


def build_summary_stats(period_df, return_df):
    """
    Comprehensive per-period × per-ticker summary combining flow and return metrics.
    Equivalent to esg_summary_stats.csv from Previous_Analysis.
    """
    ret_cols = ['period', 'ticker', 'avg_monthly_ret', 'annual_ret',
                'volatility', 'sharpe_proxy', 'neg_months', 'neg_month_pct', 'max_monthly_dd']
    return period_df.merge(
        return_df[ret_cols], on=['period', 'ticker'], how='left'
    )


def build_full_results_summary(period_df, sensitivity_df):
    """
    Full merged summary: per-period flow metrics joined with sensitivity betas.
    Equivalent to full_results_summary.csv from Previous_Analysis.
    """
    sens_cols = ['ticker', 'type', 'beta_all', 'beta_negative', 'beta_positive', 'r_squared', 'p_value']
    return period_df.merge(
        sensitivity_df[sens_cols], on=['ticker', 'type'], how='left'
    )


def compare_esg_vs_conventional(sensitivity_df):
    """
    Per-region summary comparing ESG average beta_negative vs. Conventional beta_negative.
    Used for fig8 and the esg_vs_conventional_summary.csv output.
    """
    rows = []
    for region in REGIONS:
        esg  = sensitivity_df[(sensitivity_df['type'] == 'ESG') &
                               (sensitivity_df['region'] == region)]['beta_negative'].dropna()
        conv = sensitivity_df[(sensitivity_df['type'] == 'Conventional') &
                               (sensitivity_df['region'] == region)]['beta_negative'].dropna()
        rows.append({
            'region':              region,
            'esg_n':               len(esg),
            'esg_beta_neg_mean':   round(esg.mean(),   3) if len(esg)  > 0 else np.nan,
            'esg_beta_neg_median': round(esg.median(), 3) if len(esg)  > 0 else np.nan,
            'esg_pct_below_zero':  round((esg < 0).mean(), 3) if len(esg) > 0 else np.nan,
            'conv_n':              len(conv),
            'conv_beta_neg':       round(conv.iloc[0], 3) if len(conv) == 1 else (
                                   round(conv.mean(), 3)  if len(conv)  > 1 else np.nan),
            'difference':          round(esg.mean() - conv.mean(), 3)
                                   if len(esg) > 0 and len(conv) > 0 else np.nan,
        })
    return pd.DataFrame(rows)
