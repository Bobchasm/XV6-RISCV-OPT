#include "kernel/types.h"
#include "kernel/fcntl.h"
#include "user/user.h"
#include "scene.h"

#define COMPUTE_CYCLES_PER_UNIT 220000
#define IO_BLOCK_SIZE 512

static volatile uint64 compute_sink;

static void
mark_first(int *first_tick)
{
  if (*first_tick < 0)
    *first_tick = uptime();
}

static void
file_name(char *buf, int job)
{
  strcpy(buf, "scene00");
  buf[5] = '0' + (job / 10) % 10;
  buf[6] = '0' + job % 10;
}

void
run_compute_workload(int job, int work, int *first_tick)
{
  volatile uint64 value = 1469598103934665603ULL;

  (void)job;
  for (int round = 0; round < work; round++) {
    for (int i = 0; i < COMPUTE_CYCLES_PER_UNIT; i++)
      value = (value ^ (uint64)(i + round)) * 1099511628211ULL;
    mark_first(first_tick);
  }

  compute_sink = value;
}

static const struct workload_strategy workload_strategies[] = {
  {WORKLOAD_COMPUTE, "compute", run_compute_workload},
  {WORKLOAD_IO, "io", run_io_workload},
  {WORKLOAD_INTERACTIVE, "interactive", run_interactive_workload},
};

const struct workload_strategy *
workload_strategy_for(enum workload_kind kind)
{
  for (int i = 0; i < WORKLOAD_KIND_COUNT; i++) {
    if (workload_strategies[i].kind == kind)
      return &workload_strategies[i];
  }
  return 0;
}

void
run_workload(enum workload_kind kind, int job, int work, int *first_tick)
{
  const struct workload_strategy *strategy = workload_strategy_for(kind);

  if (strategy == 0)
    exit(2);
  strategy->run(job, work, first_tick);
}

void
run_io_workload(int job, int work, int *first_tick)
{
  char name[14];
  char buf[IO_BLOCK_SIZE];
  int fd;
  int checksum = 0;

  file_name(name, job);
  for (int i = 0; i < sizeof(buf); i++)
    buf[i] = 'A' + (job + i) % 26;

  fd = open(name, O_CREATE | O_TRUNC | O_RDWR);
  if (fd < 0)
    exit(2);
  for (int round = 0; round < work; round++) {
    if (write(fd, buf, sizeof(buf)) != sizeof(buf))
      exit(2);
    mark_first(first_tick);
  }
  close(fd);

  fd = open(name, O_RDONLY);
  if (fd < 0)
    exit(2);
  while (read(fd, buf, sizeof(buf)) > 0)
    checksum += buf[0];
  close(fd);
  unlink(name);

  compute_sink = checksum;
}

void
run_interactive_workload(int job, int work, int *first_tick)
{
  char name[14];
  char buf[64];
  int loops = work;

  if (loops > 8)
    loops = 8;
  if (loops < 1)
    loops = 1;

  file_name(name, job);
  for (int i = 0; i < sizeof(buf); i++)
    buf[i] = 'a' + (job + i) % 26;

  for (int round = 0; round < loops; round++) {
    int fd = open(name, O_CREATE | O_TRUNC | O_RDWR);
    if (fd < 0)
      exit(2);
    if (write(fd, buf, sizeof(buf)) != sizeof(buf))
      exit(2);
    close(fd);
    unlink(name);
    mark_first(first_tick);
  }
}
