
import asyncio

import aiohttp
from util import asynced_time

@asynced_time
async def fetch_status(session, url) -> int:
    async with session.get(url) as result:
        return result.status
            
@asynced_time
async def main():
    async with aiohttp.ClientSession() as session:
        fetchers = [fetch_status(session, 'https:/ / www.example .com', 1),
        fetch_status(session, 'https:/ / www.example .com', 1),
        fetch_status(session, 'https:/ / www.example .com', 10)]
        for finished_task in asyncio.as_completed(fetchers):
            print(await finished_task)