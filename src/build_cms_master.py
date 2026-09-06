from pathlib import Path
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GENERAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "hospitals"
    / "cms_hospital_general.csv"
)

COST_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "cms_cost_report_canonical.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "intermediate"
    / "hospitals"
    / "cms_hospital_master.csv"
)


# ============================================================
# BUILD CMS MASTER
# ============================================================

def build_cms_master():

    print("=" * 70)
    print("BUILDING UNIFIED CMS HOSPITAL MASTER")
    print("=" * 70)

    # --------------------------------------------------------
    # 1. Load CMS General
    # --------------------------------------------------------

    general = pd.read_csv(
        GENERAL_FILE,
        dtype={
            "Facility ID": "string",
            "ZIP Code": "string",
        },
        low_memory=False,
    )

    general["Facility ID"] = (
        general["Facility ID"]
        .str.strip()
        .str.zfill(6)
    )

    print(f"CMS General rows: {len(general):,}")

    # --------------------------------------------------------
    # 2. Load canonical Cost Report
    # --------------------------------------------------------

    cost = pd.read_csv(
        COST_FILE,
        dtype={
            "Provider CCN": "string",
            "Zip Code": "string",
        },
        low_memory=False,
    )

    cost["Provider CCN"] = (
        cost["Provider CCN"]
        .str.strip()
        .str.zfill(6)
    )

    print(f"Canonical Cost Report rows: {len(cost):,}")

    # --------------------------------------------------------
    # 3. Select relevant General fields
    # --------------------------------------------------------

    general_keep = general[
        [
            "Facility ID",
            "Facility Name",
            "Address",
            "City/Town",
            "State",
            "ZIP Code",
            "County/Parish",
            "Telephone Number",
            "Hospital Type",
            "Hospital Ownership",
            "Emergency Services",
            "Hospital overall rating",
        ]
    ].copy()

    general_keep = general_keep.rename(
        columns={
            "Facility ID": "ccn",
            "Facility Name": "general_name",
            "Address": "general_address",
            "City/Town": "general_city",
            "State": "general_state",
            "ZIP Code": "general_zip",
            "County/Parish": "general_county",
            "Telephone Number": "telephone",
            "Hospital Type": "hospital_type",
            "Hospital Ownership": "hospital_ownership",
            "Emergency Services": "emergency_services",
            "Hospital overall rating": "hospital_overall_rating",
        }
    )

    general_keep["in_cms_general"] = True

    # --------------------------------------------------------
    # 4. Select relevant Cost Report fields
    # --------------------------------------------------------

    cost_columns = [
        "Provider CCN",
        "Hospital Name",
        "Street Address",
        "City",
        "State Code",
        "Zip Code",
        "County",
        "Rural Versus Urban",
        "CCN Facility Type",
        "Provider Type",
        "Type of Control",
        "Fiscal Year Begin Date",
        "Fiscal Year End Date",
        "report_days",
        "FTE - Employees on Payroll",
        "Number of Beds",
        "Hospital Number of Beds For Adults & Peds",
        "Total Days Title XVIII",
        "Total Days Title XIX",
        "Total Discharges Title XVIII",
        "Total Discharges Title XIX",
        "Hospital Total Days Title XVIII For Adults & Peds",
        "Hospital Total Days Title XIX For Adults & Peds",
        "Hospital Total Discharges Title XVIII For Adults & Peds",
        "Hospital Total Discharges Title XIX For Adults & Peds",
        "Cost of Charity Care",
        "Cost of Uncompensated Care",
        "Total Costs",
        "Inpatient Revenue",
        "Outpatient Revenue",
        "Total Patient Revenue",
        "Net Patient Revenue",
        "Net Income",
        "Cost To Charge Ratio",
        "Net Revenue from Medicaid",
        "Medicaid Charges",
    ]

    # Only select fields that actually exist
    cost_columns = [
        col
        for col in cost_columns
        if col in cost.columns
    ]

    cost_keep = cost[
        cost_columns
    ].copy()

    cost_keep = cost_keep.rename(
        columns={
            "Provider CCN": "ccn",
            "Hospital Name": "cost_name",
            "Street Address": "cost_address",
            "City": "cost_city",
            "State Code": "cost_state",
            "Zip Code": "cost_zip",
            "County": "cost_county",
        }
    )

    cost_keep["in_cost_report"] = True

    # --------------------------------------------------------
    # 5. Full outer join
    # --------------------------------------------------------

    master = general_keep.merge(
        cost_keep,
        on="ccn",
        how="outer",
        validate="one_to_one",
    )

    master["in_cms_general"] = (
        master["in_cms_general"]
        .fillna(False)
        .astype(bool)
    )

    master["in_cost_report"] = (
        master["in_cost_report"]
        .fillna(False)
        .astype(bool)
    )

    # --------------------------------------------------------
    # 6. Create unified identity fields
    #
    # Prefer current CMS General identity when available.
    # Fall back to Cost Report identity otherwise.
    # --------------------------------------------------------

    master["hospital_name"] = (
        master["general_name"]
        .combine_first(
            master["cost_name"]
        )
    )

    master["address"] = (
        master["general_address"]
        .combine_first(
            master["cost_address"]
        )
    )

    master["city"] = (
        master["general_city"]
        .combine_first(
            master["cost_city"]
        )
    )

    master["state"] = (
        master["general_state"]
        .combine_first(
            master["cost_state"]
        )
    )

    master["zip_code"] = (
        master["general_zip"]
        .combine_first(
            master["cost_zip"]
        )
    )

    master["county"] = (
        master["general_county"]
        .combine_first(
            master["cost_county"]
        )
    )

    # --------------------------------------------------------
    # 7. Source classification
    # --------------------------------------------------------

    master["cms_source_status"] = "BOTH"

    master.loc[
        master["in_cms_general"]
        & ~master["in_cost_report"],
        "cms_source_status",
    ] = "GENERAL_ONLY"

    master.loc[
        ~master["in_cms_general"]
        & master["in_cost_report"],
        "cms_source_status",
    ] = "COST_ONLY"

    # --------------------------------------------------------
    # 8. Put key fields first
    # --------------------------------------------------------

    priority_columns = [
        "ccn",
        "hospital_name",
        "address",
        "city",
        "state",
        "zip_code",
        "county",
        "cms_source_status",
        "in_cms_general",
        "in_cost_report",
    ]

    remaining_columns = [
        col
        for col in master.columns
        if col not in priority_columns
    ]

    master = master[
        priority_columns
        + remaining_columns
    ]

    master = master.sort_values(
        "ccn"
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # 9. Validation
    # --------------------------------------------------------

    print("\nVALIDATION")
    print("-" * 70)

    print(f"Master rows: {len(master):,}")

    print(
        "Duplicate CCNs:",
        master["ccn"]
        .duplicated()
        .sum(),
    )

    print(
        "Missing CCNs:",
        master["ccn"]
        .isna()
        .sum(),
    )

    print("\nSource coverage:")

    print(
        master["cms_source_status"]
        .value_counts()
        .to_string()
    )

    print("\nMissing unified identity fields:")

    for column in [
        "hospital_name",
        "city",
        "state",
        "zip_code",
    ]:
        print(
            f"{column:<20}: "
            f"{master[column].isna().sum():,}"
        )

    # --------------------------------------------------------
    # 10. Hard checks
    # --------------------------------------------------------

    assert (
        master["ccn"]
        .duplicated()
        .sum()
        == 0
    )

    assert (
        master["ccn"]
        .isna()
        .sum()
        == 0
    )

    expected_rows = (
        len(
            set(general_keep["ccn"])
            | set(cost_keep["ccn"])
        )
    )

    assert len(master) == expected_rows

    # --------------------------------------------------------
    # 11. Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    master.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("CMS MASTER COMPLETE")
    print("=" * 70)

    print(f"Saved to:\n{OUTPUT_FILE}")

    print("\nSample:")
    print(
        master[
            [
                "ccn",
                "hospital_name",
                "city",
                "state",
                "cms_source_status",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )


if __name__ == "__main__":
    build_cms_master()