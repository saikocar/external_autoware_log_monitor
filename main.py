import logging
import subprocess
from asyncio import run, create_task, gather
from pathlib import Path

from log_watcher.autoware_launch import wait_for_autoware_launch_log
from log_watcher.ndt_scan_matcher import wait_for_ndt_scan_matcher_log
from ndt_scan_match_monitor.ndt_scan_match_monitor import ndt_scan_match_monitor
from node_death_monitor.node_death_monitor import node_death_monitor
from container_monitor.container_monitor import container_monitor

HERE = Path(__file__).resolve().parent
# このファイルがあれば「NDT スコア低下」の音声を鳴らさない(ROS のノード ndt_voice_notifier に移したとき。README の「NDT の音声を移す」)
NDT_VOICE_DISABLED_FLAG = HERE / 'ndt_voice_disabled'


def get_version() -> str:
    """起動時に名乗る版(git の hash。手元に変更があれば +dirty)。"""
    try:
        h = subprocess.run(['git', '-C', str(HERE), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, timeout=5).stdout.strip()
        dirty = subprocess.run(['git', '-C', str(HERE), 'status', '--porcelain', '--untracked-files=no'],
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return (h or 'unknown') + ('+dirty' if dirty else '')
    except Exception:
        return 'unknown'


async def main():
    async def monitor_node_death():
        task = None
        async for path in wait_for_autoware_launch_log():
            if task is not None:
                task.cancel()
            task = create_task(node_death_monitor(path))

    async def monitor_matching_score():
        task = None
        async for path in wait_for_ndt_scan_matcher_log():
            if task is not None:
                task.cancel()
            task = create_task(ndt_scan_match_monitor(path))

    print(f'INFO: version {get_version()}', flush=True)
    if NDT_VOICE_DISABLED_FLAG.exists():
        # 「NDT スコア低下」は ROS のノード ndt_voice_notifier が、LiDAR を主に使う区間の中と、その入口の手前でだけ鳴らす(本人 2026-10-16)
        print(f'INFO: NDT score voice is disabled here ({NDT_VOICE_DISABLED_FLAG.name} exists): ndt_voice_notifier plays it', flush=True)
        await gather(monitor_node_death(), container_monitor(), )
    else:
        await gather(monitor_node_death(), monitor_matching_score(), container_monitor(), )


if __name__ == '__main__':
    def is_debugger_attached():
        import sys
        return sys.gettrace() is not None


    if is_debugger_attached():
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
        run(main(), debug=True)
    else:
        run(main())
