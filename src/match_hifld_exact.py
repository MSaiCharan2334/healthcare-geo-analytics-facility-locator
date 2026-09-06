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

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_exact_matches.csv"
)


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def normalize_text(value):
    """
    Basic normalization for deterministic entity matching.

    Example:
        "St. Vincent's East"
        -> "ST VINCENTS EAST"
    """

    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    # Remove accents
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    # Standardize ampersand
    value = value.replace("&", " AND ")

    # Remove punctuation
    value = re.sub(
        r"[^A-Z0-9\s]",
        " ",
        value,
    )

    # Collapse multiple spaces
    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_zip(value):
    """
    Convert ZIP/ZIP+4 values to a five-digit ZIP.
    """

    if pd.isna(value):
        return ""

    value = str(value).strip()

    match = re.search(
        r"\d{5}",
        value,
    )

    if match:
        return match.group(0)

    return ""


# ============================================================
# UNIQUE KEY MATCHING
# ============================================================

def match_unique_key(
    cms,
    hifld,
    cms_unmatched,
    hifld_available,
    key_columns,
    match_type,
):
    """
    Match only when a key occurs exactly once in CMS and
    exactly once in HIFLD.

    This prevents ambiguous many-to-one or many-to-many matches.
    """

    cms_subset = cms.loc[
        cms_unmatched
    ].copy()

    hifld_subset = hifld.loc[
        hifld_available
    ].copy()

    # Reject rows where any key component is blank
    cms_valid = cms_subset[
        cms_subset[key_columns]
        .ne("")
        .all(axis=1)
    ].copy()

    hifld_valid = hifld_subset[
        hifld_subset[key_columns]
        .ne("")
        .all(axis=1)
    ].copy()

    # Count key occurrences
    cms_counts = (
        cms_valid
        .groupby(key_columns)
        .size()
        .rename("cms_key_count")
        .reset_index()
    )

    hifld_counts = (
        hifld_valid
        .groupby(key_columns)
        .size()
        .rename("hifld_key_count")
        .reset_index()
    )

    cms_valid = cms_valid.merge(
        cms_counts,
        on=key_columns,
        how="left",
    )

    hifld_valid = hifld_valid.merge(
        hifld_counts,
        on=key_columns,
        how="left",
    )

    # Keep only unique keys on each side
    cms_unique = cms_valid[
        cms_valid["cms_key_count"] == 1
    ].copy()

    hifld_unique = hifld_valid[
        hifld_valid["hifld_key_count"] == 1
    ].copy()

    matches = cms_unique.merge(
        hifld_unique,
        on=key_columns,
        how="inner",
        suffixes=("_cms", "_hifld"),
        validate="one_to_one",
    )

    if matches.empty:
        return matches

    matches["match_type"] = match_type
    matches["match_score"] = 100

    return matches


# ============================================================
# MAIN
# ============================================================

