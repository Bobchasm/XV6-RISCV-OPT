#ifndef XV6_SCHED_H
#define XV6_SCHED_H

struct proc;

enum sched_policy {
  SCHED_RR = 0,
  SCHED_STATIC_PRIORITY,
  SCHED_MLFQ,
  SCHED_POLICY_COUNT,
};

struct sched_strategy {
  enum sched_policy policy;
  const char *name;
  struct proc *(*select_next)(void);
  void (*on_tick)(struct proc *);
  void (*on_yield)(struct proc *);
  void (*on_wakeup)(struct proc *);
  int (*should_preempt)(struct proc *);
};

#ifndef SCHED_DEFAULT_POLICY
#define SCHED_DEFAULT_POLICY SCHED_RR
#endif

#define SCHED_DEFAULT_PRIORITY 0
#define SCHED_DEFAULT_QUEUE_LEVEL 0
#define SCHED_RR_TIME_SLICE 1

// MLFQ 使用三级队列：0 为最高优先级，2 为最低优先级。
#define SCHED_MLFQ_LEVELS 3
#define SCHED_MLFQ_TIME_SLICE_0 1
#define SCHED_MLFQ_TIME_SLICE_1 2
#define SCHED_MLFQ_TIME_SLICE_2 4
#define SCHED_MLFQ_AGING_THRESHOLD 8

extern int current_sched_policy;

int sched_register_strategy(const struct sched_strategy *);
void schedinit(void);
int sched_policy_switch(enum sched_policy);
enum sched_policy sched_policy_current(void);
const char *sched_policy_name(enum sched_policy);
int sched_policy_available(enum sched_policy);

struct proc *select_next_proc(void);
void sched_proc_init(struct proc *);
void sched_proc_runnable(struct proc *);
void update_proc_after_tick(struct proc *);
void sched_on_yield(struct proc *);
void sched_on_wakeup(struct proc *);
int sched_should_preempt(struct proc *);

#endif
