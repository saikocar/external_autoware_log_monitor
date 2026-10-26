# external_autoware_log_monitor

Autoware のログ(`~/.ros/log/`)を見て、車内に警告の音声を流す(nuvo の user systemd の `external_autoware_log_monitor.service`)。

| 音声 | 引き金 | 置き場 |
|---|---|---|
| 「<ノード名> が異常終了しました」「ノードが異常終了しました」 | launch.log の `process has died` | `node_death_monitor/` |
| 「再起動をかけます。ハンドルメイン、ペダルメインを下げてください」ほか(2026-10-27) | 「異常終了しました」の後、5 秒のうちに落ちたものをまとめて、ergamio_vehicle_scripts の `nuvo/restart_autoware.sh --auto <最初に落ちたもの>` を `systemd-run --user --scope` で起こす。案内の音声・メインが下がるのを待つ・CONTEC の DIO の電源の入れ直し・10 分に 3 回の上限はそちら。音声は `say.py` で流す。このディレクトリに `auto_restart_disabled` があれば起こさない | `node_death_monitor/auto_restart.py` |
| 「NDT スコア低下」 | NDT のログの `Score is below the threshold`(一致度がしきい値以下)。どの区間でも鳴らす | `ndt_scan_match_monitor/` |

音量は `volume.json`(nuvo:8085 の画面が書く)。起動時に `INFO: version <git hash>` を出す。

## NDT の音声を移す(2026-10-16)

「NDT スコア低下」は、LiDAR を主に使う区間の中と、その入口の手前でだけ鳴らすことにした
(本人 2026-10-16「区間の条件を残さないと国交省のもとめるフェールジェントルではない」「どこがLiDARを使う区間か、記憶に頼るのも問題」)。
区間は地図の印で決まるので、ROS のノード `ndt_voice_notifier`(saikocar/ergamio_contec_poc_packages の `ergamio_extra_interface`)が鳴らす。

そのノードを動かす機体では、このプログラムの NDT の音声を止める(二重に鳴らさない)。

**Autoware を止めているときに行う。** Autoware の起動中にこのプログラムを restart すると、launch.log の見つけ方の都合で、
その回は「異常終了しました」が鳴らなくなる(ergamio_software_docs/launch/startup_scripts.md の注意)。

```bash
touch ~/external_autoware_log_monitor/ndt_voice_disabled            # 止める
T=$(date '+%F %T'); systemctl --user restart external_autoware_log_monitor
sleep 3; journalctl --user -u external_autoware_log_monitor --since "$T" | grep 'NDT score voice is disabled'   # 止まったことを確かめる
# (restart の直後はまだ行が出ていない。--since を付けないと、前の回の行が混ざって見分けられない)
```

戻すときも Autoware を止めてから、`ndt_voice_disabled` を消して restart(新しいノードを動かしたまま戻すと、範囲の中で二重に鳴る)。
目印のファイルは git に入れない(.gitignore)。
`ndt_voice_notifier` の診断は運転支援の必須項目(Lv2・Lv2B)につなぐ(`ergamio_extra_interface/tools/wire_ndt_voice_diag.py`)ので、
ノードが止まる・音の出口(ava1)につながらない(5 秒ごとの確かめが 2 回続けて失敗)・鳴らすのに失敗したときは、運転支援を始められない。
走っている最中なら手動への引き継ぎ(解除)になる。音の出口につながらないための解除では、解除の音声も同じ出口なので鳴らない(座席の振動は出る)。
ただし、ノードが動いていて NDT の一致度が届かないとき
(NDT が照合を飛ばしている、話題の名前が違う)は鳴らない。そのときは診断の値 `score_age_sec` が大きくなり、ログに WARN が 1 回出る
(これまでのプログラムも、NDT が照合を飛ばしているときは警告の行が出ないので鳴らなかった)。
