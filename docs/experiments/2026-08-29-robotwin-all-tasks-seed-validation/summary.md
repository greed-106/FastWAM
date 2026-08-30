# RoboTwin 全任务 Successful Seeds 验证总结

## 完成范围与成功标准

本项目已经完成 50 个 RoboTwin 任务的 successful seeds 搜索、稳定 YAML 归档和逐任务独立测试。稳定目录中的 50 份 YAML 与下表
50 个任务一一对应；每个任务固定包含 clean 10 个、random 10 个环境 seed。一个 seed 必须在
本次采用的验证中通过 expert 前检，并且后续 5 次 FastWAM 策略 rollout 全部成功，才计为成功。expert 前检失败时不会实际执行
rollout，但该 seed 仍直接计为失败，分母始终为每任务 20。

表格采用“最新已完成结果替换旧结果”的滚动维护方式，不再把原验证和重测结果拆成两张表：

- 13 个已经完成新 seed 独立验证的任务，以重测结果替换原表对应行；
- `put_object_cabinet` 使用补验结果，补齐第 50 个任务；
- 其余任务保留原验证结果。

因此，本文的总体统计代表当前 50 个任务各自“最新已完成验证”的汇总视图，不表示 50 项来自同一个同时启动的物理批次。

## 当前结论

全部 50 个任务均已完成测试。统一大表共有 921/1000 个 seed 成功，测试成功率为 92.10%；clean 为 464/500（92.80%），random 为
457/500（91.40%）。大多数任务达到至少 90%：共 40/50（80%），其中 22/50 达到 20/20；其余 10/50 严格低于 90%，另有
9/50 恰好为 90%。

79 个失败 seed 中，44 个未通过 expert 前检，35 个通过 expert 但策略为 0/5；没有策略 1/5 至 4/5 的中间结果。失败阶段只用于
诊断，不改变固定分母或成功判定。

`open_microwave` 新清单的独立验证于 2026-08-30 01:26:14（Asia/Shanghai）完成，clean 为 8/10、random 为 6/10，合计
14/20（70.00%）。6 个失败 seed 中，3 个未通过 expert 前检，3 个通过 expert 但策略为 0/5；没有 1/5 至 4/5 的中间结果。
这次结果已经替换旧验证的 10/20，并使统一大表增加 4 个成功 seed。

## 总体结果

| 指标 | clean | random | 合计 |
| --- | ---: | ---: | ---: |
| 验证 seed | 500 | 500 | 1000 |
| 成功 seed | 464 | 457 | 921 |
| 失败 seed | 36 | 43 | 79 |
| expert 前检失败 seed | 19 | 25 | 44 |
| expert 通过但策略 0/5 seed | 17 | 18 | 35 |
| 本 phase 10/10 的任务 | 31/50 | 27/50 | 两个 phase 均通过 22/50 |

## 每个任务的最新测试成功率

`结果来源/状态` 表示当前行使用哪次已完成验证。`重测已替换` 的 13 行已经覆盖旧数值。

