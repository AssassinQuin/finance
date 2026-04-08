# AI Agent Development Guide

## Project Overview

FCLI is a command-line financial data tool built with Python, async/await patterns, and PostgreSQL with flat table architecture (V3).

**Version**: v0.2.0

## Architecture

### Database Schema (V3)

Simple flat tables — no JOINs, no dimension tables, no star schema.

**Data Tables:**

| Table                  | Description                                                                       |
| ---------------------- | --------------------------------------------------------------------------------- |
| `gold_reserves`      | Central bank gold reserves (country_code, country_name, gold_tonnes, report_date) |
| `gpr_history`        | Geopolitical risk index (country_code, report_date, gpr_index)                    |
| `quotes`             | Asset price quotes (code, name, price, change_percent, quote_time)                |
| `fx_rates`           | Foreign exchange rates (base_currency, quote_currency, rate, rate_time)           |
| `gold_supply_demand` | Gold supply/demand quarterly data (year, quarter, all metrics)                    |
| `funds`              | Fund metadata (fund_code, fund_name)                                              |
| `fund_scales`        | Fund scale history (fund_id, scale, scale_date)                                   |
| `watchlist_assets`   | User watchlist (code, added_at)                                                   |
| `cache_entries`      | UNLOGGED cache table                                                              |

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

### Code Mapping

The `code_mapper` module (`fcli/core/code_mapper.py`) provides unified code conversion:

```python
from fcli.core.code_mapper import code_mapper

# Convert code to API-specific format
secid = code_mapper.to_eastmoney_secid(code, market)

# Infer market from code
market = code_mapper.infer_market(code)

# Infer asset type from code
asset_type = code_mapper.infer_type(code)
```

All code↔api_code/secid conversions are handled in one place, avoiding scattered mapping logic.

## CLI Commands

### Command Structure

The CLI uses Typer with nested commands. All commands support `-h` as shortcut for `--help`:

```bash
# Global help
python run.py -h
python run.py --help

# Subcommand help
python run.py watchlist -h
python run.py market -h
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

**Available Gold Reserves Sources:**
- `WGCScraper` - World Gold Council (primary)
- `RIAScraper` - Russian Central Bank (RIA Novosti)

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

**GPR Service** provides multi-country comparison and risk analysis:

```python
from fcli.services.gpr_service import GPRService

service = GPRService()
analysis = await service.get_gpr_analysis(country_code="WLD")
comparison = await service.get_multi_country_comparison(["WLD", "CHN", "RUS"])
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

**Available Forex Sources:**
- `ExchangeRateSource` - ExchangeRate API (primary)
- `FrankfurterSource` - Frankfurter API (fallback)

### Market Commands

```bash
# Fund search
python run.py market search 沪深 300
python run.py market search 510300 -t ETF
python run.py market search 黄金 -n 5

# Fund detail
python run.py market detail 510300

# Update fund data
python run.py market update
python run.py market update -t ETF -f
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
# CORRECT: Use Database.session() context manager
async def command_handler():
    async with Database.session(config):
        # Use Store classes or Database class methods
        data = await Database.fetch_all("SELECT * FROM gold_reserves")

# CORRECT: Auto-lazy-init (no explicit init needed)
async def simple_query():
    rows = await Database.fetch_all("SELECT * FROM gold_reserves")

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

## DI Container

The `Container` class (`fcli/core/container.py`) manages all service dependencies:

```python
from fcli.core.container import container

# Access services (lazy-initialized singletons)
service = container.quote_service
service = container.gold_reserve_service

# In command handlers, use with Database.session()
async with Database.session(config):
    result = await container.quote_service.get_quotes(codes)
