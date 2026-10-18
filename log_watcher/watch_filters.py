import os
from os.path import isfile, splitext
from pathlib import Path

from watchfiles import Change, DefaultFilter


class UniqueLogFileFilter(DefaultFilter):
    def __init__(self) -> None:
        self.seen_paths: set[str] = set()
        super().__init__()

    def __call__(self, change: Change, path: str) -> bool:
        if path not in self.seen_paths:
            self.seen_paths.add(path)
            return splitext(path)[1] == '.log' and isfile(path) and super().__call__(change, path)
        return False


def ros_log_dir() -> Path:
    # ROS のログの場所。ROS_LOG_DIR があればそこ(nuvo は 2026-10-18 から RAM の /dev/shm/ros_log)、無ければ ~/.ros/log
    d = Path(os.environ.get('ROS_LOG_DIR') or '~/.ros/log').expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d
