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
1. **Ingestion** (`ingestion_db.py`) — loads all CSVs in `data/` into SQLite
2. **Summary build** (`get_vendor_summary.py`) — SQL CTEs join purchases, 
   sales, and freight per vendor/brand
3. **Cleaning & feature engineering** — derives KPIs below, handles nulls, 
   strips whitespace
4. **Exploratory analysis & hypothesis testing** (Jupyter notebook)
5. **Dashboard** — Power BI report built on the cleaned summary table

## KPIs
| KPI | Definition |
|---|---|
| Total Sales | Sum of `TotalSalesDollars` |
| Total Purchase | Sum of `TotalPurchaseDollars` |
| Gross Profit | Total Sales − Total Purchase |
| Profit Margin (%) | Gross Profit / Total Sales × 100 |
| Unsold Capital | (Purchase Qty − Sales Qty) × Purchase Price, summed per vendor |
| Stock Turnover *(supporting metric)* | Sales Qty / Purchase Qty |

## Dashboard
![Dashboard](Vendor_Sales_Analysis_Dashboard.png)

- Total Sales: **$441.41M** | Total Purchase: **$307.34M** | Gross Profit: 
  **$134.07M** | Unsold Capital: **$2.71M**
- Top vendor by sales: Diageo North America (~$68M); top brand: Jack Daniel's 
  No. 7 (~$8.0M)

## Key Insights
- **Vendor concentration (Pareto analysis):** a small set of top vendors 
  accounts for the large majority of total purchase spend — visualized with 
  a cumulative contribution chart and donut breakdown.
- **Low-turnover vendors flagged:** vendors with Stock Turnover < 1 (selling 
  slower than they're restocking) were identified as carrying excess/slow-moving 
  inventory — the biggest driver of the $2.71M unsold capital figure.
- **Bulk purchasing lowers unit price:** vendors buying in larger order sizes 
  get a measurably lower average unit purchase price (boxplot comparison across 
  Small/Medium/Large order tiers).
- **High-margin, low-sales brands identified:** brands in the bottom 15th 
  percentile of sales but top 85th percentile of profit margin were flagged as 
  candidates for pricing/promotional review.
- **Statistical test — top vs. low-performing vendors:** split vendors into 
  top and bottom quartile by sales, computed 95% confidence intervals for 
  profit margin in each group, then ran a Welch's two-sample t-test. 
  **Result: p < 0.05** — low-sales vendors have a significantly *higher* 
  average profit margin (~40–43% CI) than high-sales vendors (~31–32% CI), 
  suggesting premium pricing or lower overhead rather than volume drives their 
  margin.

## Repo Structure