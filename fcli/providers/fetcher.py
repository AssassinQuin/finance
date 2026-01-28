import asyncio
from typing import Any, Dict, List, Optional

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from ..core.config import config


class AsyncFetcher:
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=config.timeout),
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
                    "Referer": "http://finance.sina.com.cn",
                },
            )
        return self._session

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def fetch(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        text_mode: bool = False,
    ) -> Any:
        session = await self.get_session()
        async with session.get(url, params=params, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"HTTP error {response.status} for {url}")
            if text_mode:
                return await response.text()
            # Handle Content-Type for JSON parsing if possible, or just try json()
            # Some APIs return text/html but content is JSON.
            try:
                return await response.json()
            except Exception:
                # Fallback to text if JSON parsing fails but user didn't request text_mode
                text = await response.text()
                # Try simple cleaning?
                return text

    async def fetch_batch(self, urls: List[str]) -> List[Any]:
        tasks = [self.fetch(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()


fetcher = AsyncFetcher()
