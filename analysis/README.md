# 调度结果绘图

运行：

```bash
python3 analysis/plot_scheduler_results.py
```

脚本读取 `results/` 下的调度实验 CSV，生成 `analysis/plots/` 下的 PNG 和
SVG 文件。PNG 适合直接放入汇报 PPT，SVG 适合后续排版和缩放。

当前图表包括：

- 不同工作量下的周转时间、响应时间、运行 tick 和 CPU share；
- `compute`、`io`、`mixed` 三类场景的周转时间、响应时间、内核响应和运行 tick；
- `work=40` 重复数据的均值与总体标准差。

现有 CSV 是任务级调度统计，没有 `perf`、调用栈或函数采样数据，因此不能生成
严格意义上的 OS 火焰图。火焰图需要采样调用栈并按函数聚合耗时；这里使用任务级
柱状图、折线图和误差线图，更适合当前数据和调度算法比较目标。
