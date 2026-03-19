# FCLI - 命令行金融行情工具

FCLI 是一个基于 Python 的轻量级命令行金融工具，支持 A股、港股、美股、公募基金、汇率及黄金储备等数据的实时查询。

## 核心特性

- **智能黄金追踪**: 跟踪全球前20大央行黄金储备，显示 1月/3月/6月/12月变化趋势
- **多数据源支持**: Akshare (A股/基金)、IMF、各国央行等数据源
- **高性能并发**: 基于 `asyncio` 异步抓取，支持并发请求
- **混合缓存**: PostgreSQL UNLOGGED 表 + 文件缓存降级，支持动态 TTL
- **灵活存储**: PostgreSQL 可选，无数据库时自动降级到本地 JSON
- **模块化架构**: 清晰的分层设计，易于维护和扩展

## 快速开始

```bash
# 查看帮助 (支持 -h 简写)
python run.py -h
python run.py --help

# 查询自选股行情 (默认命令)
python run.py
python run.py 600519 000001 AAPL
```

## 命令详解

### 自选管理 (watchlist)

```bash
# 查看帮助
python run.py watchlist -h

# 添加自选 (支持空格分隔多个代码)
python run.py watchlist add 600519
python run.py watchlist add 600519 000858 AAPL

# 列出所有自选
python run.py watchlist ls

# 删除自选 (支持空格分隔多个代码)
python run.py watchlist rm 600519
python run.py watchlist rm 600519 000858 AAPL
```

### 黄金数据 (gold)

```bash
# 查看帮助
python run.py gold -h

# 黄金储备 - 全球 Top 20 央行黄金储备 (默认命令)
python run.py gold
python run.py gold -u              # 强制更新

# 黄金供需数据
python run.py gold supply
```

### 地缘政治风险指数 (gpr)

```bash
# 查看帮助
python run.py gpr -h

# GPR 指数 (默认命令)
python run.py gpr
python run.py gpr -u              # 强制更新
python run.py gpr --no-chart      # 不显示图表

# GPR 历史趋势
python run.py gpr history -m 60   # 显示 60 个月
```

### 汇率查询 (fx)

```bash
# 查看帮助
python run.py fx -h

# 美元兑人民币
python run.py fx USD CNY

# 美元兑所有主要货币
python run.py fx USD

# 默认查询美元
python run.py fx
```

## 命令层级

```
fcli
├── watchlist          # 自选股管理
│   ├── (默认)         # 查询行情
│   ├── add [codes...] # 添加多个自选
│   ├── rm [codes...]  # 删除多个自选
│   ├── ls             # 列出自选
│   └── clear          # 清空自选 (未实现)
├── gold              # 黄金数据
│   ├── (默认)        # 黄金储备
│   └── supply        # 供需数据
├── gpr               # 地缘政治风险
│   ├── (默认)        # GPR 指数
│   └── history       # 历史趋势
└── fx [base] [quote] # 汇率查询 (默认 USD)
```

## 项目架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Entry Point                                                            │
│  run.py → fcli.main:app (Typer CLI)                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  CLI Layer (fcli/main.py)                                               │
│  watchlist | gold | gpr | fx                                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Service Layer (fcli/services/)                                         │
│  QuoteService | GoldService | ForexService | GprService | SpdrService  │
│  WatchlistService (支持批量添加/删除)                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Data Source Layer (fcli/services/scrapers/)                            │
│  BaseScraper → AkshareScraper | IMFScraper | SafeScraper               │
│  central_bank/ - 各国央行数据抓取器                                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Data Access Layer (fcli/core/stores/)                                  │
│  QuoteStore | GoldStore | ExchangeRateStore | WatchlistStore           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Infrastructure (fcli/core/ + fcli/infra/)                              │
│  Cache (Postgres UNLOGGED + File) | Database (PostgreSQL) | HttpClient  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 目录结构

```
fcli/
├── main.py              # CLI 入口 (Typer)
├── commands/            # CLI 命令处理器
│   ├── watchlist.py     # 自选股命令 (add/rm/ls/clear)
│   ├── gold.py          # 黄金命令 (reserves/supply)
│   ├── gpr.py           # GPR 命令 (index/history)
│   └── fx.py            # 汇率命令 (rate)
├── core/
│   ├── cache.py         # 混合缓存 (PostgreSQL UNLOGGED + File)
│   ├── config.py        # 配置管理
│   ├── database.py      # PostgreSQL 连接
│   ├── storage.py       # JSON 本地存储
│   ├── interfaces/      # 接口定义 (Protocol + ABC)
│   ├── models/          # 领域模型 (Asset, Gold, Log)
│   └── stores/          # 数据访问层
├── services/
│   ├── quote_service.py
│   ├── gold_service.py
│   ├── forex_service.py
│   ├── gpr_service.py
│   ├── watchlist_service.py  # 自选股服务 (批量操作)
│   └── scrapers/        # 数据抓取器
├── infra/
│   └── http_client.py   # HTTP 客户端封装
├── utils/
│   ├── presenter.py     # 终端输出格式化
│   ├── logger.py        # 日志工具
│   └── time_util.py     # 时间工具
└── scripts/
    ├── migrate.py       # 数据库迁移
    └── save_gold_reserves.py
```

## 配置

### 环境变量

```bash
# 复制配置模板
cp .env.example .env
```

```bash
# 数据库配置 (可选)
FCLI_DB_HOST=127.0.0.1
FCLI_DB_PORT=5432
FCLI_DB_USER=postgres
FCLI_DB_PASSWORD=your_password
FCLI_DB_DATABASE=fcli
```

### 缓存 TTL 配置 (config.toml)

```toml
[cache]
default_ttl = 300        # 默认缓存 5 分钟
quote_ttl = 60           # 行情缓存 1 分钟
gold_ttl = 3600          # 黄金数据缓存 1 小时
forex_ttl = 300          # 汇率缓存 5 分钟
```

### 数据库初始化

```bash
python -m fcli.scripts.migrate migrate
```

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `gold_reserves` | 央行黄金储备历史数据 |
| `central_bank_schedules` | 央行发布时间配置 |
| `fetch_logs` | 数据抓取日志 |

## 技术栈

| 类别 | 技术 |
|------|------|
| CLI 框架 | Typer + Rich |
| 异步运行时 | asyncio |
| HTTP 客户端 | aiohttp |
| 数据库 | PostgreSQL (asyncpg) |
| 缓存 | PostgreSQL UNLOGGED Table + File |
| 数据抓取 | Akshare, BeautifulSoup |
| 类型检查 | mypy (strict mode) |
| 代码规范 | Ruff |

## 开发

```bash
# 安装依赖
pip install -e .

# 类型检查
mypy fcli

# 代码检查
ruff check fcli

# 运行测试
pytest
```

## License

MIT
