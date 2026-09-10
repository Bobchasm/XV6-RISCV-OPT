#include "types.h"
#include "param.h"
#include "memlayout.h"
#include "riscv.h"
#include "spinlock.h"
#include "proc.h"
#include "defs.h"
#include "sched.h"

extern struct proc proc[NPROC];

static int rr_cursor[NCPU];

static struct proc *
rr_select_next(void)
{
  int cpu = cpuid();
  int start = rr_cursor[cpu];

  for (int offset = 0; offset < NPROC; offset++) {
    int index = (start + offset) % NPROC;
    struct proc *p = &proc[index];

    acquire(&p->lock);
    if (p->state == RUNNABLE) {
      rr_cursor[cpu] = (index + 1) % NPROC;
      return p;
    }
    release(&p->lock);
  }
  return 0;
}

static void
rr_on_tick(struct proc *p)
{
  (void)p;
}

static void
rr_on_yield(struct proc *p)
{
  p->time_slice = SCHED_RR_TIME_SLICE;
}

const struct sched_strategy rr_sched_strategy = {
  .policy = SCHED_RR,
  .name = "rr",
  .select_next = rr_select_next,
  .on_tick = rr_on_tick,
  .on_yield = rr_on_yield,
};
