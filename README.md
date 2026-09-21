# XV6-RISC-V 调度策略实验

这是一个基于 xv6-riscv 的操作系统课程实验项目，包含三种可切换的调度策略：

- `RR`：时间片轮转，编译策略为 `SCHED_RR`
- `SPQ`：静态优先级队列，编译策略为 `SCHED_STATIC_PRIORITY`
- `MLFQ`：多级反馈队列，编译策略为 `SCHED_MLFQ`

正式性能对比固定使用 `CPUS=1`，避免多核调度噪声。

## 1. 环境准备

推荐在 WSL/Ubuntu 22.04 或 Ubuntu 24.04 中执行：

```bash
./scripts/setup-env.sh
```

手动检查工具：

```bash
riscv64-linux-gnu-gcc --version
qemu-system-riscv64 --version
make --version
python3 --version
```

Makefile 会自动探测可用的 RISC-V 工具链，通常不需要在命令中写
`TOOLPREFIX=...`。如果本机使用非标准工具链，仍可手动覆盖：

```bash
make TOOLPREFIX=riscv64-unknown-elf- ...
```

## 2. 构建和启动

清理默认构建产物：

```bash
make clean
```

构建默认的 RR 内核：

```bash
make
```

启动 xv6：

```bash
make qemu
```

正式测试建议固定单 CPU：

```bash
make qemu CPUS=1
```

退出 QEMU：

```text
Ctrl-a x
```

## 3. 构建三种策略

一次构建三种策略镜像：

```bash
make policies
```

策略镜像位置：

```text
build/policies/rr/kernel-rr
build/policies/rr/fs-rr.img
build/policies/spq/kernel-spq
build/policies/spq/fs-spq.img
build/policies/mlfq/kernel-mlfq
build/policies/mlfq/fs-mlfq.img
```

也可以单独构建：

```bash
make rr
make spq
make mlfq
```

源码、内核或用户程序发生变化后，强制重新构建三种镜像：

```bash
make policies-clean
make policies
```

策略镜像已经存在时，测试脚本会自动复用；不需要每次重新构建。

## 4. 回归测试

运行 xv6 用户态回归测试：

```bash
./test-xv6.py -q usertests
```

成功标准是输出：

```text
ALL TESTS PASSED
```

## 5. 调度微基准

三种策略进行一次对比，结果自动写入：
`results/schedbench-rr-spq-mlfq.csv`。

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

也可以显式指定输出路径：

```bash
python3 scripts/run-schedbench.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --jobs 6 \
  --work 40 \
  --repeat 3 \
  --output results/schedbench-rr-spq-mlfq-work40.csv
```

脚本会为每种策略使用独立镜像，并自动固定 QEMU 为 `CPUS=1`。

## 6. 多尺度测试

一次运行多档工作量和并发任务数：

- 工作量：`5/10/20/30/40/60/80/100`
- 任务数：`1/3/6/9/12`
- 每组重复 3 次

```bash
python3 analysis/run_multiscale.py
```

结果写入 `results/`，文件名形如：

```text
results/schedbench-rr-spq-mlfq-work20.csv
results/schedbench-rr-spq-mlfq-jobs9.csv
```

## 7. 场景测试

运行计算、I/O 和混合场景：

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

只运行混合场景：

```bash
python3 schedworkloads/run-scenes.py \
  --policies SCHED_RR,SCHED_STATIC_PRIORITY,SCHED_MLFQ \
  --scenarios mixed \
  --jobs 6 \
  --work 20 \
  --repeat 3 \
  --output results/schedscene-mixed-rr-spq-mlfq.csv
```

## 8. 结果分析和绘图

安装绘图库：

```bash
python3 -m pip install -r analysis/requirements.txt
```

根据 `results/*.csv` 生成 PNG 和 SVG：

```bash
python3 analysis/plot_scheduler_results.py
```

图表输出到：

```text
analysis/plots/
```

当前图表包括多尺度趋势图、均值误差带、工作量和并发度热力图、箱线图、
响应与周转时间散点图以及场景对比图。

## 9. 文档

- [调度测试清单](docs/checkllist.md)
- [调度测试结果分析](docs/调度测试结果分析.md)
- [场景化调度测试](docs/场景化测试设计.md)
- [绘图说明](analysis/README.md)

原始 CSV 保存在 `results/`，构建产物保存在 `build/`；这两类内容默认不提交
到 Git。
