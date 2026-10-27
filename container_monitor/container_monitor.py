"""ava2・ava1 のコンテナが止まったら知らせ、ava2 の認識のコンテナなら Autoware ごと自動で再起動する(2026-10-27)。

nuvo の起動ログ(process has died)には、別の機械のコンテナが止まったことは出ない。そこで 5 秒ごとに
ssh で podman ps / docker ps を見て、Autoware(nuvo の tmux の aw-main)が動いている間に
・一度見えたコンテナが 15 秒続けて見えなくなったら「止まりました」(起動の途中の podman run --replace の入れ替えで鳴らないように 15 秒)
・aw-main を作ってから 3 分たっても一度も見えないコンテナは「起動していません」(起動の途中で落ちたもの)
・aw-main が無い・作り直された(起動し直した)ときは、見えたものの記録を消す
・「Autoware を止める」(kill_autoware.sh)が付ける /dev/shm/autoware_stopped_by_hand があるとき、
  再起動の最中(restart_autoware.sh が付ける /dev/shm/autoware_restarting があるとき)は何もしない
・ssh が届かないときは、止まったとはみなさない(ログに書くだけ)
見張るものと処置は watch_list.txt。
"""
import asyncio
from logging import getLogger
from pathlib import Path
import time

from tts import play_speech
from node_death_monitor.auto_restart import node_died

HERE = Path(__file__).resolve().parent
STOP_FLAG = Path('/dev/shm/autoware_stopped_by_hand')
RESTARTING = Path('/dev/shm/autoware_restarting')   # restart_autoware.sh が動いている間ある
POLL_SEC = 5.0
GONE_SEC = 15.0
NEVER_SEC = 180.0   # Autoware を起こしてから、これだけたっても一度も見えないものは「起動していません」


def load_watch_list():
    rows = []
    for line in (HERE / 'watch_list.txt').read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        host, dest, engine, name, action, label = line.split(None, 5)
        rows.append(dict(host=host, dest=dest, engine=engine, name=name, action=action, label=label))
    return rows


async def run(*cmd, timeout=8.0):
    p = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.DEVNULL,
                                             stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        out, _ = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        p.kill()
        return None
    return out.decode() if p.returncode == 0 else None


async def aw_main_created():
    out = await run('tmux', 'display-message', '-p', '-t', 'aw-main', '#{session_created}')
    return out.strip() if out else None


async def running(dest, engine):
    ps = 'podman ps' if engine == 'podman' else 'sudo -n docker ps'
    out = await run('ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=3', dest, f"{ps} --format '{{{{.Names}}}}'")
    return None if out is None else set(out.split())


async def container_monitor():
    logger = getLogger(__name__)
    rows = load_watch_list()
    session = None
    seen = {}       # (機, 名前) → 最後に見えた時刻
    done = set()    # 知らせ済み(同じ起動の中では 1 回だけ)
    while True:
        await asyncio.sleep(POLL_SEC)
        try:
            created = await aw_main_created()
            if created != session:
                session, seen, done = created, {}, set()
            if created is None:
                continue
            now = time.time()
            for dest, engine in {(r['dest'], r['engine']) for r in rows}:
                names = await running(dest, engine)
                if names is None:
                    logger.info(f'{dest}: {engine} ps に届かない')
                    continue
                for r in rows:
                    if (r['dest'], r['engine']) != (dest, engine):
                        continue
                    key = (r['host'], r['name'])
                    if r['name'] in names:
                        seen[key] = now
                        continue
                    if key in done:
                        continue
                    gone = (key in seen and now - seen[key] >= GONE_SEC) or (key not in seen and now - int(created) >= NEVER_SEC)
                    # 手で止めている・再起動の最中・起動し直した、なら知らせない(見えたかどうかの記録だけ続ける)
                    if not gone or STOP_FLAG.exists() or RESTARTING.exists() or await aw_main_created() != session:
                        continue
                    done.add(key)
                    how = '止まりました' if key in seen else '起動していません'
                    print(f'INFO: container {how}: {r["host"]} {r["name"]} ({r["action"]})', flush=True)
                    try:
                        await play_speech(f'{r["label"]} の {r["name"].replace("-", " ")} が{how}')
                    except Exception as e:  # noqa: BLE001
                        logger.exception(e)
                    if r['action'] == 'restart':
                        node_died(f'{r["host"]} {r["name"]}')
        except Exception as e:  # noqa: BLE001
            logger.exception(e)
