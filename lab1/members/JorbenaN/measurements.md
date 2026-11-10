# Measurements of JorbenaN

Apple MacBook Pro 16-inch M4 Pro 2024 (14 cores, 14 threads), macOS 27.0.1.
Container: 8 CPUs (`nproc`), memory limit 2 GiB (`memory.max` = 2147483648), no swap.
Measured on 2 November 2026. The commands were run through Claude Code (see
"Use of generative AI" in `REPORT.md`), each one in a fresh container started
with `docker compose run --rm lab1`, so the `oom_kill` counter starts at 0.

All timings use:

```
T='%e s elapsed, %U s user, %S s system, %M KB peak memory'
```

## 5.1 Warm-up

`run_report.sh` was `-rw-r--r--` (mode 100644): no execute bit for anyone, so
`./run_report.sh` fails with "Permission denied" (`execve` needs `x`), while
`bash run_report.sh` works because bash only needs to read the file. A teammate
had already committed the fix (`100755`), so my clone had it.

## 5.2 Task 1: report.py

Whole pipeline on the original code: `report.py` printed `Killed`, the script
went on to the next step, and `revenue_by_region_month.csv` was not written.

```
python3 steps/report.py   (whole file)
8.76 s elapsed, 8.84 s user, 0.53 s system, 2138176 KB peak memory
exit status 137
```

`memory.events`: `oom_kill` went from 0 to 1 (the kernel killed the process
when the container reached its 2 GiB limit).

| Orders | Table (printed by report.py) | Peak memory | Elapsed | User | System |
|---|---|---|---|---|---|
| 1,000,000 | 106 MiB | 519,292 KB (0.50 GiB) | 2.18 s | 2.28 s | 0.09 s |
| 2,000,000 | 211 MiB | 855,328 KB (0.82 GiB) | 2.21 s | 2.71 s | 0.10 s |
| 4,000,000 | 423 MiB | 1,567,812 KB (1.50 GiB) | 4.34 s | 4.73 s | 0.22 s |
| 8,400,000 | 887 MiB | killed at 2,138,176 KB, exit 137 | 8.76 s | 8.84 s | 0.53 s |

Peak memory grows by about 356,000 KB per million orders (between 2M and 4M),
about 3.3 times the table. Extrapolated to 8,400,000 orders:
855,328 + 6.4 x 356,242 = about 3,135,000 KB (3.0 GiB), above the 2 GiB limit.

```
python3 steps/report.py | tee /tmp/report.log
echo ${PIPESTATUS[@]}
137 0
```

`/tmp/report.log` has 0 bytes: with a pipe, Python's stdout is block-buffered,
so `report: loaded ...` was still in the buffer when SIGKILL ended the process.

After the fix (same commands):

| Orders | Table | Peak memory | Elapsed |
|---|---|---|---|
| 1,000,000 | 18 MiB | 271,592 KB | 0.56 s |
| 2,000,000 | 36 MiB | 407,180 KB | 0.92 s |
| 4,000,000 | 72 MiB | 684,940 KB | 1.65 s |
| 8,400,000 | 152 MiB | 1,288,024 KB | 3.52 s, exit 0 |

## 5.3 Task 2: extracts.sh

Original: `bash steps/extracts.sh` printed `extracts: done`, exit status 0, and
all six files in `~/data/out/extracts` have 0 bytes. The script runs from
`~/data/out/extracts`, where `../data/sales_2025.csv` is
`~/data/out/data/sales_2025.csv`: that file does not exist. grep fails (status
2), `2>/dev/null` hides its message, and the pipeline's status is the one of
its last command (`cut`, 0).

After the fix: 2.07 s, files of 29 to 76 MB (for example Iberia 76,086,137
bytes), and `check.py` passes with the expected row counts (Iberia 2,183,057).

## 5.4 Task 3: audit.py

| Input | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| Sample, 100,000 orders (original) | 0.76 s | 1.11 s | 0.24 s | 129,712 KB |
| Whole file, 8,400,000 orders (original) | 40.73 s | 30.13 s | 11.20 s | 634,136 KB |
| Sample (fixed) | 0.28 s | 0.86 s | 0.02 s | 128,604 KB |
| Whole file (fixed) | 9.50 s | 10.00 s | 0.10 s | 634,488 KB |

On the whole file the kernel took 27% of the CPU time of the original (11.20
of 41.33 s) and 1% of the fixed one. `report.py` on 4 million orders: 4% (0.22
of 4.95 s).

```
strace -c -e trace=openat,write,close python3 steps/audit.py   (sample)
```

| System call | Original | Fixed |
|---|---|---|
| openat | 100,686 | 686 |
| write | 100,001 | 17 |
| close | 100,673 | 673 |
| total | 301,360 | 1,376 |

`audit_2025.csv` on the sample: 1,952,269 bytes, so through one open file with
a 128 KiB buffer, about 15 write calls (1,952,269 / 131,072). The fixed program
made 17.

## Task 5: Ctrl-C test

Signal sent to the whole process group (what Ctrl-C does), 4 s after start:

| | Workers running | Left after SIGINT | Left after SIGTERM | Exit status |
|---|---|---|---|---|
| Original (16 workers) | 16 | 16, parent PID 1 | 15 | killed by the signal |
| Fixed (8 workers) | 8 | 0 | 0 | 130 / 143 |

## Whole fixed pipeline

```
cd ~ && /usr/bin/time -f "$T" work/ospc-lab1-a8/run_report.sh
23.10 s elapsed, 52.56 s user, 2.08 s system, 1299200 KB peak memory
```

`python3 tools/check.py`: PASS for every output.
