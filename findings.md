# FCLI 审计发现

## 分类标准

- **S-风格**: 代码风格不一致（命名、格式、import、类型注解）
- **D-设计**: 设计缺陷或模式不一致
- **B-BUG**: 潜在运行时错误
- **R-风险**: 静默失败、资源泄漏等风险

---

## B-01: save_gold_reserves.py verify_data() 查询已不存在的 V2 表

**文件**: `fcli/scripts/save_gold_reserves.py:206-238`

`verify_data()` 仍使用 V2 star schema 表名 (`fact_gold_reserve`, `dim_country`)，V3 迁移后这些表已不存在。脚本在 `main()` 中调用 `await verify_data()`，每次保存数据后会触发运行时错误。

```python
# 当前代码（错误）
rows = await conn.fetch("""
    SELECT c.country_code, c.country_name, ...
    FROM fact_gold_reserve f
    JOIN dim_country c ON f.country_id = c.id
    ...
""")

# 应改为 V3 flat table 查询
rows = await conn.fetch("""
    SELECT country_code, country_name, ...
    FROM gold_reserves
    ...
""")
```

**严重度**: P1 — 脚本每次执行都会报错

---

## B-02: QuoteStore.\_quote_to_args 脆弱的类型判断

**文件**: `fcli/core/stores/quote.py:31-32`

使用 `hasattr` + 字符串比较判断 AssetType，而非直接用枚举比较。如果 Quote.type 的类型或枚举值变化，此处会静默降级为 "stock"。

```python
# 当前代码（脆弱）
asset_type = "fund" if quote.type and hasattr(quote.type, "value") and quote.type.value == "fund" else "stock"

# 应改为
asset_type = "fund" if quote.type == AssetType.FUND else "stock"
```

**严重度**: P2 — 如果 type 为 None 或非枚举类型会静默错误

---

## B-03: \_fetch_yahoo() 空实现永远返回 None

**文件**: `fcli/services/quote_service.py` (`_fetch_yahoo` 方法)

`_fetch_yahoo()` 是空方法，只返回 `None`，但 `fetch_single()` 会根据配置尝试调用它。如果用户配置了 yahoo 作为数据源，会静默跳过无任何日志提示。

```python
async def _fetch_yahoo(self, asset: Asset) -> Quote | None:
    return None  # 空实现，无日志、无 NotImplementedError
```

**严重度**: P2 — 用户配置 yahoo 源时无法知道该功能未实现

---

## D-01: DI Container 仅部分服务使用，大量模块直接导入全局单例

**涉及文件**: 多处

Container 设计了完整的 DI 模式（懒加载单例、可替换依赖），但项目中 DI 使用不一致：

| 组件               | DI 使用                         | 实际导入方式                                  |
| ------------------ | ------------------------------- | --------------------------------------------- |
| QuoteService       | ✅ 通过 Container 创建          | Container 注入                                |
| ForexService       | ⚠️ Container 创建但导入具体类型 | `from ..core.cache import HybridCache, cache` |
| GoldReserveService | ⚠️ 接受可选 config              | `config or _default_config`                   |
| GPRService         | ⚠️ 接受可选 config              | `config or _default_config`                   |
| FundService        | ❌ 不通过 Container 传 config   | 只接收 scraper                                |
| WatchlistService   | ⚠️ 接受可选 storage             | `storage or default_storage`                  |
| Commands           | ❌ 直接导入 `config`            | `from ..core.config import config`            |
| Stores             | ❌ 不参与 DI                    | 使用 `@classmethod`                           |

Commands 层全部直接 `from ..core.config import config`，绕过 Container：

```python
# fcli/commands/watchlist.py, gold.py, gpr.py, fx.py, market.py
from ..core.config import config
async with Database.session(config):  # 直接使用全局 config
```

**严重度**: P2 — 架构意图与实际不一致，降低可测试性

---

## D-02: QuoteService 内嵌大量数据源解析逻辑，策略模式未完全生效

**文件**: `fcli/services/quote_service.py` (399 行)

QuoteService 通过构造函数接收 `sources: list[QuoteSourceABC]` 实现策略模式，但 `fetch_single()` 仍使用硬编码的 if/elif 分发：

