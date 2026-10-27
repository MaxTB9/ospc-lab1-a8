# Measurements of MaxTB9

Lenovo 83HM, Intel Core Ultra 7 258V (8 cores, 8 threads), Windows 11 Home.
Container: 8 CPUs (`nproc`), memory limit 2 GiB (`memory.max` = 2147483648).
Measured in class on 27 October 2026, with the other applications closed.

All timings use:

```
T='%e s elapsed, %U s user, %S s system, %M KB peak memory'
```

## 5.1 Warm-up

```
ls -l run_report.sh
-rwxrwxrwx 1 root root 402 Oct 27 10:37 run_report.sh
```

`./run_report.sh` ran: Docker on Windows shows every shared file as
`-rwxrwxrwx`. In git the file was `100644` (no execute bit for anyone), so it
fails on macOS and Linux. Fixed with `git update-index --chmod=+x run_report.sh`
(now `100755`).

## 5.2 Task 1: report.py

```
/usr/bin/time -f "$T" ./run_report.sh
114.81 s elapsed, 139.39 s user, 54.56 s system, 2096796 KB peak memory
```

`report.py` printed `Killed`, the script still exited with status 0, and
`revenue_by_region_month.csv` was missing from `~/data/out`.

```
python3 steps/report.py
echo $?
137
```

`cat /sys/fs/cgroup/memory.events`: `oom_kill` went from 0 to 1 after
`run_report.sh`, and grew by 1 after every run of `report.py` on the whole file.

| Orders | Table (printed by report.py) | Peak memory | Elapsed | User | System |
|---|---|---|---|---|---|
| 1,000,000 | 106 MiB | 508,348 KB (0.48 GiB) | 2.12 s | 1.98 s | 0.32 s |
| 2,000,000 | 211 MiB | 856,604 KB (0.82 GiB) | 3.18 s | 3.13 s | 0.48 s |
| 4,000,000 | 423 MiB | 1,572,128 KB (1.50 GiB) | 5.87 s | 5.34 s | 0.98 s |
| 8,400,000 | 887 MiB | killed at 2,097,156 KB (2.00 GiB), exit 137 | 12.50 s | 10.40 s | 2.15 s |

Commands: `head -n 1000001 ~/data/sales_2025.csv > /tmp/orders_1m.csv`, then
`DATA=/tmp/orders_1m.csv OUT=/tmp /usr/bin/time -f "$T" python3 steps/report.py`
(same with 2000001 and 4000001).

Peak memory grows by about 358,000 KB per million orders, about 3.3 times the
table. The whole file would need about 3,150,000 KB (3.0 GiB), above the 2 GiB
limit.

```
python3 steps/report.py | tee /tmp/report.log
echo ${PIPESTATUS[@]}
137 0
```

`/tmp/report.log` was empty: the `report: loaded ...` line was still in
Python's buffer when the process was killed.

## 5.3 Task 2: extracts.sh

```
bash steps/extracts.sh
echo $?
0
```

All six files in `~/data/out/extracts` have 0 bytes.

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
| Sample, 100,000 orders | 2.44 s | 2.10 s | 0.43 s | 141,900 KB |
| Whole file, 8,400,000 orders | 52.55 s | 35.99 s | 16.95 s | 635,812 KB |

On the whole file the kernel took 32% of the CPU time (16.95 of 52.94 s),
against 15% for `report.py` on 4 million orders (0.98 of 6.32 s).

```
export DATA=~/data/sales_2025_sample.csv
strace -c -e trace=openat,write,close python3 steps/audit.py
```

| System call | Calls | Errors |
|---|---|---|
| openat | 100,689 | 17 |
| write | 100,001 | |
| close | 100,677 | |
| total | 301,367 | 17 |

`audit_2025.csv` on the sample: 1,952,269 bytes. Through a single open file
with a 128 KiB buffer, that is about 15 write calls (1,952,269 / 131,072).
