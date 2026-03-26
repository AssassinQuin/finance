# 数据库结构优化与重构完整计划（2026-03-26，二次校准版）

## 1. 目标与边界

### 1.1 目标

- 严格基于现网真实表结构和当前代码调用链，制定可执行重构方案。
- 让数据库层与 README 对外功能保持一致，避免“架构图是 V2、运行逻辑是 V1.5”。
- 先修复会导致运行失败的高风险点，再做架构收敛与清理。

### 1.2 边界

- 仅覆盖当前 CLI 功能：`watchlist / market / gold / gpr / fx`。
- 包含 schema、store、service、命令层到数据层的端到端映射。
- 不在本批次引入新业务模块，只做一致性与可维护性提升。

---

## 2. 现状复核（以数据库真实结构为准）

## 2.1 核心表行数（当前环境）

- `dim_fund`: 26249
- `fact_fund_scale`: 1
- `fact_gold_reserve`: 4996
- `fact_gpr`: 1359
- `watchlist_assets`: 17
- `cache_entries`: 10
- `fact_quote`: 0
- `fact_fx_rate`: 0
- `gold_supply_demand`: 0
- `fact_gold_supply_demand`: 0
- `dim_asset`: 3
- `dim_currency`: 5
- `fact_fetch_log`: 0
- `dim_period`: 0
- `dim_metric`: 0
- `migrations`: 0

## 2.2 关键结构事实

### 2.2.1 旧行情/汇率物理表不存在

- `quotes` 和 `exchange_rates` 在现网中不存在。
- 但 `QuoteStore` 与 `ExchangeRateStore` 仍写这两张表，属于悬空实现。

### 2.2.2 黄金供需存在“双模型且都未形成有效写入”

- `gold_supply_demand` 是简化宽表：`year/quarter/supply_total/demand_total/...`。
- `fact_gold_supply_demand` 是指标事实模型：`period_id/metric_id/value/source_id`。
- 代码 `GoldSupplyDemandStore` 期望字段是 WGC 细分指标（mine/jewelry/etf...），与 `gold_supply_demand` 真实列不匹配。

### 2.2.3 watchlist 存在历史列漂移

- `watchlist_assets` 同时有 `asset_type` 与 `type`，代码主路径使用 `type`。

### 2.2.4 视图层现状

- 现网视图有：`v_gold_reserves`、`v_gpr_history`、`v_fund_with_scale`。
- 未发现 `gold_reserves`、`gpr_history` 这两个无 `v_` 前缀的兼容视图。

---

## 3. README 功能需求映射（功能优先级）

## 3.1 命令与真实数据路径

### A. `market`（基金搜索/详情/更新）

- 真实主链路：`FundStore -> dim_fund + fact_fund_scale`。
- 状态：与 V2 一致，属于当前最健康链路。

### B. `gold`（黄金储备）

- 真实主链路：`GoldReserveStore -> fact_gold_reserve + dim_country + dim_data_source`。
- 状态：与 V2 一致，且已有数据沉淀。

### C. `gpr`（地缘风险）

- 真实主链路：`GPRHistoryStore -> fact_gpr + dim_data_source`。
- 状态：与 V2 一致，且已有数据沉淀。

### D. `watchlist`（自选增删查 + 默认行情查询）

- 自选管理链路：`WatchlistService -> storage -> WatchlistAssetStore -> watchlist_assets`。
- 状态：可用，但表结构存在历史冗余列。

### E. `fx`（汇率查询）

- 当前链路：`ForexService -> 外部 API + cache`，未落库到 `fact_fx_rate`。
- 结论：满足 README“查询”需求，但数据库分析能力缺失。

### F. 默认行情查询（watchlist callback）

- 当前链路：`QuoteService -> source + cache`，未落库到 `fact_quote`。
- 结论：满足 README“实时查询”需求，但历史回溯能力缺失。

---

## 4. 问题分级与结论

## 4.1 P0（必须先改）

- Gold Supply/Demand：模型和表结构不一致，存在运行时报错风险。

## 4.2 P1（应尽快改）

- `QuoteStore`/`ExchangeRateStore` 指向不存在表，产生误导并增加维护风险。
- README 中数据库表说明仍偏旧，与现网 V2 不一致。

## 4.3 P2（计划清理）

- `watchlist_assets.asset_type` 与 `type` 重复。
- `fact_fetch_log`、`dim_period`、`dim_metric`、`migrations` 暂未形成真实业务闭环。

---

## 5. 更合适的重构方案（结合现状 + README 需求）

## 5.1 方案总原则

- 对用户功能无感：优先保证 `run.py` 的现有命令体验不退化。
- 对开发者可维护：代码中不得再出现“指向不存在表”的 Store。
- 对架构可演进：新增持久化能力采用 V2 表，不回头补 `quotes/exchange_rates`。

