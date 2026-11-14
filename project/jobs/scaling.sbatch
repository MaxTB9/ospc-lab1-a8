#!/bin/bash -l
# Written with Claude (Anthropic). Main prompt: "Write the Slurm job script for our exam
# timetabling project: one job runs all worker counts with 5 repeats on one node,
# Numba from the cluster module, node and job ID in the output." Reviewed and owned by Máté.
#
# Run from the project/ folder:   sbatch jobs/scaling.sbatch
# Change the experiment with environment variables (sbatch passes them on), e.g.:
#   WORKERS="1 2 4" REPEATS=1 RUNS=16 STEPS=100000 sbatch jobs/scaling.sbatch
#
# Cluster limits (course brief, section 4): each student may use up to 64 CPUs = 32
# physical cores (Slurm counts every hardware thread as a CPU), 4 running and 8 submitted
# jobs. Other jobs can share the cores, so every row records the node and its load.
# Always state the CPUs and memory you need; here 64 CPUs, so 1..32 workers sit on
# distinct physical cores (runner.py pins one worker per core, siblings only after that)
# and 64 workers show the effect of hardware threads.
#
# A full-size run needs a longer limit than the default below, e.g.
#   sbatch --time=04:00:00 jobs/scaling.sbatch
#SBATCH --job-name=ospc-scaling
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=results/slurm-%j.out

set -euo pipefail
module load numba/0.58.1-foss-2023a

WORKERS=${WORKERS:-"1 2 4 8 16 32 64"}
REPEATS=${REPEATS:-5}
RUNS=${RUNS:-256}
STEPS=${STEPS:-500000}
SCHEDULE=${SCHEDULE:-dynamic}
CHUNK=${CHUNK:-1}
INSTANCE=${INSTANCE:-toy}      # toy | generated
EXAMS=${EXAMS:-200}; STUDENTS=${STUDENTS:-1000}; SLOTS=${SLOTS:-20}

cd "${SLURM_SUBMIT_DIR:-.}/src"
OUT="../results/scaling-${SLURM_JOB_ID:-local}.csv"
WLIST=$(echo "$WORKERS" | tr ' ' ',')

echo "job=${SLURM_JOB_ID:-none} node=$(hostname) date=$(date -Is)"
echo "python=$(python3 --version 2>&1) numba=$(python3 -c 'import numba; print(numba.__version__)')"
echo "allowed CPUs: $(nproc), affinity: $(taskset -cp $$ | cut -d: -f2)"
echo "workers=$WLIST repeats=$REPEATS runs=$RUNS steps=$STEPS schedule=$SCHEDULE chunk=$CHUNK instance=$INSTANCE"
echo "node load: $(cut -d' ' -f1-3 /proc/loadavg) ($(uptime | sed 's/.*, *\([0-9]* users\).*/\1/'))"
for w in $WORKERS; do
  if [ "$w" -gt "$(nproc)" ]; then echo "WARNING: $w workers but only $(nproc) CPUs" >&2; fi
done

# Prime the Numba cache once, so the first batch does not pay for all workers compiling.
python3 -c "
from core import toy_instance, initial_timetable, Params, make_stream
from anneal_numba import anneal
i = toy_instance(); p = Params(max_steps=1000)
anneal(i, initial_timetable(i), make_stream(i, p, 0), p)"

python3 runner.py --workers "$WLIST" --repeats "$REPEATS" --runs "$RUNS" --steps "$STEPS" \
  --schedule "$SCHEDULE" --chunk "$CHUNK" --instance "$INSTANCE" \
  --exams "$EXAMS" --students "$STUDENTS" --slots "$SLOTS" --out "$OUT"

echo "done: $OUT"