```

- All services are lazy-initialized on first access
- Services can be replaced for testing
- Module-level singleton: `container = Container()`

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
- V2: Star schema (dim*\* + fact*\*) — over-engineered for a CLI tool
- V3: Flat tables — simple, no JOINs, same PG benefits

## Testing

All commands tested and working:

```bash
python run.py -h              # Show help
python run.py watchlist -h    # Watchlist help
python run.py market -h       # Market help
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
│   ├── market.py        # Market commands (search/detail/update)
│   ├── gold.py          # Gold commands (reserves/supply)
│   ├── gpr.py           # GPR commands (index/history)
│   └── fx.py            # FX commands (rate)
├── core/
│   ├── cache.py         # Hybrid cache (PG UNLOGGED + File)
│   ├── cache_strategy.py # AssetType-based cache strategy
│   ├── config.py        # Settings + config singleton
│   ├── container.py     # DI container (lazy singletons)
│   ├── database.py      # PostgreSQL pool (auto-lazy-init)
│   ├── exceptions.py    # Custom exceptions
│   ├── factories.py     # Factory functions
│   ├── code_mapper.py   # Unified code mapping (code↔api_code/secid conversions)
│   ├── storage.py       # HybridStorage (JSON local)
│   ├── interfaces/      # Interface definitions (Protocol + ABC)
│   │   ├── cache.py     # CacheABC
│   │   ├── database.py  # DatabaseABC
│   │   ├── http.py      # HttpClientABC
│   │   ├── source.py    # QuoteSourceABC
│   │   └── storage.py   # StorageABC
│   ├── models/          # Pydantic v2 models
│   │   ├── asset.py     # Asset, AssetType, Market
│   │   ├── base.py      # ScraperResult
│   │   ├── fund.py      # Fund, FundDetail, FundType
│   │   ├── gold.py      # GoldReserve
│   │   ├── gold_supply_demand.py
│   │   ├── gpr.py       # GprRecord
│   │   └── log.py       # LogEntry
│   └── stores/          # Data access layer (flat tables)
│       ├── gold.py            # GoldReserveStore
│       ├── gpr.py             # GPRHistoryStore
│       ├── quote.py           # QuoteStore
│       ├── exchange_rate.py   # ExchangeRateStore
│       ├── gold_supply_demand.py # GoldSupplyDemandStore
│       ├── fund.py            # FundStore
│       └── watchlist.py       # WatchlistAssetStore
├── services/
│   ├── quote_service.py       # Quote service
│   ├── gold_reserve_service.py
│   ├── gold_supply_demand_service.py
│   ├── forex_service.py       # Forex service
│   ├── gpr_service.py         # GPR service
│   ├── fund_service.py        # Fund service
│   ├── watchlist_service.py   # Watchlist service (batch ops)
│   ├── scrapers/        # Data scrapers
│       ├── base.py            # BaseScraper[T], ScraperResult[T]
│       ├── akshare_scraper.py # A-stock (Akshare)
│       ├── fund_scraper.py    # Fund data (Akshare)
│       ├── fund_quote_source.py # Fund quote source
│       ├── sina_quote_source.py # Sina quote source
+ │       ├── eastmoney_quote_source.py # Eastmoney quote source
│       ├── gpr_scraper.py     # GPR data
│       ├── imf_scraper.py     # IMF data
│       ├── wgc_scraper.py     # WGC gold reserves
+ │       ├── ria_scraper.py     # RIA (Russian Central Bank) gold reserves
+ │       ├── exchangerate_source.py # ExchangeRate API forex source
+ │       ├── frankfurter_source.py # Frankfurter API forex source
│       └── safe_scraper.py    # Safe scraper wrapper
├── infra/
│   └── http_client.py   # HTTP client wrapper (aiohttp)
├── utils/
│   ├── presenter.py     # Terminal output (Rich)
│   ├── logger.py        # Logging
│   └── time_util.py     # Time utilities
└── scripts/
    ├── migrate_v3.py    # V3 migration (V2→V3 flatten)
    ├── import_wgc_data.py
    └── save_gold_reserves.py
```

## Common Tasks

### Adding New Data Source

1. Create scraper in `fcli/services/scrapers/`
2. Create Store class in `fcli/core/stores/` (single flat table, no JOINs)
3. Add command in `fcli/commands/`

* [ ] Modifying Existing Data

1. Update table schema (ALTER TABLE or recreate)
2. Update Store class queries
3. Update Pydantic model in `fcli/core/models/`
4. Test with `python run.py <command>`

## Performance Optimization

- [ ] UNLOGGED tables for cache (`cache_entries`)
- [ ] Proper indexes on flat tables
- [ ] Connection pooling via asyncpg
- [ ] `execute_many()` for batch writes

## Error Handling

- Database unavailable → fallback to file cache
- Scraper failure → log and continue
- Invalid data → skip with warning

## Security

- Environment variables for credentials (`.env`)
- No hardcoded passwords
- SQL injection prevention via parameterized queries

## Code Quality

- 所有文件修改后必须运行 ruff 检查并修复格式问题：`ruff check --fix && ruff format`
