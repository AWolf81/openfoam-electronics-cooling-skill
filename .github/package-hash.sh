#!/usr/bin/env bash
# SHA-256 of the skill package: every file the skill uses, in byte order of their paths.
# Left out: README.md and CHANGELOG.md (they carry this hash), .git/, .github/ (CI only),
# .planning/ (GSD planning, not part of the skill) and
# Python's __pycache__. The same one-liner is in README.md, so a copy can be checked without
# trusting any script in it.
#   .github/package-hash.sh [DIR]        prints the package hash
#   .github/package-hash.sh --list [DIR] prints the per-file SHA256SUMS
set -euo pipefail
list=0
[ "${1:-}" = "--list" ] && { list=1; shift; }
cd "${1:-$(dirname "$0")/..}"
if command -v sha256sum >/dev/null; then sum=(sha256sum); else sum=(shasum -a 256); fi
files() {
    find . -type f ! -path './.git/*' ! -path './.github/*' ! -path './.planning/*' ! -path '*/__pycache__/*' \
        ! -name '*.pyc' ! -name README.md ! -name CHANGELOG.md -print0 | LC_ALL=C sort -z
}
if [ $list = 1 ]; then files | xargs -0 "${sum[@]}"; else files | xargs -0 "${sum[@]}" | "${sum[@]}" | cut -d' ' -f1; fi
