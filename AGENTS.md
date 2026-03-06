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
- `watchlist_assets` - User watchlist (unchanged)
- `cache_entries` - UNLOGGED table for cache storage

### Key Design Patterns

1. **Database Singleton Pattern**
   - `Database` class uses class methods with class-level state
   - All Store classes access Database through class methods (no instances)
   - Commands call `Database.init(config)` before operations
   - Proper cleanup with `Database.close()` in finally blocks

2. **Hybrid Cache Pattern**
   - PostgreSQL (UNLOGGED table) priority with File fallback
   - `HybridCache` checks PostgreSQL health before operations
   - Fallback to file cache if database unavailable

3. **Service Layer**
   - Business logic in `fcli/services/`
   - Data access in `fcli/core/stores/`
   - Scrapers in `fcli/services/scrapers/`

## Development Conventions

### Database Operations

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

## Migration Notes

### V1 → V2 Migration

- Completed: All V1 data migrated to V2 fact tables
- Backup tables dropped: `gold_reserves_v1_backup`, `gpr_history_v1_backup`
- Compatibility views created for zero-downtime migration
- Store classes still use legacy table names (via views)

### Future Refactoring

Consider updating Store classes to use V2 schema directly:
- `GoldReserveStore` → query `fact_gold_reserve` + `dim_country`
- `GPRHistoryStore` → query `fact_gpr`
- Remove compatibility views after Store migration

## Testing

All commands tested and working:
```bash
python run.py           # Quote watchlist
python run.py gold      # Gold reserves
python run.py gpr       # Geopolitical risk
python run.py fx        # Foreign exchange
python run.py watchlist # Watchlist management
```

## File Structure

```
fcli/
├── commands/       # CLI command handlers
├── core/
│   ├── models/     # Pydantic models
│   ├── stores/     # Data access layer
│   ├── cache.py    # Hybrid cache
│   ├── database.py # Database singleton
│   └── config.py   # Configuration
├── services/       # Business logic
│   └── scrapers/   # Data scrapers
└── scripts/        # Utility scripts
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
