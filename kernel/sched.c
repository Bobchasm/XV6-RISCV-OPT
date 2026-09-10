#include "types.h"
#include "param.h"
#include "memlayout.h"
#include "riscv.h"
#include "spinlock.h"
#include "proc.h"
#include "sched.h"

extern const struct sched_strategy rr_sched_strategy;

int current_sched_policy = SCHED_DEFAULT_POLICY;

static const struct sched_strategy *strategies[SCHED_POLICY_COUNT];

int
sched_register_strategy(const struct sched_strategy *strategy)
{
  if (strategy == 0 || strategy->policy < 0 ||
      strategy->policy >= SCHED_POLICY_COUNT ||
      strategy->name == 0 || strategy->select_next == 0 ||
      strategy->on_tick == 0 || strategy->on_yield == 0)
    return -1;

  strategies[strategy->policy] = strategy;
  return 0;
}

static const struct sched_strategy *
active_strategy(void)
{
  enum sched_policy policy = sched_policy_current();
  const struct sched_strategy *strategy;

  if (policy < 0 || policy >= SCHED_POLICY_COUNT)
    return &rr_sched_strategy;

  strategy = strategies[policy];
  if (strategy == 0)
    return &rr_sched_strategy;
  return strategy;
}

void
schedinit(void)
{
  sched_register_strategy(&rr_sched_strategy);
  if (!sched_policy_available(SCHED_DEFAULT_POLICY))
    current_sched_policy = SCHED_RR;
}

int
sched_policy_switch(enum sched_policy policy)
{
  if (!sched_policy_available(policy))
    return -1;

  __atomic_store_n(&current_sched_policy, policy, __ATOMIC_RELEASE);
  return 0;
}

enum sched_policy
sched_policy_current(void)
{
  return __atomic_load_n(&current_sched_policy, __ATOMIC_ACQUIRE);
}

const char *
sched_policy_name(enum sched_policy policy)
{
  switch (policy) {
  case SCHED_RR:
    return "rr";
  case SCHED_STATIC_PRIORITY:
    return "static-priority";
  case SCHED_MLFQ:
    return "mlfq";
  default:
    return "unknown";
  }
}

int
sched_policy_available(enum sched_policy policy)
{
  return policy >= 0 && policy < SCHED_POLICY_COUNT &&
         strategies[policy] != 0;
}

struct proc *
select_next_proc(void)
{
  return active_strategy()->select_next();
}

void
sched_proc_init(struct proc *p)
{
  p->priority = SCHED_DEFAULT_PRIORITY;
  p->queue_level = SCHED_DEFAULT_QUEUE_LEVEL;
  p->time_slice = SCHED_RR_TIME_SLICE;
  p->run_time = 0;
  p->ready_count = 0;
  p->wait_count = 0;
  p->sched_policy = sched_policy_current();
  for (int i = 0; i < PROC_STATE_COUNT; i++)
    p->state_stat[i] = 0;
}

void
sched_proc_runnable(struct proc *p)
{
  p->ready_count++;
}

void
update_proc_after_tick(struct proc *p)
{
  p->run_time++;
  p->state_stat[RUNNING]++;
  if (p->time_slice > 0)
    p->time_slice--;

  active_strategy()->on_tick(p);
}

void
sched_on_yield(struct proc *p)
{
  active_strategy()->on_yield(p);
}
