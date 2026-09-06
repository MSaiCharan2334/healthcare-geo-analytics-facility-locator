from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "airports"
    / "airports.csv"
)


def profile_airports():
    df = pd.read_csv(
        INPUT_CSV,
        dtype=str,
        low_memory=False
    )

    print("=" * 65)
    print("OURAIRPORTS DATA PROFILE")
    print("=" * 65)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print(f"Duplicate rows: {df.duplicated().sum():,}")

    print("\nColumns:")
    for col in df.columns:
        print(f" - {col}")

    important_columns = [
        "id",
        "ident",
        "type",
        "name",
        "latitude_deg",
        "longitude_deg",
        "elevation_ft",
        "iso_country",
        "iso_region",
        "municipality",
        "scheduled_service",
        "gps_code",
        "iata_code",
        "local_code",
    ]

    print("\nImportant field null counts:")
    print("-" * 45)

    for col in important_columns:
        if col in df.columns:
            print(
                f"{col:<25}: "
                f"{df[col].isna().sum():,}"
            )
        else:
            print(f"{col:<25}: NOT FOUND")

    # -----------------------------------------------------
    # USA only
    # -----------------------------------------------------

    if "iso_country" in df.columns:
        us = df[df["iso_country"] == "US"].copy()

        print("\n" + "=" * 65)
        print("UNITED STATES AIRPORT PROFILE")
        print("=" * 65)

        print(f"US airport records: {len(us):,}")

        if "iata_code" in us.columns:
            print(
                "US airports with IATA codes:",
                us["iata_code"].notna().sum()
            )

            print(
                "Duplicate US IATA codes:",
                us.loc[
                    us["iata_code"].notna(),
                    "iata_code"
                ].duplicated().sum()
            )

        if "type" in us.columns:
            print("\nUS airport types:")
            print(
                us["type"]
                .value_counts(dropna=False)
                .to_string()
            )

        if "scheduled_service" in us.columns:
            print("\nScheduled service:")
            print(
                us["scheduled_service"]
                .value_counts(dropna=False)
                .to_string()
            )

        # ---------------------------------------------
        # Coordinate validation
        # ---------------------------------------------

        lat = pd.to_numeric(
            us["latitude_deg"],
            errors="coerce"
        )

        lon = pd.to_numeric(
            us["longitude_deg"],
            errors="coerce"
        )

        print("\nCoordinate ranges:")

        print(
            f"Latitude : "
            f"{lat.min()} to {lat.max()}"
        )

        print(
            f"Longitude: "
            f"{lon.min()} to {lon.max()}"
        )

        print("\nInvalid coordinates:")

        print(
            "Latitude:",
            ((lat < -90) | (lat > 90)).sum()
        )

        print(
            "Longitude:",
            ((lon < -180) | (lon > 180)).sum()
        )

        # ---------------------------------------------
        # Candidate Power BI airport slicer dataset
        # ---------------------------------------------

        candidate = us[
            us["iata_code"].notna()
        ].copy()

        print("\nCandidate airport slicer records:")
        print(f"{len(candidate):,}")

        display_cols = [
            "iata_code",
            "name",
            "municipality",
            "iso_region",
            "type",
            "latitude_deg",
            "longitude_deg",
        ]

        display_cols = [
            c for c in display_cols
            if c in candidate.columns
        ]

        print("\nSample candidate airports:")

        print(
            candidate[display_cols]
            .head(20)
            .to_string(index=False)
        )


if __name__ == "__main__":
    profile_airports()