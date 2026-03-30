# DB 扁平化重构方案 — V2 星型schema → V3 简单平面表

## 一、目标

删掉所有 `dim_*` 维度表和 `fact_*` 事实表，改用类似 `watchlist_assets` 的简单平面表。
消除所有 JOIN 查询、N+1 get_or_create 开销、死代码。

保留：PostgreSQL、asyncpg、UNLOGGED cache、watchlist_assets、cache_entries。

---

## 二、新表结构 (DDL)

### 2.1 gold_reserves (替换 dim_country + fact_gold_reserve)

```sql
CREATE TABLE IF NOT EXISTS gold_reserves (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    gold_tonnes NUMERIC(12, 3) NOT NULL,
    report_date DATE NOT NULL,
    data_source VARCHAR(50) DEFAULT 'IMF',
    fetched_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (country_code, report_date)
);
CREATE INDEX IF NOT EXISTS idx_gold_reserves_date ON gold_reserves (report_date DESC);
CREATE INDEX IF NOT EXISTS idx_gold_reserves_country ON gold_reserves (country_code);
CREATE INDEX IF NOT EXISTS idx_gold_reserves_country_date ON gold_reserves (country_code, report_date DESC);
```

### 2.2 gpr_history (替换 fact_gpr + dim_data_source)

```sql
CREATE TABLE IF NOT EXISTS gpr_history (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) DEFAULT 'WLD',
    report_date DATE NOT NULL,
    gpr_index NUMERIC(10, 4) NOT NULL,
    data_source VARCHAR(50) DEFAULT 'Caldara-Iacoviello',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (country_code, report_date)
);
CREATE INDEX IF NOT EXISTS idx_gpr_date ON gpr_history (report_date DESC);
```

### 2.3 quotes (替换 dim_asset + fact_quote)

```sql
CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    asset_type VARCHAR(20) DEFAULT 'stock',
    price NUMERIC(15, 4),
    change_amount NUMERIC(15, 4),
    change_percent NUMERIC(8, 4),
    high_price NUMERIC(15, 4),
    low_price NUMERIC(15, 4),
    open_price NUMERIC(15, 4),
    prev_close NUMERIC(15, 4),
    volume BIGINT,
    quote_time TIMESTAMP NOT NULL,
    data_source VARCHAR(50) DEFAULT 'Akshare',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (code, DATE(quote_time))
);
CREATE INDEX IF NOT EXISTS idx_quotes_code ON quotes (code, quote_time DESC);
```

### 2.4 fx_rates (替换 dim_currency + fact_fx_rate)

```sql
CREATE TABLE IF NOT EXISTS fx_rates (
    id SERIAL PRIMARY KEY,
    base_currency VARCHAR(10) NOT NULL,
    quote_currency VARCHAR(10) NOT NULL,
    rate NUMERIC(15, 8) NOT NULL,
    rate_time TIMESTAMP NOT NULL,
    data_source VARCHAR(50) DEFAULT 'Frankfurter',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (base_currency, quote_currency, DATE(rate_time))
);
CREATE INDEX IF NOT EXISTS idx_fx_pair ON fx_rates (base_currency, quote_currency, rate_time DESC);
```

### 2.5 gold_supply_demand (替换 dim_period + fact_gold_supply_demand)

```sql
CREATE TABLE IF NOT EXISTS gold_supply_demand (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL CHECK (quarter IN (1, 2, 3, 4)),
    mine_production NUMERIC(12, 3),
    recycling NUMERIC(12, 3),
    net_hedging NUMERIC(12, 3),
    total_supply NUMERIC(12, 3),
    jewelry NUMERIC(12, 3),
    technology NUMERIC(12, 3),
    total_investment NUMERIC(12, 3),
    bars_coins NUMERIC(12, 3),
    etfs NUMERIC(12, 3),
    otc_investment NUMERIC(12, 3),
    central_banks NUMERIC(12, 3),
    total_demand NUMERIC(12, 3),
    supply_demand_balance NUMERIC(12, 3),
    price_avg_usd NUMERIC(10, 2),
    data_source VARCHAR(50) DEFAULT 'WGC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (year, quarter)
);
```

### 2.6 funds / fund_scales (重命名现有表)

