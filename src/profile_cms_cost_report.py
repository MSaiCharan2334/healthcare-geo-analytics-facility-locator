from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "hospitals"
    / "cms_hospital_cost_report_2023.csv"
)


def profile_cost_report():
    # Read once to inspect exact headers
    df = pd.read_csv(INPUT_CSV, low_memory=False)

    print("=" * 70)
    print("CMS HOSPITAL COST REPORT 2023 PROFILE")
    print("=" * 70)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print(f"Duplicate rows: {df.duplicated().sum():,}")

    print("\nColumns:")
    for col in df.columns:
        print(f" - {col}")

    # Try to locate the CCN column safely
    ccn_candidates = [
        "Provider CCN",
        "Provider Number",
        "CMS Certification Number",
        "CCN",
    ]

    ccn_col = next(
        (col for col in ccn_candidates if col in df.columns),
        None
    )

    if ccn_col:
        df[ccn_col] = (
            df[ccn_col]
            .astype("string")
            .str.strip()
            .str.zfill(6)
        )

        print(f"\nDetected CCN column: {ccn_col}")
        print(f"Null CCNs: {df[ccn_col].isna().sum():,}")
        print(f"Duplicate CCNs: {df[ccn_col].duplicated().sum():,}")
    else:
        print("\nWARNING: Could not automatically identify CCN column.")

    important_fields = [
        "Provider CCN",
        "Hospital Name",
        "Street Address",
        "City",
        "State Code",
        "Zip Code",
        "Provider Type",
        "Number of Beds",
        "Inpatient Revenue",
        "Outpatient Revenue",
        "Total Patient Revenue",
        "Net Patient Revenue",
        "Net Income",
        "Total Costs",
        "Cost To Charge Ratio",
        "Net Revenue from Medicaid",
    ]

    print("\nImportant-field availability / null counts:")
    print("-" * 60)

    for col in important_fields:
        if col in df.columns:
            print(f"{col:<45}: {df[col].isna().sum():,}")
        else:
            print(f"{col:<45}: NOT FOUND")

    print("\nPotential Medicare / Medicaid columns:")
    for col in df.columns:
        if (
            "medicare" in col.lower()
            or "medicaid" in col.lower()
        ):
            print(f" - {col}")

    print("\nPotential revenue / financial columns:")
    for col in df.columns:
        if any(
            term in col.lower()
            for term in [
                "revenue",
                "income",
                "cost",
                "charge",
                "expense",
                "asset",
                "liabil",
            ]
        ):
            print(f" - {col}")

    print("\nSample:")
    print(df.head(5).to_string())


if __name__ == "__main__":
    profile_cost_report()
    