#include "kernel/types.h"
#include "kernel/schedinfo.h"
#include "user/user.h"
#include "scene.h"

static char *
append_text(char *out, const char *text)
{
  while (*text)
    *out++ = *text++;
  return out;
}

static char *
append_int(char *out, int value)
{
  char digits[16];
  int count = 0;
  uint unsigned_value;

  if (value < 0) {
    *out++ = '-';
    unsigned_value = (uint)-value;
  } else {
    unsigned_value = (uint)value;
  }
  do {
    digits[count++] = '0' + unsigned_value % 10;
    unsigned_value /= 10;
  } while (unsigned_value);
  while (count > 0)
    *out++ = digits[--count];
  return out;
}

static char *
append_field(char *out, const char *name, int value)
{
  out = append_text(out, name);
  *out++ = '=';
  return append_int(out, value);
}

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
  char line[512];
  char *out = line;
  int turnaround = finish - start;
  int response = first - start;
  int kernel_response = -1;

  if (info->schedule_count > 0)
    kernel_response = info->first_run_tick - info->create_tick;

  out = append_text(out, "SCENEBENCH scenario=");
  out = append_text(out, scene_name(config->scene));
  out = append_text(out, " ");
  out = append_field(out, "job", job);
  out = append_text(out, " kind=");
  out = append_text(out, workload_name(kind));
  out = append_text(out, " ");
  out = append_field(out, "start", start);
  out = append_text(out, " ");
  out = append_field(out, "first", first);
  out = append_text(out, " ");
  out = append_field(out, "finish", finish);
  out = append_text(out, " ");
  out = append_field(out, "service", config->work);
  out = append_text(out, " ");
  out = append_field(out, "turnaround", turnaround);
  out = append_text(out, " ");
  out = append_field(out, "response", response);
  out = append_text(out, " ");
  out = append_field(out, "priority", info->priority);
  out = append_text(out, " ");
  out = append_field(out, "queue", info->queue_level);
  out = append_text(out, " ");
  out = append_field(out, "slice", info->time_slice);
  out = append_text(out, " ");
  out = append_field(out, "run_ticks", (int)info->run_time);
  out = append_text(out, " ");
  out = append_field(out, "ready_count", (int)info->ready_count);
  out = append_text(out, " ");
  out = append_field(out, "ready_ticks", (int)info->ready_ticks);
  out = append_text(out, " ");
  out = append_field(out, "total_ready_time", (int)info->total_ready_time);
  out = append_text(out, " ");
  out = append_field(out, "wait_count", (int)info->wait_count);
  out = append_text(out, " ");
  out = append_field(out, "schedule_count", (int)info->schedule_count);
  out = append_text(out, " ");
  out = append_field(out, "create_tick", (int)info->create_tick);
  out = append_text(out, " ");
  out = append_field(out, "first_run_tick", (int)info->first_run_tick);
  out = append_text(out, " ");
  out = append_field(out, "kernel_response", kernel_response);
  out = append_text(out, " ");
  out = append_field(out, "policy", info->sched_policy);
  *out++ = '\n';
  write(1, line, out - line);
}

void
print_scene_end(int start, int finish)
{
  printf("SCENEBENCH_END start=%d finish=%d\n", start, finish);
}
