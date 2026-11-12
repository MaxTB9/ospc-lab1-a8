# AI-use log

One entry per piece of AI-assisted code: date, who, tool, file, the main prompt, and how it was checked.

| Date | Who | Tool | File | Main prompt | Checked how |
|---|---|---|---|---|---|
| 12 Nov 2026 | Maximiliano | Claude (Anthropic) | `src/core.py` | "Write the shared core for our exam timetabling project: instance format as int32 CSR arrays, a clash-free start, the Carter cost, and one pre-generated random stream per run so the Python, NumPy and Numba versions make exactly the same moves." | Toy instance: start has 0 clashes, the running score equals `full_score` after 200,000 steps, the same run gives the same timetable, another run gives a different one |
| 12 Nov 2026 | Maximiliano | Claude (Anthropic) | `src/anneal_numba.py` | "Write the Numba version of the annealing step defined in core.py: integer delta over the exam's neighbours, the pre-computed threshold for the accept test, no fastmath, nogil so threads can run it in parallel." | Same checks, run as plain Python and compiled with Numba |
