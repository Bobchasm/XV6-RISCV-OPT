#ifndef SCHEDWORKLOADS_SCENE_H
#define SCHEDWORKLOADS_SCENE_H

#include "kernel/schedinfo.h"

#define SCENE_DEFAULT_JOBS 6
#define SCENE_DEFAULT_WORK 20
#define SCENE_MAX_JOBS 16
#define SCENE_CPU_PRIORITY 1
#define SCENE_IO_PRIORITY 9
#define SCENE_INTERACTIVE_PRIORITY 12

enum scene_type {
  SCENE_COMPUTE = 0,
  SCENE_IO,
  SCENE_MIXED,
};

enum workload_kind {
  WORKLOAD_COMPUTE = 0,
  WORKLOAD_IO,
  WORKLOAD_INTERACTIVE,
  WORKLOAD_KIND_COUNT,
};

typedef void (*workload_runner)(int job, int work, int *first_tick);

// 每种负载通过统一接口注册，场景入口只负责选择和调用，不关心实现细节。
struct workload_strategy {
  enum workload_kind kind;
  const char *name;
  workload_runner run;
};

struct scene_config {
  enum scene_type scene;
  int jobs;
  int work;
  int priority[WORKLOAD_KIND_COUNT];
};

const char *scene_name(enum scene_type scene);
const char *workload_name(enum workload_kind kind);
enum workload_kind scene_job_kind(enum scene_type scene, int job);
int workload_priority(struct scene_config *config, enum workload_kind kind);
const struct workload_strategy *workload_strategy_for(enum workload_kind kind);
void run_workload(enum workload_kind kind, int job, int work, int *first_tick);

void run_compute_workload(int job, int work, int *first_tick);
void run_io_workload(int job, int work, int *first_tick);
void run_interactive_workload(int job, int work, int *first_tick);

void print_scene_begin(struct scene_config *config);
void print_scene_result(struct scene_config *config, int job,
                        enum workload_kind kind, int start, int first,
                        int finish, struct psinfo *info);
void print_scene_end(int start, int finish);

#endif
