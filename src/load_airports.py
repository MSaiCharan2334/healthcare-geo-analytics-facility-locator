from pathlib import Path
import os

import pandas as pd
import mysql.connector
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

CSV_PATH = PROJECT_ROOT / "data" / "processed" / "airports.csv"


# --------------------------------------------------
# Read processed airports
# --------------------------------------------------

df = pd.read_csv(
    CSV_PATH,
    dtype={
        "airport_id": str,
        "iata_code": str,
        "icao_code": str,
        "airport_ident": str,
        "airport_name": str,
        "airport_display": str,
        "city": str,
        "state": str,
        "airport_type": str,
        "scheduled_service": str,
    },
)

print(f"Processed airports CSV rows: {len(df):,}")


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
# Safety check
# --------------------------------------------------

cursor.execute("SELECT COUNT(*) FROM airports")
existing_rows = cursor.fetchone()[0]

if existing_rows != 0:
    cursor.close()
    connection.close()

    raise RuntimeError(
        f"Safety check failed: airports table already contains "
        f"{existing_rows:,} rows."
    )


# --------------------------------------------------
# Insert
# --------------------------------------------------

insert_sql = """
INSERT INTO airports (
    airport_id,
    iata_code,
    icao_code,
    airport_ident,
    airport_name,
    airport_display,
    city,
    state,
    airport_type,
    scheduled_service,
    latitude,
    longitude,
    elevation_ft
)
VALUES (
    %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s,
    %s, %s, %s
)
"""


def clean_value(value):
    if pd.isna(value):
        return None
    return value


columns = [
    "airport_id",
    "iata_code",
    "icao_code",
    "airport_ident",
    "airport_name",
    "airport_display",
    "city",
    "state",
    "airport_type",
    "scheduled_service",
    "latitude",
    "longitude",
    "elevation_ft",
]

records = [
    tuple(clean_value(value) for value in row)
    for row in df[columns].itertuples(index=False, name=None)
]

try:
    cursor.executemany(insert_sql, records)
    connection.commit()

    print(f"Rows inserted: {cursor.rowcount:,}")

    cursor.execute("SELECT COUNT(*) FROM airports")
    database_rows = cursor.fetchone()[0]

    print(f"Rows currently in MySQL airports table: {database_rows:,}")

    if database_rows != len(df):
        raise RuntimeError(
            f"Validation failed: CSV has {len(df):,} rows "
            f"but MySQL has {database_rows:,} rows."
        )

    print("Airports load row-count validation PASSED.")

except Exception:
    connection.rollback()
    raise

finally:
    cursor.close()
    connection.close()
    print("Database connection closed.")