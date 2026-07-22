# varnishstat reference

The companion script `scripts/vg-check` already scans `*varnishstat_-1*` and automatically flags critical and caution counters in check results (`stat-counters`, `child-restart`, `expiry-queue`, `bans`, `waitinglist`, `hit-rate`). This file provides the semantics needed to interpret and explain what vg-check flags, plus material for deeper manual analysis.

Read `*varnishstat_-1*`.  Each line has the format:
```
STAT.counter    cumulative_value    per_second_rate    description
```

## Uptime

- `MGT.uptime` — management process uptime (seconds)
- `MAIN.uptime` — child process uptime; if much less than MGT.uptime, the child restarted

## Critical counters

Flag any that are non-zero:

| Counter pattern | Severity | Meaning |
|---|---|---|
| `MAIN.child_died` | 🔴 WARNING | Child process killed by signal |
| `MAIN.child_panic` | 🔴 WARNING | Child process panicked |
| `MAIN.sess_drop` | 🔴 WARNING | Sessions dropped (overload) |
| `MAIN.threads_failed` | 🔴 WARNING | Failed to create threads |
| `MAIN.sess_fail` | 🔴 WARNING | Session accept failures |
| `MAIN.sc_vcl_failure` | 🔴 WARNING | VCL failures |
| `*.ws_.*_overflow` | 🔴 WARNING | Workspace overflow |
| `*.c_insert_timeout` | 🔴 WARNING | Disk overload (MSE/SSD) |
| `*.aio_write_queue_overflow` | 🔴 WARNING | Disk overload |
| `MAIN.req_dropped` | 🔴 WARNING | Requests dropped from thread queue |
| `MAIN.sess_dropped` | 🔴 WARNING | Sessions dropped (older Varnish versions) |
| `MAIN.threads_limited` | 🟡 Caution | Thread pool at max during a spike |
| `MAIN.busy_killed` | 🟡 Caution | Requests killed while on wait-list |
| `MAIN.sess_queued` | 🟡 Caution | Sessions queued (thread starvation) |
| `MAIN.fetch_failed` | 🟡 Caution | Backend fetch failures |
| `*.nuked` | 🟡 Caution | Objects evicted under memory pressure |
| `*.waterlevel_queue` | 🟡 Caution | MSE eviction queue backing up |
| `*.waterlevel_purge` | 🟡 Caution | MSE forced purges due to watermark |

## Hit rate calculation

Collect these counters (use `grep` on `*varnishstat_-1*`):
- `MAIN.s_pass` (or `*.s_pass`) → passes
- `*.cache_hit ` (trailing space to avoid `cache_hitpass`) → hits
- `*.cache_miss` → misses
- `*.cache_hitpass` → hit-for-pass
- `*.cache_hitmiss` → hit-for-miss
- `*.s_pipe` → pipes
- `*.s_synth` → synths

Total = hits + misses + passes + pipes + hit-for-pass + hit-for-miss + synths

```
Hit rate      = hits / total * 100
Miss rate     = misses / total * 100
Pass rate     = passes / total * 100
HFP rate      = hit-for-pass / total * 100
HFM rate      = hit-for-miss / total * 100
Pipe rate     = pipes / total * 100
Synth rate    = synths / total * 100
Request rate  = per-second value from client_req line (3rd column)
```

## Busy threads / waitinglist occupancy

- Compute `busy_sleep − busy_wakeup` (if positive, objects are sitting on
  the waitinglist; a large sustained value indicates backend slowness or
  thread starvation).

## Pass buffer bloat

- Check the per-second rate (3rd column) of `Transient.c_bytes`.
  A high rate means large pass responses are flowing through Transient
  storage — this can cause memory pressure if transit_buffer is not
  configured.  Flag if the rate is consistently high relative to available
  memory.

## Cache storage

- `SMA.<name>.g_bytes` or `MSE*g_bytes` — bytes used
- `SMA.<name>.g_space` or `MSE*g_space` — bytes free
- `SMA.<name>.g_objects` or `MSE*g_objects` — object count

Report used/free in GB (value ÷ 1024³).

## Active bans

- Compute `bans − bans_completed` from `*varnishstat_-1*`.
  A large number of outstanding bans may indicate a ban lurker problem.

## Expiry queue

- Compute `exp_mailed − exp_received`.  If `exp_mailed > exp_received`,
  the expiry queue is backed up.

## jemalloc

Read `*jemalloc_stats`:
- `Version:` line
- `Allocated:`, `active:`, `mapped:` summary line
- `small:` / `large:` / `huge:` allocated bytes
- `assigned threads:` — jemalloc thread cache count
