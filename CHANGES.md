# CHANGES (revision after editorial assessment)

Base: the public `main` branch of this repository (3 commits; no validation of answers, old
suitability labels, no evaluation scripts). Every change below is exercised by the scripts in
`evaluation/`; the logs of the run on the previous code (`evaluation/logs/initial`) and on this
code (`evaluation/logs/final`) are included.

## Application
- **Answer validation (server side).** `/proses` accepts only integer answers 1-5 (ASCII digits,
  no sign/space/decimal). Anything else redirects to `/tes` with a message naming the item
  ("Jawaban pertanyaan nomor N tidak valid; pilih angka 1 sampai 5."); nothing is stored.
  Previously 0, 9, -1 were accepted and a non-numeric value caused an unhandled error (HTTP 500).
- **Interpretation labels.** Bands are now "Kemiripan Sangat Tinggi / Tinggi / Sedang / Rendah /
  Sangat Rendah" (heuristic similarity bands, thresholds unchanged: 85/70/55/40) instead of
  "Sangat Cocok ... Sangat Tidak Cocok". Scores are shown as "x / 100", not "%". The result page
  states that the score is not a probability, that the bands are heuristic, and that ranking is
  determined only by profile distance.
- **Undifferentiated profiles.** If all six stored scores are identical (`logic/scoring.py:
  profil_seragam`), the result page shows a warning, hides the Holland code and the per-program
  band labels. The code `RIA` for such profiles comes only from the fixed tie-break order
  R, I, A, S, E, C. The similarity score of a uniform profile reflects only the answer level
  (e.g. all-lowest answers still give a top score of 70.0), not an interest pattern.
- **Tie-breaking made explicit.** `kode_holland_dominan` sorts by (-score, position in R,I,A,S,E,C)
  instead of relying on dict order. Results are unchanged for canonical dict order; with a
  shuffled dict the previous code returned a different code for tied scores (test H7).
- **Auxiliary fuzzy calculation.** "Fuzzy audit" wording is replaced by "auxiliary fuzzy
  calculation" in code comments and UI. The Mamdani centroid is computed for every program, stored
  with the five returned recommendations, and shown **only** on the administrator detail page
  (`/admin/hasil/<id>`, previously the page did not render it) with the label that it does not
  affect order or score. It is not shown to ordinary users and is never part of the sort key.
- **Wording.** "Tes Kepribadian" (personality) -> "Tes Minat" (interest) on the landing, test and
  footer text; the landing headline no longer says "paling cocok" (most suitable).
- README: removed stray citation markers; added the evaluation section.

## Evaluation (new, `evaluation/`)
`verify_numeric.py` (139 checks against an independent exact-arithmetic reference),
`self_matching.py` (20 profiles), `blackbox_tests.py` (46 checks, Flask test client, temporary
database), `run_all.py` (runs all, writes logs and a code manifest). See `evaluation/README.md`.

## Tested environment
Python 3.12.3, Flask 3.0.3 (the version pinned in `backend/requirements.txt`), Werkzeug 3.1.9
(resolved from the unpinned range `>=3.0,<4.0`), SQLite. Not tested: Python 3.13 (used in
`render.yaml`), the PostgreSQL code path, and the deployed Render service.

## Scope
These checks verify implementation consistency and software behaviour. They are not evidence of
recommendation validity, individual suitability or user acceptance. The Indonesian item set and the
20x6 target matrix remain unvalidated.
