"""
Global constants and style settings shared across all ETF analysis modules.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR               = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER            = os.path.join(BASE_DIR, 'ESG_ETF_Data')
TRADITIONAL_DATA_FOLDER = os.path.join(BASE_DIR, 'Traditional_ETF_Data')

PERIODS_SHORT = {
    'Pre-COVID':    ('2019-01-01', '2020-02-29'),
    'COVID Crisis': ('2020-03-01', '2020-12-31'),
    'Recovery':     ('2021-01-01', '2021-12-31'),
    'Rate Hike':    ('2022-01-01', '2022-12-31'),
    'Rebound':      ('2023-01-01', '2023-12-31'),
    'Anti-ESG':     ('2024-01-01', '2025-12-31'),
}

# Conventional benchmark ETFs: ticker → region
CONVENTIONAL_TICKERS = {
    'IVV':  'US',
    'IEFA': 'Developed exUS',
    'IEMG': 'Emerging',
    'AGG':  'Fixed Income',
    'ACWI': 'Global',
}

# iShares ESG ETF → region classification
REGION_MAP = {
    # ESG – US
    'DSI':  'US', 'ERET': 'US',  'ESGU': 'US',
    'LCTD': 'US', 'SUSA': 'US',  'SUSL': 'US', 'USXF': 'US',
    # ESG – Developed ex-US
    'DMXF': 'Developed exUS', 'ESGD': 'Developed exUS', 'PABU': 'Developed exUS',
    # ESG – Emerging
    'EMXF': 'Emerging', 'ESGE': 'Emerging', 'LDEM': 'Emerging',
    # ESG – Fixed Income
    'EAGG': 'Fixed Income', 'EUSB': 'Fixed Income', 'HYXF': 'Fixed Income',
    'SUSB': 'Fixed Income', 'SUSC': 'Fixed Income',
    # ESG – Global
    'CRBN': 'Global',
    # Conventional benchmarks
    **CONVENTIONAL_TICKERS,
}

REGIONS = ['US', 'Developed exUS', 'Emerging', 'Fixed Income', 'Global']


def get_fund_type(ticker):
    """Return 'Conventional' for benchmark ETFs, 'ESG' for all others."""
    return 'Conventional' if ticker in CONVENTIONAL_TICKERS else 'ESG'


# ── Academic color scheme ─────────────────────────────────────────────────────
# Blue-family for ESG; orange/warm for Conventional.
# Each region also has a distinct line style for B&W reproducibility.

REGION_STYLES = {
    'US':             {'color': '#0A2342', 'linestyle': '-',           'marker': 'o', 'hatch': ''},
    'Developed exUS': {'color': '#1B6CA8', 'linestyle': '--',          'marker': 's', 'hatch': '//'},
    'Emerging':       {'color': '#2196C4', 'linestyle': ':',           'marker': '^', 'hatch': r'\\'},
    'Fixed Income':   {'color': '#5AADE2', 'linestyle': '-.',          'marker': 'D', 'hatch': 'xx'},
    'Global':         {'color': '#92C9E8', 'linestyle': (0, (5, 2)),   'marker': 'v', 'hatch': '..'},
}

# Conventional ETFs get a warm orange style, distinct from ESG blue family
CONV_STYLE = {
    'color':     '#B5440A',   # dark orange-brown
    'linestyle': (0, (4, 1)), # dense dash
    'marker':    '*',
    'hatch':     '|||',
    'linewidth': 2.0,
}

# Cycling styles for multiple ESG tickers within the same subplot
TICKER_STYLES = [
    {'linestyle': '-',               'marker': 'o'},
    {'linestyle': '--',              'marker': 's'},
    {'linestyle': ':',               'marker': '^'},
    {'linestyle': '-.',              'marker': 'D'},
    {'linestyle': (0, (5, 2)),       'marker': 'v'},
    {'linestyle': (0, (3, 1, 1, 1)), 'marker': 'P'},
    {'linestyle': (0, (1, 1)),       'marker': 'X'},
]

# Event shading colors
EVENT_COLORS = {
    'COVID':     '#8B1A1A',
    'Rate_Hike': '#4A235A',
}

# ── Matplotlib global style ───────────────────────────────────────────────────
plt.rcParams.update({
    'font.family':          'serif',
    'font.serif':           ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size':            10,
    'axes.titlesize':       10,
    'axes.labelsize':       9,
    'xtick.labelsize':      8,
    'ytick.labelsize':      8,
    'legend.fontsize':      8,
    'legend.framealpha':    0.9,
    'legend.edgecolor':     '#CCCCCC',
    'lines.linewidth':      1.5,
    'lines.markersize':     4,
    'axes.linewidth':       0.8,
    'patch.linewidth':      0.8,
    'axes.grid':            True,
    'grid.alpha':           0.25,
    'grid.linewidth':       0.5,
    'grid.color':           '#999999',
    'axes.spines.top':      False,
    'axes.spines.right':    False,
    'figure.dpi':           150,
    'savefig.dpi':          300,
    'savefig.bbox':         'tight',
    'savefig.facecolor':    'white',
})
