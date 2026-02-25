"""
Database layer for gold reserve tracking.
Uses aiomysql for async database operations.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List, Dict, Any

import aiomysql

from .config import config
from .exceptions import DatabaseError


@dataclass
class GoldReserve:
    """Gold reserve data model"""
    id: Optional[int] = None
    country_code: str = ""
    country_name: str = ""
    amount_tonnes: float = 0.0
    percent_of_reserves: Optional[float] = None
    report_date: date = None
    data_source: str = ""
    fetch_time: datetime = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "amount_tonnes": self.amount_tonnes,
            "percent_of_reserves": self.percent_of_reserves,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "data_source": self.data_source,
            "fetch_time": self.fetch_time.isoformat() if self.fetch_time else None,
        }


@dataclass
class CentralBankSchedule:
    """Central bank data release schedule"""
    id: Optional[int] = None
    country_code: str = ""
    country_name: str = ""
    release_day: Optional[int] = None  # Day of month when data is released
    release_frequency: str = "monthly"  # monthly, quarterly
    last_release_date: Optional[date] = None
    next_expected_date: Optional[date] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "release_day": self.release_day,
            "release_frequency": self.release_frequency,
            "last_release_date": self.last_release_date.isoformat() if self.last_release_date else None,
            "next_expected_date": self.next_expected_date.isoformat() if self.next_expected_date else None,
            "is_active": self.is_active,
        }


@dataclass
class FetchLog:
    """Fetch operation log"""
    id: Optional[int] = None
    data_type: str = ""  # gold_reserves, etc.
    source: str = ""  # WGC, IMF, etc.
    status: str = ""  # success, failed, partial
    records_count: int = 0
    duration_ms: int = 0
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "data_type": self.data_type,
            "source": self.source,
            "status": self.status,
            "records_count": self.records_count,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class Database:
    """Database connection pool manager"""
    
    _pool: Optional[aiomysql.Pool] = None
    _enabled: bool = False
    
    @classmethod
    async def init(cls, config_obj=None) -> bool:
        """Initialize database connection pool"""
        if cls._pool is not None:
            return True
        
        cfg = config_obj or config
        
        try:
            cls._pool = await aiomysql.create_pool(
                host=cfg.db.host,
                port=cfg.db.port,
                user=cfg.db.user,
                password=cfg.db.password,
                db=cfg.db.database,
                minsize=cfg.db.pool_min,
                maxsize=cfg.db.pool_max,
                charset='utf8mb4',
                autocommit=True,
            )
            cls._enabled = True
            
            # Test connection
            async with cls._pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
            
            return True
        except Exception as e:
            cls._enabled = False
            print(f"Database initialization failed: {e}")
            return False
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if database is enabled and available"""
        return cls._enabled and cls._pool is not None
    
    @classmethod
    def get_pool(cls) -> Optional[aiomysql.Pool]:
        """Get connection pool"""
        return cls._pool
    
    @classmethod
    async def close(cls):
        """Close all connections"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            cls._enabled = False


class GoldReserveStore:
    """Store class for gold reserve operations"""
    
    @staticmethod
    async def save_batch(reserves: List[GoldReserve]) -> int:
        """Batch save gold reserves (upsert)"""
        if not Database.is_enabled():
            raise DatabaseError("Database not enabled")
        
        if not reserves:
            return 0
        
        pool = Database.get_pool()
        sql = """
        INSERT INTO gold_reserves 
            (country_code, country_name, amount_tonnes, percent_of_reserves, 
             report_date, data_source, fetch_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            country_name = VALUES(country_name),
            amount_tonnes = VALUES(amount_tonnes),
            percent_of_reserves = VALUES(percent_of_reserves),
            data_source = VALUES(data_source),
            fetch_time = VALUES(fetch_time)
        """
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                values = [
                    (
                        r.country_code,
                        r.country_name,
                        r.amount_tonnes,
                        r.percent_of_reserves,
                        r.report_date,
                        r.data_source,
                        r.fetch_time,
                    )
                    for r in reserves
                ]
                await cur.executemany(sql, values)
                return len(values)
    
    @staticmethod
    async def get_latest(limit: int = 20) -> List[GoldReserve]:
        """Get latest gold reserves for all countries"""
        if not Database.is_enabled():
            return []
        
        pool = Database.get_pool()
        sql = """
        SELECT gr.*
        FROM gold_reserves gr
        INNER JOIN (
            SELECT country_code, MAX(report_date) as max_date
            FROM gold_reserves
            GROUP BY country_code
        ) latest ON gr.country_code = latest.country_code 
                 AND gr.report_date = latest.max_date
        ORDER BY gr.amount_tonnes DESC
        LIMIT %s
        """
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (limit,))
                rows = await cur.fetchall()
                return [GoldReserveStore._row_to_model(row) for row in rows]
    
    @staticmethod
    async def get_history(country_code: str, months: int = 24) -> List[GoldReserve]:
        """Get historical gold reserves for a country"""
        if not Database.is_enabled():
            return []
        
        pool = Database.get_pool()
        sql = """
        SELECT *
        FROM gold_reserves
        WHERE country_code = %s
        ORDER BY report_date DESC
        LIMIT %s
        """
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (country_code.upper(), months))
                rows = await cur.fetchall()
                return [GoldReserveStore._row_to_model(row) for row in rows]
    
    @staticmethod
    async def get_latest_with_changes() -> List[Dict[str, Any]]:
        """Get latest reserves with month-over-month and year-over-year changes"""
        if not Database.is_enabled():
            return []
        
        pool = Database.get_pool()
        sql = """
        WITH latest AS (
            SELECT country_code, country_name, amount_tonnes, percent_of_reserves,
                   report_date, data_source
            FROM gold_reserves gr1
            WHERE report_date = (
                SELECT MAX(report_date) FROM gold_reserves gr2 
                WHERE gr2.country_code = gr1.country_code
            )
        ),
        prev_1m AS (
            SELECT country_code, amount_tonnes as prev_1m_amount
            FROM gold_reserves gr
            WHERE report_date = (
                SELECT DISTINCT report_date FROM gold_reserves 
                ORDER BY report_date DESC LIMIT 1 OFFSET 1
            )
        ),
        prev_1y AS (
            SELECT country_code, amount_tonnes as prev_1y_amount
            FROM gold_reserves gr
            WHERE report_date = (
                SELECT DATE_SUB(MAX(report_date), INTERVAL 1 YEAR) FROM gold_reserves
            )
        )
        SELECT 
            l.country_code as code,
            l.country_name as country,
            l.amount_tonnes as amount,
            l.percent_of_reserves,
            DATE_FORMAT(l.report_date, '%Y-%m') as date,
            l.data_source as source,
            COALESCE(l.amount_tonnes - p1.prev_1m_amount, 0) as change_1m,
            COALESCE(l.amount_tonnes - p2.prev_1y_amount, 0) as change_1y
        FROM latest l
        LEFT JOIN prev_1m p1 ON l.country_code = p1.country_code
        LEFT JOIN prev_1y p2 ON l.country_code = p2.country_code
        ORDER BY l.amount_tonnes DESC
        """
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()
                return [dict(row) for row in rows]
    
    @staticmethod
    def _row_to_model(row: Dict) -> GoldReserve:
        """Convert database row to GoldReserve model"""
        return GoldReserve(
            id=row.get('id'),
            country_code=row.get('country_code', ''),
            country_name=row.get('country_name', ''),
            amount_tonnes=float(row.get('amount_tonnes', 0)),
            percent_of_reserves=float(row['percent_of_reserves']) if row.get('percent_of_reserves') else None,
            report_date=row.get('report_date'),
            data_source=row.get('data_source', ''),
            fetch_time=row.get('fetch_time'),
        )


class CentralBankScheduleStore:
    """Store class for central bank schedules"""
    
    @staticmethod
    async def get_all_active() -> List[CentralBankSchedule]:
        """Get all active central bank schedules"""
        if not Database.is_enabled():
            return []
        
        pool = Database.get_pool()
        sql = """
        SELECT * FROM central_bank_schedules
        WHERE is_active = TRUE
        ORDER BY country_code
        """
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                rows = await cur.fetchall()
                return [CentralBankScheduleStore._row_to_model(row) for row in rows]
    
    @staticmethod
    async def get_by_country(country_code: str) -> Optional[CentralBankSchedule]:
        """Get schedule for a specific country"""
        if not Database.is_enabled():
            return None
        
        pool = Database.get_pool()
        sql = "SELECT * FROM central_bank_schedules WHERE country_code = %s"
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (country_code.upper(),))
                row = await cur.fetchone()
                return CentralBankScheduleStore._row_to_model(row) if row else None
    
    @staticmethod
    async def update_schedule(schedule: CentralBankSchedule) -> bool:
        """Insert or update a schedule"""
        if not Database.is_enabled():
            return False
        
        pool = Database.get_pool()
        sql = """
        INSERT INTO central_bank_schedules 
            (country_code, country_name, release_day, release_frequency, 
             last_release_date, next_expected_date, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            country_name = VALUES(country_name),
            release_day = VALUES(release_day),
            release_frequency = VALUES(release_frequency),
            last_release_date = VALUES(last_release_date),
            next_expected_date = VALUES(next_expected_date),
            is_active = VALUES(is_active),
            updated_at = NOW()
        """
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (
                    schedule.country_code,
                    schedule.country_name,
                    schedule.release_day,
                    schedule.release_frequency,
                    schedule.last_release_date,
                    schedule.next_expected_date,
                    schedule.is_active,
                ))
                return True
    
    @staticmethod
    async def init_default_schedules():
        """Initialize default schedules for top 20 countries"""
        default_schedules = [
            {"code": "USA", "name": "美国", "release_day": 28, "frequency": "monthly"},
            {"code": "DEU", "name": "德国", "release_day": 6, "frequency": "monthly"},
            {"code": "ITA", "name": "意大利", "release_day": 7, "frequency": "monthly"},
            {"code": "FRA", "name": "法国", "release_day": 24, "frequency": "monthly"},
            {"code": "RUS", "name": "俄罗斯", "release_day": 10, "frequency": "monthly"},
            {"code": "CHN", "name": "中国", "release_day": 7, "frequency": "monthly"},
            {"code": "CHE", "name": "瑞士", "release_day": 23, "frequency": "monthly"},
            {"code": "JPN", "name": "日本", "release_day": 22, "frequency": "monthly"},
            {"code": "IND", "name": "印度", "release_day": 5, "frequency": "weekly"},
            {"code": "NLD", "name": "荷兰", "release_day": 10, "frequency": "monthly"},
            {"code": "TUR", "name": "土耳其", "release_day": 15, "frequency": "monthly"},
            {"code": "PRT", "name": "葡萄牙", "release_day": 10, "frequency": "monthly"},
            {"code": "UZB", "name": "乌兹别克斯坦", "release_day": 15, "frequency": "monthly"},
            {"code": "SAU", "name": "沙特阿拉伯", "release_day": 20, "frequency": "monthly"},
            {"code": "GBR", "name": "英国", "release_day": 20, "frequency": "monthly"},
            {"code": "KAZ", "name": "哈萨克斯坦", "release_day": 10, "frequency": "monthly"},
            {"code": "ESP", "name": "西班牙", "release_day": 15, "frequency": "monthly"},
            {"code": "AUT", "name": "奥地利", "release_day": 10, "frequency": "monthly"},
            {"code": "THA", "name": "泰国", "release_day": 10, "frequency": "monthly"},
            {"code": "SGP", "name": "新加坡", "release_day": 25, "frequency": "monthly"},
        ]
        
        for sched in default_schedules:
            schedule = CentralBankSchedule(
                country_code=sched["code"],
                country_name=sched["name"],
                release_day=sched["release_day"],
                release_frequency=sched["frequency"],
                is_active=True,
            )
            await CentralBankScheduleStore.update_schedule(schedule)
    
    @staticmethod
    def _row_to_model(row: Dict) -> CentralBankSchedule:
        """Convert database row to CentralBankSchedule model"""
        return CentralBankSchedule(
            id=row.get('id'),
            country_code=row.get('country_code', ''),
            country_name=row.get('country_name', ''),
            release_day=row.get('release_day'),
            release_frequency=row.get('release_frequency', 'monthly'),
            last_release_date=row.get('last_release_date'),
            next_expected_date=row.get('next_expected_date'),
            is_active=bool(row.get('is_active', True)),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )


class FetchLogStore:
    """Store class for fetch logs"""
    
    @staticmethod
    async def log(log_entry: FetchLog) -> bool:
        """Insert a fetch log entry"""
        if not Database.is_enabled():
            return False
        
        pool = Database.get_pool()
        sql = """
        INSERT INTO fetch_logs 
            (data_type, source, status, records_count, duration_ms, error_message)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (
                    log_entry.data_type,
                    log_entry.source,
                    log_entry.status,
                    log_entry.records_count,
                    log_entry.duration_ms,
                    log_entry.error_message,
                ))
                return True
    
    @staticmethod
    async def get_recent(data_type: str = "gold_reserves", limit: int = 10) -> List[FetchLog]:
        """Get recent fetch logs"""
        if not Database.is_enabled():
            return []
        
        pool = Database.get_pool()
        sql = """
        SELECT * FROM fetch_logs
        WHERE data_type = %s
        ORDER BY timestamp DESC
        LIMIT %s
        """
        
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, (data_type, limit))
                rows = await cur.fetchall()
                return [FetchLogStore._row_to_model(row) for row in rows]
    
    @staticmethod
    def _row_to_model(row: Dict) -> FetchLog:
        """Convert database row to FetchLog model"""
        return FetchLog(
            id=row.get('id'),
            data_type=row.get('data_type', ''),
            source=row.get('source', ''),
            status=row.get('status', ''),
            records_count=row.get('records_count', 0),
            duration_ms=row.get('duration_ms', 0),
            error_message=row.get('error_message'),
            timestamp=row.get('timestamp'),
        )
