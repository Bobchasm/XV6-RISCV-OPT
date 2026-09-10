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
};

#ifndef SCHED_DEFAULT_POLICY
#define SCHED_DEFAULT_POLICY SCHED_RR
#endif

#define SCHED_DEFAULT_PRIORITY 0
#define SCHED_DEFAULT_QUEUE_LEVEL 0
#define SCHED_RR_TIME_SLICE 1

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

#endif
