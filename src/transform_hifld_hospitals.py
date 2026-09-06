from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
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
    / "hifld_hospitals_clean.csv"
)


# ============================================================
# PROJECT GEOGRAPHIC SCOPE
# ============================================================

# United States + U.S. territories present in HIFLD.
# PLW (Palau) is excluded.
US_SCOPE_COUNTRIES = {
    "USA",
    "PRI",
    "GUM",
    "VIR",
    "ASM",
    "MNP",
}


TEXT_SENTINELS = {
    "",
    "-999",
    "NOT AVAILABLE",
    "NOT APPLICABLE",
    "UNKNOWN",
    "N/A",
    "NA",
    "NONE",
    "NULL",
}


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):

    if pd.isna(value):
        return pd.NA

    value = str(value).strip()

    if value.upper() in TEXT_SENTINELS:
        return pd.NA

    return value


def clean_numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce",
    )


# ============================================================
# TRANSFORMATION
# ============================================================

def transform_hifld():

    print("=" * 78)
    print("TRANSFORMING HIFLD HOSPITAL BASE")
    print("=" * 78)

    df = pd.read_csv(
        INPUT_FILE,
        dtype={
            "ID": "string",
            "ZIP": "string",
            "ZIP4": "string",
            "STATE_ID": "string",
            "COUNTYFIPS": "string",
        },
        low_memory=False,
    )

    print(f"\nRaw HIFLD rows: {len(df):,}")

    # --------------------------------------------------------
    # 1. Geographic scope
    # --------------------------------------------------------

    df["COUNTRY"] = (
        df["COUNTRY"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    excluded = df[
        ~df["COUNTRY"].isin(
            US_SCOPE_COUNTRIES
        )
    ].copy()

    hospitals = df[
        df["COUNTRY"].isin(
            US_SCOPE_COUNTRIES
        )
    ].copy()

    print(
        f"Rows retained in U.S./territory scope: "
        f"{len(hospitals):,}"
    )

    print(
        f"Rows excluded from scope: "
        f"{len(excluded):,}"
    )

    if not excluded.empty:

        print("\nExcluded country codes:")

        print(
            excluded["COUNTRY"]
            .value_counts(dropna=False)
            .to_string()
        )

    # --------------------------------------------------------
    # 2. Select useful columns
    # --------------------------------------------------------

    columns = [
        "ID",
        "NAME",
        "ALT_NAME",
        "ADDRESS",
        "CITY",
        "STATE",
        "ZIP",
        "ZIP4",
        "COUNTY",
        "COUNTYFIPS",
        "COUNTRY",
        "TELEPHONE",
        "TYPE",
        "STATUS",
        "OWNER",
        "BEDS",
        "TRAUMA",
        "HELIPAD",
        "LATITUDE",
        "LONGITUDE",
        "WEBSITE",
        "SOURCE",
        "SOURCEDATE",
        "VAL_METHOD",
        "VAL_DATE",
        "NAICS_CODE",
        "NAICS_DESC",
    ]

    hospitals = hospitals[
        [
            col
            for col in columns
            if col in hospitals.columns
        ]
    ].copy()

    # --------------------------------------------------------
    # 3. Rename to project-standard fields
    # --------------------------------------------------------

    hospitals = hospitals.rename(
        columns={
            "ID": "hifld_id",
            "NAME": "hifld_name",
            "ALT_NAME": "alternate_name",
            "ADDRESS": "address",
            "CITY": "city",
            "STATE": "state",
            "ZIP": "zip_code",
            "ZIP4": "zip4",
            "COUNTY": "county",
            "COUNTYFIPS": "county_fips",
            "COUNTRY": "country_code",
            "TELEPHONE": "telephone",
            "TYPE": "hifld_type",
            "STATUS": "hifld_status",
            "OWNER": "hifld_owner",
            "BEDS": "hifld_beds",
            "TRAUMA": "trauma_level",
            "HELIPAD": "helipad",
            "LATITUDE": "latitude",
            "LONGITUDE": "longitude",
            "WEBSITE": "website",
            "SOURCE": "hifld_source",
            "SOURCEDATE": "hifld_source_date",
            "VAL_METHOD": "validation_method",
            "VAL_DATE": "validation_date",
            "NAICS_CODE": "naics_code",
            "NAICS_DESC": "naics_description",
        }
    )

    # --------------------------------------------------------
    # 4. Normalize identifier
    # --------------------------------------------------------

    hospitals["hifld_id"] = (
        hospitals["hifld_id"]
        .astype("string")
        .str.strip()
    )

    # --------------------------------------------------------
    # 5. Clean text fields
    # --------------------------------------------------------

    text_columns = [
        "hifld_name",
        "alternate_name",
        "address",
        "city",
        "state",
        "zip_code",
        "zip4",
        "county",
        "county_fips",
        "country_code",
        "telephone",
        "hifld_type",
        "hifld_status",
        "hifld_owner",
        "trauma_level",
        "helipad",
        "website",
        "hifld_source",
        "hifld_source_date",
        "validation_method",
        "validation_date",
        "naics_code",
        "naics_description",
    ]

    for column in text_columns:

        if column in hospitals.columns:

            hospitals[column] = (
                hospitals[column]
                .apply(clean_text)
                .astype("string")
            )

    # --------------------------------------------------------
    # 6. Clean geographic fields
    # --------------------------------------------------------

    hospitals["latitude"] = clean_numeric(
        hospitals["latitude"]
    )

    hospitals["longitude"] = clean_numeric(
        hospitals["longitude"]
    )

    # --------------------------------------------------------
    # 7. Clean bed counts
    #
    # HIFLD uses negative / zero sentinel-like values.
    # We do not treat these as real bed counts.
    # --------------------------------------------------------

    hospitals["hifld_beds"] = clean_numeric(
        hospitals["hifld_beds"]
    )

    invalid_beds_before = (
        hospitals["hifld_beds"]
        .notna()
        &
        (
            hospitals["hifld_beds"]
            <= 0
        )
    ).sum()

    hospitals.loc[
        hospitals["hifld_beds"] <= 0,
        "hifld_beds",
    ] = pd.NA

    hospitals["hifld_beds"] = (
        hospitals["hifld_beds"]
        .round()
        .astype("Int64")
    )

    # --------------------------------------------------------
    # 8. Standardize common categorical fields
    # --------------------------------------------------------

    for column in [
        "state",
        "country_code",
        "hifld_status",
    ]:

        hospitals[column] = (
            hospitals[column]
            .str.strip()
            .str.upper()
        )

    # --------------------------------------------------------
    # 9. Useful locator flags
    # --------------------------------------------------------

    hospitals["is_open"] = (
        hospitals["hifld_status"]
        == "OPEN"
    )

    hospitals["has_valid_beds"] = (
        hospitals["hifld_beds"]
        .notna()
    )

    # --------------------------------------------------------
    # 10. Validation
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 78)

    duplicate_ids = (
        hospitals["hifld_id"]
        .duplicated()
        .sum()
    )

    missing_ids = (
        hospitals["hifld_id"]
        .isna()
        .sum()
    )

    missing_names = (
        hospitals["hifld_name"]
        .isna()
        .sum()
    )

    missing_coordinates = (
        hospitals[
            [
                "latitude",
                "longitude",
            ]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    invalid_latitudes = (
        (hospitals["latitude"] < -90)
        |
        (hospitals["latitude"] > 90)
    ).sum()

    invalid_longitudes = (
        (hospitals["longitude"] < -180)
        |
        (hospitals["longitude"] > 180)
    ).sum()

    print(
        f"Processed HIFLD rows: "
        f"{len(hospitals):,}"
    )

    print(
        f"Duplicate HIFLD IDs: "
        f"{duplicate_ids:,}"
    )

    print(
        f"Missing HIFLD IDs: "
        f"{missing_ids:,}"
    )

    print(
        f"Missing hospital names: "
        f"{missing_names:,}"
    )

    print(
        f"Missing coordinates: "
        f"{missing_coordinates:,}"
    )

    print(
        f"Invalid latitude values: "
        f"{invalid_latitudes:,}"
    )

    print(
        f"Invalid longitude values: "
        f"{invalid_longitudes:,}"
    )

    print(
        f"Bed values converted to null: "
        f"{invalid_beds_before:,}"
    )

    print(
        f"Hospitals with valid bed counts: "
        f"{hospitals['has_valid_beds'].sum():,}"
    )

    print("\nStatus distribution:")

    print(
        hospitals["hifld_status"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nCountry / territory distribution:")

    print(
        hospitals["country_code"]
        .value_counts(dropna=False)
        .to_string()
    )

    # --------------------------------------------------------
    # 11. Hard checks
    # --------------------------------------------------------

    assert duplicate_ids == 0
    assert missing_ids == 0
    assert missing_names == 0
    assert missing_coordinates == 0
    assert invalid_latitudes == 0
    assert invalid_longitudes == 0

    # Raw HIFLD had 8,340 rows and one Palau record.
    assert len(hospitals) == 8339

    # --------------------------------------------------------
    # 12. Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    hospitals.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 78)
    print("HIFLD HOSPITAL BASE COMPLETE")
    print("=" * 78)

    print(f"Saved to:\n{OUTPUT_FILE}")


if __name__ == "__main__":
    transform_hifld()