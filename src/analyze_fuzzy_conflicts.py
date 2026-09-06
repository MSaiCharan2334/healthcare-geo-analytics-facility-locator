from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CANDIDATE_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_fuzzy_candidates.csv"
)


# ============================================================
# MAIN
# ============================================================

def analyze_fuzzy_conflicts():

    print("=" * 75)
    print("HIFLD FUZZY MATCH CONFLICT ANALYSIS")
    print("=" * 75)

    df = pd.read_csv(
        CANDIDATE_FILE,
        dtype={
            "ccn": "string",
            "hifld_id": "string",
        },
        low_memory=False,
    )

    df["ccn"] = (
        df["ccn"]
        .str.strip()
        .str.zfill(6)
    )

    df["hifld_id"] = (
        df["hifld_id"]
        .str.strip()
    )

    # --------------------------------------------------------
    # 1. Re-create our current high-confidence rule
    # --------------------------------------------------------

    high_conf = df[
        (df["overall_score"] >= 90)
        &
        (
            df["score_margin"].isna()
            |
            (df["score_margin"] >= 10)
        )
    ].copy()

    print(f"\nTotal fuzzy candidate rows: {len(df):,}")
    print(
        f"Current high-confidence candidates: "
        f"{len(high_conf):,}"
    )

    # --------------------------------------------------------
    # 2. Find HIFLD IDs claimed by multiple CMS CCNs
    # --------------------------------------------------------

    claim_counts = (
        high_conf
        .groupby("hifld_id")["ccn"]
        .nunique()
        .sort_values(ascending=False)
    )

    conflicting_ids = set(
        claim_counts[
            claim_counts > 1
        ].index
    )

    conflicts = high_conf[
        high_conf["hifld_id"].isin(
            conflicting_ids
        )
    ].copy()

    # --------------------------------------------------------
    # 3. Clean one-to-one high-confidence matches
    # --------------------------------------------------------

    clean_high_conf = high_conf[
        ~high_conf["hifld_id"].isin(
            conflicting_ids
        )
    ].copy()

    print("\nCONFLICT SUMMARY")
    print("-" * 75)

    print(
        "Unique HIFLD facilities claimed by "
        "multiple CMS CCNs:",
        f"{len(conflicting_ids):,}"
    )

    print(
        "CMS candidate rows involved in conflicts:",
        f"{len(conflicts):,}"
    )

    print(
        "Clean one-to-one high-confidence matches:",
        f"{len(clean_high_conf):,}"
    )

    # --------------------------------------------------------
    # 4. Conflict size distribution
    # --------------------------------------------------------

    if len(conflicting_ids) > 0:

        print("\nCMS CCNs per conflicted HIFLD facility:")
        print("-" * 75)

        print(
            claim_counts[
                claim_counts > 1
            ]
            .value_counts()
            .sort_index()
            .rename_axis("cms_ccns_per_hifld")
            .to_frame("number_of_hifld_facilities")
            .to_string()
        )

    # --------------------------------------------------------
    # 5. Source-status distribution
    # --------------------------------------------------------

    print("\nSOURCE STATUS - CLEAN HIGH CONFIDENCE")
    print("-" * 75)

    print(
        clean_high_conf[
            "cms_source_status"
        ]
        .value_counts()
        .to_string()
    )

    if not conflicts.empty:

        print("\nSOURCE STATUS - CONFLICTED CANDIDATES")
        print("-" * 75)

        print(
            conflicts[
                "cms_source_status"
            ]
            .value_counts()
            .to_string()
        )

    # --------------------------------------------------------
    # 6. Show conflicts
    # --------------------------------------------------------

    if not conflicts.empty:

        print("\nFUZZY MATCH CONFLICTS")
        print("-" * 75)

        conflict_columns = [
            "hifld_id",
            "hifld_name",
            "hifld_city",
            "hifld_state",
            "ccn",
            "cms_name",
            "cms_city",
            "cms_state",
            "cms_source_status",
            "candidate_block",
            "candidate_count",
            "name_score",
            "address_score",
            "overall_score",
            "second_best_score",
            "score_margin",
        ]

        conflicts = conflicts.sort_values(
            [
                "hifld_id",
                "overall_score",
            ],
            ascending=[
                True,
                False,
            ],
        )

        print(
            conflicts[
                conflict_columns
            ]
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # 7. Sample clean matches
    # --------------------------------------------------------

    print("\nSAMPLE CLEAN HIGH-CONFIDENCE MATCHES")
    print("-" * 75)

    sample_columns = [
        "ccn",
        "cms_name",
        "cms_city",
        "cms_state",
        "hifld_id",
        "hifld_name",
        "candidate_block",
        "name_score",
        "address_score",
        "overall_score",
        "score_margin",
    ]

    print(
        clean_high_conf[
            sample_columns
        ]
        .sort_values(
            "overall_score",
            ascending=False,
        )
        .head(30)
        .to_string(index=False)
    )


if __name__ == "__main__":
    analyze_fuzzy_conflicts()