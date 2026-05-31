# ESG ETF Flow & Investor Loyalty Analysis

A quantitative study examining whether ESG (Environmental, Social, Governance) ETF investors exhibit stronger loyalty than conventional ETF investors — measured through fund flow sensitivity to market returns across five regions and six market periods (2019–2025).

---

## Research Question

> Do ESG ETF investors show conditional loyalty — holding positions during market downturns even when conventional investors redeem?

This is tested using the **Organic Growth Rate (OGR)** metric and **Flow-Performance Sensitivity** regression (β_neg), following the methodology of Bollen (2007).

---

## Sample

| Type | Tickers | Count |
|------|---------|------:|
| ESG ETFs | ESGU, DSI, SUSA, SUSL, USXF, LCTD, ERET, ESGD, DMXF, PABU, ESGE, EMXF, LDEM, EAGG, EUSB, HYXF, SUSB, SUSC, CRBN | 19 |
| Conventional benchmarks | IVV, IEFA, IEMG, AGG, ACWI | 5 |
| **Total** | | **24** |

All funds are iShares products (BlackRock), covering five regions: **US · Developed exUS · Emerging · Fixed Income · Global**. Data spans January 2019 – December 2025 (83 months), sourced from iShares historical NAV files.

---

## Key Metric: Organic Growth Rate (OGR)

$$\text{OGR}_t = \frac{\text{AUM}_t - \text{AUM}_{t-1} \times (1 + r_t^{\text{NAV}})}{\text{AUM}_{t-1}}$$

OGR isolates investor flow decisions from market return effects. A positive OGR indicates net inflows; a negative OGR indicates net outflows.

---

## Flow-Performance Sensitivity Model

$$\text{OGR}_t = \alpha + \beta \times r_t^{\text{NAV}} + \varepsilon_t$$

The regression is estimated separately for positive-return months (β_pos) and negative-return months (**β_neg**).

- **β_neg < 0**: OGR does not fall during market downturns → high investor loyalty
- **β_neg > 0**: Investors redeem when returns are negative → return-chasing behaviour

---

## Key Findings

### Average Monthly OGR by Region and Period (ESG ETFs only)

| Period | US | Dev. exUS | Emerging | Fixed Inc. | Global |
|--------|---:|----------:|--------:|-----------:|-------:|
| Pre-COVID | +11.83% | +7.73% | +15.17% | +11.45% | +1.36% |
| **COVID Crisis** | **+20.32%** | **+23.24%** | +3.77% | **+19.78%** | +0.42% |
| Recovery | +4.56% | +9.76% | +0.84% | +7.27% | +5.42% |
| Rate Hike | +0.06% | +3.21% | +1.07% | +1.47% | −2.02% |
| Rebound | −1.35% | +1.65% | +1.08% | +0.75% | −1.18% |
| Anti-ESG | −1.26% | +0.29% | −0.36% | +0.91% | −0.80% |

### β_neg: ESG vs Conventional by Region

| Region | ESG avg β_neg | Conventional β_neg | Direction |
|--------|-------------:|-------------------:|-----------|
| US | +0.563 | IVV: +0.186 | Conv. more loyal in downturns |
| Developed exUS | +0.194 | IEFA: +0.028 | Conv. slightly more loyal |
| **Emerging** | **−0.369** | IEMG: +0.184 | **ESG more loyal** |
| Fixed Income | +2.102 | AGG: +0.128 | Conv. markedly more loyal |
| Global | +0.257 | ACWI: −0.849 | ACWI driven by rebalancing |

**7 of 19 ESG ETFs show β_neg < 0** (HYXF p=0.007, PABU p=0.035 statistically significant), consistent with Bollen (2007). The loyalty effect is conditional and region-specific, not a universal ESG characteristic.

---

## Project Structure

```
ESG-ETF-Analysis/
│
├── ETF.py                  # Main entry point — run this to reproduce all results
├── ETF_Config.py           # Constants: regions, periods, colors, style settings
├── ETF_Loader.py           # XLS parser and data loader (handles iShares XML quirks)
├── ETF_Analysis.py         # OGR computation, regression, summary statistics
├── ETF_charts.py           # All 8 publication-quality figures
│
├── ESG_ETF_Data/           # 19 iShares ESG ETF historical NAV files (.xls)
├── Traditional_ETF_Data/   # 5 conventional benchmark ETF files (.xls)
│
├── ESG_ETF_CSV/            # Output: 11 CSV data files
│   ├── fund_info.csv                    # ETF metadata (24 funds)
│   ├── monthly_nav.csv                  # Monthly NAV prices (wide format)
│   ├── monthly_returns.csv              # Monthly NAV returns (wide format)
│   ├── flow_analysis_monthly.csv        # Long-format monthly OGR data
│   ├── flow_by_period.csv               # OGR by period × ETF
│   ├── return_analysis_by_region.csv    # Return statistics by region × period
│   ├── sensitivity_analysis.csv         # β_all, β_pos, β_neg per ETF
│   ├── summary_stats.csv                # Combined flow + return statistics
│   ├── full_results_summary.csv         # Full merged results table
│   └── esg_vs_conventional_summary.csv  # ESG vs Conv β_neg by region
│
└── Analysis_Graph/         # Output: 48 chart files (PDF + PNG per chart)
    ├── Aum_Trend/           # AUM trends (ESG and Conventional separated by region)
    ├── Net_Flow_Trend/      # Monthly net flow (3M rolling avg)
    ├── Ogr_by_Period/       # OGR line chart per region (ESG + Conv reference)
    ├── Return_Comparison/   # NAV return per region (ESG + Conv reference)
    ├── Flow_Sensitivity/    # β_neg bar chart + β_neg vs R² scatter
    ├── Downside_Protection/ # Avg return in market-down months
    ├── Regional_Heatmap/    # OGR heatmap: region × period (ESG vs Conv rows)
    └── ESG_vs_Conv_Beta/    # β_neg grouped bar: ESG avg vs Conventional
```

---

## How to Run

### 1. Install dependencies

```bash
pip install pandas numpy matplotlib scipy lxml
```

### 2. Prepare data

Place iShares XLS files (downloaded from [iShares.com](https://www.ishares.com)) into:
- `ESG_ETF_Data/` — ESG ETFs (filename = ticker symbol, e.g. `ESGU.xls`)
- `Traditional_ETF_Data/` — Conventional benchmarks (e.g. `IVV.xls`)

### 3. Run analysis

```bash
python ETF.py
```

This reproduces all CSVs in `ESG_ETF_CSV/` and all charts in `Analysis_Graph/`.

**Expected runtime:** ~60–90 seconds for 24 ETFs.

---

## Dependencies

| Package | Version tested |
|---------|---------------|
| Python | 3.13 |
| pandas | 3.0 |
| numpy | 2.3 |
| matplotlib | 3.10 |
| scipy | 1.17 |
| lxml | 6.1 |

---

## Reference

Bollen, N. P. B. (2007). Mutual fund attributes and investor behavior. *Journal of Financial and Quantitative Analysis*, 42(3), 683–708.
