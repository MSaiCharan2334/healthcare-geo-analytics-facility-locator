from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "airports"
    / "airports.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "airports.csv"
)


ALLOWED_TYPES = [
    "large_airport",
    "medium_airport",
    "small_airport",
]


def transform_airports():

    print("=" * 65)
    print("TRANSFORMING OURAIRPORTS DATA")
    print("=" * 65)

    df = pd.read_csv(
        INPUT_FILE,
        dtype=str,
        low_memory=False,
    )

    print(f"Raw rows: {len(df):,}")

    # --------------------------------------------------------
    # Filter to useful U.S. passenger airports
    # --------------------------------------------------------

    airports = df[
        (df["iso_country"] == "US")
        & (df["iata_code"].notna())
        & (df["scheduled_service"] == "yes")
        & (df["type"].isin(ALLOWED_TYPES))
    ].copy()

    print(
        "Rows after filtering: "
        f"{len(airports):,}"
    )

    # --------------------------------------------------------
    # Keep relevant columns
    # --------------------------------------------------------

    airports = airports[
        [
            "id",
            "ident",
            "iata_code",
            "icao_code",
            "name",
            "municipality",
            "iso_region",
            "type",
            "scheduled_service",
            "latitude_deg",
            "longitude_deg",
            "elevation_ft",
        ]
    ].copy()

    # --------------------------------------------------------
    # Rename columns
    # --------------------------------------------------------

    airports = airports.rename(
        columns={
            "id": "airport_id",
            "ident": "airport_ident",
            "name": "airport_name",
            "municipality": "city",
            "type": "airport_type",
            "latitude_deg": "latitude",
            "longitude_deg": "longitude",
        }
    )

    # --------------------------------------------------------
    # Clean text fields
    # --------------------------------------------------------

    text_columns = [
        "airport_id",
        "airport_ident",
        "iata_code",
        "icao_code",
        "airport_name",
        "city",
        "iso_region",
        "airport_type",
        "scheduled_service",
    ]

    for column in text_columns:
        airports[column] = (
            airports[column]
            .astype("string")
            .str.strip()
        )

    airports["iata_code"] = (
        airports["iata_code"]
        .str.upper()
    )

    # Convert US-TX -> TX
    airports["state"] = (
        airports["iso_region"]
        .str.replace(
            "US-",
            "",
            regex=False,
        )
    )

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    airports["latitude"] = pd.to_numeric(
        airports["latitude"],
        errors="coerce",
    )

    airports["longitude"] = pd.to_numeric(
        airports["longitude"],
        errors="coerce",
    )

    airports["elevation_ft"] = pd.to_numeric(
        airports["elevation_ft"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Power BI display label
    # --------------------------------------------------------

    airports["airport_display"] = (
        airports["iata_code"]
        + " - "
        + airports["airport_name"]
        + " ("
        + airports["state"]
        + ")"
    )

    # --------------------------------------------------------
    # Final column order
    # --------------------------------------------------------

    airports = airports[
        [
            "airport_id",
            "iata_code",
            "icao_code",
            "airport_ident",
            "airport_name",
            "airport_display",
            "city",
            "state",
            "airport_type",
            "scheduled_service",
            "latitude",
            "longitude",
            "elevation_ft",
        ]
    ]

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 65)

    processed_rows = len(airports)

    duplicate_ids = (
        airports["airport_id"]
        .duplicated()
        .sum()
    )

    duplicate_iata = (
        airports["iata_code"]
        .duplicated()
        .sum()
    )

    missing_iata = (
        airports["iata_code"]
        .isna()
        .sum()
    )

    missing_coordinates = (
        airports[
            ["latitude", "longitude"]
        ]
        .isna()
        .any(axis=1)
        .sum()
    )

    invalid_latitudes = (
        (airports["latitude"] < -90)
        | (airports["latitude"] > 90)
    ).sum()

    invalid_longitudes = (
        (airports["longitude"] < -180)
        | (airports["longitude"] > 180)
    ).sum()

    duplicate_display = (
        airports["airport_display"]
        .duplicated()
        .sum()
    )

    print(f"Processed rows: {processed_rows:,}")
    print(f"Duplicate airport IDs: {duplicate_ids:,}")
    print(f"Duplicate IATA codes: {duplicate_iata:,}")
    print(f"Missing IATA codes: {missing_iata:,}")
    print(f"Missing coordinates: {missing_coordinates:,}")
    print(f"Invalid latitude values: {invalid_latitudes:,}")
    print(f"Invalid longitude values: {invalid_longitudes:,}")
    print(f"Duplicate airport display labels: {duplicate_display:,}")

    print("\nAirport type distribution:")
    print(
        airports["airport_type"]
        .value_counts()
        .to_string()
    )

    # --------------------------------------------------------
    # Hard validation
    # --------------------------------------------------------

    assert processed_rows > 0
    assert duplicate_ids == 0
    assert duplicate_iata == 0
    assert missing_iata == 0
    assert missing_coordinates == 0
    assert invalid_latitudes == 0
    assert invalid_longitudes == 0
    assert duplicate_display == 0

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    airports.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 65)
    print("AIRPORT TRANSFORMATION COMPLETE")
    print("=" * 65)

    print(f"Saved to:\n{OUTPUT_FILE}")

    print("\nMajor airport check:")

    major_codes = [
        "ATL",
        "DFW",
        "JFK",
        "LAX",
        "ORD",
        "SEA",
        "SFO",
    ]

    print(
        airports[
            airports["iata_code"]
            .isin(major_codes)
        ][
            [
                "iata_code",
                "airport_name",
                "city",
                "state",
                "latitude",
                "longitude",
            ]
        ]
        .sort_values("iata_code")
        .to_string(index=False)
    )


if __name__ == "__main__":
    transform_airports()