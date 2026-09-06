from pathlib import Path
import os
from datetime import datetime

import pandas as pd
import mysql.connector
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

CSV_PATH = PROJECT_ROOT / "data" / "processed" / "hospitals.csv"


# --------------------------------------------------
# Read processed hospitals
# --------------------------------------------------

df = pd.read_csv(
    CSV_PATH,
    dtype={
        "hospital_id": str,
        "ccn": str,
        "hospital_name": str,
        "address": str,
        "city": str,
        "state": str,
        "zip_code": str,
        "county": str,
        "country_code": str,
        "telephone": str,
        "website": str,
        "hospital_type": str,
        "ownership": str,
        "status": str,
        "emergency_services": str,
        "trauma_level": str,
        "helipad": str,
        "bed_source": str,
        "provider_type": str,
        "ccn_facility_type": str,
        "type_of_control": str,
        "rural_urban": str,
        "data_source_coverage": str,
        "cms_source_status": str,
        "match_type": str,
        "hifld_source": str,
        "hifld_source_date": str,
    },
)

print(f"Processed hospitals CSV rows: {len(df):,}")


# --------------------------------------------------
# Convert date fields
# --------------------------------------------------

date_columns = [
    "fiscal_year_begin",
    "fiscal_year_end",
]

for column in date_columns:
    df[column] = pd.to_datetime(
        df[column],
        errors="coerce"
    ).dt.date


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

cursor.execute("SELECT COUNT(*) FROM hospitals")
existing_rows = cursor.fetchone()[0]

if existing_rows != 0:
    cursor.close()
    connection.close()

    raise RuntimeError(
        f"Safety check failed: hospitals table already contains "
        f"{existing_rows:,} rows."
    )


# --------------------------------------------------
# Column order must match MySQL hospitals table
# --------------------------------------------------

columns = [
    "hospital_id",
    "ccn",
    "hospital_name",
    "address",
    "city",
    "state",
    "zip_code",
    "county",
    "country_code",
    "telephone",
    "website",
    "latitude",
    "longitude",
    "hospital_type",
    "ownership",
    "status",
    "is_open",
    "emergency_services",
    "trauma_level",
    "helipad",
    "beds",
    "bed_source",
    "cms_beds",
    "hifld_beds",
    "overall_rating",
    "provider_type",
    "ccn_facility_type",
    "type_of_control",
    "rural_urban",
    "fiscal_year_begin",
    "fiscal_year_end",
    "report_days",
    "fte_employees",
    "inpatient_revenue",
    "outpatient_revenue",
    "total_patient_revenue",
    "net_patient_revenue",
    "total_costs",
    "net_income",
    "cost_to_charge_ratio",
    "charity_care_cost",
    "uncompensated_care_cost",
    "medicare_days",
    "medicare_discharges",
    "medicaid_days",
    "medicaid_discharges",
    "medicaid_net_revenue",
    "medicaid_charges",
    "data_source_coverage",
    "cms_source_status",
    "match_type",
    "match_score",
    "hifld_source",
    "hifld_source_date",
]


# --------------------------------------------------
# Verify CSV contains every expected column
# --------------------------------------------------

missing_columns = [
    column for column in columns
    if column not in df.columns
]

if missing_columns:
    cursor.close()
    connection.close()

    raise RuntimeError(
        f"Missing expected CSV columns: {missing_columns}"
    )


# --------------------------------------------------
# Insert SQL
# --------------------------------------------------

column_sql = ",\n    ".join(columns)
placeholder_sql = ", ".join(["%s"] * len(columns))

insert_sql = f"""
INSERT INTO hospitals (
    {column_sql}
)
VALUES (
    {placeholder_sql}
)
"""


# --------------------------------------------------
# Clean pandas / numpy values for MySQL
# --------------------------------------------------

def clean_value(value):

    if pd.isna(value):
        return None

    # Convert numpy scalar types to normal Python scalars
    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, AttributeError):
            pass

    return value


records = [
    tuple(clean_value(value) for value in row)
    for row in df[columns].itertuples(
        index=False,
        name=None
    )
]


# --------------------------------------------------
# Load
# --------------------------------------------------

try:
    cursor.executemany(insert_sql, records)

    connection.commit()

    print(f"Rows inserted: {cursor.rowcount:,}")

    cursor.execute("SELECT COUNT(*) FROM hospitals")
    database_rows = cursor.fetchone()[0]

    print(
        f"Rows currently in MySQL hospitals table: "
        f"{database_rows:,}"
    )

    if database_rows != len(df):
        raise RuntimeError(
            f"Validation failed: CSV has {len(df):,} rows "
            f"but MySQL has {database_rows:,} rows."
        )

    print("Hospitals load row-count validation PASSED.")

except Exception:
    connection.rollback()
    raise

finally:
    cursor.close()
    connection.close()
    print("Database connection closed.")