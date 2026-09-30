#!/usr/bin/env bash
# personal build & run script - DisappointingPlus
#
#   ./run.sh          run release; build only when inputs changed
#   ./run.sh debug    run debug; build only when inputs changed
#   ./run.sh build    build if needed, don't launch (also: ./run.sh build debug)
#   ./run.sh rebuild  force a build, don't launch (also: ./run.sh rebuild debug)
#   ./run.sh nobuild  skip building, just run
#   ./run.sh server   start a haxe compilation server (speeds up later builds)
#   ./run.sh setup    bootstrap tools/haxelibs and source preprocessing only
#
# iteration tips:
#   - `./run.sh server` once, then builds skip re-typechecking (~15-25s saved
#     per build). if a build acts stale after Project.xml/define changes,
#     `pkill -f 'haxe --wait'` and rerun server.
#   - release is the default; the release object files are reused across
#     builds so only changed files recompile + the final link runs.
#
# first run: downloads portable Haxe 4.3.6 + Neko into .tools/ (no sudo),
# installs the haxelibs once into .haxelib/, patches Project.xml so the
# song library loads from disk instead of being embedded (it's ~7GB - the
# old game shipped the same way), and fixes the case-sensitivity things
# linux needs (lowercase chart folders + case symlinks for base songs).
set -euo pipefail
cd "$(dirname "$0")"

# Keep compiler, archive, and launcher scratch files on the project drive.
# The host /tmp may be a small tmpfs, while this checkout also handles very
# large imported media libraries.
PROJECT_TMP="$PWD/tmp"
mkdir -p "$PROJECT_TMP"
export TMPDIR="$PROJECT_TMP"

MODE="${1:-release}"
DEBUG=0
[[ "$MODE" == "debug" || "${2:-}" == "debug" ]] && DEBUG=1
if [[ "$MODE" == "debug" ]]; then MODE="release"; fi   # ./run.sh debug = release-mode run of a debug build
SETUP_ONLY=0
[[ "$MODE" == "setup" ]] && SETUP_ONLY=1
BUILD_DIR="export/release"
EXTRA=""
[[ "$DEBUG" == "1" ]] && { BUILD_DIR="export/debug"; EXTRA="-debug"; }
BIN="$BUILD_DIR/linux/bin/Funkin"
launch_game() {
    if [ ! -x "$BIN" ]; then
        echo "!! no binary at $BIN - run ./run.sh build first" >&2
        exit 1
    fi
    echo ">> running"
    cd "$(dirname "$BIN")"
    exec "./$(basename "$BIN")"
}

# ---------------------------------------------------------------- toolchain
TOOLS="$PWD/.tools"
export HAXEPATH="$TOOLS/haxe"
export NEKOPATH="$TOOLS/neko"
export LD_LIBRARY_PATH="$NEKOPATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="$HAXEPATH:$NEKOPATH:$PATH"
export HAXELIB_PATH="$PWD/.haxelib"

mkdir -p "$TOOLS"

