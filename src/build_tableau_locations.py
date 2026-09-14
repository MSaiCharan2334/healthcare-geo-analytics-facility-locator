from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CITIES_PATH = PROJECT_ROOT / "data" / "processed" / "cities.csv"
AIRPORTS_PATH = PROJECT_ROOT / "data" / "processed" / "airports.csv"

OUTPUT_DIR = PROJECT_ROOT / "data" / "tableau"
OUTPUT_PATH = OUTPUT_DIR / "locations.csv"


# --------------------------------------------------
# Load processed datasets
# --------------------------------------------------

cities = pd.read_csv(
    CITIES_PATH,
    dtype={
        "city_id": str,
        "city_name": str,
        "city_display_unique": str,
        "state": str,
    },
)

airports = pd.read_csv(
    AIRPORTS_PATH,
    dtype={
        "airport_id": str,
        "iata_code": str,
        "airport_name": str,
        "airport_display": str,
        "city": str,
        "state": str,
        "airport_type": str,
    },
)

print(f"Cities loaded: {len(cities):,}")
print(f"Airports loaded: {len(airports):,}")


# --------------------------------------------------
# Build city selector rows
# --------------------------------------------------

city_locations = pd.DataFrame(
    {
        "location_id": "CITY_" + cities["city_id"],
        "location_mode": "City",
        "location_name": cities["city_name"],
        "location_display": cities["city_display_unique"],
        "city": cities["city_name"],
        "state": cities["state"],
        "iata_code": pd.NA,
        "airport_type": pd.NA,
        "latitude": cities["latitude"],
        "longitude": cities["longitude"],
    }
)


# --------------------------------------------------
# Build airport selector rows
# --------------------------------------------------

airport_locations = pd.DataFrame(
    {
        "location_id": "AIRPORT_" + airports["airport_id"],
        "location_mode": "Airport",
        "location_name": airports["airport_name"],
        "location_display": airports["airport_display"],
        "city": airports["city"],
        "state": airports["state"],
        "iata_code": airports["iata_code"],
        "airport_type": airports["airport_type"],
        "latitude": airports["latitude"],
        "longitude": airports["longitude"],
    }
)


# --------------------------------------------------
# Combine
# --------------------------------------------------

locations = pd.concat(
    [city_locations, airport_locations],
    ignore_index=True,
)

locations = locations.sort_values(
    ["location_mode", "state", "location_display"],
    na_position="last",
).reset_index(drop=True)


# --------------------------------------------------
# Validation
# --------------------------------------------------

expected_rows = len(cities) + len(airports)

duplicate_ids = locations["location_id"].duplicated().sum()

missing_coordinates = (
    locations["latitude"].isna()
    | locations["longitude"].isna()
).sum()

invalid_coordinates = (
    ~locations["latitude"].between(-90, 90)
    | ~locations["longitude"].between(-180, 180)
).sum()

mode_counts = locations["location_mode"].value_counts()


print()
print("TABLEAU LOCATION DATASET VALIDATION")
print("-----------------------------------")
print(f"Expected rows: {expected_rows:,}")
print(f"Actual rows: {len(locations):,}")
print(f"Duplicate location IDs: {duplicate_ids}")
print(f"Missing coordinates: {missing_coordinates}")
print(f"Invalid coordinates: {invalid_coordinates}")

print()
print("Mode counts:")
print(mode_counts.to_string())


if len(locations) != expected_rows:
    raise RuntimeError("Row-count validation failed.")

if duplicate_ids != 0:
    raise RuntimeError("Duplicate location IDs found.")

if missing_coordinates != 0:
    raise RuntimeError("Missing coordinates found.")

if invalid_coordinates != 0:
    raise RuntimeError("Invalid coordinates found.")


# --------------------------------------------------
# Save
# --------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

locations.to_csv(
    OUTPUT_PATH,
    index=False,
)

print()
print(f"Saved Tableau location dataset to:")
print(OUTPUT_PATH)

print()
print("Tableau location dataset validation PASSED.")