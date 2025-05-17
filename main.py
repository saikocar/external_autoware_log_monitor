import logging
from asyncio import run, create_task, gather

from log_watcher.autoware_launch import wait_for_autoware_launch_log
from log_watcher.ndt_scan_matcher import wait_for_ndt_scan_matcher_log
from ndt_scan_match_monitor.ndt_scan_match_monitor import ndt_scan_match_monitor
from node_death_monitor.node_death_monitor import node_death_monitor


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

    await gather(monitor_node_death(), monitor_matching_score(), )


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
