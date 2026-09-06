from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXACT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_exact_matches.csv"
)

FUZZY_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_fuzzy_accepted.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_match_master.csv"
)


# ============================================================
# MAIN
# ============================================================

def build_match_master():

    print("=" * 75)
    print("BUILDING CMS <-> HIFLD MATCH MASTER")
    print("=" * 75)

    exact = pd.read_csv(
        EXACT_FILE,
        dtype={
            "ccn": "string",
            "hifld_id": "string",
        },
        low_memory=False,
    )

    fuzzy = pd.read_csv(
        FUZZY_FILE,
        dtype={
            "ccn": "string",
            "hifld_id": "string",
        },
        low_memory=False,
    )

    # --------------------------------------------------------
    # Normalize identifiers
    # --------------------------------------------------------

    for df in [exact, fuzzy]:

        df["ccn"] = (
            df["ccn"]
            .str.strip()
            .str.zfill(6)
        )

        df["hifld_id"] = (
            df["hifld_id"]
            .str.strip()
        )

    print(f"\nExact matches: {len(exact):,}")
    print(
        f"Accepted fuzzy matches: "
        f"{len(fuzzy):,}"
    )

    # --------------------------------------------------------
    # Prepare exact matches
    # --------------------------------------------------------

    exact_master = pd.DataFrame(
        {
            "ccn": exact["ccn"],
            "hifld_id": exact["hifld_id"],
            "cms_name": exact["hospital_name"],
            "hifld_name": exact["hifld_name"],
            "latitude": exact["latitude"],
            "longitude": exact["longitude"],
            "match_type": exact["match_type"],
            "match_score": exact["match_score"],
        }
    )

    # Add HIFLD fields available from exact matching
    optional_exact_fields = {
        "hifld_beds": "hifld_beds",
        "hifld_type": "hifld_type",
        "hifld_status": "hifld_status",
        "hifld_owner": "hifld_owner",
        "trauma_level": "trauma_level",
        "helipad": "helipad",
    }

    for output_col, source_col in optional_exact_fields.items():

        if source_col in exact.columns:
            exact_master[output_col] = exact[source_col]
        else:
            exact_master[output_col] = pd.NA

    # Exact matches do not need fuzzy diagnostics
    exact_master["name_score"] = pd.NA
    exact_master["address_score"] = pd.NA
    exact_master["score_margin"] = pd.NA
    exact_master["candidate_block"] = pd.NA

    # --------------------------------------------------------
    # Prepare fuzzy matches
    # --------------------------------------------------------

    fuzzy_master = pd.DataFrame(
        {
            "ccn": fuzzy["ccn"],
            "hifld_id": fuzzy["hifld_id"],
            "cms_name": fuzzy["cms_name"],
            "hifld_name": fuzzy["hifld_name"],
            "latitude": fuzzy["latitude"],
            "longitude": fuzzy["longitude"],
            "match_type": fuzzy["match_type"],
            "match_score": fuzzy["match_score"],
            "name_score": fuzzy["name_score"],
            "address_score": fuzzy["address_score"],
            "score_margin": fuzzy["score_margin"],
            "candidate_block": fuzzy["candidate_block"],
        }
    )

    # HIFLD attributes will be added from the full HIFLD
    # source later during hospital-table construction.
    fuzzy_master["hifld_beds"] = pd.NA
    fuzzy_master["hifld_type"] = pd.NA
    fuzzy_master["hifld_status"] = pd.NA
    fuzzy_master["hifld_owner"] = pd.NA
    fuzzy_master["trauma_level"] = pd.NA
    fuzzy_master["helipad"] = pd.NA

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    master = pd.concat(
        [
            exact_master,
            fuzzy_master,
        ],
        ignore_index=True,
    )

    master = master.sort_values(
        "ccn"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 75)

    print(
        f"Combined accepted matches: "
        f"{len(master):,}"
    )

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

    assert len(master) == 5351
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

    print("\n" + "=" * 75)
    print("HIFLD MATCH MASTER COMPLETE")
    print("=" * 75)

    print(f"Saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    build_match_master()