def match_hifld_exact():

    print("=" * 72)
    print("CMS MASTER <-> HIFLD EXACT MATCHING")
    print("=" * 72)

    # --------------------------------------------------------
    # 1. Load
    # --------------------------------------------------------

    cms = pd.read_csv(
        CMS_FILE,
        dtype={
            "ccn": "string",
            "zip_code": "string",
        },
        low_memory=False,
    )

    hifld = pd.read_csv(
        HIFLD_FILE,
        dtype={
            "ID": "string",
            "ZIP": "string",
        },
        low_memory=False,
    )
    cms["cms_index"] = cms.index
    hifld["hifld_index"] = hifld.index
    
    cms["ccn"] = (
        cms["ccn"]
        .str.strip()
        .str.zfill(6)
    )

    print(f"CMS master rows: {len(cms):,}")
    print(f"HIFLD rows: {len(hifld):,}")

    # --------------------------------------------------------
    # 2. Create standardized matching fields
    # --------------------------------------------------------

    cms["match_name"] = (
        cms["hospital_name"]
        .apply(normalize_text)
    )

    cms["match_address"] = (
        cms["address"]
        .apply(normalize_text)
    )

    cms["match_city"] = (
        cms["city"]
        .apply(normalize_text)
    )

    cms["match_state"] = (
        cms["state"]
        .apply(normalize_text)
    )

    cms["match_zip"] = (
        cms["zip_code"]
        .apply(normalize_zip)
    )

    hifld["match_name"] = (
        hifld["NAME"]
        .apply(normalize_text)
    )

    hifld["match_address"] = (
        hifld["ADDRESS"]
        .apply(normalize_text)
    )

    hifld["match_city"] = (
        hifld["CITY"]
        .apply(normalize_text)
    )

    hifld["match_state"] = (
        hifld["STATE"]
        .apply(normalize_text)
    )

    hifld["match_zip"] = (
        hifld["ZIP"]
        .apply(normalize_zip)
    )

    # --------------------------------------------------------
    # 3. Tracking masks
    # --------------------------------------------------------

    cms_unmatched = pd.Series(
        True,
        index=cms.index,
    )

    hifld_available = pd.Series(
        True,
        index=hifld.index,
    )

    all_matches = []

    # --------------------------------------------------------
    # 4. Match pass definitions
    # --------------------------------------------------------

    match_passes = [
        (
            [
                "match_name",
                "match_zip",
                "match_state",
            ],
            "EXACT_NAME_ZIP_STATE",
        ),
        (
            [
                "match_address",
                "match_zip",
                "match_state",
            ],
            "EXACT_ADDRESS_ZIP_STATE",
        ),
        (
            [
                "match_name",
                "match_city",
                "match_state",
            ],
            "EXACT_NAME_CITY_STATE",
        ),
    ]

    # --------------------------------------------------------
    # 5. Sequential exact matching
    # --------------------------------------------------------

    for key_columns, match_type in match_passes:

        matches = match_unique_key(
            cms,
            hifld,
            cms_unmatched,
            hifld_available,
            key_columns,
            match_type,
        )

        if matches.empty:
            print(
                f"{match_type:<30}: 0"
            )
            continue

        cms_indices = (
            matches["cms_index"]
            if "cms_index" in matches.columns
            else None
        )

        print(
            f"{match_type:<30}: "
            f"{len(matches):,}"
        )

        all_matches.append(matches)

        # Identify matched IDs
        matched_ccns = set(
            matches["ccn"]
        )

        matched_hifld_ids = set(
            matches["ID"]
        )

        cms_unmatched = ~cms[
            "ccn"
        ].isin(
            matched_ccns
            | set(
                pd.concat(all_matches)[
                    "ccn"
                ]
            )
        )

        hifld_available = ~hifld[
            "ID"
        ].isin(
            matched_hifld_ids
            | set(
                pd.concat(all_matches)[
                    "ID"
                ]
            )
        )

    # --------------------------------------------------------
    # 6. Combine matches
    # --------------------------------------------------------

    if all_matches:

        matched = pd.concat(
            all_matches,
            ignore_index=True,
        )

    else:

        matched = pd.DataFrame()

    # --------------------------------------------------------
    # 7. Final mapping table
    # --------------------------------------------------------

    if not matched.empty:

        output = matched[
            [
                "ccn",
                "hospital_name",
                "ID",
                "NAME",
                "LATITUDE",
                "LONGITUDE",
                "BEDS",
                "TYPE",
                "STATUS",
                "OWNER",
                "TRAUMA",
                "HELIPAD",
                "match_type",
                "match_score",
            ]
        ].copy()

        output = output.rename(
            columns={
                "ID": "hifld_id",
                "NAME": "hifld_name",
                "LATITUDE": "latitude",
                "LONGITUDE": "longitude",
                "BEDS": "hifld_beds",
                "TYPE": "hifld_type",
                "STATUS": "hifld_status",
                "OWNER": "hifld_owner",
                "TRAUMA": "trauma_level",
                "HELIPAD": "helipad",
            }
        )

        output = output.sort_values(
            "ccn"
        ).reset_index(drop=True)

    else:

        output = pd.DataFrame()

    # --------------------------------------------------------
    # 8. Validation / summary
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 72)

    matched_count = len(output)

    unmatched_count = (
        len(cms)
        - matched_count
    )

    match_rate = (
        matched_count
        / len(cms)
        * 100
    )

    print(
        f"Exact matches: {matched_count:,}"
    )

    print(
        f"CMS hospitals still unmatched: "
        f"{unmatched_count:,}"
    )

    print(
        f"Exact match rate: "
        f"{match_rate:.2f}%"
    )

    if not output.empty:

        print(
            "Duplicate matched CCNs:",
            output["ccn"]
            .duplicated()
            .sum(),
        )

        print(
            "Duplicate matched HIFLD IDs:",
            output["hifld_id"]
            .duplicated()
            .sum(),
        )

        print("\nMatch-type distribution:")

        print(
            output["match_type"]
            .value_counts()
            .to_string()
        )

        assert (
            output["ccn"]
            .duplicated()
            .sum()
            == 0
        )

        assert (
            output["hifld_id"]
            .duplicated()
            .sum()
            == 0
        )

    # --------------------------------------------------------
    # 9. Save mapping
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 72)
    print("EXACT HIFLD MATCHING COMPLETE")
    print("=" * 72)

    print(f"Saved to:\n{OUTPUT_FILE}")

    # --------------------------------------------------------
    # 10. Sample unmatched CMS hospitals
    # --------------------------------------------------------

    matched_ccns = set(
        output["ccn"]
        if not output.empty
        else []
    )

    unmatched = cms[
        ~cms["ccn"].isin(
            matched_ccns
        )
    ]

    print("\nSample unmatched CMS hospitals:")

    print(
        unmatched[
            [
                "ccn",
                "hospital_name",
                "city",
                "state",
                "zip_code",
                "cms_source_status",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )


if __name__ == "__main__":

    # Preserve row identity for matching diagnostics
    match_hifld_exact()