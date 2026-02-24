# FCLI - 命令行金融行情工具

FCLI 是一个基于 Python 的轻量级命令行金融工具，支持 A股、港股、美股、公募基金、汇率及黄金储备等数据的实时查询。

## 核心特性

- **插拔式适配器架构**: 采用适配器模式，支持新浪、东方财富、Frankfurter 等多个数据源，自动选择最优路径
- **责任链数据处理**: 数据清洗流程：格式标准化 → 数据验证 → 数据补全 → 去重合并
- **多格式输出**: 支持 Rich 表格、JSON、CSV、Markdown 等多种输出格式
- **高性能并发**: 使用 `asyncio` 异步抓取行情，支持并行查询取最快响应
- **自动存储策略**: 检测 MySQL 配置，有则存数据库，否则存本地 SQLite

## 快速开始

### 环境要求
- Python 3.11+
- MySQL (可选，不配置则使用 SQLite)

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置 (可选)
复制 `.env.example` 为 `.env` 并配置：
```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

### 运行
```bash
python run.py --help
```

## 使用说明

### 行情查询
```bash
# 查询单个股票
python run.py quote 600519

# 批量查询
python run.py quote 600519 000001
```

### 汇率查询
```bash
# 美元兑人民币
python run.py forex USD CNY

# 美元兑所有主要货币
python run.py forex USD
```

### 市场数据
```bash
# 黄金储备
python run.py market gold

# 地缘政治风险指数
python run.py market gpr
```

## 项目架构

```
fcli/
├── adapter/           # 插拔式适配器层
│   ├── base.py      # BaseAdapter, AssetType
│   ├── registry.py  # 适配器注册表
│   ├── selector/   # 选择策略 (资产路由/优先级/并行)
│   └── sources/    # 具体适配器实现
│
├── processor/       # 责任链处理管道
│   ├── normalize.py  # 格式标准化
│   ├── validate.py  # 数据验证
│   ├── enrich.py    # 数据补全
│   └── merge.py    # 去重合并
│
├── storage/         # 存储层 (MySQL/SQLite)
├── renderer/        # 渲染层 (Rich/JSON/CSV/Markdown)
└── pipeline/       # 业务管道
```

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|-------|
| FCLI_DB_* | MySQL 数据库配置 | 使用 SQLite |
| FCLI_CACHE_*_TTL | 各类数据缓存时间 | 见 .env.example |
| FCLI_TIMEOUT | HTTP 请求超时(秒) | 10 |

## License

MIT
