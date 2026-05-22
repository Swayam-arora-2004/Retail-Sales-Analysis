"""
=============================================================================
 Retail Sales Analysis — Data Pipeline
 Dataset  : UCI Online Retail II
             https://archive.ics.uci.edu/dataset/502/online+retail+ii
 Author   : Portfolio Project
 Purpose  : Clean the raw dataset, remove cancellations / negative quantities,
            engineer a LineRevenue column, and load the result into a local
            SQLite database ready for SQL analysis and Excel export.
=============================================================================
"""

import sqlite3
import textwrap
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

# Auto-detect: prefer CSV (faster) over Excel if both exist
RAW_CSV    = Path("online_retail_II.csv")
RAW_XLSX   = Path("online_retail_II.xlsx")
RAW_FILE   = RAW_CSV if RAW_CSV.exists() else RAW_XLSX

DB_FILE    = Path("retail_sales.db")
DB_TABLE   = "transactions"

# Columns we expect in the raw file
# Note: CSV export from UCI may use 'Customer ID' or 'CustomerID'
REQUIRED_COLS = {
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
}


# ---------------------------------------------------------------------------
# HELPER: pretty-print a section banner
# ---------------------------------------------------------------------------

def banner(title: str) -> None:
    width = 70
    print("\n" + "═" * width)
    print(f"  {title}")
    print("═" * width)


# ---------------------------------------------------------------------------
# STEP 1 — Load raw data (both sheets combined)
# ---------------------------------------------------------------------------

def load_raw(path: Path) -> pd.DataFrame:
    banner("Step 1 · Loading raw data")

    if not path.exists():
        raise FileNotFoundError(
            f"\n  ✘  Dataset not found at: {path}\n"
            "  Please download 'online_retail_II.xlsx' or 'online_retail_II.csv'\n"
            "  from the UCI ML Repository and place it here.\n"
            "  URL: https://archive.ics.uci.edu/dataset/502/online+retail+ii"
        )

    if path.suffix == ".csv":
        print(f"  ↳  Reading CSV (fast path): {path.name} …")
        raw = pd.read_csv(
            path,
            encoding="latin-1",   # UCI CSV uses Latin-1, not UTF-8
            low_memory=False,
        )
    else:
        frames = []
        for sheet in ("Year 2009-2010", "Year 2010-2011"):
            print(f"  ↳  Reading sheet: {sheet} …")
            df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
            df["_source_sheet"] = sheet
            frames.append(df)
        raw = pd.concat(frames, ignore_index=True)

    print(f"  ✔  Loaded {len(raw):,} rows from {path.name}.")
    return raw


# ---------------------------------------------------------------------------
# STEP 2 — Validate schema
# ---------------------------------------------------------------------------

def validate_schema(df: pd.DataFrame) -> None:
    banner("Step 2 · Validating schema")
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")
    print(f"  ✔  All {len(REQUIRED_COLS)} expected columns are present.")


# ---------------------------------------------------------------------------
# STEP 3 — Clean & filter
# ---------------------------------------------------------------------------

def clean(df: pd.DataFrame) -> pd.DataFrame:
    banner("Step 3 · Cleaning data")

    initial_count = len(df)

    # --- 3a: Standardise column names -----------------------------------------
    df = df.rename(columns={"Customer ID": "CustomerID"})

    # --- 3b: Drop rows with missing Invoice or StockCode ----------------------
    before = len(df)
    df = df.dropna(subset=["Invoice", "StockCode"])
    print(f"  › Removed {before - len(df):,} rows with null Invoice / StockCode.")

    # --- 3c: Remove cancellations (invoices prefixed with 'C') ---------------
    before = len(df)
    df = df[~df["Invoice"].astype(str).str.startswith("C")]
    print(f"  › Removed {before - len(df):,} cancellation rows (Invoice starts with 'C').")

    # --- 3d: Remove non-product stock codes (e.g. postage, manual entries) ---
    #         Standard product codes are 5-6 digit numeric strings.
    before = len(df)
    df = df[df["StockCode"].astype(str).str.match(r"^\d{5,6}[A-Z]?$")]
    print(f"  › Removed {before - len(df):,} rows with non-product StockCodes.")

    # --- 3e: Remove rows with Quantity ≤ 0 or Price ≤ 0 ----------------------
    before = len(df)
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]
    print(f"  › Removed {before - len(df):,} rows with non-positive Quantity or Price.")

    # --- 3f: Drop rows with missing CustomerID --------------------------------
    before = len(df)
    df = df.dropna(subset=["CustomerID"])
    print(f"  › Removed {before - len(df):,} rows with null CustomerID.")

    # --- 3g: Type coercions ---------------------------------------------------
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["CustomerID"]  = df["CustomerID"].astype(int)
    df["Quantity"]    = df["Quantity"].astype(int)
    df["Price"]       = df["Price"].round(4)

    # --- 3h: Feature engineering — line revenue ------------------------------
    df["LineRevenue"] = (df["Quantity"] * df["Price"]).round(4)

    # --- 3i: Remove duplicate rows (belt-and-braces) -------------------------
    before = len(df)
    df = df.drop_duplicates()
    print(f"  › Removed {before - len(df):,} exact duplicate rows.")

    # --- 3j: Drop internal pipeline column -----------------------------------
    df = df.drop(columns=["_source_sheet"], errors="ignore")

    # --- Summary --------------------------------------------------------------
    print(
        f"\n  ✔  Cleaning complete.\n"
        f"     Raw rows:    {initial_count:>10,}\n"
        f"     Clean rows:  {len(df):>10,}\n"
        f"     Removed:     {initial_count - len(df):>10,} "
        f"({(initial_count - len(df)) / initial_count:.1%})"
    )
    return df


