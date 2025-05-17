from os.path import basename
from pathlib import Path
from typing import AsyncGenerator

from watchfiles import awatch

from log_watcher.watch_filters import UniqueLogFileFilter


async def wait_for_ndt_scan_matcher_log() -> AsyncGenerator[str, None]:
    async for changes in awatch(Path('~/.ros/log/').expanduser(), watch_filter=UniqueLogFileFilter()):
        for _, path in changes:
            filename = basename(path)
            if filename.startswith('ndt_scan_matcher_') or filename.startswith('autoware_ndt_scan_matcher_'):
                yield path
