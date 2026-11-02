# Measurements of MaxTB9

MSI MS-7E59 desktop, AMD Ryzen 9 9950X (16 cores, 32 threads), Windows 11 Pro.
Container: 32 CPUs (`nproc`), memory limit 2 GiB (`memory.max` = 2147483648), no swap.
Measured on 2 November 2026 on this desktop. These numbers replace the laptop
numbers of 27 October. The faulty runs use commit `3631e62`, the last one before
the team's fixes.

All timings use:

```
T='%e s elapsed, %U s user, %S s system, %M KB peak memory'
```

## 5.1 Warm-up

```
ls -l run_report.sh
-rwxrwxrwx 1 root root 402 Nov  2 14:02 run_report.sh
```

Docker on Windows shows every shared file as `-rwxrwxrwx`, so `./run_report.sh`
runs here. In git the file is `100755` since commit `57675a9`.

## 5.2 Task 1: report.py

```
/usr/bin/time -f "$T" ./run_report.sh
124.65 s elapsed, 117.33 s user, 90.13 s system, 2090212 KB peak memory
```

`report.py` printed `Killed`, the script carried on and finished, and
`revenue_by_region_month.csv` was missing from `~/data/out`.

```
python3 steps/report.py
echo $?
137
cat /sys/fs/cgroup/memory.events
max 8020
oom 2
oom_kill 2
```

`oom_kill` was 0 when the container started, and went up by 1 per kill: once in
`run_report.sh` and once in this run.

| Orders | Table (printed by report.py) | Peak memory | Elapsed | User | System |
|---|---|---|---|---|---|
| 1,000,000 | 106 MiB | 506,348 KB | 2.16 s | 3.03 s | 0.79 s |
| 2,000,000 | 211 MiB | 856,896 KB | 2.65 s | 3.82 s | 0.68 s |
| 4,000,000 | 423 MiB | 1,567,092 KB | 5.17 s | 4.88 s | 1.23 s |
| 8,400,000 | 887 MiB | killed, exit 137 | | | |

From 2M to 4M the peak grows by 355,098 KB per million orders, about 3.27 tables.
The whole file would need about 3,130,000 KB (3.0 GiB), above the 2 GiB limit.

```
python3 steps/report.py | tee /tmp/report.log
echo ${PIPESTATUS[@]}
137 0
```

`/tmp/report.log` was empty: the `report: loaded ...` line was still in Python's
buffer when the process was killed.

## 5.3 Task 2: extracts.sh

`bash steps/extracts.sh` printed `extracts: done`, `echo $?` gave 0, and all six
files in `~/data/out/extracts` have 0 bytes.

```
cd ~/data/out/extracts
grep ",Iberia," ../data/sales_2025.csv | cut -d, -f1,2,4,6,7 | wc -l
grep: ../data/sales_2025.csv: No such file or directory
0
echo ${PIPESTATUS[@]}
2 0 0
pwd
/home/analyst/data/out/extracts
```

From that folder, `../data/sales_2025.csv` is `~/data/out/data/sales_2025.csv`,
which does not exist.

## 5.4 Task 3: audit.py

| Input | Elapsed | User | System | Peak memory |
|---|---|---|---|---|
| Sample, 100,000 orders | 1.89 s | 1.89 s | 1.10 s | 128,680 KB |
| Whole file, 8,400,000 orders | 75.94 s | 32.88 s | 44.83 s | 634,924 KB |

On the whole file the kernel took 58% of the CPU time (44.83 of 77.71 s), against
20% for `report.py` on 4 million orders (1.23 of 6.11 s).

```
export DATA=~/data/sales_2025_sample.csv
strace -c -e trace=openat,write,close python3 steps/audit.py
```

| System call | Calls | Errors |
|---|---|---|
| openat | 100,691 | 19 |
| write | 100,001 | |
| close | 100,677 | |
| total | 301,369 | 19 |

`audit_2025.csv` on the sample: 1,952,269 bytes. Through a single open file with
a 128 KiB buffer, that is about 15 write calls (1,952,269 / 131,072).

## My own fixes, measured before and after

I made these on a local branch to learn them. The team's fixes on `main` are by
Mate Antal and JorbenaN.

| Step | Before | After |
|---|---|---|
| `report.py` | killed, exit 137 | 7.27 s, 6.79 s user, 2.15 s system, 1,859,412 KB |
| `extracts.sh` | 0 byte files | 2.51 s, 2.49 s user, 1.47 s system, 7,816 KB |
| `audit.py` | 75.94 s, 32.88 s user, 44.83 s system, 634,924 KB | 9.88 s, 10.88 s user, 0.85 s system, 634,868 KB |

`audit.py` on the sample, system calls after the fix: openat 691, write 17,
close 677.

## The whole pipeline with the team's fixes

```
/usr/bin/time -f "$T" ./run_report.sh
41.05 s elapsed, 112.74 s user, 124.61 s system, 1301336 KB peak memory
```
