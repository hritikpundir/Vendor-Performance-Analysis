"""
Vendor Risk Classifier
----------------------
Predicts whether a vendor-brand is likely to become "low-performing"
(low profit margin / zero sales) using ONLY purchase-side and pricing
information -- i.e. signals available before we know how well something
actually sold. This is the useful, non-circular version of the question:
"can we flag risk early, from purchasing behavior alone?"

We deliberately do NOT use ProfitMargin, StockTurnover, TotalSalesDollars,
GrossProfit, or SalesToPurchaseRatio as *features* -- those are what
define the label itself, so including them would be data leakage
(the model would just be re-reading the answer).
"""

import pandas as pd
import numpy as np
import sqlite3
import logging
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score

logging.basicConfig(
    filename="logs/vendor_risk_classifier.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)


def build_target(df):
    """
    Defines the label we're trying to predict: AtRisk = 1 if a
    vendor-brand is a poor performer.

    A row counts as AtRisk if EITHER:
      - it had zero sales (ProfitMargin is -inf -- purchased but never sold), OR
      - its ProfitMargin falls in the bottom 25% of all rows that DID sell
    """
    df['ProfitMargin'] = pd.to_numeric(df['ProfitMargin'], errors='coerce')

    is_zero_sales = np.isinf(df['ProfitMargin'])

    finite_margins = df.loc[~is_zero_sales, 'ProfitMargin']
    low_margin_threshold = finite_margins.quantile(0.25)

    is_low_margin = (~is_zero_sales) & (df['ProfitMargin'] <= low_margin_threshold)

    df['AtRisk'] = (is_zero_sales | is_low_margin).astype(int)
    return df, low_margin_threshold


def build_features(df):
    """
    Purchase-side / pricing features only -- available BEFORE sales
    performance is known, so predicting from these is a genuinely
    forward-looking (not circular) exercise.
    """
    features = pd.DataFrame()
    features['PurchasePrice'] = df['PurchasePrice']
    features['ActualPrice'] = df['ActualPrice']
    features['Volume'] = df['Volume']
    features['FreightCost'] = df['FreightCost']
    features['TotalPurchaseQuantity'] = df['TotalPurchaseQuantity']
    features['TotalPurchaseDollars'] = df['TotalPurchaseDollars']
    # markup: how much room there is between what vendor paid and list price
    features['PriceMarkup'] = df['ActualPrice'] - df['PurchasePrice']
    return features


def run_classifier(conn):
    logging.info('Loading vendor_sales_summary for risk classification')
    df = pd.read_sql_query("SELECT * FROM vendor_sales_summary", conn)

    df, threshold = build_target(df)
    logging.info(f'Low-margin threshold (25th percentile, finite rows only): {threshold:.2f}')
    logging.info(f"AtRisk distribution:\n{df['AtRisk'].value_counts()}")

    X = build_features(df)
    y = df['AtRisk']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # scale features -- logistic regression is sensitive to feature scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, class_weight='balanced')
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    report = classification_report(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    logging.info(f'Classification report:\n{report}')
    logging.info(f'Confusion matrix:\n{cm}')
    logging.info(f'ROC-AUC: {auc:.3f}')

    # feature importance: which purchase-side signals matter most
    coefficients = pd.Series(model.coef_[0], index=X.columns).sort_values(key=abs, ascending=False)

    # score EVERY row (not just test set) and save back to the database
    X_all_scaled = scaler.transform(X)
    df['RiskProbability'] = model.predict_proba(X_all_scaled)[:, 1]
    df['PredictedAtRisk'] = model.predict(X_all_scaled)

    df.to_sql('vendor_risk_predictions', conn, if_exists='replace', index=False)

    df.to_csv('vendor_risk_predictions.csv', index=False)

    return df, report, cm, auc, coefficients, threshold


if __name__ == '__main__':
    conn = sqlite3.connect('inventory.db')

    result_df, report, cm, auc, coefficients, threshold = run_classifier(conn)

    print(f"Low-margin threshold used to define 'AtRisk': {threshold:.2f}%")
    print(f"Total rows: {len(result_df)} | AtRisk rows: {result_df['AtRisk'].sum()} "
          f"({result_df['AtRisk'].mean()*100:.1f}%)")
    print()
    print("=== Classification Report (test set) ===")
    print(report)
    print("Confusion Matrix (test set):")
    print(cm)
    print(f"\nROC-AUC: {auc:.3f}")
    print()
    print("=== Feature importance (standardized coefficients) ===")
    print(coefficients.to_string())
    print()
    print("=== Sample of highest-risk vendor-brands (by predicted probability) ===")
    top_risk = result_df.sort_values('RiskProbability', ascending=False)[
        ['VendorName', 'Description', 'PurchasePrice', 'ActualPrice', 'FreightCost', 'RiskProbability']
    ].head(10)
    print(top_risk.to_string())
