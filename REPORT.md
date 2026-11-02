# Lab 1: The Nightly Report

Write your answers in this file. Keep them short: a few sentences, the commands
you used, and the numbers you measured. Copy the lines of output that matter,
not whole screens.

## Warm-up: Generating the report

- What happened, and why:

One of the programs didn't run. (report.py). The OOM killer killed the program.
There was also a problem with the permissions, as execute was not allowed.

- Your fix, and how it reached your teammates:

The fix is the following command:
 git update-index --chmod=+x run_report.sh
This command was pushed to github and then the teammates could pull it.

## Task 1: Generating the report… again

- Symptom: revenue_by_region_by_month.csv doesn't get generated

- Commands and recordings you used, why you chose them, and what they showed:

Ran run_report.sh with the time recording to see the before time:
/usr/bin/time -f "$T" ./run_report.sh

Printed out the files that were generated:
ls -l ~/data/out ~/data/out/extracts

Found that the revenue_by_region_by_month.csv file from the reports was not generated.

Tried to run report.py on its own and it got killed:
python3 steps/report.py

Echo is 127

Figured out that the OOM killer stopped the program:
cat /sys/fs/cgroup/memory.events
oom_kill is 4

- Cause: report.py gets killed by the OOM killer

- Before and after (your measurements):

Before:
550.46 s elapsed, 436.62 s user, 270.70 s system, 2090032 KB peak memory

With 1 million orders:
5.36 s elapsed, 3.82 s user, 1.37 s system, 505220 KB peak memory

With 2 million orders:
8.22 s elapsed, 6.75 s user, 1.68 s system, 856076 KB peak memory

With 4 million orders:
15.33 s elapsed, 12.36 s user, 3.18 s system, 1570440 KB peak memory

## Task 2: Extracting data

(Fix and text by Mate Antal, explained by Claude)

- Symptom: `steps/extracts.sh` printed `extracts: done` and exited with status 0, but all six `extracts/REGION.csv` files were 0 bytes. `tools/check.py`: `extracts/Iberia.csv  0 rows, expected 2,183,057` (same for every region).
- Commands and recordings you used, why you chose them, and what they showed:
  - `bash steps/extracts.sh; echo $?` → `0`: the script reported success.
  - `less steps/extracts.sh`: the script does `cd "$OUT/extracts"`, then reads `../data/sales_2025.csv` with `2>/dev/null` after `grep`.
  - Ran the pipeline by hand from that folder, without `2>/dev/null`:
    `cd ~/data/out/extracts; grep ",Iberia," ../data/sales_2025.csv | cut -d, -f1,2,4,6,7 | wc -l` → `grep: ../data/sales_2025.csv: No such file or directory`, count `0`.
    `echo ${PIPESTATUS[@]}` → `2 0 0` (grep failed with 2, cut and wc returned 0). `pwd` → `/home/analyst/data/out/extracts`.
- Cause: `../data/sales_2025.csv` is a relative path, resolved from the working directory. After the `cd`, it names `~/data/out/data/sales_2025.csv`, which does not exist. `2>/dev/null` threw away grep's error message, `> "$region.csv"` had already created each file empty, the pipeline's status was cut's (0) and the script's status was the final `echo`'s (0). The script also ignored the `DATA` variable.
- Fix: added `set -euo pipefail` (stop on any failed command, on unset variables, and on a failure anywhere in a pipeline); read the input from `DATA=${DATA:-$HOME/data/sales_2025.csv}`, made absolute with `realpath` before the `cd`; removed `2>/dev/null`. Checked: `DATA=/nonexistent.csv bash steps/extracts.sh` now stops with `grep: /nonexistent.csv: No such file or directory`, exit status 2. `cd ~ && bash work/ospc-lab1-a8/steps/extracts.sh` works from another folder.
- Before and after (your measurements), Mate Antal, MacBook Air M1:

  | | Elapsed | User | System | Peak memory | Result |
  |---|---|---|---|---|---|
  | Before | 0.03 s | 0.01 s | 0.03 s | 8,636 KB | 6 empty files, exit 0 |
  | After | 4.17 s | 5.09 s | 1.12 s | 6,564 KB | `check.py`: PASS for all 6 extracts, exit 0 |

  "After" is slower because it now reads the 498 MB file (six times); "before" read nothing. User > elapsed because grep and cut run as two processes at the same time. Peak memory stays tiny because grep and cut stream the file line by line.

## Task 3: Auditing

- Symptom:
- Commands and recordings you used, why you chose them, and what they showed:
- Cause:
- Fix:
- Before and after (your measurements):
## Task 4: Segmenting the orders

- Symptom:
- Commands and recordings you used, why you chose them, and what they showed:
- Cause:
- Fix:
- Before and after (your measurements):

## Task 5: Computing the statistics

- Symptom:
- Commands and recordings you used, why you chose them, and what they showed:
- Cause:
- Fix:
- Before and after (your measurements):

## The worker experiment

Every member runs `tools/sweep.sh` on their own laptop. Then run
`python3 tools/plot_sweep.py` and commit `results/sweep.png`.

![Elapsed time against the number of workers](results/sweep.png)

- How does the elapsed time change with the number of workers on each laptop?
- Why do the curves of your laptops differ? Use the cores and threads of each
  laptop, listed in `TEAM.md`.
- Which default number of workers did you choose for `stats.sh`, and why?

## Use of generative AI

Follow the format in the syllabus: quote any generated text and name the tool
and the prompts; add the same note as a comment before any generated code. If
you did not use GenAI, write: "No content generated by AI technologies has been
used in this assignment."

- Mate Antal - I used Claude to explain the lab concepts. Prompts were of the form "explain this output", "why are the extract files empty?". I ran every command and measured every number on my own laptop, and reviewed and tested the fix.
