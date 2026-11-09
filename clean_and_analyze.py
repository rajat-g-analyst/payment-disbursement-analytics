"""
clean_and_analyze.py
Cleans the raw payment data, loads it into SQLite, runs SQL queries
and saves CSVs for Power BI.
"""

import os
import sqlite3
import pandas as pd

RAW_FILE = 'raw_payment_data.csv'
CLEAN_FILE = 'clean_payment_data.csv'
DB_FILE = 'payments.db'
OUTPUT_FOLDER = 'output'

# fixed demo rates (INR per 1 unit). Real analysis would use the rate of the payment date
RATES_TO_INR = {'INR': 1, 'USD': 83, 'EUR': 90}


def load_data(file_name):
    # pandas treats the text 'None' as missing by default,
    # but here 'None' means no exception, so keep it as text
    df = pd.read_csv(file_name, keep_default_na=False, na_values=[''])
    print(f"Loaded {len(df)} rows from {file_name}")
    return df


def clean_data(df):
    print("\nMissing values before cleaning:")
    print(df.isnull().sum()[df.isnull().sum() > 0])

    before = len(df)
    df = df.drop_duplicates()
    print(f"\nRemoved {before - len(df)} duplicate rows")

    # text to real dates, needed for the days calculation below
    date_columns = ['Submission_Date', 'Approval_Date', 'Value_Date']
    for col in date_columns:
        df[col] = pd.to_datetime(df[col])

    df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')

    # not guessing the status, so mark it Unknown
    df['Payment_Status'] = df['Payment_Status'].fillna('Unknown')

    # amounts are in different currencies, so convert to INR before adding them
    df['Amount_INR'] = (df['Amount'] * df['Currency'].map(RATES_TO_INR)).round(2)

    # approval cannot be before submission
    before = len(df)
    df = df[~(df['Approval_Date'] < df['Submission_Date'])]
    print(f"Removed {before - len(df)} rows with approval before submission")

    # value date cannot be before approval
    before = len(df)
    df = df[~(df['Value_Date'] < df['Approval_Date'])]
    print(f"Removed {before - len(df)} rows with value date before approval")

    # approval days: submission to approval
    # buffer days: approval to value date (how much time was left to pay)
    # both stay blank when there is no approval date
    df['Approval_Days'] = (df['Approval_Date'] - df['Submission_Date']).dt.days
    df['Buffer_Days'] = (df['Value_Date'] - df['Approval_Date']).dt.days

    print(f"Clean data has {len(df)} rows")
    return df


def save_to_database(df, db_file):
    conn = sqlite3.connect(db_file)

    # dates saved as text (YYYY-MM-DD) so SQL date functions work
    db_df = df.copy()
    for col in ['Submission_Date', 'Approval_Date', 'Value_Date']:
        db_df[col] = db_df[col].dt.strftime('%Y-%m-%d')

    db_df.to_sql('payments', conn, if_exists='replace', index=False)
    print(f"\nSaved clean data to table 'payments' in {db_file}")
    return conn


