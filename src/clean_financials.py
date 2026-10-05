"""
Clean the 60 raw Yahoo Finance CSVs into one tidy table.

Input:
    data/raw/{TICKER}_{statement}.csv   downloaded by fetch_financials.py (never modified here)
    data/manual_overrides.csv           hand-entered values recorded in DECISIONS.md
Output:
    data/processed/financials_clean.csv  one row per company per fiscal year
    data/processed/data_quality_log.csv  every source choice, adjustment and data issue

Run from the project root:
    python src/clean_financials.py
"""

import os

import pandas as pd

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

COMPANIES_FILE = "data/companies.csv"
RAW_DIR = "data/raw"
MANUAL_OVERRIDES_FILE = "data/manual_overrides.csv"
CLEAN_FILE = "data/processed/financials_clean.csv"
QUALITY_LOG_FILE = "data/processed/data_quality_log.csv"

STATEMENT_FILES = ["balance_sheet", "income_statement", "cash_flow"]

# Yahoo reports money in rupees. 1 crore = 10,000,000 rupees, so dividing by 1e7 gives Rs crore.
CRORE_DIVISOR = 1e7

# Largest accepted gap between total assets and (liabilities + equity), as a share of total assets.
BALANCE_TOLERANCE = 0.01

# For each standard field: Yahoo rows to try, in order of preference, as (statement, exact row name).
# The first row that exists in a company's files is used. Names match notebooks/01_explore.ipynb,
# plus Cost Of Revenue and the dividend rows, which the notebook did not map.
FIELD_SOURCES = {
    "revenue": [("income_statement", "Total Revenue")],
    "cost_of_revenue": [("income_statement", "Cost Of Revenue")],
    "gross_profit": [("income_statement", "Gross Profit")],
    "ebit": [("income_statement", "EBIT")],
    "net_income": [("income_statement", "Net Income")],
    "interest_expense": [("income_statement", "Interest Expense")],
    "sga": [("income_statement", "Selling General And Administration")],
    "depreciation": [
        ("income_statement", "Depreciation And Amortization In Income Statement"),
        ("cash_flow", "Depreciation And Amortization"),
    ],
    "total_assets": [("balance_sheet", "Total Assets")],
    "current_assets": [("balance_sheet", "Current Assets")],
    "current_liabilities": [("balance_sheet", "Current Liabilities")],
    "retained_earnings": [("balance_sheet", "Retained Earnings")],
    "total_equity": [("balance_sheet", "Stockholders Equity")],
    "total_liabilities": [("balance_sheet", "Total Liabilities Net Minority Interest")],
    "receivables": [
        ("balance_sheet", "Accounts Receivable"),
        ("balance_sheet", "Receivables"),
    ],
    "inventory": [("balance_sheet", "Inventory")],
    "net_ppe": [("balance_sheet", "Net PPE")],
    "long_term_debt": [("balance_sheet", "Long Term Debt")],
    "total_debt": [("balance_sheet", "Total Debt")],
    "shares_outstanding": [
        ("balance_sheet", "Ordinary Shares Number"),
        ("balance_sheet", "Share Issued"),
    ],
    "operating_cash_flow": [("cash_flow", "Operating Cash Flow")],
    "dividends_paid": [
        ("cash_flow", "Cash Dividends Paid"),
        ("cash_flow", "Common Stock Dividend Paid"),
    ],
    # Used only by the balance check, not one of the 22 standard fields.
    "total_equity_incl_mi": [("balance_sheet", "Total Equity Gross Minority Interest")],
}

CHECK_ONLY_FIELDS = ["total_equity_incl_mi"]
STANDARD_FIELDS = [field for field in FIELD_SOURCES if field not in CHECK_ONLY_FIELDS]

# Shares outstanding is a count of shares, not money, so it is not divided by 1e7.
MONEY_FIELDS = [field for field in FIELD_SOURCES if field != "shares_outstanding"]

