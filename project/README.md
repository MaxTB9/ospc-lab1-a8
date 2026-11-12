# Group project: parallel exam timetabling

**Question:** how do we find a clash-free exam timetable with the lowest proximity cost (students with exams close together), fast enough to try many options? Data: the Toronto benchmark (public) plus our own generator. Approved by Prof. Turilli on 8 Nov 2026, with Numba as our additional technique.

This README becomes the run guide (the brief requires a small configuration that runs in under 5 minutes from a fresh clone on the cluster). Until then it holds the plan.

## Folders

| Folder | What goes there | Owner |
|---|---|---|
| `src/` | Shared modules: data loader, generator, cost model, solver versions, parallel runner | everyone, one file per owner |
| `tests/` | Automated equivalence tests (every version gives the same timetable for the same seeds) | Person 4 |
| `jobs/` | Slurm job scripts (one job runs all worker counts, 5 repeats) | Person 3 |
| `results/` | Raw timing CSVs, one row per run: version, workers, problem size, repeat, phase times, node, job ID, date | Person 5 |
| `analysis/` | The notebook that makes every table and plot from `results/` | Person 5 |
| `report/` | Report drafts, slides, AI-use log | Person 1 edits, everyone writes their section |

Large data (the Toronto files) stays out of Git: download it on the cluster with the script in `src/`.

## Rules

- Everyone commits their own work, in small commits with clear messages. The commit history is used for grading (brief section 7).
- Code written with an AI tool gets a comment above it naming the tool and the main prompt, and the prompt goes in `report/ai-log.md`.
- Measurements only from batch jobs on the cluster (`sbatch`), never from the notebook.
- Each run's random numbers come from its run number (`SeedSequence.spawn`), never from the worker number, so results don't depend on how many workers there are.
- Everyone must be able to explain their part: in the Q&A, Turilli picks who answers.

## The contract: `src/core.py`

Every solver version and every script builds on `src/core.py`. Run things from inside `src/` (or put `src/` on `PYTHONPATH`).

| Name | What it is |
|---|---|
| `Instance` | One problem: `name`, `n_exams`, `n_slots`, `n_students`, and the conflict graph as int32 CSR arrays `ptr`, `nbr`, `wt`. The neighbours of exam `e` are `nbr[ptr[e]:ptr[e+1]]`, and `wt` is the number of students the two exams share. |
| `instance_from_students(students, n_exams, n_slots, name)` | Builds an `Instance` from one array of exam ids per student. The generator and the Toronto loader should both end with this. |
| `toy_instance()` | A small random instance (200 exams, 1,000 students, 20 slots) to test with until the real data is in. |
| `initial_timetable(inst)` | A clash-free start (DSatur colouring). The same for every run. |
| `Params(max_steps, t_start, t_end, patience)` | `patience = 0`: run exactly `max_steps` steps (version comparison). `patience = K`: stop when the best score has not improved for K steps (load balancing). |
| `make_stream(inst, params, run_id, master_seed=2026)` | The random numbers of one run: `exam`, `shift` and `threshold`, one per step. Run `i` uses child `i` of `SeedSequence(master_seed).spawn(...)`, so it never depends on the worker. |
| `anneal(inst, timetable, stream, params) -> Result` | What every solver version provides. `Result` = `timetable, score, best_score, accepted, steps_done`. It must not change the timetable it is given. |
| `full_score`, `count_clashes`, `cost_per_student` | Checks from scratch. `full_score` must equal `Result.score`; `cost_per_student` is the Toronto benchmark figure. |

**One step, which every version must do exactly like this:**
1. `e = exam[k]`, `old = t[e]`, `new = (old + shift[k]) % n_slots` (a move never stays in the same slot).
2. `delta` = sum over the neighbours `v` of `e` of `wt * (W[|t[v] - new|] - W[|t[v] - old|])`, with `W = penalty_table(n_slots)`: 16, 8, 4, 2, 1 for 1 to 5 slots apart, a huge cost for a clash, 0 otherwise. Integers only.
3. Accept if `delta <= 0` or `delta < threshold[k]`. Then `t[e] = new`, `score += delta`, `accepted += 1`, and if `score < best`, update `best` and remember `k`.
4. With `patience > 0`: stop once `k - last_improvement >= patience`.

The threshold already contains the temperature and the random number (`-T * ln(u)`), so no version computes `exp` or `log`: the accept test is the same comparison everywhere, and the versions make identical moves. A clash costs more than any move can save, so a clash is never accepted and the timetable stays clash-free.

```python
from core import toy_instance, initial_timetable, Params, make_stream
from anneal_numba import anneal

inst = toy_instance()
start = initial_timetable(inst)
params = Params(max_steps=200_000)
result = anneal(inst, start, make_stream(inst, params, run_id=0), params)
```

## Dates

| Date | What |
|---|---|
| Tue 17 Nov | Progress review: first strong-scaling plot, posted on the project Blackboard forum |
| Mon 30 Nov, 23:59 | All experiments done, slides uploaded |
| Wed 2 Dec / Tue 15 Dec | Presentations |
| Tue 15 Dec, 23:59 | Repo and report |