# V-Slice desktop exports use raw ASTC textures. Keep the official Arm
# reference decoder pinned and checksum-verified beside the portable build
# toolchain, then copy the most broadly compatible x86-64 build beside each
# game binary. The importer discovers runtime-local tools/astcenc without
# modifying the donor mod.
ASTCENC_VERSION="3.7"
ASTCENC_ARCHIVE_SHA256="f69c2acbb3b07386cc95001c253cddfa567e71b9618682856f0ff600955cc2ba"
ASTCENC_DIR="$TOOLS/astcenc"
ASTCENC_BIN="$ASTCENC_DIR/astcenc"
ASTCENC_VERSION_FILE="$ASTCENC_DIR/version"
ensure_astcenc() {
    if [ -x "$ASTCENC_BIN" ] && [ -f "$ASTCENC_VERSION_FILE" ] && \
            [ "$(<"$ASTCENC_VERSION_FILE")" = "$ASTCENC_VERSION" ]; then
        return
    fi
    echo ">> downloading portable astcenc $ASTCENC_VERSION (one time)..."
    local temp_dir archive
    temp_dir="$(mktemp -d)"
    archive="$temp_dir/astcenc.zip"
    if ! curl -fL --retry 3 -o "$archive" \
            "https://github.com/ARM-software/astc-encoder/releases/download/$ASTCENC_VERSION/astcenc-$ASTCENC_VERSION-linux-x64.zip"; then
        rm -rf -- "$temp_dir"
        return 1
    fi
    mkdir -p "$ASTCENC_DIR"
    if ! python3 - "$archive" "$ASTCENC_BIN" "$ASTCENC_ARCHIVE_SHA256" <<'PYEOF'
import hashlib
import os
import sys
import zipfile

archive, destination, expected = sys.argv[1:]
actual = hashlib.sha256(open(archive, 'rb').read()).hexdigest()
if actual != expected:
    raise SystemExit(f'astcenc archive checksum mismatch: expected {expected}, found {actual}')
with zipfile.ZipFile(archive) as source:
    payload = source.read('astcenc/astcenc-sse2')
temporary = destination + '.tmp'
with open(temporary, 'wb') as output:
    output.write(payload)
os.chmod(temporary, 0o755)
os.replace(temporary, destination)
PYEOF
    then
        rm -rf -- "$temp_dir"
        return 1
    fi
    printf '%s\n' "$ASTCENC_VERSION" > "$ASTCENC_VERSION_FILE"
    rm -rf -- "$temp_dir"
}
sync_astcenc() {
    local bin_dir runtime_decoder
    # A cached executable can still be launched when the optional importer
    # decoder has not been bootstrapped yet (offline machines and copied build
    # folders are common).  Decoder setup belongs to the build/setup path, not
    # the unchanged-launch fast path.
    [ -x "$ASTCENC_BIN" ] || return 0
    bin_dir="$(dirname "$BIN")"
    [ -d "$bin_dir" ] || return 0
    runtime_decoder="$bin_dir/tools/astcenc"
    mkdir -p "$(dirname "$runtime_decoder")"
    if [ ! -x "$runtime_decoder" ] || ! cmp -s "$ASTCENC_BIN" "$runtime_decoder"; then
        install -m 755 "$ASTCENC_BIN" "$runtime_decoder"
    fi
    install -m 644 "$PWD/tools/licenses/astcenc-LICENSE.txt" \
        "$bin_dir/tools/astcenc-LICENSE.txt"
}
# Lime copies native libraries in place; overwriting a mapped lime.ndll can
# SIGBUS an open game. The lock stays held through the final exec of Funkin.
if [[ "$MODE" != "server" && "$SETUP_ONLY" == "0" ]]; then
    source "$PWD/tools/runtime_lock.sh"
    lock_runtime "$TOOLS/runtime-$DEBUG.lock"
fi
# An explicit nobuild never installs dependencies or rewrites project files.
if [[ "$MODE" == "nobuild" ]]; then
    launch_game
fi
# Keep an already-installed decoder beside a cached binary, but do not perform
# network/toolchain setup until the cache has actually established that a
# build is required.
if [[ "$MODE" != "server" && "$SETUP_ONLY" == "0" ]]; then sync_astcenc; fi
if [[ "$SETUP_ONLY" == "0" && "$MODE" != "server" && "$MODE" != "rebuild" ]] && \
        python3 tools/launch_cache.py check "$BUILD_DIR"; then
    echo ">> build is up to date"
    if [[ "$MODE" == "build" ]]; then exit 0; fi
    launch_game
fi
if [[ "$MODE" != "server" && "$SETUP_ONLY" == "0" ]]; then
    ensure_astcenc
    if [[ "$SETUP_ONLY" == "0" ]]; then sync_astcenc; fi
