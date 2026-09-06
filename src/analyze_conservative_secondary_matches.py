from pathlib import Path
import re

import pandas as pd


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_remaining_candidates.csv"
)


# ============================================================
# ADDRESS HELPER
# ============================================================

def street_number(value):
    """
    Extract the first street/building number from an address.

    Examples:
        123 MAIN ST       -> 123
        4500 S 10TH AVE   -> 4500
    """

    if pd.isna(value):
        return ""

    match = re.search(
        r"\b\d+\b",
        str(value),
    )

    if match:
        return match.group(0)

    return ""


# ============================================================
# MAIN
# ============================================================

def analyze_conservative_matches():

    print("=" * 78)
    print("CONSERVATIVE SECONDARY MATCH QUALITY ANALYSIS")
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
    # Recreate secondary rule
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
    # Remove HIFLD conflicts
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

    print(
        f"\nClean secondary candidates: "
        f"{len(clean):,}"
    )

    # --------------------------------------------------------
    # Street-number evidence
    # --------------------------------------------------------

    clean["cms_street_number"] = (
        clean["cms_address"]
        .apply(street_number)
    )

    clean["hifld_street_number"] = (
        clean["hifld_address"]
        .apply(street_number)
    )

    clean["street_number_match"] = (
        (clean["cms_street_number"] != "")
        &
        (
            clean["cms_street_number"]
            == clean["hifld_street_number"]
        )
    )

    # ========================================================
    # RULE A
    #
    # Strong ZIP-based fuzzy match
    # ========================================================

    rule_a = (
        (clean["candidate_block"] == "ZIP_STATE")
        &
        (clean["overall_score"] >= 88)
        &
        (clean["name_score"] >= 90)
        &
        (clean["address_score"] >= 85)
    )

    # ========================================================
    # RULE B
    #
    # Slightly lower overall score allowed when the exact
    # street/building number agrees.
    # ========================================================

    rule_b = (
        (clean["candidate_block"] == "ZIP_STATE")
        &
        (clean["overall_score"] >= 85)
        &
        (clean["name_score"] >= 85)
        &
        (clean["address_score"] >= 85)
        &
        clean["street_number_match"]
    )

    # ========================================================
    # RULE C
    #
    # City/state fallback requires extremely strong evidence.
    # ========================================================

    rule_c = (
        (clean["candidate_block"] == "CITY_STATE")
        &
        (clean["overall_score"] >= 95)
        &
        (clean["name_score"] >= 95)
        &
        (clean["address_score"] >= 95)
    )

    # --------------------------------------------------------
    # Combined conservative rule
    # --------------------------------------------------------

    conservative = (
        rule_a
        | rule_b
        | rule_c
    )

    accepted = clean[
        conservative
    ].copy()

    rejected = clean[
        ~conservative
    ].copy()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\nRULE COUNTS")
    print("-" * 78)

    print(
        f"Rule A - strong ZIP/name/address: "
        f"{rule_a.sum():,}"
    )

    print(
        f"Rule B - ZIP + matching street number: "
        f"{rule_b.sum():,}"
    )

    print(
        f"Rule C - extremely strong city/state: "
        f"{rule_c.sum():,}"
    )

    print(
        "\nUnique candidates passing at least one rule:",
        f"{len(accepted):,}"
    )

    print(
        "Clean candidates still held for review/unmatched:",
        f"{len(rejected):,}"
    )

    # --------------------------------------------------------
    # Accepted diagnostics
    # --------------------------------------------------------

    print("\nACCEPTED BY BLOCK")
    print("-" * 78)

    if not accepted.empty:

        print(
            accepted[
                "candidate_block"
            ]
            .value_counts()
            .to_string()
        )

    print("\nACCEPTED SCORE DISTRIBUTION")
    print("-" * 78)

    if not accepted.empty:

        print(
            accepted[
                "overall_score"
            ]
            .describe()
            .to_string()
        )

    # --------------------------------------------------------
    # Lowest scoring accepted candidates
    # --------------------------------------------------------

    print("\nLOWEST-SCORING CANDIDATES THAT WOULD PASS")
    print("-" * 78)

    columns = [
        "ccn",
        "cms_name",
        "cms_address",
        "cms_city",
        "cms_state",
        "hifld_name",
        "hifld_address",
        "candidate_block",
        "name_score",
        "address_score",
        "overall_score",
        "street_number_match",
        "score_margin",
    ]

    print(
        accepted[
            columns
        ]
        .sort_values(
            "overall_score"
        )
        .head(40)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # Highest scoring records still rejected
    # --------------------------------------------------------

    print("\nHIGHEST-SCORING CANDIDATES STILL HELD BACK")
    print("-" * 78)

    print(
        rejected[
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
    analyze_conservative_matches()