```python
for source in self._config.datasource.quote_priority:
    if source == "sina":
        quote = await self._fetch_sina(asset)      # 内部方法
    elif source == "eastmoney":
        quote = await self._fetch_eastmoney(asset)  # 内部方法
    elif source == "yahoo":
        quote = await self._fetch_yahoo(asset)      # 内部方法
```

同时 `_fetch_sina()` 内部又按 market 做 if/elif 分发（CN/HK/US/GLOBAL），且 `_fetch_fund_1234567()` + `_parse_fund_response()` 与 `FundQuoteSource` 功能完全重复。

已注入的 `self._sources` 和 `self._fund_source` 仅在 `fetch_all()` 中使用，`fetch_single()` 完全忽略它们。

**严重度**: P2 — 策略模式只实现一半，新增数据源需修改 Service

---

## D-03: ForexService 导入具体类型而非抽象接口

**文件**: `fcli/services/forex_service.py:10`

```python
from ..core.cache import HybridCache, cache  # 具体类
```

对比 QuoteService 的正确做法：

```python
from ..core.interfaces.cache import CacheABC  # 抽象接口
```

ForexService 构造函数类型标注也使用 `HybridCache`：

```python
def __init__(self, cache_backend: HybridCache | None = None, ...):
```

**严重度**: P2 — 违反依赖倒置原则，无法替换缓存实现

---

## D-04: GPRService 混合使用 JSON 文件和数据库双存储

**文件**: `fcli/services/gpr_service.py`

GPRService 同时维护：

- `self.storage_file = self._config.data_dir / "gpr_history.json"` — JSON 文件
- `GPRHistoryStore` — PostgreSQL 数据库

`load_data()` 读 JSON 文件，`update_data()` 写 JSON 并入库。其他 Service（GoldReserve, Forex, Quote）已统一为 DB-first + API fallback，GPRService 是唯一残留文件存储的服务。

**严重度**: P2 — 存储策略不一致

---

## D-05: ConsolePresenter God Class（502 行，~20 静态方法）

**文件**: `fcli/utils/presenter.py`

所有展示逻辑集中在一个类中，包含：

- 行情表格、自选股表格、搜索结果表格
- GPR 报告、黄金储备报告、供需平衡表
- 汇率表格、基金详情
- Plotext 图表
- 通用辅助方法（状态、成功、警告、错误）

应按领域拆分，例如：

- `QuotePresenter` — 行情相关
- `GoldPresenter` — 黄金/GPR 相关
- `FundPresenter` — 基金相关
- `BasePresenter` — 通用方法

**严重度**: P3 — 可维护性问题

---

## D-06: Store 全部使用 @classmethod，不参与 DI

**涉及文件**: `fcli/core/stores/` 下所有 Store

所有 Store 类（QuoteStore, GoldReserveStore, GPRHistoryStore, ExchangeRateStore, GoldSupplyDemandStore, FundStore, WatchlistAssetStore）都是纯 `@classmethod` 实现，直接调用 `Database.execute()` 等类方法。

这意味着：

1. Store 无法被 mock 替换（测试困难）
2. Store 无法持有状态（如不同的数据库连接）
3. 与 Container 的 DI 模式不一致

**严重度**: P3 — 当前 CLI 工具可接受，但限制扩展性

---

## D-07: ForexService.get_rate() 硬编码数据源 if/elif 分发

**文件**: `fcli/services/forex_service.py:62-73`

与 D-02 同样的模式：

```python
for source in self._config.datasource.forex_priority:
    if source == "frankfurter":
        rate = await self._fetch_frankfurter(base_currency, quote_currency)
    elif source == "exchangerate":
        rate = await self._fetch_exchangerate(base_currency, quote_currency)
```

应抽象为 `ForexSourceABC` 策略接口，与 `QuoteSourceABC` 模式统一。

**严重度**: P3 — 新增汇率源需修改 Service

---

## D-08: BaseScraper.\_cache 字典从未使用

**文件**: `fcli/services/scrapers/base.py:38`

```python
class BaseScraper(ABC, Generic[T]):
    def __init__(self):
        self._last_fetch_time: datetime | None = None
        self._cache: dict[str, Any] = {}  # 初始化但从未读写
```

所有子类均未使用 `self._cache`，也没有基类方法引用它。

