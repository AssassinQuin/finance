import aiohttp
import asyncio
import json
import logging
from typing import Optional, Dict, Any

from ..core.config import config

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore: Optional[asyncio.Semaphore] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(
                headers=headers,
                connector=connector,
                trust_env=True,  # 支持环境变量代理
            )
        return self.session

    async def fetch(
        self,
        url: str,
        params: Optional[Dict] = None,
        text_mode: bool = False,
        binary_mode: bool = False,
        follow_redirects: bool = True,
        use_proxy: bool = True,
    ) -> Any:
        # 使用信号量限制并发
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(config.http.max_concurrent)
        
        async with self._semaphore:
            return await self._fetch_internal(
                url, params, text_mode, binary_mode, follow_redirects, use_proxy
            )

    async def _fetch_internal(
        self,
        url: str,
        params: Optional[Dict] = None,
        text_mode: bool = False,
        binary_mode: bool = False,
        follow_redirects: bool = True,
        use_proxy: bool = True,
    ) -> Any:
        session = await self.get_session()

        # 配置代理
        proxy = None
        if use_proxy and config.proxy.enabled:
            proxy = config.proxy.http

        for attempt in range(config.http.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(
                    total=config.http.total_timeout,
                    connect=config.http.connect_timeout
                )
                async with session.get(
                    url, params=params, timeout=timeout, allow_redirects=follow_redirects, proxy=proxy
                ) as response:
                    if binary_mode:
                        return await response.read()
                    if text_mode:
                        return await response.text()
                    try:
                        return await response.json()
                    except (json.JSONDecodeError, aiohttp.ContentTypeError):
                        # Response is not JSON, return as text
                        return await response.text()
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}/{config.http.max_retries}: {url}")
                if attempt < config.http.max_retries - 1:
                    await asyncio.sleep(config.http.retry_delay * (attempt + 1))
            except aiohttp.ClientError as e:
                logger.warning(f"Request failed on attempt {attempt + 1}/{config.http.max_retries}: {e}")
                if attempt < config.http.max_retries - 1:
                    await asyncio.sleep(config.http.retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                break

        return None

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


http_client = HttpClient()
