import sqlite3
from pathlib import Path

import pandas as pd

RAW_CSV  = Path("online_retail_II.csv")
RAW_XLSX = Path("online_retail_II.xlsx")
RAW_FILE = RAW_CSV if RAW_CSV.exists() else RAW_XLSX

DB_FILE  = Path("retail_sales.db")
TABLE    = "transactions"

REQUIRED_COLS = {
    "Invoice", "StockCode", "Description",
    "Quantity", "InvoiceDate", "Price",
    "Customer ID", "Country",
}


def load_raw(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            "Download from: https://archive.ics.uci.edu/dataset/502/online+retail+ii"
        )

    if path.suffix == ".csv":
        return pd.read_csv(path, encoding="latin-1", low_memory=False)

    frames = []
    for sheet in ("Year 2009-2010", "Year 2010-2011"):
        df = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def validate(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"Customer ID": "CustomerID"})

    df = df.dropna(subset=["Invoice", "StockCode"])
    df = df[~df["Invoice"].astype(str).str.startswith("C")]
    df = df[df["StockCode"].astype(str).str.match(r"^\d{5,6}[A-Z]?$")]
    df = df[(df["Quantity"] > 0) & (df["Price"] > 0)]
    df = df.dropna(subset=["CustomerID"])

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["CustomerID"]  = df["CustomerID"].astype(int)
    df["Quantity"]    = df["Quantity"].astype(int)
    df["Price"]       = df["Price"].round(4)
    df["LineRevenue"] = (df["Quantity"] * df["Price"]).round(4)

    df = df.drop_duplicates()
    return df


def load_db(df: pd.DataFrame, path: Path) -> None:
    df = df.copy()
    df["InvoiceDate"] = df["InvoiceDate"].dt.strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(path) as conn:
        df.to_sql(TABLE, conn, if_exists="replace", index=False)
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_stock    ON {TABLE}(StockCode)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_invoice  ON {TABLE}(Invoice)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_customer ON {TABLE}(CustomerID)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_date     ON {TABLE}(InvoiceDate)")


def report(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        stats = {
            "Transactions":    f"SELECT COUNT(*) FROM {TABLE}",
            "Customers":       f"SELECT COUNT(DISTINCT CustomerID) FROM {TABLE}",
            "Products":        f"SELECT COUNT(DISTINCT StockCode) FROM {TABLE}",
            "Countries":       f"SELECT COUNT(DISTINCT Country) FROM {TABLE}",
            "Revenue (GBP)":   f"SELECT ROUND(SUM(LineRevenue), 2) FROM {TABLE}",
            "Date from":       f"SELECT MIN(InvoiceDate) FROM {TABLE}",
            "Date to":         f"SELECT MAX(InvoiceDate) FROM {TABLE}",
        }
        for label, sql in stats.items():
            val = conn.execute(sql).fetchone()[0]
            if isinstance(val, (int, float)) and abs(val) > 999:
                val = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
            print(f"  {label:<18}: {val}")


def main():
    print(f"\nLoading {RAW_FILE.name} ...")
    raw = load_raw(RAW_FILE)
    print(f"Rows loaded      : {len(raw):,}")

    validate(raw)

    clean_df = clean(raw)
    removed  = len(raw) - len(clean_df)
    print(f"Rows after clean : {len(clean_df):,}  ({removed:,} removed)")

    load_db(clean_df, DB_FILE)
    print(f"\nDatabase         : {DB_FILE.resolve()}\n")

    report(DB_FILE)
    print("\nDone. Run export_to_excel.py to generate the Pareto output.\n")


if __name__ == "__main__":
    main()
