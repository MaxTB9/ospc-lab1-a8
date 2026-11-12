# Written with Claude (Anthropic). Main prompt: "Write the Numba version of the
# annealing step defined in core.py: integer delta over the exam's neighbours, the
# pre-computed threshold for the accept test, no fastmath, nogil so threads can run
# it in parallel." Reviewed and owned by Maximiliano.
"""Numba version of the solver. Same moves as every other version (see core.py)."""
import numpy as np
from numba import njit

from core import Result, penalty_table, full_score


@njit(cache=True, nogil=True)
def _anneal(t, ptr, nbr, wt, w, n_slots, exam, shift, threshold, score, patience):
    best = score
    accepted = 0
    last_improvement = 0
    steps_done = exam.shape[0]
    for k in range(exam.shape[0]):
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
    t = np.array(timetable, dtype=np.int32)
    score, best, accepted, steps_done = _anneal(
        t, inst.ptr, inst.nbr, inst.wt, penalty_table(inst.n_slots), inst.n_slots,
        stream.exam, stream.shift, stream.threshold,
        np.int64(full_score(inst, t)), params.patience)
    return Result(t, int(score), int(best), int(accepted), int(steps_done))