fi
if [ ! -x "$HAXEPATH/haxe" ] || ! haxe --version 2>/dev/null | grep -q '^4\.3\.'; then
    echo ">> downloading portable Haxe 4.3.6 (one time)..."
    HAXE_ARCHIVE="$PROJECT_TMP/haxe-4.3.6-linux64.tar.gz"
    curl -fL --retry 3 -o "$HAXE_ARCHIVE" \
        https://github.com/HaxeFoundation/haxe/releases/download/4.3.6/haxe-4.3.6-linux64.tar.gz
    rm -rf "$HAXEPATH"
    mkdir -p "$HAXEPATH" && tar -xzf "$HAXE_ARCHIVE" -C "$HAXEPATH" --strip-components=1
fi
if [ ! -x "$NEKOPATH/neko" ]; then
    echo ">> downloading portable Neko (one time)..."
    NEKO_ARCHIVE="$PROJECT_TMP/neko-2.3.0-linux64.tar.gz"
    curl -fL --retry 3 -o "$NEKO_ARCHIVE" \
        https://github.com/HaxeFoundation/neko/releases/download/v2-3-0/neko-2.3.0-linux64.tar.gz
    mkdir -p "$NEKOPATH" && tar -xzf "$NEKO_ARCHIVE" -C "$NEKOPATH" --strip-components=1
fi
[ -f ~/.haxelib ] || echo "$HAXELIB_PATH" > ~/.haxelib
mkdir -p "$HAXELIB_PATH"

# ---------------------------------------------------------------- haxelibs
# one `haxelib list` total; a pinned lib is only touched when the pinned
# version isn't already the SELECTED one ([brackets] in haxelib list)
HL_CACHE="$(haxelib list 2>/dev/null || true)"
hl_has()  { grep -q "^$1:" <<<"$HL_CACHE"; }
hl_sel()  { grep "^$1: .*\[$2\]" <<<"$HL_CACHE" | grep -q .; }
inst() {
    if [ -n "${2:-}" ]; then
        hl_sel "$1" "$2" && return 0
        haxelib install "$1" "$2" --always >/dev/null
        haxelib set "$1" "$2" >/dev/null 2>&1 || true
        HL_CACHE="$(haxelib list 2>/dev/null || true)"
    else
        hl_has "$1" && return 0
        haxelib install "$1" --always >/dev/null
        HL_CACHE="$(haxelib list 2>/dev/null || true)"
    fi
}
gitinst() { hl_has "$1" && return 0
    echo ">> haxelib git $1"
    haxelib git "$1" "$2" --always
    HL_CACHE="$(haxelib list 2>/dev/null || true)"; }

inst hxcpp 4.3.2
inst lime 8.3.2
inst openfl 9.5.2
inst flixel 6.1.2
inst funkin-modchart 1.2.5
inst flixel-addons 4.0.2
inst flixel-ui 2.6.5
inst flixel-animate 1.5.0
inst hscript 2.5.0
inst hscript-iris 1.1.3
inst hxvlc 2.3.1
inst tjson
gitinst hscript-ex https://github.com/ianharrigan/hscript-ex
gitinst discord_rpc https://github.com/Aidan63/linc_discord-rpc

# hxcpp 4.3.2 must confirm that a large allocation still belongs to its live
# list before decrementing accounting or returning it to the recycle list.
# The exact-source guard lives in tools/ and is safe to apply on every setup.
python3 tools/patch_hxcpp_large_free.py

# The archived Codename Flx3D wrappers use the matching Away3D fork API.
# Verify the exact upstream commit before any Lime/Haxe build resolves it.
python3 tools/install_codename_3d.py

# OpenFL 9.5.2's Context3D bitmap snapshot allocates a full-frame byte array
# for every readback. Reuse one staging buffer per context and discard it on
# resize/dispose; the GPU readback and BitmapData copy remain unchanged.
python3 tools/patch_openfl_context3d_readback.py

# OpenFL prepends a GLSL precision block before authored shader source. Move
# any source #version directive ahead of that prefix so newer core syntax can
# compile on desktop GL drivers.
python3 tools/patch_openfl_shader_version.py

