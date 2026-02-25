import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def fetch(
        self, 
        url: str, 
        params: Optional[Dict] = None, 
        text_mode: bool = False,
        binary_mode: bool = False,
        follow_redirects: bool = True
    ) -> Any:
        session = await self.get_session()
        
        for attempt in range(self.max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                async with session.get(
                    url, 
                    params=params, 
                    timeout=timeout,
                    allow_redirects=follow_redirects
                ) as response:
                    if binary_mode:
                        return await response.read()
                    if text_mode:
                        return await response.text()
                    try:
                        return await response.json()
                    except:
                        return await response.text()
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}: {url}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
            except aiohttp.ClientError as e:
                logger.warning(f"Request failed on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                break
        
        return None
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


http_client = HttpClient()
