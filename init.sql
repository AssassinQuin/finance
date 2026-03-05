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
    change_1m DECIMAL(15, 3),
    change_3m DECIMAL(15, 3),
    change_6m DECIMAL(15, 3),
    change_12m DECIMAL(15, 3),
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

-- Central bank schedules
CREATE TABLE IF NOT EXISTS central_bank_schedules (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) UNIQUE NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    release_frequency VARCHAR(20),
    release_day_of_month INTEGER,
    release_time TIME,
    timezone VARCHAR(50),
    data_source VARCHAR(100),
    source_url TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Fetch logs
CREATE TABLE IF NOT EXISTS fetch_logs (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    records_count INTEGER DEFAULT 0,
    error_message TEXT,
    details JSONB
);

CREATE INDEX IF NOT EXISTS idx_fetch_logs_task_time 
ON fetch_logs(task_name, started_at DESC);

-- Quotes table
CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    price DECIMAL(18, 4),
    change DECIMAL(18, 4),
    change_percent DECIMAL(8, 4),
    volume BIGINT,
    open DECIMAL(18, 4),
    high DECIMAL(18, 4),
    low DECIMAL(18, 4),
    prev_close DECIMAL(18, 4),
    market VARCHAR(10),
    quote_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(code, DATE(quote_time))
);

CREATE INDEX IF NOT EXISTS idx_quotes_code_time 
ON quotes(code, quote_time DESC);

-- Exchange rates
CREATE TABLE IF NOT EXISTS exchange_rates (
    id SERIAL PRIMARY KEY,
    base_currency VARCHAR(3) NOT NULL,
    quote_currency VARCHAR(3) NOT NULL,
    rate DECIMAL(18, 8) NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(base_currency, quote_currency, DATE(fetched_at))
);

CREATE INDEX IF NOT EXISTS idx_rates_base_quote_date 
ON exchange_rates(base_currency, quote_currency, fetched_at DESC);

-- Watchlist assets
CREATE TABLE IF NOT EXISTS watchlist_assets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    market VARCHAR(10) NOT NULL,
    asset_type VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_watchlist_active 
ON watchlist_assets(is_active) WHERE is_active = TRUE;

-- GPR History
CREATE TABLE IF NOT EXISTS gpr_history (
    id SERIAL PRIMARY KEY,
    gpr_value DECIMAL(10, 4) NOT NULL,
    gpr_type VARCHAR(20) DEFAULT 'monthly',
    data_date DATE NOT NULL UNIQUE,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gpr_date 
ON gpr_history(data_date DESC);

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

-- Insert seed data for central banks
INSERT INTO central_bank_schedules 
(country_code, country_name, release_frequency, release_day_of_month, release_time, timezone, data_source, source_url, notes)
VALUES 
    ('US', 'United States', 'monthly', 20, '15:00', 'America/New_York', 'FRED/Treasury', 'https://fred.stlouisfed.org/', 'Treasury International Capital data'),
    ('DE', 'Germany', 'monthly', 7, '14:00', 'Europe/Berlin', 'Bundesbank', 'https://www.bundesbank.de/', 'Monthly reserve assets'),
    ('IT', 'Italy', 'monthly', 7, '14:00', 'Europe/Rome', 'Banca d''Italia', 'https://www.bancaditalia.it/', 'Official reserve assets'),
    ('FR', 'France', 'monthly', 7, '14:00', 'Europe/Paris', 'Banque de France', 'https://www.banque-france.fr/', 'Reserve assets'),
    ('CN', 'China', 'monthly', 7, '15:00', 'Asia/Shanghai', 'SAFE', 'http://www.safe.gov.cn/', 'Official reserve assets'),
    ('RU', 'Russia', 'monthly', 7, '12:00', 'Europe/Moscow', 'CBR', 'https://www.cbr.ru/', 'International reserves'),
    ('JP', 'Japan', 'monthly', 7, '09:00', 'Asia/Tokyo', 'BOJ', 'https://www.boj.or.jp/', 'Foreign reserves'),
    ('IN', 'India', 'monthly', 7, '17:30', 'Asia/Kolkata', 'RBI', 'https://www.rbi.org.in/', 'Foreign exchange reserves'),
    ('TR', 'Turkey', 'weekly', NULL, '14:30', 'Europe/Istanbul', 'CBRT', 'https://www.tcmb.gov.tr/', 'Weekly international reserves'),
    ('CH', 'Switzerland', 'monthly', 7, '08:00', 'Europe/Zurich', 'SNB', 'https://www.snb.ch/', 'Foreign currency reserves')
ON CONFLICT (country_code) DO NOTHING;
