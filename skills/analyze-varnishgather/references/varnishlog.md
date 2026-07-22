# varnishlog / varnishncsa analysis

`varnishlog.raw` is a binary VSL capture (written with `varnishlog -d -g
raw -w`); never `cat`/`grep` it directly. All recipes below use the
companion wrapper `scripts/vg-log`, which picks a local tool when
available or a docker container matching the gather's Varnish version
otherwise.

## Running the tools

```
vg-log [-m auto|local|docker] [-t log|ncsa|json] [-g GATHER_DIR] [-n] [--] EXTRA_ARGS...
```

- `-m` mode (default `auto`: local tool if in `PATH`, docker otherwise;
  docker image is derived from the gather's `*varnishd_-V` —
  `varnish/varnish-enterprise:<ver>` for varnish-plus builds,
  `varnish:<ver>` for open source)
- `-t` tool: `log` = varnishlog, `ncsa` = varnishncsa, `json` =
  varnishlog-json (Enterprise only)
- `-g` gather directory containing `varnishlog.raw` (default `.`)
- `-n` dry-run (print the command)
- args after `--` go straight to the underlying tool (`-q`, `-F`, `-i`,
  `-c`, `-b`, ...)

## varnishncsa recipes

`varnishncsa -F` prints exactly the requested fields, so pipelines that
merely extract a value from `varnishlog` output become much simpler.
Useful format fields:

- `%{Varnish:handling}x` — hit/miss/pass/synth/pipe
- `%{Varnish:time_firstbyte}x` — seconds to first byte
- `%D` — full request duration in microseconds
- `%t` — timestamp
- `%s` — status
- `%U%q` — URL

Note: varnishncsa by default logs client transactions; `time_firstbyte`
is time-to-first-byte, whereas the old `Timestamp:Resp` recipes measured
full response time. Use `%D` (microseconds) as the full-duration
equivalent.

```sh
# Count client requests
vg-log -t ncsa -- -F '%{Varnish:handling}x' | wc -l

# Count by handling class
vg-log -t ncsa -- -F '%{Varnish:handling}x' | sort | uniq -c

# Time span
vg-log -t ncsa -- -F '%t' | head -1
vg-log -t ncsa -- -F '%t' | tail -1

# Average hit/miss response time (time-to-first-byte, seconds) + handling distribution
vg-log -t ncsa -- -F '%{Varnish:handling}x %{Varnish:time_firstbyte}x' | awk '
  {
    t[$1]+=$2; c[$1]++; total++
  }
  END {
    for (h in c) printf "%-6s avg %f seconds (count: %d)\n", h":", t[h]/(c[h]+0.0000001), c[h]
    print "---"
    for (h in c) printf "%-6s %.2f%%\n", h":", 100*c[h]/(total+0.0000001)
  }'
```

For the full request duration (as opposed to time-to-first-byte),
replace `%{Varnish:time_firstbyte}x` with `%D` in the pipeline above
(remember `%D` is in microseconds, not seconds).

## varnishlog recipes

These queries rely on tags/logic varnishncsa cannot express, so they
stay on `varnishlog` (via `vg-log -t log -- ...`). The query logic and
awk bodies are preserved as-is.

```sh
# Average waitinglist delay (object coalescing / backend saturation)
vg-log -t log -- -c \
  -q "ReqMethod eq GET and Timestamp:Waitinglist" -i Timestamp | grep Waitinglist: | \
  awk '{t+=$5} END{print t/(NR+0.0000001) " seconds (count: " NR ")"}'

# VHA6 cluster requests
vg-log -t log -- -c -q "ReqMethod ~ VHA" -i ReqStart | grep ReqStart | wc -l

# Error lines (excluding benign noise)
vg-log -t log -- -g raw | grep -i error | \
  grep -Eiv "vha6|RespReason|Timestamp|Cache-Control|pHeader|qHeader|qURL"

# Transactions with 0s TTL (cacheability problem candidates)
vg-log -t log -- -b \
  -q "Begin[3] ne pass and VCL_return eq deliver" -i TTL | awk '$2=="TTL" && $4==0'

# Fetch performance broken down by storage stevedore
vg-log -t log -- -b -i Timestamp -i Storage | awk '
  {
    if ($2=="Storage") { s = $3"_"$4 }
    else if ($3=="BerespBody:") { t[s]+=$5; c[s]++ }
  }
  END { for(s in t) printf "%-25s %f seconds (count: %d)\n", s":", t[s]/(c[s]+0.0000001), c[s] }'
```

`varnishlog-json` (`-t json`) gives structured output for `jq` — this
tool is **Enterprise only**, not available in the `varnish:*` OSS image.

## Ad-hoc debugging

```sh
# Full request/response view grouped by request
vg-log -t log -- -g request

# Client requests only
vg-log -t log -- -c

# Filter to a specific URL or header
vg-log -t log -- -g request -q 'ReqURL ~ "/api/v1/repos"'

# JSON output (Enterprise image only)
vg-log -t json --
```