```sql
-- dim_fund 本身就是平面表，只改名
ALTER TABLE dim_fund RENAME TO funds;
-- fact_fund_scale 也是，改名
ALTER TABLE fact_fund_scale RENAME TO fund_scales;
-- fund_scales.fund_id 引用的表从 dim_fund 变成 funds，FK 自动跟着
```

### 2.7 不变的表

- `watchlist_assets` — 已经是平面表，不动
- `cache_entries` — UNLOGGED 缓存表，不动
- `migrations` — 迁移记录表，不动

---

## 三、数据迁移 (SQL)

```sql
-- ============================================================
-- Step 1: gold_reserves (fact_gold_reserve + dim_country + dim_data_source → gold_reserves)
-- ============================================================
INSERT INTO gold_reserves (country_code, country_name, gold_tonnes, report_date, data_source, fetched_at, created_at, updated_at)
SELECT
    c.country_code,
    c.country_name,
    f.gold_tonnes,
    f.report_date,
    COALESCE(ds.source_name, 'IMF'),
    f.fetched_at,
    f.created_at,
    f.updated_at
FROM fact_gold_reserve f
JOIN dim_country c ON f.country_id = c.id
LEFT JOIN dim_data_source ds ON f.source_id = ds.id
ON CONFLICT (country_code, report_date) DO NOTHING;

-- ============================================================
-- Step 2: gpr_history (fact_gpr + dim_data_source → gpr_history)
-- ============================================================
INSERT INTO gpr_history (country_code, report_date, gpr_index, data_source, created_at)
SELECT
    f.country_code,
    f.report_date,
    f.gpr_index,
    COALESCE(ds.source_name, 'Caldara-Iacoviello'),
    f.created_at
FROM fact_gpr f
LEFT JOIN dim_data_source ds ON f.source_id = ds.id
ON CONFLICT (country_code, report_date) DO NOTHING;

-- ============================================================
-- Step 3: quotes (fact_quote + dim_asset → quotes)
-- ============================================================
INSERT INTO quotes (code, name, asset_type, price, change_amount, change_percent, high_price, low_price, open_price, prev_close, volume, quote_time, data_source, created_at)
SELECT
    a.asset_code,
    a.asset_name,
    a.asset_type,
    f.price,
    f.change_amount,
    f.change_percent,
    f.high_price,
    f.low_price,
    f.open_price,
    f.prev_close,
    f.volume,
    f.quote_time,
    COALESCE(ds.source_name, 'Akshare'),
    f.created_at
FROM fact_quote f
JOIN dim_asset a ON f.asset_id = a.id
LEFT JOIN dim_data_source ds ON f.source_id = ds.id
ON CONFLICT (code, DATE(quote_time)) DO NOTHING;

-- ============================================================
-- Step 4: fx_rates (fact_fx_rate + dim_currency → fx_rates)
-- ============================================================
INSERT INTO fx_rates (base_currency, quote_currency, rate, rate_time, data_source, created_at)
SELECT
    bc.currency_code,
    qc.currency_code,
    f.rate,
    f.rate_time,
    COALESCE(ds.source_name, 'Frankfurter'),
    f.created_at
FROM fact_fx_rate f
JOIN dim_currency bc ON f.base_currency_id = bc.id
JOIN dim_currency qc ON f.quote_currency_id = qc.id
LEFT JOIN dim_data_source ds ON f.source_id = ds.id
ON CONFLICT (base_currency, quote_currency, DATE(rate_time)) DO NOTHING;

-- ============================================================
-- Step 5: gold_supply_demand (fact_gold_supply_demand + dim_period → gold_supply_demand)
-- ============================================================
INSERT INTO gold_supply_demand (year, quarter, mine_production, recycling, net_hedging, total_supply, jewelry, technology, total_investment, bars_coins, etfs, otc_investment, central_banks, total_demand, supply_demand_balance, price_avg_usd, data_source, created_at, updated_at)
SELECT
    p.year,
    p.quarter,
    f.mine_production,
    f.recycling,
    f.net_hedging,
    f.total_supply,
    f.jewelry,
    f.technology,
    f.total_investment,
    f.bars_coins,
    f.etfs,
    f.otc_investment,
    f.central_banks,
    f.total_demand,
    f.supply_demand_balance,
    f.price_avg_usd,
    COALESCE(ds.source_name, 'WGC'),
    f.created_at,
    f.updated_at
FROM fact_gold_supply_demand f
JOIN dim_period p ON f.period_id = p.id
LEFT JOIN dim_data_source ds ON f.source_id = ds.id
ON CONFLICT (year, quarter) DO NOTHING;

-- ============================================================
-- Step 6: 重命名 fund 相关表
-- ============================================================
ALTER TABLE dim_fund RENAME TO funds;
ALTER TABLE fact_fund_scale RENAME TO fund_scales;
```

