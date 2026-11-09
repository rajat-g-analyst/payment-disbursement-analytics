"""
generate_data.py
Makes fake payment data for my SQL + Python + Power BI project.
Real MIS data is confidential, so everything here is made up.
"""

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

rows = []

for i in range(NUM_ROWS):

    request_id = f"REQ{100000 + i}"
    requestor_id = random.choice(requestor_ids)
    region = requestor_region[requestor_id]
    batch_id = f"BATCH{random.randint(1, 300)}"

    beneficiary_name = random.choice(beneficiary_names)
    currency = beneficiaries[beneficiary_name]
    low, high = amount_ranges[currency]
    amount = round(random.uniform(low, high), 2)
    payment_method = random.choice(payment_methods)

    # payment created: 18 months of data, Jan 2025 to Jun 2026
    submission_date = fake.date_between(start_date=date(2025, 1, 1), end_date=date(2026, 6, 30))

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

columns = [
    'Request_ID', 'Requestor_ID', 'Beneficiary_Name', 'Submission_Date', 'Approval_Date', 'Value_Date',
    'Payment_Method', 'Batch_ID', 'Approval_Status', 'Payment_Status',
    'Amount', 'Currency', 'Exception_Type', 'Region'
]

df = pd.DataFrame(rows, columns=columns)

# 3% of payment status left blank, approved rows only
approved_rows = df[df['Approval_Status'] == 'Approved']
missing_indices = approved_rows.sample(frac=0.03, random_state=1).index
df.loc[missing_indices, 'Payment_Status'] = np.nan

# 1% duplicate rows
duplicate_rows = df.sample(frac=0.01, random_state=3)
df = pd.concat([df, duplicate_rows], ignore_index=True)

df.to_csv('raw_payment_data.csv', index=False)

print(f"Done! Generated {len(df)} rows (including some intentional duplicates and missing values).")
print("Saved as raw_payment_data.csv")