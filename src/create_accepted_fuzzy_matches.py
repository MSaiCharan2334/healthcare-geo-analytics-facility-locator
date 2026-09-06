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

EXACT_MATCH_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_exact_matches.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_fuzzy_accepted.csv"
)


# ============================================================
# MAIN
# ============================================================

def create_accepted_fuzzy_matches():

    print("=" * 75)
    print("CREATING ACCEPTED HIGH-CONFIDENCE FUZZY MATCHES")
    print("=" * 75)

    candidates = pd.read_csv(
        CANDIDATE_FILE,
        dtype={
            "ccn": "string",
            "hifld_id": "string",
        },
        low_memory=False,
    )

    exact = pd.read_csv(
        EXACT_MATCH_FILE,
        dtype={
            "ccn": "string",
            "hifld_id": "string",
        },
        low_memory=False,
    )

    # --------------------------------------------------------
    # Normalize IDs
    # --------------------------------------------------------

    candidates["ccn"] = (
        candidates["ccn"]
        .str.strip()
        .str.zfill(6)
    )

    candidates["hifld_id"] = (
        candidates["hifld_id"]
        .str.strip()
    )

    exact["ccn"] = (
        exact["ccn"]
        .str.strip()
        .str.zfill(6)
    )

    exact["hifld_id"] = (
        exact["hifld_id"]
        .str.strip()
    )

    # --------------------------------------------------------
    # 1. Apply high-confidence rule
    # --------------------------------------------------------

    high_conf = candidates[
        (candidates["overall_score"] >= 90)
        &
        (
            candidates["score_margin"].isna()
            |
            (candidates["score_margin"] >= 10)
        )
    ].copy()

    print(
        f"\nHigh-confidence candidates before conflict removal: "
        f"{len(high_conf):,}"
    )

    # --------------------------------------------------------
    # 2. Find HIFLD facilities claimed by multiple CMS CCNs
    # --------------------------------------------------------

    claim_counts = (
        high_conf
        .groupby("hifld_id")["ccn"]
        .nunique()
    )

    conflicted_hifld_ids = set(
        claim_counts[
            claim_counts > 1
        ].index
    )

    conflicted_rows = high_conf[
        high_conf["hifld_id"].isin(
            conflicted_hifld_ids
        )
    ].copy()

    # --------------------------------------------------------
    # 3. Accept only one-to-one matches
    # --------------------------------------------------------

    accepted = high_conf[
        ~high_conf["hifld_id"].isin(
            conflicted_hifld_ids
        )
    ].copy()

    accepted["match_type"] = (
        "FUZZY_HIGH_CONFIDENCE"
    )

    accepted["match_score"] = (
        accepted["overall_score"]
    )

    # --------------------------------------------------------
    # 4. Validate against exact matches
    # --------------------------------------------------------

    exact_ccns = set(
        exact["ccn"]
    )

    exact_hifld_ids = set(
        exact["hifld_id"]
    )

    fuzzy_ccns = set(
        accepted["ccn"]
    )

    fuzzy_hifld_ids = set(
        accepted["hifld_id"]
    )

    ccn_overlap = (
        exact_ccns
        & fuzzy_ccns
    )

    hifld_overlap = (
        exact_hifld_ids
        & fuzzy_hifld_ids
    )

    # --------------------------------------------------------
    # 5. Validation output
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 75)

    print(
        "Conflicted HIFLD facilities removed:",
        f"{len(conflicted_hifld_ids):,}"
    )

    print(
        "Conflicted candidate rows removed:",
        f"{len(conflicted_rows):,}"
    )

    print(
        "Accepted fuzzy matches:",
        f"{len(accepted):,}"
    )

    print(
        "Duplicate accepted CCNs:",
        accepted["ccn"]
        .duplicated()
        .sum(),
    )

    print(
        "Duplicate accepted HIFLD IDs:",
        accepted["hifld_id"]
        .duplicated()
        .sum(),
    )

    print(
        "Overlap with exact-match CCNs:",
        len(ccn_overlap),
    )

    print(
        "Overlap with exact-match HIFLD IDs:",
        len(hifld_overlap),
    )

    # --------------------------------------------------------
    # 6. Hard checks
    # --------------------------------------------------------

    assert (
        accepted["ccn"]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        accepted["hifld_id"]
        .duplicated()
        .sum()
        == 0
    )

    assert len(ccn_overlap) == 0
    assert len(hifld_overlap) == 0

    # Based on current analysis
    assert len(accepted) == 407

    # --------------------------------------------------------
    # 7. Keep useful mapping / audit fields
    # --------------------------------------------------------

    output_columns = [
        "ccn",
        "cms_name",
        "cms_address",
        "cms_city",
        "cms_state",
        "cms_zip",
        "cms_source_status",
        "hifld_id",
        "hifld_name",
        "hifld_address",
        "hifld_city",
        "hifld_state",
        "hifld_zip",
        "latitude",
        "longitude",
        "candidate_block",
        "candidate_count",
        "name_score",
        "address_score",
        "overall_score",
        "second_best_score",
        "score_margin",
        "match_type",
        "match_score",
    ]

    output_columns = [
        col
        for col in output_columns
        if col in accepted.columns
    ]

    accepted = accepted[
        output_columns
    ].copy()

    accepted = accepted.sort_values(
        "ccn"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # 8. Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    accepted.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 75)
    print("ACCEPTED FUZZY MATCH FILE COMPLETE")
    print("=" * 75)

    print(f"Saved to:\n{OUTPUT_FILE}")

    print("\nSample accepted matches:")

    print(
        accepted[
            [
                "ccn",
                "cms_name",
                "hifld_name",
                "overall_score",
                "score_margin",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )


if __name__ == "__main__":
    create_accepted_fuzzy_matches()