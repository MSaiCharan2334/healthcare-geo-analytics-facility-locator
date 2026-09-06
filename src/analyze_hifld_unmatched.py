from pathlib import Path
import re
import unicodedata

import pandas as pd


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

    value = value.replace(
        "&",
        " AND ",
    )

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
# PREPARE MATCHING FIELDS
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
# EXACT COLLISION CHECK
# ============================================================

def find_collisions(
    unmatched,
    used_hifld,
    key_columns,
    collision_type,
):

    cms_valid = unmatched[
        unmatched[key_columns]
        .ne("")
        .all(axis=1)
    ].copy()

    hifld_valid = used_hifld[
        used_hifld[key_columns]
        .ne("")
        .all(axis=1)
    ].copy()

    collisions = cms_valid.merge(
        hifld_valid,
        on=key_columns,
        how="inner",
        suffixes=("_cms", "_hifld"),
    )

    if not collisions.empty:
        collisions["collision_type"] = (
            collision_type
        )

    return collisions


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_unmatched():

    print("=" * 75)
    print("CMS <-> HIFLD UNMATCHED / COLLISION ANALYSIS")
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
    # Matched / unmatched pools
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

    used_hifld = hifld[
        hifld["ID"].isin(
            used_hifld_ids
        )
    ].copy()

    available_hifld = hifld[
        ~hifld["ID"].isin(
            used_hifld_ids
        )
    ].copy()

    print(f"\nCMS master rows: {len(cms):,}")
    print(f"Already matched CMS: {len(exact):,}")
    print(f"Unmatched CMS: {len(unmatched):,}")

    print(f"\nHIFLD rows: {len(hifld):,}")
    print(f"Already used HIFLD: {len(used_hifld):,}")
    print(
        f"Available HIFLD for future matching: "
        f"{len(available_hifld):,}"
    )

    # --------------------------------------------------------
    # Source status of unmatched CMS
    # --------------------------------------------------------

    print("\nUNMATCHED CMS SOURCE STATUS")
    print("-" * 75)

    print(
        unmatched[
            "cms_source_status"
        ]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Connect used HIFLD facilities to the CMS CCN that
    # already claimed them
    # --------------------------------------------------------

    used_hifld = used_hifld.merge(
        exact[
            [
                "hifld_id",
                "ccn",
            ]
        ],
        left_on="ID",
        right_on="hifld_id",
        how="left",
        validate="one_to_one",
    )

    used_hifld = used_hifld.rename(
        columns={
            "ccn": "already_matched_ccn"
        }
    )

    # --------------------------------------------------------
    # Collision analysis
    #
    # These are unmatched CMS records that have an exact
    # identity key pointing to a HIFLD facility already used
    # by another CMS CCN.
    # --------------------------------------------------------

    collision_passes = [
        (
            [
                "match_name",
                "match_zip",
                "match_state",
            ],
            "NAME_ZIP_STATE_COLLISION",
        ),
        (
            [
                "match_address",
                "match_zip",
                "match_state",
            ],
            "ADDRESS_ZIP_STATE_COLLISION",
        ),
        (
            [
                "match_name",
                "match_city",
                "match_state",
            ],
            "NAME_CITY_STATE_COLLISION",
        ),
    ]

    all_collisions = []

    for keys, collision_type in collision_passes:

        collision = find_collisions(
            unmatched,
            used_hifld,
            keys,
            collision_type,
        )

        print(
            f"{collision_type:<35}: "
            f"{collision['ccn'].nunique() if not collision.empty else 0:,}"
        )

        if not collision.empty:
            all_collisions.append(
                collision
            )

    # --------------------------------------------------------
    # Consolidate collision CCNs
    # --------------------------------------------------------

    if all_collisions:

        collision_df = pd.concat(
            all_collisions,
            ignore_index=True,
        )

        collision_ccns = set(
            collision_df["ccn"]
        )

    else:

        collision_df = pd.DataFrame()
        collision_ccns = set()

    print("\nCOLLISION SUMMARY")
    print("-" * 75)

    print(
        "Unique unmatched CMS CCNs that point to "
        "an already-used HIFLD facility:",
        f"{len(collision_ccns):,}"
    )

    clean_unmatched = unmatched[
        ~unmatched["ccn"].isin(
            collision_ccns
        )
    ].copy()

    print(
        "Remaining CMS records suitable for "
        "future candidate/fuzzy matching:",
        f"{len(clean_unmatched):,}"
    )

    # --------------------------------------------------------
    # Candidate availability diagnostics
    # --------------------------------------------------------

    zip_candidates = clean_unmatched.merge(
        available_hifld[
            [
                "ID",
                "match_zip",
                "match_state",
            ]
        ],
        on=[
            "match_zip",
            "match_state",
        ],
        how="inner",
    )

    city_candidates = clean_unmatched.merge(
        available_hifld[
            [
                "ID",
                "match_city",
                "match_state",
            ]
        ],
        on=[
            "match_city",
            "match_state",
        ],
        how="inner",
    )

    print("\nAVAILABLE CANDIDATE COVERAGE")
    print("-" * 75)

    print(
        "Clean unmatched CMS hospitals with at least "
        "one HIFLD candidate in same ZIP/state:",
        f"{zip_candidates['ccn'].nunique():,}"
    )

    print(
        "Clean unmatched CMS hospitals with at least "
        "one HIFLD candidate in same city/state:",
        f"{city_candidates['ccn'].nunique():,}"
    )

    # --------------------------------------------------------
    # Samples
    # --------------------------------------------------------

    if not collision_df.empty:

        print("\nSAMPLE COLLISIONS")
        print("-" * 75)

        sample_columns = [
            "ccn",
            "hospital_name",
            "city",
            "state",
            "cms_source_status",
            "already_matched_ccn",
            "NAME",
            "CITY",
            "STATE",
            "ID",
            "collision_type",
        ]

        sample_columns = [
            column
            for column in sample_columns
            if column in collision_df.columns
        ]

        print(
            collision_df[
                sample_columns
            ]
            .drop_duplicates(
                subset=[
                    "ccn",
                    "already_matched_ccn",
                ]
            )
            .head(25)
            .to_string(index=False)
        )

    print("\nSAMPLE CLEAN UNMATCHED CMS HOSPITALS")
    print("-" * 75)

    print(
        clean_unmatched[
            [
                "ccn",
                "hospital_name",
                "city",
                "state",
                "zip_code",
                "cms_source_status",
            ]
        ]
        .head(25)
        .to_string(index=False)
    )


if __name__ == "__main__":
    analyze_unmatched()