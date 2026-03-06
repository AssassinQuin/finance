# FCLI Refactoring & Optimization Design Document

## 1. Project Analysis (Current State)

### 1.1. Strengths
- **Tech Stack**: Modern async stack (`asyncio`, `aiohttp`, `typer`, `pydantic`).
- **Configuration**: robust `pydantic-settings` based configuration handling `.env` and `config.toml`.
- **Infrastructure**: Centralized `HttpClient` with retry/proxy logic.

### 1.2. Weaknesses & Technical Debt
1.  **High Coupling**:
    - Services (e.g., `QuoteService`) import global instances (`http_client`, `cache`, `config`) directly.
    - Hard to test in isolation (requires patching globals).
2.  **SRP Violation (Single Responsibility)**:
    - `QuoteService` contains both *orchestration logic* (caching, fallback) and *scraping logic* (`_fetch_sina`, `_fetch_fund`).
    - Scraping logic should be in dedicated provider classes.
3.  **Inconsistent Abstractions**:
    - `BaseScraper` exists for Gold/GPR but `QuoteService` implements its own ad-hoc scraping methods.
4.  **Repetitive Logic**:
    - Caching logic (`get` -> `check` -> `fetch` -> `set`) is repeated in service methods.
5.  **Database Dependency**:
    - Code is tightly coupled to specific DB implementations (migrating to Postgres helps, but interfaces are missing).

## 2. Proposed Architecture

We will move towards a **Hexagonal Architecture (Ports and Adapters)** style to decouple core logic from infrastructure.

```
Layered Structure:

[ CLI (Interface) ] -> [ Application (Services) ] -> [ Domain (Models/Interfaces) ]
                                      |
                                      v
                             [ Infrastructure ]
                             (Postgres, HTTP Scrapers, Cache)
```

### 2.1. Key Design Patterns
1.  **Dependency Injection (DI)**:
    - Remove global imports in services.
    - Pass dependencies (`http_client`, `repo`, `sources`) via `__init__`.
    - Use a `Container` class to wire dependencies at startup.
2.  **Strategy Pattern**:
    - Define `QuoteSource` interface.
    - Implement `SinaQuoteSource`, `TencentQuoteSource`, etc.
    - Service iterates over a list of strategies.
3.  **Repository Pattern**:
    - Define `QuoteRepository` interface (Save/Load quotes).
    - Implement `PostgresQuoteRepository`.
4.  **Decorator Pattern**:
    - Use `@cached` decorator for service methods to handle cache hits/misses transparently.

## 3. Detailed Refactoring Plan

### Phase 1: Interface Definition & Scraper Extraction
**Goal**: Clean up `QuoteService`.

1.  **Define Interfaces** (`fcli/core/interfaces/`):
    ```python
    class QuoteSource(Protocol):
        async def fetch(self, asset: Asset) -> Optional[Quote]: ...
        @property
        def name(self) -> str: ...

    class QuoteRepository(Protocol):
        async def save(self, quote: Quote) -> bool: ...
        async def get_latest(self, code: str) -> Optional[Quote]: ...
    ```

2.  **Extract Scrapers**:
    - Create `fcli/services/scrapers/quote/sina.py`.
    - Move `_fetch_sina*` logic there.
    - Create `fcli/services/scrapers/quote/fund_gz.py`.
    - Move `_fetch_fund_1234567` logic there.

3.  **Refactor Service**:
    ```python
    class QuoteService:
        def __init__(self, sources: List[QuoteSource], repo: QuoteRepository):
            self.sources = sources
            self.repo = repo

        async def fetch_quote(self, asset: Asset) -> Optional[Quote]:
            # Logic: Try sources in order, fallback, save to repo
            ...
    ```

### Phase 2: Dependency Injection & Container
**Goal**: Centralize object creation.

1.  **Create Container** (`fcli/core/container.py`):
    ```python
    class Container:
        def __init__(self):
            self.config = load_config()
            self.db = Database(self.config.db)
            self.http = HttpClient(self.config.http)
            self.cache = PostgresCache(self.db)
            
            # Repos
            self.quote_repo = PostgresQuoteRepository(self.db)
            
            # Sources
            self.quote_sources = [
                SinaQuoteSource(self.http),
                # ...
            ]
            
            # Services
            self.quote_service = QuoteService(self.sources, self.quote_repo)
    ```

2.  **Update CLI**:
    - `main.py` instantiates `Container`.
    - Commands use `container.quote_service`.

### Phase 3: Caching & Cross-Cutting Concerns
**Goal**: Remove boilerplate.

1.  **Implement Decorator** (`fcli/core/decorators.py`):
    ```python
    def cached(ttl_strategy: Callable[[Asset], int]):
        def decorator(func):
            async def wrapper(self, asset):
                # check cache
                # if hit return
                # result = await func(self, asset)
                # set cache
                return result
            return wrapper
        return decorator
    ```

2.  **Apply to Service**:
    - Annotate `fetch_quote` with `@cached`.

## 4. Directory Structure Optimization

```
fcli/
├── commands/           # CLI Entry points (keep logic minimal)
├── core/
│   ├── config.py
│   ├── container.py    # [NEW] DI Container
│   ├── exceptions.py
│   ├── interfaces/     # [NEW] Protocols/ABCs
│   │   ├── repository.py
│   │   └── source.py
│   └── models/         # Domain Models
├── infra/              # Infrastructure Implementations
│   ├── cache/          # Cache impls
│   ├── database/       # DB Connection
│   ├── http/           # HTTP Client
│   └── repositories/   # [MOVED] From stores/
├── services/           # Application Logic
│   ├── quote_service.py
│   └── scrapers/       # Data Fetching Strategies
│       ├── quote/      # [NEW] Quote specific scrapers
│       ├── gold/
│       └── base.py
└── utils/
```

## 5. Next Steps
1.  **Approve Design**: Confirm this architectural direction.
2.  **Execute Phase 1**: Extract `SinaScraper` and define `QuoteSource` interface.
3.  **Execute Phase 2**: Implement `Container` and refactor `main.py`.
