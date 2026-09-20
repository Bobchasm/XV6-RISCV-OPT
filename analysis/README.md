# 调度结果分析和绘图

所有命令都从仓库根目录执行：

```bash
cd XV6/XV6-RISCV-OPT
```

安装 Python 绘图库：

```bash
python3 -m pip install -r analysis/requirements.txt
```

## 生成数据

重新运行多尺度测试，比较 `RR`、`SPQ` 和 `MLFQ`：

```bash
python3 analysis/run_multiscale.py
```

该脚本固定使用 `CPUS=1`，测试：

- 工作量：`5/10/20/30/40/60/80/100`
- 并发任务数：`1/3/6/9/12`
- 每组重复：`3` 次

结果写入 `results/`，文件名分别为：

```text
results/schedbench-rr-spq-mlfq-work5.csv
results/schedbench-rr-spq-mlfq-work10.csv
...
results/schedbench-rr-spq-mlfq-work100.csv
results/schedbench-rr-spq-mlfq-jobs1.csv
results/schedbench-rr-spq-mlfq-jobs3.csv
...
results/schedbench-rr-spq-mlfq-jobs12.csv
```

也可以先使用 `scripts/run-schedbench.py` 或
`schedworkloads/run-scenes.py` 生成单组数据，详见根目录
[README](../README.md) 和 [测试清单](../docs/checkllist.md)。

## 生成图表

脚本读取 `results/` 下的 CSV，生成 PNG 和 SVG：

```bash
python3 analysis/plot_scheduler_results.py
```

图表输出到 `analysis/plots/`。PNG 可直接放入 PPT，SVG 适合报告排版和缩放。
当前包括：

- CPU、I/O、Mixed 三类任务的多工作量趋势图；
- 均值、总体标准差和误差带；
- 工作量和并发任务数热力图；
- 并发度趋势图；
- 跨工作量的箱线图；
- 响应时间与周转时间散点图；
- 计算、I/O、混合场景对比图。

如果只想重新绘图而不重新运行 QEMU，直接执行绘图命令即可；如果
`results/` 中缺少对应 CSV，脚本会报错。

当前 CSV 是任务级调度统计，没有 `perf`、调用栈或函数采样数据，因此不能生成严格
意义上的 OS 火焰图。现有图表更适合比较三种调度策略在不同工作量、并发度和任务类型
下的调度表现。
