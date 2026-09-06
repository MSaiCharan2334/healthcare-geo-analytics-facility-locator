from pathlib import Path
import os

import pandas as pd
import mysql.connector
from dotenv import load_dotenv


# --------------------------------------------------
# Paths / environment
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

CSV_PATH = PROJECT_ROOT / "data" / "processed" / "cities.csv"


# --------------------------------------------------
# Read processed cities
# --------------------------------------------------

df = pd.read_csv(
    CSV_PATH,
    dtype={
        "city_id": str,
        "city_name": str,
        "city_name_original": str,
        "city_display": str,
        "city_display_unique": str,
        "state": str,
        "place_type": str,
        "place_type_code": str,
        "functional_status": str,
    },
)

print(f"Processed cities CSV rows: {len(df):,}")


# --------------------------------------------------
# Database connection
# --------------------------------------------------

connection = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)

cursor = connection.cursor()


# --------------------------------------------------
# Safety check — table must be empty
# --------------------------------------------------

cursor.execute("SELECT COUNT(*) FROM cities")
existing_rows = cursor.fetchone()[0]

if existing_rows != 0:
    cursor.close()
    connection.close()

    raise RuntimeError(
        f"Safety check failed: cities table already contains "
        f"{existing_rows:,} rows."
    )


# --------------------------------------------------
# Insert
# --------------------------------------------------

insert_sql = """
INSERT INTO cities (
    city_id,
    city_name,
    city_name_original,
    city_display,
    city_display_unique,
    state,
    place_type,
    place_type_code,
    functional_status,
    latitude,
    longitude
)
VALUES (
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s
)
"""


def clean_value(value):
    if pd.isna(value):
        return None
    return value


records = [
    tuple(clean_value(value) for value in row)
    for row in df[
        [
            "city_id",
            "city_name",
            "city_name_original",
            "city_display",
            "city_display_unique",
            "state",
            "place_type",
            "place_type_code",
            "functional_status",
            "latitude",
            "longitude",
        ]
    ].itertuples(index=False, name=None)
]

try:
    cursor.executemany(insert_sql, records)
    connection.commit()

    print(f"Rows inserted: {cursor.rowcount:,}")

    cursor.execute("SELECT COUNT(*) FROM cities")
    database_rows = cursor.fetchone()[0]

    print(f"Rows currently in MySQL cities table: {database_rows:,}")

    if database_rows != len(df):
        raise RuntimeError(
            f"Validation failed: CSV has {len(df):,} rows "
            f"but MySQL has {database_rows:,} rows."
        )

    print("Cities load row-count validation PASSED.")

except Exception:
    connection.rollback()
    raise

finally:
    cursor.close()
    connection.close()
    print("Database connection closed.")