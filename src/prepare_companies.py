"""
Prepare the list of companies for the Pharma red-flag screener.

This script does two things:
1. build_company_list(): reads the official Nifty Pharma constituents file
   and saves a clean list of companies with their Yahoo Finance tickers.
2. check_tickers(): confirms each ticker is recognised by Yahoo Finance by
   asking for the last few days of prices.

Why check tickers: before we download years of financial statements, we
want to know every ticker points to a live NSE-listed stock. If Yahoo
returns recent prices, the ticker is valid. If it returns nothing, the
ticker is wrong, the stock is delisted/suspended, or Yahoo does not cover it.

Run from the project root:
    python src/prepare_companies.py
"""

import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# Official Nifty Pharma constituents list, downloaded from NSE (not edited).
SOURCE_FILE = "data/nifty_pharma_list.csv"

# Clean company list that later steps of the project will read.
COMPANIES_FILE = "data/companies.csv"

# Yahoo Finance identifies NSE-listed stocks by adding ".NS" to the NSE symbol,
# e.g. SUNPHARMA on NSE -> SUNPHARMA.NS on Yahoo.
NSE_SUFFIX = ".NS"

# "5d" = the last 5 calendar days. Weekends and market holidays have no
# trading, so we may get fewer than 5 rows, but any actively traded stock
# should have at least one row.
PRICE_PERIOD = "5d"

# Short, readable company names for chart labels and the Excel watchlist.
# company_name (from NSE) is the full legal name, e.g. "Ajanta Pharmaceuticals
# Ltd.", which is too long to print under a bar in a chart. These are chosen
# by hand, not derived automatically, so unusual names (e.g. "Divi's",
# "Dr Reddy's") stay readable.
SHORT_NAMES = {
    "ABBOTINDIA.NS": "Abbott",
    "AJANTPHARM.NS": "Ajanta",
    "ALKEM.NS": "Alkem",
    "AUROPHARMA.NS": "Aurobindo",
    "BIOCON.NS": "Biocon",
    "CIPLA.NS": "Cipla",
    "DIVISLAB.NS": "Divi's",
    "DRREDDY.NS": "Dr Reddy's",
    "GLAND.NS": "Gland",
    "GLENMARK.NS": "Glenmark",
    "IPCALAB.NS": "IPCA",
    "LAURUSLABS.NS": "Laurus",
    "LUPIN.NS": "Lupin",
    "MANKIND.NS": "Mankind",
    "PPLPHARMA.NS": "Piramal",
    "SAILIFE.NS": "Sai Life",
    "SUNPHARMA.NS": "Sun Pharma",
    "TORNTPHARM.NS": "Torrent",
    "WOCKPHARMA.NS": "Wockhardt",
    "ZYDUSLIFE.NS": "Zydus",
}


# ---------------------------------------------------------------------------
# Step 1: build the company list
# ---------------------------------------------------------------------------

def build_company_list():
    """
    Read the Nifty Pharma list, build Yahoo tickers, and save companies.csv.

    ticker = NSE Symbol + ".NS"

    Returns the company table (columns: ticker, company_name, short_name,
    industry).
    """
    source = pd.read_csv(SOURCE_FILE)

    # Remove any stray spaces around the text so tickers are exact.
    symbols = source["Symbol"].str.strip()
    names = source["Company Name"].str.strip()
    industries = source["Industry"].str.strip()
    tickers = symbols + NSE_SUFFIX

    # Look up each ticker's short name from the hand-picked SHORT_NAMES dict.
    short_names = tickers.map(SHORT_NAMES)

    # If the Nifty Pharma list ever adds/removes a company, SHORT_NAMES will
    # be missing an entry and short_names will contain NaN. Fail loudly here
    # instead of silently saving a blank short_name.
    missing = tickers[short_names.isna()].tolist()
    if missing:
        raise ValueError(f"SHORT_NAMES has no entry for: {missing}")

    # Build the output table with the four columns later steps need.
    companies = pd.DataFrame({
        "ticker": tickers,
        "company_name": names,
        "short_name": short_names,
        "industry": industries,
    })

    # index=False stops pandas writing its row numbers as an extra column.
    companies.to_csv(COMPANIES_FILE, index=False)
    print(f"Saved {len(companies)} companies to {COMPANIES_FILE}")
    print()

    return companies


# ---------------------------------------------------------------------------
# Step 2: check each ticker on Yahoo Finance
# ---------------------------------------------------------------------------

def ticker_has_recent_prices(ticker):
    """
    Return True if Yahoo Finance has daily price data for `ticker`
    in the last PRICE_PERIOD, otherwise False.

    A ticker "passes" when the downloaded price table has at least one row.
    """
    try:
        # history() returns a table of daily prices
        # (Open, High, Low, Close, Volume) indexed by date.
        prices = yf.Ticker(ticker).history(period=PRICE_PERIOD)
    except Exception as error:
        # Network problems or unknown tickers can raise errors.
        # We treat any error as a failed check and print the reason.
        print(f"    error for {ticker}: {error}")
        return False

    # An empty table means Yahoo has no recent prices for this ticker.
    return len(prices) > 0


def check_tickers(companies):
    """
    Check every ticker in the `companies` table and print OK or FAILED
    for each one, followed by a summary.

    Returns the list of tickers that failed (empty if all passed).
    """
    ok_tickers = []
    failed_tickers = []

    for index, row in companies.iterrows():
        ticker = row["ticker"]
        name = row["company_name"]

        if ticker_has_recent_prices(ticker):
            status = "OK"
            ok_tickers.append(ticker)
        else:
            status = "FAILED"
            failed_tickers.append(ticker)

        print(f"{status:<7} {ticker:<16} {name}")

    # Summary at the end so the result is easy to see at a glance.
    print()
    print(f"Total tickers checked: {len(companies)}")
    print(f"OK:     {len(ok_tickers)}")
    print(f"FAILED: {len(failed_tickers)}")
    if failed_tickers:
        print("Failed tickers: " + ", ".join(failed_tickers))

    return failed_tickers


# ---------------------------------------------------------------------------
# Main: runs only when the file is executed directly, not when imported
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Build the list first, then check exactly the tickers we just saved.
    company_table = build_company_list()
    check_tickers(company_table)
