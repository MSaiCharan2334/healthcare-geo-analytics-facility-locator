from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "cms_cost_report_canonical.csv"
)


def analyze_long_reports():

    print("=" * 70)
    print("CMS CANONICAL COST REPORT - LONG REPORT ANALYSIS")
    print("=" * 70)

    df = pd.read_csv(
        INPUT_FILE,
        dtype={"Provider CCN": "string"},
        low_memory=False,
    )

    df["Provider CCN"] = (
        df["Provider CCN"]
        .str.strip()
        .str.zfill(6)
    )

    df["Fiscal Year Begin Date"] = pd.to_datetime(
        df["Fiscal Year Begin Date"],
        errors="coerce",
    )

    df["Fiscal Year End Date"] = pd.to_datetime(
        df["Fiscal Year End Date"],
        errors="coerce",
    )

    # Recalculate to ensure accuracy
    df["report_days_check"] = (
        df["Fiscal Year End Date"]
        - df["Fiscal Year Begin Date"]
    ).dt.days + 1

    long_reports = df[
        df["report_days_check"] > 366
    ].copy()

    long_reports = long_reports.sort_values(
        "report_days_check",
        ascending=False,
    )

    print(f"\nCanonical rows: {len(df):,}")
    print(
        "Reports longer than 366 days:",
        len(long_reports),
    )

    print("\nDuration distribution:")
    print(
        long_reports["report_days_check"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    columns_to_show = [
        "Provider CCN",
        "rpt_rec_num",
        "Hospital Name",
        "State Code",
        "Provider Type",
        "Fiscal Year Begin Date",
        "Fiscal Year End Date",
        "report_days_check",
        "Number of Beds",
        "Total Patient Revenue",
        "Net Patient Revenue",
        "Total Costs",
        "Net Income",
    ]

    columns_to_show = [
        col
        for col in columns_to_show
        if col in long_reports.columns
    ]

    print("\nLong-report records:")
    print("-" * 70)

    print(
        long_reports[
            columns_to_show
        ].to_string(index=False)
    )


if __name__ == "__main__":
    analyze_long_reports()