---

## 四、Store 层改动

### 4.1 GoldReserveStore → 简化

**删除方法:**
- `_get_or_create_country()`
- `_get_or_create_source()`

**save() 改动:**
```python
# 之前: get_or_create_country → get_or_create_source → INSERT with FK IDs
# 之后: 直接 INSERT
@classmethod
async def save(cls, data: GoldReserve) -> bool:
    await Database.execute("""
        INSERT INTO gold_reserves (country_code, country_name, gold_tonnes, report_date, data_source, fetched_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (country_code, report_date) DO UPDATE SET
            gold_tonnes = EXCLUDED.gold_tonnes,
            fetched_at = EXCLUDED.fetched_at,
            updated_at = CURRENT_TIMESTAMP
    """, data.country_code, data.country_name, data.amount_tonnes,
         data.report_date or date.today(), data.data_source or "IMF", datetime.now())
```

**save_batch() 改动 — 消除 N+1:**
```python
@classmethod
async def save_batch(cls, data_list: list[GoldReserve]) -> int:
    args_list = [
        (d.country_code, d.country_name, d.amount_tonnes,
         d.report_date or date.today(), d.data_source or "IMF", datetime.now())
        for d in data_list
    ]
    await Database.execute_many("""
        INSERT INTO gold_reserves (country_code, country_name, gold_tonnes, report_date, data_source, fetched_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (country_code, report_date) DO UPDATE SET
            gold_tonnes = EXCLUDED.gold_tonnes, fetched_at = EXCLUDED.fetched_at, updated_at = CURRENT_TIMESTAMP
    """, args_list)
    return len(args_list)
```

**所有读查询 — 去掉 JOIN:**
```python
# 之前:
#   SELECT f.id, c.country_code, c.country_name, f.gold_tonnes, ...
#   FROM fact_gold_reserve f JOIN dim_country c ON ... JOIN dim_data_source ds ON ...
# 之后:
#   SELECT id, country_code, country_name, gold_tonnes, report_date, data_source, fetched_at
#   FROM gold_reserves WHERE ... ORDER BY report_date DESC
```

**get_latest_with_stats() — 核心查询简化:**
CTE 结构不变，只是去掉 JOIN，直接用 gold_reserves 表:
```sql
WITH latest AS (
    SELECT DISTINCT ON (country_code)
        country_code, country_name, gold_tonnes, report_date, data_source
    FROM gold_reserves
    ORDER BY country_code, report_date DESC
),
yoy AS (
    SELECT l.*,
        l.gold_tonnes - h_yoy.gold_tonnes as yoy_change
    FROM latest l
    LEFT JOIN LATERAL (
        SELECT gold_tonnes FROM gold_reserves
        WHERE country_code = l.country_code AND report_date <= l.report_date - INTERVAL '1 year'
        ORDER BY report_date DESC LIMIT 1
    ) h_yoy ON true
),
...  -- rest unchanged, just gold_reserves instead of fact_gold_reserve + JOINs
```

### 4.2 GPRHistoryStore → 简化

**删除方法:**
- `_get_or_create_source()`

**save_batch() → 真正的批量写入:**
```python
@classmethod
async def save_batch(cls, records: list[GPRHistory]) -> int:
    args_list = [
        (r.country_code, r.report_date, r.gpr_index, r.data_source or 'Caldara-Iacoviello')
        for r in records
    ]
    await Database.execute_many("""
        INSERT INTO gpr_history (country_code, report_date, gpr_index, data_source)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (country_code, report_date) DO UPDATE SET
            gpr_index = EXCLUDED.gpr_index
    """, args_list)
    return len(args_list)
```

