#!/bin/bash
# Bootstrap 95% confidence intervals for the average order value of every
# region and month. The work is split among WORKERS processes that run at
# the same time. More workers than CPUs cannot be faster: the default is the
# number of CPUs of the machine (or of the container).

# Fixed with Claude Code (Anthropic, Claude Sonnet 5.5); prompt: "help me do them".
WORKERS=${WORKERS:-$(nproc)}
OUT=${OUT:-$HOME/data/out}

# Background jobs of a script ignore Ctrl-C (SIGINT), so the workers would
# keep running after the script stops. On SIGINT or SIGTERM, end every
# worker with SIGTERM, wait for them, and exit with 128 + the signal number.
cleanup() {
    kill $(jobs -p) 2>/dev/null
    wait 2>/dev/null
    exit "$1"
}
trap 'cleanup 130' INT
trap 'cleanup 143' TERM

python3 steps/stats_prepare.py
mkdir -p "$OUT/stats"
rm -f "$OUT"/stats/part_*.csv
for k in $(seq 0 $((WORKERS - 1))); do
    python3 steps/stats_worker.py "$k" "$WORKERS" &
done
wait
cat "$OUT"/stats/part_*.csv | sort > "$OUT/stats.csv"
echo "stats: done with $WORKERS workers"
