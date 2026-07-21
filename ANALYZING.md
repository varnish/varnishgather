# ANALYZING.md — how to analyze a varnishgather

This document tells you how to read a varnishgather and produce a useful
diagnostic report without needing any external analysis script.

The official Varnish Enterprise troubleshooting guide at
https://docs.varnish-software.com/varnish-enterprise/troubleshooting/
is an authoritative companion reference — it describes known issues,
their metrics/symptoms, and concrete remediation steps.  Cross-reference
it whenever you flag a warning in your report.

---

## 1. Getting started

A gather is delivered as a `.tar.gz` archive or as a directory that has
already been extracted.

**If you have a tarball:**
```sh
tar xzf varnishgather.<id>.tar.gz
cd varnishgather-<id>/
```

**If you already have a directory:** just `cd` into it.  The directory
name follows the pattern `varnishgather-<hostname>-<YYYYMMDD-HHMMSS>[-name]`.

Verify you are in the right place:
```sh
cat varnishgather.log | head -5
# Should show: "Varnishgather version: X.XXX"
```

Once extracted, most files in the directory are regular readable text files.
Exceptions — do not try to parse these as text:
- `varnishlog.raw` — binary VSL log
- `NNN_vcls.tar` — tar archive of all VCL files
- `NNN_irq.tar.gz` — compressed archive of IRQ/interrupt data
- `NNN_modsec.tar` — ModSecurity config archive (if present)
- `perf.data` — perf record output (if `-p` was used)

No special permissions are needed to read the text files — just open and
parse them directly.

---

## 2. File naming convention

Every file in the directory is named `NNN_<sanitised-command>`, where
`NNN` is a zero-padded item number.  The rest of the filename is the
command and its arguments with spaces and slashes replaced by `_`.

Examples:
- `001_varnishd_-V` — output of `varnishd -V`
- `060_varnishstat_-1` — output of `varnishstat -1`
- `525_varnishadm_--_param_show_changed` — output of `varnishadm param.show changed`
- `503_varnishadm_--_vcl_list` — output of `varnishadm vcl.list`

Each file begins with a small log header like:
```
--------------------------------
Item NNN: <original command>
--------------------------------
```
The actual command output follows.

When a command was not found or a file was not readable, the output file is
**absent** (never created — the script increments the counter and returns
without opening any file).  A file that exists but contains only the 3-line
banner means the command ran but produced no output.  Use glob patterns like
`*varnishstat_-1*` to find files without needing to know the exact item
number — numbers shift between gather versions.

---

## 3. Producing a report — section by section

Work through the sections below in order.  Flag anything that matches
the WARNING conditions described.

### 3.1 Identity

| What to read | Glob pattern |
|---|---|
| Varnish version | `*varnishd_-V` |
| Hostname | `*hostname` |
| OS | `*lsb_release*` or `*redhat-release` or `*os-release` |
| Kernel | `*uname_-a` |
| Capture date | `*date` |
| Varnishgather version | `varnishgather.log` (first line) |

Summarise: version string, hostname, OS+kernel, date of capture.

### 3.2 Running processes

Read `*ps_aux*` and look for:

| Process | Pattern to grep |
|---|---|
| varnishd | `varnishd ` |
| MSE3 | `mse,` |
| MSE4 | `mse4,` |
| Hitch (TLS) | `hitch ` |
| VHA (legacy) | `vha-agent  ` |
| VHA6 | presence of `vha6_stats` in `*varnishstat_-1*` |
| VAC | `vac.jar` |
| varnish-agent | `varnish-agent` |
| VCS/vstatd | `vcs \|vstatd ` |
| Broadcaster | `broadcaster ` |
| Varnish Controller | `varnish-controller-*` |

Also check for containerisation:
- `*_cgroup` containing `kubepods` → running in Kubernetes
- `*_cgroup` containing `docker` → running in Docker

**varnishd command line:** read `*ps_aux*`, isolate the line with
`varnishd ` (not `grep varnishd`).  Print the arguments one per line.
Key arguments to highlight: `-n`, `-s` (storage), `-T`, `-M`, `-a`,
`-p`, `-f`.

### 3.3 Installed packages

Read `*dpkg_--list*` (Debian/Ubuntu) and/or `*rpm_--query_--all*` (RHEL).
List all varnish-related packages with their versions.  Key packages:
`varnish`, `varnish-plus`, any `vmod-*`, `hitch`, `vha-agent`, `gcc`.

### 3.4 System resources

