﻿# FCLI 系统设计问题修复计划

基于全量代码审查（40+ 文件）发现的 27 个设计问题，按优先级分 4 阶段修复。

---

## 阶段一：P0 BUG 修复（立即执行）

### BUG-1: fund_service.py 查询已不存在的 V2 表

- **文件**: `fcli/services/fund_service.py:28`
- **现象**: V3 迁移已将 `dim_fund` 重命名为 `funds`，但此处仍查询旧表名
- **影响**: `needs_monthly_update()` 每次抛异常 → 每次都触发全量更新
- **修复**:

```python
# 修改前
"SELECT MAX(updated_at) as last_update FROM dim_fund"
# 修改后
"SELECT MAX(updated_at) as last_update FROM funds"
```

### BUG-2: cache_strategy.py 黄金缓存条件错误

- **文件**: `fcli/core/cache_strategy.py:144`
- **现象**: 用 `AssetType.STOCK and Market.GLOBAL` 匹配黄金数据，但黄金既不是 STOCK 也不是 GLOBAL market
- **影响**: 黄金数据永远无法命中 `_gold_ttl`（86400秒），走了默认 300 秒缓存
- **修复**: 需配合 `AssetType` 枚举新增 `GOLD` 值（见 P1-1），修复后条件改为：

```python
# 修改前
if asset_type == AssetType.STOCK and market == Market.GLOBAL:
    return self._gold_ttl
# 修改后
if asset_type == AssetType.GOLD:
    return self._gold_ttl
```

- **前置依赖**: P1-1（AssetType 新增 GOLD）

### BUG-3: market.py Database.init() 缺少 config 参数

- **文件**: `fcli/commands/market.py:106, 116, 151`
- **现象**: 三个 async 函数中 `await Database.init()` 未传 config，而 `Database.init()` 签名需要 config 参数
- **影响**: 基金搜索、详情、更新功能无法正常初始化数据库连接
- **修复**:

```python
# 修改前
await Database.init()
# 修改后
from ..core.config import config
await Database.init(config)
```

三个位置均需修改：`_search_funds()`、`_get_fund_detail()`、`_update_fund_data()`

### BUG-4: logger.py \_log() 方法重复执行

- **文件**: `fcli/utils/logger.py:83-88`
- **现象**: `_log()` 方法体被复制粘贴，每条日志实际输出两次
- **影响**: ERROR 及以上级别日志重复输出；结合 `if level < logging.ERROR: return` 逻辑，info/warning/debug 均被静默吞掉
- **修复**:

```python
# 修改前（第 83-88 行）
def _log(self, level: int, message: str, context: LogContext | None = None, **kwargs):
    """内部日志方法 - 只输出 ERROR 及以上级别"""
    if level < logging.ERROR:
        return
    extra = {"context": context} if context else {}
    self.logger.log(level, message, extra=extra, **kwargs)
    """内部日志方法"""        # ← 重复
    extra = {"context": context} if context else {}
    self.logger.log(level, message, extra=extra, **kwargs)  # ← 重复

# 修改后
def _log(self, level: int, message: str, context: LogContext | None = None, **kwargs):
    if level < logging.ERROR:
        return
    extra = {"context": context} if context else {}
    self.logger.log(level, message, extra=extra, **kwargs)
```

- **额外建议**: 当前逻辑静默吞掉 INFO/WARNING 级别日志，应考虑将过滤级别改为可配置，而非硬编码 ERROR

---

## 阶段二：P1 架构问题修复

### P1-1: AssetType 缺少 GOLD 枚举值

- **文件**: `fcli/core/models/base.py`
- **现象**: `AssetType` 枚举只有 STOCK/FUND/INDEX/FOREX/BOND，黄金数据无法被正确分类
- **影响**: 黄金数据在缓存策略、资产识别等处被迫用 `AssetType.STOCK + Market.GLOBAL` 硬编码匹配
- **修复**:

```python
class AssetType(str, Enum):
    STOCK = "STOCK"
    FUND = "FUND"
    INDEX = "INDEX"
    FOREX = "FOREX"
    BOND = "BOND"
    GOLD = "GOLD"      # 新增
```

- **联动修改**:
  - `cache_strategy.py` 的 `DEFAULT_TTLS` 字典增加 `AssetType.GOLD` 条目
  - `cache_strategy.py:144` 条件改为 `if asset_type == AssetType.GOLD`
  - `factories.py` 的 `AssetFactory.from_code()` 需识别黄金代码
  - `presenter.py` 的 `_TYPE_MAP` / `_TYPE_COLOR` 增加 GOLD 映射
  - `config.py` 的 `SymbolRegistry.infer_type()` 增加黄金识别逻辑

