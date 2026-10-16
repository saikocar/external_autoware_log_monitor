# external_autoware_log_monitor

Autoware のログ(`~/.ros/log/`)を見て、車内に警告の音声を流す(nuvo の user systemd の `external_autoware_log_monitor.service`)。

| 音声 | 引き金 | 置き場 |
|---|---|---|
| 「<ノード名> が異常終了しました」「ノードが異常終了しました」 | launch.log の `process has died` | `node_death_monitor/` |
| 「NDT スコア低下」 | NDT のログの `Score is below the threshold`(一致度がしきい値以下)。どの区間でも鳴らす | `ndt_scan_match_monitor/` |

音量は `volume.json`(nuvo:8085 の画面が書く)。起動時に `INFO: version <git hash>` を出す。

## NDT の音声を移す(2026-10-16)

「NDT スコア低下」は、LiDAR を主に使う区間の中と、その入口の手前でだけ鳴らすことにした
(本人 2026-10-16「区間の条件を残さないと国交省のもとめるフェールジェントルではない」「どこがLiDARを使う区間か、記憶に頼るのも問題」)。
区間は地図の印で決まるので、ROS のノード `ndt_voice_notifier`(saikocar/ergamio_contec_poc_packages の `ergamio_extra_interface`)が鳴らす。

そのノードを動かす機体では、このプログラムの NDT の音声を止める(二重に鳴らさない)。

```bash
touch ~/external_autoware_log_monitor/ndt_voice_disabled            # 止める
systemctl --user restart external_autoware_log_monitor
journalctl --user -u external_autoware_log_monitor -n 5 | grep 'NDT score voice is disabled'   # 止まったことを確かめる
```

戻すときは `ndt_voice_disabled` を消して restart。目印のファイルは git に入れない(.gitignore)。
`ndt_voice_notifier` の診断は運転支援の必須項目につなぐ(`ergamio_extra_interface/tools/wire_ndt_voice_diag.py`)ので、
ノードが止まれば運転支援を始められない(NDT の音声が鳴らないまま走ることはない)。
