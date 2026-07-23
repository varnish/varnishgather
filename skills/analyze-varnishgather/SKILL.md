---
name: analyze-varnishgather
description: Analyze a varnishgather diagnostic archive from a Varnish
  Cache/Enterprise server and produce a diagnostic report. Use when the
  user provides a varnishgather tarball or directory, or asks to analyze
  a "gather", check Varnish health, or troubleshoot from collected data.
allowed-tools:
  - Bash(${CLAUDE_SKILL_DIR}/scripts/vg-check *)
  - Bash(${CLAUDE_SKILL_DIR}/scripts/vg-log *)
  - Bash(tar xzf *)
  - Bash(awk *)
  - Bash(sort *)
  - Bash(uniq *)
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/guard-destructive"
---

# Analyzing a varnishgather

A varnishgather is a directory of small text files (plus a few binary
blobs) collected from a Varnish server for offline troubleshooting. This
skill walks you through extracting it, running the automated checks, and
producing a structured diagnostic report.

**Analysis is read-only.** The archive and anything extracted from it
are the user's case data: never delete, move, or modify them. Do not
clean up the extraction directory when you are done — leave that to the
user, and ask first if cleanup seems needed.

The official Varnish Enterprise troubleshooting guide at
https://docs.varnish-software.com/varnish-enterprise/troubleshooting/ is
an authoritative companion reference — it describes known issues, their
metrics/symptoms, and concrete remediation steps. Cross-reference it
whenever you flag a warning in the report.

## Getting started

If given a tarball:
```sh
tar xzf varnishgather.<id>.tar.gz
cd varnishgather-<id>/
```
If given a directory, just `cd` into it (name pattern:
`varnishgather-<hostname>-<YYYYMMDD-HHMMSS>[-name]`).

Verify you are in the right place:
```sh
head -5 varnishgather.log
# Should show: "Varnishgather version: X.XXX"
```

Most files are regular readable text. Never parse these as text:
- `varnishlog.raw` — binary VSL log
- `NNN_vcls.tar` — tar archive of all VCL files
- `NNN_irq.tar.gz` — compressed IRQ/interrupt data
- `NNN_modsec.tar` — ModSecurity config archive (if present)
- `perf.data` — perf record output (if `-p` was used)

## File naming convention

Every file is named `NNN_<sanitised-command>` (`NNN` = zero-padded item
number, rest = command/args with spaces and slashes replaced by `_`),
and starts with a 3-line banner:
```
--------------------------------
Item NNN: <original command>
--------------------------------
```
Item numbers shift between varnishgather versions, so always match by
glob (e.g. `*varnishstat_-1*`), never by hardcoded number. A file that
is **absent** means the command doesn't exist on that host (normal, not
an error). A file that exists but contains only the 3-line banner means
the command ran but produced no output.

## Workflow

1. **Run the automated checker first**:
   ```sh
   ${CLAUDE_SKILL_DIR}/scripts/vg-check <gather-dir>
   ```
   Always invoke the bundled scripts by this full path — it is what the
   skill's pre-approved permissions match, so the commands run without
   permission prompts.
   It works through the mechanical part of the warning checklist and
   prints one line per check (`WARN`, `CAUTION`, `OK`, `INFO`, or
   `SKIP` if the needed file is absent), followed by a summary line.
   Exit status 1 means at least one `WARN` was found; 2 means a usage
   error or the directory isn't a gather. Use this output to seed the
   "Critical findings" and "Warnings" sections of the report.
2. Work through `references/checks.md` section by section for
   everything `vg-check` does not automate (identity, running
   processes, installed packages, system resources, storage devices,
   VCL/backend/ban details, additional components, etc.).
3. Use `references/varnishstat.md` to interpret and explain the counter
   findings `vg-check` reports (severities, hit-rate math, storage
   sizing, jemalloc) and for any deeper manual `*varnishstat_-1*`
   analysis.
4. If `varnishlog.raw` is present, use the recipes in
   `references/varnishlog.md` via `${CLAUDE_SKILL_DIR}/scripts/vg-log`
   (it auto-selects a local `varnishlog`/`varnishncsa` install or spins
   up a version-matched Docker image otherwise).

