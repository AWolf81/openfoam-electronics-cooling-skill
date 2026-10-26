#!/usr/bin/env bash
# Run a command inside the OpenFOAM v2412 container with a case directory mounted.
#
#   scripts/of.sh <case-dir> ./Allrun
#   scripts/of.sh <case-dir> foamLog log.chtMultiRegionSimpleFoam
#
# Env: OF_IMAGE (default opencfd/openfoam-default:2412), OF_CPUS (docker --cpus limit).
# Uses the current Docker context; if that daemon is down (for example Docker Desktop is
# off) and the system engine socket exists, it falls back to the system engine.
set -euo pipefail

case_dir=${1:?usage: of.sh <case-dir> <command...>}
shift
[ $# -gt 0 ] || { echo "usage: of.sh <case-dir> <command...>" >&2; exit 2; }
[ -d "$case_dir" ] || { echo "no such case directory: $case_dir" >&2; exit 2; }
image=${OF_IMAGE:-opencfd/openfoam-default:2412}

if ! docker info >/dev/null 2>&1; then
    if [ -S /var/run/docker.sock ] && DOCKER_HOST=unix:///var/run/docker.sock docker info >/dev/null 2>&1; then
        export DOCKER_HOST=unix:///var/run/docker.sock
        echo "of.sh: current Docker context is down, using the system engine" >&2
    else
        echo "of.sh: no Docker daemon reachable (start Docker Desktop or the docker service)" >&2
        exit 3
    fi
fi

if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "of.sh: pulling $image (about 2.2 GB, once)" >&2
    docker pull "$image" >&2
fi

abs=$(cd "$case_dir" && pwd)
extra=()
[ -n "${OF_CPUS:-}" ] && extra+=(--cpus "$OF_CPUS")

# Run as the calling user so results are not root-owned; MPI needs a writable HOME.
exec docker run --rm -i \
    -u "$(id -u):$(id -g)" -e HOME=/tmp -e OMPI_MCA_rmaps_base_oversubscribe=1 \
    --shm-size=1g "${extra[@]}" \
    -v "$abs":/case -w /case \
    "$image" bash -c "cd /case && $(printf '%q ' "$@")"   # the image entrypoint changes directory