# DECISIONS.md: these companies have no long-term debt row (or a partial one), so Total Debt is used for all years.
TOTAL_DEBT_AS_LONG_TERM_DEBT = ["ABBOTINDIA.NS", "DIVISLAB.NS", "AJANTPHARM.NS"]

# DECISIONS.md: Torrent's retained earnings is blank for these years, so they are rolled forward.
ROLL_FORWARD_RE_YEARS = {"TORNTPHARM.NS": [2025, 2026]}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def log_entry(ticker, fiscal_year, check, field, detail):
    """Build one row of the data-quality log as a dictionary."""
    return {
        "ticker": ticker,
        "fiscal_year": fiscal_year,
        "check": check,
        "field": field,
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# Reading the raw files
# ---------------------------------------------------------------------------

def load_statement(ticker, statement):
    """
    Read one raw statement CSV, with line items as the row index and fiscal years as columns.

    Yahoo's column headers are year-end dates such as "2026-03-31". Indian companies mostly end
    their year on 31 March, so the calendar year of that date is the fiscal year that ends in it
    (FY2025-26 -> 2026).
    """
    prefix = ticker.replace(".", "_")
    path = os.path.join(RAW_DIR, f"{prefix}_{statement}.csv")
    table = pd.read_csv(path, index_col="line_item")
    table.columns = [pd.Timestamp(column).year for column in table.columns]
    return table


def pick_first_available_row(statements, candidates):
    """
    Return (source_name, values) for the first candidate row that exists, or (None, None).

    source_name looks like "Total Revenue (income_statement)" so the log shows where a number came from.
    values is a row of numbers, one per fiscal year, which may contain blanks (NaN).
    """
    for statement, line_item in candidates:
        table = statements[statement]
        if line_item in table.index:
            return f"{line_item} ({statement})", table.loc[line_item]
    return None, None


# ---------------------------------------------------------------------------
# Building one company's table
# ---------------------------------------------------------------------------

def build_company_table(ticker, log_rows):
    """
    Build one company's table: one row per fiscal year, one column per standard field, in raw rupees.

    Every source row chosen is recorded in log_rows. A fiscal year where every standard field is blank
    is dropped and logged, because Yahoo sometimes returns an empty older column (same rule as
    src/fetch_financials.py).
    """
    statements = {name: load_statement(ticker, name) for name in STATEMENT_FILES}

    columns = {}
    for field, candidates in FIELD_SOURCES.items():
        source_name, values = pick_first_available_row(statements, candidates)
        if source_name is None:
            log_rows.append(log_entry(ticker, None, "source_used", field, "NOT FOUND in any candidate row"))
            columns[field] = pd.Series(dtype="float64")
        else:
            log_rows.append(log_entry(ticker, None, "source_used", field, source_name))
            columns[field] = values.astype("float64")

    table = pd.DataFrame(columns)
    table.index.name = "fiscal_year"

    all_blank = table[STANDARD_FIELDS].isna().all(axis=1)
    for year in table.index[all_blank]:
        log_rows.append(log_entry(ticker, year, "empty_year_dropped", None, "no values in any standard field"))
    table = table[~all_blank]

    table.insert(0, "ticker", ticker)
    return table.sort_index()


# ---------------------------------------------------------------------------
# Units and adjustments
# ---------------------------------------------------------------------------

def convert_money_to_crore(table):
    """
    Divide every money field by 1e7 so values are in Rs crore.

    Formula: value_crore = value_rupees / 10,000,000
    """
    for field in MONEY_FIELDS:
        table[field] = table[field] / CRORE_DIVISOR
    return table


def apply_debt_overrides(table, ticker, log_rows):
    """
    Set long_term_debt equal to total_debt in every year, for the companies in TOTAL_DEBT_AS_LONG_TERM_DEBT.

    Why: these companies have no long-term debt row (or a partial one). Screener.in's borrowings match
    Yahoo's Total Debt exactly for them, so Total Debt is used as the borrowing figure.
    If a Yahoo long_term_debt value already exists for a year (AJANTPHARM FY2024), it is replaced and the log says so.
    """
    if ticker not in TOTAL_DEBT_AS_LONG_TERM_DEBT:
        return table

    for year in table.index:
        old_value = table.loc[year, "long_term_debt"]
        detail = "long_term_debt set to total_debt"
        if pd.notna(old_value):
            detail += f" (replaced Yahoo value of {old_value:.2f} crore)"
        log_rows.append(log_entry(ticker, year, "adjustment", "long_term_debt", detail))

    table["long_term_debt"] = table["total_debt"]
    return table


def load_manual_overrides():
    """Read data/manual_overrides.csv, which holds the hand-entered values recorded in DECISIONS.md."""
    return pd.read_csv(MANUAL_OVERRIDES_FILE)


def apply_manual_overrides(table, ticker, overrides, log_rows):
    """
    Write each hand-entered value for this ticker into its cell.

    Values in the file are already in Rs crore, so this runs after the crore conversion and is not divided again.
    """
    rows = overrides[overrides["ticker"] == ticker]
    for _, row in rows.iterrows():
        year = int(row["fiscal_year"])
        field = row["field"]
        if year not in table.index:
            raise ValueError(f"Manual override for {ticker} FY{year} has no matching year in the raw data")
        table.loc[year, field] = row["value_crore"]
        detail = f"{field} from manual override: {row['value_crore']} crore ({row['source']})"
        log_rows.append(log_entry(ticker, year, "adjustment", field, detail))
    return table


def roll_forward_retained_earnings(table, ticker, log_rows):
    """
    Fill retained earnings for the years in ROLL_FORWARD_RE_YEARS by rolling the previous year forward.

    Formula (retained earnings roll-forward):
        RE(t) = RE(t-1) + Net income(t) - |Dividends paid(t)|

    Retained earnings is the cumulative profit kept in the business. Each year it grows by that year's
    profit and shrinks by the dividends paid out. Yahoo reports dividends paid as a negative number,
    so abs() takes their size. Years are processed in order, so FY2026 uses the rolled-forward FY2025.
    This ignores other equity movements (share issues, other comprehensive income, acquisition effects),
    so it is an approximation.
    """
    for year in ROLL_FORWARD_RE_YEARS.get(ticker, []):
        previous_re = table.loc[year - 1, "retained_earnings"]
        net_income = table.loc[year, "net_income"]
        dividends = table.loc[year, "dividends_paid"]
        new_re = previous_re + net_income - abs(dividends)
        table.loc[year, "retained_earnings"] = new_re
        detail = (
            f"retained_earnings rolled forward from FY{year - 1}: "
            f"{previous_re:.2f} + {net_income:.2f} - {abs(dividends):.2f} = {new_re:.2f} crore"
        )
        log_rows.append(log_entry(ticker, year, "adjustment", "retained_earnings", detail))
    return table


# ---------------------------------------------------------------------------
# Quality checks
# ---------------------------------------------------------------------------

def run_balance_check(table, ticker):
    """
    Check that total assets roughly equals total liabilities plus total equity including minority interest.

    Formula (balance sheet identity):
        gap = |Total assets - (Total liabilities + Total equity incl. minority interest)| / Total assets
    A year passes if gap <= 1%. Minority interest is the part of subsidiaries' equity owned by outside
    shareholders. It counts as equity on a consolidated balance sheet, so it must be included.
    Returns a list of log rows for the years that fail or cannot be checked.
    """
    issues = []
    for year, row in table.iterrows():
        assets = row["total_assets"]
        liabilities = row["total_liabilities"]
        equity = row["total_equity_incl_mi"]
        if pd.isna(assets) or pd.isna(liabilities) or pd.isna(equity):
            detail = "total_assets, total_liabilities or total equity incl. minority interest is blank"
            issues.append(log_entry(ticker, year, "balance_check_not_possible", None, detail))
            continue
        gap = abs(assets - (liabilities + equity)) / assets
        if gap > BALANCE_TOLERANCE:
            detail = f"gap is {gap:.2%} of total assets (limit {BALANCE_TOLERANCE:.0%})"
            issues.append(log_entry(ticker, year, "balance_check_failed", None, detail))
    return issues


def find_missing_required(table, ticker):
    """Return one log row for each blank standard field, in each year. Blank values stay NaN."""
    issues = []
    for year, row in table.iterrows():
        for field in STANDARD_FIELDS:
            if pd.isna(row[field]):
                issues.append(log_entry(ticker, year, "missing_required", field, "blank in Yahoo data; left as NaN"))
    return issues


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def build_data_notes(clean, log_rows):
    """Return one text cell per row, joining that row's adjustment messages with '; '."""
    notes = {}
    for entry in log_rows:
        if entry["check"] == "adjustment":
            key = (entry["ticker"], entry["fiscal_year"])
            notes.setdefault(key, []).append(entry["detail"])
    return [
        "; ".join(notes.get((ticker, year), []))
        for ticker, year in zip(clean["ticker"], clean["fiscal_year"])
    ]


def print_summary(clean, log_rows):
    """Print row counts, blanks per field, adjustments and quality issues."""
    log = pd.DataFrame(log_rows)

    print(f"Companies in output: {clean['ticker'].nunique()} (expected 20)")
    print(f"Rows in output:      {len(clean)}")
    print()
    print("Rows per company:")
    print(clean.groupby("ticker").size().to_string())

    print()
    print("Blank values per standard field (across all rows):")
    blanks = clean[STANDARD_FIELDS].isna().sum()
    print(blanks[blanks > 0].to_string() if (blanks > 0).any() else "  none")

    print()
    print("Adjustments made:")
    adjustments = log[log["check"] == "adjustment"]
    for _, row in adjustments.iterrows():
        print(f"  {row['ticker']:<15} FY{int(row['fiscal_year'])}  {row['detail']}")

    print()
    print("Source rows not found in any candidate name:")
    not_found = log[log["detail"].astype(str).str.startswith("NOT FOUND")]
    if len(not_found) == 0:
        print("  none")
    for _, row in not_found.iterrows():
        print(f"  {row['ticker']:<15} {row['field']}")

    print()
    print("Balance check (total assets vs liabilities + equity incl. minority interest):")
    balance = log[log["check"].isin(["balance_check_failed", "balance_check_not_possible"])]
    if len(balance) == 0:
        print("  all rows pass")
    for _, row in balance.iterrows():
        print(f"  {row['check']:<26} {row['ticker']:<15} FY{int(row['fiscal_year'])}  {row['detail']}")

    print()
    print("Empty fiscal years dropped:", int((log["check"] == "empty_year_dropped").sum()))

    print()
    print("Blank required fields, by field:")
    missing = log[log["check"] == "missing_required"]
    if len(missing) == 0:
        print("  none")
    else:
        print(missing["field"].value_counts().to_string())


def main():
    companies = pd.read_csv(COMPANIES_FILE)
    overrides = load_manual_overrides()

    log_rows = []
    tables = []
    for ticker in companies["ticker"]:
        table = build_company_table(ticker, log_rows)
        table = convert_money_to_crore(table)
        table = apply_debt_overrides(table, ticker, log_rows)
        table = apply_manual_overrides(table, ticker, overrides, log_rows)
        table = roll_forward_retained_earnings(table, ticker, log_rows)
        log_rows.extend(run_balance_check(table, ticker))
        log_rows.extend(find_missing_required(table, ticker))
        tables.append(table)

    clean = pd.concat(tables).reset_index()
    clean["data_notes"] = build_data_notes(clean, log_rows)
    clean = clean[["ticker", "fiscal_year"] + STANDARD_FIELDS + CHECK_ONLY_FIELDS + ["data_notes"]]

    os.makedirs(os.path.dirname(CLEAN_FILE), exist_ok=True)
    clean.to_csv(CLEAN_FILE, index=False)
    pd.DataFrame(log_rows).to_csv(QUALITY_LOG_FILE, index=False)
    print(f"Saved {CLEAN_FILE} and {QUALITY_LOG_FILE}")
    print()

    print_summary(clean, log_rows)


if __name__ == "__main__":
    main()
