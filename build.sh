#!/usr/bin/env bash
# Cross-platform build entry point for Disappointing Plus.
#
#   ./build.sh linux [debug] [--skip-build]
#   ./build.sh appimage [debug] [--skip-build]
#   ./build.sh windows [debug] [--skip-build] [--wine-smoke]
#   ./build.sh wine-smoke [debug] [--skip-build] [--timeout seconds]
#
# Linux builds are delegated to run.sh so that the portable toolchain,
# haxelib pins, asset setup, and runtime lock stay in one place. Windows
# remains a native run.bat build on a Windows POSIX shell; on Linux this entry
# point uses hxcpp's supported MinGW cross-toolchain. Wine is only an optional
# post-build launch smoke test, never the compiler.
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Packaging tools can need considerably more scratch space than the system
# tmpfs provides.  Keep their temporary output beside the project instead.
PROJECT_TMP="$ROOT/tmp"
mkdir -p "$PROJECT_TMP"
export TMPDIR="$PROJECT_TMP"

usage() {
	cat <<'USAGE'
Usage:
  ./build.sh linux [debug] [--skip-build]
  ./build.sh appimage [debug] [--skip-build]
  ./build.sh windows [debug] [--skip-build] [--wine-smoke] [--timeout seconds]
  ./build.sh wine-smoke [debug] [--skip-build] [--timeout seconds]

Targets:
  linux       Build the native Linux executable with run.sh.
  appimage    Build Linux, then package export/<mode>/linux/bin as an AppImage.
  windows     Build a Windows executable with hxcpp MinGW on Linux, or
              delegate to run.bat from native Windows/MSYS/Cygwin.
  wine-smoke  Launch an existing/new Linux-host Windows build through Wine;
              a timeout is treated as a live-startup result, while early
              non-zero exits are reported as crashes.

Options:
  debug         Build into export/debug and enable Lime's debug build.
  --skip-build  Reuse an existing target executable (appimage/windows).
  --wine-smoke  After a Linux-host Windows build, run a bounded Wine smoke.
  --timeout N   Wine smoke timeout in seconds (default: 30).

Linux Windows prerequisites:
  Run ./run.sh setup once to install the pinned portable Haxe/haxelib setup,
  install either a 64-bit GCC MinGW-w64 toolchain
  (x86_64-w64-mingw32-g++) or the self-contained LLVM-MinGW toolchain
  (x86_64-w64-mingw32-clang++), and set MINGW_ROOT when it is not the
  standard /usr/x86_64-w64-mingw32 sysroot. Set HXCPP_MINGW_EXE to use a
  different triplet compiler. Wine and GNU timeout are required only for the
  --wine-smoke mode.
USAGE
}

die() {
	echo "!! $*" >&2
	exit 1
}

require_executable() {
	local path="$1"
	local hint="$2"
	[[ -x "$path" ]] || die "$hint (missing or not executable: $path)"
}

require_file() {
	local path="$1"
	local hint="$2"
	[[ -f "$path" && -r "$path" ]] || die "$hint (missing or unreadable: $path)"
}