**读查询 → 去掉 JOIN dim_data_source:**
```python
# SELECT country_code, report_date, gpr_index, data_source, created_at
# FROM gpr_history WHERE country_code = $1 ORDER BY report_date DESC LIMIT $2
```

### 4.3 QuoteFactStore → QuoteStore (重命名)

**删除方法:**
- `_get_or_create_asset_id()`
- `_get_source_id()`

**save() → 简单 INSERT:**
```python
@classmethod
async def save(cls, quote: Quote) -> bool:
    asset_type = "fund" if quote.type and hasattr(quote.type, "value") and quote.type.value == "fund" else "stock"
    await Database.execute("""
        INSERT INTO quotes (code, name, asset_type, price, change_percent, high_price, low_price, volume, quote_time, data_source)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (code, DATE(quote_time)) DO UPDATE SET
            price = EXCLUDED.price, change_percent = EXCLUDED.change_percent,
            high_price = EXCLUDED.high_price, low_price = EXCLUDED.low_price, volume = EXCLUDED.volume
    """, quote.code, quote.name, asset_type, quote.price, quote.change_percent,
         quote.high, quote.low, int(quote.volume) if quote.volume and quote.volume.isdigit() else None,
         quote.update_time or datetime.now(), "Akshare")
```

**save_many() → execute_many:**
去掉 asset_cache 和逐条处理，直接 execute_many。

**读查询 → 去掉 JOIN dim_asset:**
```python
# SELECT code, name, price, change_percent, high_price, low_price, volume, quote_time
# FROM quotes WHERE code = $1 ORDER BY quote_time DESC LIMIT $2
```

### 4.4 ExchangeRateFactStore → ExchangeRateStore (重命名)

**删除方法:**
- `_get_or_create_currency_id()`
- `_get_source_id()`

**save() → 简单 INSERT:**
```python
@classmethod
async def save(cls, rate: ExchangeRate) -> bool:
    await Database.execute("""
        INSERT INTO fx_rates (base_currency, quote_currency, rate, rate_time, data_source)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (base_currency, quote_currency, DATE(rate_time)) DO UPDATE SET
            rate = EXCLUDED.rate
    """, rate.base_currency, rate.quote_currency, rate.rate,
         rate.update_time or datetime.now(), rate.source or "Frankfurter")
```

**读查询 → 去掉 JOIN dim_currency:**
```python
# SELECT base_currency, quote_currency, rate, rate_time, data_source
# FROM fx_rates WHERE base_currency = $1 AND quote_currency = $2 ORDER BY rate_time DESC LIMIT 1
```

### 4.5 GoldSupplyDemandStore → 简化

**删除方法:**
- `_get_or_create_period()`
- `_get_or_create_source()`

**save_quarterly() → 直接 INSERT:**
```python
@classmethod
async def save_quarterly(cls, data: GoldSupplyDemand) -> bool:
    await Database.execute("""
        INSERT INTO gold_supply_demand (year, quarter, mine_production, ..., data_source)
        VALUES ($1, $2, $3, ...)
        ON CONFLICT (year, quarter) DO UPDATE SET ...
    """, data.year, data.quarter, data.mine_production, ...)
```

**读查询 → 去掉 JOIN dim_period + dim_data_source:**
```sql
-- 之前: SELECT f.*, p.year, p.quarter, ds.source_name FROM fact_... f JOIN dim_period p JOIN dim_data_source ds
-- 之后: SELECT * FROM gold_supply_demand ORDER BY year DESC, quarter DESC
```

### 4.6 FundStore → 表名更新

只改 SQL 中的表名: `dim_fund` → `funds`, `fact_fund_scale` → `fund_scales`

---

## 五、Service 层改动

| Service | 改动 | 说明 |
|---------|------|------|
| `gold_reserve_service.py` | 无 | 通过 Store 层间接使用，Store 接口不变 |
| `gpr_service.py` | 无 | Store 接口不变 |
| `quote_service.py` | import 改名 | `QuoteFactStore` → `QuoteStore` |
| `forex_service.py` | import 改名 | `ExchangeRateFactStore` → `ExchangeRateStore` |
| `gold_supply_demand_service.py` | 无 | Store 接口不变 |
| `watchlist_service.py` | 无 | 不涉及 |
| `fund_service.py` | 无 | Store 内部已改表名 |

