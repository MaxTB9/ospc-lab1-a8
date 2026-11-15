#!/bin/bash -l
# Written with Claude (Anthropic). Main prompt: "Write the Slurm job for the scheduling
# experiment: fixed worker count, static vs dynamic scheduling and several chunk sizes,
# 5 repeats, runs of different lengths (patience), one CSV." Reviewed and owned by Máté.
#
# Run from the project/ folder:   sbatch -c 32 jobs/schedule.sbatch
# Compares static (one block per worker) with dynamic (shared queue) at several chunk
# sizes, with the same runs every time (checksum must not change). Runs have different
# lengths because PATIENCE > 0 stops a run when it stops improving; that is what makes
# the choice of schedule matter. Change with env vars, e.g.
#   WORKERS=8 CHUNKS="1 8" REPEATS=1 RUNS=64 sbatch -c 16 jobs/schedule.sbatch
# CPUs: Slurm allocates whole cores, so -c 32 gives 16 physical cores (see scaling.sbatch).
#SBATCH --job-name=ospc-schedule
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=results/slurm-%j.out

set -euo pipefail
module load numba/0.58.1-foss-2023a

WORKERS=${WORKERS:-16}
CHUNKS=${CHUNKS:-"1 2 4 8 16 32"}      # dynamic chunk sizes (runs per queue item)
REPEATS=${REPEATS:-5}
RUNS=${RUNS:-512}
STEPS=${STEPS:-1000000}
PATIENCE=${PATIENCE:-20000}
INSTANCE=${INSTANCE:-toy}              # toy | generated
EXAMS=${EXAMS:-200}; STUDENTS=${STUDENTS:-1000}; SLOTS=${SLOTS:-20}

cd "${SLURM_SUBMIT_DIR:-.}/src"
OUT="../results/schedule-${SLURM_JOB_ID:-local}.csv"

echo "job=${SLURM_JOB_ID:-none} node=$(hostname) date=$(date -Is)"
echo "python=$(python3 --version 2>&1) numba=$(python3 -c 'import numba; print(numba.__version__)')"
echo "allowed CPUs: $(nproc), affinity: $(taskset -cp $$ | cut -d: -f2)"
echo "workers=$WORKERS chunks=$CHUNKS repeats=$REPEATS runs=$RUNS steps=$STEPS patience=$PATIENCE instance=$INSTANCE"
echo "node load: $(cut -d' ' -f1-3 /proc/loadavg)"
if [ "$WORKERS" -gt "$(nproc)" ]; then echo "WARNING: $WORKERS workers but only $(nproc) CPUs" >&2; fi

# Prime the Numba cache once, so the first batch does not pay for compiling.
python3 -c "
from core import toy_instance, initial_timetable, Params, make_stream
from anneal_numba import anneal
i = toy_instance(); p = Params(max_steps=1000)
anneal(i, initial_timetable(i), make_stream(i, p, 0), p)"

common=(--workers "$WORKERS" --repeats "$REPEATS" --runs "$RUNS" --steps "$STEPS"
        --patience "$PATIENCE" --instance "$INSTANCE" --exams "$EXAMS"
        --students "$STUDENTS" --slots "$SLOTS" --out "$OUT")

echo "== static =="
python3 runner.py "${common[@]}" --schedule static
for c in $CHUNKS; do
  echo "== dynamic, chunk $c =="
  python3 runner.py "${common[@]}" --schedule dynamic --chunk "$c"
done
echo "done: $OUT"
