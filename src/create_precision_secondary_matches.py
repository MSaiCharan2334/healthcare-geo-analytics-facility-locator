from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_remaining_candidates.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_precision_secondary_accepted.csv"
)


# ------------------------------------------------------------
# Manually held after precision review
# ------------------------------------------------------------

HELD_CCNS = {
    "454161",  # 5680 vs 5860 Frisco Square Blvd
    "043031",  # 221 vs 2201 Wildwood Ave
    "010005",  # Hwy 431 North vs South
}


def create_precision_secondary_matches():

    print("=" * 78)
    print("CREATING PRECISION SECONDARY HIFLD MATCHES")
    print("=" * 78)

    df = pd.read_csv(
        INPUT_FILE,
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
    # Recreate secondary candidate pool
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

    # --------------------------------------------------------
    # Remove HIFLD facilities claimed by >1 CMS CCN
    # --------------------------------------------------------

    claim_counts = (
        secondary
        .groupby("hifld_id")["ccn"]
        .nunique()
    )

    conflicted_ids = set(
        claim_counts[
            claim_counts > 1
        ].index
    )

    clean = secondary[
        ~secondary["hifld_id"].isin(
            conflicted_ids
        )
    ].copy()

    # --------------------------------------------------------
    # Precision Rule A
    # --------------------------------------------------------

    rule_a = (
        (clean["candidate_block"] == "ZIP_STATE")
        &
        (clean["overall_score"] >= 88)
        &
        (clean["name_score"] >= 90)
        &
        (clean["address_score"] >= 85)
    )

    # --------------------------------------------------------
    # Precision Rule C
    # --------------------------------------------------------

    rule_c = (
        (clean["candidate_block"] == "CITY_STATE")
        &
        (clean["overall_score"] >= 95)
        &
        (clean["name_score"] >= 95)
        &
        (clean["address_score"] >= 95)
    )

    precision = clean[
        rule_a | rule_c
    ].copy()

    print(
        f"\nPrecision candidates before manual holds: "
        f"{len(precision):,}"
    )

    # --------------------------------------------------------
    # Manual hold exclusions
    # --------------------------------------------------------

    held = precision[
        precision["ccn"].isin(
            HELD_CCNS
        )
    ].copy()

    accepted = precision[
        ~precision["ccn"].isin(
            HELD_CCNS
        )
    ].copy()

    # --------------------------------------------------------
    # Provenance
    # --------------------------------------------------------

    accepted["match_type"] = (
        "FUZZY_PRECISION_SECONDARY"
    )

    accepted["match_score"] = (
        accepted["overall_score"]
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 78)

    print(
        "Manual-review holds:",
        f"{len(held):,}"
    )

    print(
        "Accepted precision secondary matches:",
        f"{len(accepted):,}"
    )

    print(
        "Duplicate accepted CCNs:",
        accepted["ccn"]
        .duplicated()
        .sum()
    )

    print(
        "Duplicate accepted HIFLD IDs:",
        accepted["hifld_id"]
        .duplicated()
        .sum()
    )

    print("\nHeld records:")

    print(
        held[
            [
                "ccn",
                "cms_name",
                "cms_address",
                "hifld_name",
                "hifld_address",
            ]
        ]
        .to_string(index=False)
    )

    assert len(precision) == 43
    assert len(held) == 3
    assert len(accepted) == 40

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

    # --------------------------------------------------------
    # Keep useful audit fields
    # --------------------------------------------------------

    columns = [
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

    columns = [
        col
        for col in columns
        if col in accepted.columns
    ]

    accepted = accepted[
        columns
    ].copy()

    accepted = accepted.sort_values(
        "ccn"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Save
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

    print("\n" + "=" * 78)
    print("PRECISION SECONDARY MATCH FILE COMPLETE")
    print("=" * 78)

    print(f"Saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    create_precision_secondary_matches()