**Memory** — read `*proc_meminfo`:
```
MemTotal, MemFree, Buffers, Cached, MemAvailable, SwapTotal, SwapFree
```
Compute used = MemTotal − MemFree − Buffers − Cached.  Report total,
used, available, and swap usage.  Also read `*proc_*_status` (for the
`cache-main` process) for `VmRSS`, `VmSize`, `RssFile`.

**CPU** — count processors from `*proc_cpuinfo` (`grep ^processor | wc -l`).

**Load** — read `*uptime`.  High load (> CPU count) is worth flagging.

**Top processes by memory** — read `*ps_axo*pmem*head*`.

**vmstat** — read `*vmstat*` for context switches and I/O wait trends.

### 3.5 Storage

- `*df_-h` — disk usage; flag any filesystem over 85% full.
- `*mount*` — check if `/var/lib/varnish` is mounted as `tmpfs`.
  ⚠️ If it is **not** tmpfs, flag it: the shared memory log should be
  on tmpfs for performance; see
  https://docs.varnish-software.com/varnish-enterprise/installation/#the-shared-memory-log
- `*lsblk` and `*blockdev_info*` — storage device info.
- `*lvdisplay*`, `*vgdisplay*`, `*pvdisplay*` — LVM info if present.

### 3.6 Kernel / OS checks

**Transparent Huge Pages** — read `*hugepage_enabled` (maps to
`/sys/kernel/mm/transparent_hugepage/enabled`).
⚠️ If the value does not contain `[never]`, THP is enabled — flag it.
Reference: https://docs.varnish-software.com/varnish-enterprise/installation/#transparent-huge-pages-thp

**vm.max_map_count** — read `*sysctl*`, find `vm.max_map_count`.
⚠️ If the value is less than **262144**, flag it.
Reference: https://docs.varnish-software.com/varnish-enterprise/installation/#maximum-memory-maps

**dmesg / system log** — read `*dmesg*` and `*log_messages` /
`*log_syslog` and look for:
- `oom-killer` → memory pressure, flag as WARNING
- `Child (` — varnishd child process events; report last 10 lines
- `varnish`, `hitch`, `broadcaster`, `vha-agent` error messages

**SELinux** — read `*getenforce`, `*semodule*`, `*semanage*`.
If SELinux is enforcing, note it; AVC denials would appear in `*ausearch*`.

**Network errors** — read `*ip_-s_l`.  For each interface, find the
`RX:` and `TX:` statistics lines.  The columns are:
`bytes  packets  errors  dropped  missed  mcast`.
⚠️ If errors/packets > 10% for any interface, flag it.

**ulimits / process limits** — read `*limits` (maps to
`/proc/<varnishd-pid>/limits`).  Check that open files and max processes
are not at low defaults.

**Open file descriptors** — read `*lsof_-p*` (one file per varnishd PID).
Count the lines to get the current FD count and compare it against the
`Max open files` value from `*limits`.  If the count is above ~80% of the
limit, flag it.

**IRQ affinity** — read `*irq*` (the IRQ tarball captured from
`/proc/interrupts` and `/proc/irq/`).  On high-traffic servers, check that
network interface interrupts are spread across CPUs rather than pinned to
a single core.

### 3.7 Varnish parameters

Read `*param_show_changed` for non-default parameter values.

Key parameters to highlight and check:

| Parameter | Check |
|---|---|
| `thread_pool_min` / `thread_pool_max` | Note values |
| `thread_pool_add_delay` | ⚠️ Should be `0` — flag if non-zero |
| `workspace_client` | ⚠️ Flag if greater than `128k` |
| `workspace_backend` | ⚠️ Flag if greater than `128k` |
| `vsl_space` | Note value; used to size `/var/lib/varnish` tmpfs |
| `transit_buffer` | Note if set |
| `pipe_timeout` | Flag if very high (>300s without good reason) |
| `connect_timeout` | Note value |
| `cc_command` | Note if customised (indicates custom VCL compiler) |

For `workspace_client` and `workspace_backend`: the unit is appended
(`k`=KB, `m`=MB, `g`=GB).  Values above 128k indicate a deliberate
override — warn the user, as large workspaces can cause memory pressure
under high concurrency.

Also read `*param_show` (full, not just changed) if you need to look up
a specific parameter's current value.

### 3.8 varnishstat analysis

Read `*varnishstat_-1*`.  Each line has the format:
```
STAT.counter    cumulative_value    per_second_rate    description
```

**Uptime:**
- `MGT.uptime` — management process uptime (seconds)
- `MAIN.uptime` — child process uptime; if much less than MGT.uptime, the child restarted

**Critical counters — flag any that are non-zero:**

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

**Hit rate calculation:**

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

