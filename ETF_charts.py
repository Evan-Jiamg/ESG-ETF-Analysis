"""
Publication-quality figures for academic paper.
Each function returns a list of (filename_stem, fig) tuples — one entry per file.

Design principles:
  - Times New Roman, 10 pt base / 9 pt axis labels / 8 pt ticks & legend
  - Data lines 1.5 pt; reference/zero lines 0.8 pt
  - Blue-family colors + distinct line styles for B&W reproducibility
  - Bar charts use hatching for B&W print
  - No text annotations overlaid on data
  - Single-panel figures: one chart per output file
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from ETF_Config import (
    PERIODS_SHORT, REGION_MAP, REGIONS,
    REGION_STYLES, TICKER_STYLES, EVENT_COLORS,
    CONVENTIONAL_TICKERS, CONV_STYLE, REGION_BENCHMARK, get_fund_type,
)

# ── Constants ─────────────────────────────────────────────────────────────────
_FW  = 6.5   # standard figure width (inches)
_LW  = 1.5   # data line width
_RW  = 0.8   # reference / zero-line width
_MS  = 4     # marker size

_PERIOD_LABELS = list(PERIODS_SHORT.keys())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _shade_events(ax):
    for pname, (s, e) in PERIODS_SHORT.items():
        if pname == 'COVID Crisis':
            ax.axvspan(pd.Timestamp(s), pd.Timestamp(e),
                       alpha=0.10, color=EVENT_COLORS['COVID'], zorder=0)
        elif pname == 'Rate Hike':
            ax.axvspan(pd.Timestamp(s), pd.Timestamp(e),
                       alpha=0.08, color=EVENT_COLORS['Rate_Hike'], zorder=0)


def _tickers_in(monthly_flows, region, fund_type=None):
    """Return sorted tickers for a region, optionally filtered by fund_type."""
    return [t for t in sorted(monthly_flows)
            if REGION_MAP.get(t) == region
            and (fund_type is None or get_fund_type(t) == fund_type)]


def _plot_conv_line(ax, monthly_flows, region, col='nav_return', scale=1.0, period_labels=None):
    """
    Overlay the conventional benchmark for a region as a distinct orange line.
    For time-series charts: col is the DataFrame column name.
    For period charts: period_labels must be provided and col averaged per period.
    """
    conv_ticker = next(
        (t for t in CONVENTIONAL_TICKERS if CONVENTIONAL_TICKERS[t] == region
         and t in monthly_flows), None)
    if conv_ticker is None:
        return

    df = monthly_flows[conv_ticker]

    if period_labels is None:
        # Time-series mode
        series = df[col] * scale if col in df.columns else df['nav'] * scale
        ax.plot(df.index, series,
                color=CONV_STYLE['color'],
                linestyle=CONV_STYLE['linestyle'],
                linewidth=CONV_STYLE['linewidth'],
                marker=None, alpha=0.90,
                label=f'{conv_ticker} (Conv.)', zorder=4)
    else:
        # Period-axis mode: compute per-period average
        vals = []
        for p in period_labels:
            s, e = PERIODS_SHORT[p]
            sub  = df.loc[(df.index >= s) & (df.index <= e), col].dropna()
            vals.append(sub.mean() * scale if len(sub) > 0 else np.nan)
        ax.plot(range(len(period_labels)), vals,
                color=CONV_STYLE['color'],
                linestyle=CONV_STYLE['linestyle'],
                linewidth=CONV_STYLE['linewidth'],
                marker=CONV_STYLE['marker'],
                markersize=_MS + 1, alpha=0.90,
                label=f'{conv_ticker} (Conv.)', zorder=4)


def _bottom_legend(ax, handles, ncol=None):
    """Place legend below the axes, centred, so it never overlaps data."""
    if ncol is None:
        ncol = min(len(handles), 4)
    ax.legend(handles=handles, fontsize=7,
              loc='upper center', bbox_to_anchor=(0.5, -0.18),
              ncol=ncol, framealpha=0.9,
              handlelength=1.8, handletextpad=0.4, columnspacing=1.0)


def _line_legend(ax, tickers, conv_ticker=None):
    handles = [
        Line2D([0], [0],
               color=f'C{i}',
               linestyle=TICKER_STYLES[i % len(TICKER_STYLES)]['linestyle'],
               linewidth=_LW, label=t)
        for i, t in enumerate(tickers)
    ]
    if conv_ticker:
        handles.append(
            Line2D([0], [0], color=CONV_STYLE['color'],
                   linestyle=CONV_STYLE['linestyle'],
                   linewidth=CONV_STYLE['linewidth'],
                   label=f'{conv_ticker} (Conv.)')
        )
    _bottom_legend(ax, handles, ncol=min(len(handles), 4))


def _region_legend(ax):
    handles = [
        Patch(facecolor=REGION_STYLES[r]['color'],
              hatch=REGION_STYLES[r]['hatch'],
              label=r, edgecolor='#333333', linewidth=0.5)
        for r in REGIONS if r in REGION_STYLES
    ]
    _bottom_legend(ax, handles, ncol=min(len(handles), 3))


def _set_period_xticks(ax, rotation=30):
    ax.set_xticks(range(len(_PERIOD_LABELS)))
    ax.set_xticklabels(_PERIOD_LABELS, rotation=rotation, ha='right', fontsize=8)


def _zero_line(ax, axis='h'):
    if axis == 'h':
        ax.axhline(0, color='#333333', linewidth=_RW, zorder=1)
    else:
        ax.axvline(0, color='#333333', linewidth=_RW, zorder=1)


def _regions_present(monthly_flows):
    return [r for r in REGIONS if any(REGION_MAP.get(t) == r for t in monthly_flows)]


def _safe_stem(region):
    """Convert region name to a safe filename stem."""
    return region.replace(' ', '_').replace('/', '_')


# Per-region AUM split: ESG dominant / ESG smaller / Conventional benchmark.
# Separating ESG from Conventional avoids scale-mismatch on a single y-axis.
_AUM_SPLIT = {
    'US': {
        'main':         ['ESGU'],
        'secondary':    ['DSI', 'SUSA', 'SUSL', 'USXF', 'LCTD', 'ERET'],
        'conventional': ['IVV'],
    },
    'Developed exUS': {
        'main':         ['DMXF', 'ESGD', 'PABU'],
        'conventional': ['IEFA'],
    },
    'Emerging': {
        'main':         ['ESGE'],
        'secondary':    ['EMXF', 'LDEM'],
        'conventional': ['IEMG'],
    },
    'Fixed Income': {
        'main':         ['EAGG', 'EUSB', 'HYXF', 'SUSB', 'SUSC'],
        'conventional': ['AGG'],
    },
    'Global': {
        'main':         ['CRBN'],
        'conventional': ['ACWI'],
    },
}


def _aum_panel(monthly_flows, tickers, title, is_conventional=False):
    """Draw one AUM trend panel; conventional panels use the orange CONV_STYLE."""
    fig, ax = plt.subplots(figsize=(_FW, 3.0))

    for i, ticker in enumerate(tickers):
        if ticker not in monthly_flows:
            continue
        df = monthly_flows[ticker]
        if is_conventional:
            color, ls, lw = CONV_STYLE['color'], CONV_STYLE['linestyle'], CONV_STYLE['linewidth']
        else:
            style = TICKER_STYLES[i % len(TICKER_STYLES)]
            color, ls, lw = f'C{i}', style['linestyle'], _LW
        ax.plot(df.index, df['aum'] / 1e9,
                color=color, linestyle=ls, linewidth=lw, alpha=0.90, label=ticker)

    _shade_events(ax)
    ax.set_title(title, fontsize=10)
    ax.set_ylabel('AUM (USD Billion)', fontsize=9)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.1f'))

    event_patches = [
        Patch(facecolor=EVENT_COLORS['COVID'],     alpha=0.3, label='COVID Crisis'),
        Patch(facecolor=EVENT_COLORS['Rate_Hike'], alpha=0.3, label='Rate Hike'),
    ]
    if is_conventional:
        line_handles = [
            Line2D([0], [0], color=CONV_STYLE['color'], linestyle=CONV_STYLE['linestyle'],
                   linewidth=CONV_STYLE['linewidth'], label=t)
            for t in tickers if t in monthly_flows
        ]
    else:
        line_handles = [
            Line2D([0], [0], color=f'C{i}',
                   linestyle=TICKER_STYLES[i % len(TICKER_STYLES)]['linestyle'],
                   linewidth=_LW, label=t)
            for i, t in enumerate(tickers) if t in monthly_flows
        ]
    all_handles = event_patches + line_handles
    _bottom_legend(ax, all_handles, ncol=min(len(all_handles), 4))
    plt.tight_layout()
    return fig


# ── fig1 – AUM Trend (ESG and Conventional split into separate files per region) ──

def fig1_aum_trend(monthly_flows):
    results = []
    for region in _regions_present(monthly_flows):
        split = _AUM_SPLIT.get(region, {})

        # ESG main chart
        main_t = [t for t in split.get('main', _tickers_in(monthly_flows, region, 'ESG'))
                  if t in monthly_flows]
        if main_t:
            title = (f'AUM Trend — {main_t[0]} ({region}, ESG), 2019–2025'
                     if len(main_t) == 1
                     else f'AUM Trend — {region} ESG, 2019–2025')
            results.append((f'{_safe_stem(region)}_esg_main',
                            _aum_panel(monthly_flows, main_t, title)))

        # ESG secondary chart (smaller funds)
        sec_t = [t for t in split.get('secondary', []) if t in monthly_flows]
        if sec_t:
            results.append((
                f'{_safe_stem(region)}_esg_secondary',
                _aum_panel(monthly_flows, sec_t,
                           f'AUM Trend — {region} (Smaller ESG Funds), 2019–2025')
            ))

        # Conventional benchmark chart (separate y-axis scale)
        conv_t = [t for t in split.get('conventional', []) if t in monthly_flows]
        if conv_t:
            results.append((
                f'{_safe_stem(region)}_conventional',
                _aum_panel(monthly_flows, conv_t,
                           f'AUM Trend — {conv_t[0]} ({region}, Conventional), 2019–2025',
                           is_conventional=True)
            ))

    return results


# ── fig2 – Net Flow Trend (one file per region, ESG only — Conv scale too different) ──

def fig2_net_flow_trend(monthly_flows):
    results = []
    for region in _regions_present(monthly_flows):
        esg_tickers = _tickers_in(monthly_flows, region, fund_type='ESG')
        fig, ax = plt.subplots(figsize=(_FW, 3.0))

        for i, ticker in enumerate(esg_tickers):
            df    = monthly_flows[ticker]
            style = TICKER_STYLES[i % len(TICKER_STYLES)]
            flow  = (df['net_flow'] / 1e6).rolling(3, min_periods=1).mean()
            ax.plot(df.index, flow,
                    color=f'C{i}', linestyle=style['linestyle'],
                    linewidth=_LW, alpha=0.90, label=ticker)

        # Overlay conventional benchmark (also in million USD)
        _plot_conv_line(ax, monthly_flows, region, col='net_flow', scale=1/1e6)

        conv_t = next((t for t in CONVENTIONAL_TICKERS
                       if CONVENTIONAL_TICKERS[t] == region and t in monthly_flows), None)
        _shade_events(ax)
        _zero_line(ax)
        ax.set_title(f'Monthly Net Flow — {region} (3-Month Rolling Avg, ESG vs Conv.)', fontsize=10)
        ax.set_ylabel('Net Flow (USD Million)', fontsize=9)
        _line_legend(ax, esg_tickers, conv_ticker=conv_t)

        plt.tight_layout()
        results.append((_safe_stem(region), fig))

    return results


# ── fig3 – OGR by Period (ESG lines + Conv reference line) ───────────────────

def fig3_ogr_by_period(period_df):
    results = []
    covid_idx = _PERIOD_LABELS.index('COVID Crisis')

    for region in [r for r in REGIONS if r in period_df['region'].values]:
        sub         = period_df[period_df['region'] == region]
        esg_tickers = sorted(sub[sub['type'] == 'ESG']['ticker'].unique())
        conv_t      = next((t for t in CONVENTIONAL_TICKERS
                            if CONVENTIONAL_TICKERS[t] == region and t in sub['ticker'].values), None)
        fig, ax = plt.subplots(figsize=(_FW, 3.0))

        for i, ticker in enumerate(esg_tickers):
            t_sub = sub[sub['ticker'] == ticker].set_index('period')
            vals  = [t_sub.loc[p, 'avg_ogr_pct'] if p in t_sub.index else np.nan
                     for p in _PERIOD_LABELS]
            style = TICKER_STYLES[i % len(TICKER_STYLES)]
            ax.plot(range(len(_PERIOD_LABELS)), vals,
                    color=f'C{i}', linestyle=style['linestyle'],
                    marker=style['marker'], markersize=_MS,
                    linewidth=_LW, alpha=0.90, label=ticker)

        # Conventional reference line
        if conv_t:
            c_sub = sub[sub['ticker'] == conv_t].set_index('period')
            c_vals = [c_sub.loc[p, 'avg_ogr_pct'] if p in c_sub.index else np.nan
                      for p in _PERIOD_LABELS]
            ax.plot(range(len(_PERIOD_LABELS)), c_vals,
                    color=CONV_STYLE['color'], linestyle=CONV_STYLE['linestyle'],
                    marker=CONV_STYLE['marker'], markersize=_MS + 1,
                    linewidth=CONV_STYLE['linewidth'], alpha=0.90,
                    label=f'{conv_t} (Conv.)', zorder=4)

        ax.axvspan(covid_idx - 0.4, covid_idx + 0.4,
                   alpha=0.10, color=EVENT_COLORS['COVID'], zorder=0)
        _zero_line(ax)
        _set_period_xticks(ax)
        ax.set_title(f'Avg Monthly OGR by Period — {region}  (ESG vs Conv.)', fontsize=10)
        ax.set_ylabel('Avg Monthly OGR (%)', fontsize=9)
        _line_legend(ax, esg_tickers, conv_ticker=conv_t)

        plt.tight_layout()
        results.append((_safe_stem(region), fig))

    return results


# ── fig4 – Return Comparison (ESG lines + Conv reference line) ───────────────

def fig4_return_comparison(return_df):
    results = []
    for region in [r for r in REGIONS if r in return_df['region'].values]:
        sub         = return_df[return_df['region'] == region]
        esg_tickers = sorted(sub[sub['type'] == 'ESG']['ticker'].unique())
        conv_t      = next((t for t in CONVENTIONAL_TICKERS
                            if CONVENTIONAL_TICKERS[t] == region and t in sub['ticker'].values), None)
        fig, ax = plt.subplots(figsize=(_FW, 3.0))

        for i, ticker in enumerate(esg_tickers):
            t_sub = sub[sub['ticker'] == ticker].set_index('period')
            vals  = [t_sub.loc[p, 'avg_monthly_ret'] if p in t_sub.index else np.nan
                     for p in _PERIOD_LABELS]
            style = TICKER_STYLES[i % len(TICKER_STYLES)]
            ax.plot(range(len(_PERIOD_LABELS)), vals,
                    color=f'C{i}', linestyle=style['linestyle'],
                    marker=style['marker'], markersize=_MS,
                    linewidth=_LW, alpha=0.90, label=ticker)

        if conv_t:
            c_sub = sub[sub['ticker'] == conv_t].set_index('period')
            c_vals = [c_sub.loc[p, 'avg_monthly_ret'] if p in c_sub.index else np.nan
                      for p in _PERIOD_LABELS]
            ax.plot(range(len(_PERIOD_LABELS)), c_vals,
                    color=CONV_STYLE['color'], linestyle=CONV_STYLE['linestyle'],
                    marker=CONV_STYLE['marker'], markersize=_MS + 1,
                    linewidth=CONV_STYLE['linewidth'], alpha=0.90,
                    label=f'{conv_t} (Conv.)', zorder=4)

        _zero_line(ax)
        _set_period_xticks(ax)
        ax.set_title(f'Avg Monthly NAV Return by Period — {region}  (ESG vs Conv.)', fontsize=10)
        ax.set_ylabel('Avg Monthly Return (%)', fontsize=9)
        _line_legend(ax, esg_tickers, conv_ticker=conv_t)

        plt.tight_layout()
        results.append((_safe_stem(region), fig))

    return results


# ── fig5 – Flow-Performance Sensitivity (ESG + Conv, two files) ──────────────

def fig5_flow_sensitivity(sensitivity_df, monthly_flows):
    results = []
    df_sorted = sensitivity_df.dropna(subset=['beta_negative']).sort_values('beta_negative')
    n = len(df_sorted)

    # ── 5a: β_neg horizontal bar, ESG blue / Conv orange ──
    fig1, ax1 = plt.subplots(figsize=(_FW, max(3.5, n * 0.28)))

    for i, (_, row) in enumerate(df_sorted.iterrows()):
        is_conv = (row.get('type', 'ESG') == 'Conventional')
        if is_conv:
            color, hatch = CONV_STYLE['color'], CONV_STYLE['hatch']
        else:
            r     = REGION_MAP.get(row['ticker'], '')
            style = REGION_STYLES.get(r, {'color': '#999999', 'hatch': ''})
            color, hatch = style['color'], style['hatch']
        ax1.barh(i, row['beta_negative'],
                 color=color, hatch=hatch,
                 edgecolor='#333333', linewidth=0.6, alpha=0.85, height=0.7)

    _zero_line(ax1, axis='v')
    ax1.set_yticks(range(n))
    ax1.set_yticklabels(df_sorted['ticker'], fontsize=8)
    ax1.set_xlabel(r'$\beta_{neg}$  (OGR sensitivity, each ETF\'s own negative-return months)', fontsize=9)
    ax1.set_title(r'$\beta_{neg}$ by ETF — ESG (blue) vs. Conventional (orange)'
                  '\n' r'Negative months defined by each ETF\'s own NAV return $<$ 0', fontsize=10)

    legend_handles = [
        Patch(facecolor=REGION_STYLES[r]['color'], hatch=REGION_STYLES[r]['hatch'],
              label=f'ESG – {r}', edgecolor='#333333', linewidth=0.5)
        for r in REGIONS if r in REGION_STYLES
    ] + [Patch(facecolor=CONV_STYLE['color'], hatch=CONV_STYLE['hatch'],
               label='Conventional', edgecolor='#333333', linewidth=0.5)]
    _bottom_legend(ax1, legend_handles, ncol=3)

    plt.tight_layout()
    results.append(('beta_negative', fig1))

    # ── 5b: β_neg vs R² scatter ──
    fig2, ax2 = plt.subplots(figsize=(_FW, 3.8))

    for _, row in sensitivity_df.dropna(subset=['beta_negative']).iterrows():
        is_conv = (row.get('type', 'ESG') == 'Conventional')
        if is_conv:
            color  = CONV_STYLE['color']
            marker = CONV_STYLE['marker']
        else:
            r      = REGION_MAP.get(row['ticker'], '')
            style  = REGION_STYLES.get(r, {'color': '#999999', 'marker': 'o'})
            color, marker = style['color'], style['marker']
        ax2.scatter(row['beta_negative'], row['r_squared'],
                    color=color, marker=marker,
                    s=50, alpha=0.85, zorder=3, edgecolors='#333333', linewidths=0.5)

    _zero_line(ax2, axis='v')
    ax2.set_xlabel(r'$\beta_{neg}$  (each ETF\'s own negative-return months)', fontsize=9)
    ax2.set_ylabel(r'$R^{2}$', fontsize=9)
    ax2.set_title(r'Signal Strength: $\beta_{neg}$ vs. $R^{2}$  (ESG vs Conv.)', fontsize=10)

    scatter_legend = [
        Patch(facecolor=REGION_STYLES[r]['color'], label=f'ESG – {r}', edgecolor='#333333', linewidth=0.5)
        for r in REGIONS if r in REGION_STYLES
    ] + [Patch(facecolor=CONV_STYLE['color'], label='Conventional',
               edgecolor='#333333', linewidth=0.5)]
    _bottom_legend(ax2, scatter_legend, ncol=3)

    plt.tight_layout()
    results.append(('beta_scatter', fig2))

    return results


# ── fig6 – Downside Protection (all ETFs, ESG + Conv) ────────────────────────

def fig6_downside_protection(monthly_flows):
    # Define down months per ETF using its region's official benchmark (avoids circular definition)
    down_rets   = {}
    n_by_region = {}
    for ticker, df in monthly_flows.items():
        region = REGION_MAP.get(ticker, '')
        bm     = REGION_BENCHMARK.get(region)
        if not bm or bm not in monthly_flows:
            continue
        bm_ret   = monthly_flows[bm]['nav_return'].dropna()
        down_idx = bm_ret[bm_ret < 0].index
        n_by_region[region] = len(down_idx)
        r = df.loc[df.index.isin(down_idx), 'nav_return'].dropna()
        if len(r) >= 3:
            down_rets[ticker] = r.mean() * 100

    # Build subtitle showing n per region
    n_note = '  |  '.join(
        f'{REGION_BENCHMARK[reg]} n={n}' for reg, n in sorted(n_by_region.items())
    )

    sorted_t = sorted(down_rets, key=lambda x: down_rets[x], reverse=True)
    fig, ax  = plt.subplots(figsize=(_FW, 3.8))

    for i, ticker in enumerate(sorted_t):
        is_conv = (get_fund_type(ticker) == 'Conventional')
        if is_conv:
            color, hatch = CONV_STYLE['color'], CONV_STYLE['hatch']
        else:
            r     = REGION_MAP.get(ticker, '')
            style = REGION_STYLES.get(r, {'color': '#999999', 'hatch': ''})
            color, hatch = style['color'], style['hatch']
        ax.bar(i, down_rets[ticker],
               color=color, hatch=hatch,
               edgecolor='#333333', linewidth=0.6, alpha=0.85, width=0.7)

    _zero_line(ax)
    ax.set_xticks(range(len(sorted_t)))
    ax.set_xticklabels(sorted_t, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Avg NAV Return (%)', fontsize=9)
    ax.set_title(
        'Downside Protection: Avg Return in Benchmark Market-Down Months\n'
        f'{n_note}',
        fontsize=10
    )

    legend_handles = [
        Patch(facecolor=REGION_STYLES[r]['color'], hatch=REGION_STYLES[r]['hatch'],
              label=f'ESG – {r}', edgecolor='#333333', linewidth=0.5)
        for r in REGIONS if r in REGION_STYLES
    ] + [Patch(facecolor=CONV_STYLE['color'], hatch=CONV_STYLE['hatch'],
               label='Conventional', edgecolor='#333333', linewidth=0.5)]
    _bottom_legend(ax, legend_handles, ncol=3)

    plt.tight_layout()
    return [('downside_protection', fig)]


# ── fig7 – OGR Heatmap: ESG avg vs Conventional (two rows per region) ────────

def fig7_regional_heatmap(period_df):
    regions  = [r for r in REGIONS if r in period_df['region'].values]
    n_p      = len(_PERIOD_LABELS)
    row_labels, matrix_rows = [], []

    for region in regions:
        # ESG average
        esg_row = []
        for period in _PERIOD_LABELS:
            sub = period_df[(period_df['region'] == region) &
                            (period_df['period'] == period) &
                            (period_df['type'] == 'ESG')]
            esg_row.append(sub['avg_ogr_pct'].mean() if not sub.empty else 0.0)
        row_labels.append(f'{region} — ESG')
        matrix_rows.append(esg_row)

        # Conventional (single ETF)
        conv_row = []
        for period in _PERIOD_LABELS:
            sub = period_df[(period_df['region'] == region) &
                            (period_df['period'] == period) &
                            (period_df['type'] == 'Conventional')]
            conv_row.append(sub['avg_ogr_pct'].mean() if not sub.empty else np.nan)
        if any(not np.isnan(v) for v in conv_row):
            row_labels.append(f'{region} — Conv.')
            matrix_rows.append([0.0 if np.isnan(v) else v for v in conv_row])

    matrix = np.array(matrix_rows)
    vmax   = max(np.abs(matrix).max(), 0.01)
    n_r    = len(row_labels)

    fig, ax = plt.subplots(figsize=(_FW, max(3.0, n_r * 0.5)))
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(n_p))
    ax.set_xticklabels(_PERIOD_LABELS, fontsize=8)
    ax.set_yticks(range(n_r))
    ax.set_yticklabels(row_labels, fontsize=8)
    ax.set_title('Average Monthly OGR: ESG vs. Conventional by Region and Period',
                 fontsize=10)

    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label('Avg Monthly OGR (%)', fontsize=9)
    cbar.ax.tick_params(labelsize=8)

    plt.tight_layout()
    return [('regional_heatmap', fig)]


# ── fig8 – β_neg by Region: ESG avg vs Conventional (new comparison chart) ───

def fig8_esg_vs_conv_beta(comparison_df):
    """
    Grouped bar chart: per region, ESG average β_neg vs. Conventional β_neg.
    comparison_df comes from compare_esg_vs_conventional().
    """
    df = comparison_df.dropna(subset=['esg_beta_neg_mean'])

    x      = np.arange(len(df))
    width  = 0.35
    fig, ax = plt.subplots(figsize=(_FW, 3.5))

    esg_bars  = ax.bar(x - width / 2, df['esg_beta_neg_mean'],  width,
                       color='#1B6CA8', hatch='//', edgecolor='#333333',
                       linewidth=0.6, alpha=0.85, label='ESG (avg)')
    conv_bars = ax.bar(x + width / 2, df['conv_beta_neg'].fillna(0), width,
                       color=CONV_STYLE['color'], hatch=CONV_STYLE['hatch'],
                       edgecolor='#333333', linewidth=0.6, alpha=0.85,
                       label='Conventional')

    _zero_line(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(df['region'], fontsize=8)
    ax.set_ylabel(r'Average $\beta_{neg}$', fontsize=9)
    ax.set_title(r'$\beta_{neg}$ by Region: ESG vs. Conventional'
                 '\n(lower = investors hold during downturns = higher loyalty)',
                 fontsize=10)
    _bottom_legend(ax, ax.get_legend_handles_labels()[0] or
                   [Patch(facecolor='#1B6CA8', hatch='//', label='ESG (avg)', edgecolor='#333333'),
                    Patch(facecolor=CONV_STYLE['color'], hatch=CONV_STYLE['hatch'],
                          label='Conventional', edgecolor='#333333')],
                   ncol=2)

    plt.tight_layout()
    return [('esg_vs_conv_beta_by_region', fig)]
