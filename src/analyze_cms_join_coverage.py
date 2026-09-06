from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GENERAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "hospitals"
    / "cms_hospital_general.csv"
)

COST_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "cms_cost_report_canonical.csv"
)


def analyze_join_coverage():

    print("=" * 70)
    print("CMS GENERAL <-> COST REPORT JOIN COVERAGE")
    print("=" * 70)

    general = pd.read_csv(
        GENERAL_FILE,
        dtype={
            "Facility ID": "string",
            "ZIP Code": "string",
        },
        low_memory=False,
    )

    cost = pd.read_csv(
        COST_FILE,
        dtype={
            "Provider CCN": "string",
            "Zip Code": "string",
        },
        low_memory=False,
    )

    # --------------------------------------------------------
    # Normalize identifiers
    # --------------------------------------------------------

    general["Facility ID"] = (
        general["Facility ID"]
        .str.strip()
        .str.zfill(6)
    )

    cost["Provider CCN"] = (
        cost["Provider CCN"]
        .str.strip()
        .str.zfill(6)
    )

    # --------------------------------------------------------
    # Basic counts
    # --------------------------------------------------------

    general_ids = set(
        general["Facility ID"].dropna()
    )

    cost_ids = set(
        cost["Provider CCN"].dropna()
    )

    matched_ids = general_ids & cost_ids

    general_only = general_ids - cost_ids
    cost_only = cost_ids - general_ids

    print(f"\nCMS General rows: {len(general):,}")
    print(
        "Unique CMS General Facility IDs:",
        len(general_ids),
    )

    print(f"\nCanonical Cost Report rows: {len(cost):,}")
    print(
        "Unique Cost Report CCNs:",
        len(cost_ids),
    )

    print("\nJOIN COVERAGE")
    print("-" * 70)

    print(
        "Matching CCNs:",
        f"{len(matched_ids):,}"
    )

    print(
        "CMS General without Cost Report:",
        f"{len(general_only):,}"
    )

    print(
        "Cost Report without CMS General:",
        f"{len(cost_only):,}"
    )

    match_rate = (
        len(matched_ids)
        / len(general_ids)
        * 100
    )

    print(
        f"\nCMS General match rate: "
        f"{match_rate:.2f}%"
    )

    # --------------------------------------------------------
    # Analyze unmatched CMS General hospitals
    # --------------------------------------------------------

    unmatched_general = general[
        general["Facility ID"].isin(
            general_only
        )
    ].copy()

    print(
        "\nHospital types among CMS General records "
        "without a Cost Report:"
    )
    print("-" * 70)

    if not unmatched_general.empty:
        print(
            unmatched_general[
                "Hospital Type"
            ]
            .value_counts(dropna=False)
            .to_string()
        )

    # --------------------------------------------------------
    # Analyze unmatched Cost Report providers
    # --------------------------------------------------------

    unmatched_cost = cost[
        cost["Provider CCN"].isin(
            cost_only
        )
    ].copy()

    print(
        "\nProvider types among Cost Report records "
        "without CMS General:"
    )
    print("-" * 70)

    if not unmatched_cost.empty:
        print(
            unmatched_cost[
                "Provider Type"
            ]
            .value_counts(dropna=False)
            .to_string()
        )

    # --------------------------------------------------------
    # Sample unmatched records
    # --------------------------------------------------------

    print("\nSample CMS General records without Cost Report:")
    print("-" * 70)

    if not unmatched_general.empty:

        cols = [
            "Facility ID",
            "Facility Name",
            "City/Town",
            "State",
            "Hospital Type",
        ]

        print(
            unmatched_general[
                cols
            ]
            .head(20)
            .to_string(index=False)
        )

    print("\nSample Cost Report records without CMS General:")
    print("-" * 70)

    if not unmatched_cost.empty:

        cols = [
            "Provider CCN",
            "Hospital Name",
            "City",
            "State Code",
            "Provider Type",
        ]

        print(
            unmatched_cost[
                cols
            ]
            .head(20)
            .to_string(index=False)
        )


if __name__ == "__main__":
    analyze_join_coverage()