**Busy threads / waitinglist occupancy:**
- Compute `busy_sleep − busy_wakeup` (if positive, objects are sitting on
  the waitinglist; a large sustained value indicates backend slowness or
  thread starvation).

**Pass buffer bloat:**
- Check the per-second rate (3rd column) of `Transient.c_bytes`.
  A high rate means large pass responses are flowing through Transient
  storage — this can cause memory pressure if transit_buffer is not
  configured.  Flag if the rate is consistently high relative to available
  memory.

**Cache storage:**
- `SMA.<name>.g_bytes` or `MSE*g_bytes` — bytes used
- `SMA.<name>.g_space` or `MSE*g_space` — bytes free
- `SMA.<name>.g_objects` or `MSE*g_objects` — object count

Report used/free in GB (value ÷ 1024³).

**Active bans:**
- Compute `bans − bans_completed` from `*varnishstat_-1*`.
  A large number of outstanding bans may indicate a ban lurker problem.

**Expiry queue:**
- Compute `exp_mailed − exp_received`.  If `exp_mailed > exp_received`,
  the expiry queue is backed up.

**jemalloc** — read `*jemalloc_stats`:
- `Version:` line
- `Allocated:`, `active:`, `mapped:` summary line
- `small:` / `large:` / `huge:` allocated bytes
- `assigned threads:` — jemalloc thread cache count

### 3.9 VCL analysis

Read `*vcl_list`:
- Count lines by first column: `active` (should be 1), `available`, `discarded`
- Count by second column state: `label`, `warm`, `cold`
- Note the name of the active VCL (first column = `active`, 4th field)

Find the corresponding `vcl_show` file: `*vcl_show*<active-vcl-name>*`.

From the VCL show output, parse the `VCL.SHOW` log tag lines to extract
the file sections.  For each non-builtin, non-vha6 section:
- Collect all `import <vmod>;` statements → list of VMODs in use
- Count lines of VCL code
- Count number of VCL source files

**XKey + persistent MSE cohabitation:**
⚠️ If `*varnishstat_-1*` contains `MSE_BOOK` and any `*vcl_show*` file
contains `import xkey`, flag it — long startup times may result.
Reference: https://docs.varnish-software.com/varnish-cache-plus/vmods/ykey/#xkey

Read `*backend_list*`:
- List backends and their probe health
- ⚠️ Flag any backend that is `Sick`

Read `*ban_list`:
- Report how many bans are present
- If there are active bans, quote the most recent few

**MSE database_sync check:**
⚠️ If varnishd is running with an MSE storage (`mse,` in cmdline) and
`database_sync` is not set to `false` in the MSE config files
(`*mse*`, `*conf*`), flag it.
Reference: https://docs.varnish-software.com/varnish-cache-plus/features/mse/settings/#database-sync

### 3.10 Panic

Read `*panic_show`:
- If it contains `Panic at`, a panic has occurred — print the full
  panic text verbatim; this is high-priority information.
- If it says `Child has not panicked or panic has been cleared`, report
  no panic.

### 3.11 varnishlog analysis

The file `varnishlog.raw` is a binary VSL log file captured with
`varnishlog -d -g raw -w`.  If `varnishlog` is available in `PATH`,
you can read it:

```sh
# Count client requests
varnishlog -r varnishlog.raw -c -i ReqStart | grep ReqStart | wc -l

# Time span
varnishlog -r varnishlog.raw -c -i Timestamp | grep "Start:" | head -1
varnishlog -r varnishlog.raw -c -i Timestamp | grep "Start:" | tail -1

# Average hit response time (seconds)
varnishlog -r varnishlog.raw -c \
  -q "ReqMethod eq GET and VCL_call eq HIT" -i Timestamp | grep Resp: | \
  awk '{t+=$5} END{print t/(NR+0.0000001) " seconds (count: " NR ")"}'

# Average miss response time (seconds)
varnishlog -r varnishlog.raw -c \
  -q "ReqMethod eq GET and VCL_call eq MISS" -i Timestamp | grep Resp: | \
  awk '{t+=$5} END{print t/(NR+0.0000001) " seconds (count: " NR ")"}'

# Average waitinglist delay (object coalescing / backend saturation)
varnishlog -r varnishlog.raw -c \
  -q "ReqMethod eq GET and Timestamp:Waitinglist" -i Timestamp | grep Waitinglist: | \
  awk '{t+=$5} END{print t/(NR+0.0000001) " seconds (count: " NR ")"}'

# VHA6 cluster requests
varnishlog -r varnishlog.raw -c -q "ReqMethod ~ VHA" -i ReqStart | grep ReqStart | wc -l

# Error lines (excluding benign noise)
varnishlog -r varnishlog.raw -g raw | grep -i error | \
  grep -Eiv "vha6|RespReason|Timestamp|Cache-Control|pHeader|qHeader|qURL"

# Transactions with 0s TTL (cacheability problem candidates)
varnishlog -r varnishlog.raw -b \
  -q "Begin[3] ne pass and VCL_return eq deliver" -i TTL | awk '$2=="TTL" && $4==0'

# Fetch performance broken down by storage stevedore
varnishlog -r varnishlog.raw -b -i Timestamp -i Storage | awk '
  {
    if ($2=="Storage") { s = $3"_"$4 }
    else if ($3=="BerespBody:") { t[s]+=$5; c[s]++ }
  }
  END { for(s in t) printf "%-25s %f seconds (count: %d)\n", s":", t[s]/(c[s]+0.0000001), c[s] }'
```

