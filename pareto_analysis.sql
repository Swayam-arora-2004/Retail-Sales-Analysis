-- =============================================================================
--  Retail Sales Analysis — Pareto Analysis Query
--  Database : retail_sales.db  (populated by pipeline.py)
--  Purpose  : Identify the top 10% of products responsible for ~60% of total
--             revenue, demonstrating the Pareto Principle (80/20 Rule).
--  Features : CTEs · Window Functions · Cumulative Distribution
-- =============================================================================

-- ---------------------------------------------------------------------------
-- CTE 1: product_revenue
--   Aggregate total revenue and units sold per product.
-- ---------------------------------------------------------------------------
WITH product_revenue AS (
    SELECT
        StockCode,
        -- Use MAX(Description) to pick a single description per product
        -- (avoids grouping on a free-text field that can vary slightly)
        MAX(Description)            AS ProductDescription,
        SUM(Quantity)               AS TotalUnitsSold,
        SUM(LineRevenue)            AS TotalRevenue,
        COUNT(DISTINCT Invoice)     AS NumberOfOrders
    FROM transactions
    GROUP BY StockCode
),

-- ---------------------------------------------------------------------------
-- CTE 2: revenue_ranked
--   Rank products by descending revenue and compute each product's share of
--   total revenue using a window function over the entire result set.
-- ---------------------------------------------------------------------------
revenue_ranked AS (
    SELECT
        StockCode,
        ProductDescription,
        TotalUnitsSold,
        ROUND(TotalRevenue, 2)          AS TotalRevenue,
        NumberOfOrders,

        -- Rank: 1 = highest revenue product
        RANK() OVER (ORDER BY TotalRevenue DESC)   AS RevenueRank,

        -- Total number of distinct products (used to compute decile threshold)
        COUNT(*) OVER ()                           AS TotalProducts,

        -- Each product's percentage contribution to overall portfolio revenue
        ROUND(
            TotalRevenue * 100.0
            / SUM(TotalRevenue) OVER (),
            4
        )                                          AS RevenuePct,

        -- Running cumulative revenue percentage (ordered by revenue desc)
        ROUND(
            SUM(TotalRevenue) OVER (
                ORDER BY TotalRevenue DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) * 100.0
            / SUM(TotalRevenue) OVER (),
            4
        )                                          AS CumulativeRevenuePct
    FROM product_revenue
),

-- ---------------------------------------------------------------------------
-- CTE 3: pareto_flagged
--   Flag each product as 'Top 10%' or 'Remaining 90%' using the rank and
--   total product count calculated in the previous CTE.
-- ---------------------------------------------------------------------------
pareto_flagged AS (
    SELECT
        *,
        -- Top 10% threshold: products whose rank falls within the top decile
        CASE
            WHEN RevenueRank <= CEIL(TotalProducts * 0.10)
            THEN 'Top 10%'
            ELSE 'Remaining 90%'
        END AS ParetoSegment
    FROM revenue_ranked
),

-- ---------------------------------------------------------------------------
-- CTE 4: pareto_summary
--   Aggregate the Pareto segments to produce the headline business insight.
-- ---------------------------------------------------------------------------
pareto_summary AS (
    SELECT
        ParetoSegment,
        COUNT(*)                         AS ProductCount,
        ROUND(SUM(TotalRevenue), 2)      AS SegmentRevenue,
        ROUND(SUM(RevenuePct), 2)        AS SegmentRevenuePct,
        SUM(TotalUnitsSold)              AS SegmentUnitsSold,
        SUM(NumberOfOrders)              AS SegmentOrders
    FROM pareto_flagged
    GROUP BY ParetoSegment
)

-- =============================================================================
--  FINAL OUTPUT (Section A): Per-product detail, limited to the Top 10%
--  Paste this into Excel to build the Pareto chart.
-- =============================================================================
SELECT
    pf.RevenueRank,
    pf.StockCode,
    pf.ProductDescription,
    pf.TotalUnitsSold,
    pf.TotalRevenue,
    pf.NumberOfOrders,
    pf.RevenuePct                    AS "Revenue %",
    pf.CumulativeRevenuePct          AS "Cumulative Revenue %",
    pf.ParetoSegment
FROM pareto_flagged pf
WHERE pf.ParetoSegment = 'Top 10%'
ORDER BY pf.RevenueRank;

-- =============================================================================
--  FINAL OUTPUT (Section B): Headline Pareto Summary
--  Demonstrates that the top 10% of SKUs drive ~60%+ of portfolio revenue.
-- =============================================================================
-- Uncomment the query below and run separately to view the summary table.

-- SELECT
--     ParetoSegment,
--     ProductCount,
--     SegmentRevenue,
--     SegmentRevenuePct  AS "% of Total Revenue",
--     SegmentUnitsSold,
--     SegmentOrders
-- FROM pareto_summary
-- ORDER BY ParetoSegment DESC;