QUERIES = {

    # how many approved payments each method got processed
    'method_summary': """
        SELECT Payment_Method,
               COUNT(*) AS total_payments,
               SUM(CASE WHEN Approval_Status = 'Approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN Payment_Status = 'Processed' THEN 1 ELSE 0 END) AS processed,
               ROUND(100.0 * SUM(CASE WHEN Payment_Status = 'Processed' THEN 1 ELSE 0 END)
                     / SUM(CASE WHEN Approval_Status = 'Approved' THEN 1 ELSE 0 END), 2) AS processed_pct_of_approved
        FROM payments
        GROUP BY Payment_Method
    """,

    # % of payments with an exception, per method
    'exception_rate_by_method': """
        SELECT Payment_Method,
               COUNT(*) AS total_payments,
               SUM(CASE WHEN Exception_Type != 'None' THEN 1 ELSE 0 END) AS exceptions,
               ROUND(100.0 * SUM(CASE WHEN Exception_Type != 'None' THEN 1 ELSE 0 END)
                     / COUNT(*), 2) AS exception_rate_pct
        FROM payments
        GROUP BY Payment_Method
    """,

    # average days to approve, per region (approved payments only)
    'approval_days_by_region': """
        SELECT Region,
               COUNT(*) AS approved_payments,
               ROUND(AVG(Approval_Days), 2) AS avg_approval_days
        FROM payments
        WHERE Approval_Status = 'Approved'
        GROUP BY Region
        ORDER BY avg_approval_days DESC
    """,

    'exception_types': """
        SELECT Exception_Type, COUNT(*) AS total
        FROM payments
        WHERE Exception_Type != 'None'
        GROUP BY Exception_Type
        ORDER BY total DESC
    """,

    'approval_vs_payment_status': """
        SELECT Approval_Status, Payment_Status, COUNT(*) AS total
        FROM payments
        GROUP BY Approval_Status, Payment_Status
        ORDER BY Approval_Status, total DESC
    """,

    # approvals that took more than 3 days, per region
    'slow_approvals_by_region': """
        SELECT Region,
               COUNT(*) AS approved_payments,
               SUM(CASE WHEN Approval_Days > 3 THEN 1 ELSE 0 END) AS slow_approvals,
               ROUND(100.0 * SUM(CASE WHEN Approval_Days > 3 THEN 1 ELSE 0 END)
                     / COUNT(*), 2) AS slow_approval_pct
        FROM payments
        WHERE Approval_Status = 'Approved'
        GROUP BY Region
        ORDER BY slow_approval_pct DESC
    """,

    # payments per month, and change from the previous month (LAG)
    'monthly_trend': """
        SELECT month,
               total_payments,
               total_payments - LAG(total_payments) OVER (ORDER BY month) AS change_vs_prev_month
        FROM (
            SELECT strftime('%Y-%m', Submission_Date) AS month,
                   COUNT(*) AS total_payments
            FROM payments
            GROUP BY month
        )
        ORDER BY month
    """,

    # top 3 requestors in each region (RANK)
    'top_requestors_by_region': """
        SELECT Region, Requestor_ID, total_amount_inr, rank_in_region
        FROM (
            SELECT Region,
                   Requestor_ID,
                   ROUND(SUM(Amount_INR), 2) AS total_amount_inr,
                   RANK() OVER (PARTITION BY Region ORDER BY SUM(Amount_INR) DESC) AS rank_in_region
            FROM payments
            GROUP BY Region, Requestor_ID
        )
        WHERE rank_in_region <= 3
        ORDER BY Region, rank_in_region
    """,

    'top_beneficiaries': """
        SELECT Beneficiary_Name,
               Currency,
               COUNT(*) AS total_payments,
               ROUND(SUM(Amount_INR), 2) AS total_amount_inr
        FROM payments
        GROUP BY Beneficiary_Name, Currency
        ORDER BY total_amount_inr DESC
        LIMIT 5
    """,

    # what happens to payments with and without an exception
    'exception_vs_outcome': """
        SELECT CASE WHEN Exception_Type = 'None' THEN 'No exception' ELSE 'Exception' END AS exception_flag,
               COUNT(*) AS total_payments,
               ROUND(100.0 * SUM(CASE WHEN Approval_Status = 'Approved' THEN 1 ELSE 0 END) / COUNT(*), 2) AS approved_pct,
               ROUND(100.0 * SUM(CASE WHEN Approval_Status = 'On Hold' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_hold_pct,
               ROUND(100.0 * SUM(CASE WHEN Approval_Status = 'Rejected' THEN 1 ELSE 0 END) / COUNT(*), 2) AS rejected_pct
        FROM payments
        GROUP BY exception_flag
    """,
}


def run_queries(conn, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    for name, query in QUERIES.items():
        result = pd.read_sql(query, conn)
        result.to_csv(os.path.join(output_folder, f"{name}.csv"), index=False)
        print(f"\n--- {name} ---")
        print(result.to_string(index=False))


# runs all the steps in order
def main():
    df = load_data(RAW_FILE)
    df = clean_data(df)
    df.to_csv(CLEAN_FILE, index=False)
    conn = save_to_database(df, DB_FILE)
    run_queries(conn, OUTPUT_FOLDER)
    conn.close()
    print(f"\nDone! Clean data saved as {CLEAN_FILE}, query results saved in '{OUTPUT_FOLDER}' folder")


if __name__ == '__main__':
    main()