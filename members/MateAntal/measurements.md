# Measurements: Mate Antal (@MateAntal)

Laptop: Apple MacBook Air 13-inch M1 2020, macOS Sonoma 14.6.1
CPU: 8 cores (4 performance + 4 efficiency), 8 threads. Container: nproc = 8, memory limit 2 GiB, no swap.

## 5.1 Warm-up: ./run_report.sh

- `./run_report.sh` → `Permission denied`
- `ls -l run_report.sh` before: `-rw-r--r--` (mode 644): no execute (x) bit for owner, group or others
- After `chmod +x run_report.sh`: `-rwxr-xr-x` (mode 755). Git recorded `mode change 100644 => 100755`.
- `./run_report.sh` asks the kernel to execute the file, which needs x. `bash run_report.sh` executes /bin/bash, which only reads the script, so r is enough.

## 5.2 Task 1: report.py

Full pipeline, `/usr/bin/time -f "$T" ./run_report.sh`:

    162.44 s elapsed, 213.28 s user, 28.92 s system, 2087580 KB peak memory

- `report.py` printed `loaded 8,400,000 orders (887 MiB)`, then `Killed`. The script carried on and printed "finished".
- `revenue_by_region_month.csv` missing; all six `extracts/*.csv` 0 bytes.
- `python3 steps/report.py; echo $?` → **137** = 128 + 9 = SIGKILL.
- `cat /sys/fs/cgroup/memory.events` → `oom_kill 2`: the kernel's OOM killer killed it (once in the pipeline, once alone) because the container reached `memory.max` (2 GiB).
- user (213 s) > elapsed (162 s) because the stats step ran several workers in parallel.

Memory growth, `report.py` on the first N orders:

| Orders | Table (printed) | Peak RSS | Elapsed |
|---|---|---|---|
| 1,000,000 | 106 MiB | 507,464 KB | 2.26 s |
| 2,000,000 | 211 MiB | 857,908 KB | 3.84 s |
| 4,000,000 | 423 MiB | 1,570,116 KB | 6.96 s |
| 8,400,000 | 887 MiB | killed (predicted ≈ 3,100,000 KB ≈ 3 GiB) | |

- Growth is linear: about 350 MB per million orders, plus about 150 MB fixed (interpreter and libraries).
- Peak RSS is about 3.3x the printed table size: Python object overhead and temporary copies during processing. The kernel limits RSS, not the program's own estimate, so 887 MiB of data needs about 3 GiB > 2 GiB limit.
- The limit is crossed at roughly 5.5 million orders.

`python3 steps/report.py | tee /tmp/report.log`: nothing on screen, log file empty.
- Through a pipe, Python's stdout is block-buffered, not line-buffered. The "loaded" line was still in the buffer when SIGKILL arrived, and SIGKILL cannot be caught, so it was never flushed.
- No "Killed" message: the pipeline's status is tee's (0). `echo ${PIPESTATUS[@]}` would show `137 0`.

## 6.4 Worker experiment (stats step), averages of 3 runs

| Workers | Elapsed | Speedup | Efficiency | User |
|---|---|---|---|---|
| 1 | 35.9 s | 1.00 | 100% | 36.3 s |
| 2 | 19.4 s | 1.85 | 93% | 38.4 s |
| 4 | 12.2 s | 2.95 | 74% | 46.4 s |
| 8 | 10.7 s | 3.36 | 42% | 75.6 s |
| 16 | 11.3 s | 3.17 | 20% | 81.7 s |

- Fastest at 8 workers = my core count; 16 is slower (oversubscription: more workers than cores, extra context switches).
- 4 → 8 gains little: workers 5-8 run on the slower efficiency cores; serial parts limit speedup (Amdahl's law).
- User time grows with workers: parallel overhead. Later runs are slower (fanless laptop, likely thermal throttling).

## 5.3 Task 2: extracts.sh

- `bash steps/extracts.sh; echo $?` → prints `extracts: done`, exit status **0**, but all six `extracts/*.csv` are 0 bytes.
- From `~/data/out/extracts`: `grep ",Iberia," ../data/sales_2025.csv | cut ... | wc -l` → `grep: ../data/sales_2025.csv: No such file or directory`, count 0.
- `echo ${PIPESTATUS[@]}` → `2 0 0` (grep 2 = error; cut and wc 0). `pwd` → `/home/analyst/data/out/extracts`.
- The relative path resolves to `~/data/out/data/sales_2025.csv`, which does not exist. `2>/dev/null` hid grep's error; the pipeline and script both reported the last command's status (0).

## 5.4 Task 3: audit.py

| Run | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| Sample, 100,000 orders | 1.32 s | 1.59 s | 0.33 s | 127,364 KB |
| Full, 8,400,000 orders | 79.95 s | 60.03 s | 20.50 s | 635,136 KB |

- `strace -c -e trace=openat,write,close` on the sample: openat 100,686, write 100,001, close 100,673 (301,360 calls in total) for a 1,952,269-byte file.
- About one open, write and close per order: the file is reopened and closed for every line, so Python's buffer never helps.
- Kernel share on the full file: 20.50 / (60.03 + 20.50) ≈ 25%, against about 9% for report.py.
- Closing does not save to disk: write() only copies data to the page cache; fsync() would force it to disk.
- With one open file and a 128 KiB buffer: about 1,952,269 / 131,072 ≈ 15 write calls on the sample.

---
Measurements taken by me on my laptop. Used Claude to understand concepts and results.
