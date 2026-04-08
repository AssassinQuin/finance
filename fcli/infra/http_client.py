import asyncio
import atexit
import json
from collections.abc import Coroutine
from typing import Any, TypeVar

import aiohttp

from ..core.config import config
from ..utils.logger import get_logger

logger = get_logger("fcli.http")

T = TypeVar("T")


class HttpClient:
    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self._semaphore: asyncio.Semaphore | None = None
        atexit.register(self._sync_cleanup)

    def _sync_cleanup(self):
        try:
            loop = asyncio.get_event_loop()
            if loop is None or loop.is_closed():
                return
            if loop.is_running():
                if self.session and not self.session.closed:
                    loop.create_task(self._async_close())
                return
            if self.session and not self.session.closed:
                loop.run_until_complete(self._async_close())
        except Exception as e:
            logger.debug(f"Error during HTTP client cleanup: {e}")

    async def _async_close(self):
        if self.session and not self.session.closed:
            connector = self.session.connector
            await self.session.close()
            if connector and not connector.closed:
                await connector.close()
            self.session = None
            logger.debug("HTTP client session closed")

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {
                "User-Agent": config.http.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            connector = aiohttp.TCPConnector(
                ssl=False,
                limit=config.http.max_connections,
                limit_per_host=config.http.max_per_host,
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=config.http.total_timeout or 30),
            )
        return self.session

    async def fetch(
        self,
        url: str,
        params: dict | None = None,
        text_mode: bool = False,
        binary_mode: bool = False,
        follow_redirects: bool = True,
        use_proxy: bool = True,
        headers: dict | None = None,
        encoding: str | None = None,
    ) -> Any:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(config.http.max_concurrent or 10)

        async with self._semaphore:
            return await self._fetch_internal(
                url, params, text_mode, binary_mode, follow_redirects, use_proxy, headers, encoding
            )

    async def _fetch_internal(
        self,
        url: str,
        params: dict | None = None,
        text_mode: bool = False,
        binary_mode: bool = False,
        follow_redirects: bool = True,
        use_proxy: bool = True,
        extra_headers: dict | None = None,
        encoding: str | None = None,
    ) -> Any:
        session = await self.get_session()

        max_retries = config.http.max_retries or 1
        retry_delay = config.http.retry_delay or 0.5
        total_timeout = config.http.total_timeout or 30

        proxy = None
        if use_proxy and config.proxy.enabled:
            if url.startswith("https://"):
                proxy = config.proxy.https or config.proxy.http
            else:
                proxy = config.proxy.http

            if proxy:
                logger.debug(f"Using proxy: {proxy}")

        request_headers = {}
        if extra_headers:
            request_headers.update(extra_headers)

        for attempt in range(max_retries):
            try:
                response = await session.get(
                    url,
                    params=params,
                    proxy=proxy,
                    headers=request_headers,
                    allow_redirects=follow_redirects,
                    timeout=aiohttp.ClientTimeout(total=total_timeout),
                )
                response.raise_for_status()
                if binary_mode:
                    return await response.read()
                if text_mode:
                    return await response.text(encoding=encoding) if encoding else await response.text()
                response_text = await response.text(encoding=encoding) if encoding else await response.text()
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError:
                    return response_text
            except asyncio.TimeoutError:
                logger.debug(f"Timeout on attempt {attempt + 1}/{max_retries}: {url}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
            except aiohttp.ClientError as e:
                logger.debug(f"Request failed on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                break
        return None

    async def get_binary(self, url: str, use_proxy: bool = True) -> bytes | None:
        result = await self.fetch(url, binary_mode=True, use_proxy=use_proxy)
        return result if isinstance(result, bytes) else None

    async def close(self):
        await self._async_close()


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run async coroutine with automatic HTTP client cleanup.

    Usage:
        # Instead of:
        asyncio.run(my_async_func())

        # Use:
        run_async(my_async_func())
    """

    async def _runner() -> T:
        try:
            return await coro
        except Exception:
            logger.exception("Error during async task execution")
            raise

    return asyncio.run(_runner())


http_client = HttpClient()
