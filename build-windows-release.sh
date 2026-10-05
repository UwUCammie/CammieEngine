#!/usr/bin/env bash
# Build and package a Windows x64 release from this Linux checkout.
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

TAG="${1:-v$(tr -d '\r\n' < VERSION)}"
if [[ "$TAG" == "-h" || "$TAG" == "--help" ]]; then
	cat <<'EOF'
Usage: ./build-windows-release.sh [release-tag] [--wine-smoke]

Builds Windows x64 with the local LLVM-MinGW toolchain (or a configured/system
MinGW compiler), checks the bundled results pack, and writes a clean ZIP plus
SHA256SUMS.txt to dist/. The optional Wine check runs offscreen after building.
EOF
	exit 0
fi
if [[ $# -gt 2 || ( $# -eq 2 && "$2" != "--wine-smoke" ) ]]; then
	echo "Invalid arguments; see ./build-windows-release.sh --help" >&2
	exit 2
fi

RESULTS_ROOT="$ROOT/assets/imported_mods/bundled-vslice-results"
[[ -f "$RESULTS_ROOT/pack.json" && -f "$RESULTS_ROOT/scripts/results.lua" ]] || {
	echo "Bundled results screen is missing from this source checkout." >&2
	exit 1
}

./run.sh setup

LOCAL_COMPILER="$ROOT/.tools/llvm-mingw/bin/x86_64-w64-mingw32-clang++"
if [[ -z "${HXCPP_MINGW_EXE:-}" && -x "$LOCAL_COMPILER" ]]; then
	export HXCPP_MINGW_EXE="$LOCAL_COMPILER"
	export MINGW_ROOT="$ROOT/.tools/llvm-mingw"
fi

./build.sh windows
if [[ "${2:-}" == "--wine-smoke" ]]; then
	./build.sh wine-smoke --skip-build
fi

python3 tools/package_windows_release.py \
	--runtime export/release/windows/bin \
	--output-dir dist \
	--tag "$TAG"

echo "Windows ZIP and checksum are ready in $ROOT/dist/"
