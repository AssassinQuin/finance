import asyncio
import atexit
import json
import logging
import weakref
from collections.abc import Coroutine
from typing import Any, TypeVar

import aiohttp

from ..core.config import config

logger = logging.getLogger(__name__)

T = TypeVar("T")


class HttpClient:
    _instance: weakref.ReferenceType["HttpClient"] | None = None
    _cleanup_registered = False

    def __new__(cls):
        instance = super().__new__(cls)
        cls._instance = weakref.ref(instance)
        return instance

    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._register_cleanup()

    def _register_cleanup(self):
        if not HttpClient._cleanup_registered:
            atexit.register(self._sync_cleanup)
            HttpClient._cleanup_registered = True

    @staticmethod
    def _sync_cleanup():
        try:
            loop = asyncio.get_event_loop()
            if loop is None or loop.is_closed():
                return
            if HttpClient._instance is not None:
                client = HttpClient._instance()
                if client is not None and client.session and not client.session.closed:
                    loop.run_until_complete(client._async_close())
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
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            connection_limit = getattr(config.http, "max_connections", None) or config.http.max_concurrent or 100
            host_limit = getattr(config.http, "max_per_host", None) or 10
            connector = aiohttp.TCPConnector(
                ssl=False,
                limit=connection_limit,
                limit_per_host=host_limit,
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
                response = await asyncio.wait_for(
                    session.get(
                        url,
                        params=params,
                        proxy=proxy,
                        headers=request_headers,
                        allow_redirects=follow_redirects,
                    ),
                    timeout=total_timeout,
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

    @classmethod
    async def cleanup_all(cls):
        if cls._instance is not None:
            client = cls._instance()
            if client is not None:
                await client._async_close()


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
        finally:
            try:
                await HttpClient.cleanup_all()
            except Exception:
                logger.exception("Error during HTTP client cleanup")

    return asyncio.run(_runner())


http_client = HttpClient()