# ---------------------------------------------------------------------------
# STEP 4 — Load into SQLite
# ---------------------------------------------------------------------------

def load_to_sqlite(df: pd.DataFrame, db_path: Path) -> None:
    banner("Step 4 · Loading into SQLite")

    # Convert InvoiceDate to ISO string — SQLite has no native datetime type
    df = df.copy()
    df["InvoiceDate"] = df["InvoiceDate"].dt.strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(db_path) as conn:
        # Replace existing table on each pipeline run (idempotent)
        df.to_sql(DB_TABLE, conn, if_exists="replace", index=False)

        # Create indices to accelerate the analytical queries
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_stockcode ON {DB_TABLE}(StockCode);")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_invoice   ON {DB_TABLE}(Invoice);")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_customer  ON {DB_TABLE}(CustomerID);")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_date      ON {DB_TABLE}(InvoiceDate);")

        row_count = conn.execute(f"SELECT COUNT(*) FROM {DB_TABLE}").fetchone()[0]

    print(
        f"  ✔  Database: {db_path.resolve()}\n"
        f"     Table   : {DB_TABLE}\n"
        f"     Rows    : {row_count:,}"
    )


# ---------------------------------------------------------------------------
# STEP 5 — Quick sanity checks
# ---------------------------------------------------------------------------

def sanity_check(db_path: Path) -> None:
    banner("Step 5 · Sanity checks")

    with sqlite3.connect(db_path) as conn:
        checks = {
            "Total transactions": f"SELECT COUNT(*) FROM {DB_TABLE}",
            "Unique customers":   f"SELECT COUNT(DISTINCT CustomerID) FROM {DB_TABLE}",
            "Unique products":    f"SELECT COUNT(DISTINCT StockCode) FROM {DB_TABLE}",
            "Unique countries":   f"SELECT COUNT(DISTINCT Country) FROM {DB_TABLE}",
            "Total revenue (£)":  f"SELECT ROUND(SUM(LineRevenue), 2) FROM {DB_TABLE}",
            "Date range (start)": f"SELECT MIN(InvoiceDate) FROM {DB_TABLE}",
            "Date range (end)":   f"SELECT MAX(InvoiceDate) FROM {DB_TABLE}",
        }

        for label, sql in checks.items():
            value = conn.execute(sql).fetchone()[0]
            # Format large numbers with commas where applicable
            if isinstance(value, (int, float)) and abs(value) > 999:
                value = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
            print(f"  {label:<28}: {value}")

    print(f"\n  ✔  All checks passed. Database ready for analysis.\n")


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def main() -> None:
    print(
        textwrap.dedent("""
        ╔══════════════════════════════════════════════════════════════════════╗
        ║          Retail Sales Analysis — Data Pipeline (UK English)         ║
        ║          UCI Online Retail II  ·  pandas + sqlite3                  ║
        ╚══════════════════════════════════════════════════════════════════════╝
        """)
    )

    raw_df    = load_raw(RAW_FILE)
    validate_schema(raw_df)
    clean_df  = clean(raw_df)
    load_to_sqlite(clean_df, DB_FILE)
    sanity_check(DB_FILE)

    print("  Pipeline complete. Next: run 'pareto_analysis.sql' against retail_sales.db\n")


if __name__ == "__main__":
    main()
