from pathlib import Path
import re

import pandas as pd


# ============================================================
# PATH CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cities"
    / "2025_Gaz_place_national.txt"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cities.csv"
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_place_name(name):
    """
    Create a user-friendly city/place name while preserving
    the original Census place name in another column.

    Examples:
        "Abbeville city"      -> "Abbeville"
        "Addison town"        -> "Addison"
        "Abanda CDP"          -> "Abanda"
        "Alexander City city" -> "Alexander City"
    """

    if pd.isna(name):
        return None

    cleaned = str(name).strip()

    suffix_patterns = [
        r"\s+CDP$",
        r"\s+city$",
        r"\s+town$",
        r"\s+village$",
        r"\s+borough$",
        r"\s+municipality$",
    ]

    for pattern in suffix_patterns:
        cleaned = re.sub(
            pattern,
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    return cleaned.strip()


def infer_place_type(name):
    """
    Derive a readable place type from the official Census name.
    """

    if pd.isna(name):
        return "Other"

    name_lower = str(name).strip().lower()

    if name_lower.endswith(" cdp"):
        return "CDP"

    if name_lower.endswith(" city"):
        return "City"

    if name_lower.endswith(" town"):
        return "Town"

    if name_lower.endswith(" village"):
        return "Village"

    if name_lower.endswith(" borough"):
        return "Borough"

    if name_lower.endswith(" municipality"):
        return "Municipality"

    return "Other"


# ============================================================
# TRANSFORMATION
# ============================================================

def transform_cities():

    print("=" * 65)
    print("TRANSFORMING CENSUS PLACES DATA")
    print("=" * 65)

    # --------------------------------------------------------
    # 1. LOAD RAW DATA
    # --------------------------------------------------------

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Census input file not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        sep="|",
        dtype=str,
    )

    # Remove accidental whitespace from column headers
    df.columns = df.columns.str.strip()

    print(f"Raw rows: {len(df):,}")
    print(f"Raw columns: {len(df.columns):,}")

    # --------------------------------------------------------
    # 2. VERIFY REQUIRED COLUMNS
    # --------------------------------------------------------

    required_columns = [
        "GEOID",
        "NAME",
        "USPS",
        "LSAD",
        "FUNCSTAT",
        "INTPTLAT",
        "INTPTLONG",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Required Census columns are missing: "
            + ", ".join(missing_columns)
        )

    # --------------------------------------------------------
    # 3. KEEP ONLY PROJECT-RELEVANT FIELDS
    # --------------------------------------------------------

    cities = df[
        [
            "GEOID",
            "NAME",
            "USPS",
            "LSAD",
            "FUNCSTAT",
            "INTPTLAT",
            "INTPTLONG",
        ]
    ].copy()

    # --------------------------------------------------------
    # 4. RENAME COLUMNS
    # --------------------------------------------------------

    cities = cities.rename(
        columns={
            "GEOID": "city_id",
            "NAME": "city_name_original",
            "USPS": "state",
            "LSAD": "place_type_code",
            "FUNCSTAT": "functional_status",
            "INTPTLAT": "latitude",
            "INTPTLONG": "longitude",
        }
    )

    # --------------------------------------------------------
    # 5. CLEAN STRING FIELDS
    # --------------------------------------------------------

    string_columns = [
        "city_id",
        "city_name_original",
        "state",
        "place_type_code",
        "functional_status",
    ]

    for column in string_columns:
        cities[column] = (
            cities[column]
            .astype("string")
            .str.strip()
        )

    cities["state"] = cities["state"].str.upper()

    # --------------------------------------------------------
    # 6. CREATE CLEAN CITY / PLACE NAME
    # --------------------------------------------------------

    cities["city_name"] = (
        cities["city_name_original"]
        .apply(clean_place_name)
    )

    cities["place_type"] = (
        cities["city_name_original"]
        .apply(infer_place_type)
    )

    # --------------------------------------------------------
    # 7. CREATE BASIC POWER BI DISPLAY LABEL
    # --------------------------------------------------------

    cities["city_display"] = (
        cities["city_name"]
        + ", "
        + cities["state"]
    )

    # --------------------------------------------------------
    # 8. HANDLE DUPLICATE CITY + STATE NAMES
    #
    # Example:
    # Some Census places may clean to the same:
    #
    #     Example, PA
    #     Example, PA
    #
    # Power BI should not treat those as one selectable place.
    #
    # Normal places remain:
    #     Dallas, TX
    #
    # Ambiguous places become:
    #     Example, PA (CDP - 4212345)
    # --------------------------------------------------------

    duplicate_display_mask = (
        cities["city_display"]
        .duplicated(keep=False)
    )

    cities["city_display_unique"] = (
        cities["city_display"]
    )

    cities.loc[
        duplicate_display_mask,
        "city_display_unique",
    ] = (
        cities.loc[
            duplicate_display_mask,
            "city_display",
        ]
        + " ("
        + cities.loc[
            duplicate_display_mask,
            "place_type",
        ]
        + " - "
        + cities.loc[
            duplicate_display_mask,
            "city_id",
        ]
        + ")"
    )

    # --------------------------------------------------------
    # 9. CONVERT COORDINATES TO NUMERIC
    # --------------------------------------------------------

    cities["latitude"] = pd.to_numeric(
        cities["latitude"],
        errors="coerce",
    )

    cities["longitude"] = pd.to_numeric(
        cities["longitude"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # 10. FINAL COLUMN ORDER
    # --------------------------------------------------------

    cities = cities[
        [
            "city_id",
            "city_name",
            "city_name_original",
            "city_display",
            "city_display_unique",
            "state",
            "place_type",
            "place_type_code",
            "functional_status",
            "latitude",
            "longitude",
        ]
    ]

    # --------------------------------------------------------
    # 11. VALIDATION
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 65)

    processed_rows = len(cities)

    duplicate_city_ids = (
        cities["city_id"]
        .duplicated()
        .sum()
    )

    missing_city_ids = (
        cities["city_id"]
        .isna()
        .sum()
    )

    missing_city_names = (
        cities["city_name"]
        .isna()
        .sum()
    )

    missing_coordinates = (
        cities[
            ["latitude", "longitude"]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    invalid_latitudes = (
        (cities["latitude"] < -90)
        | (cities["latitude"] > 90)
    ).sum()

    invalid_longitudes = (
        (cities["longitude"] < -180)
        | (cities["longitude"] > 180)
    ).sum()

    duplicate_basic_labels = (
        cities["city_display"]
        .duplicated(keep=False)
        .sum()
    )

    duplicate_unique_labels = (
        cities["city_display_unique"]
        .duplicated()
        .sum()
    )

    print(f"Processed rows: {processed_rows:,}")
    print(f"Missing city IDs: {missing_city_ids:,}")
    print(f"Duplicate city IDs: {duplicate_city_ids:,}")
    print(f"Missing city names: {missing_city_names:,}")
    print(f"Missing coordinates: {missing_coordinates:,}")
    print(f"Invalid latitude values: {invalid_latitudes:,}")
    print(f"Invalid longitude values: {invalid_longitudes:,}")

    print(
        "Rows sharing the same City, State label: "
        f"{duplicate_basic_labels:,}"
    )

    print(
        "Duplicate unique slicer labels: "
        f"{duplicate_unique_labels:,}"
    )

    # --------------------------------------------------------
    # 12. HARD QUALITY CHECKS
    # --------------------------------------------------------

    assert processed_rows > 0, (
        "Processed cities dataset is empty."
    )

    assert missing_city_ids == 0, (
        "Missing Census GEOIDs detected."
    )

    assert duplicate_city_ids == 0, (
        "Duplicate Census GEOIDs detected."
    )

    assert missing_city_names == 0, (
        "Missing city/place names detected."
    )

    assert missing_coordinates == 0, (
        "Missing latitude/longitude detected."
    )

    assert invalid_latitudes == 0, (
        "Invalid latitude values detected."
    )

    assert invalid_longitudes == 0, (
        "Invalid longitude values detected."
    )

    assert duplicate_unique_labels == 0, (
        "Power BI city slicer labels are not unique."
    )

    # --------------------------------------------------------
    # 13. SAVE PROCESSED DATA
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cities.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # 14. OUTPUT SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("CITY TRANSFORMATION COMPLETE")
    print("=" * 65)

    print(f"Saved to:\n{OUTPUT_FILE}")

    print("\nPlace type distribution:")
    print(
        cities["place_type"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nSample processed records:")

    print(
        cities[
            [
                "city_id",
                "city_name",
                "city_display_unique",
                "state",
                "place_type",
                "latitude",
                "longitude",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )

    # Show a few examples where duplicate labels
    # required disambiguation
    duplicate_examples = cities[
        duplicate_display_mask
    ][
        [
            "city_id",
            "city_name_original",
            "city_display",
            "city_display_unique",
        ]
    ].head(10)

    if not duplicate_examples.empty:

        print("\nExample duplicate-name resolutions:")

        print(
            duplicate_examples
            .to_string(index=False)
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    transform_cities()