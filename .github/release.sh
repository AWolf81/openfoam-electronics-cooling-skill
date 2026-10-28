#!/usr/bin/env bash
# Cut a release: VERSION, CHANGELOG section with the package hash, README hash table, commit,
# annotated tag. The Release workflow then recomputes the hash on GitHub, refuses to publish if it
# differs, and creates the GitHub release with the notes and SHA256SUMS.
#   .github/release.sh 0.2.0           prepare commit and tag locally
#   .github/release.sh 0.2.0 --push    and push main and the tag
set -euo pipefail
ver=${1:?usage: release.sh X.Y.Z [--push]}
[[ "$ver" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "version must be X.Y.Z" >&2; exit 2; }
cd "$(dirname "$0")/.."
[ -z "$(git status --porcelain)" ] || { echo "working tree not clean" >&2; exit 1; }
[ "$(git branch --show-current)" = main ] || { echo "not on main" >&2; exit 1; }
git rev-parse -q --verify "refs/tags/v$ver" >/dev/null && { echo "tag v$ver exists" >&2; exit 1; }

printf '%s\n' "$ver" > VERSION
hash=$(.github/package-hash.sh)
python3 - "$ver" "$hash" "$(date +%F)" <<'PY'
import re, sys
ver, h, today = sys.argv[1:]
repo = "https://github.com/AWolf81/openfoam-electronics-cooling-skill"
c = open("CHANGELOG.md").read()
if f"## [{ver}]" not in c:   # move Unreleased into a new version section
    c = c.replace("## [Unreleased]\n", f"## [Unreleased]\n\n## [{ver}] - {today}\n\nPackage SHA-256: `<!-- package-sha256 -->`\n", 1)
    prev = re.search(r"^\[(\d+\.\d+\.\d+)\]: ", c, re.M)
    c = re.sub(r"^\[Unreleased\]: .*$", f"[Unreleased]: {repo}/compare/v{ver}...HEAD", c, flags=re.M)
    link = f"[{ver}]: {repo}/compare/v{prev.group(1)}...v{ver}" if prev else f"[{ver}]: {repo}/releases/tag/v{ver}"
    c = c.replace(f"[Unreleased]: {repo}/compare/v{ver}...HEAD", f"[Unreleased]: {repo}/compare/v{ver}...HEAD\n{link}", 1)
sec = c.index(f"## [{ver}]")
end = c.find("\n## [", sec + 1)
end = len(c) if end < 0 else end
c = c[:sec] + re.sub(r"Package SHA-256: `[^`]*`", f"Package SHA-256: `{h}`", c[sec:end], count=1) + c[end:]
open("CHANGELOG.md", "w").write(c)
r = open("README.md").read()
a, b = r.index("<!-- package-sha256:start -->"), r.index("<!-- package-sha256:end -->")
rows = [l for l in r[a:b].splitlines()[3:] if l.startswith("|") and not l.startswith(f"| {ver} |")]
table = "<!-- package-sha256:start -->\n| Version | Package SHA-256 |\n|---|---|\n" + \
        "\n".join([f"| {ver} | `{h}` |"] + rows) + "\n"
open("README.md", "w").write(r[:a] + table + r[b:])
r = open("README.md").read()
r = re.sub(r"git clone --branch v\d+\.\d+\.\d+ ", f"git clone --branch v{ver} ", r)
r = re.sub(r"`--branch v\d+\.\d+\.\d+`", f"`--branch v{ver}`", r)
open("README.md", "w").write(r)
PY
[ "$(.github/package-hash.sh)" = "$hash" ] || { echo "hash changed while writing README/CHANGELOG" >&2; exit 1; }
git add -A
git commit -q -m "Release v$ver

Package SHA-256: $hash"
git tag -a "v$ver" -m "v$ver

Package SHA-256: $hash"
echo "v$ver  package SHA-256 $hash"
if [ "${2:-}" = "--push" ]; then git push -q origin main "v$ver"; echo "pushed main and v$ver"; else echo "push with: git push origin main v$ver"; fi
