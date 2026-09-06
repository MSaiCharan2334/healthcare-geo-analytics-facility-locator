from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CITIES_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cities.csv"
)

AIRPORTS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "airports.csv"
)

HOSPITALS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hospitals.csv"
)


# ============================================================
# HELPERS
# ============================================================

def validate_coordinates(
    df,
    latitude_col,
    longitude_col,
    dataset_name,
):
    missing = (
        df[
            [
                latitude_col,
                longitude_col,
            ]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    invalid_lat = (
        (df[latitude_col] < -90)
        |
        (df[latitude_col] > 90)
    ).sum()

    invalid_lon = (
        (df[longitude_col] < -180)
        |
        (df[longitude_col] > 180)
    ).sum()

    print(
        f"{dataset_name} missing coordinates: "
        f"{missing:,}"
    )

    print(
        f"{dataset_name} invalid latitudes: "
        f"{invalid_lat:,}"
    )

    print(
        f"{dataset_name} invalid longitudes: "
        f"{invalid_lon:,}"
    )

    assert missing == 0
    assert invalid_lat == 0
    assert invalid_lon == 0


# ============================================================
# MAIN
# ============================================================

def validate_processed_data():

    print("=" * 82)
    print("FINAL PROCESSED DATA VALIDATION")
    print("=" * 82)

    # --------------------------------------------------------
    # 1. Load datasets
    # --------------------------------------------------------

    cities = pd.read_csv(
        CITIES_FILE,
        dtype={
            "city_id": "string",
            "state": "string",
        },
        low_memory=False,
    )

    airports = pd.read_csv(
        AIRPORTS_FILE,
        dtype={
            "airport_id": "string",
            "iata_code": "string",
        },
        low_memory=False,
    )

    hospitals = pd.read_csv(
        HOSPITALS_FILE,
        dtype={
            "hospital_id": "string",
            "ccn": "string",
        },
        low_memory=False,
    )

    # ========================================================
    # CITIES
    # ========================================================

    print("\n" + "=" * 82)
    print("CITIES")
    print("=" * 82)

    print(
        f"Rows: {len(cities):,}"
    )

    print(
        "Duplicate city IDs:",
        cities["city_id"]
        .duplicated()
        .sum(),
    )

    print(
        "Missing city IDs:",
        cities["city_id"]
        .isna()
        .sum(),
    )

    print(
        "Missing city names:",
        cities["city_name"]
        .isna()
        .sum(),
    )

    print(
        "Duplicate slicer labels:",
        cities["city_display_unique"]
        .duplicated()
        .sum(),
    )

    validate_coordinates(
        cities,
        "latitude",
        "longitude",
        "Cities",
    )

    assert len(cities) == 32350

    assert (
        cities["city_id"]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        cities["city_id"]
        .isna()
        .sum()
        == 0
    )

    assert (
        cities["city_name"]
        .isna()
        .sum()
        == 0
    )

    assert (
        cities["city_display_unique"]
        .duplicated()
        .sum()
        == 0
    )

    # ========================================================
    # AIRPORTS
    # ========================================================

    print("\n" + "=" * 82)
    print("AIRPORTS")
    print("=" * 82)

    print(
        f"Rows: {len(airports):,}"
    )

    print(
        "Duplicate airport IDs:",
        airports["airport_id"]
        .duplicated()
        .sum(),
    )

    print(
        "Duplicate IATA codes:",
        airports["iata_code"]
        .duplicated()
        .sum(),
    )

    print(
        "Missing IATA codes:",
        airports["iata_code"]
        .isna()
        .sum(),
    )

    print(
        "Duplicate display labels:",
        airports["airport_display"]
        .duplicated()
        .sum(),
    )

    validate_coordinates(
        airports,
        "latitude",
        "longitude",
        "Airports",
    )

    assert len(airports) == 634

    assert (
        airports["airport_id"]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        airports["iata_code"]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        airports["iata_code"]
        .isna()
        .sum()
        == 0
    )

    assert (
        airports["airport_display"]
        .duplicated()
        .sum()
        == 0
    )

    # Major-airport sanity check
    required_airports = {
        "ATL",
        "DFW",
        "JFK",
        "LAX",
        "ORD",
        "SEA",
        "SFO",
    }

    existing_airports = set(
        airports["iata_code"]
        .dropna()
    )

    missing_major_airports = (
        required_airports
        - existing_airports
    )

    print(
        "Missing major-airport sanity checks:",
        missing_major_airports,
    )

    assert len(
        missing_major_airports
    ) == 0

    # ========================================================
    # HOSPITALS
    # ========================================================

    print("\n" + "=" * 82)
    print("HOSPITALS")
    print("=" * 82)

    print(
        f"Rows: {len(hospitals):,}"
    )

    print(
        "Duplicate hospital IDs:",
        hospitals["hospital_id"]
        .duplicated()
        .sum(),
    )

    print(
        "Missing hospital IDs:",
        hospitals["hospital_id"]
        .isna()
        .sum(),
    )

    print(
        "Missing hospital names:",
        hospitals["hospital_name"]
        .isna()
        .sum(),
    )

    validate_coordinates(
        hospitals,
        "latitude",
        "longitude",
        "Hospitals",
    )

    cms_count = (
        hospitals["ccn"]
        .notna()
        .sum()
    )

    open_count = (
        hospitals["is_open"]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    bed_count = (
        hospitals["beds"]
        .notna()
        .sum()
    )

    print(
        f"CMS-enriched hospitals: "
        f"{cms_count:,}"
    )

    print(
        f"Open hospitals: "
        f"{open_count:,}"
    )

    print(
        f"Hospitals with beds: "
        f"{bed_count:,}"
    )

    print(
        "Duplicate non-null CMS CCNs:",
        hospitals.loc[
            hospitals["ccn"].notna(),
            "ccn",
        ]
        .duplicated()
        .sum(),
    )

    assert len(hospitals) == 8339

    assert (
        hospitals["hospital_id"]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        hospitals["hospital_id"]
        .isna()
        .sum()
        == 0
    )

    assert (
        hospitals["hospital_name"]
        .isna()
        .sum()
        == 0
    )

    assert cms_count == 5391

    assert (
        hospitals.loc[
            hospitals["ccn"].notna(),
            "ccn",
        ]
        .duplicated()
        .sum()
        == 0
    )

    # ========================================================
    # SCHEMA CHECKS
    # ========================================================

    print("\n" + "=" * 82)
    print("REQUIRED SCHEMA CHECK")
    print("=" * 82)

    required_city_columns = {
        "city_id",
        "city_name",
        "city_display_unique",
        "state",
        "latitude",
        "longitude",
    }

    required_airport_columns = {
        "airport_id",
        "iata_code",
        "airport_name",
        "airport_display",
        "state",
        "latitude",
        "longitude",
    }

    required_hospital_columns = {
        "hospital_id",
        "ccn",
        "hospital_name",
        "address",
        "city",
        "state",
        "latitude",
        "longitude",
        "hospital_type",
        "ownership",
        "status",
        "is_open",
        "beds",
        "bed_source",
        "overall_rating",
        "total_patient_revenue",
        "net_patient_revenue",
        "total_costs",
        "net_income",
        "medicare_days",
        "medicare_discharges",
        "medicaid_days",
        "medicaid_discharges",
        "data_source_coverage",
        "match_type",
    }

    missing_city_columns = (
        required_city_columns
        - set(cities.columns)
    )

    missing_airport_columns = (
        required_airport_columns
        - set(airports.columns)
    )

    missing_hospital_columns = (
        required_hospital_columns
        - set(hospitals.columns)
    )

    print(
        "Missing city columns:",
        missing_city_columns,
    )

    print(
        "Missing airport columns:",
        missing_airport_columns,
    )

    print(
        "Missing hospital columns:",
        missing_hospital_columns,
    )

    assert not missing_city_columns
    assert not missing_airport_columns
    assert not missing_hospital_columns

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 82)
    print("PROCESSED DATASET SUMMARY")
    print("=" * 82)

    print(
        f"Cities     : {len(cities):,}"
    )

    print(
        f"Airports   : {len(airports):,}"
    )

    print(
        f"Hospitals  : {len(hospitals):,}"
    )

    print(
        f"Total rows : "
        f"{len(cities) + len(airports) + len(hospitals):,}"
    )

    print("\n" + "=" * 82)
    print("ALL PROCESSED DATA VALIDATION PASSED")
    print("=" * 82)


if __name__ == "__main__":
    validate_processed_data()