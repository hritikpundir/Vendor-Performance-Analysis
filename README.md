# Vendor Performance Analysis

An end-to-end analysis of vendor and brand performance for a retail/distribution 
dataset, built with SQL, Python, and Power BI. Goes beyond dashboarding — 
includes percentile-based outlier detection and a two-sample hypothesis test 
to check whether high-volume and low-volume vendors differ significantly in 
profit margin.

## Tools Used
- **SQL** (SQLite) — data storage and aggregation via CTEs
- **Python** — pandas, SQLAlchemy for ingestion; matplotlib/seaborn for EDA; 
  scipy for statistical testing
- **Power BI** — interactive dashboard

## Data
Six source tables: `purchases`, `purchase_prices`, `sales`, `vendor_invoice`, 
`begin_inventory`, `end_inventory` — ingested from CSV into a SQLite database 
(`inventory.db`), then merged into a single `vendor_sales_summary` table 
(10,692 rows, 128 vendors) via a multi-CTE SQL query joining purchase, sales, 
and freight data at the vendor-brand level.

## Workflow
1. Data ingestion
2. SQL querying
3. Data cleaning
4. Dashboard creation

## Dashboard
(Add dashboard screenshot here)

## Key Insights
- Top vendors by sales
- Low-performing vendors
- Brand-level performance
- Profitability analysis