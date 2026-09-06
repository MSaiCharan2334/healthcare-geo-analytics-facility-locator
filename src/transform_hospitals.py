from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "hospital_enriched_base.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hospitals.csv"
)


# ============================================================
# HELPERS
# ============================================================

def get_column(df, column_name):
    """
    Return a column if it exists, otherwise an all-null Series.
    """

    if column_name in df.columns:
        return df[column_name].copy()

    return pd.Series(
        pd.NA,
        index=df.index,
    )


def coalesce(df, columns):
    """
    Return the first non-null value across the supplied columns.
    """

    result = pd.Series(
        pd.NA,
        index=df.index,
        dtype="object",
    )

    for column in columns:

        if column in df.columns:
            result = result.combine_first(
                df[column]
            )

    return result


def numeric_column(df, column_name):
    """
    Safely convert an existing column to numeric.
    """

    return pd.to_numeric(
        get_column(
            df,
            column_name,
        ),
        errors="coerce",
    )


def numeric_coalesce(df, columns):
    """
    Coalesce several possible numeric fields.
    """

    result = pd.Series(
        np.nan,
        index=df.index,
        dtype="float64",
    )

    for column in columns:

        if column not in df.columns:
            continue

        values = pd.to_numeric(
            df[column],
            errors="coerce",
        )

        # Zero/negative values should not represent
        # valid hospital beds/utilization counts.
        result = result.combine_first(
            values
        )

    return result


def clean_positive(series):
    """
    Convert zero/negative numeric values to null.
    """

    series = pd.to_numeric(
        series,
        errors="coerce",
    )

    return series.where(
        series > 0
    )


# ============================================================
# MAIN TRANSFORMATION
# ============================================================

