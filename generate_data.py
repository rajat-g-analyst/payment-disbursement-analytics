"""
generate_data.py
Makes fake payment data for my SQL + Python + Power BI project.
Real MIS data is confidential, so everything here is made up.
"""

import os
import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import timedelta, date

# fixed seed, so I get the same data every run
Faker.seed(42)
random.seed(42)
np.random.seed(42)

fake = Faker()

NUM_ROWS = 12000
RAW_FOLDER = 'raw_data'

payment_methods = ['H2H', 'Manual']
regions = ['North', 'South', 'East', 'West']

approval_statuses = ['Approved', 'On Hold', 'Rejected']
approval_weights = {
    'None':            [90, 5, 5],
    'Duplicate':       [50, 15, 35],
    'Amount Mismatch': [55, 35, 10],
    'Wrong Details':   [50, 20, 30],
}

processing_statuses = ['Processed', 'Rejected', 'On Hold']
processing_weights = {
    'H2H':    {'clean': [95, 2, 3],  'exception': [75, 12, 13]},
    'Manual': {'clean': [88, 5, 7],  'exception': [65, 18, 17]},
}

# Manual has more exceptions because details are typed by hand
exception_types = ['None', 'Duplicate', 'Amount Mismatch', 'Wrong Details']
exception_weights = {
    'H2H':    [91, 3, 4, 2],
    'Manual': [78, 6, 7, 9],
}

currency_list = ['INR', 'USD', 'EUR']
currency_weights = [60, 25, 15]
amount_ranges = {'INR': (5000, 500000), 'USD': (100, 10000), 'EUR': (100, 10000)}

beneficiaries = {}
for _ in range(150):
    name = fake.unique.company()
    beneficiaries[name] = random.choices(currency_list, weights=currency_weights, k=1)[0]
beneficiary_names = list(beneficiaries.keys())

requestor_ids = [f"USR{n}" for n in range(1000, 1201)]
requestor_region = {r: random.choice(regions) for r in requestor_ids}

columns = [
    'Request_ID', 'Requestor_ID', 'Beneficiary_Name', 'Submission_Date', 'Approval_Date', 'Value_Date',
    'Payment_Method', 'Batch_ID', 'Approval_Status', 'Payment_Status',
    'Amount', 'Currency', 'Exception_Type', 'Region'
]


# makes payment requests submitted between start_date and end_date
# (also used by generate_new_month.py)
def generate_rows(num_rows, start_date, end_date, first_id):
    rows = []

    for i in range(num_rows):

        request_id = f"REQ{first_id + i}"
        requestor_id = random.choice(requestor_ids)
        region = requestor_region[requestor_id]
        batch_id = f"BATCH{random.randint(1, 300)}"

        beneficiary_name = random.choice(beneficiary_names)
        currency = beneficiaries[beneficiary_name]
        low, high = amount_ranges[currency]
        amount = round(random.uniform(low, high), 2)
        payment_method = random.choice(payment_methods)

        # payment created
        submission_date = fake.date_between(start_date=start_date, end_date=end_date)

        exception_type = random.choices(
            exception_types, weights=exception_weights[payment_method], k=1
        )[0]

        approval_status = random.choices(
            approval_statuses, weights=approval_weights[exception_type], k=1
        )[0]

        if approval_status == 'Approved':
            # East approvals take longer
            approval_gap = random.randint(0, 4)
            if region == 'East':
                approval_gap += random.randint(1, 3)
            approval_date = submission_date + timedelta(days=approval_gap)

            value_date = approval_date + timedelta(days=random.randint(0, 5))

            # processor result, only for approved payments
            kind = 'clean' if exception_type == 'None' else 'exception'
            payment_status = random.choices(
                processing_statuses, weights=processing_weights[payment_method][kind], k=1
            )[0]

        else:
            approval_date = None
            value_date = submission_date + timedelta(days=random.randint(1, 7))
            payment_status = 'Not Applicable'

        rows.append([
            request_id, requestor_id, beneficiary_name, submission_date, approval_date, value_date,
            payment_method, batch_id, approval_status, payment_status,
            amount, currency, exception_type, region
        ])

    return pd.DataFrame(rows, columns=columns)


# adds some mess on purpose, so the cleaning script has something to fix
def add_mess(df):
    # 3% of payment status left blank, approved rows only
    approved_rows = df[df['Approval_Status'] == 'Approved']
    missing_indices = approved_rows.sample(frac=0.03, random_state=1).index
    df.loc[missing_indices, 'Payment_Status'] = np.nan

    # 1% duplicate rows
    duplicate_rows = df.sample(frac=0.01, random_state=3)
    df = pd.concat([df, duplicate_rows], ignore_index=True)
    return df


def main():
    df = generate_rows(NUM_ROWS, date(2025, 1, 1), date(2026, 6, 30), 100000)
    df = add_mess(df)

    os.makedirs(RAW_FOLDER, exist_ok=True)

    # remove old monthly files, so every run starts fresh
    for file_name in os.listdir(RAW_FOLDER):
        if file_name.startswith('raw_') and file_name.endswith('.csv'):
            os.remove(os.path.join(RAW_FOLDER, file_name))

    # one file per submission month, like raw_2025_01.csv
    df['month_key'] = pd.to_datetime(df['Submission_Date']).dt.strftime('%Y_%m')
    for month, month_df in df.groupby('month_key'):
        month_df = month_df.drop(columns='month_key')
        month_df.to_csv(os.path.join(RAW_FOLDER, f"raw_{month}.csv"), index=False)

    print(f"Done! Generated {len(df)} rows (including some intentional duplicates and missing values).")
    print(f"Saved as one file per month in the '{RAW_FOLDER}' folder")


if __name__ == '__main__':
    main()