### P1-2: Market 枚举混入资产类型语义

- **文件**: `fcli/core/models/base.py`
- **现象**: `Market` 枚举混合了地理市场（CN/HK/US）和资产类型（FUND/FOREX/BOND/GLOBAL），语义不清晰
- **影响**: 条件判断复杂化（如 `cache_strategy.py` 需同时判断 asset_type + market），`is_trading_hours()` 对非地理 market 无意义
- **修复方案**:

```python
class Market(str, Enum):
    CN = "CN"
    HK = "HK"
    US = "US"
    GLOBAL = "GLOBAL"    # 保留，表示全球市场（如国际金价）

# 以下值应从 Market 移除，由 AssetType 承载：
# FUND → 已在 AssetType 中
# FOREX → 已在 AssetType 中
# BOND → 已在 AssetType 中
```

- **联动修改**:
  - 所有使用 `Market.FUND`/`Market.FOREX`/`Market.BOND` 的地方改为检查 `AssetType`
  - `is_trading_hours()` 只接受地理 Market（CN/HK/US/GLOBAL）
  - `time_util.py` 去掉对非地理 Market 的无效分支
  - `cache_strategy.py` 的 market 参数类型改为仅地理市场
  - Store 层和 Service 层中引用这些 Market 值的位置全部更新
- **影响范围**: 涉及 models/base.py, factories.py, cache_strategy.py, time_util.py, presenter.py, quote_service.py, 各 command 文件等

### P1-3: DI Container 仅 QuoteService 使用，其余服务绕过

- **文件**: `fcli/core/container.py`
- **现象**: `quote_service` 获得完整 DI 注入（cache/config/http_client/sources），而 `gold_reserve_service` 等其余服务直接 `ServiceClass()` 无参构造
- **影响**: Container 形同虚设，大部分服务内部自行获取依赖（模块级单例），无法统一替换依赖进行测试
- **修复方案**:
  - 方案 A（推荐）：统一所有 Service 构造函数签名，接受 cache/config/http_client 等依赖参数
  - 方案 B：弱化 Container 为纯工厂，仅提供便捷创建方法，不强制 DI

  方案 A 的具体步骤：
  1. 为每个 Service 添加 `__init__(self, cache=None, config=None, http_client=None)` 参数
  2. Service 内部不再 import 模块级单例，改为使用注入的实例
  3. Container 中所有 property 统一注入依赖
  4. Command 层从 `container.xxx_service` 获取服务实例

### P1-4: Scraper 三派不统一

- **现象**: 9 个 Scraper 分为三派：
  | 派系 | 基类 | 数据类 | 代表 |
  |------|------|--------|------|
  | 派系 1 | `BaseScraper` | `ScraperResult` | wgc_scraper, imf_scraper, gpr_scraper |
  | 派系 2 | `QuoteSourceABC` | 各自定义 | sina_quote_source, fund_quote_source |
  | 派系 3 | 无基类 | `ScrapeResult` | fund_scraper, akshare_scraper, safe_scraper |
- **影响**: 结果类型不统一（`ScraperResult` vs `ScrapeResult`），无法用统一接口处理；派系 3 的 Scraper 完全游离于类型体系外
- **修复方案**:
  1. 定义统一的 `ScraperResult` 数据类（泛型，支持不同返回数据类型）
  2. 定义统一的 `BaseScraper` ABC（fetch + parse + scrape 三方法模式）
  3. 派系 2 的 `QuoteSourceABC` 和 `IDataSource` Protocol 保留为 Quote 领域专用接口，但内部 scrape 返回统一 result
  4. 派系 3 的 `FundScraper`、`AKShareScraper`、`SafeScraper` 继承 `BaseScraper`

### P1-5: 双接口系统（Protocol + ABC）过度设计

- **文件**: `fcli/core/interfaces/`
- **现象**: 每个组件同时定义 Protocol（结构化子类型）和 ABC（名义子类型）两套接口，但实际使用中没有任何地方利用 Protocol 的鸭子类型优势
- **影响**: 维护成本翻倍，新增接口需要同步维护两套定义
- **修复方案**:
  - 保留 ABC 作为唯一接口定义方式（项目中已有继承 ABC 的习惯）
  - 删除所有 Protocol 接口：`IDataSource`, `IQuoteSource`, `IGoldSource`, `IForexSource`, `IGprSource`, `IHttpClient`, `ICache`, `IStorage`, `ICacheStrategy`
  - 更新 `interfaces/__init__.py` 的导出列表

