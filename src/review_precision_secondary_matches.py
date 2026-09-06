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


def review_precision_candidates():

    print("=" * 82)
    print("PRECISION SECONDARY MATCH REVIEW")
    print("=" * 82)

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
    # Recreate secondary pool
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
    # Remove HIFLD IDs claimed by multiple CMS CCNs
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

    review = clean[
        rule_a | rule_c
    ].copy()

    review["precision_rule"] = "RULE_A"

    review.loc[
        rule_c,
        "precision_rule"
    ] = "RULE_C"

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print(f"\nClean secondary pool: {len(clean):,}")

    print("\nPRECISION RULE COUNTS")
    print("-" * 82)

    print(
        f"Rule A candidates: "
        f"{rule_a.sum():,}"
    )

    print(
        f"Rule C candidates: "
        f"{rule_c.sum():,}"
    )

    print(
        f"Unique precision candidates: "
        f"{len(review):,}"
    )

    print(
        "Duplicate CMS CCNs:",
        review["ccn"]
        .duplicated()
        .sum()
    )

    print(
        "Duplicate HIFLD IDs:",
        review["hifld_id"]
        .duplicated()
        .sum()
    )

    # --------------------------------------------------------
    # Print every candidate
    # --------------------------------------------------------

    print("\nALL PRECISION CANDIDATES")
    print("-" * 82)

    columns = [
        "precision_rule",
        "ccn",
        "cms_name",
        "cms_address",
        "cms_city",
        "cms_state",
        "cms_source_status",
        "hifld_id",
        "hifld_name",
        "hifld_address",
        "hifld_city",
        "hifld_state",
        "candidate_block",
        "candidate_count",
        "name_score",
        "address_score",
        "overall_score",
        "second_best_score",
        "score_margin",
    ]

    review = review.sort_values(
        [
            "overall_score",
            "name_score",
        ],
        ascending=[
            False,
            False,
        ],
    )

    print(
        review[
            columns
        ].to_string(index=False)
    )


if __name__ == "__main__":
    review_precision_candidates()