resolve_command() {
	local requested="$1"
	local label="$2"
	if [[ "$requested" == */* ]]; then
		local resolved="$requested"
		if [[ "$resolved" != /* ]]; then
			resolved="$ROOT/$resolved"
		fi
		require_executable "$resolved" "$label"
		printf '%s\n' "$resolved"
		return
	fi
	command -v "$requested" >/dev/null 2>&1 || die "$label '$requested' was not found on PATH"
	command -v "$requested"
}

ensure_portable_toolchain() {
	local tools="$ROOT/.tools"
	local haxe_path="$tools/haxe"
	local neko_path="$tools/neko"
	local haxelib_root="$ROOT/.haxelib"
	require_executable "$haxe_path/haxe" "portable Haxe 4.3.x is missing; run ./run.sh setup once to bootstrap the project toolchain"
	require_executable "$haxe_path/haxelib" "portable haxelib is missing; run ./run.sh setup once to bootstrap the project toolchain"
	require_executable "$neko_path/neko" "portable Neko is missing; run ./run.sh setup once to bootstrap the project toolchain"
	[[ -d "$haxelib_root" ]] || die "pinned haxelibs are missing at $haxelib_root; run ./run.sh setup once before a cross-build"
	[[ -d "$haxelib_root/lime/8,3,2" ]] || die "pinned Lime 8.3.2 is missing; run ./run.sh setup once before a cross-build"
	[[ -d "$haxelib_root/hxcpp/4,3,2" ]] || die "pinned hxcpp 4.3.2 is missing; run ./run.sh setup once before a cross-build"

	export HAXEPATH="$haxe_path"
	export NEKOPATH="$neko_path"
	export HAXELIB_PATH="$haxelib_root"
	export PATH="$HAXEPATH:$NEKOPATH:$PATH"
	if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
		export LD_LIBRARY_PATH="$NEKOPATH:$HAXEPATH:$LD_LIBRARY_PATH"
	else
		export LD_LIBRARY_PATH="$NEKOPATH:$HAXEPATH"
	fi
	command -v haxelib >/dev/null 2>&1 || die "portable haxelib could not be resolved after setting HAXEPATH=$HAXEPATH"
	local haxe_version
	haxe_version="$(haxe --version 2>/dev/null || true)"
	[[ "$haxe_version" == 4.3.* ]] || die "expected portable Haxe 4.3.x, found '${haxe_version:-unavailable}'; run ./run.sh setup to repair .tools"
}

ensure_mingw_toolchain() {
	local triplet="${HXCPP_MINGW_TRIPLET:-x86_64-w64-mingw32}"
	local requested_compiler="${HXCPP_MINGW_EXE:-}"
	local compiler="${requested_compiler:-$triplet-g++}"
	local resolved_compiler=""
	local compiler_dir=""
	local tool_dir=""
	local candidate=""
	local root_value="${MINGW_ROOT:-}"
	local inferred_root=""
	local compiler_sysroot=""
	local compiler_target=""
	local compiler_family="gcc"
	local target_tool=""
	local target_tool_path=""

	[[ "$(uname -s)" == "Linux" ]] || die "Linux-host Windows cross-builds require a Linux host; use run.bat for native Windows"
	[[ "$triplet" == x86_64-w64-mingw32 ]] || die "this entry point currently targets 64-bit MinGW; use HXCPP_MINGW_TRIPLET=x86_64-w64-mingw32 or native run.bat for another architecture"

	# Prefer an explicitly supplied compiler path, then a compiler inside the
	# supplied sysroot, and finally the canonical triplet name on PATH. Never
	# accept the host g++ implicitly: it would produce a Linux binary. The
	# CachyOS/Arch llvm-mingw package exposes the same target triplet with a
	# clang++ suffix, so use it only after the GCC compiler is absent.
	if [[ "$compiler" == */* ]]; then
		require_executable "$compiler" "HXCPP_MINGW_EXE is not executable"
		resolved_compiler="$compiler"
		compiler_dir="$(dirname "$compiler")"
	else
		if [[ -n "$root_value" && -x "$root_value/bin/$compiler" ]]; then
			resolved_compiler="$root_value/bin/$compiler"
			compiler_dir="$root_value/bin"
		elif command -v "$compiler" >/dev/null 2>&1; then
			resolved_compiler="$(command -v "$compiler")"
			compiler_dir="$(dirname "$resolved_compiler")"
		elif [[ -z "$requested_compiler" ]]; then
			compiler="$triplet-clang++"
			if [[ -n "$root_value" && -x "$root_value/bin/$compiler" ]]; then
				resolved_compiler="$root_value/bin/$compiler"
				compiler_dir="$root_value/bin"
			elif command -v "$compiler" >/dev/null 2>&1; then
				resolved_compiler="$(command -v "$compiler")"
				compiler_dir="$(dirname "$resolved_compiler")"
			fi
		else
			die "MinGW compiler '$compiler' was not found; install GCC '$triplet-g++' or LLVM-MinGW '$triplet-clang++', or set HXCPP_MINGW_EXE=/path/to/compiler"
		fi
	fi
	[[ -n "$resolved_compiler" ]] || die "MinGW compiler was not found; install GCC '$triplet-g++' or LLVM-MinGW '$triplet-clang++', or set HXCPP_MINGW_EXE=/path/to/compiler"
	if [[ "$(basename "$resolved_compiler")" == *clang* ]]; then
		compiler_family="llvm-mingw"
	fi

	# hxcpp's Linux toolchain expects MINGW_ROOT to be the triplet sysroot,
	# not merely the directory containing the compiler executable. Infer only
	# conventional triplet roots; custom layouts must be explicit.
	if [[ -z "$root_value" ]]; then
		compiler_sysroot="$("$resolved_compiler" -print-sysroot 2>/dev/null || true)"
		if [[ -n "$compiler_sysroot" && -d "$compiler_sysroot/$triplet/include" && -d "$compiler_sysroot/$triplet/lib" ]]; then
			inferred_root="$compiler_sysroot/$triplet"
		elif [[ -n "$compiler_sysroot" && -d "$compiler_sysroot/include" && -d "$compiler_sysroot/lib" && "$compiler_family" != "llvm-mingw" ]]; then
			inferred_root="$compiler_sysroot"
		fi
		tool_dir="$(dirname "$resolved_compiler")"
		if [[ -z "$inferred_root" ]]; then
			for candidate in \
				"$(dirname "$tool_dir")" \
				"$(dirname "$tool_dir")/$triplet" \
				"/usr/$triplet" \
				"/usr/local/$triplet"; do
				if [[ "$(basename "$candidate")" == "$triplet" && \
					-d "$candidate/include" && -d "$candidate/lib" ]]; then
					inferred_root="$candidate"
					break
				fi
			done
		fi
		root_value="$inferred_root"
	fi
	# A self-contained LLVM-MinGW archive uses PREFIX/bin for the wrappers and
	# PREFIX/<triplet>/{include,lib} for its target sysroot. Accept PREFIX in
	# MINGW_ROOT for that layout, then normalize to the target root hxcpp expects.
	if [[ -n "$root_value" && -d "$root_value/$triplet/include" && \
		-d "$root_value/$triplet/lib" ]]; then
		root_value="$root_value/$triplet"
	fi
	[[ -n "$root_value" ]] || die "could not infer MINGW_ROOT for '$resolved_compiler'; set MINGW_ROOT to the MinGW sysroot (for example /usr/$triplet)"
	[[ -d "$root_value" ]] || die "MINGW_ROOT does not exist: $root_value"
	[[ -d "$root_value/include" && -d "$root_value/lib" ]] || die "MINGW_ROOT must be a MinGW sysroot containing include/ and lib/: $root_value"

	# Put the sysroot tools first for hxcpp's gcc/ar/ranlib lookups. Keep the
	# compiler's basename as HXCPP_MINGW_EXE so paths containing spaces remain
	# a single environment value and the toolchain can resolve its siblings.
	if [[ -d "$root_value/bin" ]]; then
		export PATH="$root_value/bin:$PATH"
	fi
	if [[ -n "$compiler_dir" && -d "$compiler_dir" ]]; then
		export PATH="$compiler_dir:$PATH"
	fi
	if [[ "$compiler" == */* ]]; then
		compiler="$(basename "$compiler")"
	fi
	export MINGW_ROOT="$root_value"
	export HXCPP_MINGW_EXE="$compiler"
	command -v "$HXCPP_MINGW_EXE" >/dev/null 2>&1 || die "MINGW_ROOT is set but '$HXCPP_MINGW_EXE' is not resolvable; check $MINGW_ROOT/bin or PATH"
	resolved_compiler="$(command -v "$HXCPP_MINGW_EXE")"
	"$resolved_compiler" --version >/dev/null 2>&1 || die "MinGW compiler '$resolved_compiler' could not run; repair the toolchain or set HXCPP_MINGW_EXE to a working compiler"
	compiler_target="$("$resolved_compiler" -dumpmachine 2>/dev/null || true)"
	case "$compiler_target" in
		x86_64-w64-mingw32*|x86_64-w64-windows-gnu*|x86_64-pc-windows-gnu*) ;;
		*) die "MinGW compiler '$resolved_compiler' targets '${compiler_target:-unknown}', not a 64-bit MinGW/LLVM-MinGW target; set HXCPP_MINGW_EXE to the 64-bit triplet compiler" ;;
	esac
	if [[ "$compiler_family" == "llvm-mingw" ]]; then
		# Remember this for the Lime/hxcpp invocation below.  LLVM-MinGW's
		# clang driver deliberately does not treat a .rc file as a resource,
		# unlike the MinGW GCC driver; hxcpp therefore needs llvm-windres for
		# the generated ApplicationMain.rc entry.
		export DP_LLVM_MINGW=1
		export HXCPP_RC=llvm-windres
		# hxcpp's Windows sources use the casing from a case-insensitive
		# Windows include tree (for example, Ws2tcpip.h), while the
		# self-contained LLVM-MinGW sysroot ships lowercase header names.
		# Linux-hosted cross-builds still resolve includes case-sensitively,
		# so add non-destructive aliases only when the real header exists.
		local header_pair=""
		local header_alias=""
		local header_real=""
		local header_root="$MINGW_ROOT/include"
		for header_pair in \
			"In6addr.h:in6addr.h" \
			"Ws2tcpip.h:ws2tcpip.h" \
			"Memoryapi.h:memoryapi.h" \
			"Roapi.h:roapi.h"; do
			header_alias="${header_pair%%:*}"
			header_real="${header_pair#*:}"
			if [[ -f "$header_root/$header_real" && \
				! -e "$header_root/$header_alias" && \
				! -L "$header_root/$header_alias" ]]; then
				ln -s "$header_real" "$header_root/$header_alias" || \
					die "could not create LLVM-MinGW header alias $header_alias"
			fi
		done
		# hxcpp's static linker defaults to the host 'ar' when EXEPREFIX is not
		# set. Prefer LLVM-MinGW's target wrappers so archives never get built
		# with the host ELF archiver. These are normally supplied beside the
		# clang wrapper; fallback to the unprefixed LLVM tools in that prefix.
		for target_tool in "$triplet-ar" "$triplet-ranlib" "$triplet-strip"; do
			target_tool_path="$(command -v "$target_tool" 2>/dev/null || true)"
			if [[ -n "$target_tool_path" ]]; then
				case "$target_tool" in
					"$triplet-ar") export HXCPP_AR="$target_tool" ;;
					"$triplet-ranlib") export HXCPP_RANLIB="$target_tool" ;;
					"$triplet-strip") export HXCPP_STRIP="$target_tool" ;;
				esac
			fi
		done
		[[ -n "${HXCPP_AR:-}" ]] || { command -v llvm-ar >/dev/null 2>&1 && export HXCPP_AR="llvm-ar"; }
		[[ -n "${HXCPP_RANLIB:-}" ]] || { command -v llvm-ranlib >/dev/null 2>&1 && export HXCPP_RANLIB="llvm-ranlib"; }
		[[ -n "${HXCPP_STRIP:-}" ]] || { command -v llvm-strip >/dev/null 2>&1 && export HXCPP_STRIP="llvm-strip"; }
	fi
	echo ">> using ${compiler_family} compiler $resolved_compiler with MINGW_ROOT=$MINGW_ROOT"
}

configure_llvm_mingw_resources() {
	local toolchain="$ROOT/.haxelib/hxcpp/4,3,2/toolchain/mingw-toolchain.xml"
	[[ -f "$toolchain" ]] || die "hxcpp MinGW toolchain is missing: $toolchain"
	command -v llvm-windres >/dev/null 2>&1 || \
		die "LLVM-MinGW compiler was found, but llvm-windres is missing from PATH"
	# hxcpp 4.3.2 has an rc compiler entry for MSVC but not for its MinGW
	# compiler.  Keep the fix local and idempotent in the pinned haxelib, and
	# gate it on HXCPP_RC so native/MSVC builds never inherit this tool.
	if ! grep -q "dp-llvm-mingw-resource-compiler" "$toolchain"; then
		python3 - "$toolchain" <<'PYEOF'
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as source:
	    text = source.read()
marker = "  <!-- dp-llvm-mingw-resource-compiler -->"
if marker not in text:
    needle = "</compiler>"
    addition = """  <!-- dp-llvm-mingw-resource-compiler -->
  <rcexe name="${HXCPP_RC}" if="HXCPP_RC" />
  <rcext value=".res" if="HXCPP_RC" />
"""
    if needle not in text:
        raise SystemExit("could not locate the MinGW compiler section in hxcpp's toolchain")
    text = text.replace(needle, addition + needle, 1)
    with open(path, "w", encoding="utf-8") as destination:
        destination.write(text)

PYEOF
		echo ">> configured hxcpp LLVM-MinGW resource compiler"
	fi
	# The stock hxcpp toolchain knows the GCC sysroot layouts, where
	# libwinpthread-1.dll is commonly under sys-root/mingw/bin or lib.  The
	# self-contained LLVM-MinGW layout puts the runtime DLL beside its target
	# compiler in ${MINGW_ROOT}/bin, so teach hxcpp to stage that DLL before the
	# executable link.  Keep this separate from the resource marker so existing
	# setups receive the fix on the next run as well.
	if ! grep -q "dp-llvm-mingw-runtime-dll" "$toolchain"; then
		python3 - "$toolchain" <<'PYEOF'
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as source:
	text = source.read()
marker = "  <!-- dp-llvm-mingw-runtime-dll -->"
if marker not in text:
	needle = '<copyFile toolId="exe" name="libwinpthread-1.dll" from="${MINGW_ROOT}/lib" allowMissing="true" unless="no_shared_libs"/>'
	addition = '''<!-- dp-llvm-mingw-runtime-dll -->
<copyFile toolId="exe" name="libwinpthread-1.dll" from="${MINGW_ROOT}/bin" allowMissing="true" unless="no_shared_libs"/>
'''
	if needle not in text:
		raise SystemExit("could not locate the MinGW runtime copy rule in hxcpp's toolchain")
	text = text.replace(needle, addition + needle, 1)
	with open(path, "w", encoding="utf-8") as destination:
		destination.write(text)
PYEOF
		echo ">> configured LLVM-MinGW runtime DLL staging"
	fi
	# LLVM-MinGW uses libc++/compiler-rt rather than GCC's libstdc++ and
	# libgcc DLL names.  hxcpp's generic MinGW rules still try to copy those
	# two GCC DLLs and abort the link when they are absent.  Disable only those
	# generic copy rules when HXCPP_RC identifies this LLVM-MinGW build.
	if ! grep -q "dp-llvm-mingw-gcc-runtime-guard" "$toolchain"; then
		python3 - "$toolchain" <<'PYEOF'
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as source:
	text = source.read()
marker = "<!-- dp-llvm-mingw-gcc-runtime-guard -->"
if marker not in text:
	for name in ("libgcc_s_dw2-1.dll", "libstdc++-6.dll"):
		needle = f'<copyFile toolId="exe" name="{name}" from="${{MINGW_ROOT}}/bin" allowMissing="true" unless="no_shared_libs"/>'
		replacement = needle.replace('unless="no_shared_libs"', 'unless="no_shared_libs || HXCPP_RC"')
		if needle not in text:
			raise SystemExit(f"could not locate the MinGW GCC runtime copy rule for {name}")
		text = text.replace(needle, replacement, 1)
	needle = '<copyFile toolId="exe" name="libgcc_s_dw2-1.dll" from="${MINGW_ROOT}/bin" allowMissing="true" unless="no_shared_libs || HXCPP_RC"/>'
text = text.replace(needle, marker + "\n" + needle, 1)
with open(path, "w", encoding="utf-8") as destination:
	destination.write(text)
PYEOF
		echo ">> configured LLVM-MinGW GCC runtime guards"
	fi
	# Some hxcpp versions accept boolean expressions on sections but treat an
	# expression on copyFile itself as a literal condition.  Put the two GCC
	# copy rules behind a dedicated section so HXCPP_RC reliably suppresses
	# them for LLVM-MinGW while leaving the stock rules intact for GCC MinGW.
	if ! grep -q "dp-llvm-mingw-gcc-runtime-section" "$toolchain"; then
		python3 - "$toolchain" <<'PYEOF'
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as source:
	text = source.read()
marker = "<!-- dp-llvm-mingw-gcc-runtime-section -->"
if marker not in text:
	old = '''<!-- dp-llvm-mingw-gcc-runtime-guard -->
<copyFile toolId="exe" name="libgcc_s_dw2-1.dll" from="${MINGW_ROOT}/bin" allowMissing="true" unless="no_shared_libs || HXCPP_RC"/>
<copyFile toolId="exe" name="libstdc++-6.dll" from="${MINGW_ROOT}/bin" allowMissing="true" unless="no_shared_libs || HXCPP_RC"/>'''
	new = '''<!-- dp-llvm-mingw-gcc-runtime-section -->
<section unless="HXCPP_RC">
<copyFile toolId="exe" name="libgcc_s_dw2-1.dll" from="${MINGW_ROOT}/bin" allowMissing="true" unless="no_shared_libs"/>
<copyFile toolId="exe" name="libstdc++-6.dll" from="${MINGW_ROOT}/bin" allowMissing="true" unless="no_shared_libs"/>
</section>'''
	if old not in text:
		raise SystemExit("could not locate the LLVM-MinGW GCC runtime guard block")
	text = text.replace(old, new, 1)
	with open(path, "w", encoding="utf-8") as destination:
		destination.write(text)
PYEOF
		echo ">> configured LLVM-MinGW GCC runtime section"
	fi
}

prepare_cross_project() {
	# run.sh owns the repository-wide preparation that must precede every Lime
	# invocation: pinned tool bootstrap, lower-case chart/case mirrors,
	# Project.xml disk mounts, and the patched flixel/rapidjson sources. Its
	# setup mode deliberately stops before launch_cache/build so this Windows
	# path never performs an unrelated Linux build.
	if [[ "$debug" == 1 ]]; then
		"$ROOT/run.sh" setup debug
	else
		"$ROOT/run.sh" setup
	fi
}

ensure_windows_astc_decoder() {
	local astc_dir="$ROOT/.tools/astcenc-windows"
	local astc_source="$astc_dir/astcenc-sse2.exe"
	local version_file="$astc_dir/version"
	local expected_version="3.7"
	local archive_sha256="ecb0e1a5dcbfbaca8a38630e427638380b9d337c266660b39738260e1df5244a"
	local archive_url="https://github.com/ARM-software/astc-encoder/releases/download/3.7/astcenc-3.7-windows-x64.zip"
	local temp_dir=""
	local archive=""

	if [[ -x "$astc_source" && -f "$version_file" && "$(<"$version_file")" == "$expected_version" ]]; then
		return 0
	fi
	command -v curl >/dev/null 2>&1 || die "Windows ASTC decoder bootstrap requires curl; install curl or place astcenc-sse2.exe under $astc_dir"
	command -v python3 >/dev/null 2>&1 || die "Windows ASTC decoder bootstrap requires python3 for the checksum/archive probe"
	temp_dir="$(mktemp -d "$PROJECT_TMP/astcenc-windows.XXXXXX")"
	archive="$temp_dir/astcenc.zip"
	if ! curl -fL --retry 3 -o "$archive" "$archive_url"; then
		rm -rf -- "$temp_dir"
		die "could not download the Windows ASTC decoder; check network access or place astcenc-sse2.exe under $astc_dir"
	fi
	if ! python3 - "$archive" "$astc_source" "$archive_sha256" <<'PYEOF'
import hashlib
import os
import sys
import zipfile

archive, destination, expected = sys.argv[1:]
actual = hashlib.sha256(open(archive, 'rb').read()).hexdigest()
if actual != expected:
    raise SystemExit(f'Windows astcenc archive checksum mismatch: expected {expected}, found {actual}')
with zipfile.ZipFile(archive) as source:
    names = [name for name in source.namelist()
             if name.replace('\\', '/').rsplit('/', 1)[-1] == 'astcenc-sse2.exe']
    if not names:
        raise SystemExit('Windows astcenc archive did not contain astcenc-sse2.exe')
    payload = source.read(names[0])
os.makedirs(os.path.dirname(destination), exist_ok=True)
temporary = destination + '.tmp'
with open(temporary, 'wb') as output:
    output.write(payload)
os.chmod(temporary, 0o755)
os.replace(temporary, destination)
PYEOF
	then
		rm -rf -- "$temp_dir"
		die "could not verify or unpack the Windows ASTC decoder; remove $astc_dir and retry"
	fi
	rm -rf -- "$temp_dir"
	printf '%s\n' "$expected_version" > "$version_file"
}

sync_windows_astc_decoder() {
	local runtime_tools="$1/tools"
	local astc_source="$ROOT/.tools/astcenc-windows/astcenc-sse2.exe"
	[[ -f "$astc_source" ]] || die "Windows ASTC decoder is missing after bootstrap: $astc_source"
	require_file "$ROOT/tools/licenses/astcenc-LICENSE.txt" "Windows ASTC decoder license is missing from the repository"
	mkdir -p "$runtime_tools"
	install -m 755 "$astc_source" "$runtime_tools/astcenc.exe"
	install -m 644 "$ROOT/tools/licenses/astcenc-LICENSE.txt" "$runtime_tools/astcenc-LICENSE.txt"
}

sync_llvm_mingw_windows_output() {
	[[ "${DP_LLVM_MINGW:-0}" == 1 ]] || return 0
	local windows_obj="$1"
	local windows_bin="$2"
	local application_name="ApplicationMain.exe"
	local linked_exe=""
	local runtime_dir="${MINGW_ROOT%/}/bin"
	local runtime=""
	[[ "$debug" == 1 ]] && application_name="ApplicationMain-debug.exe"
	linked_exe="$windows_obj/$application_name"
	[[ -f "$linked_exe" ]] || return 1

	# Lime 8.3.2 unconditionally stages GCC MinGW DLL names after a successful
	# non-static link. LLVM-MinGW links against compiler-rt/libc++ instead, so
	# those names do not exist and Lime exits after it has already produced the
	# valid PE executable. Keep this recovery limited to the known LLVM-MinGW
	# output and copy only the linked executable plus runtimes that actually
	# exist in the selected LLVM-MinGW prefix.
	mkdir -p "$windows_bin"
	install -m 755 "$linked_exe" "$windows_bin/Funkin.exe"
	for runtime in libwinpthread-1.dll libc++.dll libunwind.dll; do
		if [[ -f "$runtime_dir/$runtime" ]]; then
			install -m 755 "$runtime_dir/$runtime" "$windows_bin/$runtime"
		fi
	done
	echo ">> staged LLVM-MinGW Windows output in $windows_bin"
}

ensure_wine_tools() {
	WINE_COMMAND="$(resolve_command "${WINE_BIN:-${WINE:-wine}}" "Wine")"
	TIMEOUT_COMMAND="$(resolve_command "${TIMEOUT_BIN:-timeout}" "GNU timeout")"
	"$TIMEOUT_COMMAND" --version 2>/dev/null | grep -qi "GNU coreutils" || die "Wine smoke requires GNU timeout with --foreground/--kill-after support; set TIMEOUT_BIN to a GNU timeout executable"
	[[ "$wine_timeout" =~ ^[1-9][0-9]*$ ]] || die "Wine smoke timeout must be a positive integer number of seconds (got '$wine_timeout')"
}

run_wine_smoke() {
	local executable="$1"
	local build_bin="$2"
	local smoke_log="$PROJECT_TMP/wine-smoke-$$.log"
	local wine_prefix="${WINEPREFIX:-$PROJECT_TMP/wine-prefix}"
	local startup_window=5
	local smoke_pid
	local smoke_status
	local observed_start=0
	local elapsed=0

	[[ "$wine_timeout" -lt "$startup_window" ]] && startup_window="$wine_timeout"
	if [[ "$wine_prefix" != /* ]]; then
		wine_prefix="$ROOT/$wine_prefix"
	fi
	require_file "$executable" "Wine smoke cannot find the Windows executable"
	if command -v file >/dev/null 2>&1; then
		local file_type
		file_type="$(file -b "$executable" 2>/dev/null || true)"
		[[ "$file_type" == *PE32* || "$file_type" == *MS-DOS* ]] || die "Wine smoke expected a Windows PE executable, but file reports: ${file_type:-unknown}"
	fi
	mkdir -p -- "$wine_prefix"
	echo ">> Wine smoke: launching $executable (startup window ${startup_window}s, timeout ${wine_timeout}s)"
	echo ">> Wine smoke log: $smoke_log"
	set +e
	(
		cd "$build_bin" || exit 126
		WINEPREFIX="$wine_prefix" "$TIMEOUT_COMMAND" --foreground --kill-after=5s "${wine_timeout}s" "$WINE_COMMAND" "$executable"
	) >"$smoke_log" 2>&1 &
	smoke_pid=$!
	while kill -0 "$smoke_pid" 2>/dev/null; do
		if [[ "$elapsed" -ge "$startup_window" ]]; then
			observed_start=1
			break
		fi
		sleep 1
		elapsed=$((elapsed + 1))
	done
	wait "$smoke_pid"
	smoke_status=$?
	set -e

	case "$smoke_status" in
		124)
			echo ">> Wine smoke: process stayed alive through startup and timed out safely after ${wine_timeout}s (log: $smoke_log)"
			return 0
			;;
		137|143)
			if [[ "$observed_start" == 1 ]]; then
				echo ">> Wine smoke: process stayed alive through startup and was terminated safely at the ${wine_timeout}s timeout (log: $smoke_log)"
				return 0
			fi
			echo "!! Wine smoke: process crashed or was terminated before startup completed (status $smoke_status; log: $smoke_log)" >&2
			return "$smoke_status"
			;;
		0)
			if [[ "$observed_start" == 1 ]]; then
				echo ">> Wine smoke: process started and exited cleanly before the timeout (log: $smoke_log)"
				return 0
			fi
			die "Wine smoke exited before the ${startup_window}s startup window (log: $smoke_log)"
			;;
		*)
			echo "!! Wine smoke: process crashed or exited with status $smoke_status before startup completed (log: $smoke_log)" >&2
			return "$smoke_status"
			;;
	esac
}

is_windows_shell() {
	case "${OS:-}" in
		Windows_NT) return 0 ;;
	esac
	case "${OSTYPE:-}" in
		msys*|mingw*|cygwin*) return 0 ;;
	esac
	return 1
}

host_arch() {
	case "$(uname -m)" in
		x86_64|amd64) echo "x86_64" ;;
		aarch64|arm64) echo "aarch64" ;;
		*) uname -m ;;
	esac
}

target="${1:-}"
[[ -n "$target" ]] || { usage >&2; exit 2; }
case "$target" in
	-h|--help|help) usage; exit 0 ;;
esac
shift

debug=0
skip_build=0
wine_smoke=0
wine_timeout="${WINE_SMOKE_TIMEOUT:-${WINE_TIMEOUT:-30}}"
while [[ "$#" -gt 0 ]]; do
	option="$1"
	case "${option,,}" in
		debug) debug=1; shift ;;
		--skip-build|skip-build) skip_build=1; shift ;;
		--wine-smoke) wine_smoke=1; shift ;;
		--timeout|--wine-timeout)
			[[ "$#" -ge 2 ]] || die "$option requires a timeout in seconds"
			wine_timeout="$2"
			shift 2
			;;
		--timeout=*|--wine-timeout=*) wine_timeout="${option#*=}"; shift ;;
		-h|--help) usage; exit 0 ;;
		*) die "unknown option '$option' (see ./build.sh --help)" ;;
	esac
done

target_kind="${target,,}"
if [[ "$target_kind" == "wine-smoke" ]]; then
	wine_smoke=1
	target_kind="windows"
fi

case "$target_kind" in
	linux|appimage)
		[[ "$wine_smoke" == 0 ]] || die "--wine-smoke is only valid with the windows target"
		[[ "$(uname -s)" == "Linux" ]] || die "the '$target' target requires a Linux host; use run.bat for a native Windows build or build on Linux for an AppImage"
		if [[ "$skip_build" == 1 && "$target_kind" == "linux" ]]; then
			die "--skip-build is only valid with the appimage target"
		fi
		if [[ "$target_kind" == "appimage" ]]; then
			APPIMAGETOOL="${APPIMAGETOOL:-appimagetool}"
			if [[ "$APPIMAGETOOL" == */* ]]; then
				[[ -x "$APPIMAGETOOL" ]] || die "APPIMAGETOOL is not executable: $APPIMAGETOOL (install appimagetool or set APPIMAGETOOL to its path)"
			else
				command -v "$APPIMAGETOOL" >/dev/null 2>&1 || die "appimagetool is required for the appimage target; install it or set APPIMAGETOOL=/path/to/appimagetool"
				APPIMAGETOOL="$(command -v "$APPIMAGETOOL")"
			fi
		fi

		if [[ "$skip_build" == 0 ]]; then
			if [[ "$debug" == 1 ]]; then
				"$ROOT/run.sh" build debug
			else
				"$ROOT/run.sh" build
			fi
		fi

		if [[ "$debug" == 1 ]]; then
			BUILD_ROOT="$ROOT/export/debug"
		else
			BUILD_ROOT="$ROOT/export/release"
		fi
		LINUX_BIN="$BUILD_ROOT/linux/bin"
		require_executable "$LINUX_BIN/Funkin" "Linux build did not produce an executable; run ./run.sh build first"
		[[ -d "$LINUX_BIN/assets" ]] || die "Linux build is missing its assets directory: $LINUX_BIN/assets"

		if [[ "$target_kind" == "linux" ]]; then
			echo ">> built $LINUX_BIN/Funkin"
			exit 0
		fi

		APP_VERSION="$(sed -n 's/.*<app[^>]*version="\([^"]*\)".*/\1/p' Project.xml | head -n 1)"
		APP_VERSION="${APP_VERSION:-unknown}"
		APP_NAME="DisappointingPlus-${APP_VERSION}-linux-$(host_arch).AppImage"
		APPIMAGE_DIR="$BUILD_ROOT/appimage"
		APPDIR="$APPIMAGE_DIR/AppDir"
		OUTPUT="$APPIMAGE_DIR/$APP_NAME"

		# This is an explicit build-output directory. It is kept under export/
		# so it remains ignored and can be inspected after a packaging failure.
		rm -rf -- "$APPDIR"
		mkdir -p "$APPDIR/usr/bin" \
			"$APPDIR/usr/share/applications" \
			"$APPDIR/usr/share/icons/hicolor/64x64/apps"
		cp -a "$LINUX_BIN"/. "$APPDIR/usr/bin/"
		cp "$ROOT/tools/appimage/AppRun" "$APPDIR/AppRun"
		# appimagetool discovers the desktop entry and icon from the AppDir
		# root. Keep copies in the freedesktop data tree too for extracted
		# runtimes and desktop integration tools.
		cp "$ROOT/tools/appimage/disappointing-plus.desktop" \
			"$APPDIR/disappointing-plus.desktop"
		cp "$ROOT/tools/appimage/disappointing-plus.desktop" \
			"$APPDIR/usr/share/applications/disappointing-plus.desktop"
		cp "$ROOT/art/icon64.png" \
			"$APPDIR/disappointing-plus.png"
		cp "$ROOT/art/icon64.png" \
			"$APPDIR/usr/share/icons/hicolor/64x64/apps/disappointing-plus.png"
		chmod +x "$APPDIR/AppRun"

		# A new id gives each AppImage build its own persistent writable runtime
		# directory. It avoids silently mixing mutable data with a newer payload.
		printf '%s\n' "$(date -u +%Y%m%d%H%M%S)-$$" > "$APPDIR/usr/bin/.dp-runtime-id"
		printf '%s\n' "$(date -u +%Y%m%d%H%M%S)" > "$APPDIR/usr/bin/.dp-build-time"
		rm -f -- "$OUTPUT"
		echo ">> packaging $OUTPUT"
		"$APPIMAGETOOL" "$APPDIR" "$OUTPUT"
		[[ -f "$OUTPUT" ]] || die "appimagetool returned successfully but did not create $OUTPUT"
		chmod +x "$OUTPUT"
		echo ">> built $OUTPUT"
		;;
	windows)
		if is_windows_shell; then
			[[ "$wine_smoke" == 0 ]] || die "--wine-smoke is Linux-host only; use run.bat for a native Windows launch"
			[[ "$skip_build" == 0 ]] || die "--skip-build is only valid for Linux-host Windows reuse"
			command -v cmd.exe >/dev/null 2>&1 || die "native Windows shell detected, but cmd.exe is unavailable; run run.bat from Windows Command Prompt or Git Bash"
			WIN_SCRIPT="$ROOT/run.bat"
			if command -v cygpath >/dev/null 2>&1; then
				WIN_SCRIPT="$(cygpath -w "$WIN_SCRIPT")"
			fi
			# /c consumes the remainder as one command line. Keep the batch path
			# quoted inside that command so a checkout such as
			# "External Storage\\DisappointingPlus" remains addressable.
			if [[ "$debug" == 1 ]]; then
				cmd.exe /d /c "call \"$WIN_SCRIPT\" build debug"
			else
				cmd.exe /d /c "call \"$WIN_SCRIPT\" build"
			fi
			exit 0
		fi

		[[ "$(uname -s)" == "Linux" ]] || die "Linux-host Windows cross-builds require Linux; use run.bat on native Windows or a native toolchain on macOS"
		if [[ "$wine_smoke" == 1 ]]; then
			ensure_wine_tools
		fi
		if [[ "$skip_build" == 0 ]]; then
			prepare_cross_project
			ensure_portable_toolchain
			ensure_mingw_toolchain
			if [[ "${DP_LLVM_MINGW:-0}" == 1 ]]; then
				configure_llvm_mingw_resources
			fi
			source "$ROOT/tools/runtime_lock.sh"
			lock_runtime "$ROOT/.tools/runtime-$debug.lock"
			ensure_windows_astc_decoder
			# `-D...` supplies Haxe/hxcpp defines, but Lime also needs the
			# target flag that selects its C++ cross-compilation path.  Without
			# `-mingw`, HXProject sees a foreign desktop target with no cpp flag
			# and falls back to generating a Neko project instead of invoking
			# hxcpp's MinGW toolchain.
			lime_args=(haxelib run lime build windows -mingw -Dwindows -DHXCPP_MINGW -DHXCPP_M64)
			if [[ "${DP_LLVM_MINGW:-0}" == 1 ]]; then
				lime_args+=(-DHXCPP_RC=llvm-windres)
			fi
			if [[ "$debug" == 1 ]]; then
				lime_args+=(-debug)
				build_label="debug"
			else
				build_label="release"
			fi
			echo ">> cross-building Windows $build_label with hxcpp MinGW"
			if ! "${lime_args[@]}"; then
				# Lime's WindowsPlatform.hx has a GCC-only post-link copy step.
				# With LLVM-MinGW the link itself can succeed before that step
				# reports a missing libstdc++/libgcc DLL. Preserve all other
				# failures, but keep the already-linked PE for the scoped case.
				windows_obj="$ROOT/export/$build_label/windows/obj"
				if [[ "${DP_LLVM_MINGW:-0}" == 1 && ( \
					-f "$windows_obj/ApplicationMain.exe" || \
					-f "$windows_obj/ApplicationMain-debug.exe" ) ]]; then
					sync_llvm_mingw_windows_output "$windows_obj" "$ROOT/export/$build_label/windows/bin" || \
						exit 1
					echo ">> ignored Lime's LLVM-MinGW-only GCC DLL staging error after a successful link"
				else
					exit 1
				fi
			fi
		fi

		if [[ "$debug" == 1 ]]; then
			BUILD_ROOT="$ROOT/export/debug"
		else
			BUILD_ROOT="$ROOT/export/release"
		fi
		WINDOWS_BIN="$BUILD_ROOT/windows/bin"
		WINDOWS_EXE="$WINDOWS_BIN/Funkin.exe"
		if [[ "$skip_build" == 0 && "${DP_LLVM_MINGW:-0}" == 1 ]]; then
			sync_llvm_mingw_windows_output "$BUILD_ROOT/windows/obj" "$WINDOWS_BIN" || \
				die "LLVM-MinGW link output is missing: $BUILD_ROOT/windows/obj"
		fi
		require_file "$WINDOWS_EXE" "Windows build did not produce an executable; install MinGW and run ./build.sh windows first"
		if [[ "$skip_build" == 0 ]]; then
			sync_windows_astc_decoder "$WINDOWS_BIN"
		fi
		if [[ "$wine_smoke" == 1 ]]; then
			run_wine_smoke "$WINDOWS_EXE" "$WINDOWS_BIN"
		else
			echo ">> built $WINDOWS_EXE"
		fi
		;;
	*)
		usage >&2
		exit 2
		;;
esac
