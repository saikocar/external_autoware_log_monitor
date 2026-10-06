import json
from pathlib import Path

# 警告音声の音量(0.1〜1.0)。brake_scale_webui(nuvo:8085)が書く。
# 鳴らすたびに読むので、変更に再起動は要らない。
VOLUME_FILE = Path(__file__).resolve().parent / 'volume.json'
MIN_VOLUME = 0.1  # 警告が聞こえなくならないように 0 にはしない


def get_volume() -> float:
    try:
        volume = float(json.loads(VOLUME_FILE.read_text())['volume'])
        return min(1.0, max(MIN_VOLUME, volume))
    except Exception:  # ファイルが無い・壊れている → 今までどおり 100 %
        return 1.0
