"""
generate_new_month.py
The data is fake, same as generate_data.py.
"""

import os
import random
from datetime import date, timedelta

import pandas as pd
from faker import Faker

from generate_data import generate_rows, add_mess, RAW_FOLDER

NEW_MONTH_ROWS = 650


def monthly_files():
    return sorted(
        f for f in os.listdir(RAW_FOLDER)
        if f.startswith('raw_') and f.endswith('.csv')
    )

def next_month():
    last_file = monthly_files()[-1]
    year = int(last_file[4:8])
    month = int(last_file[9:11])
    if month == 12:
        return year + 1, 1
    return year, month + 1


def last_request_number():
    ids = pd.concat(
        [pd.read_csv(os.path.join(RAW_FOLDER, f), usecols=['Request_ID']) for f in monthly_files()]
    )
    return ids['Request_ID'].str[3:].astype(int).max()


def main():
    year, month = next_month()
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year, 12, 31)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    # different seed for each month, so months are not copies of each other
    seed = year * 100 + month
    random.seed(seed)
    Faker.seed(seed)

    df = generate_rows(NEW_MONTH_ROWS, start_date, end_date, last_request_number() + 1)
    df = add_mess(df)

    file_name = f"raw_{year}_{month:02d}.csv"
    df.to_csv(os.path.join(RAW_FOLDER, file_name), index=False)
    print(f"Created {file_name} with {len(df)} rows")


if __name__ == '__main__':
    main()