**严重度**: P3 — 死代码

---

## D-09: QuoteService.\_fetch_eastmoney() 中的 secid_map 硬编码

**文件**: `fcli/services/quote_service.py`

`_fetch_eastmoney()` 方法内嵌了一个市场到 secid 前缀的映射表：

```python
secid_map = {
    Market.CN: f"1.{asset.api_code[2:]}" if ... else f"0.{...}",
    Market.HK: f"116.{...}",
    Market.US: f"105.{...}",
    Market.GLOBAL: f"106.{...}",
}
```

这个映射属于数据源（东方财富）的内部知识，不应硬编码在 Service 层。

**严重度**: P3 — 数据源细节泄漏到 Service 层

---

## D-10: Container.forex_service 注入 HybridCache 而非 CacheABC

**文件**: `fcli/core/container.py:133-138`

```python
@property
def forex_service(self) -> ForexService:
    if self._forex_service is None:
        from ..services.forex_service import ForexService
        self._forex_service = ForexService(
            cache=self.cache,       # self.cache 返回 CacheABC
            config=self._config,
            http_client=self.http_client,
        )
```

Container 传入的是 `CacheABC` 类型，但 ForexService 构造函数声明为 `HybridCache`，类型不匹配。目前能运行是因为运行时传入的确实是 HybridCache 实例，但静态类型检查会报错。

**严重度**: P3 — 类型标注不匹配

---

## S-01: Command 层 5 个文件重复相同模板代码

**涉及文件**: `fcli/commands/` 下所有 5 个文件

每个命令都重复完全相同的模式：

```python
from ..core.config import config
from ..core.container import container
from ..core.database import Database
from ..infra.http_client import run_async
from ..utils.presenter import ConsolePresenter

# 每个命令函数：
try:
    run_async(_func())
except Exception as e:
    ConsolePresenter.print_error(f"xxx失败: {e}")
    raise typer.Exit(1) from e

# 每个 async 函数：
async def _func():
    async with Database.session(config):
        with ConsolePresenter.status("..."):
            result = await container.xxx_service.method()
```

可以抽取为装饰器或基类：

```python
def async_command(status_msg: str, error_msg: str):
    def decorator(func):
        def wrapper():
            try:
                return run_async(_run_with_session(func, status_msg))
            except Exception as e:
                ConsolePresenter.print_error(f"{error_msg}: {e}")
                raise typer.Exit(1) from e
        return wrapper
    return decorator
```

**严重度**: P3 — 大量重复代码

---

## S-02: 日志使用方式不一致

**涉及文件**: 多处

项目中定义了 `StructuredLogger`（`fcli/utils/logger.py`），但使用方式不统一：

| 服务                    | 日志方式                                                |
| ----------------------- | ------------------------------------------------------- |
| QuoteService            | `from ..utils.logger import quote_logger as logger` ✅  |
| GoldReserveService      | `logging.getLogger(__name__)` ❌                        |
| GoldSupplyDemandService | `logging.getLogger(__name__)` ❌                        |
| FundService             | `logging.getLogger(__name__)` ❌                        |
| GPRService              | `logging.getLogger(__name__)` ❌                        |
| ForexService            | 无 logger（直接静默） ❌                                |
| SinaQuoteSource         | `from ...utils.logger import quote_logger as logger` ✅ |
| FundQuoteSource         | `from ...utils.logger import quote_logger as logger` ✅ |

应统一使用 StructuredLogger 或预定义的 logger 实例。

**严重度**: P3 — 风格不一致

---

## S-03: ForexService 中模块级工具函数应移至 utils

**文件**: `fcli/services/forex_service.py:13-36`

`COMMON_CURRENCIES` 字典、`get_currency_name()` 和 `format_currency_display()` 是纯工具函数，不依赖任何 Service 状态，放在 Service 文件中违反单一职责。

```python
# 当前：放在 forex_service.py（Service 层）
COMMON_CURRENCIES = { "USD": "美元", ... }
def get_currency_name(code: str) -> str: ...
def format_currency_display(code: str) -> str: ...

# 应移至：fcli/utils/currency.py 或 fcli/core/constants.py
```

presenter.py 中通过延迟导入使用它：

