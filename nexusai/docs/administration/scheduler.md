# Scheduler

Run scrapes on a recurring schedule with a worker pool, retries and notifications.

## Defining schedules

Schedules come in four kinds — cron, daily, weekly and monthly. Using the scheduler
service programmatically:

```python
from nexusai_pro_scheduler import SchedulerService

svc = SchedulerService()
svc.add_daily("prices", target="https://example.com", at="02:00")
svc.add_cron("hourly", target="https://example.com", expr="0 * * * *")
svc.list_schedules()
svc.start()          # begin the tick loop and worker pool
```

## How it runs

Due schedules are enqueued and drained by a worker pool. Failures retry with exponential
backoff via the queue's delayed visibility, then dead-letter when attempts are exhausted.
Every transition is reported to the configured notifiers. See the
[scheduler architecture](../architecture/scheduler.md).

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `NEXUSAI_SCHED_WORKERS` | `2` | Worker-pool size |
| `NEXUSAI_SCHED_TICK` | `1.0` | Tick interval (seconds) |
| `NEXUSAI_SCHED_HISTORY` | `500` | In-memory run-history cap |
| `NEXUSAI_SCHED_WEBHOOK` | *(none)* | Webhook URL for notifications |

## Notifications

Notifiers deliver run outcomes to logging, the console, or a webhook. Set
`NEXUSAI_SCHED_WEBHOOK` to post to your alerting endpoint.

!!! tip "High availability"
    Run a single active scheduler loop (or partition schedules) to avoid duplicate firing.
    Backing schedules with a durable store enables leader-elected HA — see the
    [Roadmap](../about/roadmap.md).
