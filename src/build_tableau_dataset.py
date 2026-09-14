from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

LOCATIONS_PATH = (
    PROJECT_ROOT / "data" / "tableau" / "locations.csv"
)

HOSPITALS_PATH = (
    PROJECT_ROOT / "data" / "processed" / "hospitals.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "data" / "tableau"

OUTPUT_PATH = (
    OUTPUT_DIR / "location_hospital_distances.csv"
)


# --------------------------------------------------
# Configuration
# --------------------------------------------------

MAX_RADIUS_MILES = 100.0

# Number of locations processed at once.
# Keeps memory usage reasonable on a Mac.
LOCATION_CHUNK_SIZE = 250

EARTH_RADIUS_MILES = 3958.7613


# --------------------------------------------------
# Load inputs
# --------------------------------------------------

locations = pd.read_csv(
    LOCATIONS_PATH,
    dtype={
        "location_id": str,
        "location_mode": str,
    },
)

hospitals = pd.read_csv(
    HOSPITALS_PATH,
    dtype={
        "hospital_id": str,
        "ccn": str,
    },
)

print(f"Locations loaded: {len(locations):,}")
print(f"Hospitals loaded: {len(hospitals):,}")


# --------------------------------------------------
# Input validation
# --------------------------------------------------

required_location_columns = {
    "location_id",
    "latitude",
    "longitude",
}

required_hospital_columns = {
    "hospital_id",
    "latitude",
    "longitude",
}

missing_location_columns = (
    required_location_columns - set(locations.columns)
)

missing_hospital_columns = (
    required_hospital_columns - set(hospitals.columns)
)

if missing_location_columns:
    raise RuntimeError(
        f"Locations missing columns: "
        f"{sorted(missing_location_columns)}"
    )

if missing_hospital_columns:
    raise RuntimeError(
        f"Hospitals missing columns: "
        f"{sorted(missing_hospital_columns)}"
    )


if locations["location_id"].duplicated().any():
    raise RuntimeError("Duplicate location IDs found.")

if hospitals["hospital_id"].duplicated().any():
    raise RuntimeError("Duplicate hospital IDs found.")


if (
    locations["latitude"].isna().any()
    or locations["longitude"].isna().any()
):
    raise RuntimeError(
        "Missing coordinates found in locations."
    )

if (
    hospitals["latitude"].isna().any()
    or hospitals["longitude"].isna().any()
):
    raise RuntimeError(
        "Missing coordinates found in hospitals."
    )


# --------------------------------------------------
# Prepare coordinates in radians
# --------------------------------------------------

location_lat_rad = np.radians(
    locations["latitude"].to_numpy(dtype=float)
)

location_lon_rad = np.radians(
    locations["longitude"].to_numpy(dtype=float)
)

hospital_lat_rad = np.radians(
    hospitals["latitude"].to_numpy(dtype=float)
)

hospital_lon_rad = np.radians(
    hospitals["longitude"].to_numpy(dtype=float)
)


hospital_ids = hospitals["hospital_id"].to_numpy()

location_ids = locations["location_id"].to_numpy()


# --------------------------------------------------
# Prepare output
# --------------------------------------------------

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

# Remove old output so rerunning the script
# never duplicates previously generated rows.
if OUTPUT_PATH.exists():
    OUTPUT_PATH.unlink()


first_write = True

total_pairs = 0

locations_with_hospitals = set()

hospitals_represented = set()

minimum_distance_seen = None
maximum_distance_seen = None


# --------------------------------------------------
# Calculate Haversine distances in chunks
# --------------------------------------------------

total_locations = len(locations)

print()
print(
    f"Generating location-hospital pairs "
    f"within {MAX_RADIUS_MILES:.0f} miles..."
)
print()


for start in range(
    0,
    total_locations,
    LOCATION_CHUNK_SIZE,
):

    end = min(
        start + LOCATION_CHUNK_SIZE,
        total_locations,
    )

    # Shape:
    # location chunk = (N, 1)
    # hospitals      = (1, H)

    lat1 = location_lat_rad[start:end, None]
    lon1 = location_lon_rad[start:end, None]

    lat2 = hospital_lat_rad[None, :]
    lon2 = hospital_lon_rad[None, :]

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2.0) ** 2
    )

    # Protect against tiny floating-point
    # values outside the valid [0, 1] range.
    a = np.clip(a, 0.0, 1.0)

    angular_distance = (
        2.0
        * np.arcsin(
            np.sqrt(a)
        )
    )

    distances = (
        EARTH_RADIUS_MILES
        * angular_distance
    )

    within_radius = (
        distances <= MAX_RADIUS_MILES
    )

    location_indices, hospital_indices = (
        np.where(within_radius)
    )

    if len(location_indices) > 0:

        matched_distances = distances[
            location_indices,
            hospital_indices,
        ]

        chunk_location_ids = location_ids[
            start:end
        ][location_indices]

        chunk_hospital_ids = hospital_ids[
            hospital_indices
        ]

        chunk_output = pd.DataFrame(
            {
                "location_id": chunk_location_ids,
                "hospital_id": chunk_hospital_ids,
                "distance_miles": np.round(
                    matched_distances,
                    3,
                ),
            }
        )

        chunk_output.to_csv(
            OUTPUT_PATH,
            mode="a",
            header=first_write,
            index=False,
        )

        first_write = False

        total_pairs += len(chunk_output)

        locations_with_hospitals.update(
            chunk_output[
                "location_id"
            ].unique()
        )

        hospitals_represented.update(
            chunk_output[
                "hospital_id"
            ].unique()
        )

        chunk_min = (
            chunk_output["distance_miles"].min()
        )

        chunk_max = (
            chunk_output["distance_miles"].max()
        )

        if minimum_distance_seen is None:
            minimum_distance_seen = chunk_min
        else:
            minimum_distance_seen = min(
                minimum_distance_seen,
                chunk_min,
            )

        if maximum_distance_seen is None:
            maximum_distance_seen = chunk_max
        else:
            maximum_distance_seen = max(
                maximum_distance_seen,
                chunk_max,
            )

    print(
        f"Processed locations "
        f"{start + 1:,}-{end:,} "
        f"of {total_locations:,} | "
        f"pairs so far: {total_pairs:,}"
    )


# --------------------------------------------------
# Final validation
# --------------------------------------------------

print()
print("TABLEAU DISTANCE DATASET VALIDATION")
print("-----------------------------------")

print(
    f"Total location-hospital pairs: "
    f"{total_pairs:,}"
)

print(
    f"Locations with >=1 hospital "
    f"within {MAX_RADIUS_MILES:.0f} miles: "
    f"{len(locations_with_hospitals):,}"
)

print(
    f"Unique hospitals represented: "
    f"{len(hospitals_represented):,}"
)

if minimum_distance_seen is not None:
    print(
        f"Minimum distance: "
        f"{minimum_distance_seen:.3f} miles"
    )

if maximum_distance_seen is not None:
    print(
        f"Maximum distance: "
        f"{maximum_distance_seen:.3f} miles"
    )


if total_pairs == 0:
    raise RuntimeError(
        "No location-hospital pairs generated."
    )

if maximum_distance_seen > MAX_RADIUS_MILES:
    raise RuntimeError(
        "Distance greater than configured "
        "maximum radius found."
    )


print()
print("Saved Tableau distance dataset to:")
print(OUTPUT_PATH)

print()
print(
    "Tableau distance dataset "
    "validation PASSED."
)