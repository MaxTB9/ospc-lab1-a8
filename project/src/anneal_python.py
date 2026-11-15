# Written with Claude (Anthropic). Main prompt: "Write the plain Python version of the
# annealing step defined in core.py (README, 'The contract'): same moves as the Numba
# version, pure Python loops on lists, no NumPy inside the loop, so we can measure the
# interpreter cost." Reviewed and owned by Zhenyang.
"""Plain Python version of the solver. Same moves as every other version (see core.py).

Why lists and not NumPy arrays: indexing a NumPy array from Python creates a new NumPy
scalar object every time, which is slower than reading a Python list. This version is
meant to show what the interpreter costs (Layer 2 of Lecture 1), so it uses the fastest
plain-Python containers. Converting the arrays to lists is done once, before the loop,
and is timed separately (Result does not include it, the runner times the whole call).
"""
import numpy as np

from core import Result, penalty_table, full_score


def _anneal(t, ptr, nbr, wt, w, n_slots, exam, shift, threshold, score, patience):
    """The contract's step, one line per rule. All arguments are Python lists or ints.
    t is changed in place."""
    best = score
    accepted = 0
    last_improvement = 0
    steps_done = len(exam)
    for k in range(len(exam)):
        e = exam[k]
        old = t[e]
        new = (old + shift[k]) % n_slots
        delta = 0
        for j in range(ptr[e], ptr[e + 1]):
            other = t[nbr[j]]
            delta += wt[j] * (w[abs(other - new)] - w[abs(other - old)])
        if delta <= 0 or delta < threshold[k]:
            t[e] = new
            score += delta
            accepted += 1
            if score < best:
                best = score
                last_improvement = k
        if patience > 0 and k - last_improvement >= patience:
            steps_done = k + 1
            break
    return score, best, accepted, steps_done


def anneal(inst, timetable, stream, params):
    """Same signature and Result as anneal_numba.anneal. Does not change `timetable`."""
    t = np.array(timetable, dtype=np.int32)          # private copy
    start_score = full_score(inst, t)
    t_list = t.tolist()
    score, best, accepted, steps_done = _anneal(
        t_list, inst.ptr.tolist(), inst.nbr.tolist(), inst.wt.tolist(),
        penalty_table(inst.n_slots).tolist(), inst.n_slots,
        stream.exam.tolist(), stream.shift.tolist(), stream.threshold.tolist(),
        start_score, params.patience)
    return Result(np.array(t_list, dtype=np.int32), int(score), int(best),
                  int(accepted), int(steps_done))