---

## 阶段三：P2 设计一致性问题修复

### P2-1: 三种单例模式共存

- **现象**:
  | 模式 | 使用者 | 实现方式 |
  |------|--------|----------|
  | `__new__` + weakref | HttpClient | 类内 `__new__` 方法 |
  | 模块级实例 | services, cache, config | `xxx = XxxClass()` |
  | 类方法 + 无实例 | Database, Store | `@classmethod` |
- **影响**: 新开发者不确定应遵循哪种模式；HttpClient 的 `__new__` 单例在测试中难以替换
- **修复方案**:
  - Service 单例：统一由 Container 管理（配合 P1-3），移除模块级实例
  - HttpClient：移除 `__new__` 单例逻辑，由 Container 管理生命周期
  - Database/Store：保持类方法模式（适合无状态的数据访问层，无需改动）
  - Cache/Config：保持模块级实例（轻量配置对象，改动收益不大）

### P2-2: WatchlistAssetDB 使用 str 而非枚举

- **文件**: `fcli/core/models/log.py:15-16`
- **现象**: `market: str` 和 `type: str` 应使用 `Market` 和 `AssetType` 枚举
- **影响**: 失去类型安全，调用方可能传入任意字符串
- **修复**:

```python
from .base import AssetType, Market

class WatchlistAssetDB(BaseModel):
    market: Market = Market.CN
    type: AssetType = AssetType.STOCK
```

### P2-3: Command 层 DB init/close 样板代码重复

- **现象**: 每个 command 的 async 函数都有相同的 `try: await Database.init(config) ... finally: await Database.close()` 样板
- **修复方案**: 使用装饰器或上下文管理器封装

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def db_session():
    await Database.init(config)
    try:
        yield
    finally:
        await Database.close()

# 使用
async def _reserves(update: bool) -> None:
    async with db_session():
        reserves = await gold_reserve_service.fetch_all_with_auto_update(force=update)
```

- **涉及文件**: `commands/gold.py`, `commands/market.py`, `commands/fx.py`, `commands/gpr.py`, `commands/watchlist.py`

### P2-4: presenter.py 模块级加载 config

- **文件**: `fcli/utils/presenter.py:8-10`
- **现象**: 模块顶层直接 `from ..core.config import config` 并读取 `config.display.xxx` 构建映射表
- **影响**: 如果 config 尚未初始化（如测试环境），导入 presenter 就会失败或使用空值
- **修复方案**: 将 `_MARKET_MAP`/`_TYPE_MAP`/`_TYPE_COLOR` 改为延迟加载

```python
_MARKET_MAP: dict[str, str] | None = None

def _get_market_map() -> dict[str, str]:
    global _MARKET_MAP
    if _MARKET_MAP is None:
        _MARKET_MAP = config.display.market_map or {}
    return _MARKET_MAP
```

### P2-5: time_util.get_cache_ttl 与 AssetTypeCacheStrategy.get_ttl 功能重叠

- **文件**: `fcli/utils/time_util.py`, `fcli/core/cache_strategy.py`
- **现象**: 两个地方都实现了缓存 TTL 计算逻辑
- **修复方案**: 保留 `AssetTypeCacheStrategy` 作为唯一 TTL 计算入口，删除 `time_util.get_cache_ttl()`（如果存在），或将 time_util 中的 TTL 逻辑委托给 cache_strategy

### P2-6: presenter.py 供需数据表格代码重复

- **现象**: `print_gold_report()` 和 `print_gold_supply_balance()` 中有重复的供需数据表格渲染代码
- **修复方案**: 提取 `_render_supply_balance_table()` 内部方法

### P2-7: exchange_rate.py 向后兼容别名

- **文件**: `fcli/core/stores/exchange_rate.py`（文件末尾）
- **现象**: `ExchangeRateFactStore = ExchangeRateStore` 别名仍存在
- **修复**: 确认无外部引用后删除别名，全局搜索替换所有 `ExchangeRateFactStore` → `ExchangeRateStore`

### P2-8: market.py 手动组装 FundDetail

- **文件**: `fcli/commands/market.py:119-139`
- **现象**: 逐字段手动从 `Fund` + `scale_history` 组装 `FundDetail`，字段多达 17 个
- **修复方案**: 在 `FundDetail` 模型上增加 `from_fund()` 类方法，或在 `FundStore` 中直接返回 `FundDetail`

```python
@classmethod
def from_fund(cls, fund: Fund, scale_history: list | None = None) -> "FundDetail":
    return cls(**fund.model_dump(), scale_history=scale_history or [])
