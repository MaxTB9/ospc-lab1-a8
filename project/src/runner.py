# Written with Claude (Anthropic). Main prompt: "Write the parallel runner for our exam
# timetabling project: a process pool whose workers start once and keep the instance,
# one worker pinned per core, static vs dynamic scheduling with a chunk size,
# OMP_NUM_THREADS=1, the pool start time measured directly, and a CLI that writes one
# CSV row per (workers, repeat) with node and Slurm job ID." Reviewed and owned by Máté.
"""Parallel runner: many independent annealing runs on a pool of worker processes.

Workers start ONCE, load/receive the instance ONCE, pin themselves to one core, warm up
the Numba code, and then only receive run ids. Each run builds its own random stream from
its run id (core.make_stream), so the result of run i does not depend on the number of
workers, the schedule or the chunk size. The `checksum` column proves it: it must be the
same for every worker count and schedule with the same runs.

Scheduling
  dynamic: run ids are cut into chunks of `chunk` and put on ONE shared queue; a free
           worker takes the next chunk (good when runs differ in length).
  static:  the run ids are split into `workers` contiguous blocks up front, one private
           queue per worker (no balancing; the baseline to compare against).

Pool start time (the required overhead) = from just before the first worker process is
started until every worker has reported ready (process start, imports, pinning, Numba
warm-up). It is measured per batch, so each (workers, repeat) row has its own sample.
"""
import os

# One thread per worker: parallelism comes from the processes only. This must be set
# before numpy/numba are imported (a spawned worker re-imports this module first).
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMBA_NUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import csv
import datetime
import multiprocessing as mp
import socket
import sys
import time
import zlib
from time import perf_counter

import numpy as np

from core import Params, initial_timetable, make_stream, toy_instance
from anneal_numba import anneal

VERSION = "numba-pool"
WARMUP_STEPS = 1000


def _worker(rank, cpu, inst, start, params, inbox, outbox, ready):
    t0 = perf_counter()
    pinned = -1
    if cpu is not None and hasattr(os, "sched_setaffinity"):  # Linux only
        os.sched_setaffinity(0, {cpu})
        pinned = cpu
    warm = params._replace(max_steps=WARMUP_STEPS, patience=0)
    anneal(inst, start, make_stream(inst, warm, 0), warm)  # loads/compiles the kernel
    ready.put((rank, os.getpid(), pinned, perf_counter() - t0))
    while True:
        chunk = inbox.get()
        if chunk is None:
            break
        for run_id in chunk:
            a = perf_counter()
            stream = make_stream(inst, params, run_id)
            b = perf_counter()
            r = anneal(inst, start, stream, params)
            c = perf_counter()
            outbox.put((run_id, rank, b - a, c - b, r.score, r.best_score,
                        r.accepted, r.steps_done, zlib.crc32(r.timetable.tobytes())))


def _core_of(cpu):
    """(socket, core) of a logical CPU from sysfs; (0, cpu) if it cannot be read."""
    base = f"/sys/devices/system/cpu/cpu{cpu}/topology/"
    try:
        with open(base + "physical_package_id") as f1, open(base + "core_id") as f2:
            return int(f1.read()), int(f2.read())
    except OSError:
        return 0, cpu


def pin_order(cpus):
    """Allowed CPUs ordered so that every physical core gets one worker before any core
    gets a second (its hyperthread sibling). So n <= physical cores means n distinct
    cores, and going past that shows the effect of hardware threads."""
    by_core = {}
    for c in sorted(cpus):
        by_core.setdefault(_core_of(c), []).append(c)
    cores = sorted(by_core)
    depth = max((len(v) for v in by_core.values()), default=0)
    return [by_core[k][d] for d in range(depth) for k in cores if len(by_core[k]) > d]


def _get(queue, procs, what):
    """queue.get() that fails loudly instead of hanging if a worker has died."""
    while True:
        try:
            return queue.get(timeout=1.0)
        except Exception:
            dead = [p for p in procs if p.exitcode not in (None, 0)]
            if dead:
                raise RuntimeError(f"worker died while waiting for {what}: "
                                   f"exit codes {[p.exitcode for p in dead]}")


