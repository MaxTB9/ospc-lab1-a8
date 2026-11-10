# Measurements: Zhenyang Rao (@zraoieu2024-web)

Laptop: Apple MacBook Pro 14-inch M5, macOS Golden Gate 27.0.1
CPU: 10 cores (4 super + 6 efficiency), 10 threads. Container: nproc = 10, memory limit 2 GiB, no swap.
All numbers below were measured by me on my laptop, running the original scripts of the template (ospc-lab1), not the fixed team versions.

## 5.1 Warm-up: ./run_report.sh

- `./run_report.sh` -> `bash: ./run_report.sh: /bin/bash: bad interpreter: Permission denied`
- `ls -l run_report.sh` before: `-rw-r--r--` (mode 644): nobody has the execute (x) permission.
- `./run_report.sh` asks the kernel to execute the file, which needs x. `bash run_report.sh` only makes bash read the file, so r is enough.
- Fix: `chmod +x run_report.sh` (mode 755).

## 5.2 Task 1: report.py

- `python3 steps/report.py; echo $?` on the whole file -> exit status **137** = 128 + 9 = SIGKILL.
- `/sys/fs/cgroup/memory.events` before: `oom_kill 0`. After: `max 641`, `oom 1`, `oom_kill 1`. The kernel's OOM killer killed it because the container reached its memory limit (2 GiB).

Memory growth, `report.py` on the first N orders:

| Orders | Table (printed) | Peak RSS | Elapsed |
|---|---|---|---|
| 1,000,000 | 106 MiB | 507,856 KB | 1.09 s |
| 2,000,000 | 211 MiB | 899,936 KB | 1.87 s |
| 4,000,000 | 423 MiB | 1,566,492 KB | 3.57 s |
| 8,400,000 | 887 MiB (as in the team report) | killed (predicted about 3,100,000 KB, about 3 GiB) | |

- Growth is linear: about 353,000 KB per million orders plus about 155,000 KB fixed. For 8.4 million orders that is about 3.1 GB, above the 2 GiB limit, so the program is killed. The limit is crossed at about 5.5 million orders.
- The peak RSS is much bigger than the table size printed by the program, so the kernel limit applies to the real memory used, not to the program's own estimate.

## 5.3 Task 2: extracts.sh

- `bash steps/extracts.sh; echo $?` -> prints `extracts: done` and exit status **0**, but all six `extracts/REGION.csv` files are 0 bytes (`ls -l` shows `0`).
- So the script reports success while producing nothing.
- Cause, as explained in the team REPORT.md (I did not rerun the grep by hand): the script changes folder and then reads the relative path `../data/sales_2025.csv`, which does not exist from there; `2>/dev/null` hides grep's error, and the exit status is the one of the last command.

## 5.4 Task 3: audit.py

| Run | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| Sample, 100,000 orders | 0.59 s | 1.20 s | 0.14 s | 127,552 KB |
| Full, 8,400,000 orders | 35.31 s | 26.25 s | 9.84 s | 634,800 KB |

- `strace -c -e trace=openat,write,close` on the sample: openat 100,686 (13 errors), write 100,001, close 100,673, 301,360 calls in total.
- About one open, write and close per order: the file is opened and closed for every line, so Python's buffer never helps.
- Kernel share on the full file: 9.84 / (26.25 + 9.84) = about 27%. For report.py on 4 million orders it was 0.10 / (4.25 + 0.10) = about 2%.

## 5.5 Task 4: segments.py

- Whole file: 21.97 s elapsed, 22.71 s user, 0.04 s system, 743,492 KB peak memory.
- Almost all the time is user time (the program's own code), not the kernel.

## 6.4 Worker experiment (stats step), median of 3 runs

| Workers | Elapsed | Speedup | Efficiency | User |
|---|---|---|---|---|
| 1 | 25.67 s | 1.00 | 100% | 26.59 s |
| 2 | 13.54 s | 1.90 | 95% | 27.56 s |
| 4 | 7.16 s | 3.59 | 90% | 28.05 s |
| 8 | 4.76 s | 5.39 | 67% | 34.55 s |
| 16 | 4.68 s | 5.49 | 34% | 41.18 s |

- The time halves from 1 to 2 and from 2 to 4 workers, then improves less: the gain from 8 to 16 workers is almost zero.
- My laptop has 10 cores (4 super + 6 efficiency), so with 16 workers there are more processes than cores. They take turns, and the user time grows (26.59 s to 41.18 s) without making the run faster.

---
Measurements taken by me, used claude to understand the concepts and correct errors.
