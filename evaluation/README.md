# Verification scripts and logs

Everything here verifies **implementation consistency and software behaviour only**. Passing
tests are not evidence that recommendations are accurate, suitable for an individual, or
acceptable to users.

## Run
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt                 # Flask==3.0.3 (pinned)
python evaluation/run_all.py --label final              # exit code 0 = all checks passed
git rev-parse HEAD                                      # record the tested commit next to the logs
```
Individual suites: `python evaluation/verify_numeric.py`, `self_matching.py`, `blackbox_tests.py`
(each accepts `--app-dir <backend folder>`, `--out <log folder>`, `--label <name>`).
Checking out an older commit and running with `--label initial` reproduces the "initial" logs.

## Suites
| Script | What it checks | Checks |
|---|---|---|
| `verify_numeric.py` | Deployed functions vs. an independent re-implementation using exact fractions: normalization (all raw sums 8-40, clipping, rounding of 28.125 -> 28.12), membership (grid + points around breakpoints, partition of unity), per-dimension overlap, main-dimension selection incl. ties (e.g. Ilmu Hukum: I = S = 0.5 -> I), the three firing strengths, MIN/MAX aggregation at 101 points, centroid (incl. zero denominator), distance score, Holland code ties, band boundaries, alphabetical tie-break, uniform-profile detection, and 800 profile x program pairs end to end. Full-precision vs. stored two-decimal inputs are reported separately (alphaModerate 0.8750 vs 0.8752; centroid 37.0078 vs 37.0089; both display as 37.01). | 139 |
| `self_matching.py` | Each target x 100 used as user profile: own score exactly 100.00, rank 1, nearest other program and margin; no identical target vectors. | 22 |
| `blackbox_tests.py` | Flask test client on a fresh temporary SQLite file: access/route protection, registration, 48-item page, incomplete and invalid submissions (value, expected message after redirect, 47 other answers valid, nothing stored), boundary and uniform patterns (all 1-5), non-uniform case, interface text, history, role protection, data isolation between users, centroid visible only on the admin detail page, and that manipulating the centroid (constant 0 / 100 / inverted) leaves ranking and scores unchanged (direct calls and full HTTP flow). | 46 |

## Database initialisation and test order (`blackbox_tests.py`)
1. A temporary folder and an empty SQLite file are created; `database.DB_PATH` is pointed to it
   before `app.py` is imported (no `DATABASE_URL`).
2. Importing `app.py` runs `database.init_db()`: tables `users`, `hasil_tes`, plus the admin
   account from `ADMIN_EMAIL` / `ADMIN_PASSWORD` (set by the script). Scenario S0 asserts this.
3. Scenarios run in the order of their ids (S0, S1, ... S19) on that single database; each invalid
   case compares the stored-result count before and after.

## Logs (`logs/`)
`initial/` = run on the repository before these changes (code hash in `initial_manifest.json`);
`final/` = run on the code in this tree (`final_manifest.json`). Per suite: `.txt` (one line per
check: input, expected, observed, status), `.csv`, `.json`; `final_self_matching_table.csv` lists
all 20 cases. The manifest holds SHA-256 hashes of every file under `backend/` and `frontend/`.
Environment of both runs: Python 3.12.3, Flask 3.0.3, Werkzeug 3.1.9.

| Suite | initial | final |
|---|---|---|
| numeric | 124/139 | 139/139 |
| self-matching | 22/22 | 22/22 |
| black-box | 26/46 | 46/46 |
