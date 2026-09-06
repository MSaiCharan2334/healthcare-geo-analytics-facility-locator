from pathlib import Path
import requests
import pandas as pd


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "hospitals"
OUTPUT_CSV = RAW_DIR / "hifld_hospitals.csv"


# ---------------------------------------------------------
# HIFLD API
# ---------------------------------------------------------

HIFLD_QUERY_URL = (
    "https://mapservices.pasda.psu.edu/server/rest/services/"
    "pasda/HIFLD_FEMA/MapServer/51/query"
)


def collect_hifld():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("HIFLD HOSPITAL DATA COLLECTION")
    print("=" * 60)

    all_rows = []
    offset = 0
    page_size = 2000

    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "f": "json",
        }

        print(f"Fetching records starting at offset {offset:,}...")

        response = requests.get(
            HIFLD_QUERY_URL,
            params=params,
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        if "error" in data:
            raise RuntimeError(data["error"])

        features = data.get("features", [])

        if not features:
            break

        rows = [feature["attributes"] for feature in features]
        all_rows.extend(rows)

        print(f"Received {len(rows):,} records")

        if len(rows) < page_size:
            break

        offset += page_size

    df = pd.DataFrame(all_rows)

    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8",
    )

    print("\nDownload complete.")
    print(f"Saved to: {OUTPUT_CSV}")
    print(f"Rows collected: {len(df):,}")

    return df


def profile_hifld(df):
    print("\n" + "=" * 60)
    print("HIFLD DATA PROFILE")
    print("=" * 60)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")
    print(f"Duplicate rows: {df.duplicated().sum():,}")

    print("\nColumns:")
    for column in df.columns:
        print(f" - {column}")

    important_columns = [
        "ID",
        "NAME",
        "ADDRESS",
        "CITY",
        "STATE",
        "ZIP",
        "LATITUDE",
        "LONGITUDE",
        "TYPE",
        "STATUS",
        "BEDS",
        "TTL_STAFF",
        "TRAUMA",
        "OWNER",
    ]

    print("\nImportant field null counts:")
    print("-" * 40)

    for column in important_columns:
        if column in df.columns:
            null_count = df[column].isna().sum()

            print(
                f"{column:<15}"
                f"{null_count:>8,}"
            )

    print("\nSample:")
    print(df.head(5).to_string())
    print("\nHospital Types:")
    print(df["TYPE"].value_counts().to_string())

    print("\nStatus:")
    print(df["STATUS"].value_counts().to_string())

    print("\nCountries:")
    print(df["COUNTRY"].value_counts().to_string())

    print("\nCoordinate ranges:")
    print("Latitude :", df["LATITUDE"].min(), "to", df["LATITUDE"].max())
    print("Longitude:", df["LONGITUDE"].min(), "to", df["LONGITUDE"].max())

    print("\nBeds <= 0:")
    print((df["BEDS"] <= 0).sum())

    print("\nTTL_STAFF <= 0:")
    print((df["TTL_STAFF"] <= 0).sum())

    print("\nDuplicate IDs:")
    print(df["ID"].duplicated().sum())    

    


if __name__ == "__main__":
    hospitals = collect_hifld()
    profile_hifld(hospitals)