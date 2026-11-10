# Abdelaziz Moumen — Lab 1 Measurements

## Task 3 — Audit Performance

### Problem
The original audit implementation performed excessive file operations, causing unnecessary system calls and slowing execution.

### Fix
The optimized implementation opens the output file once and uses buffered writing instead of repeatedly opening and closing the file.

### Measured results (current optimized code)

| Metric | Value |
|---|---:|
| Elapsed time | 20.05 s |
| User CPU time | 19.24 s |
| System CPU time | 1.29 s |
| Peak memory | 635128 KB |
| Total system calls | 11536 |
| write system calls | 1470 |
| Audit records | 8400000 |

### Validation
PASS: audit_2025.csv — 8400000 lines, expected 8400000.

### Note
Original-version measurements are still required for a complete before-and-after comparison.
