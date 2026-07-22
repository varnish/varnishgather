# Section-by-section checks

Work through these sections in order to build the report. The companion script
`scripts/vg-check` automates the mechanical warning checks — where a check below
is automated, it is marked `[automated: vg-check <id>]`. Still read the
surrounding guidance to interpret and explain results.

## Identity

| What to read | Glob pattern |
|---|---|
| Varnish version | `*varnishd_-V` |
| Hostname | `*hostname` |
| OS | `*lsb_release*` or `*redhat-release` or `*os-release` |
| Kernel | `*uname_-a` |
| Capture date | `*date` |
| Varnishgather version | `varnishgather.log` (first line) |

Summarise: version string, hostname, OS+kernel, date of capture.

## Running processes

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

## Installed packages

Read `*dpkg_--list*` (Debian/Ubuntu) and/or `*rpm_--query_--all*` (RHEL).
List all varnish-related packages with their versions.  Key packages:
`varnish`, `varnish-plus`, any `vmod-*`, `hitch`, `vha-agent`, `gcc`.

## System resources

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

## Storage

- `*df_-h` — disk usage; flag any filesystem over 85% full.
  [automated: vg-check disk-usage]
- `*mount*` — check if `/var/lib/varnish` is mounted as `tmpfs`.
  [automated: vg-check tmpfs]
  ⚠️ If it is **not** tmpfs, flag it: the shared memory log should be
  on tmpfs for performance; see
  https://docs.varnish-software.com/varnish-enterprise/installation/#the-shared-memory-log
- `*lsblk` and `*blockdev_info*` — storage device info.
- `*lvdisplay*`, `*vgdisplay*`, `*pvdisplay*` — LVM info if present.

## Kernel / OS checks

**Transparent Huge Pages** — read `*hugepage_enabled` (maps to
`/sys/kernel/mm/transparent_hugepage/enabled`).
[automated: vg-check thp]
⚠️ If the value does not contain `[never]`, THP is enabled — flag it.
Reference: https://docs.varnish-software.com/varnish-enterprise/installation/#transparent-huge-pages-thp

**vm.max_map_count** — read `*sysctl*`, find `vm.max_map_count`.
[automated: vg-check max-map-count]
⚠️ If the value is less than **262144**, flag it.
Reference: https://docs.varnish-software.com/varnish-enterprise/installation/#maximum-memory-maps

**dmesg / system log** — read `*dmesg*` and `*log_messages` /
`*log_syslog` and look for:
- `oom-killer` → memory pressure, flag as WARNING
  [automated: vg-check oom]
- `Child (` — varnishd child process events; report last 10 lines
- `varnish`, `hitch`, `broadcaster`, `vha-agent` error messages

**SELinux** — read `*getenforce`, `*semodule*`, `*semanage*`.
If SELinux is enforcing, note it; AVC denials would appear in `*ausearch*`.

**Network errors** — read `*ip_-s_l`.  For each interface, find the
`RX:` and `TX:` statistics lines.  The columns are:
`bytes  packets  errors  dropped  missed  mcast`.
[automated: vg-check net-errors]
⚠️ If errors/packets > 10% for any interface, flag it.

**ulimits / process limits** — read `*limits` (maps to
`/proc/<varnishd-pid>/limits`).  Check that open files and max processes
are not at low defaults.

**Open file descriptors** — read `*lsof_-p*` (one file per varnishd PID).
[automated: vg-check fd-usage]
Count the lines to get the current FD count and compare it against the
`Max open files` value from `*limits`.  If the count is above ~80% of the
limit, flag it.

**IRQ affinity** — read `*irq*` (the IRQ tarball captured from
`/proc/interrupts` and `/proc/irq/`).  On high-traffic servers, check that
network interface interrupts are spread across CPUs rather than pinned to
a single core.

## Varnish parameters

Read `*param_show_changed` for non-default parameter values.

Key parameters to highlight and check:

| Parameter | Check |
|---|---|
| `thread_pool_min` / `thread_pool_max` | Note values |
| `thread_pool_add_delay` | ⚠️ Should be `0` — flag if non-zero [automated: vg-check params] |
| `workspace_client` | ⚠️ Flag if greater than `128k` [automated: vg-check params] |
| `workspace_backend` | ⚠️ Flag if greater than `128k` [automated: vg-check params] |
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

## VCL analysis

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
  [automated: vg-check sick-backends]

Read `*ban_list`:
- Report how many bans are present
- If there are active bans, quote the most recent few

**MSE database_sync check:**
⚠️ If varnishd is running with an MSE storage (`mse,` in cmdline) and
`database_sync` is not set to `false` in the MSE config files
(`*mse*`, `*conf*`), flag it.
Reference: https://docs.varnish-software.com/varnish-cache-plus/features/mse/settings/#database-sync

## Panic

Read `*panic_show`:
[automated: vg-check panic]
- If it contains `Panic at`, a panic has occurred — print the full
  panic text verbatim; this is high-priority information.
- If it says `Child has not panicked or panic has been cleared`, report
  no panic.

## varnishscoreboard

Read `*varnishscoreboard`.  This is a snapshot of all worker thread slots
showing their current state (idle, working, waiting, etc.).  It gives a
quick visual picture of thread pool saturation at the moment the gather
was taken.  A large number of slots in a non-idle state (especially
`wait` or `bereq`) alongside elevated `threads_limited` or `sess_queued`
counters indicates a thread pool or backend bottleneck.

## Additional components

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