```python
def print_exchange_rate(rate: ExchangeRate):
    from ..services.forex_service import get_currency_name  # 跨层导入
```

**严重度**: P3 — 职责错放

---

## S-04: presenter.py 跨层导入 Service 层函数

**文件**: `fcli/utils/presenter.py`

```python
def print_exchange_rate(rate: ExchangeRate):
    from ..services.forex_service import get_currency_name
```

`utils/` 是底层模块，`services/` 是上层模块。utils 不应反向导入 services。结合 S-03，将 `get_currency_name` 移到 utils 后此问题自然解决。

**严重度**: P3 — 循环依赖风险

---

## S-05: presenter.py 使用模块级可变全局变量

**文件**: `fcli/utils/presenter.py:14`

```python
_display_cache: dict[str, dict[str, str]] | None = None

def _get_display_maps() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    global _display_cache
    if _display_cache is None:
        ...
    return ...
```

使用模块级 `global` 可变状态。虽然功能上没问题，但与项目其他地方的 DI 模式不一致。可以考虑将 `_display_cache` 封装为 ConsolePresenter 的类变量。

**严重度**: P3 — 风格不一致

---

## S-06: Service 构造函数可选参数默认值风格不一致

**涉及文件**: 多个 Service

| Service                 | 可选参数默认方式                                           |
| ----------------------- | ---------------------------------------------------------- |
| QuoteService            | 必填，无默认值 ✅                                          |
| ForexService            | `HybridCache \| None = None`，fallback 到全局 `cache`      |
| GoldReserveService      | `Settings \| None = None`，fallback 到全局 `config`        |
| GPRService              | `Settings \| None = None`，fallback 到 `_default_config`   |
| FundService             | `FundScraper \| None = None`，内部 `or FundScraper()`      |
| GoldSupplyDemandService | `WGCScraper \| None = None`，内部 `or WGCScraper()`        |
| WatchlistService        | `StorageABC \| None = None`，fallback 到 `default_storage` |

三种不同的 fallback 写法：

1. `param or global_singleton`（ForexService, GoldReserveService, GPRService）
2. `param or ConcreteClass()`（FundService, GoldSupplyDemandService）
3. 必填参数（QuoteService）✅

Container 统一传入所有依赖，这些 fallback 实际上只在非 DI 场景生效。应统一风格。

**严重度**: P3 — 风格不一致

---

## S-07: volume 字段类型为 str 而非 float

**文件**: `fcli/core/models/asset.py:44`

```python
class Quote(BaseModel):
    volume: str | None = None  # 字符串类型
```

QuoteStore 中的处理也反映了这个奇怪的设计：

```python
int(quote.volume) if quote.volume and quote.volume.isdigit() else None
```

成交量本质是数值，应使用 `float | None` 或 `int | None`。当前字符串设计导致 Store 层需要做 `isdigit()` 检查。

**严重度**: P3 — 类型语义不匹配

---

## R-01: run_async() 每次调用创建新事件循环并关闭 HTTP 客户端

**文件**: `fcli/infra/http_client.py`

```python
def run_async(coro: Coroutine[Any, Any, T]) -> T:
    async def _runner() -> T:
        try:
            return await coro
        finally:
            await http_client.close()  # 每次命令结束都关闭
    return asyncio.run(_runner())
```

问题：

1. `asyncio.run()` 每次创建新事件循环，无法复用
2. `finally` 中无条件关闭 `http_client`，即使后续还有请求
3. 如果同一个 CLI 调用中多次使用 `run_async()`（如某些 batch 场景），HTTP 连接会被反复创建/销毁

**严重度**: P2 — 资源浪费，潜在连接问题

---

## R-02: GoldSupplyDemandService 两个高度相似的 dict 格式化方法

**文件**: `fcli/services/gold_supply_demand_service.py`

`_format_supply_demand_response(data)` 和 `_supply_demand_to_dict(db_data)` 返回几乎相同结构的 dict，区别仅在于输入类型（scraper data vs DB model）。

```python
@staticmethod
def _format_supply_demand_response(data: Any) -> dict:
    return {
        "period": data.period,
        "year": data.year,
        "supply": {"mine_production": data.supply.mine_production, ...},
        ...
    }

@staticmethod
def _supply_demand_to_dict(db_data: GoldSupplyDemand) -> dict:
    return {
        "period": db_data.period,
        "year": db_data.year,
        "supply": {"mine_production": db_data.mine_production, ...},
        ...
    }
```