**Using Docker when `varnishlog` is not installed locally:**

If the Varnish tools are not available in your `PATH`, run them via
Docker using an image that matches the version found in `*varnishd_-V`.

1. **Extract the version** from `001_varnishd_-V` (or whichever file
   matches `*varnishd_-V`):
   ```
   varnishd (varnish-plus-6.0.16r12 revision ...)   → Enterprise build
   varnishd (varnish-7.6.2 revision ...)             → Open-source build
   ```

2. **Choose the image:**
   - Enterprise (`varnish-plus-*`): `varnish/varnish-enterprise:<version>`
     e.g. `varnish/varnish-enterprise:6.0.16r12`
   - Open-source: `varnish:<version>`
     e.g. `varnish:7.6.2`

3. **Mount the gather directory** with `-v` so the container can read
   `varnishlog.raw`:
   ```sh
   # Replace IMAGE as determined above
   IMAGE=varnish/varnish-enterprise:6.0.16r12   # or varnish:X.Y.Z
   GATHER=$PWD   # must be the extracted gather directory

   # Full request/response view grouped by request
   docker run --rm -v "$GATHER:/gather" $IMAGE \
     varnishlog -r /gather/varnishlog.raw -g request

   # Client requests only
   docker run --rm -v "$GATHER:/gather" $IMAGE \
     varnishlog -r /gather/varnishlog.raw -c

   # Filter to a specific URL or header
   docker run --rm -v "$GATHER:/gather" $IMAGE \
     varnishlog -r /gather/varnishlog.raw -g request \
       -q 'ReqURL ~ "/api/v1/repos"'

   # JSON output — Enterprise image only (varnish/varnish-enterprise:*)
   docker run --rm -v "$GATHER:/gather" $IMAGE \
     varnishlog-json -r /gather/varnishlog.raw
   ```

   Typical use-cases:
   - **`varnishlog -r -g request`** — shows each transaction as a
     grouped block; best for debugging individual requests.
   - **`varnishlog -r -g request -q '…'`** — filter to specific
     transactions using VSL query syntax.
   - **`varnishlog-json -r`** — structured JSON output; easier to parse
     programmatically or pipe into `jq`.  **Enterprise image only** —
     not available in the `varnish:*` OSS image.

### 3.12 varnishscoreboard

Read `*varnishscoreboard`.  This is a snapshot of all worker thread slots
showing their current state (idle, working, waiting, etc.).  It gives a
quick visual picture of thread pool saturation at the moment the gather
was taken.  A large number of slots in a non-idle state (especially
`wait` or `bereq`) alongside elevated `threads_limited` or `sess_queued`
counters indicates a thread pool or backend bottleneck.

### 3.13 Additional components

**VHA6 (High Availability):**
- Check `*varnishstat_-1*` for `vha6_stats.*error` counters.
- Read `*vha-agent_-V` or `*vcs-agent_*` for version info.
- Read `*nodes_conf*` for cluster node configuration.

**Hitch (TLS terminator):**
- Read `*hitch_conf` for configuration.
- Check `/var/log` messages for `hitch` errors.

**Broadcaster:**
- Check `*broadcaster_-V` for version.
- Read `*nodes_conf*` for group/node counts.
- Check system log for `broadcaster.*ERROR` and `broadcaster.*WARNING`.

**Varnish Controller:**
- Check `*varnish-controller-*-version` files for version.
- Check system log for `ERROR`/`WARNING` messages per component
  (`agent`, `brainz`, `api-gw`, `ui`).

