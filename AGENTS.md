# AGENTS.md — guidance for AI coding agents

## Repository overview

`varnishgather` is a single POSIX shell script that collects diagnostic
information from a running Varnish Cache server and packages it into a
`.tar.gz` archive.  There is no build system, no compiled code, and no
automated test suite.  The entire codebase is:

| File | Purpose |
|------|---------|
| `varnishgather` | The script itself (the only deliverable) |
| `README.rst` | User-facing documentation |
| `ANALYZING.md` | How to analyze a gather and produce a diagnostic report |
| `packaging/` | RPM/Debian packaging metadata |

---

## Design constraints — read before changing anything

1. **POSIX `sh` only.**  The shebang is `#!/bin/sh`.  Do not use bash
   extensions: no `[[ ]]`, no `$(( ))` arithmetic beyond what POSIX
   guarantees, no `local`, no arrays, no `$'...'` quoting, no process
   substitution `<(...)`.  Run `shellcheck --shell=sh varnishgather` to
   check.

2. **Non-invasive.**  The script is meant to be safe to run on production
   Varnish servers.  Do not add anything that writes to Varnish state,
   flushes caches, changes configuration, or has lasting side-effects.

3. **Silent-skip for missing commands.**  `run()` calls `command -v`
   before executing; if the binary is absent it increments the item
   counter and returns silently.  New data-collection steps should use
   `run` or `mycat` so they behave the same way on systems where the
   relevant tool or file is absent.

4. **Numbered output files.**  Every item written to the output directory
   carries a zero-padded three-digit prefix (`001_`, `002_`, …) via
   `item_num()`.  The counter `ITEM` is incremented by `incr()`.  Any
   new collection step that skips execution must still call `incr` so the
   numbering stays consistent and diffs between runs remain meaningful.

---

## Key functions

| Function | Description |
|----------|-------------|
| `run CMD [ARGS…]` | Run a command; write stdout+stderr to a numbered file named after the command. Skips silently if the binary is not in `PATH`. |
| `runpipe CMD1 CMD2 …` | Run a shell pipeline; each element is a separate argument. |
| `mycat FILE` | Capture a file with `run cat FILE`; if the file is unreadable, increments the counter and does nothing. |
| `vadmin SUBCMD [ARGS…]` | Run `varnishadm` with the deduced admin arguments. No-ops if no admin port was found. |
| `vadmin_getvcls` | Returns the list of loaded VCL names via `varnishadm vcl.list`. |
| `vcl_find` | Discovers all VCL files (search paths + inline includes) and prints their absolute paths. |
| `vcl_find_includes VCL` | Recursively resolves `include` directives inside a VCL file. |
| `pack_vcls` | Tars all discovered VCL files into a single archive entry. |
| `foreacharg OPT` | Reads `/proc/<pid>/cmdline` for each varnishd PID and prints the value of argument `OPT`. |
| `show_packages PKG…` | Runs both `dpkg` and `rpm` queries for the given package globs (one of them will fail silently on any given distro). |
| `show_limits` | Captures `/proc/<varnishd-pid>/limits`. |
| `call_blockdev PATH` | Captures block-device queue parameters from sysfs for a device. |
| `upload` | POSTs the finished tarball to `filebin.varnish-software.com` via `curl`. |
| `list_names` | Discovers all running varnishd `-n` names by reading `/proc/*/cmdline`. |
| `get_pid` | Falls back to scanning `/proc` when `pidof`/`pgrep` are unavailable. |
| `logname ARGS…` | Sanitises a command string into a safe filename fragment. |

---

## Adding a new data-collection step

1. Decide where in the script the new step fits logically (system info,
   Varnish-specific, logs, etc.).
2. Use `run`, `runpipe`, or `mycat` — do **not** write bare shell
   commands that redirect to files yourself.
3. If the step collects data for every varnishd PID, loop over
   `$PID_ALL_VARNISHD` or `$PID_VARNISHD` as existing loops do.
4. If the step needs a Varnish admin command, use `vadmin`.
5. Do not add a step that requires root and will crash (not just warn)
   when run as a non-root user.  The script already warns the user and
   continues.

---

## Validating changes

There is no automated test suite.  Validate changes with:

```sh
# Lint (install shellcheck if needed)
shellcheck --shell=sh varnishgather

# Smoke-test: run against a live Varnish instance
sudo sh ./varnishgather -h          # should print usage and exit 0
sudo sh ./varnishgather             # should produce varnishgather.*.tar.gz

# Inspect the archive
tar tzvf varnishgather.*.tar.gz | head -40
```

If no Varnish instance is available, verify at minimum that
`shellcheck` reports no errors and that `sh -n varnishgather` (syntax
check) exits 0.

---

## Things to avoid

- **Do not add `bash`-only syntax.**  Always test with `shellcheck --shell=sh`.
- **Do not hardcode PIDs or timestamps** in logic; use the existing
  `$PID_VARNISHD` / `$PID_CACHEMAIN` / `$PID_ALL_VARNISHD` variables.
- **Do not capture secrets.**  The script deliberately excludes
  `/etc/varnish/secret`; do not add steps that would capture secret
  files, passwords, or private keys.
- **Do not change the `VERSION` string** unless you are bumping it as
  part of a deliberate release commit.
- **Do not reorder the `incr` call** relative to the actual work inside
  custom collection blocks — the item counter must advance exactly once
  per logical item regardless of whether the item was skipped.
