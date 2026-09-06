from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

HIFLD_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_hospitals_clean.csv"
)

MATCH_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hifld_match_master_v2.csv"
)

CMS_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "cms_hospital_master.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hospital_enriched_base.csv"
)


# ============================================================
# MAIN
# ============================================================

def build_enriched_hospital_base():

    print("=" * 80)
    print("BUILDING ENRICHED HOSPITAL BASE")
    print("=" * 80)

    # --------------------------------------------------------
    # 1. Load clean HIFLD base
    # --------------------------------------------------------

    hifld = pd.read_csv(
        HIFLD_FILE,
        dtype={
            "hifld_id": "string",
            "zip_code": "string",
        },
        low_memory=False,
    )

    hifld["hifld_id"] = (
        hifld["hifld_id"]
        .str.strip()
    )

    print(
        f"\nClean HIFLD facilities: "
        f"{len(hifld):,}"
    )

    # --------------------------------------------------------
    # 2. Load accepted CMS <-> HIFLD mapping
    # --------------------------------------------------------

    matches = pd.read_csv(
        MATCH_FILE,
        dtype={
            "hifld_id": "string",
            "ccn": "string",
        },
        low_memory=False,
    )

    matches["hifld_id"] = (
        matches["hifld_id"]
        .str.strip()
    )

    matches["ccn"] = (
        matches["ccn"]
        .str.strip()
        .str.zfill(6)
    )

    print(
        f"Accepted HIFLD-CMS matches: "
        f"{len(matches):,}"
    )

    # Keep only mapping/provenance fields here.
    # HIFLD attributes will come directly from clean HIFLD.
    match_keep = matches[
        [
            "hifld_id",
            "ccn",
            "match_type",
            "match_score",
            "name_score",
            "address_score",
            "score_margin",
            "candidate_block",
        ]
    ].copy()

    # --------------------------------------------------------
    # 3. Load CMS master
    # --------------------------------------------------------

    cms = pd.read_csv(
        CMS_FILE,
        dtype={
            "ccn": "string",
            "zip_code": "string",
        },
        low_memory=False,
    )

    cms["ccn"] = (
        cms["ccn"]
        .str.strip()
        .str.zfill(6)
    )

    print(
        f"CMS master facilities: "
        f"{len(cms):,}"
    )

    # --------------------------------------------------------
    # 4. HIFLD LEFT JOIN -> match mapping
    #
    # HIFLD is the physical/geographic facility base.
    # --------------------------------------------------------

    enriched = hifld.merge(
        match_keep,
        on="hifld_id",
        how="left",
        validate="one_to_one",
    )

    # --------------------------------------------------------
    # 5. Join CMS attributes
    # --------------------------------------------------------

    enriched = enriched.merge(
        cms,
        on="ccn",
        how="left",
        validate="many_to_one",
        suffixes=(
            "_hifld",
            "_cms",
        ),
    )

    # --------------------------------------------------------
    # 6. Coverage flags
    # --------------------------------------------------------

    enriched["has_cms_match"] = (
        enriched["ccn"]
        .notna()
    )

    enriched["data_source_coverage"] = (
        "HIFLD_ONLY"
    )

    enriched.loc[
        enriched["has_cms_match"],
        "data_source_coverage",
    ] = "HIFLD_CMS"

    # --------------------------------------------------------
    # 7. Validation
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 80)

    total_rows = len(enriched)

    duplicate_hifld_ids = (
        enriched["hifld_id"]
        .duplicated()
        .sum()
    )

    missing_hifld_ids = (
        enriched["hifld_id"]
        .isna()
        .sum()
    )

    missing_coordinates = (
        enriched[
            [
                "latitude",
                "longitude",
            ]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    matched_rows = (
        enriched["has_cms_match"]
        .sum()
    )

    unmatched_rows = (
        (~enriched["has_cms_match"])
        .sum()
    )

    duplicate_matched_ccns = (
        enriched.loc[
            enriched["has_cms_match"],
            "ccn",
        ]
        .duplicated()
        .sum()
    )

    print(
        f"Enriched hospital rows: "
        f"{total_rows:,}"
    )

    print(
        f"Duplicate HIFLD IDs: "
        f"{duplicate_hifld_ids:,}"
    )

    print(
        f"Missing HIFLD IDs: "
        f"{missing_hifld_ids:,}"
    )

    print(
        f"Missing coordinates: "
        f"{missing_coordinates:,}"
    )

    print(
        f"HIFLD facilities with CMS enrichment: "
        f"{matched_rows:,}"
    )

    print(
        f"HIFLD-only facilities: "
        f"{unmatched_rows:,}"
    )

    print(
        f"Duplicate matched CMS CCNs: "
        f"{duplicate_matched_ccns:,}"
    )

    cms_coverage = (
        matched_rows
        / total_rows
        * 100
    )

    print(
        f"CMS enrichment coverage of HIFLD base: "
        f"{cms_coverage:.2f}%"
    )

    print("\nData-source coverage:")

    print(
        enriched[
            "data_source_coverage"
        ]
        .value_counts()
        .to_string()
    )

    print("\nMatch-type distribution:")

    print(
        enriched[
            "match_type"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    # --------------------------------------------------------
    # 8. CMS field availability
    # --------------------------------------------------------

    print("\nCMS ENRICHMENT FIELD AVAILABILITY")
    print("-" * 80)

    fields_to_check = [
        "hospital_name",
        "hospital_type",
        "hospital_ownership",
        "emergency_services",
        "hospital_overall_rating",
        "Number of Beds",
        "Total Patient Revenue",
        "Net Patient Revenue",
        "Inpatient Revenue",
        "Outpatient Revenue",
        "Total Costs",
        "Net Income",
        "Net Revenue from Medicaid",
        "Medicaid Charges",
    ]

    for field in fields_to_check:

        if field in enriched.columns:

            populated = (
                enriched[field]
                .notna()
                .sum()
            )

            print(
                f"{field:<35}: "
                f"{populated:,}"
            )

    # --------------------------------------------------------
    # 9. Hard checks
    # --------------------------------------------------------

    assert total_rows == 8339
    assert duplicate_hifld_ids == 0
    assert missing_hifld_ids == 0
    assert missing_coordinates == 0

    # Accepted linkage layer contains 5,391 matches.
    assert matched_rows == 5391

    # Linkage is one-to-one.
    assert duplicate_matched_ccns == 0

    # --------------------------------------------------------
    # 10. Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    enriched.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 80)
    print("ENRICHED HOSPITAL BASE COMPLETE")
    print("=" * 80)

    print(f"Saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    build_enriched_hospital_base()