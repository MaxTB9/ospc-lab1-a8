# Written with Claude (Anthropic). Main prompt: "Write the shared core for our exam
# timetabling project: instance format as int32 CSR arrays, a clash-free start, the
# Carter cost, and one pre-generated random stream per run so the Python, NumPy and
# Numba versions make exactly the same moves." Reviewed and owned by Maximiliano.
"""Shared core of the project. Every solver version imports from here.

The rule that makes the versions comparable: a solver never draws random numbers.
It reads the Stream made by make_stream(), one entry per step, in order. So for the
same run_id every version makes the same moves and ends with the same timetable.

The step that every version must implement exactly (see README, "The contract"):

    for k in range(len(stream.exam)):
        e = stream.exam[k]
        old = t[e]
        new = (old + stream.shift[k]) % n_slots
        delta = sum over neighbours v of e: wt * (W[abs(t[v] - new)] - W[abs(t[v] - old)])
        if delta <= 0 or delta < stream.threshold[k]:
            t[e] = new, score += delta, accepted += 1
            if score < best: best = score, last_improvement = k
        if params.patience > 0 and k - last_improvement >= params.patience:
            stop (steps_done = k + 1)

delta is an integer and threshold a float made once here, so the accept test is
the same comparison in every version: no exp() or log() inside the solvers.
"""
from typing import NamedTuple

import numpy as np

CLASH = 1_000_000_000
PROXIMITY = (16, 8, 4, 2, 1)


class Instance(NamedTuple):
    name: str
    n_exams: int
    n_slots: int
    n_students: int
    ptr: np.ndarray
    nbr: np.ndarray
    wt: np.ndarray


class Params(NamedTuple):
    max_steps: int = 1_000_000
    t_start: float = 80.0
    t_end: float = 0.05
    patience: int = 0


class Stream(NamedTuple):
    exam: np.ndarray
    shift: np.ndarray
    threshold: np.ndarray


class Result(NamedTuple):
    timetable: np.ndarray
    score: int
    best_score: int
    accepted: int
    steps_done: int


def instance_from_students(students, n_exams, n_slots, name):
    """students: one array of exam ids per student. Two exams are linked if they
    share a student; the link weight is the number of students they share."""
    pairs = []
    for exams in students:
        exams = np.unique(np.asarray(exams, dtype=np.int64))
        i, j = np.triu_indices(len(exams), 1)
        pairs.append(exams[i] * n_exams + exams[j])
    keys = np.concatenate(pairs) if pairs else np.zeros(0, dtype=np.int64)
    keys, counts = np.unique(keys, return_counts=True)
    a = keys // n_exams
    b = keys % n_exams
    src = np.concatenate([a, b])
    dst = np.concatenate([b, a])
    wt = np.concatenate([counts, counts])
    order = np.lexsort((dst, src))
    ptr = np.searchsorted(src[order], np.arange(n_exams + 1))
    return Instance(name, int(n_exams), int(n_slots), len(students),
                    ptr.astype(np.int32), dst[order].astype(np.int32), wt[order].astype(np.int32))


def toy_instance(n_exams=200, n_students=1000, n_slots=20, seed=0):
    """Small random instance so everyone can test before the real data loader exists."""
    rng = np.random.default_rng(seed)
    students = [rng.choice(n_exams, rng.integers(2, 6), replace=False) for _ in range(n_students)]
    return instance_from_students(students, n_exams, n_slots, f"toy-{n_exams}-{n_students}-{seed}")


def penalty_table(n_slots):
    """W[d] = cost of one shared student whose two exams are d slots apart."""
    w = np.zeros(max(n_slots, len(PROXIMITY) + 1), dtype=np.int64)
    w[0] = CLASH
    w[1:len(PROXIMITY) + 1] = PROXIMITY
    return w[:n_slots]


def full_score(inst, timetable):
    """Total cost from scratch, in the same units the solvers track (clashes included)."""
    t = np.asarray(timetable, dtype=np.int64)
    src = np.repeat(np.arange(inst.n_exams), np.diff(inst.ptr))
    d = np.abs(t[src] - t[inst.nbr])
    return int((inst.wt.astype(np.int64) * penalty_table(inst.n_slots)[d]).sum() // 2)


def count_clashes(inst, timetable):
    """Number of students with two exams in the same slot (counted per exam pair)."""
    t = np.asarray(timetable)
    src = np.repeat(np.arange(inst.n_exams), np.diff(inst.ptr))
    return int(inst.wt[t[src] == t[inst.nbr]].sum() // 2)


def cost_per_student(inst, timetable):
    """The Toronto benchmark figure: proximity cost divided by the number of students."""
    if count_clashes(inst, timetable):
        raise ValueError("timetable has clashes")
    return full_score(inst, timetable) / inst.n_students


def initial_timetable(inst):
    """Clash-free start, the same for every run (DSatur graph colouring).
    Raises ValueError if it cannot fit the exams into n_slots."""
    used = np.zeros((inst.n_exams, inst.n_slots), dtype=bool)
    saturation = np.zeros(inst.n_exams, dtype=np.int64)
    degree = np.diff(inst.ptr).astype(np.int64)
    t = np.full(inst.n_exams, -1, dtype=np.int32)
    for _ in range(inst.n_exams):
        key = np.where(t < 0, saturation * (inst.n_exams + 1) + degree, -1)
        e = int(np.argmax(key))
        free = np.flatnonzero(~used[e])
        if len(free) == 0:
            raise ValueError(f"{inst.name}: no clash-free start with {inst.n_slots} slots")
        s = int(free[0])
        t[e] = s
        nb = inst.nbr[inst.ptr[e]:inst.ptr[e + 1]]
        fresh = nb[~used[nb, s]]
        used[fresh, s] = True
        saturation[fresh] += 1
    return t


def make_stream(inst, params, run_id, master_seed=2026):
    """The random numbers of one run. Child run_id of SeedSequence(master_seed), so a
    run's numbers depend on its run_id only, never on the worker that runs it."""
    seq = np.random.SeedSequence(master_seed).spawn(run_id + 1)[run_id]
    rng = np.random.default_rng(seq)
    n = params.max_steps
    exam = rng.integers(0, inst.n_exams, n, dtype=np.int32)
    shift = rng.integers(1, inst.n_slots, n, dtype=np.int32)
    u = 1.0 - rng.random(n)
    temperature = params.t_start * (params.t_end / params.t_start) ** (np.arange(n) / n)
    return Stream(exam, shift, -temperature * np.log(u))
