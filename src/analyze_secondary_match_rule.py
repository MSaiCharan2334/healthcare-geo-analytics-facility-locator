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
    / "hifld_remaining_candidates.csv"
)


# ============================================================
# MAIN
# ============================================================

def analyze_secondary_rule():

    print("=" * 78)
    print("SECONDARY HIFLD MATCH RULE ANALYSIS")
    print("=" * 78)

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
    # 1. Secondary candidate rule
    # --------------------------------------------------------

    secondary = df[
        (df["overall_score"] >= 85)
        &
        (
            df["score_margin"].isna()
            |
            (df["score_margin"] >= 15)
        )
    ].copy()

    print(
        f"\nSecondary-rule candidates: "
        f"{len(secondary):,}"
    )

    # --------------------------------------------------------
    # 2. Detect HIFLD facilities claimed by >1 CMS CCN
    # --------------------------------------------------------

    claim_counts = (
        secondary
        .groupby("hifld_id")["ccn"]
        .nunique()
    )

    conflicted_hifld_ids = set(
        claim_counts[
            claim_counts > 1
        ].index
    )

    conflicts = secondary[
        secondary["hifld_id"].isin(
            conflicted_hifld_ids
        )
    ].copy()

    clean = secondary[
        ~secondary["hifld_id"].isin(
            conflicted_hifld_ids
        )
    ].copy()

    # --------------------------------------------------------
    # 3. Summary
    # --------------------------------------------------------

    print("\nCONFLICT SUMMARY")
    print("-" * 78)

    print(
        "Unique HIFLD facilities with multiple CMS claims:",
        f"{len(conflicted_hifld_ids):,}"
    )

    print(
        "CMS rows involved in conflicts:",
        f"{len(conflicts):,}"
    )

    print(
        "Clean one-to-one secondary candidates:",
        f"{len(clean):,}"
    )

    # --------------------------------------------------------
    # 4. Clean-candidate diagnostics
    # --------------------------------------------------------

    print("\nCLEAN SECONDARY CANDIDATES BY SOURCE STATUS")
    print("-" * 78)

    if not clean.empty:
        print(
            clean[
                "cms_source_status"
            ]
            .value_counts()
            .to_string()
        )

    print("\nCLEAN SECONDARY CANDIDATES BY BLOCK")
    print("-" * 78)

    if not clean.empty:
        print(
            clean[
                "candidate_block"
            ]
            .value_counts()
            .to_string()
        )

    print("\nCLEAN SCORE DISTRIBUTION")
    print("-" * 78)

    if not clean.empty:
        print(
            clean[
                "overall_score"
            ]
            .describe()
            .to_string()
        )

    # --------------------------------------------------------
    # 5. Conflict size distribution
    # --------------------------------------------------------

    if not conflicts.empty:

        print("\nCMS CLAIMS PER CONFLICTED HIFLD FACILITY")
        print("-" * 78)

        print(
            claim_counts[
                claim_counts > 1
            ]
            .value_counts()
            .sort_index()
            .rename_axis("cms_ccns_per_hifld")
            .to_frame("hifld_facilities")
            .to_string()
        )

    # --------------------------------------------------------
    # 6. Analyze source-status combinations in conflicts
    # --------------------------------------------------------

    if not conflicts.empty:

        status_summary = (
            conflicts
            .groupby("hifld_id")[
                "cms_source_status"
            ]
            .apply(
                lambda x:
                " | ".join(
                    sorted(x.astype(str).tolist())
                )
            )
            .value_counts()
        )

        print("\nCONFLICT SOURCE-STATUS COMBINATIONS")
        print("-" * 78)

        print(
            status_summary.to_string()
        )

    # --------------------------------------------------------
    # 7. Show all conflicts
    # --------------------------------------------------------

    if not conflicts.empty:

        print("\nSECONDARY-RULE CONFLICTS")
        print("-" * 78)

        columns = [
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
                columns
            ]
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # 8. Sample clean secondary matches
    # --------------------------------------------------------

    print("\nSAMPLE CLEAN SECONDARY CANDIDATES")
    print("-" * 78)

    columns = [
        "ccn",
        "cms_name",
        "cms_city",
        "cms_state",
        "cms_source_status",
        "hifld_id",
        "hifld_name",
        "candidate_block",
        "name_score",
        "address_score",
        "overall_score",
        "second_best_score",
        "score_margin",
    ]

    print(
        clean[
            columns
        ]
        .sort_values(
            "overall_score",
            ascending=False,
        )
        .head(40)
        .to_string(index=False)
    )


if __name__ == "__main__":
    analyze_secondary_rule()