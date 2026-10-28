---
phase: 01-baseline-and-validation-fixes
plan: 01
subsystem: testing
tags: [regression, bash, git-worktree, hand_calc, make_case, shellcheck]

requires: []
provides:
  - ".github/regression.sh [REF]: per-case comparison of hand calc and generated case files against v0.1.0 (or any ref)"
  - "Clean baseline run on develop: every existing case same, validation-plate-fin new"
affects: [every later v0.2.0 plan that must prove 'default case unchanged vs v0.1.0']

tech-stack:
  added: []
  patterns:
    - "Baseline via temporary detached git worktree under mktemp, removed by trap"
    - "PYTHONHASHSEED=0 for reproducible make_case.py output"

key-files:
  created: [.github/regression.sh]
  modified: []

key-decisions:
  - "Fix PYTHONHASHSEED=0 on both sides: make_case.py writes interface patches of 0/<region>/T in Python set order"
  - "Tool exit status and stderr are compared too; tree paths in tracebacks replaced by <TREE>"
  - "case.yaml copies that differ only in comments/layout (parsed YAML equal) are reported as a note on a 'same' line, not as DIFF"
  - "codeql.yml left unchanged: its ShellCheck glob .github/*.sh already covers the script"

patterns-established:
  - "Proof of no change: run .github/regression.sh, exit 0 with every existing case 'same'"

duration: 8min
completed: 2026-10-28
---

# Phase 01 Plan 01: Regression Harness Summary

**`.github/regression.sh` runs hand_calc.py and make_case.py (coarse) from a temporary v0.1.0 worktree and from the working tree on all 7 case YAMLs and reports per-case same/DIFF/new; it is clean on develop, catches a one-digit correlation change, and takes about 2.5 s**

## Performance

- **Duration:** about 8 min
- **Started:** 2026-10-28T22:34+01:00
- **Completed:** 2026-10-28T22:42+01:00
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments

- One command (`.github/regression.sh [REF]`, default `v0.1.0`) compares every `assets/**/*.yaml` and `evals/**/*.yaml` against the baseline, one line per case, exit 1 on any DIFF. Nothing is written into the repo, and no worktree or temp directory is left behind (checked with `git worktree list`).
- First run on develop (exit 0):
  ```
  assets/example-case.yaml                         same (input YAML differs in comments/layout only)
  assets/validation-plate-fin.yaml                 new (no baseline in v0.1.0)
  evals/b2b-mosfet-hand-calc/case.yaml             same (not a case file: both sides reject it identically)
  evals/build-and-smoke-test-case/case.yaml        same (not a case file: both sides reject it identically)
  evals/build-and-smoke-test-case/files/case.yaml  same
  evals/fan-cooled-hand-calc/case.yaml             same (not a case file: both sides reject it identically)
  evals/vague-request-asks-inputs/case.yaml        same (not a case file: both sides reject it identically)
  ```
- Negative test: Elenbaas constant 576.0 -> 577.0 in `scripts/cooling_model.py`; exit 1, and both real cases were named:
  `assets/example-case.yaml` and `evals/build-and-smoke-test-case/files/case.yaml` -> `DIFF (hand calc) DIFF (case: 0/heatsink/T, 0/ims/T, 0/q1/T, 0/q2/T, case-meta.json, system/q1/fvOptions, system/q2/fvOptions)`. After undoing the edit, `git status` was clean and the next run exited 0.
- Runtime of a full run: 2.3-2.7 s wall clock.

## Task Commits

1. **Task 1: Write .github/regression.sh** - `5382861` (feat)
2. **Task 2: First run and a negative test** - no commit (verification only; no files changed)

**Plan metadata:** see the `docs(01-01): complete regression harness plan` commit

## Files Created/Modified

- `.github/regression.sh` - regression check against a git ref (outside the hashed package)

## Decisions Made

See key-decisions in the frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] make_case.py output depends on the Python hash seed**
- **Found during:** Task 2 (first run)
- **Issue:** `0/<region>/T` differed between two runs of the same code: `make_case.py` builds `pairs` (region interfaces) as a set of string tuples and iterates it to write the patch entries, so their order follows string hashing. OpenFOAM looks the entries up by name, so physics is unaffected, but a byte compare fails at random.
- **Fix:** the script exports `PYTHONHASHSEED=0` for both sides (documented in a comment). The package code was not changed (out of scope for this plan and it would change the package hash and generated output relative to v0.1.0).
- **Files modified:** .github/regression.sh
- **Verification:** seeds 0,0 gave identical files and seeds 1,2,3 gave different ones; with the fixed seed, repeated runs are clean.
- **Committed in:** 5382861

**2. [Rule 1 - Bug] Absolute script paths in tracebacks, and the diff locale**
- **Found during:** Task 2 (first run)
- **Issue:** four eval YAMLs are eval specs, not case files, so both tools exit with a traceback that contains the tree path (the working tree also appears with symlinks resolved, `/media/...`). German diff messages broke the file-name parsing.
- **Fix:** the tool stdout, stderr and exit status are recorded and compared after replacing both forms of the tree path with `<TREE>`. `LC_ALL=C` is set. Such cases report `same (not a case file: both sides reject it identically)`.
- **Committed in:** 5382861

**3. [Rule 2 - Missing] Comment-only change to the example YAML**
- **Found during:** Task 2
- **Issue:** `assets/example-case.yaml` gained a comment line since v0.1.0 (FIX-02, plan 01-02), so the copied `case/case.yaml` differs byte-wise although every generated file is identical.
- **Fix:** if only `case.yaml` differs and both parse to equal YAML data, the case is reported `same (input YAML differs in comments/layout only)`. Any change to a value is still a DIFF.
- **Committed in:** 5382861

---

**Total deviations:** 3 auto-fixed (2 Rule 1, 1 Rule 2), all inside .github/regression.sh.
**Impact on plan:** these were needed for a correct comparison. No real difference is hidden.

## Issues Encountered

- The safety hook blocked `git restore`, so the negative-test edit was undone with the Edit tool (exact reverse edit); `git status` was clean afterwards.
- The package hash is `ae708ed8...834eb` after this plan, not `eececc59...a95`. The change comes from 01-02's parallel commits (SKILL.md, assets/example-case.yaml). `.github/` is excluded from the hash (`package-hash.sh --list` shows no `.github` entry), so this plan does not affect it.

## User Setup Required

None. Needs python3 with PyYAML (already needed by the scripts) and git.

## Next Phase Readiness

- Later plans can run `.github/regression.sh` as their proof of no change for existing cases.
- Concern: if a later plan makes `make_case.py` deterministic (for example `for p, q in sorted(pairs)`), the patch order in `0/<region>/T` will differ from the v0.1.0 baseline under seed 0. That plan should then show the change is order-only (or compare against a ref that already has the fix).

---
*Phase: 01-baseline-and-validation-fixes*
*Completed: 2026-10-28*
