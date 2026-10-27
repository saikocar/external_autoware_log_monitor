import re
from logging import getLogger
from asyncio import sleep
from fnmatch import fnmatch
from pathlib import Path

from aiofiles import open
from file_util import follow
from tts import play_speech
from node_death_monitor.auto_restart import node_died
from volume import make_playback

STOP_FLAG = Path('/dev/shm/autoware_stopped_by_hand')


async def node_death_monitor(path: str):
    logger = getLogger(__name__)

    async with open(Path(__file__).resolve().parent / 'ignore_node_list.txt') as f:
        ignore_nodes = [line.strip() for line in await f.readlines()]

    async for line in follow(path, 0.1):
        if 'user interrupted with ctrl-c (SIGINT)' in line:
            logger.debug('detected user interrupt')
            break

        if 'process has died' not in line:
            continue

        if '__node:=' in line:
            node_name = line[line.find('__node:=') + 8:].split(' ', 1)[0]
        else:
            node_name = line.split(' ', 4)[2][1:-2]
            # launch の番号(lidar_air_wiper-56 の -56)を外す。読み上げで「ごじゅうろく」と読まれ、無視の一覧とも合わない(2026-10-27)
            node_name = re.sub(r'-\d+$', '', node_name)

        # 「Autoware を止める」(kill_autoware.sh)で止めている最中・止めた後に落ちたものは、読み上げも再起動もしない(2026-10-27)
        if STOP_FLAG.exists():
            logger.debug(f'stopped by hand, ignored: {node_name}')
            continue

        if any([fnmatch(node_name, pattern) for pattern in ignore_nodes]):
            logger.debug(f'node ignored: {node_name}')
            continue

        try:
            logger.debug(f'{node_name} is dead')
            await play_speech(f'{node_name.replace("_", " ")} が異常終了しました')
        except Exception as e:
            logger.exception(e)
            playback = make_playback(str(Path(__file__).resolve().parent / 'node_died.mp3'))
            playback.play()
            while playback.active:
                await sleep(0.01)
        # 「異常終了しました」の後に、自動で再起動をかける(まとめと再起動の中身は auto_restart.py)
        node_died(node_name)
