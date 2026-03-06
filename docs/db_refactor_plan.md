# 数据库完整重构计划（不兼容旧结构）

## 目标与范围
- 目标：彻底重构数据库表结构，统一口径、提升扩展性与维护性，允许不兼容旧结构
- 范围：当前 init.sql 中全部业务表与其对应的服务层读写路径
- 非目标：保留旧表兼容层、双写、旧数据完全无损迁移

## 现状痛点简述
- 模型层与表字段不一致，导致维护成本高、数据语义混乱
- 缺少维度表，国家/货币/资产/数据源等属性重复存储
- 时间维度与唯一键口径不统一，难以支持多频率、多来源

## 重构原则
- 维度表统一口径：国家、货币、资产、数据源、时间周期
- 事实表按主题拆分：报价、汇率、黄金储备、GPR、供需等
- 强约束与可追溯：唯一键、来源、时间戳清晰
- 面向扩展：新增指标与来源不改表结构或最小改动

## 目标数据库结构（V2）

### 维度表
1. dim_country  
   - id, code, name, region, timezone, currency_id, is_active
2. dim_currency  
   - id, code, name, symbol
3. dim_data_source  
   - id, name, url, notes
4. dim_asset  
   - id, code, api_code, name, market, asset_type, currency_id, extra(jsonb), is_active, created_at, updated_at
5. dim_period  
   - id, year, quarter, period_label, period_type(quarterly/annual)
6. dim_metric  
   - id, code, name, unit, domain

### 事实表
1. fact_quote  
   - asset_id, quote_time, price, change, change_percent, open, high, low, prev_close, volume, source_id  
   - unique(asset_id, quote_time)
2. fact_fx_rate  
   - base_currency_id, quote_currency_id, rate_time, rate, source_id  
   - unique(base_currency_id, quote_currency_id, rate_time)
3. fact_gold_reserve  
   - country_id, report_date, gold_tonnes, gold_share_pct, gold_value_usd_m, change_1m, change_3m, change_6m, change_12m, source_id, fetched_at  
   - unique(country_id, report_date)
4. dim_central_bank_schedule  
   - country_id, release_frequency, release_day, release_time, timezone, source_id, source_url, notes, is_active, created_at, updated_at
5. fact_gpr  
   - country_id, report_date, gpr_index, gpr_threat, gpr_act, source_id  
   - unique(country_id, report_date)
6. fact_gold_supply_demand  
   - period_id, metric_id, value, source_id  
   - unique(period_id, metric_id, source_id)
7. fact_fetch_log  
   - task_name, status, started_at, completed_at, records_count, error_message, details(jsonb), source_id, duration_ms
8. cache_entries  
   - key, namespace, value(jsonb), expires_at, created_at, updated_at

## 表与模型映射建议
- Quote -> fact_quote
- ExchangeRate -> fact_fx_rate
- GoldReserve -> fact_gold_reserve
- GPRHistory -> fact_gpr
- GoldSupplyDemand -> fact_gold_supply_demand（通过 dim_metric 标准化指标）
- WatchlistAsset -> dim_asset

## 重构执行计划（不兼容旧结构）

### 阶段 1：设计与准备
- 确认业务指标口径与单位（gold_tonnes、gpr_index 等）
- 明确时间粒度规则（date vs timestamp）
- 明确资产/市场/货币枚举范围
- 制作 V2 DDL 与索引方案

### 阶段 2：新结构落地
- 新建 V2 库或 V2 schema
- 执行 V2 DDL（维度表 -> 事实表 -> 索引）
- 初始化维度数据：货币、国家、资产、数据源、指标、周期

### 阶段 3：服务层重构
- 修改 Store 与 Model，全面对齐 V2 表结构
- 重构读写路径：
  - Quote 服务写入 fact_quote
  - FX 服务写入 fact_fx_rate
  - Gold/GPR/供需服务写入对应 fact_*
- 移除旧表写入逻辑

### 阶段 4：数据重建（可选）
- 如果保留历史数据，执行离线重建：
  - 从旧库或备份导出原始数据
  - 按 V2 结构清洗与重载
- 若不保留历史数据，直接从数据源重新抓取全量

### 阶段 5：切换与验证
- 启用 V2 配置，应用仅连接新库/新 schema
- 验证关键报表与命令输出一致性
- 验证索引覆盖与查询性能

### 阶段 6：清理
- 删除旧库与旧脚本
- 删除旧迁移脚本与不再使用的模型字段
- 更新 init.sql 与部署脚本

## 风险与控制
- 指标口径不一致：提前明确单位/频率/来源
- 数据丢失风险：重构前做一次结构与数据备份
- 上游抓取失败：准备可重试的批量重建脚本

## 验证清单
- 数据完整性：主键/唯一键/外键/非空校验
- 业务输出：gold/gpr/fx/watchlist 命令输出正常
- 性能：核心查询有索引命中

## 交付物清单
- V2 DDL 脚本
- V2 数据初始化脚本
- 服务层改造提交
- 离线重建脚本（可选）
