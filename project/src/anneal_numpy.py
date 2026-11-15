# Written with Claude (Anthropic). Main prompt: "Write the NumPy version of the annealing
# step defined in core.py (README, 'The contract'): same moves as the Numba version, the
# loop over steps stays in Python because each step depends on the previous one, and the
# delta over the exam's neighbours is computed with NumPy array operations." Reviewed and
# owned by Zhenyang.
"""NumPy version of the solver. Same moves as every other version (see core.py).

What NumPy can and cannot vectorize here: step k+1 depends on the timetable left by
step k (an accepted move changes t), so the loop over steps cannot become one array
operation. Only the inner sum over the neighbours of one exam is vectorized. Each step
therefore pays a fixed cost for several NumPy calls (each creates temporary arrays) to
work on only deg(e) numbers. On instances with few neighbours per exam, that fixed cost
can make this version slower than plain Python; with many neighbours it should win.
Measuring where the crossover lies is one of our results.
"""
import numpy as np

from core import Result, penalty_table, full_score


def _neighbour_views(inst):
    """Per exam, the slices of nbr and wt (views, no copy), cut once before the loop so
    the loop does not slice ptr every step. wt is widened to int64 so the products
    cannot overflow (a clash costs 1e9 per shared student)."""
    wt64 = inst.wt.astype(np.int64)
    nbrs = [inst.nbr[inst.ptr[e]:inst.ptr[e + 1]] for e in range(inst.n_exams)]
    wts = [wt64[inst.ptr[e]:inst.ptr[e + 1]] for e in range(inst.n_exams)]
    return nbrs, wts


def anneal(inst, timetable, stream, params):
    """Same signature and Result as anneal_numba.anneal. Does not change `timetable`."""
    t = np.array(timetable, dtype=np.int32)          # private copy
    w = penalty_table(inst.n_slots)                  # int64
    nbrs, wts = _neighbour_views(inst)
    n_slots = inst.n_slots
    exam, shift, threshold = stream.exam, stream.shift, stream.threshold
    patience = params.patience

    score = full_score(inst, t)
    best = score
    accepted = 0
    last_improvement = 0
    steps_done = len(exam)
    for k in range(len(exam)):
        e = int(exam[k])
        old = int(t[e])
        new = (old + int(shift[k])) % n_slots
        others = t[nbrs[e]]                                   # slots of the neighbours
        # delta = sum of wt * (W[|t[v]-new|] - W[|t[v]-old|]), as one dot product
        delta = int(wts[e] @ (w[np.abs(others - new)] - w[np.abs(others - old)]))
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
    return Result(t, int(score), int(best), int(accepted), int(steps_done))
