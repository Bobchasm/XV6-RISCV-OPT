#include "kernel/types.h"
#include "kernel/sched.h"
#include "kernel/schedinfo.h"
#include "user/user.h"

static char *
state_name(int state)
{
  static char *names[] = {
    "UNUSED", "USED", "SLEEPING", "RUNNABLE", "RUNNING", "ZOMBIE",
  };

  if (state < 0 || state >= 6)
    return "UNKNOWN";
  return names[state];
}

int
main(int argc, char **argv)
{
  struct psinfo info;
  struct sched_stat stat;
  int pid = getpid();
  int priority = 5;

  if (argc > 1)
    priority = atoi(argv[1]);

  if (set_prio(pid, priority) < 0) {
    printf("schedinfo: set_prio failed\n");
    exit(1);
  }
  if (get_psinfo(pid, &info) < 0) {
    printf("schedinfo: get_psinfo failed\n");
    exit(1);
  }
  if (sys_stat(&stat) < 0) {
    printf("schedinfo: sys_stat failed\n");
    exit(1);
  }

  printf("PSINFO pid=%d name=%s state=%s priority=%d queue=%d "
         "slice=%d policy=%d run=%d ready=%d ready_ticks=%d wait=%d\n",
         info.pid, info.name, state_name(info.state), info.priority,
         info.queue_level, info.time_slice, info.sched_policy,
         (int)info.run_time, (int)info.ready_count, (int)info.ready_ticks,
         (int)info.wait_count);
  printf("SCHEDSTAT policy=%d processes=%d runnable=%d running=%d "
         "sleeping=%d zombie=%d run=%d ready=%d wait=%d\n",
         stat.current_policy, stat.process_count, stat.runnable_count,
         stat.running_count, stat.sleeping_count, stat.zombie_count,
         (int)stat.total_run_time, (int)stat.total_ready_count,
         (int)stat.total_wait_count);
  exit(0);
}