**api-engine:**
If the directory `/etc/api-engine` existed on the server, the gather
includes api-engine logs and config.  Read:
- `*api-engine-rest_log` and `*api-engine-sync_log` for errors
- `*api-engine-rest_cfg` and `*api-engine-syncutil_cfg` for configuration
- `*current_vcl` for the generated VCL being served

---

## 4. Warning checklist summary

Run through all of these before finalising your report:

| # | Check | File(s) |
|---|---|---|
| 1 | varnishd child died / panic in varnishstat | `*varnishstat_-1*` |
| 2 | Panic text present | `*panic_show` |
| 3 | Sessions dropped / queued (`sess_drop`, `sess_dropped`, `req_dropped`) | `*varnishstat_-1*` |
| 4 | Thread failures or pool at limit | `*varnishstat_-1*` |
| 5 | Workspace overflow | `*varnishstat_-1*` |
| 6 | Disk overload (c_insert_timeout, aio_write_queue_overflow) | `*varnishstat_-1*` |
| 7 | OOM killer in system log | `*log_messages`, `*log_syslog` |
| 8 | Transparent hugepages NOT set to `never` | `*hugepage_enabled` |
| 9 | vm.max_map_count < 262144 | `*sysctl*` |
| 10 | `/var/lib/varnish` not on tmpfs | `*mount*` |
| 11 | thread_pool_add_delay ≠ 0 | `*param_show_changed` |
| 12 | workspace_client or workspace_backend > 128k | `*param_show_changed` |
| 13 | XKey imported alongside persistent MSE | `*varnishstat_-1*` + `*vcl_show*` |
| 14 | MSE database_sync not disabled | MSE config files |
| 15 | Sick backends | `*backend_list*` |
| 16 | Network TX/RX errors > 10% | `*ip_-s_l` |
| 17 | varnishd run with `-n` but gather collected without `-n` | `*ps_aux*` vs `*param_show*` filename |
| 18 | Child uptime much less than management uptime | `*varnishstat_-1*` |
| 19 | High `Transient.c_bytes` rate (pass buffer bloat) | `*varnishstat_-1*` |
| 20 | MSE waterlevel_queue / waterlevel_purge non-zero | `*varnishstat_-1*` |
| 21 | Open FD count above ~80% of the limit | `*lsof_-p*` + `*limits` |

---

## 5. Report structure

**Lead with the most critical findings.**  A reader should be able to
see whether there is an active crisis in the first few lines of the
report.  Run the full warning checklist (section 4) before writing
anything else, then open with the results.

A good analysis report should contain these sections in order:

1. **Critical findings** — panics, child restarts, dropped sessions,
   thread failures, OOM events, sick backends; anything from the
   checklist that is 🔴 WARNING severity.  If there are none, say so
   explicitly ("No critical issues found").
2. **Warnings** — 🟡 Caution items from the checklist and any
   configuration issues (THP, vm.max_map_count, tmpfs, workspace sizes,
   etc.) with a brief explanation and reference URL for each.
3. **Identity** — version, hostname, OS, kernel, capture date
4. **Running components** — what is installed and running
5. **System resources** — memory, CPU count, load, swap
6. **varnishstat summary** — uptime, request rate, hit/miss/pass rates, cache size
7. **VCL summary** — active VCL name, VMODs in use, VCL file count/LOC
8. **Backend health** — full backend list with probe status
9. **Bans** — active ban count
10. **varnishlog highlights** — if raw log is available: request count, time span, average hit/miss times, error count, 0s-TTL candidates
11. **Recommendations** — concrete action items ranked by severity.
    For each flagged issue, link to the relevant section of
    https://docs.varnish-software.com/varnish-enterprise/troubleshooting/
    where it exists.

---

## 6. Tips

- **Use glob patterns without item numbers** — numbers shift between
  gather versions.  Use `*varnishstat_-1*`, not `060_varnishstat_-1`.
- **Each file starts with a header block** — skip the first 3 lines (the
  `---` banner) when parsing programmatically, or just grep past them.
- **Missing files are normal** — many probes run commands that don't exist
  on the target system.  If a command was not in `PATH`, the script
  silently skips it and the output file is never created (absent).  A file
  that exists but contains only the 3-line header banner means the command
  ran but produced no output.
- **Multiple PIDs** — some files are per-PID (`*proc_<pid>_*`).  If
  there are multiple varnishd processes, there will be multiple such
  files.
- **varnishlog.raw is binary** — do not try to read it with `cat` or
  `grep`; use `varnishlog -r varnishlog.raw`.
- **Redacted fields** — the gather script intentionally omits
  `/etc/varnish/secret` and uses `grep -v _PASS` on brainz systemd
  config; some fields may be absent by design.
