import aiohttp
import asyncio
from typing import Optional, Dict, Any

class HttpClient:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
        return self.session
    
    async def fetch(self, url: str, params: Optional[Dict] = None, text_mode: bool = False) -> Any:
        session = await self.get_session()
        try:
            async with session.get(url, params=params, timeout=10) as response:
                if text_mode:
                    return await response.text()
                try:
                    return await response.json()
                except:
                    return await response.text()
        except Exception as e:
            print(f"Request failed: {e}")
            return None

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

http_client = HttpClient()
