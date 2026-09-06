from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_MASTER_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_match_master.csv"
)

SECONDARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_precision_secondary_accepted.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_match_master_v2.csv"
)


# ============================================================
# MAIN
# ============================================================

def build_match_master_v2():

    print("=" * 78)
    print("BUILDING UPDATED CMS <-> HIFLD MATCH MASTER")
    print("=" * 78)

    base = pd.read_csv(
        BASE_MASTER_FILE,
        dtype={
            "ccn": "string",
            "hifld_id": "string",
        },
        low_memory=False,
    )

    secondary = pd.read_csv(
        SECONDARY_FILE,
        dtype={
            "ccn": "string",
            "hifld_id": "string",
        },
        low_memory=False,
    )

    # --------------------------------------------------------
    # Normalize identifiers
    # --------------------------------------------------------

    for df in [base, secondary]:

        df["ccn"] = (
            df["ccn"]
            .str.strip()
            .str.zfill(6)
        )

        df["hifld_id"] = (
            df["hifld_id"]
            .str.strip()
        )

    print(
        f"\nExisting accepted matches: "
        f"{len(base):,}"
    )

    print(
        f"Precision secondary matches: "
        f"{len(secondary):,}"
    )

    # --------------------------------------------------------
    # Check overlap before combining
    # --------------------------------------------------------

    base_ccns = set(
        base["ccn"]
    )

    base_hifld_ids = set(
        base["hifld_id"]
    )

    secondary_ccns = set(
        secondary["ccn"]
    )

    secondary_hifld_ids = set(
        secondary["hifld_id"]
    )

    ccn_overlap = (
        base_ccns
        & secondary_ccns
    )

    hifld_overlap = (
        base_hifld_ids
        & secondary_hifld_ids
    )

    print("\nPRE-COMBINE VALIDATION")
    print("-" * 78)

    print(
        "CMS CCN overlap:",
        len(ccn_overlap),
    )

    print(
        "HIFLD ID overlap:",
        len(hifld_overlap),
    )

    assert len(ccn_overlap) == 0
    assert len(hifld_overlap) == 0

    # --------------------------------------------------------
    # Align columns
    # --------------------------------------------------------

    all_columns = sorted(
        set(base.columns)
        | set(secondary.columns)
    )

    base = base.reindex(
        columns=all_columns
    )

    secondary = secondary.reindex(
        columns=all_columns
    )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    master = pd.concat(
        [
            base,
            secondary,
        ],
        ignore_index=True,
    )

    master = master.sort_values(
        "ccn"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\nFINAL VALIDATION")
    print("-" * 78)

    duplicate_ccns = (
        master["ccn"]
        .duplicated()
        .sum()
    )

    duplicate_hifld = (
        master["hifld_id"]
        .duplicated()
        .sum()
    )

    missing_ccns = (
        master["ccn"]
        .isna()
        .sum()
    )

    missing_hifld = (
        master["hifld_id"]
        .isna()
        .sum()
    )

    missing_coordinates = (
        master[
            [
                "latitude",
                "longitude",
            ]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    print(
        f"Combined accepted matches: "
        f"{len(master):,}"
    )

    print(
        "Duplicate CMS CCNs:",
        duplicate_ccns,
    )

    print(
        "Duplicate HIFLD IDs:",
        duplicate_hifld,
    )

    print(
        "Missing CMS CCNs:",
        missing_ccns,
    )

    print(
        "Missing HIFLD IDs:",
        missing_hifld,
    )

    print(
        "Missing coordinates:",
        missing_coordinates,
    )

    print("\nMatch type distribution:")

    print(
        master[
            "match_type"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Hard checks
    # --------------------------------------------------------

    assert len(master) == 5391
    assert duplicate_ccns == 0
    assert duplicate_hifld == 0
    assert missing_ccns == 0
    assert missing_hifld == 0
    assert missing_coordinates == 0

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    master.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 78)
    print("UPDATED HIFLD MATCH MASTER COMPLETE")
    print("=" * 78)

    print(f"Saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    build_match_master_v2()