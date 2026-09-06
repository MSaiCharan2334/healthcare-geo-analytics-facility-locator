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

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "cms_cost_report_canonical.csv"
)


def create_canonical_cost_report():

    print("=" * 70)
    print("CREATING CANONICAL CMS COST REPORT")
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

    # Convert dates
    df["Fiscal Year Begin Date"] = pd.to_datetime(
        df["Fiscal Year Begin Date"],
        errors="coerce",
    )

    df["Fiscal Year End Date"] = pd.to_datetime(
        df["Fiscal Year End Date"],
        errors="coerce",
    )

    # Calculate report duration
    report_days = (
        df["Fiscal Year End Date"]
        - df["Fiscal Year Begin Date"]
    ).dt.days + 1

    # Count populated fields
    non_null_fields = df.notna().sum(axis=1)

    # Add temporary ranking columns in one operation
    df = df.assign(
        report_days=report_days,
        non_null_fields=non_null_fields,
    )

    print(f"Raw rows: {len(df):,}")
    print(
        f"Unique CCNs before canonicalization: "
        f"{df['Provider CCN'].nunique():,}"
    )

    # --------------------------------------------------------
    # Rank records within each CCN
    #
    # Priority:
    # 1. longest reporting period
    # 2. latest fiscal year end
    # 3. most complete record
    # 4. highest report record number
    # --------------------------------------------------------

    ranked = df.sort_values(
        by=[
            "Provider CCN",
            "report_days",
            "Fiscal Year End Date",
            "non_null_fields",
            "rpt_rec_num",
        ],
        ascending=[
            True,
            False,
            False,
            False,
            False,
        ],
    )

    canonical = ranked.drop_duplicates(
        subset=["Provider CCN"],
        keep="first",
    ).copy()

    canonical = canonical.sort_values(
        "Provider CCN"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 70)

    print(
        f"Canonical rows: "
        f"{len(canonical):,}"
    )

    print(
        "Duplicate CCNs remaining:",
        canonical["Provider CCN"]
        .duplicated()
        .sum(),
    )

    print(
        "Missing CCNs:",
        canonical["Provider CCN"]
        .isna()
        .sum(),
    )

    print(
        "\nSelected report-duration distribution:"
    )

    print(
        canonical["report_days"]
        .describe()
        .to_string()
    )

    print(
        "\nSelected records by report length:"
    )

    bins = pd.cut(
        canonical["report_days"],
        bins=[
            0,
            90,
            180,
            270,
            364,
            366,
        ],
        labels=[
            "<=90 days",
            "91-180 days",
            "181-270 days",
            "271-364 days",
            "365-366 days",
        ],
        include_lowest=True,
    )

    print(
        bins.value_counts()
        .sort_index()
        .to_string()
    )

    assert (
        canonical["Provider CCN"]
        .duplicated()
        .sum()
        == 0
    )

    assert len(canonical) == (
        df["Provider CCN"].nunique()
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    canonical.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("CANONICAL COST REPORT COMPLETE")
    print("=" * 70)

    print(f"Saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    create_canonical_cost_report()