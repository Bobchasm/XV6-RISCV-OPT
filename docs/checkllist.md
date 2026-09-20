# 调度测试 Checklist

约定：

- 正式对比固定 `CPUS=1`
- `RR`：`SCHED_RR`，镜像名 `rr`
- `SPQ`：`SCHED_STATIC_PRIORITY`，镜像名 `spq`
- `MLFQ`：`SCHED_MLFQ`，镜像名 `mlfq`
- `results/` 中 CSV 为原始测试结果
- `--output` 后不写路径时，脚本自动写入 `results/`

## 1 环境和构建

检查工具：

```bash
command -v riscv64-linux-gnu-gcc
command -v qemu-system-riscv64
make --version
python3 --version
```

清理旧构建和旧结果：

```bash
make policies-clean
make clean
rm -f results/schedbench-*.csv results/schedscene-*.csv
```

构建三个策略镜像：

```bash
make policies
```

检查镜像：

```bash
find build/policies -maxdepth 2 -type f -print | sort
```

应包含：

```text
build/policies/rr/kernel-rr
build/policies/rr/fs-rr.img
build/policies/spq/kernel-spq
build/policies/spq/fs-spq.img
build/policies/mlfq/kernel-mlfq
build/policies/mlfq/fs-mlfq.img
```

## 2 回归测试

运行 xv6 用户态回归测试：

```bash
./test-xv6.py -q usertests
```

要求输出 `ALL TESTS PASSED`，且没有 `panic`、超时或 QEMU 残留进程。

## 3 调度微基准

微基准包含 CPU 密集、I/O 密集和混合任务，比较周转时间、响应时间、
等待时间、运行 tick、调度次数和吞吐量。

三种策略单次对比，使用默认输出目录和默认文件名：

```bash
python3 scripts/run-schedbench.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --jobs 6 \
  --work 40 \
  --cpu-priority 1 \
  --io-priority 9 \
  --mixed-priority 5 \
  --repeat 1 \
  --output
```

三种工作量各重复 3 次：

```bash
python3 scripts/run-schedbench.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --jobs 6 \
  --work 10 \
  --cpu-priority 1 \
  --io-priority 9 \
  --mixed-priority 5 \
  --repeat 3 \
  --output results/schedbench-rr-spq-mlfq-work10.csv

python3 scripts/run-schedbench.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --jobs 6 \
  --work 40 \
  --cpu-priority 1 \
  --io-priority 9 \
  --mixed-priority 5 \
  --repeat 3 \
  --output results/schedbench-rr-spq-mlfq-work40.csv

python3 scripts/run-schedbench.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --jobs 6 \
  --work 80 \
  --cpu-priority 1 \
  --io-priority 9 \
  --mixed-priority 5 \
  --repeat 3 \
  --output results/schedbench-rr-spq-mlfq-work80.csv
```

检查静态优先级变化：

```bash
python3 scripts/run-schedbench.py \
  --policies SCHED_STATIC_PRIORITY \
  --jobs 6 \
  --work 40 \
  --cpu-priority 1 \
  --io-priority 9 \
  --mixed-priority 5 \
  --repeat 3 \
  --output results/schedbench-spq-lowcpu.csv

python3 scripts/run-schedbench.py \
  --policies SCHED_STATIC_PRIORITY \
  --jobs 6 \
  --work 40 \
  --cpu-priority 9 \
  --io-priority 1 \
  --mixed-priority 5 \
  --repeat 3 \
  --output results/schedbench-spq-highcpu.csv
```

多尺度数据：一次覆盖多档工作量和并发任务数，供绘图和报告分析使用。

```bash
python3 analysis/run_multiscale.py
```

## 4 场景测试

三个场景分别代表计算密集、I/O 密集和交互与后台任务混合负载。

一次运行三个策略、三个场景，各重复 3 次：

```bash
python3 schedworkloads/run-scenes.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --scenarios compute,io,mixed \
  --jobs 6 \
  --work 20 \
  --compute-priority 1 \
  --io-priority 9 \
  --interactive-priority 12 \
  --repeat 3 \
  --output results/schedscene-rr-spq-mlfq-repeat3.csv
```

分别保存三个场景，便于报告制图：

```bash
python3 schedworkloads/run-scenes.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --scenarios compute \
  --jobs 6 \
  --work 20 \
  --compute-priority 1 \
  --io-priority 9 \
  --interactive-priority 12 \
  --repeat 3 \
  --output results/schedscene-compute-rr-spq-mlfq.csv

python3 schedworkloads/run-scenes.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --scenarios io \
  --jobs 6 \
  --work 20 \
  --compute-priority 1 \
  --io-priority 9 \
  --interactive-priority 12 \
  --repeat 3 \
  --output results/schedscene-io-rr-spq-mlfq.csv

python3 schedworkloads/run-scenes.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --scenarios mixed \
  --jobs 6 \
  --work 20 \
  --compute-priority 1 \
  --io-priority 9 \
  --interactive-priority 12 \
  --repeat 3 \
  --output results/schedscene-mixed-rr-spq-mlfq.csv
```

## 5 边界和专项测试

单任务：观察没有任务竞争时的基线。

```bash
python3 scripts/run-schedbench.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --jobs 1 \
  --work 40 \
  --repeat 3 \
  --output results/schedbench-rr-spq-mlfq-jobs1.csv
```

高并发：观察进程表、等待和回收路径。

```bash
python3 scripts/run-schedbench.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --jobs 12 \
  --work 40 \
  --repeat 3 \
  --timeout 300 \
  --output results/schedbench-rr-spq-mlfq-jobs12.csv
```

MLFQ 长任务：观察队列降级和长任务完成情况。

```bash
python3 scripts/run-schedbench.py \
  --policies SCHED_MLFQ \
  --jobs 12 \
  --work 80 \
  --repeat 3 \
  --timeout 300 \
  --output results/schedbench-mlfq-starvation.csv
```

MLFQ I/O 和混合任务：观察睡眠、唤醒和响应。

```bash
python3 schedworkloads/run-scenes.py \
  --policies SCHED_MLFQ \
  --scenarios io,mixed \
  --jobs 6 \
  --work 20 \
  --compute-priority 1 \
  --io-priority 9 \
  --interactive-priority 12 \
  --repeat 3 \
  --output results/schedscene-mlfq-io-mixed.csv
```

## 6 结果校验

检查所有 CSV 的策略、字段和数值：

```bash
python3 - <<'PY'
import csv
from collections import Counter
from pathlib import Path

policies = {"SCHED_RR", "SCHED_STATIC_PRIORITY", "SCHED_MLFQ"}
numeric = {
    "turnaround", "weighted_turnaround", "response", "kernel_response",
    "throughput", "run_ticks", "schedule_count", "total_ready_time",
}

files = sorted(Path("results").glob("sched*.csv"))
assert files, "没有找到结果文件"
for path in files:
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows, path
    assert set(row["policy"] for row in rows) <= policies, path
    for row in rows:
        for field in numeric:
            assert float(row[field]) >= 0, (path, field, row[field])
    print(path, "rows=", len(rows),
          "policies=", dict(Counter(row["policy"] for row in rows)))
PY
```

检查 QEMU 是否全部退出：

```bash
pgrep -af qemu-system-riscv64 || true
```
