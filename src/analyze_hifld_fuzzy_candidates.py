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
    / "hifld_fuzzy_candidates.csv"
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
# PREP DATA
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
# SIMILARITY
# ============================================================

def similarity_score(cms_row, hifld_row):

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

    # Name is the strongest signal.
    # Address adds confidence.
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

def analyze_fuzzy_candidates():

    print("=" * 75)
    print("CMS <-> HIFLD FUZZY CANDIDATE ANALYSIS")
    print("=" * 75)

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

    exact = pd.read_csv(
        EXACT_MATCH_FILE,
        dtype={
            "ccn": "string",
            "hifld_id": "string",
        },
        low_memory=False,
    )

    cms = prepare_cms(cms)
    hifld = prepare_hifld(hifld)

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
    # Remove already matched records
    # --------------------------------------------------------

    matched_ccns = set(
        exact["ccn"]
    )

    used_hifld_ids = set(
        exact["hifld_id"]
    )

    unmatched = cms[
        ~cms["ccn"].isin(
            matched_ccns
        )
    ].copy()

    available_hifld = hifld[
        ~hifld["ID"].isin(
            used_hifld_ids
        )
    ].copy()

    # --------------------------------------------------------
    # Remove known collision CCNs
    #
    # Detect unmatched CMS rows that exactly match an
    # already-used HIFLD facility on any strong identity key.
    # --------------------------------------------------------

    used_hifld = hifld[
        hifld["ID"].isin(
            used_hifld_ids
        )
    ].copy()

    collision_ccns = set()

    collision_keys = [
        [
            "match_name",
            "match_zip",
            "match_state",
        ],
        [
            "match_address",
            "match_zip",
            "match_state",
        ],
        [
            "match_name",
            "match_city",
            "match_state",
        ],
    ]

    for keys in collision_keys:

        cms_valid = unmatched[
            unmatched[keys]
            .ne("")
            .all(axis=1)
        ]

        hifld_valid = used_hifld[
            used_hifld[keys]
            .ne("")
            .all(axis=1)
        ]

        collisions = cms_valid.merge(
            hifld_valid,
            on=keys,
            how="inner",
        )

        if not collisions.empty:
            collision_ccns.update(
                collisions["ccn"]
            )

    clean_unmatched = unmatched[
        ~unmatched["ccn"].isin(
            collision_ccns
        )
    ].copy()

    print(
        f"Clean unmatched CMS hospitals: "
        f"{len(clean_unmatched):,}"
    )

    print(
        f"Available HIFLD hospitals: "
        f"{len(available_hifld):,}"
    )

    # --------------------------------------------------------
    # Build candidate results
    # --------------------------------------------------------

    results = []

    for _, cms_row in clean_unmatched.iterrows():

        # ----------------------------------------------------
        # Primary block: same ZIP + state
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Fallback: same city + state
        # ----------------------------------------------------

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

        scored_candidates = []

        for _, hifld_row in candidates.iterrows():

            (
                name_score,
                address_score,
                overall_score,
            ) = similarity_score(
                cms_row,
                hifld_row,
            )

            scored_candidates.append(
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

        scored_candidates = sorted(
            scored_candidates,
            key=lambda x: x["overall_score"],
            reverse=True,
        )

        best = scored_candidates[0]

        second_score = (
            scored_candidates[1]["overall_score"]
            if len(scored_candidates) > 1
            else None
        )

        margin = (
            best["overall_score"] - second_score
            if second_score is not None
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
                "candidate_count": len(
                    scored_candidates
                ),
                **best,
                "second_best_score": second_score,
                "score_margin": (
                    round(margin, 2)
                    if margin is not None
                    else None
                ),
            }
        )

    candidate_df = pd.DataFrame(results)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\nCANDIDATE COVERAGE")
    print("-" * 75)

    print(
        "CMS hospitals with at least one candidate:",
        f"{len(candidate_df):,}"
    )

    print(
        "CMS hospitals with no candidate:",
        f"{len(clean_unmatched) - len(candidate_df):,}"
    )

    if not candidate_df.empty:

        print("\nCandidate blocking method:")

        print(
            candidate_df[
                "candidate_block"
            ]
            .value_counts()
            .to_string()
        )

        print("\nBest overall score distribution:")

        print(
            candidate_df[
                "overall_score"
            ]
            .describe()
            .to_string()
        )

        print("\nScore thresholds:")

        for threshold in [
            95,
            90,
            85,
            80,
            75,
        ]:

            count = (
                candidate_df[
                    "overall_score"
                ]
                >= threshold
            ).sum()

            print(
                f">= {threshold}: "
                f"{count:,}"
            )

        print(
            "\nHigh-confidence candidates "
            "(score >= 90 and margin >= 10):"
        )

        high_confidence = candidate_df[
            (
                candidate_df[
                    "overall_score"
                ] >= 90
            )
            &
            (
                candidate_df[
                    "score_margin"
                ].isna()
                |
                (
                    candidate_df[
                        "score_margin"
                    ] >= 10
                )
            )
        ]

        print(
            f"{len(high_confidence):,}"
        )

        print("\nTop sample candidates:")
        print("-" * 75)

        sample_columns = [
            "ccn",
            "cms_name",
            "cms_city",
            "cms_state",
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
                sample_columns
            ]
            .sort_values(
                "overall_score",
                ascending=False,
            )
            .head(30)
            .to_string(index=False)
        )

    # --------------------------------------------------------
    # Save for review
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

    print("\n" + "=" * 75)
    print("FUZZY CANDIDATE ANALYSIS COMPLETE")
    print("=" * 75)

    print(f"Saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    analyze_fuzzy_candidates()