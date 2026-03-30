# AI Agent Development Guide

## Project Overview

FCLI is a command-line financial data tool built with Python, async/await patterns, and PostgreSQL with flat table architecture (V3).

## Architecture

### Database Schema (V3)

Simple flat tables — no JOINs, no dimension tables, no star schema.

**Data Tables:**
| Table | Description |
|-------|-------------|
| `gold_reserves` | Central bank gold reserves (country_code, country_name, gold_tonnes, report_date) |
| `gpr_history` | Geopolitical risk index (country_code, report_date, gpr_index) |
| `quotes` | Asset price quotes (code, name, price, change_percent, quote_time) |
| `fx_rates` | Foreign exchange rates (base_currency, quote_currency, rate, rate_time) |
| `gold_supply_demand` | Gold supply/demand quarterly data (year, quarter, all metrics) |
| `funds` | Fund metadata (fund_code, fund_name) |
| `fund_scales` | Fund scale history (fund_id, scale, scale_date) |
| `watchlist_assets` | User watchlist (code, added_at) |
| `cache_entries` | UNLOGGED cache table |

### SQL Queries

All queries are simple single-table SELECTs:
```sql
-- Get latest gold reserves
SELECT * FROM gold_reserves
ORDER BY report_date DESC, gold_tonnes DESC;

-- Get quotes by code
SELECT * FROM quotes WHERE code = $1
ORDER BY quote_time DESC LIMIT 1;

-- Get exchange rate
SELECT * FROM fx_rates
WHERE base_currency = $1 AND quote_currency = $2
ORDER BY rate_time DESC LIMIT 1;
```

### Datetime Handling

- PostgreSQL TIMESTAMP fields use `datetime` objects
- NOT Unix timestamps
- Use `datetime.now(timezone.utc)` for current time

## CLI Commands

### Command Structure

The CLI uses Typer with nested commands. All commands support `-h` as shortcut for `--help`:

```bash
# Global help
python run.py -h
python run.py --help

# Subcommand help
python run.py watchlist -h
python run.py gold -h
python run.py gpr -h
python run.py fx -h
```

### Watchlist Commands

```bash
# Query watchlist quotes (default)
python run.py watchlist
python run.py watchlist -h

# Add multiple assets (space-separated)
python run.py watchlist add 600519
python run.py watchlist add 600519 000858 AAPL

# Remove multiple assets (space-separated)
python run.py watchlist rm 600519
python run.py watchlist rm 600519 000858 AAPL

# List all watchlist assets
python run.py watchlist ls

# Clear watchlist (not implemented)
python run.py watchlist clear
```

### Gold Commands

```bash
# Gold reserves (default)
python run.py gold
python run.py gold -u           # Force update
python run.py gold -h           # Show help

# Gold supply/demand
python run.py gold supply
```

### GPR Commands

```bash
# GPR index (default)
python run.py gpr
python run.py gpr -u              # Force update
python run.py gpr --no-chart      # No chart display
python run.py gpr -h              # Show help

# GPR history
python run.py gpr history -m 60   # 60 months
```

### FX Commands

```bash
# USD rates (default)
python run.py fx
python run.py fx -h              # Show help

# Specific rate
python run.py fx USD CNY         # USD/CNY rate
python run.py fx EUR             # EUR rates
```

### Watchlist Service

The `WatchlistService` supports batch operations:

```python
from fcli.services.watchlist_service import watchlist_service

# Add multiple assets
count = await watchlist_service.add_assets(["600519", "000858", "AAPL"])

# Remove multiple assets  
count = await watchlist_service.remove_assets(["600519", "000858"])

# List all assets
assets = await watchlist_service.list_assets()
```

## Database Operations

```python
# CORRECT: Use class methods, init before use
async def command_handler():
    try:
        await Database.init(config)
        # Use Store classes or Database class methods
        data = await Database.fetch_all("SELECT * FROM gold_reserves")
    finally:
        await Database.close()

# INCORRECT: Creating Database instances
db = Database()  # Never do this
```

### Store Classes

All Store classes follow the same pattern:
- Use `Database.fetch_all()`, `Database.fetch_one()`, `Database.execute()`, `Database.execute_many()`
- No instance state (class methods only)
- Check `Database.is_enabled()` before database operations
- Single-table queries (no JOINs)

