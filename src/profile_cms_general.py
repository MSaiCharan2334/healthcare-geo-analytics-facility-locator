from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "hospitals"
    / "cms_hospital_general.csv"
)


def profile_cms():
    # Keep identifiers and ZIP codes as strings
    df = pd.read_csv(
        INPUT_CSV,
        dtype={
            "Facility ID": "string",
            "ZIP Code": "string",
        },
    )

    print("=" * 60)
    print("CMS HOSPITAL GENERAL INFORMATION PROFILE")
    print("=" * 60)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print(f"Duplicate rows: {df.duplicated().sum():,}")

    print("\nColumns:")
    for col in df.columns:
        print(f" - {col}")

    important_columns = [
        "Facility ID",
        "Facility Name",
        "Address",
        "City/Town",
        "State",
        "ZIP Code",
        "County/Parish",
        "Hospital Type",
        "Hospital Ownership",
        "Emergency Services",
        "Hospital overall rating",
    ]

    print("\nImportant field null counts:")
    print("-" * 45)

    for col in important_columns:
        if col in df.columns:
            print(f"{col:<35}: {df[col].isna().sum():,}")

    print("\nDuplicate Facility IDs:")
    print(df["Facility ID"].duplicated().sum())

    print("\nHospital Types:")
    print(df["Hospital Type"].value_counts(dropna=False).to_string())

    print("\nStates / Territories:")
    print(df["State"].value_counts(dropna=False).sort_index().to_string())

    print("\nSample:")
    print(
        df[
            [
                "Facility ID",
                "Facility Name",
                "City/Town",
                "State",
                "ZIP Code",
                "Hospital Type",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    profile_cms()