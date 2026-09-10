#include "kernel/types.h"
#include "kernel/stat.h"
#include "user/user.h"

#define DEFAULT_JOBS 6
#define DEFAULT_WORK 40
#define MAX_JOBS 16
#define CPU_CYCLES_PER_ROUND 5000000

static volatile uint64 work_sink;

// 用易解析的 key=value 行输出结果，宿主机脚本不需要理解 xv6 内核结构。
static void
print_result(int job, int kind, int start, int first, int finish, int work)
{
  char *kind_name = "cpu";
  int turnaround = finish - start;
  int response = first - start;

  if (kind == 1)
    kind_name = "io";
  else if (kind == 2)
    kind_name = "mixed";

  printf("SCHEDBENCH job=%d kind=%s start=%d first=%d finish=%d "
         "service=%d turnaround=%d response=%d\n",
         job, kind_name, start, first, finish, work, turnaround, response);
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
  int start = uptime();
  int first = -1;

  if (kind == 0) {
    for (int i = 0; i < work; i++) {
      busy_work(1);
      if (first < 0)
        first = uptime();
      // xv6 的 uptime 以 tick 为单位；主动等待使每个 CPU 工作单元
      // 都能被稳定观测，也避免小样本落在同一个 tick 内。
      pause(1);
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
  print_result(job, kind, start, first, finish, work);
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

  if (jobs < 1)
    jobs = 1;
  if (jobs > MAX_JOBS)
    jobs = MAX_JOBS;
  if (work < 1)
    work = 1;

  printf("SCHEDBENCH_BEGIN jobs=%d work=%d\n", jobs, work);

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
