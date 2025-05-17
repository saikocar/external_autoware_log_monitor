from asyncio import wait_for, TimeoutError, create_task, Queue
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional, Sequence

from watchfiles import DefaultFilter, Change
from watchfiles import awatch

from file_util import follow


class FirstSeenFileFilter(DefaultFilter):
    def __init__(self, *, match_filenames: Sequence[str] = None) -> None:
        self.match_filenames = match_filenames
        self.seen_paths: set[str] = set()
        super().__init__()

    def __call__(self, change: Change, path: str) -> bool:
        if path not in self.seen_paths:
            self.seen_paths.add(path)
            if super().__call__(change, path):
                path = Path(path)
                matched = (path.name in self.match_filenames) if self.match_filenames else True
                return matched and path.is_file()
        return False


async def wait_for_autoware_launch_log() -> AsyncGenerator[str, None]:
    async def check_is_file_autoware_launch_log(file_path: str):
        component_container_mt = False
        robot_state_publisher = False
        component_container = False
        topic_state_monitor_node = False
        async for line in follow(file_path):
            if 'component_container_mt-' in line:
                component_container_mt = True
            elif 'robot_state_publisher-' in line:
                robot_state_publisher = True
            elif 'component_container-' in line:
                component_container = True
            elif 'autoware_topic_state_monitor_node-' in line or 'topic_state_monitor_node-' in line:
                topic_state_monitor_node = True
            if component_container_mt and robot_state_publisher and component_container and topic_state_monitor_node:
                return True
        return False

    async def worker(file_path: str, timeout_sec: float = 60.0):
        try:
            if await wait_for(check_is_file_autoware_launch_log(file_path), timeout=timeout_sec):
                await queue.put(file_path)
        except TimeoutError:
            pass

    async def producer(watch_path: Path | str, watch_filter: Optional[Callable[[Change, str], bool]]):
        async for changes in awatch(watch_path, watch_filter=watch_filter):
            for change, path in changes:
                create_task(worker(path))

    queue: Queue[str] = Queue()
    create_task(producer(Path('~/.ros/log/').expanduser(), FirstSeenFileFilter(match_filenames=['launch.log', ])))
    while True:
        yield await queue.get()
