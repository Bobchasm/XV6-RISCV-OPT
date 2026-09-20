#include "kernel/types.h"
#include "kernel/schedinfo.h"
#include "user/user.h"
#include "scene.h"

const char *
scene_name(enum scene_type scene)
{
  switch (scene) {
  case SCENE_COMPUTE:
    return "compute-heavy";
  case SCENE_IO:
    return "io-heavy";
  case SCENE_MIXED:
    return "mixed-interactive";
  default:
    return "unknown";
  }
}

const char *
workload_name(enum workload_kind kind)
{
  const struct workload_strategy *strategy = workload_strategy_for(kind);

  if (strategy != 0)
    return strategy->name;

  return "unknown";
}

void
print_scene_begin(struct scene_config *config)
{
  printf("SCENEBENCH_BEGIN scenario=%s jobs=%d work=%d "
         "compute_prio=%d io_prio=%d interactive_prio=%d\n",
         scene_name(config->scene), config->jobs, config->work,
         config->priority[WORKLOAD_COMPUTE],
         config->priority[WORKLOAD_IO],
         config->priority[WORKLOAD_INTERACTIVE]);
}

void
print_scene_result(struct scene_config *config, int job,
                   enum workload_kind kind, int start, int first, int finish,
                   struct psinfo *info)
{
  int turnaround = finish - start;
  int response = first - start;
  int kernel_response = -1;

  if (info->schedule_count > 0)
    kernel_response = info->first_run_tick - info->create_tick;

  printf("SCENEBENCH scenario=%s job=%d kind=%s start=%d first=%d finish=%d "
         "service=%d turnaround=%d response=%d priority=%d queue=%d "
         "slice=%d run_ticks=%d ready_count=%d ready_ticks=%d "
         "total_ready_time=%d wait_count=%d schedule_count=%d "
         "create_tick=%d first_run_tick=%d kernel_response=%d policy=%d\n",
         scene_name(config->scene), job, workload_name(kind), start, first,
         finish, config->work, turnaround, response, info->priority,
         info->queue_level, info->time_slice, (int)info->run_time,
         (int)info->ready_count, (int)info->ready_ticks,
         (int)info->total_ready_time, (int)info->wait_count,
         (int)info->schedule_count, (int)info->create_tick,
         (int)info->first_run_tick, kernel_response, info->sched_policy);
}

void
print_scene_end(int start, int finish)
{
  printf("SCENEBENCH_END start=%d finish=%d\n", start, finish);
}
