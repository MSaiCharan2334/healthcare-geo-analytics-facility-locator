from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "cities"


def find_data_file():
    """
    Locate the already-extracted Census Gazetteer file.
    Ignore ZIP files.
    """

    candidates = []

    for file in RAW_DIR.rglob("*"):
        if file.is_file() and file.suffix.lower() in {
            ".txt",
            ".tsv",
            ".csv",
        }:
            candidates.append(file)

    if not candidates:
        raise FileNotFoundError(
            "No extracted Census data file found in data/raw/cities."
        )

    print(f"Found Census data file: {candidates[0]}")

    return candidates[0]


def profile_cities(input_file):

    # Census Gazetteer files are normally tab-separated
    df = pd.read_csv(
        input_file,
        sep="|",
        dtype=str
    )

    # Clean column-header whitespace
    df.columns = df.columns.str.strip()

    print("=" * 60)
    print("CENSUS PLACES DATA PROFILE")
    print("=" * 60)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print(f"Duplicate rows: {df.duplicated().sum():,}")

    print("\nColumns:")
    for col in df.columns:
        print(f" - {col}")

    important_columns = [
        "USPS",
        "GEOID",
        "NAME",
        "ALAND",
        "AWATER",
        "INTPTLAT",
        "INTPTLONG",
    ]

    print("\nImportant field null counts:")
    print("-" * 40)

    for col in important_columns:

        if col in df.columns:

            null_count = df[col].isna().sum()

            print(
                f"{col:<15}: "
                f"{null_count:,}"
            )

        else:

            print(
                f"{col:<15}: NOT FOUND"
            )

    if "GEOID" in df.columns:

        print("\nDuplicate GEOIDs:")
        print(
            df["GEOID"]
            .duplicated()
            .sum()
        )

    if "USPS" in df.columns:

        print("\nState / Territory counts:")

        print(
            df["USPS"]
            .value_counts(
                dropna=False
            )
            .sort_index()
            .to_string()
        )

    if "NAME" in df.columns:

        print("\nSample place names:")

        print(
            df["NAME"]
            .head(20)
            .to_string(
                index=False
            )
        )

    # Validate coordinates
    if (
        "INTPTLAT" in df.columns
        and "INTPTLONG" in df.columns
    ):

        lat = pd.to_numeric(
            df["INTPTLAT"],
            errors="coerce"
        )

        lon = pd.to_numeric(
            df["INTPTLONG"],
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

    print("\nSample:")
    print(
        df.head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":

    census_file = find_data_file()

    profile_cities(census_file)