import sqlite3
import pandas as pd
import logging
from ingestion_db import ingest_db

logging.basicConfig(
    filename="logs/get_vendor_summary.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)

def create_vendor_summary(conn):
    """This function will merge the different tables to get the overall vendor summary and adding new columns in the resultant data"""
    vendor_sales_summary = pd.read_sql_query("""
        WITH FreightSummary AS (
            SELECT
                VendorNumber,
                SUM(Freight) AS FreightCost
            FROM vendor_invoice
            GROUP BY VendorNumber
        ),
        PurchaseSummary AS (
            SELECT
                p.VendorNumber,
                p.VendorName,
                p.Brand,
                p.Description,
                p.PurchasePrice,
                pp.Price AS ActualPrice,
                pp.Volume,
                SUM(p.Quantity) AS TotalPurchaseQuantity,
                SUM(p.Dollars) AS TotalPurchaseDollars
            FROM purchases p
            JOIN purchase_prices pp
                ON p.Brand = pp.Brand
            WHERE p.PurchasePrice > 0
            GROUP BY
                p.VendorNumber,
                p.VendorName,
                p.Brand,
                p.Description,
                p.PurchasePrice,
                pp.Price,
                pp.Volume
        ),
        SalesSummary AS (
            SELECT
                VendorNo,
                Brand,
                SUM(SalesQuantity) AS TotalSalesQuantity,
                SUM(SalesDollars) AS TotalSalesDollars,
                SUM(SalesPrice) AS TotalSalesPrice,
                SUM(ExciseTax) AS TotalExciseTax
            FROM sales
            GROUP BY VendorNo, Brand
        )
        SELECT
            ps.VendorNumber,
            ps.VendorName,
            ps.Brand,
            ps.Description,
            ps.PurchasePrice,
            ps.ActualPrice,
            ps.Volume,
            ps.TotalPurchaseQuantity,
            ps.TotalPurchaseDollars,
            ss.TotalSalesQuantity,
            ss.TotalSalesDollars,
            ss.TotalSalesPrice,
            ss.TotalExciseTax,
            fs.FreightCost
        FROM PurchaseSummary ps
        LEFT JOIN SalesSummary ss
            ON ps.VendorNumber = ss.VendorNo
            AND ps.Brand = ss.Brand
        LEFT JOIN FreightSummary fs
            ON ps.VendorNumber = fs.VendorNumber
        ORDER BY ps.TotalPurchaseDollars DESC
    """, conn)
    
    return vendor_sales_summary





def clean_data(df):
    """
    This function cleans the vendor sales summary data
    and creates derived business metrics.
    """

    logging.info("Starting data cleaning process")

    # 1. Change datatype
    if 'Volume' in df.columns:
        df['Volume'] = df['Volume'].astype(float)

    # 2. Fill missing values
    df.fillna(0, inplace=True)

    # 3. Remove extra spaces from categorical columns
    if 'VendorName' in df.columns:
        df['VendorName'] = df['VendorName'].astype(str).str.strip()

    if 'Description' in df.columns:
        df['Description'] = df['Description'].astype(str).str.strip()

    # 4. Create new analytical columns

    # Gross Profit
    df['GrossProfit'] = (
        df['TotalSalesDollars'] - df['TotalPurchaseDollars']
    )

    # Profit Margin (%)
    df['ProfitMargin'] = (
        df['GrossProfit']
        / df['TotalSalesDollars'].replace(0, pd.NA)
    ) * 100

    # Stock Turnover
    df['StockTurnover'] = (
        df['TotalSalesQuantity']
        / df['TotalPurchaseQuantity'].replace(0, pd.NA)
    )

    # Sales to Purchase Ratio
    df['SalesToPurchaseRatio'] = (
        df['TotalSalesDollars']
        / df['TotalPurchaseDollars'].replace(0, pd.NA)
    )

    logging.info("Data cleaning process completed successfully")

    return df

if __name__ == '__main__':

    # creating database connection
    conn = sqlite3.connect('inventory.db')

    logging.info('Creating Vendor Summary Table.....')
    summary_df = create_vendor_summary(conn)
    logging.info(summary_df.head())

    logging.info('Cleaning Data....')
    clean_df = clean_data(summary_df)
    logging.info(clean_df.head())

    logging.info('Ingesting data....')
    ingest_db('vendor_sales_summary', clean_df, conn)
    logging.info('Completed')
