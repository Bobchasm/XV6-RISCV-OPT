#include "types.h"
#include "param.h"
#include "memlayout.h"
#include "riscv.h"
#include "spinlock.h"
#include "proc.h"
#include "defs.h"
#include "sched.h"

extern struct proc proc[NPROC];

// 每个 CPU 都维护独立游标，保证相同优先级的进程也能轮流获得 CPU。
static int priority_cursor[NCPU];

static struct proc *
priority_select_next(void)
{
  int cpu = cpuid();
  
  // 进程锁不能跨进程持有，否则多核扫描时可能形成锁的交叉等待。
  // 如果候选进程在重新加锁时已经不再可运行，就重新扫描一次。
  for (;;) {
    int start = priority_cursor[cpu];
    struct proc *best = 0;
    int best_index = -1;
    int best_priority = 0;

    for (int offset = 0; offset < NPROC; offset++) {
      int index = (start + offset) % NPROC;
      struct proc *p = &proc[index];

      acquire(&p->lock);
      if (p->state == RUNNABLE &&
          (best == 0 || p->priority > best_priority)) {
        // 只保存候选指针和优先级，扫描结束前立即释放进程锁。
        best = p;
        best_index = index;
        best_priority = p->priority;
      }
      release(&p->lock);
    }

    if (best == 0)
      return 0;

    acquire(&best->lock);
    if (best->state == RUNNABLE) {
      priority_cursor[cpu] = (best_index + 1) % NPROC;
      return best;
    }
    release(&best->lock);
  }
}

// 静态优先级策略不根据运行时间动态调整优先级。
static void
priority_on_tick(struct proc *p)
{
  (void)p;
}

static void
priority_on_yield(struct proc *p)
{
  // 保持与 RR 相同的时间片初始化，便于共享现有的时钟抢占路径。
  p->time_slice = SCHED_RR_TIME_SLICE;
}

const struct sched_strategy priority_sched_strategy = {
  .policy = SCHED_STATIC_PRIORITY,
  .name = "static-priority",
  .select_next = priority_select_next,
  .on_tick = priority_on_tick,
  .on_yield = priority_on_yield,
};
