WITH product_revenue AS (
    SELECT
        StockCode,
        MAX(Description)            AS ProductDescription,
        SUM(Quantity)               AS TotalUnitsSold,
        SUM(LineRevenue)            AS TotalRevenue,
        COUNT(DISTINCT Invoice)     AS NumberOfOrders
    FROM transactions
    GROUP BY StockCode
),
revenue_ranked AS (
    SELECT
        StockCode,
        ProductDescription,
        TotalUnitsSold,
        ROUND(TotalRevenue, 2)      AS TotalRevenue,
        NumberOfOrders,
        RANK() OVER (
            ORDER BY TotalRevenue DESC
        )                           AS RevenueRank,
        COUNT(*) OVER ()            AS TotalProducts,
        ROUND(
            TotalRevenue * 100.0 / SUM(TotalRevenue) OVER (),
            4
        )                           AS RevenuePct,
        ROUND(
            SUM(TotalRevenue) OVER (
                ORDER BY TotalRevenue DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) * 100.0 / SUM(TotalRevenue) OVER (),
            4
        )                           AS CumulativeRevenuePct
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
ORDER BY RevenueRank;