**Available Stores:**
- `GoldReserveStore` - Flat table `gold_reserves`
- `GPRHistoryStore` - Flat table `gpr_history`
- `QuoteStore` - Flat table `quotes`
- `ExchangeRateStore` - Flat table `fx_rates`
- `GoldSupplyDemandStore` - Flat table `gold_supply_demand`
- `FundStore` - Flat tables `funds` + `fund_scales`
- `WatchlistAssetStore` - Flat table `watchlist_assets`

**Backward compatibility aliases (deprecated):**
- `QuoteFactStore` = `QuoteStore`
- `ExchangeRateFactStore` = `ExchangeRateStore`

## Migration Notes

### V2 → V3 Migration

- Dropped all `dim_*` dimension tables (dim_country, dim_currency, dim_data_source, dim_asset, dim_period, dim_metric)
- Dropped all `fact_*` fact tables (fact_gold_reserve, fact_gpr, fact_fx_rate, fact_quote, fact_gold_supply_demand)
- Renamed `dim_fund` → `funds`, `fact_fund_scale` → `fund_scales`
- Created flat tables: gold_reserves, gpr_history, quotes, fx_rates, gold_supply_demand
- Data migrated via INSERT...SELECT from V2 star schema
- All Stores rewritten: no JOINs, no get_or_create, batch writes via execute_many()
- Migration script: `fcli/scripts/migrate_v3.py`

### V1 → V2 → V3 History

- V1: Simple tables (gold_reserves, gpr_history)
- V2: Star schema (dim_* + fact_*) — over-engineered for a CLI tool
- V3: Flat tables — simple, no JOINs, same PG benefits

## Testing

All commands tested and working:
```bash
python run.py -h              # Show help
python run.py watchlist -h    # Watchlist help
python run.py gold -h         # Gold help
python run.py gpr -h          # GPR help
python run.py fx -h           # FX help
```

## File Structure

```
fcli/
├── main.py              # CLI entry (Typer)
├── commands/            # CLI command handlers
│   ├── watchlist.py     # Watchlist commands (add/rm/ls/clear)
│   ├── gold.py          # Gold commands (reserves/supply)
│   ├── gpr.py           # GPR commands (index/history)
│   └── fx.py            # FX commands (rate)
├── core/
│   ├── models/          # Pydantic models
│   ├── stores/          # Data access layer (flat tables)
│   │   ├── gold.py            # GoldReserveStore
│   │   ├── gpr.py             # GPRHistoryStore
│   │   ├── quote.py           # QuoteStore
│   │   ├── exchange_rate.py   # ExchangeRateStore
│   │   ├── gold_supply_demand.py # GoldSupplyDemandStore
│   │   ├── fund.py            # FundStore
│   │   └── watchlist.py       # WatchlistAssetStore
│   ├── cache.py         # Hybrid cache
│   ├── database.py      # Database singleton
│   └── config.py        # Configuration
├── services/
│   ├── quote_service.py
│   ├── gold_reserve_service.py
│   ├── gold_supply_demand_service.py
│   ├── forex_service.py
│   ├── gpr_service.py
│   ├── watchlist_service.py  # Watchlist service (batch ops)
│   └── scrapers/        # Data scrapers
├── infra/
│   └── http_client.py   # HTTP client wrapper
├── utils/
│   ├── presenter.py     # Terminal output
│   ├── logger.py        # Logging
│   └── time_util.py     # Time utilities
└── scripts/
    ├── migrate_v3.py    # V3 migration (V2→V3 flatten)
    └── save_gold_reserves.py
```

## Common Tasks

### Adding New Data Source

1. Create scraper in `fcli/services/scrapers/`
2. Create Store class in `fcli/core/stores/` (single flat table, no JOINs)
3. Add command in `fcli/commands/`

### Modifying Existing Data

1. Update table schema (ALTER TABLE or recreate)
2. Update Store class queries
3. Update Pydantic model in `fcli/core/models/`
4. Test with `python run.py <command>`

## Performance Optimization

- UNLOGGED tables for cache (`cache_entries`)
- Proper indexes on flat tables
- Connection pooling via asyncpg
- `execute_many()` for batch writes

## Error Handling

- Database unavailable → fallback to file cache
- Scraper failure → log and continue
- Invalid data → skip with warning

## Security

- Environment variables for credentials (`.env`)
- No hardcoded passwords
- SQL injection prevention via parameterized queries
