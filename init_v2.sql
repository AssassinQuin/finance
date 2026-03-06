-- V2 Schema: Dimensional Model with Fact/Dimension Tables
-- Optimized for analytics and storage efficiency

-- ============================================
-- DIMENSION TABLES
-- ============================================

-- Currency dimension
CREATE TABLE IF NOT EXISTS dim_currency (
    id SERIAL PRIMARY KEY,
    currency_code VARCHAR(10) UNIQUE NOT NULL,
    currency_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Data source dimension
CREATE TABLE IF NOT EXISTS dim_data_source (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) UNIQUE NOT NULL,
    source_url VARCHAR(255),
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Country dimension
CREATE TABLE IF NOT EXISTS dim_country (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) UNIQUE NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    region VARCHAR(50),
    timezone VARCHAR(50),
    currency_id INTEGER REFERENCES dim_currency(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Asset dimension (stocks, funds, etc.)
CREATE TABLE IF NOT EXISTS dim_asset (
    id SERIAL PRIMARY KEY,
    asset_code VARCHAR(20) UNIQUE NOT NULL,
    api_code VARCHAR(50),
    asset_name VARCHAR(200),
    market VARCHAR(20),
    asset_type VARCHAR(20),
    currency_id INTEGER REFERENCES dim_currency(id),
    extra JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Period dimension (for supply/demand data)
CREATE TABLE IF NOT EXISTS dim_period (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    quarter INTEGER,
    period_label VARCHAR(20) UNIQUE NOT NULL,
    period_type VARCHAR(20) NOT NULL, -- 'yearly', 'quarterly'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Metric dimension (for supply/demand metrics)
CREATE TABLE IF NOT EXISTS dim_metric (
    id SERIAL PRIMARY KEY,
    metric_code VARCHAR(50) UNIQUE NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    unit VARCHAR(20),
    domain VARCHAR(50), -- 'gold_supply_demand'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- FACT TABLES
-- ============================================

-- Gold reserves fact table
CREATE TABLE IF NOT EXISTS fact_gold_reserve (
    id SERIAL PRIMARY KEY,
    country_id INTEGER NOT NULL REFERENCES dim_country(id),
    report_date DATE NOT NULL,
    gold_tonnes DECIMAL(15, 3),
    gold_share_pct DECIMAL(10, 4), -- Calculable: gold_tonnes / total_reserves
    gold_value_usd_m DECIMAL(20, 2), -- Calculable: gold_tonnes * gold_price
    source_id INTEGER REFERENCES dim_data_source(id),
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country_id, report_date)
);

-- GPR (Geopolitical Risk) fact table
CREATE TABLE IF NOT EXISTS fact_gpr (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL,
    report_date DATE NOT NULL,
    gpr_index DECIMAL(10, 4),
    source_id INTEGER REFERENCES dim_data_source(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country_code, report_date)
);

-- FX rate fact table
CREATE TABLE IF NOT EXISTS fact_fx_rate (
    id SERIAL PRIMARY KEY,
    base_currency_id INTEGER NOT NULL REFERENCES dim_currency(id),
    quote_currency_id INTEGER NOT NULL REFERENCES dim_currency(id),
    rate_time TIMESTAMP WITH TIME ZONE NOT NULL,
    rate DECIMAL(20, 10) NOT NULL,
    source_id INTEGER REFERENCES dim_data_source(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(base_currency_id, quote_currency_id, rate_time)
);

-- Quote fact table (for stock/fund prices)
CREATE TABLE IF NOT EXISTS fact_quote (
    id SERIAL PRIMARY KEY,
    asset_id INTEGER NOT NULL REFERENCES dim_asset(id),
    quote_time TIMESTAMP WITH TIME ZONE NOT NULL,
    price DECIMAL(20, 4),
    change_amount DECIMAL(20, 4),
    change_percent DECIMAL(10, 4),
    open_price DECIMAL(20, 4),
    high_price DECIMAL(20, 4),
    low_price DECIMAL(20, 4),
    prev_close DECIMAL(20, 4),
    volume BIGINT,
    source_id INTEGER REFERENCES dim_data_source(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset_id, quote_time)
);

-- Gold supply/demand fact table
CREATE TABLE IF NOT EXISTS fact_gold_supply_demand (
    id SERIAL PRIMARY KEY,
    period_id INTEGER NOT NULL REFERENCES dim_period(id),
    metric_id INTEGER NOT NULL REFERENCES dim_metric(id),
    value DECIMAL(20, 3),
    source_id INTEGER REFERENCES dim_data_source(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_id, metric_id)
);

-- Fetch log fact table (audit trail)
CREATE TABLE IF NOT EXISTS fact_fetch_log (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'success', 'failed', 'partial'
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    records_count INTEGER,
    error_message TEXT,
    details JSONB,
    source_id INTEGER REFERENCES dim_data_source(id),
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Gold reserves indexes
CREATE INDEX idx_fact_gold_reserve_country ON fact_gold_reserve(country_id);
CREATE INDEX idx_fact_gold_reserve_date ON fact_gold_reserve(report_date DESC);
CREATE INDEX idx_fact_gold_reserve_country_date ON fact_gold_reserve(country_id, report_date DESC);

-- GPR indexes
CREATE INDEX idx_fact_gpr_country ON fact_gpr(country_code);
CREATE INDEX idx_fact_gpr_date ON fact_gpr(report_date DESC);
CREATE INDEX idx_fact_gpr_country_date ON fact_gpr(country_code, report_date DESC);

-- FX rate indexes
CREATE INDEX idx_fact_fx_rate_currencies ON fact_fx_rate(base_currency_id, quote_currency_id);
CREATE INDEX idx_fact_fx_rate_time ON fact_fx_rate(rate_time DESC);

-- Quote indexes
CREATE INDEX idx_fact_quote_asset ON fact_quote(asset_id);
CREATE INDEX idx_fact_quote_time ON fact_quote(quote_time DESC);
CREATE INDEX idx_fact_quote_asset_time ON fact_quote(asset_id, quote_time DESC);

-- Gold supply/demand indexes
CREATE INDEX idx_fact_gold_supply_demand_period ON fact_gold_supply_demand(period_id);
CREATE INDEX idx_fact_gold_supply_demand_metric ON fact_gold_supply_demand(metric_id);

-- Fetch log indexes
CREATE INDEX idx_fact_fetch_log_task ON fact_fetch_log(task_name);
CREATE INDEX idx_fact_fetch_log_status ON fact_fetch_log(status);
CREATE INDEX idx_fact_fetch_log_started ON fact_fetch_log(started_at DESC);

-- ============================================
-- VIEWS FOR CONVENIENCE
-- ============================================

-- Gold reserves with country names (backward compatible)
CREATE OR REPLACE VIEW v_gold_reserves AS
SELECT 
    gr.id,
    c.country_code,
    c.country_name,
    gr.gold_tonnes,
    gr.gold_share_pct,
    gr.gold_value_usd_m,
    gr.report_date AS data_date,
    ds.source_name AS data_source,
    gr.fetched_at
FROM fact_gold_reserve gr
JOIN dim_country c ON gr.country_id = c.id
LEFT JOIN dim_data_source ds ON gr.source_id = ds.id
ORDER BY gr.report_date DESC, gr.gold_tonnes DESC;

-- GPR with details
CREATE OR REPLACE VIEW v_gpr_history AS
SELECT 
    gpr.id,
    gpr.country_code,
    gpr.report_date,
    gpr.gpr_index,
    ds.source_name AS data_source,
    gpr.created_at
FROM fact_gpr gpr
LEFT JOIN dim_data_source ds ON gpr.source_id = ds.id
ORDER BY gpr.report_date DESC;

-- ============================================
-- CACHE TABLE (UNLOGGED for performance)
-- ============================================

-- Cache entries (UNLOGGED for high performance)
CREATE UNLOGGED TABLE IF NOT EXISTS cache_entries (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cache_expires ON cache_entries(expires_at);

-- ============================================
-- WATCHLIST (User preferences)
-- ============================================

-- Watchlist assets
CREATE TABLE IF NOT EXISTS watchlist_assets (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    api_code VARCHAR(50),
    name VARCHAR(200),
    market VARCHAR(20),
    asset_type VARCHAR(20),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