| 任务 | clean 成功 seed | random 成功 seed | 成功 seed | 测试成功率 | expert 失败 | 策略 0/5 | 结果来源/状态 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `adjust_bottle` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `beat_block_hammer` | 10/10 | 9/10 | 19/20 | 95.00% | 1 | 0 | 原验证 |
| `blocks_ranking_rgb` | 10/10 | 9/10 | 19/20 | 95.00% | 1 | 0 | 原验证 |
| `blocks_ranking_size` | 10/10 | 9/10 | 19/20 | 95.00% | 0 | 1 | 原验证 |
| `click_alarmclock` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `click_bell` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `dump_bin_bigbin` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 重测已替换 |
| `grab_roller` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `handover_block` | 10/10 | 7/10 | 17/20 | 85.00% | 3 | 0 | 重测已替换 |
| `handover_mic` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `hanging_mug` | 4/10 | 8/10 | 12/20 | 60.00% | 4 | 4 | 重测已替换 |
| `lift_pot` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `move_can_pot` | 9/10 | 7/10 | 16/20 | 80.00% | 4 | 0 | 重测已替换 |
| `move_pillbottle_pad` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `move_playingcard_away` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `move_stapler_pad` | 9/10 | 8/10 | 17/20 | 85.00% | 0 | 3 | 重测已替换 |
| `open_laptop` | 10/10 | 9/10 | 19/20 | 95.00% | 1 | 0 | 原验证 |
| `open_microwave` | 8/10 | 6/10 | 14/20 | 70.00% | 3 | 3 | 重测已替换 |
| `pick_diverse_bottles` | 9/10 | 10/10 | 19/20 | 95.00% | 0 | 1 | 原验证 |
| `pick_dual_bottles` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `place_a2b_left` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 重测已替换 |
| `place_a2b_right` | 9/10 | 9/10 | 18/20 | 90.00% | 1 | 1 | 原验证 |
| `place_bread_basket` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `place_bread_skillet` | 10/10 | 7/10 | 17/20 | 85.00% | 2 | 1 | 重测已替换 |
| `place_burger_fries` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `place_can_basket` | 6/10 | 7/10 | 13/20 | 65.00% | 4 | 3 | 重测已替换 |
| `place_cans_plasticbox` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `place_container_plate` | 9/10 | 10/10 | 19/20 | 95.00% | 0 | 1 | 原验证 |
| `place_dual_shoes` | 8/10 | 8/10 | 16/20 | 80.00% | 3 | 1 | 重测已替换 |
| `place_empty_cup` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `place_fan` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `place_mouse_pad` | 9/10 | 10/10 | 19/20 | 95.00% | 0 | 1 | 原验证 |
| `place_object_basket` | 4/10 | 8/10 | 12/20 | 60.00% | 4 | 4 | 重测已替换 |
| `place_object_scale` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 重测已替换 |
| `place_object_stand` | 9/10 | 9/10 | 18/20 | 90.00% | 1 | 1 | 原验证 |
| `place_phone_stand` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `place_shoe` | 9/10 | 9/10 | 18/20 | 90.00% | 2 | 0 | 原验证 |
| `press_stapler` | 10/10 | 8/10 | 18/20 | 90.00% | 1 | 1 | 原验证 |
| `put_bottles_dustbin` | 9/10 | 10/10 | 19/20 | 95.00% | 0 | 1 | 原验证 |
| `put_object_cabinet` | 10/10 | 8/10 | 18/20 | 90.00% | 2 | 0 | 补验已完成 |
| `rotate_qrcode` | 10/10 | 8/10 | 18/20 | 90.00% | 1 | 1 | 原验证 |
| `scan_object` | 9/10 | 9/10 | 18/20 | 90.00% | 2 | 0 | 原验证 |
| `shake_bottle` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `shake_bottle_horizontally` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `stack_blocks_three` | 9/10 | 9/10 | 18/20 | 90.00% | 2 | 0 | 原验证 |
| `stack_blocks_two` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `stack_bowls_three` | 7/10 | 7/10 | 14/20 | 70.00% | 0 | 6 | 重测已替换 |
| `stack_bowls_two` | 10/10 | 10/10 | 20/20 | 100.00% | 0 | 0 | 原验证 |
| `stamp_seal` | 9/10 | 9/10 | 18/20 | 90.00% | 2 | 0 | 原验证 |
| `turn_switch` | 9/10 | 10/10 | 19/20 | 95.00% | 0 | 1 | 原验证 |

22 个任务达到 20/20：`adjust_bottle`、`click_alarmclock`、`click_bell`、`dump_bin_bigbin`、`grab_roller`、`handover_mic`、
`lift_pot`、`move_pillbottle_pad`、`move_playingcard_away`、`pick_dual_bottles`、`place_a2b_left`、`place_bread_basket`、
`place_burger_fries`、`place_cans_plasticbox`、`place_empty_cup`、`place_fan`、`place_object_scale`、`place_phone_stand`、
`shake_bottle`、`shake_bottle_horizontally`、`stack_blocks_two`、`stack_bowls_two`。

当前严格低于 90% 的 10 个任务为 `handover_block`、`hanging_mug`、`move_can_pot`、`move_stapler_pad`、`open_microwave`、
`place_bread_skillet`、`place_can_basket`、`place_dual_shoes`、`place_object_basket` 和 `stack_bowls_three`。

## 失败分类与运行告警

| 类型 | seed 数 | 统一统计结果 |
| --- | ---: | --- |
| expert planning 未达到任务成功 | 40 | seed 失败，后续 5 次 rollout 视为失败 |
| `open_microwave` 新验证的 `target_pose` 断言 | 3 | seed 失败，后续 5 次 rollout 视为失败 |
| 场景物体不稳定 `UnStableError` | 1 | seed 失败，后续 5 次 rollout 视为失败 |
| expert 通过、策略执行 0/5 | 35 | seed 失败 |

上述 79 个失败 seed 已全部计入固定分母。当前统一结果仍呈二分：expert 通过后的失败均为策略 0/5，没有 1/5 至 4/5。

所有被采用的已完成验证批次均已完成 SQLite、逐 seed JSON、CSV 与任务 summary 的一致性审计，没有调度失败、超时、OOM、CUDA
错误、native crash、进程被杀或磁盘写满。worker 日志中存在 SAPIEN Vulkan fallback、`missing pytorch3d` 和少量 clutter 对象数量
提示，但未导致验证程序异常退出。

## 结果来源与证据

- 原验证中仍被采用的 36 项：`evaluate_results/robotwin/seed_validation/all_tasks_successful_seeds_49_20260829_0207/`
- 已替换旧行的 12 项重测：`evaluate_results/robotwin/seed_validation/refreshed_successful_seeds_12_20260829_1833/`
- `put_object_cabinet` 补验：`evaluate_results/robotwin/seed_refresh/put_validation_low_success_13_20260829_1500/jobs/validate_put_object_cabinet/`
- `open_microwave` 已完成搜索：`evaluate_results/robotwin/seed_refresh/put_validation_low_success_13_20260829_1500/jobs/open_microwave/`
- `open_microwave` 新清单并行验证：`evaluate_results/robotwin/seed_validation/open_microwave_refreshed_20260830_0112/`
- 完整执行记录：[ledger.md](ledger.md)
