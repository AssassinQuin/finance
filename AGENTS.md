# AI Agent Development Guide

## Project Overview

FCLI is a command-line financial data tool built with Python, async/await patterns, and PostgreSQL with dimension/fact table architecture (V2).

## Architecture

### Database Schema (V2)

The project uses a **dimensional modeling** approach (star schema):

**Dimension Tables:**
- `dim_country` - Country reference data
- `dim_currency` - Currency reference data
- `dim_data_source` - Data source metadata
- `dim_asset` - Financial asset metadata
- `dim_period` - Time period dimensions
- `dim_metric` - Metric definitions

**Fact Tables:**
- `fact_gold_reserve` - Central bank gold reserves
- `fact_gpr` - Geopolitical risk index data
- `fact_fx_rate` - Foreign exchange rates
- `fact_quote` - Asset price quotes
- `fact_gold_supply_demand` - Gold supply/demand data
- `fact_fetch_log` - Data fetch operation logs

**Legacy Compatibility:**
- `gold_reserves` (VIEW) → maps to `fact_gold_reserve` + `dim_country`
- `gpr_history` (VIEW) → maps to `fact_gpr`

### SQL Queries

Use V2 fact/dimension tables in new code:
```sql
-- PREFERRED: V2 schema with joins
SELECT 
    f.gold_tonnes,
    c.country_name,
    ds.source_name
FROM fact_gold_reserve f
JOIN dim_country c ON f.country_id = c.id
JOIN dim_data_source ds ON f.source_id = ds.id

-- ACCEPTABLE: Legacy views (for backward compatibility)
SELECT * FROM gold_reserves
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
        data = await Database.fetch_all("SELECT * FROM fact_gold_reserve")
    finally:
        await Database.close()

# INCORRECT: Creating Database instances
db = Database()  # Never do this
```

### Store Classes

All Store classes follow the same pattern:
- Use `Database.fetch_all()`, `Database.fetch_one()`, `Database.execute()`
- No instance state (class methods only)
- Check `Database.is_enabled()` before database operations

**Available Stores:**
- `GoldSupplyDemandStore` - V2 fact tables (fact_gold_supply_demand + dim_period + dim_metric)
- `QuoteFactStore` - V2 fact tables (fact_quote + dim_asset) - not yet integrated in services
- `ExchangeRateFactStore` - V2 fact tables (fact_fx_rate + dim_currency) - not yet integrated in services
- `GoldReserveStore` - Legacy view (gold_reserves)
- `GPRHistoryStore` - Legacy view (gpr_history)
- `WatchlistAssetStore` - Direct table (watchlist_assets)
- `FundStore` - Direct table (funds)

## Migration Notes

### V1 → V2 Migration

- Completed: All V1 data migrated to V2 fact tables
- Backup tables dropped: `gold_reserves_v1_backup`, `gpr_history_v1_backup`
- Compatibility views created for zero-downtime migration
- V1 Stores removed: `QuoteStore`, `ExchangeRateStore` (dead code)
- GoldSupplyDemandStore migrated to V2 schema

### Future Refactoring

Consider updating Store classes to use V2 schema directly:
- `GoldReserveStore` → query `fact_gold_reserve` + `dim_country`
- `GPRHistoryStore` → query `fact_gpr`
- Remove compatibility views after Store migration
- Integrate `QuoteFactStore` and `ExchangeRateFactStore` into services

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
│   ├── stores/          # Data access layer
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
    ├── migrate.py       # Database migration
    └── save_gold_reserves.py
```

## Common Tasks

### Adding New Data Source

1. Create scraper in `fcli/services/scrapers/`
2. Create Store class in `fcli/core/stores/`
3. Add dimensions to `init_v2.sql` if needed
4. Create fact table in `init_v2.sql`
5. Add command in `fcli/commands/`

### Modifying Existing Data

1. Update fact table schema in `init_v2.sql`
2. Update Store class queries
3. Update Pydantic model in `fcli/core/models/`
4. Test with `python run.py <command>`

### Database Schema Changes

1. Modify `init_v2.sql`
2. Create migration script if data exists
3. Test migration on backup
4. Apply to production
5. Update Store classes

## Performance Optimization

- UNLOGGED tables for cache (`cache_entries`)
- Proper indexes on fact tables (see `init_v2.sql`)
- Connection pooling via asyncpg
- Dimensional modeling for query performance

## Error Handling

- Database unavailable → fallback to file cache
- Scraper failure → log and continue
- Invalid data → skip with warning

## Security

- Environment variables for credentials (`.env`)
- No hardcoded passwords
- SQL injection prevention via parameterized queries
