"""
=============================================================================
 Retail Sales Analysis — SQL Query Runner & Excel Exporter
 Purpose : Execute the Pareto analysis SQL and export results to Excel.
=============================================================================
"""

import sqlite3
from pathlib import Path

import pandas as pd

DB_FILE     = Path("retail_sales.db")
EXPORT_FILE = Path("pareto_output.xlsx")

# ---------------------------------------------------------------------------
# Section A — Per-product Pareto detail (Top 10% only)
# ---------------------------------------------------------------------------
QUERY_DETAIL = """
WITH product_revenue AS (
    SELECT
        StockCode,
        MAX(Description)        AS ProductDescription,
        SUM(Quantity)           AS TotalUnitsSold,
        SUM(LineRevenue)        AS TotalRevenue,
        COUNT(DISTINCT Invoice) AS NumberOfOrders
    FROM transactions
    GROUP BY StockCode
),
revenue_ranked AS (
    SELECT
        StockCode,
        ProductDescription,
        TotalUnitsSold,
        ROUND(TotalRevenue, 2)   AS TotalRevenue,
        NumberOfOrders,
        RANK() OVER (ORDER BY TotalRevenue DESC)   AS RevenueRank,
        COUNT(*) OVER ()                           AS TotalProducts,
        ROUND(
            TotalRevenue * 100.0 / SUM(TotalRevenue) OVER (),
            4
        )                                          AS RevenuePct,
        ROUND(
            SUM(TotalRevenue) OVER (
                ORDER BY TotalRevenue DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) * 100.0 / SUM(TotalRevenue) OVER (),
            4
        )                                          AS CumulativeRevenuePct
    FROM product_revenue
),
pareto_flagged AS (
    SELECT
        *,
        CASE
            WHEN RevenueRank <= CEIL(TotalProducts * 0.10)
            THEN 'Top 10%'
            ELSE 'Remaining 90%'
        END AS ParetoSegment
    FROM revenue_ranked
)
SELECT
    RevenueRank,
    StockCode,
    ProductDescription,
    TotalUnitsSold,
    TotalRevenue,
    NumberOfOrders,
    RevenuePct              AS "Revenue %",
    CumulativeRevenuePct    AS "Cumulative Revenue %",
    ParetoSegment
FROM pareto_flagged
WHERE ParetoSegment = 'Top 10%'
ORDER BY RevenueRank
"""

# ---------------------------------------------------------------------------
# Section B — Headline Pareto summary (2 rows: Top 10% vs Remaining 90%)
# ---------------------------------------------------------------------------
QUERY_SUMMARY = """
WITH product_revenue AS (
    SELECT
        StockCode,
        SUM(LineRevenue)        AS TotalRevenue,
        SUM(Quantity)           AS TotalUnitsSold,
        COUNT(DISTINCT Invoice) AS NumberOfOrders
    FROM transactions
    GROUP BY StockCode
),
revenue_ranked AS (
    SELECT *,
        RANK() OVER (ORDER BY TotalRevenue DESC)                 AS RevenueRank,
        COUNT(*) OVER ()                                         AS TotalProducts,
        TotalRevenue * 100.0 / SUM(TotalRevenue) OVER ()        AS RevenuePct
    FROM product_revenue
),
pareto_flagged AS (
    SELECT *,
        CASE
            WHEN RevenueRank <= CEIL(TotalProducts * 0.10)
            THEN 'Top 10%'
            ELSE 'Remaining 90%'
        END AS ParetoSegment
    FROM revenue_ranked
)
SELECT
    ParetoSegment,
    COUNT(*)                     AS ProductCount,
    ROUND(SUM(TotalRevenue), 2)  AS SegmentRevenue,
    ROUND(SUM(RevenuePct), 2)    AS "SegmentRevenuePct (%)",
    SUM(TotalUnitsSold)          AS SegmentUnitsSold,
    SUM(NumberOfOrders)          AS SegmentOrders
FROM pareto_flagged
GROUP BY ParetoSegment
ORDER BY ParetoSegment DESC
"""


def run_pareto_to_excel() -> None:
    if not DB_FILE.exists():
        raise FileNotFoundError(
            "retail_sales.db not found. Run pipeline.py first."
        )

    print("Running Pareto analysis queries …")

    with sqlite3.connect(DB_FILE) as conn:
        detail_df  = pd.read_sql_query(QUERY_DETAIL,  conn)
        summary_df = pd.read_sql_query(QUERY_SUMMARY, conn)

    # ---- Export to Excel (two sheets) ---------------------------------------
    with pd.ExcelWriter(EXPORT_FILE, engine="openpyxl") as writer:
        detail_df.to_excel(writer,  sheet_name="Pareto_Detail",  index=False)
        summary_df.to_excel(writer, sheet_name="Pareto_Summary", index=False)

    print(f"\n  ✔  Exported to: {EXPORT_FILE.resolve()}")
    print(f"     Sheet 1 — 'Pareto_Detail'  : {len(detail_df):,} products (Top 10%)")
    print(f"     Sheet 2 — 'Pareto_Summary' : {len(summary_df)} rows\n")

    print("  📊  Pareto Summary:")
    print(summary_df.to_string(index=False))
    print("\n  Open pareto_output.xlsx in Excel to build your dashboard.")


if __name__ == "__main__":
    run_pareto_to_excel()
