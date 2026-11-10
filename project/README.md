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

## Dates

| Date | What |
|---|---|
| Tue 17 Nov | Progress review: first strong-scaling plot, posted on the project Blackboard forum |
| Mon 30 Nov, 23:59 | All experiments done, slides uploaded |
| Wed 2 Dec / Tue 15 Dec | Presentations |
| Tue 15 Dec, 23:59 | Repo and report |
