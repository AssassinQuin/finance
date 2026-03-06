"""PostgreSQL initialization script.

Run this as part of Docker entrypoint to create initial schema.
"""

# This script is mounted at /docker-entrypoint-initdb.d/ in PostgreSQL container
# PostgreSQL executes all .sql files in this directory on first startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create migrations table first
CREATE TABLE IF NOT EXISTS migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) UNIQUE NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Gold reserves table
CREATE TABLE IF NOT EXISTS gold_reserves (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    gold_tonnes DECIMAL(15, 3),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country_code, data_date)
);

CREATE INDEX IF NOT EXISTS idx_gold_country_date 
ON gold_reserves(country_code, data_date DESC);

CREATE INDEX IF NOT EXISTS idx_gold_data_date 
ON gold_reserves(data_date DESC);

-- Watchlist assets
CREATE TABLE IF NOT EXISTS watchlist_assets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    api_code VARCHAR(50),
    name VARCHAR(100) NOT NULL,
    market VARCHAR(10) NOT NULL,
    asset_type VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    extra JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_watchlist_active 
ON watchlist_assets(is_active) WHERE is_active = TRUE;

-- GPR History
CREATE TABLE IF NOT EXISTS gpr_history (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL DEFAULT 'WLD',
    report_date DATE NOT NULL,
    gpr_index DECIMAL(10, 4) NOT NULL,
    data_source VARCHAR(50) NOT NULL DEFAULT 'Caldara-Iacoviello',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country_code, report_date)
);

CREATE INDEX IF NOT EXISTS idx_gpr_history_date 
ON gpr_history(report_date DESC);

CREATE INDEX IF NOT EXISTS idx_gpr_history_country 
ON gpr_history(country_code);

-- Gold supply demand
CREATE TABLE IF NOT EXISTS gold_supply_demand (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    quarter INTEGER,
    supply_total DECIMAL(15, 3),
    demand_total DECIMAL(15, 3),
    data_source VARCHAR(50),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(year, quarter)
);

-- UNLOGGED cache table - no WAL, faster for ephemeral data
CREATE UNLOGGED TABLE IF NOT EXISTS cache_entries (
    key VARCHAR(512) PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cache_expires 
ON cache_entries(expires_at) 
WHERE expires_at IS NOT NULL;