## Warning checklist

Every row must be checked before finalising a report. `vg-check <id>`
means the row is automated (run vg-check as above and read its output);
otherwise follow the referenced file.

| # | Check | File(s) | Coverage |
|---|---|---|---|
| 1 | varnishd child died / panic in varnishstat | `*varnishstat_-1*` | `vg-check stat-counters` |
| 2 | Panic text present | `*panic_show` | `vg-check panic` |
| 3 | Sessions dropped / queued (`sess_drop`, `sess_dropped`, `req_dropped`) | `*varnishstat_-1*` | `vg-check stat-counters` |
| 4 | Thread failures or pool at limit | `*varnishstat_-1*` | `vg-check stat-counters` |
| 5 | Workspace overflow | `*varnishstat_-1*` | `vg-check stat-counters` |
| 6 | Disk overload (c_insert_timeout, aio_write_queue_overflow) | `*varnishstat_-1*` | `vg-check stat-counters` |
| 7 | OOM killer in system log | `*log_messages`, `*log_syslog` | `vg-check oom` |
| 8 | Transparent hugepages NOT set to `never` | `*hugepage_enabled` | `vg-check thp` |
| 9 | vm.max_map_count < 262144 | `*sysctl*` | `vg-check max-map-count` |
| 10 | `/var/lib/varnish` not on tmpfs | `*mount*` | `vg-check tmpfs` |
| 11 | thread_pool_add_delay ≠ 0 | `*param_show_changed` | `vg-check params` |
| 12 | workspace_client or workspace_backend > 128k | `*param_show_changed` | `vg-check params` |
| 13 | XKey imported alongside persistent MSE | `*varnishstat_-1*` + `*vcl_show*` | manual → `references/checks.md` |
| 14 | MSE database_sync not disabled | MSE config files | manual → `references/checks.md` |
| 15 | Sick backends | `*backend_list*` | `vg-check sick-backends` |
| 16 | Network TX/RX errors > 10% | `*ip_-s_l` | `vg-check net-errors` |
| 17 | varnishd run with `-n` but gather collected without `-n` | `*ps_aux*` vs `*param_show*` filename | manual → `references/checks.md` |
| 18 | Child uptime much less than management uptime | `*varnishstat_-1*` | `vg-check child-restart` |
| 19 | High `Transient.c_bytes` rate (pass buffer bloat) | `*varnishstat_-1*` | `references/varnishstat.md` |
| 20 | MSE waterlevel_queue / waterlevel_purge non-zero | `*varnishstat_-1*` | `vg-check stat-counters` |
| 21 | Open FD count above ~80% of the limit | `*lsof_-p*` + `*limits` | `vg-check fd-usage` |

`vg-check` additionally reports `expiry-queue`, `bans`, `waitinglist`,
and `hit-rate` (as `INFO`), and `disk-usage` (filesystems over 85%
full) — fold these into the report even though they aren't numbered
rows above.

## Report structure

**Lead with the most critical findings.** A reader should be able to
see whether there is an active crisis in the first few lines of the
report. Run the full warning checklist above before writing anything
else, then open with the results.

A good analysis report should contain these sections in order:

1. **Critical findings** — panics, child restarts, dropped sessions,
   thread failures, OOM events, sick backends; anything from the
   checklist that is 🔴 WARNING severity. If there are none, say so
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

## Tips

- Use glob patterns without item numbers (`*varnishstat_-1*`, not
  `060_varnishstat_-1`) — numbers shift between gather versions.
- Each file starts with the 3-line banner; skip it (or `grep` past it)
  when parsing programmatically.
- Missing files are normal — a command absent from the target host is
  silently skipped and its output file never created.
- Some files are per-PID (`*proc_<pid>_*`); expect multiple matches if
  there are multiple varnishd processes.
- `varnishlog.raw` is binary — never `cat`/`grep` it; go through
  `scripts/vg-log`.
- Some fields are redacted by design (`/etc/varnish/secret` is never
  collected, `_PASS` is stripped from brainz systemd config) — treat
  their absence as expected, not a finding.
