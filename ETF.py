"""
ESG ETF Multi-Fund Flow & Performance Analysis
===============================================
Loads ESG ETFs from ESG_ETF_Data/ and conventional benchmarks from
Traditional_ETF_Data/, then runs a unified flow-performance analysis
comparing both fund types.

Outputs
  ESG_ETF_CSV/               all CSV data files
  Analysis_Graph/<folder>/   PDF + PNG charts (one file per panel)

Dependencies: pip install pandas numpy matplotlib scipy lxml
"""

import os
import sys
import warnings

import pandas as pd
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

from ETF_Config   import BASE_DIR, DATA_FOLDER, TRADITIONAL_DATA_FOLDER
from ETF_Loader   import load_all_data
from ETF_Analysis import (
    compute_all_monthly_flows,
    period_flow_summary,
    flow_performance_sensitivity,
    nav_return_by_region,
    build_monthly_long,
    build_monthly_nav_wide,
    build_monthly_returns_wide,
    build_fund_info,
    build_summary_stats,
    build_full_results_summary,
    compare_esg_vs_conventional,
)
from etf_charts import (
    fig1_aum_trend,
    fig2_net_flow_trend,
    fig3_ogr_by_period,
    fig4_return_comparison,
    fig5_flow_sensitivity,
    fig6_downside_protection,
    fig7_regional_heatmap,
    fig8_esg_vs_conv_beta,
)

CSV_DIR   = os.path.join(BASE_DIR, 'ESG_ETF_CSV')
GRAPH_DIR = os.path.join(BASE_DIR, 'Analysis_Graph')


def _save_csv(df, filename):
    path = os.path.join(CSV_DIR, filename)
    df.to_csv(path, index=True if df.index.name else False)
    print(f'  {filename}')


def _clean_root_csvs():
    stray = [
        'flow_analysis_monthly.csv', 'flow_by_period.csv',
        'return_analysis_by_region.csv', 'sensitivity_analysis.csv',
    ]
    for fname in stray:
        p = os.path.join(BASE_DIR, fname)
        if os.path.exists(p):
            os.remove(p)
            print(f'  removed root-level {fname}')


def main():
    print('\n' + '=' * 60)
    print('ESG ETF Multi-Fund Analysis (ESG + Conventional)')
    print('=' * 60)

    os.makedirs(CSV_DIR,   exist_ok=True)
    os.makedirs(GRAPH_DIR, exist_ok=True)

    # ── 1. Load ESG + Conventional data ──────────────────────
    all_data = load_all_data(DATA_FOLDER, TRADITIONAL_DATA_FOLDER)
    if not all_data:
        print('No data loaded.')
        sys.exit(1)

    # ── 2. Compute monthly flows ──────────────────────────────
    monthly_flows = compute_all_monthly_flows(all_data)
    if not monthly_flows:
        print('No monthly flow data computed.')
        sys.exit(1)

    # ── 3. Run analyses ───────────────────────────────────────
    print('=' * 60)
    print('Running analyses...')
    print('=' * 60)

    period_df      = period_flow_summary(monthly_flows)
    return_df      = nav_return_by_region(monthly_flows)
    sensitivity_df = flow_performance_sensitivity(monthly_flows)
    comparison_df  = compare_esg_vs_conventional(sensitivity_df)

    # ── 4. Print key results ──────────────────────────────────
    pd.set_option('display.float_format', '{:.3f}'.format)

    print('\n--- Flow-Performance Sensitivity (ESG) ---')
    esg_s = sensitivity_df[sensitivity_df['type'] == 'ESG']
    print(esg_s[['ticker', 'region', 'n_months', 'beta_all',
                 'beta_negative', 'r_squared', 'p_value']].to_string(index=False))

    print('\n--- Flow-Performance Sensitivity (Conventional) ---')
    conv_s = sensitivity_df[sensitivity_df['type'] == 'Conventional']
    print(conv_s[['ticker', 'region', 'n_months', 'beta_all',
                  'beta_negative', 'r_squared', 'p_value']].to_string(index=False))

    print('\n--- ESG vs Conventional beta_neg Summary by Region ---')
    print(comparison_df.to_string(index=False))

    print('\n--- COVID Crisis OGR (sorted) ---')
    covid = (period_df[period_df['period'] == 'COVID Crisis']
             .sort_values('avg_ogr_pct', ascending=False))
    print(covid[['ticker', 'type', 'region', 'avg_ogr_pct',
                 'outflow_rate_pct']].to_string(index=False))

    # ── 5. Save CSVs ──────────────────────────────────────────
    print('\n' + '=' * 60)
    print('Saving CSVs to ESG_ETF_CSV/')
    print('=' * 60)

    _save_csv(build_fund_info(all_data, monthly_flows),             'fund_info.csv')
    _save_csv(build_monthly_nav_wide(monthly_flows),                'monthly_nav.csv')
    _save_csv(build_monthly_returns_wide(monthly_flows),            'monthly_returns.csv')
    _save_csv(build_monthly_long(monthly_flows),                    'flow_analysis_monthly.csv')
    _save_csv(period_df,                                            'flow_by_period.csv')
    _save_csv(return_df,                                            'return_analysis_by_region.csv')
    _save_csv(sensitivity_df,                                       'sensitivity_analysis.csv')
    _save_csv(build_summary_stats(period_df, return_df),            'summary_stats.csv')
    _save_csv(build_full_results_summary(period_df, sensitivity_df),'full_results_summary.csv')
    _save_csv(comparison_df,                                        'esg_vs_conventional_summary.csv')

    _clean_root_csvs()

    # ── 6. Save charts ────────────────────────────────────────
    print('\n' + '=' * 60)
    print('Saving charts to Analysis_Graph/')
    print('=' * 60)

    chart_fns = [
        ('Aum_Trend',           lambda: fig1_aum_trend(monthly_flows)),
        ('Net_Flow_Trend',      lambda: fig2_net_flow_trend(monthly_flows)),
        ('Ogr_by_Period',       lambda: fig3_ogr_by_period(period_df)),
        ('Return_Comparison',   lambda: fig4_return_comparison(return_df)),
        ('Flow_Sensitivity',    lambda: fig5_flow_sensitivity(sensitivity_df, monthly_flows)),
        ('Downside_Protection', lambda: fig6_downside_protection(monthly_flows)),
        ('Regional_Heatmap',    lambda: fig7_regional_heatmap(period_df)),
        ('ESG_vs_Conv_Beta',    lambda: fig8_esg_vs_conv_beta(comparison_df)),
    ]

    for folder, fn in chart_fns:
        folder_path = os.path.join(GRAPH_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)
        for stem, fig in fn():
            for ext, fmt, kw in [('.pdf', 'pdf', {}), ('.png', 'png', {'dpi': 300})]:
                path = os.path.join(folder_path, stem + ext)
                fig.savefig(path, format=fmt, bbox_inches='tight', facecolor='white', **kw)
                print(f'  {folder}/{stem}{ext}')
            plt.close(fig)

    # ── 7. Done ───────────────────────────────────────────────
    print('\n' + '=' * 60)
    print('Done!')
    print(f'  CSV    → {CSV_DIR}')
    print(f'  Charts → {GRAPH_DIR}')
    print('=' * 60)


if __name__ == '__main__':
    main()
