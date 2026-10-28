#!/usr/bin/env bash
# Regression check: the hand calculation and the generated OpenFOAM case of every case YAML
# must be unchanged against a baseline git ref (default v0.1.0).
#   .github/regression.sh            compare the working tree against v0.1.0
#   .github/regression.sh REF        compare against another ref (tag, branch, commit)
# Cases: every *.yaml under assets/ and evals/ in the working tree. A case missing from the
# baseline is run on the working tree only and reported "new" (not a failure). The baseline
# side uses the baseline's own copy of the YAML, so a changed YAML shows up as a difference.
# Prints one line per case (same / DIFF (hand calc) / DIFF (case: files) / new) and exits 1
# if any case differs. Nothing is written into the repo: the baseline is a temporary
# detached worktree under a mktemp directory, removed on exit.
set -euo pipefail
ref=${1:-v0.1.0}
repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo"
git rev-parse -q --verify "$ref^{commit}" >/dev/null || { echo "unknown ref: $ref" >&2; exit 2; }

tmp=$(mktemp -d)
base="$tmp/base"
cleanup() {
    git -C "$repo" worktree remove --force "$base" >/dev/null 2>&1 || true
    git -C "$repo" worktree prune >/dev/null 2>&1 || true
    rm -rf "$tmp"
}
trap cleanup EXIT
git worktree add -q --detach "$base" "$ref"
export LC_ALL=C PYTHONDONTWRITEBYTECODE=1
# make_case.py iterates a Python set of region pairs when it writes the interface patches of
# 0/<region>/T, so their order follows string hashing and changes from run to run (the
# entries are named, so OpenFOAM does not care). A fixed hash seed on both sides makes the
# order reproducible; any change in the set of interfaces or their contents still shows.
export PYTHONHASHSEED=0

# run TREE SIDE CASE_ID YAML_REL: hand calc and case generation from TREE's scripts on TREE's
# copy of the YAML. make_case.py runs with the output directory's parent as working directory
# and the relative output path "case", so both sides get identical arguments. The generated
# case files embed no absolute paths or timestamps (checked: case-meta.json, Allrun,
# system/controlDict), so they are compared byte for byte. A tool's exit status and stderr
# are recorded too, so an eval YAML that is not a case file (the tools reject it) is still
# compared; Python tracebacks name the script paths, which are replaced by <TREE> (both the
# path as given and with symlinks resolved).
run() {
    local tree=$1 out="$tmp/$2/$3" yaml="$1/$4" real rc
    real=$(cd "$tree" && pwd -P)
    mkdir -p "$out"
    rc=0; python3 "$tree/scripts/hand_calc.py" "$yaml" >"$out/hand.raw" 2>&1 || rc=$?
    echo "exit $rc" >>"$out/hand.raw"
    rc=0; (cd "$out" && python3 "$tree/scripts/make_case.py" "$yaml" case --resolution coarse) \
        >"$out/make.raw" 2>&1 || rc=$?
    echo "exit $rc" >>"$out/make.raw"
    for f in hand make; do
        TREE="$tree" REAL="$real" python3 -c '
import os, sys
s = sys.stdin.read()
for p in sorted({os.environ["TREE"], os.environ["REAL"]}, key=len, reverse=True):
    s = s.replace(p, "<TREE>")
sys.stdout.write(s)' <"$out/$f.raw" >"$out/$f.txt"
    done
}

# same_yaml A B: true if two YAML files parse to the same data (they differ in comments or
# layout only)
same_yaml() {
    python3 -c 'import sys, yaml; a, b = (yaml.safe_load(open(p)) for p in sys.argv[1:]); sys.exit(a != b)' "$1" "$2"
}

fail=0
while IFS= read -r -d '' yaml; do
    yaml=${yaml#./}
    id=${yaml//\//__}
    run "$repo" work "$id" "$yaml"
    if [ ! -f "$base/$yaml" ]; then
        printf '%-48s new (no baseline in %s)\n' "$yaml" "$ref"
        continue
    fi
    run "$base" base "$id" "$yaml"
    w="$tmp/work/$id" b="$tmp/base/$id" res=() notes=()
    diff -u "$b/hand.txt" "$w/hand.txt" >"$tmp/$id.hand.diff" || res+=("DIFF (hand calc)")
    files=()
    diff -q "$b/make.txt" "$w/make.txt" >/dev/null || files+=("make_case output")
    if [ -d "$b/case" ] || [ -d "$w/case" ]; then
        while IFS= read -r line; do
            case $line in
                "Files "*)
                    f=${line#Files "$b/case/"}; f=${f%% and *}
                    # case.yaml is a verbatim copy of the input: a comment-only edit is noted
                    if [ "$f" = case.yaml ] && same_yaml "$b/case/$f" "$w/case/$f"; then
                        notes+=("input YAML differs in comments/layout only")
                    else
                        files+=("$f")
                    fi ;;
                "Only in "*) files+=("only in ${line#Only in "$tmp/"}") ;;
                *) files+=("$line") ;;
            esac
        done < <(diff -rq "$b/case" "$w/case" 2>&1 || true)
    fi
    [ ${#files[@]} -eq 0 ] || res+=("DIFF (case: $(IFS=,; echo "${files[*]}" | sed 's/,/, /g'))")
    if [ ${#res[@]} -eq 0 ]; then
        grep -qx 'exit 0' "$w/hand.txt" && grep -qx 'exit 0' "$w/make.txt" ||
            notes+=("not a case file: both sides reject it identically")
        printf '%-48s same%s\n' "$yaml" "${notes[*]:+ (${notes[*]})}"
    else
        fail=1
        printf '%-48s %s\n' "$yaml" "${res[*]}"
        [ -s "$tmp/$id.hand.diff" ] && sed 's/^/    /' "$tmp/$id.hand.diff"
    fi
done < <(find assets evals -name '*.yaml' -type f -print0 | sort -z)
exit $fail