def run_batch(inst, params, run_ids, workers, schedule="dynamic", chunk=1,
              start_method=None):
    """Run `run_ids` on a fresh pool of `workers` processes. Returns (summary, rows)."""
    if schedule not in ("static", "dynamic"):
        raise ValueError("schedule must be 'static' or 'dynamic'")
    method = start_method or ("fork" if sys.platform.startswith("linux") else "spawn")
    ctx = mp.get_context(method)
    start = initial_timetable(inst)          # same clash-free start for every run
    cpus = pin_order(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else []
    cores_used = len({_core_of(c) for c in cpus[:workers]})
    load_before = os.getloadavg()[0]         # load of the node (shared with other jobs)
    ids = [int(i) for i in run_ids]

    ready, outbox = ctx.Queue(), ctx.Queue()
    if schedule == "static":
        inboxes = [ctx.Queue() for _ in range(workers)]
    else:
        inboxes = [ctx.Queue()] * workers    # one shared queue
    procs = [ctx.Process(target=_worker, args=(
        r, cpus[r % len(cpus)] if cpus else None, inst, start, params,
        inboxes[r], outbox, ready)) for r in range(workers)]

    t_pool = perf_counter()
    for p in procs:
        p.start()
    infos = [_get(ready, procs, "workers to start") for _ in procs]
    pool_start_s = perf_counter() - t_pool

    t_run = perf_counter()
    if schedule == "static":
        for q, block in zip(inboxes, np.array_split(ids, workers)):
            q.put([int(i) for i in block])
            q.put(None)
    else:
        for i in range(0, len(ids), chunk):
            inboxes[0].put(ids[i:i + chunk])
        for _ in range(workers):
            inboxes[0].put(None)
    rows = sorted(_get(outbox, procs, "results") for _ in ids)
    wall_s = perf_counter() - t_run
    for p in procs:
        p.join()

    crcs = np.array([r[8] for r in rows], dtype=np.uint32)
    summary = dict(
        workers=workers, schedule=schedule, chunk=chunk, start_method=method,
        pool_start_s=pool_start_s, init_max_s=max(i[3] for i in infos),
        compute_wall_s=wall_s, total_s=perf_counter() - t_pool,
        anneal_sum_s=sum(r[3] for r in rows), stream_sum_s=sum(r[2] for r in rows),
        checksum=zlib.crc32(crcs.tobytes()), pinned=int(infos[0][2] >= 0),
        cpus_available=len(cpus), cores_used=cores_used,
        load_before=load_before, load_after=os.getloadavg()[0])
    return summary, rows


CSV_COLUMNS = [
    "version", "instance", "n_exams", "n_students", "n_slots", "runs", "steps",
    "workers", "schedule", "chunk", "start_method", "pinned", "cpus_available",
    "cores_used", "load_before", "load_after", "repeat",
    "pool_start_s", "init_max_s", "compute_wall_s", "total_s", "anneal_sum_s",
    "stream_sum_s", "checksum", "node", "job_id", "date"]


def _instance(args):
    if args.instance == "toy":
        return toy_instance()
    from generator import generate_instance
    return generate_instance(args.exams, args.students, args.slots)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", default="1,2,4", help="comma list, e.g. 1,2,4,8")
    ap.add_argument("--repeats", type=int, default=5)
    ap.add_argument("--runs", type=int, default=32, help="annealing runs per batch")
    ap.add_argument("--steps", type=int, default=200_000)
    ap.add_argument("--schedule", choices=("static", "dynamic"), default="dynamic")
    ap.add_argument("--chunk", type=int, default=1)
    ap.add_argument("--start-method", choices=("fork", "spawn", "forkserver"))
    ap.add_argument("--instance", choices=("toy", "generated"), default="toy")
    ap.add_argument("--exams", type=int, default=200)
    ap.add_argument("--students", type=int, default=1000)
    ap.add_argument("--slots", type=int, default=20)
    ap.add_argument("--out", default="../results/runner.csv")
    args = ap.parse_args()

    inst = _instance(args)
    params = Params(max_steps=args.steps)
    node, job_id = socket.gethostname(), os.environ.get("SLURM_JOB_ID", "")
    new = not os.path.exists(args.out)
    with open(args.out, "a", newline="") as f:
        out = csv.DictWriter(f, CSV_COLUMNS)
        if new:
            out.writeheader()
        for workers in [int(w) for w in args.workers.split(",")]:
            for repeat in range(args.repeats):
                s, _ = run_batch(inst, params, range(args.runs), workers,
                                 args.schedule, args.chunk, args.start_method)
                row = dict(s, version=VERSION, instance=inst.name, n_exams=inst.n_exams,
                           n_students=inst.n_students, n_slots=inst.n_slots,
                           runs=args.runs, steps=args.steps, repeat=repeat, node=node,
                           job_id=job_id, date=datetime.datetime.now().isoformat(
                               timespec="seconds"))
                out.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v)
                              for k, v in row.items() if k in CSV_COLUMNS})
                f.flush()
                print(f"workers={workers} repeat={repeat} pool_start={s['pool_start_s']:.3f}s "
                      f"wall={s['compute_wall_s']:.3f}s checksum={s['checksum']}", flush=True)


if __name__ == "__main__":
    main()
