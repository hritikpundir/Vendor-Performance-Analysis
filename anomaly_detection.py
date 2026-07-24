import pandas as pd
import numpy as np
import sqlite3
import logging

logging.basicConfig(
    filename="logs/anomaly_detection.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)


def flag_anomalies(df, column, threshold=2.5):
    """
    Flags rows where a column's value is unusually far from the mean,
    using a z-score. Adds two new columns: <column>_zscore and <column>_anomaly.

    threshold=2.5 means: flag anything more than 2.5 standard deviations
    away from the mean (roughly the top/bottom ~1% of values).
    """

    # Make sure the column is actually numeric before doing any math on it --
    # depending on how the database stored it, it can come back as text.
    # errors='coerce' turns anything that truly isn't a number into NaN
    # instead of crashing.
    df[column] = pd.to_numeric(df[column], errors='coerce')

    # Some rows have TotalSalesDollars = 0 (a brand was purchased but never sold),
    # which makes ProfitMargin mathematically undefined (-inf). These aren't
    # "statistical outliers" in the normal sense -- they're a different case
    # (zero-sales brands) and would otherwise break the mean/std calculation
    # for every other row. So we flag them separately and exclude them from
    # the z-score math.
    is_infinite = np.isinf(df[column])
    df[f'{column}_zero_sales_flag'] = is_infinite

    finite_values = df.loc[~is_infinite, column]
    mean_val = finite_values.mean()
    std_val = finite_values.std()

    # z-score = how many standard deviations this value is from the mean
    df[f'{column}_zscore'] = (df[column] - mean_val) / std_val
    df.loc[is_infinite, f'{column}_zscore'] = np.nan  # undefined for these rows

    # flag anything beyond the threshold, in either direction (excluding the inf rows)
    df[f'{column}_anomaly'] = (df[f'{column}_zscore'].abs() > threshold) & ~is_infinite

    return df


def run_anomaly_detection(conn):
    """Loads the vendor summary, flags anomalies on key KPIs, and saves results back."""

    logging.info('Loading vendor_sales_summary for anomaly detection')
    df = pd.read_sql_query("SELECT * FROM vendor_sales_summary", conn)

    # check for unusual profit margins (very high or very low)
    df = flag_anomalies(df, 'ProfitMargin', threshold=2.5)

    # check for unusual stock turnover (excess stock or unusually fast-selling)
    df = flag_anomalies(df, 'StockTurnover', threshold=2.5)

    # combine into a single flag: True if EITHER metric is a statistical anomaly
    df['IsAnomaly'] = df['ProfitMargin_anomaly'] | df['StockTurnover_anomaly']

    # zero-sales brands (purchased but never sold) are a separate, distinct issue
    df['IsZeroSalesBrand'] = df['ProfitMargin_zero_sales_flag']

    flagged = df[df['IsAnomaly']]
    zero_sales = df[df['IsZeroSalesBrand']]
    logging.info(f'Flagged {len(flagged)} statistical anomalies out of {len(df)}')
    logging.info(f'Found {len(zero_sales)} zero-sales (purchased-never-sold) rows')

    # save back to the database as a new table, so Power BI can read it separately
    df.to_sql('vendor_sales_summary_flagged', conn, if_exists='replace', index=False)

    return df, flagged


if __name__ == '__main__':
    conn = sqlite3.connect('inventory.db')

    logging.info('Starting anomaly detection...')
    full_df, flagged_rows = run_anomaly_detection(conn)

    zero_sales_rows = full_df[full_df['IsZeroSalesBrand']]

    print(f"Total rows: {len(full_df)}")
    print(f"Statistical anomalies flagged (ProfitMargin or StockTurnover z-score > 2.5): {len(flagged_rows)}")
    print(f"Zero-sales brands (purchased but never sold): {len(zero_sales_rows)}")
    print()
    print("Sample statistical anomalies:")
    print(flagged_rows[['VendorName', 'Description', 'ProfitMargin', 'StockTurnover']].head(10).to_string())
