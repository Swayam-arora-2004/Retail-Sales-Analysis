# 📊 Retail Sales Analysis | SQL · Excel · AI-Assisted

> End-to-end data pipeline and Pareto analysis on 500,000+ e-commerce transactions, demonstrating data engineering, advanced SQL, and business intelligence skills.

## Business Objective

A UK-based online retailer generates millions of transactions annually. This project answers one high-value commercial question:

> *"Which products disproportionately drive our revenue, and by how much?"*

Understanding revenue concentration allows a business to prioritise inventory procurement, renegotiate supplier contracts for high-value SKUs, and design targeted promotional strategies — each directly impacting margin.

## Dataset

| Attribute | Detail |
|---|---|
| **Source** | [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii) |
| **Scope** | UK-based online retailer, Dec 2009 – Dec 2011 |
| **Raw size** | ~1,067,371 rows across two annual sheets |
| **Post-cleaning** | ~750,000+ qualified transactions |
| **Unique products** | ~3,600 active SKUs |

## Technical Stack

- **Python 3.11** — `pandas`, `sqlite3`, `openpyxl`
- **SQLite** — lightweight analytical database
- **SQL** — CTEs, Window Functions (`RANK`, `SUM OVER`, `COUNT OVER`)
- **Excel** — Combo Pareto chart, PivotTables, Slicers, KPI dashboard

## Methodology

### 1. Data Engineering (`pipeline.py`)

The raw dataset is loaded from both annual Excel sheets, validated against an expected schema, and subjected to a multi-stage cleaning process:

| Stage | Action | Rows Removed (approx.) |
|---|---|---|
| Null Invoice / StockCode | Drop | ~5,000 |
| Cancellation invoices | Drop rows where Invoice starts with `"C"` | ~17,000 |
| Non-product stock codes | Regex filter `^\d{5,6}[A-Z]?$` | ~6,000 |
| Non-positive Quantity / Price | Drop `Quantity ≤ 0` or `Price ≤ 0` | ~11,000 |
| Missing CustomerID | Drop | ~240,000 |
| Exact duplicates | Drop | ~5,000+ |

A `LineRevenue` feature (`Quantity × Price`) is engineered during the pipeline and stored in the database, avoiding repeated computation at query time.

### 2. Analytical SQL (`pareto_analysis.sql`)

A four-stage CTE chain performs the Pareto segmentation entirely in SQL:

```
product_revenue → revenue_ranked → pareto_flagged → pareto_summary
(aggregate)        (rank + share)   (segment label)  (headline KPI)
```

Key SQL techniques:

- `RANK() OVER` — ordinal product ranking by descending revenue
- `SUM(...) OVER (ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` — cumulative revenue line
- `COUNT(*) OVER ()` — dynamic product count (adapts to any dataset size)
- `CEIL(TotalProducts * 0.10)` — dynamic 10% threshold, never hard-coded

### 3. Visualisation (Excel)

- **Pareto Combo Chart** — clustered bar (revenue per product) + cumulative % line
- **KPI Dashboard** — headline metrics with interactive slicers
- **Pivot Table** — revenue drill-down by product, filterable by Pareto segment

## Key Finding

> **The top ~10% of active SKUs account for approximately 60% of total portfolio revenue** — consistent with the Pareto Principle and commercially significant for inventory and merchandising strategy.

## How to Reproduce

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/retail-sales-analysis.git
cd retail-sales-analysis

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download the dataset and place it in the project root
#    https://archive.ics.uci.edu/dataset/502/online+retail+ii

# 4. Run the data pipeline
python pipeline.py

# 5. Export SQL results to Excel
python export_to_excel.py

# 6. Open pareto_output.xlsx in Excel and follow the dashboard guide
```

## Repository Structure

```
retail-sales-analysis/
├── pipeline.py            # ETL: cleans raw Excel → loads into SQLite
├── pareto_analysis.sql    # Pareto analysis: CTEs + Window Functions
├── export_to_excel.py     # Runs SQL and exports results to .xlsx
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Skills Demonstrated

`Data Cleaning` · `Data Modelling` · `SQL Window Functions` · `CTEs` · `Pareto / 80-20 Analysis` · `Business Intelligence` · `Excel Dashboard Design` · `Python (pandas · sqlite3)` · `Reproducible Research`

---

*Dataset: Dua, D. and Graff, C. (2019). UCI Machine Learning Repository. Irvine, CA: University of California, School of Information and Computer Science.*
