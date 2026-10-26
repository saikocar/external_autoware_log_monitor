"""1 文を車内に読み上げる(2026-10-27)。再起動の道具(ergamio_vehicle_scripts の restart_autoware.sh)が使う。

  .venv/bin/python3 say.py "再起動をかけます"

音の出口は external_autoware_log_monitor.service と同じ(PULSE_SERVER・PULSE_SINK を呼ぶ側で渡す)。
読み上げ(Google)が使えなければ、ノードが落ちたときと同じ音(node_death_monitor/node_died.mp3)を鳴らす。
"""
import sys
from asyncio import run, sleep
from pathlib import Path

from tts import play_speech
from volume import make_playback


async def main(text: str) -> None:
    try:
        await play_speech(text)
    except Exception as e:  # noqa: BLE001
        print(f'WARN: 読み上げに失敗({e})。代わりの音を鳴らす', file=sys.stderr)
        playback = make_playback(str(Path(__file__).resolve().parent / 'node_death_monitor' / 'node_died.mp3'))
        playback.play()
        while playback.active:
            await sleep(0.01)


if __name__ == '__main__':
    run(main(' '.join(sys.argv[1:])))
