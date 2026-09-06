from pathlib import Path
import re
import unicodedata

import pandas as pd
from rapidfuzz import fuzz


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CMS_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "cms_hospital_master.csv"
)

HIFLD_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "hospitals"
    / "hifld_hospitals.csv"
)

MATCH_MASTER_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_match_master.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_remaining_candidates.csv"
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):

    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.replace("&", " AND ")

    value = re.sub(
        r"[^A-Z0-9\s]",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_zip(value):

    if pd.isna(value):
        return ""

    match = re.search(
        r"\d{5}",
        str(value),
    )

    if match:
        return match.group(0)

    return ""


# ============================================================
# PREP
# ============================================================

def prepare_cms(df):

    df = df.copy()

    df["ccn"] = (
        df["ccn"]
        .astype("string")
        .str.strip()
        .str.zfill(6)
    )

    df["match_name"] = (
        df["hospital_name"]
        .apply(normalize_text)
    )

    df["match_address"] = (
        df["address"]
        .apply(normalize_text)
    )

    df["match_city"] = (
        df["city"]
        .apply(normalize_text)
    )

    df["match_state"] = (
        df["state"]
        .apply(normalize_text)
    )

    df["match_zip"] = (
        df["zip_code"]
        .apply(normalize_zip)
    )

    return df


def prepare_hifld(df):

    df = df.copy()

    df["ID"] = (
        df["ID"]
        .astype("string")
        .str.strip()
    )

    df["match_name"] = (
        df["NAME"]
        .apply(normalize_text)
    )

    df["match_address"] = (
        df["ADDRESS"]
        .apply(normalize_text)
    )

    df["match_city"] = (
        df["CITY"]
        .apply(normalize_text)
    )

    df["match_state"] = (
        df["STATE"]
        .apply(normalize_text)
    )

    df["match_zip"] = (
        df["ZIP"]
        .apply(normalize_zip)
    )

    return df


# ============================================================
# SCORING
# ============================================================

def score_candidate(cms_row, hifld_row):

    name_score = fuzz.WRatio(
        cms_row["match_name"],
        hifld_row["match_name"],
    )

    if (
        cms_row["match_address"]
        and hifld_row["match_address"]
    ):
        address_score = fuzz.WRatio(
            cms_row["match_address"],
            hifld_row["match_address"],
        )
    else:
        address_score = 0

    overall_score = (
        0.70 * name_score
        + 0.30 * address_score
    )

    return (
        round(name_score, 2),
        round(address_score, 2),
        round(overall_score, 2),
    )


# ============================================================
# MAIN
# ============================================================

def analyze_remaining_candidates():

    print("=" * 78)
    print("REMAINING CMS <-> HIFLD CANDIDATE ANALYSIS")
    print("=" * 78)

    cms = pd.read_csv(
        CMS_FILE,
        dtype={"ccn": "string"},
        low_memory=False,
    )

    hifld = pd.read_csv(
        HIFLD_FILE,
        dtype={"ID": "string"},
        low_memory=False,
    )

    matches = pd.read_csv(
        MATCH_MASTER_FILE,
        dtype={
            "ccn": "string",
            "hifld_id": "string",
        },
        low_memory=False,
    )

    cms = prepare_cms(cms)
    hifld = prepare_hifld(hifld)

    matches["ccn"] = (
        matches["ccn"]
        .str.strip()
        .str.zfill(6)
    )

    matches["hifld_id"] = (
        matches["hifld_id"]
        .str.strip()
    )

    # --------------------------------------------------------
    # Remaining pools
    # --------------------------------------------------------

    used_ccns = set(
        matches["ccn"]
    )

    used_hifld_ids = set(
        matches["hifld_id"]
    )

    remaining_cms = cms[
        ~cms["ccn"].isin(
            used_ccns
        )
    ].copy()

    available_hifld = hifld[
        ~hifld["ID"].isin(
            used_hifld_ids
        )
    ].copy()

    print(f"\nCMS master rows: {len(cms):,}")
    print(f"Accepted matches: {len(matches):,}")
    print(
        f"Remaining CMS hospitals: "
        f"{len(remaining_cms):,}"
    )

    print(f"\nHIFLD rows: {len(hifld):,}")
    print(
        f"Remaining available HIFLD hospitals: "
        f"{len(available_hifld):,}"
    )

    print("\nREMAINING CMS SOURCE STATUS")
    print("-" * 78)

    print(
        remaining_cms[
            "cms_source_status"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Generate fresh candidates
    # --------------------------------------------------------

    results = []

    for _, cms_row in remaining_cms.iterrows():

        # First try same ZIP + state
        candidates = available_hifld[
            (
                available_hifld["match_zip"]
                == cms_row["match_zip"]
            )
            &
            (
                available_hifld["match_state"]
                == cms_row["match_state"]
            )
        ]

        candidate_block = "ZIP_STATE"

        # If nothing, try same city + state
        if candidates.empty:

            candidates = available_hifld[
                (
                    available_hifld["match_city"]
                    == cms_row["match_city"]
                )
                &
                (
                    available_hifld["match_state"]
                    == cms_row["match_state"]
                )
            ]

            candidate_block = "CITY_STATE"

        if candidates.empty:
            continue

        scored = []

        for _, hifld_row in candidates.iterrows():

            (
                name_score,
                address_score,
                overall_score,
            ) = score_candidate(
                cms_row,
                hifld_row,
            )

            scored.append(
                {
                    "hifld_id": hifld_row["ID"],
                    "hifld_name": hifld_row["NAME"],
                    "hifld_address": hifld_row["ADDRESS"],
                    "hifld_city": hifld_row["CITY"],
                    "hifld_state": hifld_row["STATE"],
                    "hifld_zip": hifld_row["ZIP"],
                    "latitude": hifld_row["LATITUDE"],
                    "longitude": hifld_row["LONGITUDE"],
                    "name_score": name_score,
                    "address_score": address_score,
                    "overall_score": overall_score,
                }
            )

        scored = sorted(
            scored,
            key=lambda x: x["overall_score"],
            reverse=True,
        )

        best = scored[0]

        second_best_score = (
            scored[1]["overall_score"]
            if len(scored) > 1
            else None
        )

        score_margin = (
            best["overall_score"]
            - second_best_score
            if second_best_score is not None
            else None
        )

        results.append(
            {
                "ccn": cms_row["ccn"],
                "cms_name": cms_row["hospital_name"],
                "cms_address": cms_row["address"],
                "cms_city": cms_row["city"],
                "cms_state": cms_row["state"],
                "cms_zip": cms_row["zip_code"],
                "cms_source_status": cms_row[
                    "cms_source_status"
                ],
                "candidate_block": candidate_block,
                "candidate_count": len(scored),
                **best,
                "second_best_score": second_best_score,
                "score_margin": (
                    round(score_margin, 2)
                    if score_margin is not None
                    else None
                ),
            }
        )

    candidate_df = pd.DataFrame(
        results
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\nCANDIDATE COVERAGE")
    print("-" * 78)

    print(
        "Remaining CMS hospitals with at least "
        "one available HIFLD candidate:",
        f"{len(candidate_df):,}"
    )

    print(
        "Remaining CMS hospitals with no candidate:",
        f"{len(remaining_cms) - len(candidate_df):,}"
    )

    if not candidate_df.empty:

        print("\nBlocking method:")

        print(
            candidate_df[
                "candidate_block"
            ]
            .value_counts()
            .to_string()
        )

        print("\nBest-score distribution:")

        print(
            candidate_df[
                "overall_score"
            ]
            .describe()
            .to_string()
        )

        print("\nSCORE TIERS")
        print("-" * 78)

        tiers = [
            ("95+", 95, 101),
            ("90-94.99", 90, 95),
            ("85-89.99", 85, 90),
            ("80-84.99", 80, 85),
            ("75-79.99", 75, 80),
            ("Below 75", 0, 75),
        ]

        for label, low, high in tiers:

            count = (
                (
                    candidate_df[
                        "overall_score"
                    ] >= low
                )
                &
                (
                    candidate_df[
                        "overall_score"
                    ] < high
                )
            ).sum()

            print(
                f"{label:<15}: {count:,}"
            )

        # ----------------------------------------------------
        # Potential secondary-rule diagnostics
        # ----------------------------------------------------

        print("\nPOTENTIAL SECONDARY MATCH RULES")
        print("-" * 78)

        rules = {
            "Score >= 85, margin >= 15": (
                (candidate_df["overall_score"] >= 85)
                &
                (
                    candidate_df["score_margin"].isna()
                    |
                    (candidate_df["score_margin"] >= 15)
                )
            ),

            "Name >= 90 AND address >= 80": (
                (candidate_df["name_score"] >= 90)
                &
                (candidate_df["address_score"] >= 80)
            ),

            "Name >= 95 AND same ZIP/state": (
                (candidate_df["name_score"] >= 95)
                &
                (
                    candidate_df["candidate_block"]
                    == "ZIP_STATE"
                )
            ),

            "Overall >= 85 AND same ZIP/state": (
                (candidate_df["overall_score"] >= 85)
                &
                (
                    candidate_df["candidate_block"]
                    == "ZIP_STATE"
                )
            ),
        }

        for label, mask in rules.items():

            print(
                f"{label:<40}: "
                f"{mask.sum():,}"
            )

        print("\nTOP REMAINING CANDIDATES")
        print("-" * 78)

        columns = [
            "ccn",
            "cms_name",
            "cms_city",
            "cms_state",
            "cms_source_status",
            "candidate_block",
            "candidate_count",
            "hifld_name",
            "name_score",
            "address_score",
            "overall_score",
            "second_best_score",
            "score_margin",
        ]

        print(
            candidate_df[
                columns
            ]
            .sort_values(
                "overall_score",
                ascending=False,
            )
            .head(40)
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidate_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 78)
    print("REMAINING CANDIDATE ANALYSIS COMPLETE")
    print("=" * 78)

    print(f"Saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    analyze_remaining_candidates()