# Keep imported Codename class modules isolated by owner. This tracked patch
# extends only the selected hscript-ex implementation in .haxelib; the source
# patch itself lives in tools/ and the owner registry in source/hscript/.
python3 tools/patch_hscript_ex_owner_scope.py

# Lime treats a missing directory named by an <assets path="..."> entry as a
# project error.  Keep the declared mount points present even when the user has
# deliberately cleared every source asset before importing a new mod library.
# These are empty scaffolding directories only; no removed content is restored.
mkdir -p assets/images assets/videos assets/data assets/shaders assets/music \
    assets/songs assets/sounds assets/module assets/discord assets/fonts assets/scripts

# ------------------------------------------------- linux case-sensitivity fix
# the engine looks charts up lowercased (Song.loadFromJson), but the ported
# folders keep their original case; base-game song folders are lowercase while
# their chart song fields aren't ("Fresh" vs assets/songs/fresh)
python3 - << 'PYEOF'
import json, os, re
root = os.getcwd()
data = os.path.join(root, 'assets', 'data')
stamp = os.path.join(root, '.tools', 'casefix.stamp')
if not os.path.isdir(data):
    # A source checkout may intentionally start with an empty assets tree so
    # its content can be populated by the in-game importer.  There is nothing
    # to case-normalize yet, and getmtime/listdir would otherwise abort the
    # launcher before Haxe gets a chance to build.
    print('case fix: skipped (assets/data is not present)')
    raise SystemExit(0)
data_mtime = os.path.getmtime(data)
def read_stamp():
    try:
        return float(open(stamp).read().strip())
    except Exception:
        return -1.0
renamed = linked = 0
for e in sorted(os.listdir(data)):
    p = os.path.join(data, e)
    if not os.path.isdir(p) or e == e.lower():
        continue
    low = os.path.join(data, e.lower())
    if os.path.exists(low):
        print(f'!! case collision, leaving {e} alone')
        continue
    os.rename(p, low); renamed += 1
    for f in os.listdir(low):
        if f.endswith('.json') and f != f.lower() and not os.path.exists(os.path.join(low, f.lower())):
            os.rename(os.path.join(low, f), os.path.join(low, f.lower()))
# the mirror below parses every chart to extract song fields (~1-2s); only
# redo it when assets/data changed (folders added/removed/re-ported)
if renamed or read_stamp() != data_mtime:
    songs = os.path.join(root, 'assets', 'songs')
    fields = set()
    for e in sorted(os.listdir(data)):
        d = os.path.join(data, e)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.endswith('.json') or f in ('noteInfo.json', 'events.json', 'event.json'):
                continue
            try:
                ch = json.JSONDecoder().raw_decode(
                    re.sub(r'//[^\n]*', '', open(os.path.join(d, f), encoding='utf-8', errors='replace').read())
                )[0].get('song')
                if isinstance(ch, dict) and isinstance(ch.get('song'), str):
                    fields.add(ch['song'].strip())
            except Exception:
                pass
    # mirror assets/songs/<lowercase folder> into <SongField>-cased folders
    # (real dirs + hardlinks) so CoolUtil.getSongFile's case-sensitive checks
    # resolve. symlinks don't survive lime's asset sync - hardlinks do
    for sf in sorted(fields):
        if not sf or '/' in sf or sf == sf.lower():
            continue
        src = os.path.join(songs, sf.lower())
        dst = os.path.join(songs, sf)
        if not os.path.isdir(src):
            continue
        if os.path.islink(dst):
            os.remove(dst)
        os.makedirs(dst, exist_ok=True)
        for f in os.listdir(src):
            t = os.path.join(dst, f)
            if not os.path.exists(t):
                os.link(os.path.join(src, f), t); linked += 1
    os.makedirs(os.path.dirname(stamp), exist_ok=True)
    open(stamp, 'w').write(str(data_mtime))
print(f'case fix: {renamed} folders renamed, {linked} song files hardlinked')
PYEOF

