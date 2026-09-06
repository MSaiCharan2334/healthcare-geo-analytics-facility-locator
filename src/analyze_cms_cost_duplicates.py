from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "hospitals"
    / "cms_hospital_cost_report_2023.csv"
)


def analyze_duplicates():

    print("=" * 70)
    print("CMS COST REPORT - DUPLICATE CCN ANALYSIS")
    print("=" * 70)

    df = pd.read_csv(
        INPUT_FILE,
        dtype={"Provider CCN": "string"},
        low_memory=False,
    )

    # Preserve six-digit CCNs
    df["Provider CCN"] = (
        df["Provider CCN"]
        .str.strip()
        .str.zfill(6)
    )

    # Convert fiscal dates
    df["Fiscal Year Begin Date"] = pd.to_datetime(
        df["Fiscal Year Begin Date"],
        errors="coerce",
    )

    df["Fiscal Year End Date"] = pd.to_datetime(
        df["Fiscal Year End Date"],
        errors="coerce",
    )

    # Report duration
    df["report_days"] = (
        df["Fiscal Year End Date"]
        - df["Fiscal Year Begin Date"]
    ).dt.days + 1

    # Count populated fields as a rough completeness score
    df["non_null_fields"] = df.notna().sum(axis=1)

    # --------------------------------------------------------
    # Find duplicated CCNs
    # --------------------------------------------------------

    duplicate_mask = df["Provider CCN"].duplicated(
        keep=False
    )

    duplicates = df[
        duplicate_mask
    ].copy()

    duplicate_ccns = (
        duplicates["Provider CCN"]
        .nunique()
    )

    print(f"\nTotal rows: {len(df):,}")
    print(
        f"Unique Provider CCNs: "
        f"{df['Provider CCN'].nunique():,}"
    )

    print(
        f"CCNs appearing more than once: "
        f"{duplicate_ccns:,}"
    )

    print(
        f"Rows belonging to duplicate CCNs: "
        f"{len(duplicates):,}"
    )

    # --------------------------------------------------------
    # Number of records per duplicated CCN
    # --------------------------------------------------------

    print("\nRecords per duplicated CCN:")
    print("-" * 70)

    print(
        duplicates["Provider CCN"]
        .value_counts()
        .value_counts()
        .sort_index()
        .rename_axis("records_per_ccn")
        .to_frame("number_of_ccns")
        .to_string()
    )

    # --------------------------------------------------------
    # Useful comparison fields
    # --------------------------------------------------------

    columns_to_show = [
        "Provider CCN",
        "rpt_rec_num",
        "Hospital Name",
        "State Code",
        "Fiscal Year Begin Date",
        "Fiscal Year End Date",
        "report_days",
        "Number of Beds",
        "Total Patient Revenue",
        "Net Patient Revenue",
        "Total Costs",
        "Net Income",
        "non_null_fields",
    ]

    columns_to_show = [
        column
        for column in columns_to_show
        if column in duplicates.columns
    ]

    duplicates = duplicates.sort_values(
        [
            "Provider CCN",
            "Fiscal Year End Date",
        ]
    )

    print("\nDuplicate records:")
    print("-" * 70)

    print(
        duplicates[
            columns_to_show
        ].to_string(index=False)
    )

    # --------------------------------------------------------
    # Check fiscal period characteristics
    # --------------------------------------------------------

    print("\nReport-duration distribution among duplicates:")
    print("-" * 70)

    print(
        duplicates["report_days"]
        .describe()
        .to_string()
    )

    print("\nDuplicate CCNs with different hospital names:")
    print("-" * 70)

    name_counts = (
        duplicates
        .groupby("Provider CCN")["Hospital Name"]
        .nunique()
    )

    different_names = name_counts[
        name_counts > 1
    ]

    print(
        f"Count: {len(different_names):,}"
    )

    if len(different_names) > 0:
        print(
            different_names.to_string()
        )


if __name__ == "__main__":
    analyze_duplicates()