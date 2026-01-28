# Finance CLI (FCLI) - 命令行金融行情工具

FCLI 是一个基于 Python 的轻量级命令行金融工具，支持 A股、港股、美股、公募基金以及全球重要指数的实时行情查询与资产管理。

## 核心特性

-   **多源聚合 (Strategy Pattern)**: 采用策略模式，自动调度新浪、东方财富等多个数据源，确保行情获取的准确性与覆盖度。
-   **本地全量索引**: 收录全球超过 2.6 万条资产元数据。搜索不再仅仅依赖远程 API，支持极速本地匹配。
-   **高性能并发**: 使用 `asyncio` 异步抓取行情，多资产查询秒级响应。
-   **智能搜索**: 优先搜索本地索引，支持代码前缀匹配和名称模糊搜索，轻松查找“美元指数”、“纳斯达克”等全球指数。
-   **人性化设计**:
    *   **默认行为**: 直接运行 `python run.py` 即可查看自选行情。
    *   **命令简写**: 支持 `ls` (list), `rm` (remove) 等快捷指令。
    *   **数据隔离**: 自动定位项目根目录下的 `data/` 文件夹，不受执行路径影响。

## 安装指南

### 环境要求
-   Python 3.12+

### 快速开始

1.  **创建并激活虚拟环境 (推荐)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **初始化索引**:
    首次使用建议运行更新，拉取全量资产列表：
    ```bash
    python run.py update
    ```

## 使用说明

### 1. 查看行情 (默认命令)
如果不带任何参数运行，将直接显示所有自选资产的实时行情：
```bash
python run.py
```
或使用显式命令：
```bash
python run.py quote
```

### 2. 搜索资产
支持按名称或代码搜索。搜索结果会显示 `API Code`，方便查看数据来源。
```bash
python run.py search 美元指数
python run.py search NDX
```

### 3. 管理自选
-   **添加资产**: 支持批量添加。程序会自动匹配最接近的结果。
    ```bash
    python run.py add SH000001 SP500 UDI
    ```
-   **删除资产**:
    ```bash
    python run.py remove SH000001
    # 或简写
    python run.py rm SP500
    ```
-   **列出所有资产**:
    ```bash
    python run.py list
    # 或简写
    python run.py ls
    ```

### 4. 更新本地索引
当发现搜索不到新发行的基金或全球指数时，运行此命令刷新本地数据库：
```bash
python run.py update
```

## 项目结构

```text
fcli/
├── commands/       # 命令行入口逻辑
├── services/       # 业务逻辑 (索引服务、行情聚合服务)
├── sources/        # 数据源策略 (新浪、东财等)
├── core/           # 核心模型、配置与存储
└── utils/          # 格式化输出与工具函数
```

## 配置
配置文件位于 `config.toml`，可调整数据存储路径等基础设置。
