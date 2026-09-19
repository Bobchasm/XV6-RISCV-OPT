#include "kernel/types.h"
#include "kernel/schedinfo.h"
#include "kernel/stat.h"
#include "user/user.h"

#define DEFAULT_JOBS 6
#define DEFAULT_WORK 40
#define MAX_JOBS 16
#define DEFAULT_CPU_PRIORITY 1
#define DEFAULT_IO_PRIORITY 9
#define DEFAULT_MIXED_PRIORITY 5
#define CPU_CYCLES_PER_ROUND 1500000

static volatile uint64 work_sink;

static int priorities[3] = {
  DEFAULT_CPU_PRIORITY,
  DEFAULT_IO_PRIORITY,
  DEFAULT_MIXED_PRIORITY,
};

// 用易解析的 key=value 行输出结果，宿主机脚本不需要理解 xv6 内核结构。
static void
print_result(int job, int kind, int start, int first, int finish, int work,
             struct psinfo *info)
{
  char *kind_name = "cpu";
  int turnaround = finish - start;
  int response = first - start;
  int kernel_response = -1;

  if (kind == 1)
    kind_name = "io";
  else if (kind == 2)
    kind_name = "mixed";

  if (info->schedule_count > 0)
    kernel_response = info->first_run_tick - info->create_tick;

  printf("SCHEDBENCH job=%d kind=%s start=%d first=%d finish=%d "
         "service=%d turnaround=%d response=%d priority=%d queue=%d "
         "slice=%d run_ticks=%d ready_count=%d ready_ticks=%d "
         "total_ready_time=%d wait_count=%d schedule_count=%d "
         "create_tick=%d first_run_tick=%d kernel_response=%d policy=%d\n",
         job, kind_name, start, first, finish, work, turnaround, response,
         info->priority, info->queue_level, info->time_slice,
         (int)info->run_time, (int)info->ready_count,
         (int)info->ready_ticks, (int)info->total_ready_time,
         (int)info->wait_count, (int)info->schedule_count,
         (int)info->create_tick, (int)info->first_run_tick, kernel_response,
         info->sched_policy);
}

static void
busy_work(int rounds)
{
  volatile uint64 value = 0;

  for (int i = 0; i < rounds * CPU_CYCLES_PER_ROUND; i++)
    value = value * 1664525 + i + 1013904223;

  // 写入 volatile 汇总变量，防止优化器删除整个计算循环。
  work_sink = value;
}

static void
run_job(int job, int kind, int work)
{
  struct psinfo info;
  int priority = priorities[kind];
  set_prio(getpid(), priority);

  int start = uptime();
  int first = -1;

  if (kind == 0) {
    for (int i = 0; i < work; i++) {
      busy_work(1);
      if (first < 0)
        first = uptime();
    }
  } else if (kind == 1) {
    for (int i = 0; i < work; i++) {
      pause(1);
      if (first < 0)
        first = uptime();
    }
  } else {
    for (int i = 0; i < work; i++) {
      busy_work(1);
      if (first < 0)
        first = uptime();
      pause(1);
    }
  }

  int finish = uptime();
  if (first < 0)
    first = finish;
  if (get_psinfo(getpid(), &info) < 0) {
    printf("SCHEDBENCH_ERROR get_psinfo job=%d\n", job);
    exit(1);
  }
  print_result(job, kind, start, first, finish, work, &info);
  exit(0);
}

int
main(int argc, char **argv)
{
  int jobs = DEFAULT_JOBS;
  int work = DEFAULT_WORK;

  if (argc > 1)
    jobs = atoi(argv[1]);
  if (argc > 2)
    work = atoi(argv[2]);
  if (argc > 3)
    priorities[0] = atoi(argv[3]);
  if (argc > 4)
    priorities[1] = atoi(argv[4]);
  if (argc > 5)
    priorities[2] = atoi(argv[5]);

  if (jobs < 1)
    jobs = 1;
  if (jobs > MAX_JOBS)
    jobs = MAX_JOBS;
  if (work < 1)
    work = 1;

  printf("SCHEDBENCH_BEGIN jobs=%d work=%d cpu_prio=%d io_prio=%d "
         "mixed_prio=%d\n",
         jobs, work, priorities[0], priorities[1], priorities[2]);

  int start = uptime();
  for (int i = 0; i < jobs; i++) {
    int pid = fork();
    if (pid < 0) {
      printf("SCHEDBENCH_ERROR fork job=%d\n", i);
      continue;
    }
    if (pid == 0)
      run_job(i, i % 3, work);
  }

  for (int i = 0; i < jobs; i++)
    wait(0);

  printf("SCHEDBENCH_END start=%d finish=%d\n", start, uptime());
  exit(0);
}
