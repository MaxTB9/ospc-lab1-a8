# Written with Claude (Anthropic). Main prompt: "Write tests/test_equivalence.py: for 5 run
# ids in fixed mode check that the Numba timetable gives every exam one slot, has no
# clashes and that full_score equals result.score; then check that the Python, NumPy and
# Numba versions give the same timetable, score and accepted moves for the same stream."
# Reviewed and owned by Nikolozi (Person 4).
"""Equivalence tests. Run with pytest, or without it on the cluster:

    /data/software/envs/ospc/bin/python tests/test_equivalence.py

The Python and NumPy versions are tested as soon as src/anneal_python.py and
src/anneal_numpy.py exist; until then that test only checks Numba against itself.
"""
import importlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core import Params, count_clashes, full_score, initial_timetable, make_stream, toy_instance

RUN_IDS = range(5)
FIXED = Params(max_steps=200_000, patience=0)
PATIENCE = Params(max_steps=200_000, patience=5_000)

INST = toy_instance()
START = initial_timetable(INST)


def _versions():
    """The solver modules that exist right now, Numba first."""
    found = {}
    for name in ("anneal_numba", "anneal_python", "anneal_numpy"):
        try:
            found[name] = importlib.import_module(name)
        except ModuleNotFoundError as err:
            if err.name != name:  # the module exists but one of its imports is missing
                raise
    return found


def _run(module, run_id, params):
    start = START.copy()
    result = module.anneal(INST, start, make_stream(INST, params, run_id), params)
    assert np.array_equal(start, START), f"{module.__name__} changed the timetable it was given"
    return result


def test_numba_fixed_mode_is_valid():
    import anneal_numba
    for run_id in RUN_IDS:
        r = _run(anneal_numba, run_id, FIXED)
        assert r.timetable.shape == (INST.n_exams,), "every exam needs exactly one slot"
        assert r.timetable.min() >= 0 and r.timetable.max() < INST.n_slots, "slot out of range"
        assert count_clashes(INST, r.timetable) == 0, f"run {run_id} has clashes"
        assert full_score(INST, r.timetable) == r.score, f"run {run_id}: running score drifted"
        assert r.best_score <= r.score
        assert r.steps_done == FIXED.max_steps, "fixed mode must run every step"


def test_versions_make_the_same_moves():
    versions = _versions()
    reference = versions.pop("anneal_numba")
    if not versions:
        print("only anneal_numba found: Python/NumPy comparison skipped")
    for params in (FIXED, PATIENCE):
        for run_id in RUN_IDS:
            want = _run(reference, run_id, params)
            for name, module in versions.items():
                got = _run(module, run_id, params)
                where = f"{name} vs anneal_numba, run {run_id}, patience {params.patience}"
                assert got.accepted == want.accepted, f"{where}: accepted moves differ"
                assert got.steps_done == want.steps_done, f"{where}: stopped at a different step"
                assert got.score == want.score and got.best_score == want.best_score, f"{where}: score differs"
                assert np.array_equal(got.timetable, want.timetable), f"{where}: timetable differs"


if __name__ == "__main__":
    for test in (test_numba_fixed_mode_is_valid, test_versions_make_the_same_moves):
        test()
        print("ok", test.__name__)
