# Healthcare Geo-Analytics & Facility Locator

An end-to-end healthcare geo-analytics project that integrates public hospital, geographic, airport, and CMS datasets into an interactive facility-locator dashboard.

The project covers the complete workflow:

**Data Collection → Data Profiling → Entity Resolution → ETL → MySQL → Geospatial Modeling → Tableau**

## Live Dashboard

**Tableau Public:**  
https://public.tableau.com/shared/53B8QXYPJ?:display_count=n&:origin=viz_share_link

The dashboard allows users to:

- Search around a U.S. city or airport
- Select a search radius from 0–100 miles
- View hospitals within the selected radius
- Compare hospital distance, bed capacity, ownership, status, emergency services, and CMS rating
- View summary KPIs for the selected area
- Switch between City and Airport modes while preserving the previous selection

---

## Project Architecture

    Authoritative Public Datasets
                ↓
    Python Collection & Profiling
                ↓
       ETL + Entity Resolution
                ↓
       Processed Data Layer
                ↓
              MySQL
                ↓
      Geospatial Distance Bridge
                ↓
             Tableau
                ↓
    Interactive Facility Locator

---

## Data Sources

### HIFLD Hospitals

Used as the primary geographic hospital universe.

- **8,339** final physical hospital records
- Provides hospital coordinates and geographic attributes
- Covers the United States and supported U.S. territories

### CMS Hospital General Information

Used to enrich hospitals with:

- CMS Certification Number
- Hospital type
- Ownership
- Emergency services
- CMS overall rating

### CMS Hospital Cost Report

Used for hospital operational and financial measures including:

- Beds
- Patient revenue
- Hospital costs
- Net income
- Medicare utilization
- Medicaid utilization
- Charity care
- Uncompensated care

### U.S. Census Places

Used for the City search mode.

- **32,350** cities, towns, villages, CDPs, and other Census places

### OurAirports

Used for the Airport search mode.

- **634** U.S. scheduled-service airports with IATA codes

---

## Entity Resolution

Hospital records across HIFLD and CMS do not share a universal identifier, so the project uses a multi-stage entity-resolution pipeline.

The final trusted HIFLD ↔ CMS linkage contains **5,391 hospitals**.

| Match Rule | Matches |
|---|---:|
| Exact Name + ZIP + State | 3,557 |
| Exact Address + ZIP + State | 1,261 |
| Exact Name + City + State | 126 |
| High-Confidence Fuzzy Match | 407 |
| Precision Secondary Fuzzy Match | 40 |
| **Total** | **5,391** |

Uncertain matches were intentionally left unresolved instead of forcing low-confidence relationships.

### Final Hospital Coverage

| Coverage | Hospitals |
|---|---:|
| CMS Enriched | 5,391 |
| HIFLD Only | 2,948 |
| **Total** | **8,339** |

---

## Geospatial Modeling

A precomputed location-to-hospital distance bridge was created using Haversine distance.

### Search Locations

| Location Type | Count |
|---|---:|
| Census Places | 32,350 |
| Airports | 634 |
| **Total** | **32,984** |

Only location-hospital pairs within **100 miles** are retained.

### Distance Bridge

- **4,242,623** location-hospital pairs
- **32,791** locations with at least one hospital within 100 miles
- **8,334** hospitals represented

Precomputing the bridge avoids recalculating every geographic distance during Tableau interactions and makes radius filtering substantially more responsive.

---

## MySQL Data Layer

Database:

    healthcare_geo_analytics

Main analytical tables:

| Table | Rows |
|---|---:|
| cities | 32,350 |
| airports | 634 |
| hospitals | 8,339 |
| **Total** | **41,323** |

Database schema and index definitions are stored in the `sql/` directory.

---

## Tableau Dashboard

The final dashboard provides an interactive healthcare facility search experience.

### Search Controls

- **Search By:** City / Airport
- **Location:** dynamic selector based on search mode
- **Radius:** 0–100 miles

City and Airport selections are stored independently, allowing users to switch modes without temporarily blanking the dashboard.

### KPI Cards

- Hospital Count
- Open Hospitals
- Total Beds
- Average CMS Rating

### Map

The interactive map includes:

- Hospitals within the selected radius
- Selected-location marker
- Hospital distance tooltips
- Dynamic geographic filtering

### Hospital Results Table

The results table includes:

