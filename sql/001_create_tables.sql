USE healthcare_geo_analytics;


-- ============================================================
-- CITIES
-- ============================================================

CREATE TABLE IF NOT EXISTS cities (
    city_id VARCHAR(20) NOT NULL,
    city_name VARCHAR(255) NOT NULL,
    city_name_original VARCHAR(255),
    city_display VARCHAR(300),
    city_display_unique VARCHAR(350) NOT NULL,
    state VARCHAR(10) NOT NULL,
    place_type VARCHAR(50),
    place_type_code VARCHAR(20),
    functional_status VARCHAR(20),

    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,

    PRIMARY KEY (city_id),

    INDEX idx_cities_state (state),
    INDEX idx_cities_name_state (city_name, state),
    INDEX idx_cities_coordinates (latitude, longitude)
);


-- ============================================================
-- AIRPORTS
-- ============================================================

CREATE TABLE IF NOT EXISTS airports (
    airport_id VARCHAR(30) NOT NULL,
    iata_code VARCHAR(10) NOT NULL,
    icao_code VARCHAR(10),
    airport_ident VARCHAR(20),

    airport_name VARCHAR(255) NOT NULL,
    airport_display VARCHAR(350) NOT NULL,

    city VARCHAR(255),
    state VARCHAR(10),

    airport_type VARCHAR(50),
    scheduled_service VARCHAR(10),

    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    elevation_ft DOUBLE,

    PRIMARY KEY (airport_id),

    UNIQUE KEY uq_airports_iata (iata_code),

    INDEX idx_airports_state (state),
    INDEX idx_airports_city_state (city, state),
    INDEX idx_airports_coordinates (latitude, longitude)
);


-- ============================================================
-- HOSPITALS
-- ============================================================

CREATE TABLE IF NOT EXISTS hospitals (
    hospital_id VARCHAR(30) NOT NULL,
    ccn VARCHAR(10),

    hospital_name VARCHAR(500) NOT NULL,

    address VARCHAR(500),
    city VARCHAR(255),
    state VARCHAR(10),
    zip_code VARCHAR(20),
    county VARCHAR(255),
    country_code VARCHAR(10),

    telephone VARCHAR(50),
    website TEXT,

    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,

    hospital_type VARCHAR(255),
    ownership VARCHAR(255),
    status VARCHAR(50),

    is_open BOOLEAN,

    emergency_services VARCHAR(50),
    trauma_level VARCHAR(100),
    helipad VARCHAR(50),

    beds INT,
    bed_source VARCHAR(50),
    cms_beds INT,
    hifld_beds INT,

    overall_rating DECIMAL(6,2),

    provider_type VARCHAR(100),
    ccn_facility_type VARCHAR(255),
    type_of_control VARCHAR(255),
    rural_urban VARCHAR(100),

    fiscal_year_begin DATE,
    fiscal_year_end DATE,
    report_days INT,

    fte_employees DECIMAL(18,2),

    inpatient_revenue DECIMAL(20,2),
    outpatient_revenue DECIMAL(20,2),
    total_patient_revenue DECIMAL(20,2),
    net_patient_revenue DECIMAL(20,2),
    total_costs DECIMAL(20,2),
    net_income DECIMAL(20,2),

    cost_to_charge_ratio DECIMAL(12,6),

    charity_care_cost DECIMAL(20,2),
    uncompensated_care_cost DECIMAL(20,2),

    medicare_days DECIMAL(20,2),
    medicare_discharges DECIMAL(20,2),

    medicaid_days DECIMAL(20,2),
    medicaid_discharges DECIMAL(20,2),

    medicaid_net_revenue DECIMAL(20,2),
    medicaid_charges DECIMAL(20,2),

    data_source_coverage VARCHAR(50),
    cms_source_status VARCHAR(50),

    match_type VARCHAR(100),
    match_score DECIMAL(8,2),

    hifld_source TEXT,
    hifld_source_date VARCHAR(100),

    PRIMARY KEY (hospital_id),

    UNIQUE KEY uq_hospitals_ccn (ccn),

    INDEX idx_hospitals_state (state),
    INDEX idx_hospitals_city_state (city, state),
    INDEX idx_hospitals_status (status),
    INDEX idx_hospitals_open (is_open),
    INDEX idx_hospitals_type (hospital_type),
    INDEX idx_hospitals_coordinates (latitude, longitude),
    INDEX idx_hospitals_cms_coverage (data_source_coverage)
);