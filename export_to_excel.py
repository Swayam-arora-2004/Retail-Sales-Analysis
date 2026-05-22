import sqlite3
from pathlib import Path

import pandas as pd

DB_FILE     = Path("retail_sales.db")
EXPORT_FILE = Path("pareto_output.xlsx")

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
        ROUND(TotalRevenue, 2)  AS TotalRevenue,
        NumberOfOrders,
        RANK() OVER (ORDER BY TotalRevenue DESC)    AS RevenueRank,
        COUNT(*) OVER ()                            AS TotalProducts,
        ROUND(
            TotalRevenue * 100.0 / SUM(TotalRevenue) OVER (),
            4
        )                                           AS RevenuePct,
        ROUND(
            SUM(TotalRevenue) OVER (
                ORDER BY TotalRevenue DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) * 100.0 / SUM(TotalRevenue) OVER (),
            4
        )                                           AS CumulativeRevenuePct
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
    SELECT
        *,
        RANK() OVER (ORDER BY TotalRevenue DESC)                    AS RevenueRank,
        COUNT(*) OVER ()                                            AS TotalProducts,
        TotalRevenue * 100.0 / SUM(TotalRevenue) OVER ()           AS RevenuePct
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


def run():
    if not DB_FILE.exists():
        raise FileNotFoundError("retail_sales.db not found — run pipeline.py first.")

    with sqlite3.connect(DB_FILE) as conn:
        detail_df  = pd.read_sql_query(QUERY_DETAIL,  conn)
        summary_df = pd.read_sql_query(QUERY_SUMMARY, conn)

    with pd.ExcelWriter(EXPORT_FILE, engine="openpyxl") as writer:
        detail_df.to_excel(writer,  sheet_name="Pareto_Detail",  index=False)
        summary_df.to_excel(writer, sheet_name="Pareto_Summary", index=False)

    print(f"\nExported to: {EXPORT_FILE.resolve()}")
    print(f"  Pareto_Detail  : {len(detail_df):,} products")
    print(f"  Pareto_Summary : {len(summary_df)} rows\n")
    print(summary_df.to_string(index=False))
    print()


if __name__ == "__main__":
    run()