```

---

## 阶段四：P3 代码质量提升

### P3-1: fund_scraper.py ScrapeResult 与 base.py ScraperResult 重复定义

- **文件**: `fcli/services/scrapers/fund_scraper.py:17`, `fcli/services/scrapers/base.py:14`
- **现象**: 两个文件各定义了一个结果数据类，字段不同但语义相同
- **修复**: 统一使用 `base.py` 中的 `ScraperResult`（配合 P1-4 的统一结果类型）

### P3-2: fund_scraper.py / akshare_scraper.py 无基类

- **现象**: 这两个 Scraper 不继承任何基类，完全独立实现
- **修复**: 配合 P1-4，让它们继承统一的 `BaseScraper`

### P3-3: logger.py 静默吞掉 INFO/WARNING 级别日志

- **文件**: `fcli/utils/logger.py:84`
- **现象**: `if level < logging.ERROR: return` 导致所有非 ERROR/CRITICAL 日志被丢弃
- **修复**: 将过滤级别改为可配置参数，默认设为 INFO

```python
def __init__(self, name: str, level: int = logging.INFO):
```

### P3-4: StructuredLogger.info/warning/debug 实际无效

- **文件**: `fcli/utils/logger.py:99-106`
- **现象**: `info()`, `warning()`, `debug()` 方法调用 `_log()` 但被 `level < ERROR` 过滤掉
- **修复**: 配合 P3-3，修复后这些方法自然生效

---

## 修复顺序与依赖关系

```
阶段一（P0 BUG）── 无依赖，立即执行
  ├── BUG-1: fund_service 表名修复
  ├── BUG-3: market.py Database.init() 参数修复
  ├── BUG-4: logger.py 重复代码修复
  └── BUG-2: cache_strategy 条件修复（依赖 P1-1）

阶段二（P1 架构）── 部分依赖 P0
  ├── P1-1: AssetType 新增 GOLD     ← 解除 BUG-2 阻塞
  ├── P1-5: 删除 Protocol 接口       ← 独立
  ├── P1-2: Market 枚举重构          ← 依赖 P1-1
  ├── P1-4: Scraper 统一基类         ← 依赖 P1-5
  └── P1-3: Container DI 统一       ← 依赖 P1-2

阶段三（P2 设计）── 部分依赖 P1
  ├── P2-1: 单例模式统一            ← 依赖 P1-3
  ├── P2-3: DB init/close 装饰器    ← 独立
  ├── P2-4: presenter 延迟加载      ← 独立
  ├── P2-8: FundDetail 工厂方法     ← 独立
  ├── P2-2: WatchlistAssetDB 枚举化 ← 依赖 P1-1, P1-2
  ├── P2-5: TTL 逻辑统一           ← 依赖 P1-1
  ├── P2-6: presenter 表格代码去重  ← 独立
  └── P2-7: 删除兼容别名           ← 独立

阶段四（P3 质量）── 独立或依赖 P1
  ├── P3-1: ScraperResult 统一     ← 依赖 P1-4
  ├── P3-2: fund_scraper 加基类    ← 依赖 P1-4
  ├── P3-3: logger 级别可配置      ← 独立
  └── P3-4: info/warning/debug 生效 ← 依赖 P3-3
```

## 影响范围汇总

| 修复项      | 涉及文件数 | 风险等级                      |
| ----------- | ---------- | ----------------------------- |
| 阶段一 (P0) | 4          | 低 — 改动小且明确             |
| P1-1 + P1-2 | 10+        | 中 — 枚举变更影响面广         |
| P1-3        | 8          | 中 — Service 构造函数签名变更 |
| P1-4 + P1-5 | 12+        | 中高 — Scraper 体系重构       |
| 阶段三 (P2) | 8          | 低 — 设计改进，逻辑不变       |
| 阶段四 (P3) | 4          | 低 — 代码质量改进             |

## 验证方式

每个阶段完成后执行：

```bash
# 类型检查
mypy fcli/

# 运行测试
pytest tests/

# 手动冒烟测试
python run.py gold -h
python run.py market search 沪深300
python run.py fx USD CNY
python run.py gpr -h
python run.py watchlist ls
```