# ------------------------------------------------- assets on disk, not embedded
python3 - << 'PYEOF'
import os
p = 'Project.xml'
s = open(p, encoding='utf-8').read()
orig = s
for d in ('images', 'data', 'music', 'songs'):
    old = f'<assets path="assets/{d}" />'
    new = f'<assets path="assets/{d}" embed="false" />'
    if old in s:
        s = s.replace(old, new)
if s != orig:
    open(p, 'w', encoding='utf-8').write(s)
    print('Project.xml: big asset folders set to embed="false"')
PYEOF

# discord_rpc's bundled rapidjson is old enough that gcc >= 15 rejects it
# (-Wtemplate-body); upstream fixed this by deleting the assignment operator
RJ=.haxelib/discord_rpc/git/lib/rapidjson/include/rapidjson/document.h
if [ -f "$RJ" ] && grep -q "s = rhs.s; length = rhs.length;" "$RJ"; then
    sed -i 's/GenericStringRef& operator=(const GenericStringRef& rhs) { s = rhs.s; length = rhs.length; }/GenericStringRef\& operator=(const GenericStringRef\& rhs) = delete;/' "$RJ"
    echo ">> patched rapidjson const-assignment in discord_rpc"
fi

# flixel 6.1.2: a sprite with NO frames whose fallback logo fails to resolve
# leaves _frame null and draw() segfaults at `_frame.type` (faker crash).
# Give checkEmptyFrame a 1x1 generated-frame last resort. Idempotent.
FS=.haxelib/flixel/6,1,2/flixel/FlxSprite.hx
if [ -f "$FS" ] && ! grep -q "dpui-fallback-frame" "$FS"; then
    python3 - "$FS" <<'PYEOF'
import sys, re
p = sys.argv[1]
s = open(p).read()
old = '''		if (_frame == null)
			loadGraphic("flixel/images/logo/default.png");
		else if (graphic != null && graphic.isDestroyed)'''
new = '''		if (_frame == null)
		{
			loadGraphic("flixel/images/logo/default.png");
			// local patch (DisappointingPlus): generated 1x1 last resort so
			// draw() can never deref a null _frame (SIGSEGV otherwise)
			if (_frame == null)
				makeGraphic(1, 1, 0, true, "dpui-fallback-frame");
		}
		else if (graphic != null && graphic.isDestroyed)'''
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched flixel checkEmptyFrame null-frame fallback')
else:
    print('!! flixel patch pattern not found - FlxSprite.hx updated upstream?')
PYEOF
fi

# Keep set_frame from dereferencing a null frame: its empty-collection
# fallback can still index to null, and copyTo on null is a native SIGSEGV
# mid-song (a V-Slice atlas swap on a swapped-in character crashed exactly
# there). Same empty-frame class as the checkEmptyFrame patch above. Idempotent.
if [ -f "$FS" ] && ! grep -q "dpui-null-frame-guard" "$FS"; then
    python3 - "$FS" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p).read()
old = "\t\t_frame = frame.copyTo(_frame);"
new = """\t\t// local patch (DisappointingPlus): the empty-collection fallback above
\t\t// can still leave frame null; copyTo on null is a native SIGSEGV
\t\tif (frame == null)
\t\t\treturn null;
\t\t_frame = frame.copyTo(_frame); // dpui-null-frame-guard"""
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched flixel set_frame null-frame guard')
else:
    print('!! flixel set_frame patch pattern not found - FlxSprite.hx updated upstream?')
PYEOF
fi

# funkin-modchart 1.2.5 reads FlxUVRect.right/top using the pre-6.1.1
# coordinate order and its rotated hold path advances UVs with an 8-float
# stride despite emitting 12 floats per subdivision. Its camera lookup also
# mistakes Flixel's global draw default for an explicit sprite assignment.
# Route both methods through tracked helpers under the shared runtime lock.
FMU=.haxelib/funkin-modchart/1,2,5/modchart/backend/util/ModchartUtil.hx
if [ -f "$FMU" ]; then
    python3 tools/patch_funkin_modchart_uv.py "$FMU"
fi

