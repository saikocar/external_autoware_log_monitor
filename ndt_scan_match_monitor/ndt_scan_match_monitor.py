from asyncio import sleep
from pathlib import Path
from time import time

from just_playback import Playback

from file_util import follow

NOTIFICATION_COOLDOWN = 10.0


async def play_notification_sound():
    sound_path = str(Path(__file__).resolve().parent / 'bad_score.mp3')
    playback = Playback(sound_path)
    playback.play()
    while playback.active:
        await sleep(0.01)


async def ndt_scan_match_monitor(path: str):
    next_notification_time = 0.0

    async for line in follow(path, 0.1):
        if 'Score is below the threshold' in line:
            current_time = time()
            if current_time >= next_notification_time:
                await play_notification_sound()
            next_notification_time = current_time + NOTIFICATION_COOLDOWN