def transform_hospitals():

    print("=" * 82)
    print("BUILDING FINAL PROCESSED HOSPITAL TABLE")
    print("=" * 82)

    df = pd.read_csv(
        INPUT_FILE,
        dtype={
            "hifld_id": "string",
            "ccn": "string",
        },
        low_memory=False,
    )

    print(
        f"\nEnriched input rows: "
        f"{len(df):,}"
    )

    # --------------------------------------------------------
    # 1. Normalize identifiers
    # --------------------------------------------------------

    df["hifld_id"] = (
        df["hifld_id"]
        .astype("string")
        .str.strip()
    )

    if "ccn" in df.columns:

        df["ccn"] = (
            df["ccn"]
            .astype("string")
            .str.strip()
            .str.zfill(6)
        )

    # --------------------------------------------------------
    # 2. Unified hospital identity
    #
    # Prefer CMS names where a trusted match exists.
    # Otherwise retain HIFLD identity.
    # --------------------------------------------------------

    hospital_name = coalesce(
        df,
        [
            "hospital_name",
            "hifld_name",
        ],
    )

    # --------------------------------------------------------
    # 3. Physical location
    #
    # HIFLD is our geographic authority because coordinates
    # come from HIFLD.
    # --------------------------------------------------------

    address = coalesce(
        df,
        [
            "address_hifld",
            "address",
            "address_cms",
        ],
    )

    city = coalesce(
        df,
        [
            "city_hifld",
            "city",
            "city_cms",
        ],
    )

    state = coalesce(
        df,
        [
            "state_hifld",
            "state",
            "state_cms",
        ],
    )

    zip_code = coalesce(
        df,
        [
            "zip_code_hifld",
            "zip_code",
            "zip_code_cms",
        ],
    )

    county = coalesce(
        df,
        [
            "county_hifld",
            "county",
            "county_cms",
        ],
    )

    telephone = coalesce(
        df,
        [
            "telephone_cms",
            "telephone",
            "telephone_hifld",
        ],
    )

    # --------------------------------------------------------
    # 4. Unified hospital type / ownership
    # --------------------------------------------------------

    hospital_type = coalesce(
        df,
        [
            "hospital_type",
            "hifld_type",
        ],
    )

    ownership = coalesce(
        df,
        [
            "hospital_ownership",
            "hifld_owner",
        ],
    )

    # --------------------------------------------------------
    # 5. Bed-count precedence
    #
    # Prefer hospital-specific CMS bed count when available,
    # then general CMS cost-report bed count,
    # then HIFLD bed count.
    # --------------------------------------------------------

    cms_adult_peds_beds = clean_positive(
        numeric_column(
            df,
            "Hospital Number of Beds For Adults & Peds",
        )
    )

    cms_report_beds = clean_positive(
        numeric_column(
            df,
            "Number of Beds",
        )
    )

    hifld_beds = clean_positive(
        numeric_column(
            df,
            "hifld_beds",
        )
    )

    beds = (
        cms_adult_peds_beds
        .combine_first(
            cms_report_beds
        )
        .combine_first(
            hifld_beds
        )
    )

    bed_source = pd.Series(
        pd.NA,
        index=df.index,
        dtype="string",
    )

    bed_source.loc[
        cms_adult_peds_beds.notna()
    ] = "CMS_ADULT_PEDS"

    bed_source.loc[
        cms_adult_peds_beds.isna()
        &
        cms_report_beds.notna()
    ] = "CMS_COST_REPORT"

    bed_source.loc[
        cms_adult_peds_beds.isna()
        &
        cms_report_beds.isna()
        &
        hifld_beds.notna()
    ] = "HIFLD"

    # --------------------------------------------------------
    # 6. Medicare utilization
    #
    # Title XVIII = Medicare
    # --------------------------------------------------------

    medicare_days = numeric_coalesce(
        df,
        [
            "Hospital Total Days Title XVIII For Adults & Peds",
            "Total Days Title XVIII",
        ],
    )

    medicare_discharges = numeric_coalesce(
        df,
        [
            "Hospital Total Discharges Title XVIII For Adults & Peds",
            "Total Discharges Title XVIII",
        ],
    )

    # --------------------------------------------------------
    # 7. Medicaid utilization
    #
    # Title XIX = Medicaid
    # --------------------------------------------------------

    medicaid_days = numeric_coalesce(
        df,
        [
            "Hospital Total Days Title XIX For Adults & Peds",
            "Total Days Title XIX",
        ],
    )

    medicaid_discharges = numeric_coalesce(
        df,
        [
            "Hospital Total Discharges Title XIX For Adults & Peds",
            "Total Discharges Title XIX",
        ],
    )

    # --------------------------------------------------------
    # 8. CMS quality rating
    # --------------------------------------------------------

    overall_rating = pd.to_numeric(
        get_column(
            df,
            "hospital_overall_rating",
        ),
        errors="coerce",
    )

    # --------------------------------------------------------
    # 9. Construct final production dataframe
    # --------------------------------------------------------

    hospitals = pd.DataFrame(
        {
            # ------------------------------------------------
            # Primary identifiers
            # ------------------------------------------------
            "hospital_id": df["hifld_id"],
            "ccn": get_column(df, "ccn"),

            # ------------------------------------------------
            # Core facility identity
            # ------------------------------------------------
            "hospital_name": hospital_name,
            "address": address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "county": county,
            "country_code": get_column(
                df,
                "country_code",
            ),
            "telephone": telephone,
            "website": get_column(
                df,
                "website",
            ),

            # ------------------------------------------------
            # Geography
            # ------------------------------------------------
            "latitude": numeric_column(
                df,
                "latitude",
            ),
            "longitude": numeric_column(
                df,
                "longitude",
            ),

            # ------------------------------------------------
            # Facility characteristics
            # ------------------------------------------------
            "hospital_type": hospital_type,
            "ownership": ownership,
            "status": get_column(
                df,
                "hifld_status",
            ),
            "is_open": get_column(
                df,
                "is_open",
            ),
            "emergency_services": get_column(
                df,
                "emergency_services",
            ),
            "trauma_level": get_column(
                df,
                "trauma_level",
            ),
            "helipad": get_column(
                df,
                "helipad",
            ),

            # ------------------------------------------------
            # Beds
            # ------------------------------------------------
            "beds": beds,
            "bed_source": bed_source,
            "cms_beds": cms_report_beds,
            "hifld_beds": hifld_beds,

            # ------------------------------------------------
            # CMS quality
            # ------------------------------------------------
            "overall_rating": overall_rating,

            # ------------------------------------------------
            # Cost report context
            # ------------------------------------------------
            "provider_type": get_column(
                df,
                "Provider Type",
            ),
            "ccn_facility_type": get_column(
                df,
                "CCN Facility Type",
            ),
            "type_of_control": get_column(
                df,
                "Type of Control",
            ),
            "rural_urban": get_column(
                df,
                "Rural Versus Urban",
            ),
            "fiscal_year_begin": get_column(
                df,
                "Fiscal Year Begin Date",
            ),
            "fiscal_year_end": get_column(
                df,
                "Fiscal Year End Date",
            ),
            "report_days": numeric_column(
                df,
                "report_days",
            ),
            "fte_employees": numeric_column(
                df,
                "FTE - Employees on Payroll",
            ),

            # ------------------------------------------------
            # Financials
            # ------------------------------------------------
            "inpatient_revenue": numeric_column(
                df,
                "Inpatient Revenue",
            ),
            "outpatient_revenue": numeric_column(
                df,
                "Outpatient Revenue",
            ),
            "total_patient_revenue": numeric_column(
                df,
                "Total Patient Revenue",
            ),
            "net_patient_revenue": numeric_column(
                df,
                "Net Patient Revenue",
            ),
            "total_costs": numeric_column(
                df,
                "Total Costs",
            ),
            "net_income": numeric_column(
                df,
                "Net Income",
            ),
            "cost_to_charge_ratio": numeric_column(
                df,
                "Cost To Charge Ratio",
            ),
            "charity_care_cost": numeric_column(
                df,
                "Cost of Charity Care",
            ),
            "uncompensated_care_cost": numeric_column(
                df,
                "Cost of Uncompensated Care",
            ),

            # ------------------------------------------------
            # Medicare
            # ------------------------------------------------
            "medicare_days": medicare_days,
            "medicare_discharges": medicare_discharges,

            # ------------------------------------------------
            # Medicaid
            # ------------------------------------------------
            "medicaid_days": medicaid_days,
            "medicaid_discharges": medicaid_discharges,
            "medicaid_net_revenue": numeric_column(
                df,
                "Net Revenue from Medicaid",
            ),
            "medicaid_charges": numeric_column(
                df,
                "Medicaid Charges",
            ),

            # ------------------------------------------------
            # Source / linkage provenance
            # ------------------------------------------------
            "data_source_coverage": get_column(
                df,
                "data_source_coverage",
            ),
            "cms_source_status": get_column(
                df,
                "cms_source_status",
            ),
            "match_type": get_column(
                df,
                "match_type",
            ),
            "match_score": numeric_column(
                df,
                "match_score",
            ),
            "hifld_source": get_column(
                df,
                "hifld_source",
            ),
            "hifld_source_date": get_column(
                df,
                "hifld_source_date",
            ),
        }
    )

    # --------------------------------------------------------
    # 10. Final type cleanup
    # --------------------------------------------------------

    hospitals["hospital_name"] = (
        hospitals["hospital_name"]
        .astype("string")
        .str.strip()
    )

    hospitals["state"] = (
        hospitals["state"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    hospitals["country_code"] = (
        hospitals["country_code"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    hospitals["beds"] = (
        hospitals["beds"]
        .round()
        .astype("Int64")
    )

    hospitals["cms_beds"] = (
        hospitals["cms_beds"]
        .round()
        .astype("Int64")
    )

    hospitals["hifld_beds"] = (
        hospitals["hifld_beds"]
        .round()
        .astype("Int64")
    )

    # --------------------------------------------------------
    # 11. Validation
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 82)

    total_rows = len(
        hospitals
    )

    duplicate_ids = (
        hospitals["hospital_id"]
        .duplicated()
        .sum()
    )

    missing_ids = (
        hospitals["hospital_id"]
        .isna()
        .sum()
    )

    missing_names = (
        hospitals["hospital_name"]
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

    cms_matches = (
        hospitals["ccn"]
        .notna()
        .sum()
    )

    open_hospitals = (
        hospitals["is_open"]
        .fillna(False)
        .astype(bool)
        .sum()
    )

    valid_beds = (
        hospitals["beds"]
        .notna()
        .sum()
    )

    print(
        f"Final hospital rows: "
        f"{total_rows:,}"
    )

    print(
        f"Duplicate hospital IDs: "
        f"{duplicate_ids:,}"
    )

    print(
        f"Missing hospital IDs: "
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
        f"Hospitals with CMS enrichment: "
        f"{cms_matches:,}"
    )

    print(
        f"Open hospitals: "
        f"{open_hospitals:,}"
    )

    print(
        f"Hospitals with usable bed counts: "
        f"{valid_beds:,}"
    )

    print("\nBed source distribution:")

    print(
        hospitals[
            "bed_source"
        ]
        .value_counts(
            dropna=False
        )
        .to_string()
    )

    print("\nData source coverage:")

    print(
        hospitals[
            "data_source_coverage"
        ]
        .value_counts()
        .to_string()
    )

    print("\nFinancial field availability:")

    financial_fields = [
        "total_patient_revenue",
        "net_patient_revenue",
        "total_costs",
        "net_income",
        "medicaid_net_revenue",
    ]

    for column in financial_fields:

        print(
            f"{column:<30}: "
            f"{hospitals[column].notna().sum():,}"
        )

    print("\nMedicare / Medicaid utilization availability:")

    for column in [
        "medicare_days",
        "medicare_discharges",
        "medicaid_days",
        "medicaid_discharges",
    ]:

        print(
            f"{column:<30}: "
            f"{hospitals[column].notna().sum():,}"
        )

    # --------------------------------------------------------
    # 12. Hard checks
    # --------------------------------------------------------

    assert total_rows == 8339
    assert duplicate_ids == 0
    assert missing_ids == 0
    assert missing_names == 0
    assert missing_coordinates == 0
    assert invalid_latitudes == 0
    assert invalid_longitudes == 0

    # Trusted CMS linkage count
    assert cms_matches == 5391

    # --------------------------------------------------------
    # 13. Save
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

    print("\n" + "=" * 82)
    print("FINAL HOSPITAL TRANSFORMATION COMPLETE")
    print("=" * 82)

    print(
        f"Saved to:\n"
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    transform_hospitals()