# Apply the same ordered, idempotent HScript compatibility patches on Linux
# and Windows. The shared tool fails explicitly if pinned source patterns drift.
python3 tools/patch_hscript_compat.py

# hxcpp 4.3.2: LLVM-MinGW keeps Windows DWORD as an unsigned long, while
# Dynamic has no unsigned-long constructor.  Make the Windows process exit
# code select the existing 32-bit unsigned constructor on Linux cross-builds.
HP=.haxelib/hxcpp/4,3,2/src/hx/libs/std/Process.cpp
if [ -f "$HP" ] && ! grep -q "dp-win-dword-return" "$HP"; then
    python3 - "$HP" <<'PYEOF'
import sys

p = sys.argv[1]
s = open(p, encoding='utf-8').read()
old = '''      else
         return rval;
   }
   #else
   int options=0;'''
new = '''      else
      {
         // local patch (DisappointingPlus, dp-win-dword-return):
         // LLVM-MinGW's DWORD is unsigned long; select Dynamic's
         // unsigned-int constructor explicitly.
         return (unsigned int)rval;
      }
   }
   #else
   int options=0;'''
if old not in s:
    print('!! hxcpp Process.cpp Windows DWORD patch pattern not found')
else:
    open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))
    print('>> patched hxcpp Windows DWORD Dynamic conversion')
PYEOF
fi

# ---------------------------------------------------------------- build + run
if [[ "$MODE" == "server" ]]; then
    if pgrep -f "haxe --wait 6000" >/dev/null 2>&1; then
        echo ">> compilation server already running"
    else
        nohup haxe --wait 6000 >/dev/null 2>&1 &
        echo ">> compilation server started (port 6000)"
    fi
    exit 0
fi
if [[ "$SETUP_ONLY" == "1" ]]; then
    echo ">> project setup complete (no Linux build or launch)"
    exit 0
fi
# reuse the compilation server when it's up - skips re-typechecking
CONNECT=""
if pgrep -f "haxe --wait 6000" >/dev/null 2>&1; then
    CONNECT="--connect 6000"
fi