- Hospital Name
- Emergency Services
- Hospital Type
- Ownership
- Status
- Distance
- Beds
- CMS Overall Rating

---

## Repository Structure

    healthcare-geo-analytics-facility-locator/
    │
    ├── README.md
    ├── requirements.txt
    ├── .env.example
    │
    ├── sql/
    │   ├── 001_create_tables.sql
    │   ├── 01_schema.sql
    │   └── 02_indexes.sql
    │
    ├── src/
    │   ├── collect_hifld.py
    │   ├── collect_cms_general.py
    │   │
    │   ├── profile_airports.py
    │   ├── profile_census_cities.py
    │   ├── profile_cms_cost_report.py
    │   ├── profile_cms_general.py
    │   │
    │   ├── transform_airports.py
    │   ├── transform_cities.py
    │   ├── transform_hifld_hospitals.py
    │   ├── transform_hospitals.py
    │   │
    │   ├── match_hifld_exact.py
    │   ├── create_accepted_fuzzy_matches.py
    │   ├── create_precision_secondary_matches.py
    │   │
    │   ├── build_cms_master.py
    │   ├── build_hifld_match_master.py
    │   ├── build_enriched_hospital_base.py
    │   │
    │   ├── build_tableau_locations.py
    │   ├── build_tableau_dataset.py
    │   │
    │   ├── load_cities.py
    │   ├── load_airports.py
    │   ├── load_hospitals.py
    │   ├── load_pipeline.py
    │   │
    │   ├── validate_processed_data.py
    │   ├── validators.py
    │   ├── utils_geo.py
    │   └── config.py
    │
    ├── data/
    │   ├── raw/
    │   ├── intermediate/
    │   ├── processed/
    │   └── tableau/
    │
    └── logs/

Large generated datasets are excluded from Git through `.gitignore`.

---

## Technology Stack

**Data Engineering**
- Python
- pandas
- GeoPandas
- RapidFuzz
- Requests

**Database**
- MySQL

**Geospatial Analysis**
- Haversine distance
- Latitude/longitude spatial modeling

**Visualization**
- Tableau
- Tableau Public

**Development**
- Git
- GitHub
- Python virtual environments

---

## Data Pipeline

    1. Collect authoritative public datasets
    2. Profile schemas and data quality
    3. Standardize hospital and location records
    4. Perform deterministic hospital matching
    5. Analyze unmatched hospital records
    6. Apply high-confidence fuzzy matching
    7. Build canonical CMS hospital records
    8. Enrich the HIFLD hospital universe
    9. Validate processed datasets
    10. Load analytical tables into MySQL
    11. Build Tableau location dataset
    12. Precompute location-hospital distances
    13. Build and publish the Tableau dashboard

---

## Key Engineering Decisions

### HIFLD as the Geographic Hospital Base

HIFLD provides the physical hospital universe and facility coordinates. CMS datasets are used as enrichment sources rather than replacing the geographic base.

### Conservative Entity Resolution

Only deterministic and high-confidence fuzzy matches are accepted. Ambiguous records remain unmatched instead of introducing potentially incorrect relationships.

### Precomputed Distance Bridge

Location-hospital distances are precomputed for all pairs within 100 miles. This moves expensive geospatial calculations out of the dashboard runtime and improves interactivity.

### Generated Data Excluded from Git

Raw, intermediate, processed, and Tableau-generated datasets are excluded from version control. The repository contains the source code required to reproduce the pipeline.

---

## Example Workflow

    Select City
        ↓
    Choose Stony Brook, NY
        ↓
    Set Radius
        ↓
    View Nearby Hospitals
        ↓
    Compare Distance, Beds, Ownership,
    Emergency Services, and CMS Rating

The same workflow can be performed using an airport such as JFK instead of a city.

---

## Future Enhancements

Potential extensions include:

- Hospital specialty filtering
- Advanced financial-performance analysis
- Medicare and Medicaid utilization analysis
- Hospital quality comparisons
- Road-network or drive-time distance
- Demographic context
- Cloud-hosted analytical infrastructure
- Automated source-data refresh pipelines

---

## Author

**Sai Charan Movva**  
M.S. Data Science — Stony Brook University

**GitHub:**  
https://github.com/MSaiCharan2334

---

## Explore the Project

**Healthcare Geo-Analytics & Facility Locator**

https://public.tableau.com/shared/53B8QXYPJ?:display_count=n&:origin=viz_share_link