应统一为一个序列化方法，或在 GoldSupplyDemand 模型上实现 `to_display_dict()` 方法。

**严重度**: P3 — 代码重复

---

## R-03: Service 异常处理大量使用裸 except 静默吞错

**涉及文件**: 多个 Store 和 Service

Store 层普遍使用 `except Exception: return False / return []`：

```python
# QuoteStore
except Exception:
    return False  # 保存失败静默返回

# GoldReserveStore, ExchangeRateStore 等
except Exception:
    return []  # 查询失败静默返回空列表
```

Service 层同样：

```python
# QuoteService.fetch_single
except Exception as e:
    logger.warning(f"Source {source} failed: {e}")
    if not self._config.datasource.fallback_enabled:
        raise
    continue  # 静默跳过失败的数据源
```

数据库写入失败时，数据会丢失但无任何用户可见提示。

**严重度**: P2 — 数据丢失无感知

---

## R-04: ConsolePresenter.print_quote_table 忽略 quote.market 和 quote.type 可能为 None

**文件**: `fcli/utils/presenter.py:81-82`

```python
market_cn = ConsolePresenter._get_market_display(quote.market.value)
type_cn, type_color = ConsolePresenter._get_type_display(quote.type.value)
```

Quote model 中 `market` 和 `type` 都是非可选字段（有默认值），但如果缓存数据中缺少这些字段（反序列化失败），`.value` 调用可能抛出 `AttributeError`。

**严重度**: P3 — 边界条件风险

---

## 汇总

| 编号 | 类别 | 严重度 | 简述                                               |
| ---- | ---- | ------ | -------------------------------------------------- |
| B-01 | BUG  | P1     | save_gold_reserves.py verify_data() 查询 V2 已删表 |
| B-02 | BUG  | P2     | QuoteStore 脆弱类型判断 (hasattr + 字符串)         |
| B-03 | BUG  | P2     | \_fetch_yahoo() 空实现无任何提示                   |
| D-01 | 设计 | P2     | DI Container 使用不一致，多处直导全局单例          |
| D-02 | 设计 | P2     | QuoteService 策略模式半成品，内嵌数据源解析        |
| D-03 | 设计 | P2     | ForexService 导入具体 HybridCache 而非 CacheABC    |
| D-04 | 设计 | P2     | GPRService 混合 JSON+DB 双存储                     |
| D-05 | 设计 | P3     | ConsolePresenter God Class (502行)                 |
| D-06 | 设计 | P3     | Store @classmethod 不参与 DI                       |
| D-07 | 设计 | P3     | ForexService 硬编码数据源 if/elif                  |
| D-08 | 设计 | P3     | BaseScraper.\_cache 死代码                         |
| D-09 | 设计 | P3     | secid_map 硬编码在 Service 层                      |
| D-10 | 设计 | P3     | Container/ForexService 类型标注不匹配              |
| S-01 | 风格 | P3     | 5 个 Command 文件重复模板代码                      |
| S-02 | 风格 | P3     | 日志使用方式不统一 (StructuredLogger vs getLogger) |
| S-03 | 风格 | P3     | 工具函数错放在 Service 层                          |
| S-04 | 风格 | P3     | presenter.py 跨层反向导入 Service                  |
| S-05 | 风格 | P3     | presenter.py 模块级可变全局变量                    |
| S-06 | 风格 | P3     | Service 可选参数默认值写法不一致                   |
| S-07 | 风格 | P3     | Quote.volume 类型为 str 而非数值类型               |
| R-01 | 风险 | P2     | run_async() 每次新建事件循环+关闭 HTTP             |
| R-02 | 风险 | P3     | GoldSupplyDemandService 重复 dict 格式化           |
| R-03 | 风险 | P2     | Store/Service 大量裸 except 静默吞错               |
| R-04 | 风险 | P3     | presenter 未防御 market/type 可能为空              |

**总计**: 24 个发现（3 BUG, 10 设计, 7 风格, 4 风险）

- **P1**: 1 个
- **P2**: 7 个
- **P3**: 16 个