if [[ "$MODE" != "nobuild" ]]; then
    echo ">> building (linux $([[ "$DEBUG" == "1" ]] && echo debug) $MODE)..."
    # In-game imports are written into the runtime asset tree because the
    # executable runs from export/.../bin. Lime refreshes that tree during a
    # build and removes files which are not present in the source checkout.
    # Snapshot the live tree with hardlinks, let Lime update its existing
    # output tree, then merge back only runtime-only files. Moving the tree
    # away made Lime recopy the entire media library on every rebuild.
    RUNTIME_ASSETS="$BUILD_DIR/linux/bin/assets"
    ASSETS_BAK="$BUILD_DIR/linux/bin/.assets-preserve-$$"
    if [ -e "$ASSETS_BAK" ]; then
        echo "!! temporary runtime asset path already exists: $ASSETS_BAK" >&2
        exit 1
    fi
    RUNTIME_REGISTRIES="
        assets/images/custom_chars/custom_chars.jsonc
        assets/images/custom_chars/custom_chars.json
        assets/images/custom_chars/icon_only_chars.json
        assets/images/custom_stages/custom_stages.json
        assets/images/custom_cutscenes/cutscenes.json
        assets/images/custom_difficulties/difficulties.json
        assets/images/custom_ui/ui_packs/ui.json
        assets/data/freeplaySongJson.jsonc
        assets/data/storySonglist.json
    "

    REGISTRIES_BAK=""
    if [ -d "$RUNTIME_ASSETS" ]; then
        REGISTRIES_BAK="$(mktemp -d)"
        for rel in $RUNTIME_REGISTRIES; do
            # $RUNTIME_ASSETS IS the assets dir: strip its prefix for the probe.
            rel_in_assets="${rel#assets/}"
            if [ -f "$RUNTIME_ASSETS/$rel_in_assets" ]; then
                mkdir -p "$REGISTRIES_BAK/$(dirname "$rel")"
                cp "$RUNTIME_ASSETS/$rel_in_assets" "$REGISTRIES_BAK/$rel"
            fi
        done
    fi
    # Save live preferences before Lime sync. The old move-first flow made
    # this probe miss the file and replaced settings with the default seed.
    LIVE_OPTS="$RUNTIME_ASSETS/data/options.json"
    OPTS_BAK=""
    if [ -f "$LIVE_OPTS" ]; then
        OPTS_BAK="$(mktemp)"
        cp "$LIVE_OPTS" "$OPTS_BAK"
    fi
    if [ -d "$RUNTIME_ASSETS" ]; then
        cp -al "$RUNTIME_ASSETS" "$ASSETS_BAK"
    else
        ASSETS_BAK=""
    fi
    # Lime's asset sync copies the repo options.json seed over the file the
    # game actually reads/writes (its cwd is the export bin dir).
    # Same hazard for the importer-written registries: they are repo-tracked
    # seeds the game extends at runtime, so lime's sync would silently drop
    # every imported character/stage/ui registration on each rebuild. The
    # runtime copy (seed + accumulated imports) wins, like options.json.
    restore_registries() {
        if [ -n "$REGISTRIES_BAK" ] && [ -d "$REGISTRIES_BAK" ] && [ -d "$RUNTIME_ASSETS" ]; then
            for rel in $RUNTIME_REGISTRIES; do
                rel_in_assets="${rel#assets/}"
                if [ -f "$REGISTRIES_BAK/$rel" ]; then
                    mkdir -p "$(dirname "$RUNTIME_ASSETS/$rel_in_assets")"
                    cp -f "$REGISTRIES_BAK/$rel" "$RUNTIME_ASSETS/$rel_in_assets"
                fi
            done
        fi
        if [ -n "$REGISTRIES_BAK" ] && [ -d "$REGISTRIES_BAK" ]; then
            rm -rf -- "$REGISTRIES_BAK"
        fi
        REGISTRIES_BAK=""
    }
    restore_options() {
        if [ -n "$OPTS_BAK" ]; then
            mkdir -p "$(dirname "$LIVE_OPTS")"
            cp "$OPTS_BAK" "$LIVE_OPTS"
            rm -f "$OPTS_BAK"
            OPTS_BAK=""
        fi
    }
    restore_runtime_assets() {
        if [ -z "$ASSETS_BAK" ] || [ ! -d "$ASSETS_BAK" ]; then
            return
        fi
        if [ ! -d "$RUNTIME_ASSETS" ]; then
            mv "$ASSETS_BAK" "$RUNTIME_ASSETS"
        else
            # Both paths are under the explicit export build directory and on
            # the same filesystem. Missing runtime files become hardlinks;
            # duplicates produced by Lime remain the authoritative copies.
            cp -aln "$ASSETS_BAK"/. "$RUNTIME_ASSETS"/
            rm -rf -- "$ASSETS_BAK"
        fi
        ASSETS_BAK=""
    }
    finish_build() {
        restore_runtime_assets
        restore_registries
        restore_options
    }
    trap finish_build EXIT
    BUILD_INPUTS="$(python3 tools/launch_cache.py capture "$BUILD_DIR")"
    if [ -n "$CONNECT" ]; then
        # The persistent server can retain stale type state after Project.xml
        # or haxelib changes. A failed server compile gets one clean local
        # retry before we report a real build failure.
        if ! haxelib run lime build linux $EXTRA $CONNECT; then
            echo ">> compilation server build failed; retrying without server" >&2
            haxelib run lime build linux $EXTRA
        fi
    else
        haxelib run lime build linux $EXTRA
    fi
    finish_build
    trap - EXIT
    trap - EXIT
    python3 tools/launch_cache.py record "$BUILD_DIR" "$BUILD_INPUTS"
    sync_astcenc
fi
if [[ "$MODE" == "build" || "$MODE" == "rebuild" ]]; then
    echo ">> built $BIN"
    exit 0
fi
launch_game
