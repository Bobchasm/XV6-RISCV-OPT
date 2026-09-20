#include "kernel/types.h"
#include "kernel/schedinfo.h"
#include "user/user.h"
#include "scene.h"

static int
streq(const char *left, const char *right)
{
  return strcmp(left, right) == 0;
}

static enum scene_type
parse_scene(char *name)
{
  if (streq(name, "compute") || streq(name, "compute-heavy"))
    return SCENE_COMPUTE;
  if (streq(name, "io") || streq(name, "io-heavy"))
    return SCENE_IO;
  if (streq(name, "mixed") || streq(name, "mixed-interactive"))
    return SCENE_MIXED;
  return -1;
}

enum workload_kind
scene_job_kind(enum scene_type scene, int job)
{
  if (scene == SCENE_COMPUTE)
    return WORKLOAD_COMPUTE;
  if (scene == SCENE_IO)
    return WORKLOAD_IO;

  switch (job % 3) {
  case 0:
    return WORKLOAD_COMPUTE;
  case 1:
    return WORKLOAD_IO;
  default:
    return WORKLOAD_INTERACTIVE;
  }
}

int
workload_priority(struct scene_config *config, enum workload_kind kind)
{
  return config->priority[kind];
}

static void
run_child(struct scene_config *config, int job)
{
  struct psinfo info;
  enum workload_kind kind = scene_job_kind(config->scene, job);
  int priority = workload_priority(config, kind);

  set_prio(getpid(), priority);

  int start = uptime();
  int first = -1;

  run_workload(kind, job, config->work, &first);

  int finish = uptime();
  if (first < 0)
    first = finish;
  if (get_psinfo(getpid(), &info) < 0) {
    printf("SCENEBENCH_ERROR get_psinfo job=%d\n", job);
    exit(1);
  }

  print_scene_result(config, job, kind, start, first, finish, &info);
  exit(0);
}

int
main(int argc, char **argv)
{
  struct scene_config config;

  config.scene = SCENE_MIXED;
  config.jobs = SCENE_DEFAULT_JOBS;
  config.work = SCENE_DEFAULT_WORK;
  config.priority[WORKLOAD_COMPUTE] = SCENE_CPU_PRIORITY;
  config.priority[WORKLOAD_IO] = SCENE_IO_PRIORITY;
  config.priority[WORKLOAD_INTERACTIVE] = SCENE_INTERACTIVE_PRIORITY;

  if (argc > 1) {
    config.scene = parse_scene(argv[1]);
    if ((int)config.scene < 0) {
      printf("SCENEBENCH_ERROR unknown scenario=%s\n", argv[1]);
      exit(1);
    }
  }
  if (argc > 2)
    config.jobs = atoi(argv[2]);
  if (argc > 3)
    config.work = atoi(argv[3]);
  if (argc > 4)
    config.priority[WORKLOAD_COMPUTE] = atoi(argv[4]);
  if (argc > 5)
    config.priority[WORKLOAD_IO] = atoi(argv[5]);
  if (argc > 6)
    config.priority[WORKLOAD_INTERACTIVE] = atoi(argv[6]);

  if (config.jobs < 1)
    config.jobs = 1;
  if (config.jobs > SCENE_MAX_JOBS)
    config.jobs = SCENE_MAX_JOBS;
  if (config.work < 1)
    config.work = 1;

  print_scene_begin(&config);

  int start = uptime();
  for (int i = 0; i < config.jobs; i++) {
    int pid = fork();
    if (pid < 0) {
      printf("SCENEBENCH_ERROR fork job=%d\n", i);
      continue;
    }
    if (pid == 0)
      run_child(&config, i);
  }

  for (int i = 0; i < config.jobs; i++)
    wait(0);

  print_scene_end(start, uptime());
  exit(0);
}
