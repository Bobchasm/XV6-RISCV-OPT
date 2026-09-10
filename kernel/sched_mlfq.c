#include "types.h"
#include "param.h"
#include "memlayout.h"
#include "riscv.h"
#include "spinlock.h"
#include "proc.h"
#include "defs.h"
#include "sched.h"

extern struct proc proc[NPROC];
extern uint ticks;

// 每个 CPU 使用独立游标，保证同一 MLFQ 队列中的进程可以轮转。
static int mlfq_cursor[NCPU];

static int
mlfq_time_slice(int level)
{
  switch (level) {
  case 0:
    return SCHED_MLFQ_TIME_SLICE_0;
  case 1:
    return SCHED_MLFQ_TIME_SLICE_1;
  default:
    return SCHED_MLFQ_TIME_SLICE_2;
  }
}

static int
mlfq_level(int level)
{
  if (level < 0)
    return 0;
  if (level >= SCHED_MLFQ_LEVELS)
    return SCHED_MLFQ_LEVELS - 1;
  return level;
}

static void
mlfq_age_locked(struct proc *p)
{
  if (p->state != RUNNABLE)
    return;

  p->ready_ticks = ticks - p->ready_since;
  if (p->ready_ticks >= SCHED_MLFQ_AGING_THRESHOLD &&
      p->queue_level > 0) {
    // 长时间未被调度的进程提升一级，避免低优先级队列饥饿。
    p->queue_level--;
    p->time_slice = mlfq_time_slice(p->queue_level);
    p->ready_since = ticks;
    p->ready_ticks = 0;
  }
}

static struct proc *
mlfq_select_next(void)
{
  int cpu = cpuid();

  // 扫描阶段不跨进程持锁，避免多核调度器之间形成锁的交叉等待。
  for (;;) {
    int start = mlfq_cursor[cpu];
    struct proc *best = 0;
    int best_index = -1;
    int best_level = SCHED_MLFQ_LEVELS;

    for (int offset = 0; offset < NPROC; offset++) {
      int index = (start + offset) % NPROC;
      struct proc *p = &proc[index];

      acquire(&p->lock);
      mlfq_age_locked(p);
      if (p->state == RUNNABLE && p->queue_level < best_level) {
        best = p;
        best_index = index;
        best_level = p->queue_level;
      }
      release(&p->lock);
    }

    if (best == 0)
      return 0;

    acquire(&best->lock);
    mlfq_age_locked(best);
    if (best->state == RUNNABLE) {
      // 重新加锁后以最新队列层级校验候选，防止并发状态变化。
      if (best->queue_level <= best_level) {
        mlfq_cursor[cpu] = (best_index + 1) % NPROC;
        return best;
      }
    }
    release(&best->lock);
  }
}

static void
mlfq_on_tick(struct proc *p)
{
  // 公共层已经完成运行时间和剩余时间片递减；降级放在 yield 钩子中，
  // 这样主动睡眠的 I/O 进程不会因为一次未完成的 CPU 时间片被错误降级。
  (void)p;
}

static void
mlfq_on_yield(struct proc *p)
{
  p->queue_level = mlfq_level(p->queue_level);
  if (p->time_slice <= 0) {
    // 只有真正用完整个时间片的 CPU 密集型进程才降级。
    if (p->queue_level < SCHED_MLFQ_LEVELS - 1)
      p->queue_level++;
    p->time_slice = mlfq_time_slice(p->queue_level);
  }

  // 抢占只暂时挂起进程，保留它在当前队列中的剩余时间片。
  p->ready_since = ticks;
  p->ready_ticks = 0;
}

static void
mlfq_on_wakeup(struct proc *p)
{
  p->queue_level = mlfq_level(p->queue_level);
  if (p->queue_level > 0)
    p->queue_level--;
  p->time_slice = mlfq_time_slice(p->queue_level);
  p->ready_since = ticks;
}

static int
mlfq_should_preempt(struct proc *p)
{
  if (p->time_slice <= 0)
    return 1;

  // 高级队列中出现就绪进程时，尽快让低级队列让出 CPU。
  for (struct proc *candidate = proc; candidate < &proc[NPROC];
       candidate++) {
    acquire(&candidate->lock);
    if (candidate->state == RUNNABLE &&
        candidate->queue_level < p->queue_level) {
      release(&candidate->lock);
      return 1;
    }
    release(&candidate->lock);
  }
  return 0;
}

const struct sched_strategy mlfq_sched_strategy = {
  .policy = SCHED_MLFQ,
  .name = "mlfq",
  .select_next = mlfq_select_next,
  .on_tick = mlfq_on_tick,
  .on_yield = mlfq_on_yield,
  .on_wakeup = mlfq_on_wakeup,
  .should_preempt = mlfq_should_preempt,
};
