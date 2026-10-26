"""ノードが落ちたら Autoware を自動で再起動する(2026-10-27 本人「人がやるものではなく自動で再起動をかけるように」)。

「<ノード名> が異常終了しました」を流した後に呼ぶ。数秒のうちに続けて落ちたものは 1 回にまとめ、
最初に落ちたものの名前で ergamio_vehicle_scripts の restart_autoware.sh --auto を起こす。
再起動の中身(音声「再起動をかけます。ハンドルメイン、ペダルメインを下げてください」、メインが下がるのを待つ、
CONTEC の DIO の電源の入れ直し、10 分に 3 回までの上限、どの起動スクリプトかの確かめ)は restart_autoware.sh の側。

このプログラムの unit(external_autoware_log_monitor.service)の中で起こすと、unit を restart したときに Autoware ごと止まるので、
systemd-run --user --scope で別の単位にして起こす。
このディレクトリに auto_restart_disabled があれば何もしない(試験・車庫用。git に入れない)。
"""
from asyncio import create_task, sleep
from logging import getLogger
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent.parent
DISABLED_FLAG = HERE / 'auto_restart_disabled'
RESTART = Path.home() / 'dw_ws/ergamio_vehicle_scripts/nuvo/restart_autoware.sh'
GATHER_SEC = 5.0

_pending: list[str] = []
_task = None


async def _fire():
    global _task
    await sleep(GATHER_SEC)
    names = list(_pending)
    _pending.clear()
    _task = None
    logger = getLogger(__name__)
    if DISABLED_FLAG.exists():
        print(f'INFO: auto restart is disabled ({DISABLED_FLAG.name} exists): {names}', flush=True)
        return
    print(f'INFO: auto restart: {names}', flush=True)
    try:
        subprocess.Popen(['systemd-run', '--user', '--scope', '--quiet', '--unit', f'restart-autoware-{int(__import__("time").time())}',
                          'bash', str(RESTART), '--auto', names[0]],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception as e:  # noqa: BLE001
        logger.exception(e)


def node_died(name: str) -> None:
    global _task
    _pending.append(name)
    if _task is None:
        _task = create_task(_fire())
