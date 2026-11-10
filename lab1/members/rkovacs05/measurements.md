## Task 1:

Before:
550.46 s elapsed, 436.62 s user, 270.70 s system, 2090032 KB peak memory

With 1 million orders:
5.36 s elapsed, 3.82 s user, 1.37 s system, 505220 KB peak memory

With 2 million orders:
8.22 s elapsed, 6.75 s user, 1.68 s system, 856076 KB peak memory

With 4 million orders:
15.33 s elapsed, 12.36 s user, 3.18 s system, 1570440 KB peak memory

After:
13.50 s elapsed, 10.26 s user, 3.10 s system, 1289476 KB peak memory

## Task 2

Before:
0.09 s elapsed, 0.01 s user, 0.05 s system, 7992 KB peak memory

After:
6.79 s elapsed, 7.61 s user, 3.77 s system, 7904 KB peak memory

## Task 3

Audit on 100 000 lines:
5.75 s elapsed, 3.04 s user, 2.57 s system, 129160 KB peak memory

Audit on 8.4 million lines:
330.82 s elapsed, 163.97 s user, 166.92 s system, 635520 KB peak memory

strace:
audit: 100,000 lines written
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 36.67    5.966113          59    100689        17 openat
 34.40    5.596080          55    100001           write
 28.93    4.706086          46    100677           close
------ ----------- ----------- --------- --------- ----------------
100.00   16.268279          53    301367        17 total

## Task 4

Before:
126.05 s elapsed, 124.46 s user, 1.75 s system, 727456 KB peak memory

After:
13.38 s elapsed, 10.17 s user, 3.41 s system, 1022428 KB peak memory

## Task 5

Before:
53.39 s elapsed, 114.82 s user, 93.48 s system, 111784 KB peak memory

After:
45.86 s elapsed, 98.28 s user, 66.34 s system, 111804 KB peak memory