import io
from asyncio import sleep
from pathlib import PurePath
from typing import AsyncGenerator

import aiofiles


async def follow(file_path: PurePath | str) -> AsyncGenerator[str, None]:
    async with aiofiles.open(file_path, mode='r') as f:
        await f.seek(0, io.SEEK_END)
        while not f.closed:
            line = await f.readline()
            (yield line.strip()) if line else (await sleep(0.01))
