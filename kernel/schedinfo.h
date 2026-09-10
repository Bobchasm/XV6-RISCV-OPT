#ifndef XV6_SCHEDINFO_H
#define XV6_SCHEDINFO_H

#include "kernel/types.h"

#define PSINFO_NAME_LEN 16
#define PSINFO_STATE_COUNT 6

// 用户态可见的单进程调度快照；字段只来自公共 PCB 调度状态。
struct psinfo {
  int inuse;
  int pid;
  int state;
  int priority;
  int queue_level;
  int time_slice;
  int sched_policy;
  char name[PSINFO_NAME_LEN];
  uint64 run_time;
  uint64 ready_count;
  uint64 wait_count;
  uint64 state_stat[PSINFO_STATE_COUNT];
};

// 用户态可见的全局调度统计，用于性能测试脚本或监控程序汇总观察。
struct sched_stat {
  int current_policy;
  int process_count;
  int runnable_count;
  int running_count;
  int sleeping_count;
  int zombie_count;
  uint64 total_run_time;
  uint64 total_ready_count;
  uint64 total_wait_count;
  uint64 total_state_stat[PSINFO_STATE_COUNT];
};

#endif
