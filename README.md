# FCLI - 命令行金融行情工具

FCLI 是一个基于 Python 的轻量级命令行金融工具，支持 A股、港股、美股、公募基金、汇率及黄金储备等数据的实时查询。

## 核心特性

- **智能黄金追踪**: 跟踪全球前20大央行黄金储备，基于发布时间表自动更新
- **多数据源**: 支持新浪、东方财富、Frankfurter 等多个数据源
- **高性能并发**: 使用 `asyncio` 异步抓取行情
- **自动存储**: 检测 MySQL 配置，有则存数据库，否则存本地 JSON

## 快速开始

```bash
# 查看帮助
python run.py --help
```

## 命令详解

### 行情查询

```bash
# 查询自选股行情 (默认命令)
python run.py quote
python run.py quote 600519 000001
```

### 自选管理 (watch)

```bash
# 添加自选
python run.py watch add 600519
python run.py watch add AAPL

# 列出所有自选
python run.py watch list

# 删除自选
python run.py watch remove 600519
```

### 市场数据 (market)

```bash
# 黄金储备 (自动检测更新)
python run.py market gold
python run.py market gold --update        # 强制更新
python run.py market gold --history CN    # 中国历史趋势

# 地缘政治风险指数
python run.py market gpr
python run.py market gpr --no-chart        # 不显示图表
```

### 汇率查询 (forex)

```bash
# 美元兑人民币
python run.py forex USD CNY

# 美元兑所有主要货币
python run.py forex USD
```

### 资产搜索 (search)

```bash
# 搜索股票/基金
python run.py search 茅台
python run.py search AAPL
```

### 系统管理 (system)

```bash
# 清除缓存
python run.py system clear-cache
```

## 配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑数据库配置 (可选)
FCLI_DB_HOST=127.0.0.1
FCLI_DB_PORT=3306
FCLI_DB_USER=root
FCLI_DB_PASSWORD=your_password
FCLI_DB_DATABASE=fcli
```

### 数据库初始化 (可选)

```bash
python -m fcli.scripts.migrate migrate
```

## 命令层级

```
fcli
├── quote <codes...>      # 行情查询 (默认)
│
├── watch                # 自选管理
│   ├── add <code>      # 添加自选
│   ├── list            # 列出自选
│   └── remove <code>   # 删除自选
│
├── market               # 市场数据
│   ├── gold            # 黄金储备
│   │   --update       # 强制更新
│   │   --history CN   # 历史趋势
│   └── gpr            # 地缘风险
│
├── forex <from> [to]   # 汇率查询
│
├── search <query>      # 资产搜索
│
└── system             # 系统管理
```

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `gold_reserves` | 央行黄金储备历史数据 |
| `central_bank_schedules` | 央行发布时间配置 |
| `fetch_logs` | 数据抓取日志 |

## License

MIT