---

## 六、文件改动清单

| 操作 | 文件 |
|------|------|
| **重写** | `fcli/core/stores/gold.py` — 去掉 JOIN, get_or_create, 改用 gold_reserves |
| **重写** | `fcli/core/stores/gpr.py` — 去掉 JOIN, get_or_create, 改用 gpr_history |
| **重写** | `fcli/core/stores/quote_fact.py` → 重命名为 `quote.py` — 去掉 JOIN, get_or_create, 改用 quotes |
| **重写** | `fcli/core/stores/exchange_rate_fact.py` → 重命名为 `exchange_rate.py` — 去掉 JOIN, get_or_create, 改用 fx_rates |
| **重写** | `fcli/core/stores/gold_supply_demand.py` — 去掉 JOIN, get_or_create, 改用 gold_supply_demand |
| **更新** | `fcli/core/stores/fund.py` — 表名 dim_fund→funds, fact_fund_scale→fund_scales |
| **更新** | `fcli/core/stores/__init__.py` — import 改名 |
| **更新** | `fcli/services/quote_service.py` — import QuoteFactStore→QuoteStore |
| **更新** | `fcli/services/forex_service.py` — import ExchangeRateFactStore→ExchangeRateStore |
| **新建** | `fcli/scripts/migrate_v3.py` — V3 迁移脚本 |
| **删除** | `fcli/scripts/migrate_v2.py` — 不再需要 |
| **更新** | `AGENTS.md` — 更新文档 |
| **更新** | `README.md` — 更新表结构说明 |

---

## 七、执行顺序

```
Phase 1: 创建新表 + 数据迁移 (migrate_v3.py)
  1.1 创建 5 个新平面表 (gold_reserves, gpr_history, quotes, fx_rates, gold_supply_demand)
  1.2 从 V2 星型表迁移数据到平面表 (INSERT...SELECT...FROM fact_* JOIN dim_*)
  1.3 重命名 dim_fund → funds, fact_fund_scale → fund_scales
  1.4 验证行数一致

Phase 2: Store 层重写 (7 个文件)
  2.1 GoldReserveStore
  2.2 GPRHistoryStore
  2.3 QuoteStore (原 QuoteFactStore)
  2.4 ExchangeRateStore (原 ExchangeRateFactStore)
  2.5 GoldSupplyDemandStore
  2.6 FundStore
  2.7 __init__.py

Phase 3: Service 层更新 (2 个文件)
  3.1 quote_service.py — import 改名
  3.2 forex_service.py — import 改名

Phase 4: 清理
  4.1 删除旧 V2 表 (DROP TABLE fact_*, dim_*)
  4.2 删除旧兼容视图 (DROP VIEW IF EXISTS gold_reserves_view, gpr_history_view)
  4.3 删除 migrate_v2.py
  4.4 更新 AGENTS.md, README.md

Phase 5: 验证
  5.1 python run.py gold
  5.2 python run.py gold supply
  5.3 python run.py gpr
  5.4 python run.py gpr history -m 60
  5.5 python run.py fx USD CNY
  5.6 python run.py watchlist
  5.7 python run.py watchlist ls
```

---

## 八、风险与回滚

**风险:**
- 数据迁移不完整 → Phase 1.4 验证行数确保完整
- Store 重写引入 bug → 逐个 Store 改写，每个改完即测

**回滚方案:**
- 迁移脚本在 DROP 旧表前创建 `_v2_backup` 备份
- V2 星型表在 Phase 4 才删除，Phase 1-3 期间两套表共存
- 如需回滚，切回旧 Store 代码 + 恢复旧表

---

## 九、代码量估算

| 改动 | 预计行数变化 |
|------|-------------|
| GoldReserveStore | -120 行 (去掉 JOIN, get_or_create) |
| GPRHistoryStore | -60 行 |
| QuoteStore | -80 行 |
| ExchangeRateStore | -60 行 |
| GoldSupplyDemandStore | -40 行 |
| FundStore | -5 行 (只改表名) |
| migrate_v3.py | +100 行 (新迁移脚本) |
| **净减** | **~265 行** |
