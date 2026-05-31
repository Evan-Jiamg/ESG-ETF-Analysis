"""
Data loading: parse iShares SpreadsheetML XLS files and batch-load a folder.

Handles two known quirks in iShares XLS exports:
  1. Unescaped & in XML (e.g. URL query strings)  → regex-escape before parsing
  2. Double UTF-8 BOM at file start               → strip all leading BOMs
"""

import re
import os
import pandas as pd
from lxml import etree


def parse_ishares_xls(filepath):
    """
    Parse one iShares Historical NAV XLS file.
    Returns a daily DataFrame indexed by date with columns: nav, shares, aum.
    Returns None if the file cannot be parsed or has insufficient data.
    """
    with open(filepath, 'rb') as f:
        raw = f.read()

    # Strip all leading UTF-8 BOMs
    while raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]

    # Escape bare & that are not part of a valid XML entity reference
    content = raw.decode('utf-8', errors='replace')
    content = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', '&amp;', content)

    root = etree.fromstring(content.encode('utf-8'))
    ns   = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}

    # Find the Historical worksheet
    nav_sheet = None
    for ws in root.findall('.//ss:Worksheet', ns):
        name = ws.get('{urn:schemas-microsoft-com:office:spreadsheet}Name', '')
        if 'Historical' in name:
            nav_sheet = ws
            break

    if nav_sheet is None:
        return None

    rows = [
        [cell.find('ss:Data', ns).text if cell.find('ss:Data', ns) is not None else ''
         for cell in row.findall('ss:Cell', ns)]
        for row in nav_sheet.findall('.//ss:Row', ns)
    ]

    # Locate header row (contains "As Of" or "NAV")
    header_idx = next(
        (i for i, r in enumerate(rows)
         if any('As Of' in str(c) or 'NAV' in str(c) for c in r)),
        None
    )
    if header_idx is None:
        return None

    headers   = [str(c).strip() for c in rows[header_idx]]
    data_rows = rows[header_idx + 1:]
    if not data_rows:
        return None

    df = pd.DataFrame(data_rows, columns=headers[:len(data_rows[0])])

    date_col   = next((c for c in df.columns if 'As Of' in c or 'Date' in c), None)
    nav_col    = next((c for c in df.columns if 'NAV'   in c and 'Non' not in c), None)
    shares_col = next((c for c in df.columns if 'Shares' in c), None)

    if not all([date_col, nav_col, shares_col]):
        return None

    df = df[[date_col, nav_col, shares_col]].copy()
    df.columns = ['date', 'nav', 'shares']

    df = df[df['date'].notna() & (df['date'] != '')]
    df['date']   = pd.to_datetime(df['date'], format='%b %d, %Y', errors='coerce')
    df['nav']    = pd.to_numeric(df['nav'], errors='coerce')
    df['shares'] = pd.to_numeric(
        df['shares'].astype(str).str.replace(',', '', regex=False), errors='coerce'
    )
    df = df.dropna().sort_values('date')
    df = df[(df['date'] >= '2019-01-01') & (df['date'] <= '2025-12-31')]

    if len(df) < 200:
        return None

    df['aum'] = df['nav'] * df['shares']
    return df.set_index('date')


def load_all_xls(data_folder):
    """
    Load every .xls file in data_folder.
    Returns dict of {ticker: daily_DataFrame}.
    """
    all_data = {}
    for filename in sorted(os.listdir(data_folder)):
        if not filename.endswith('.xls'):
            continue
        ticker   = filename.replace('.xls', '')
        filepath = os.path.join(data_folder, filename)
        try:
            df = parse_ishares_xls(filepath)
            if df is None:
                print(f'  {ticker}: skipped (parse failed or data < 200 rows)')
                continue
            all_data[ticker] = df
            print(f'  {ticker}: {len(df)} days  '
                  f'({df.index[0].date()} ~ {df.index[-1].date()})')
        except Exception as e:
            print(f'  {ticker}: error - {e}')
    return all_data


def load_all_data(esg_folder, traditional_folder):
    """
    Load ESG and Conventional ETFs from their respective folders.
    Returns dict of {ticker: daily_DataFrame} with all ETFs combined.
    """
    print('=' * 60)
    print('Loading ESG ETFs...')
    print('=' * 60)
    esg_data = load_all_xls(esg_folder)
    print(f'  → {len(esg_data)} ESG ETFs loaded\n')

    print('=' * 60)
    print('Loading Conventional ETFs...')
    print('=' * 60)
    conv_data = load_all_xls(traditional_folder)
    print(f'  → {len(conv_data)} Conventional ETFs loaded\n')

    return {**esg_data, **conv_data}