## 5.2 领域决策（最终建议）

### A. Market/Gold/GPR

- 保持现状，不做方向性变更。
- 只做索引与查询微优化。

### B. Gold Supply/Demand（关键决策）

- 主存储改为 `fact_gold_supply_demand`（指标事实表），不再围绕 `gold_supply_demand` 扩列。
- 原因：
  - 当前 `gold_supply_demand` 与业务模型差异过大，补列会退回“大宽表”模式。
  - WGC 数据天然是“季度 + 指标”结构，更适配 `period + metric + value`。
  - `dim_metric`、`dim_period` 当前为空，正好可被该功能真正激活，避免僵尸表。
- 落地方式：
  - 新增 `GoldSupplyDemandFactStore`（或重构现有 Store）将模型字段映射到 metric 行。
  - Service 层保持现有返回结构，避免 CLI 展示改动。
  - `gold_supply_demand` 仅保留为过渡兼容读（若需要），不再作为主写入表。

### C. Quote/FX

- 短期策略：继续 cache-first，保障查询速度与容错。
- 中期策略：新增“异步落库开关”写入 `fact_quote`、`fact_fx_rate`，默认关闭。
- 说明：README 当前核心诉求是查询体验，不要求强制历史落库；因此采用“可选持久化”比“一刀切强制入库”更稳。

### D. Watchlist

- 保留 `type`，逐步淘汰 `asset_type`。
- 先回填、再冻结、最后删除，降低回滚成本。

---

## 6. 分阶段实施（重新排序）

## Phase 0：基线与可回滚机制

- 导出关键表结构和数据快照。
- 固化迁移脚本目录与命名规范。
- 给 `migrations` 表接入真实写入逻辑，避免“有表无记录”。

## Phase 1：P0 修复（Gold Supply/Demand）

- 重构 store/service 的供需持久化路径到 `fact_gold_supply_demand`。
- 初始化 `dim_metric` 与 `dim_period` 基础数据。
- 提供季度 upsert 与读取聚合查询。

## Phase 2：P1 收敛（Quote/FX）

- 处理旧 Store：要么删除，要么改造为 V2 表实现。
- 给 `QuoteService`/`ForexService` 增加可配置的异步持久化写入。
- 继续保留 cache-first 查询路径。

## Phase 3：P2 清理（Watchlist + 无效暴露）

- 清理 `watchlist_assets` 重复字段。
- 修正 `stores.__all__` 悬空导出项。

## Phase 4：文档与运维一致性

- README 数据库章节改为 V2 实际结构与真实视图名。
- AGENTS 与 scripts 使用方式统一（`migrate.py` 不存在，需改为实际脚本）。

---

## 7. 迁移脚本建议

## 7.1 脚本序列

- `data/migrations/20260326_01_supply_demand_fact_refactor.sql`
- `data/migrations/20260326_02_quote_fx_store_cleanup.sql`
- `data/migrations/20260326_03_watchlist_type_consolidation.sql`
- `data/migrations/20260326_04_docs_runtime_alignment.sql`

## 7.2 每个脚本要求

- 幂等执行（`IF EXISTS / IF NOT EXISTS`）。
- 可回滚说明（至少给出逆向 DDL 与数据恢复入口）。
- 数据校验 SQL（行数、唯一键、样本一致性）。

---

## 8. 验收标准（以 README 命令为准）

## 8.1 命令验收

- `python run.py watchlist add 600519`
- `python run.py watchlist`
- `python run.py market search 纳斯达克`
- `python run.py market detail QQQ`
- `python run.py gold`
- `python run.py gold supply`
- `python run.py gpr`
- `python run.py fx USD CNY`

## 8.2 数据验收

- `fact_gold_reserve`、`fact_gpr` 持续可读。
- `fact_gold_supply_demand` 在执行 `gold supply` 后有增量。
- 开启落库开关后，`fact_quote`、`fact_fx_rate` 出现增量。
- `watchlist_assets` 字段语义唯一，不再存在重复定义。

## 8.3 质量验收

- `ruff check fcli`
- `mypy fcli`
- `pytest`

---

## 9. 最终执行建议

1. 立即启动 Phase 1（供需模型改造到事实表），这是唯一 P0。
2. Phase 2 不强制改变用户体验，先做可选落库与旧 Store 清理。
3. Phase 3/4 作为结构降噪与文档收敛，放在功能稳定后执行。

该方案相比上一版更贴近“数据库真实结构 + README 现有功能”，能在不打断用户使用的前提下，逐步把项目收敛到真正可维护的 V2 架构。
