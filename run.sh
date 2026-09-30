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

# hscript 2.5.0: a field read/write on a null object threw EInvalidAccess,
# which through the native Dynamic-call plumbing can abort the remainder of
# an imported script callback with NO visible error (whole stage backgrounds
# silently vanished). Degrade null-target field access to a diagnosed no-op
# (write) / null return (read) so donor scripts keep running. Idempotent.
HS=.haxelib/hscript/2,5,0/hscript/Interp.hx
if [ -f "$HS" ] && ! grep -q "hscript-null-access" "$HS"; then
    python3 - "$HS" <<'PYEOF2'
import sys
p = sys.argv[1]
s = open(p).read()
old_set = "\tfunction set( o : Dynamic, f : String, v : Dynamic ) : Dynamic {\n\t\tif( o == null ) error(EInvalidAccess(f));\n\t\tReflect.setProperty(o,f,v);\n\t\treturn v;\n\t}"
new_set_lines = [
"\tfunction set( o : Dynamic, f : String, v : Dynamic ) : Dynamic {",
"\t\t// DisappointingPlus local patch: a donor script writing a field on a",
"\t\t// null object (for example a V-Slice PlayState member this engine does",
"\t\t// not carry) used to throw EInvalidAccess which, through the native",
"\t\t// Dynamic-call plumbing, aborted the remainder of the closure with no",
"\t\t// visible error - entire stage backgrounds silently disappeared. Degrade",
"\t\t// the write to a diagnosed no-op so the rest of the callback keeps",
"\t\t// running; genuinely null objects are still reported once per field.",
"\t\tif( o == null ) {",
"\t\t\tnullAccessDiagnose(\"write\", f);",
"\t\t\treturn v;",
"\t\t}",
"\t\tReflect.setProperty(o,f,v);",
"\t\treturn v;",
"\t}",
"",
"\tfunction nullAccessDiagnose( kind : String, f : String ) : Void {",
"\t\t#if sys",
"\t\tvar key = kind + \":\" + f;",
"\t\tvar seen = _dpNullAccessSeen;",
"\t\tif( seen == null ) {",
"\t\t\tseen = new haxe.ds.StringMap();",
"\t\t\t_dpNullAccessSeen = seen;",
"\t\t}",
"\t\tif( !seen.exists(key) ) {",
"\t\t\tseen.set(key, true);",
"\t\t\tSys.println('[hscript-null-access] ' + kind + ' to \"' + f + '\" on a null object was ignored so the script can continue');",
"\t\t}",
"\t\t#end",
"\t}",
]
new_set = "\n".join(new_set_lines)
old_get = "\tfunction get( o : Dynamic, f : String ) : Dynamic {\n\t\tif ( o == null ) error(EInvalidAccess(f));"
new_get_lines = [
"\tfunction get( o : Dynamic, f : String ) : Dynamic {",
"\t\t// DisappointingPlus local patch: reading a field of a null object used",
"\t\t// to throw EInvalidAccess which, on native Dynamic-call paths, can end",
"\t\t// the whole callback with no visible error. Imported scripts commonly",
"\t\t// probe optional graph members this way; return null (diagnosed once)",
"\t\t// so their own null checks keep working.",
"\t\tif ( o == null ) {",
"\t\t\tnullAccessDiagnose(\"read\", f);",
"\t\t\treturn null;",
"\t\t}",
]
new_get = "\n".join(new_get_lines)
old_field = "\tpublic var variables : Map<String,Dynamic>;\n\tvar locals : Map<String,{ r : Dynamic }>;\n\tvar binops : Map<String, Expr -> Expr -> Dynamic >;\n#else"
new_field = "\tpublic var variables : Map<String,Dynamic>;\n\tvar locals : Map<String,{ r : Dynamic }>;\n\tvar binops : Map<String, Expr -> Expr -> Dynamic >;\n\t// DisappointingPlus local patch: dedupe set for null-access diagnostics.\n\tvar _dpNullAccessSeen : Map<String,Bool>;\n#else"
ok = 0
if old_set in s:
    s = s.replace(old_set, new_set); ok += 1
if old_get in s:
    s = s.replace(old_get, new_get); ok += 1
if old_field in s:
    s = s.replace(old_field, new_field); ok += 1
if ok == 3:
    open(p, 'w').write(s)
    print('>> patched hscript null-access silent-abort fallback')
else:
    print('!! hscript patch matched only %d/3 patterns - Interp.hx changed upstream?' % ok)
PYEOF2
fi

# Keep null field reads/writes and null-target calls attributable to their
# active HScript source and callback. This upgrades earlier null-access
# fallbacks without changing their null read/write/call behavior. Idempotent.
if [ -f "$HS" ] && ! grep -q "hscript-null-access-context" "$HS"; then
    python3 - "$HS" <<'PYNULLACCESSCONTEXT'
import sys
p = sys.argv[1]
s = open(p).read()
start = s.find("\tfunction nullAccessDiagnose( kind : String, f : String ) : Void {")
end = s.find("\n\t/**", start)
if start < 0 or end < 0:
    raise SystemExit('hscript null-access context patch could not find nullAccessDiagnose')
new = '''\tfunction nullAccessDiagnose( kind : String, f : String ) : Void {
		// DisappointingPlus local patch (hscript-null-access-context): include
		// the active imported source/callback so a null receiver can be traced
		// to its source API use without changing the safe null result.
		#if sys
		var source = variables.get("__compatDiagnosticSource");
		var callback = variables.get("__compatDiagnosticCallback");
		var context = source == null ? "" : Std.string(source);
		if( callback != null ) context += "#" + Std.string(callback);
		var key = kind + ":" + f + ":" + context;
		var seen = _dpNullAccessSeen;
		if( seen == null ) {
			seen = new haxe.ds.StringMap();
			_dpNullAccessSeen = seen;
		}
		if( !seen.exists(key) ) {
			seen.set(key, true);
			Sys.println('[hscript-null-access] ' + kind + ' to "' + f + '" on a null object was ignored so the script can continue' + (context == '' ? '' : ' (' + context + ')'));
		}
		#end
	}'''
open(p, 'w').write(s[:start] + new + s[end:])
print('patched hscript null-access diagnostic context')
PYNULLACCESSCONTEXT
fi

# hscript 2.5.0: arithmetic/ordering Dynamic binops with a null operand
# dereference the null vtable inside hxcpp operator plumbing and SIGSEGV
# before any exception can surface (DDTO's extra-opponent chain crashed the
# whole process this way). Guard the op closures so null operands degrade
# like the web engines instead of taking the game down.
if [ -f "$HS" ] && ! grep -q "hscript-null-operand" "$HS"; then
    python3 - "$HS" <<'PYEOF3'
import sys
p = sys.argv[1]
s = open(p).read()
helper = """\t/**
\t * On hxcpp, arithmetic/ordering Dynamic operations with a null operand
\t * dereference the null value's vtable inside generated operator plumbing
\t * and SIGSEGV before any exception can be raised. Ported scripts that
\t * chain optional lookups (e.g. missing donor metadata) must degrade like
\t * the web engines do instead of taking the process down.
\t */
\tfunction nullOperandDiagnose( op : String ) : Void {
\t\t#if sys
\t\tvar key = "operand:" + op;
\t\tvar seen = _dpNullAccessSeen;
\t\tif( seen == null ) {
\t\t\tseen = new haxe.ds.StringMap();
\t\t\t_dpNullAccessSeen = seen;
\t\t}
\t\tif( !seen.exists(key) ) {
\t\t\tseen.set(key, true);
\t\t\tSys.println('[hscript-null-operand] "' + op + '" used a null operand and returned null so the script can continue');
\t\t}
\t\t#end
\t}

\tfunction fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {"""
anchor_fcall = "\tfunction fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {"
if anchor_fcall in s and "nullOperandDiagnose" not in s:
    s = s.replace(anchor_fcall, helper, 1)

old_ops = """\t\tbinops.set("+",function(e1,e2) return me.expr(e1) + me.expr(e2));
\t\tbinops.set("-",function(e1,e2) return me.expr(e1) - me.expr(e2));
\t\tbinops.set("*",function(e1,e2) return me.expr(e1) * me.expr(e2));
\t\tbinops.set("/",function(e1,e2) return me.expr(e1) / me.expr(e2));
\t\tbinops.set("%",function(e1,e2) return me.expr(e1) % me.expr(e2));
\t\tbinops.set("&",function(e1,e2) return me.expr(e1) & me.expr(e2));
\t\tbinops.set("|",function(e1,e2) return me.expr(e1) | me.expr(e2));
\t\tbinops.set("^",function(e1,e2) return me.expr(e1) ^ me.expr(e2));
\t\tbinops.set("<<",function(e1,e2) return me.expr(e1) << me.expr(e2));
\t\tbinops.set(">>",function(e1,e2) return me.expr(e1) >> me.expr(e2));
\t\tbinops.set(">>>",function(e1,e2) return me.expr(e1) >>> me.expr(e2));"""
def guarded(symbol, body):
    return ('\t\tbinops.set("%s",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
            'if( a == null || b == null ) { me.nullOperandDiagnose("%s"); return null; } return %s; });'
            % (symbol, symbol, body))
new_ops_lines = [
    guarded("+", "a + b"),
    guarded("-", "a - b"),
    guarded("*", "a * b"),
    guarded("/", "a / b"),
    guarded("%", "a % b"),
    guarded("&", "a & b"),
    guarded("|", "a | b"),
    guarded("^", "a ^ b"),
    guarded("<<", "a << b"),
    guarded(">>", "a >> b"),
    guarded(">>>", "a >>> b"),
]
if old_ops in s:
    s = s.replace(old_ops, "\n".join(new_ops_lines), 1)

old_cmp = """\t\tbinops.set(">=",function(e1,e2) return me.expr(e1) >= me.expr(e2));
\t\tbinops.set("<=",function(e1,e2) return me.expr(e1) <= me.expr(e2));
\t\tbinops.set(">",function(e1,e2) return me.expr(e1) > me.expr(e2));
\t\tbinops.set("<",function(e1,e2) return me.expr(e1) < me.expr(e2));"""
def guarded_cmp(symbol, body):
    return ('\t\tbinops.set("%s",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
            'if( a == null || b == null ) { me.nullOperandDiagnose("%s"); return false; } return %s; });'
            % (symbol, symbol, body))
new_cmp_lines = [
    guarded_cmp(">=", "a >= b"),
    guarded_cmp("<=", "a <= b"),
    guarded_cmp(">", "a > b"),
    guarded_cmp("<", "a < b"),
]
if old_cmp in s:
    s = s.replace(old_cmp, "\n".join(new_cmp_lines), 1)

old_range = '\t\tbinops.set("...",function(e1,e2) return new #if (haxe_211 || haxe3) IntIterator #else IntIter #end(me.expr(e1),me.expr(e2)));'
new_range = ('\t\tbinops.set("...",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
             'if( a == null || b == null ) { me.nullOperandDiagnose("..."); return new #if (haxe_211 || haxe3) IntIterator #else IntIter #end(0,0); } '
             'return new #if (haxe_211 || haxe3) IntIterator #else IntIter #end(a,b); });')
if old_range in s:
    s = s.replace(old_range, new_range, 1)

import re
for symbol, body in [("+=", "v1 + v2"), ("-=", "v1 - v2"), ("*=", "v1 * v2"), ("/=", "v1 / v2"),
                     ("%=", "v1 % v2"), ("&=", "v1 & v2"), ("|=", "v1 | v2"), ("^=", "v1 ^ v2"),
                     ("<<=", "v1 << v2"), (">>=", "v1 >> v2"), (">>>=", "v1 >>> v2")]:
    pat = re.compile(r'assignOp\("' + re.escape(symbol) + r'",function\(v1(:[^)]*)?,v2(:[^)]*)?\) return (v1 [^;]+);\)')
    m = pat.search(s)
    if m:
        s = s[:m.start()] + ('assignOp("%s",function(v1:Dynamic,v2:Dynamic) { if( v1 == null || v2 == null ) { me.nullOperandDiagnose("%s"); return null; } return %s; })'
                             % (symbol, symbol, m.group(3))) + s[m.end():]

if "nullOperandDiagnose" not in s:
    print("hscript binop guard patch did not apply", file=sys.stderr)
    sys.exit(1)
open(p, "w").write(s)
print("patched hscript binops with null-operand guards")
PYEOF3
fi

# Keep null-operand diagnostics attributable to their interpreter/callback.
# This changes diagnostic context and deduplication only, not operator behavior.
if [ -f "$HS" ] && ! grep -q '__compatDiagnosticSource' "$HS"; then
    python3 - "$HS" <<'PYNULLCONTEXT'
import sys
p = sys.argv[1]
s = open(p).read()
old_key = '\t\tvar key = "operand:" + op;'
new_key = '''\t\tvar source = variables.get("__compatDiagnosticSource");
\t\tvar callback = variables.get("__compatDiagnosticCallback");
\t\tvar context = source == null ? "" : Std.string(source);
\t\tif( callback != null ) context += "#" + Std.string(callback);
\t\tvar key = "operand:" + op + ":" + context;'''
# Include the closing quote around the operator in the original message.
old_message = "'\" used a null operand and returned null so the script can continue'"
new_message = old_message + " + (context == '' ? '' : ' (' + context + ')')"
if old_key not in s or old_message not in s:
    raise SystemExit('hscript diagnostic context patch did not apply')
s = s.replace(old_key, new_key, 1).replace(old_message, new_message, 1)
open(p, 'w').write(s)
print('patched hscript null-operand diagnostic context')
PYNULLCONTEXT
fi

# hscript 2.5.0: on COMPILED targets (hxcpp), the Dynamic -/*/%% binop closures
# evaluated as INT arithmetic, silently truncating Float operands (1477 * 0.67
# -> 0, 0.2 * health -> 0). Interpreted runs keep float semantics, so fixture
# tests passed while the shipped binary broke every donor script that scaled a
# size by a fraction (Expurgation signs stayed 1.5x, the gremlin drained to 0
# instead of 20%% and chased the wrong bar end). Promote to double math when
# either operand is a Float; Int-only math keeps the native path. Idempotent.
if [ -f "$HS" ] && ! grep -q "dpFloatAwareArith" "$HS"; then
    python3 - "$HS" <<'PYFLOAT'
import sys
p = sys.argv[1]
s = open(p).read()
changed = False
for symbol in ("-", "*", "%"):
    old = ('\t\tbinops.set("%s",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
           'if( a == null || b == null ) { me.nullOperandDiagnose("%s"); return null; } return a %s b; });'
           % (symbol, symbol, symbol))
    new = ('\t\tbinops.set("%s",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
           'if( a == null || b == null ) { me.nullOperandDiagnose("%s"); return null; } return me.dpFloatAwareArith("%s", a, b); });'
           % (symbol, symbol, symbol))
    if old in s:
        s = s.replace(old, new, 1)
        changed = True
for symbol in ("-=", "*=", "%="):
    old = ('\t\tassignOp("%s",function(v1:Dynamic,v2:Dynamic) { if( v1 == null || v2 == null ) { me.nullOperandDiagnose("%s"); return null; } return v1 %s v2; });'
           % (symbol, symbol, symbol[:-1]))
    new = ('\t\tassignOp("%s",function(v1:Dynamic,v2:Dynamic) { if( v1 == null || v2 == null ) { me.nullOperandDiagnose("%s"); return null; } return me.dpFloatAwareArith("%s", v1, v2); });'
           % (symbol, symbol, symbol[:-1]))
    if old in s:
        s = s.replace(old, new, 1)
        changed = True
helper = (
    '\tfunction dpFloatAwareArith(op:String, a:Dynamic, b:Dynamic):Dynamic {\n'
    '\t\tif (Std.isOfType(a, Float) || Std.isOfType(b, Float)) {\n'
    '\t\t\tvar fa:Float = a;\n'
    '\t\t\tvar fb:Float = b;\n'
    '\t\t\treturn switch (op) {\n'
    '\t\t\t\tcase "-": fa - fb;\n'
    '\t\t\t\tcase "*": fa * fb;\n'
    '\t\t\t\tcase "%": fa % fb;\n'
    '\t\t\t\tdefault: a;\n'
    '\t\t\t};\n'
    '\t\t}\n'
    '\t\treturn switch (op) {\n'
    '\t\t\tcase "-": a - b;\n'
    '\t\t\tcase "*": a * b;\n'
    '\t\t\tcase "%": a % b;\n'
    '\t\t\tdefault: a;\n'
    '\t\t};\n'
    '\t}\n'
)
if 'function dpFloatAwareArith' not in s:
    anchor_fn = '\tfunction nullOperandDiagnose( op : String ) : Void {'
    if anchor_fn in s:
        s = s.replace(anchor_fn, helper + anchor_fn, 1)
        changed = True
if not changed and 'dpFloatAwareArith' not in s:
    print('hscript float-arith patch did not apply', file=sys.stderr)
    sys.exit(1)
open(p, 'w').write(s)
print('patched hscript arith with float-aware promotion')
PYFLOAT
fi

# hscript 2.5.0: for-in over a null value called .iterator() on a null Dynamic,
# which on hxcpp dereferences the null object inside generated call plumbing
# and SIGSEGVs before any Haxe exception can surface (imported V-Slice
# substates iterate optional members such as FlxG.touches.list). Degrade the
# loop to empty with a one-time diagnostic, in the same style as the
# null-access and null-operand guards. Idempotent.
if [ -f "$HS" ] && ! grep -q "hscript-null-iterator" "$HS"; then
    python3 - "$HS" <<'PYEOF4'
import sys
p = sys.argv[1]
s = open(p).read()
old = """\tfunction makeIterator( v : Dynamic ) : Iterator<Dynamic> {
\t\t#if ((flash && !flash9) || (php && !php7 && haxe_ver < '4.0.0'))
\t\tif ( v.iterator != null ) v = v.iterator();
\t\t#else
\t\ttry v = v.iterator() catch( e : Dynamic ) {};
\t\t#end
\t\tif( v.hasNext == null || v.next == null ) error(EInvalidIterator(v));
\t\treturn v;
\t}"""
new = """\tfunction makeIterator( v : Dynamic ) : Iterator<Dynamic> {
\t\t// DisappointingPlus local patch (hscript-null-iterator): for-in over a
\t\t// null value used to call .iterator() on a null Dynamic, which on hxcpp
\t\t// dereferences the null object inside generated call plumbing and
\t\t// SIGSEGVs before any Haxe exception can surface. Imported scripts
\t\t// iterate optional members (for example FlxG.touches.list on a host
\t\t// which does not carry them); degrade the loop to empty with a one-time
\t\t// diagnostic, consistent with the null-access / null-operand guards.
\t\tif( v == null ) {
\t\t\tnullIteratorDiagnose();
\t\t\tvar emptyIterator : Iterator<Dynamic> = { hasNext : function() : Bool return false, next : function() : Dynamic return null };
\t\t\treturn emptyIterator;
\t\t}
\t\t#if ((flash && !flash9) || (php && !php7 && haxe_ver < '4.0.0'))
\t\tif ( v.iterator != null ) v = v.iterator();
\t\t#else
\t\ttry v = v.iterator() catch( e : Dynamic ) {};
\t\t#end
\t\tif( v.hasNext == null || v.next == null ) error(EInvalidIterator(v));
\t\treturn v;
\t}

\tfunction nullIteratorDiagnose() : Void {
\t\t#if sys
\t\tvar key = "iterator:null";
\t\tvar seen = _dpNullAccessSeen;
\t\tif( seen == null ) {
\t\t\tseen = new haxe.ds.StringMap();
\t\t\t_dpNullAccessSeen = seen;
\t\t}
\t\tif( !seen.exists(key) ) {
\t\t\tseen.set(key, true);
\t\t\tSys.println('[hscript-null-iterator] for-in used a null value and was treated as an empty loop so the script can continue');
\t\t}
\t\t#end
\t}"""
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched hscript makeIterator with null for-in guard')
else:
    print('!! hscript makeIterator patch pattern not found - Interp.hx changed upstream?')
PYEOF4
fi

# Keep null-iterator diagnostics attributable to their source and callback,
# matching null-operand reporting. This also upgrades the existing local
# hscript-null-iterator patch when the library was already patched before this
# context was added. Idempotent.
if [ -f "$HS" ] && ! grep -q "hscript-null-iterator-context" "$HS"; then
    python3 - "$HS" <<'PYNULLITERCONTEXT'
import sys
p = sys.argv[1]
s = open(p).read()
start = s.find("\tfunction nullIteratorDiagnose() : Void {")
end = s.find("\n\tfunction forLoop(", start)
if start < 0 or end < 0:
    raise SystemExit('hscript null-iterator context patch could not find nullIteratorDiagnose')
new = '''\tfunction nullIteratorDiagnose() : Void {
\t\t// DisappointingPlus local patch (hscript-null-iterator-context): keep
\t\t// null for-in diagnostics attributable to the active source callback.
\t\t#if sys
\t\tvar source = variables.get("__compatDiagnosticSource");
\t\tvar callback = variables.get("__compatDiagnosticCallback");
\t\tvar context = source == null ? "" : Std.string(source);
\t\tif( callback != null ) context += "#" + Std.string(callback);
\t\tvar key = "iterator:null:" + context;
\t\tvar seen = _dpNullAccessSeen;
\t\tif( seen == null ) {
\t\t\tseen = new haxe.ds.StringMap();
\t\t\t_dpNullAccessSeen = seen;
\t\t}
\t\tif( !seen.exists(key) ) {
\t\t\tseen.set(key, true);
\t\t\tSys.println('[hscript-null-iterator] for-in used a null value and was treated as an empty loop so the script can continue' + (context == '' ? '' : ' (' + context + ')'));
\t\t}
\t\t#end
\t}'''
open(p, 'w').write(s[:start] + new + s[end:])
print('patched hscript null-iterator diagnostic context')
PYNULLITERCONTEXT
fi

# Haxe 4.3 inlines IntIterator.hasNext/next, so hscript's dynamic reflection
# sees neither method on a `0...end` for-range. Wrap its typed methods before
# the generic iterator check. This fixes source HScript class loops and other
# imported scripts without changing their authored expressions. Idempotent.
if [ -f "$HS" ] && ! grep -q "hscript-int-iterator" "$HS"; then
    python3 - "$HS" <<'PYINTITER'
import sys
p = sys.argv[1]
s = open(p).read()
old = '\t\tif( v.hasNext == null || v.next == null ) error(EInvalidIterator(v));'
new = '''\t\t// DisappointingPlus local patch (hscript-int-iterator): Haxe 4.3
\t\t// inlines these methods, which are not visible to dynamic reflection.
\t\tif( Std.isOfType(v, IntIterator) ) {
\t\t\tvar range:IntIterator = cast v;
\t\t\treturn { hasNext:function():Bool return range.hasNext(),
\t\t\t\tnext:function():Dynamic return range.next() };
\t\t}
''' + old
if old not in s:
    print('!! hscript IntIterator patch pattern not found - Interp.hx changed upstream?')
else:
    open(p, 'w').write(s.replace(old, new, 1))
    print('>> patched hscript IntIterator reflection bridge')
PYINTITER
fi

# hscript 2.5.0: a method call on a null object (or on a field which does not
# exist) passes a null function to Reflect.callMethod, which on hxcpp
# dereferences the null function and SIGSEGVs before any exception can
# surface - the same crash class as makeIterator(null). Imported scripts
# probe optional donor APIs this way. Degrade to a diagnosed null return.
# Idempotent.
if [ -f "$HS" ] && ! grep -q "hscript-null-fcall" "$HS"; then
    python3 - "$HS" <<'PYEOF5'
import sys
p = sys.argv[1]
s = open(p).read()
old = """\tfunction fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {
\t\treturn call(o, get(o, f), args);
\t}"""
new = """\tfunction fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {
\t\t// DisappointingPlus local patch (hscript-null-fcall): calling a method
\t\t// on a null object, or on a member which does not exist, handed a null
\t\t// function to Reflect.callMethod - which on hxcpp dereferences the null
\t\t// function and SIGSEGVs before any Haxe exception can surface (donor
\t\t// scripts probe optional APIs such as missing module methods this way).
\t\t// Degrade to a diagnosed null return so the callback keeps running,
\t\t// consistent with the null-access / null-iterator guards.
\t\tvar field : Dynamic = get(o, f);
\t\tif( field == null ) {
\t\t\tnullAccessDiagnose("call", f);
\t\t\treturn null;
\t\t}
\t\treturn call(o, field, args);
\t}"""
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched hscript fcall with null-target guard')
else:
    print('!! hscript fcall patch pattern not found - Interp.hx changed upstream?')
PYEOF5
fi

# hscript 2.5.0: a method call through a field on a null object throws
# EInvalidAccess inside the ECall handler before fcall is ever reached - the
# same abort-the-callback class the null-access field shims fixed (and after
# them the null never surfaces as a catchable script error). Degrade to a
# diagnosed null return like the field shims. Idempotent.
if [ -f "$HS" ] && ! grep -q "hscript-null-ecall" "$HS"; then
    python3 - "$HS" <<'PYEOF6'
import sys
p = sys.argv[1]
s = open(p).read()
old = """\t\t\tcase EField(e,f):
\t\t\t\tvar obj = expr(e);
\t\t\t\tif( obj == null ) error(EInvalidAccess(f));
\t\t\t\treturn fcall(obj,f,args);"""
new = """\t\t\tcase EField(e,f):
\t\t\t\tvar obj = expr(e);
\t\t\t\t// DisappointingPlus local patch (hscript-null-ecall): a method
\t\t\t\t// call on a null object used to throw EInvalidAccess here, which
\t\t\t\t// through the native Dynamic-call plumbing aborts the remainder
\t\t\t\t// of the callback (after the null-access shims the null never
\t\t\t\t// surfaces as a catchable script error). Imported scripts probe
\t\t\t\t// optional donor APIs this way; degrade to a diagnosed null
\t\t\t\t// return, consistent with the null-access / null-iterator guards.
\t\t\t\tif( obj == null ) {
\t\t\t\t\tnullAccessDiagnose("call", f);
\t\t\t\t\treturn null;
\t\t\t\t}
\t\t\t\treturn fcall(obj,f,args);"""
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched hscript ECall with null-object guard')
else:
    print('!! hscript ECall patch pattern not found - Interp.hx changed upstream?')
PYEOF6
fi

# hscript 2.5.0: indexing a null value (`optionalMetadata[0]` after a donor
# lookup the engine does not expose) dereferences the null inside hxcpp array
# access and SIGSEGVs mid-expression, the same crash class the null-access and
# null-operand guards fix. Degrade to a diagnosed null return. Idempotent.
if [ -f "$HS" ] && ! grep -q "hscript-null-earray" "$HS"; then
    python3 - "$HS" <<'PYEOF7'
import sys
p = sys.argv[1]
s = open(p).read()
old = """\t\tcase EArray(e, index):
\t\t\tvar arr:Dynamic = expr(e);
\t\t\tvar index:Dynamic = expr(index);
\t\t\tif (isMap(arr)) {
\t\t\t\treturn getMapValue(arr, index);
\t\t\t}
\t\t\telse {
\t\t\t\treturn arr[index];
\t\t\t}"""
new = """\t\tcase EArray(e, index):
\t\t\tvar arr:Dynamic = expr(e);
\t\t\tvar index:Dynamic = expr(index);
\t\t\t// DisappointingPlus local patch (hscript-null-earray): indexing a
\t\t\t// null value dereferences the null inside hxcpp array access and
\t\t\t// SIGSEGVs before any exception can surface (imported scripts index
\t\t\t// optional donor metadata, such as missing splash offsets, this
\t\t\t// way). Degrade to a diagnosed null return, consistent with the
\t\t\t// null-access / null-operand / null-iterator guards.
\t\t\tif( arr == null ) {
\t\t\t\tnullAccessDiagnose("index", Std.string(index));
\t\t\t\treturn null;
\t\t\t}
\t\t\tif (isMap(arr)) {
\t\t\t\treturn getMapValue(arr, index);
\t\t\t}
\t\t\telse {
\t\t\t\treturn arr[index];
\t\t\t}"""
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched hscript EArray with null-object guard')
else:
    print('!! hscript EArray patch pattern not found - Interp.hx changed upstream?')
PYEOF7
fi

# hscript 2.5.0: a compound assign (`splash.x += null`) whose operation was
# skipped for a null operand must keep the previous value; writing the shimmed
# null back into a native non-nullable Float/Int field SIGSEGVs inside hxcpp's
# reflection write. Track the null-operand diagnosis and skip the write-back.
# Idempotent.
if [ -f "$HS" ] && ! grep -q "hscript-null-assignop" "$HS"; then
    python3 - "$HS" <<'PYEOF8'
import sys
p = sys.argv[1]
s = open(p).read()

anchor = "\tfunction nullOperandDiagnose( op : String ) : Void {\n\t\t#if sys"
flagged = """\tfunction nullOperandDiagnose( op : String ) : Void {
\t\tnullOperandSeen = true;
\t\t#if sys"""
# Declare the flag next to the existing diagnostics dedupe set (both branches).
flag_decl = "\tvar nullOperandSeen : Bool;"
if "nullOperandSeen" not in s:
    s = s.replace("\tvar _dpNullAccessSeen : Map<String,Bool>;",
                  "\tvar _dpNullAccessSeen : Map<String,Bool>;\n" + flag_decl)
    s = s.replace(anchor, flagged, 1)

old_field = """\t\tcase EField(e,f):
\t\t\tvar obj = expr(e);
\t\t\tv = fop(get(obj,f),expr(e2));
\t\t\tv = set(obj,f,v);"""
new_field = """\t\tcase EField(e,f):
\t\t\tvar obj = expr(e);
\t\t\tnullOperandSeen = false;
\t\t\tv = fop(get(obj,f),expr(e2));
\t\t\t// DisappointingPlus local patch (hscript-null-assignop): a compound
\t\t\t// assign whose operation was skipped for a null operand keeps the
\t\t\t// previous value instead of writing null into a native non-nullable
\t\t\t// field, which on hxcpp SIGSEGVs inside the reflection write.
\t\t\tif( v != null || !nullOperandSeen )
\t\t\t\tv = set(obj,f,v);
\t\t\tnullOperandSeen = false;"""
if old_field in s:
    s = s.replace(old_field, new_field, 1)

old_array = """\t\tcase EArray(e, index):
\t\t\tvar arr:Dynamic = expr(e);
\t\t\tvar index:Dynamic = expr(index);
\t\t\tif (isMap(arr)) {
\t\t\t\tv = fop(getMapValue(arr, index), expr(e2));
\t\t\t\tsetMapValue(arr, index, v);
\t\t\t}
\t\t\telse {
\t\t\t\tv = fop(arr[index],expr(e2));
\t\t\t\tarr[index] = v;
\t\t\t}"""
new_array = """\t\tcase EArray(e, index):
\t\t\tvar arr:Dynamic = expr(e);
\t\t\tvar index:Dynamic = expr(index);
\t\t\tnullOperandSeen = false;
\t\t\tif (isMap(arr)) {
\t\t\t\tv = fop(getMapValue(arr, index), expr(e2));
\t\t\t\tif( v != null || !nullOperandSeen )
\t\t\t\t\tsetMapValue(arr, index, v);
\t\t\t}
\t\t\telse {
\t\t\t\tv = fop(arr[index],expr(e2));
\t\t\t\tif( v != null || !nullOperandSeen )
\t\t\t\t\tarr[index] = v;
\t\t\t}
\t\t\tnullOperandSeen = false;"""
if old_array in s:
    s = s.replace(old_array, new_array, 1)

if "hscript-null-assignop" not in s:
    print("hscript compound-assign guard patch did not apply", file=sys.stderr)
    sys.exit(1)
open(p, "w").write(s)
print("patched hscript compound assigns with null-operand write-back guard")
PYEOF8
fi

# hscript 2.5.0 on hxcpp: the typed `catch( err : Stop )` handlers wrongly
# match ANY enum value - including hscript.Error values thrown by real script
# errors - so a script-level error inside a loop became a phantom
# break/continue and a try/catch body never ran (the completion closure of
# imported confirm popups silently no-op'd). Catch dynamically and match Stop
# values by runtime type, rethrowing genuine script errors to the script's own
# try/catch. Idempotent.
if [ -f "$HS" ] && ! grep -q "hscript-stop-catch" "$HS"; then
    python3 - "$HS" <<'PYEOF9'
import sys
p = sys.argv[1]
s = open(p).read()
ok = 0

# runtime Stop matcher, added next to the Stop enum declaration
old_enum = """private enum Stop {"""
new_enum = """// DisappointingPlus local patch (hscript-stop-catch): Stop values must be
// matched by runtime type on hxcpp, whose typed enum catch wrongly grabs
// hscript.Error values thrown by real script errors.
function isHscriptStop( v : Dynamic ) : Bool {
	// hxcpp's enum type resolution collapses distinct enums (both the typed
	// catch and the type checks above report hscript.Error values as Stop),
	// but each value keeps its constructor name, which never collides.
	if( v == null )
		return false;
	// DisappointingPlus local patch (hscript-stop-safe-enum): hxcpp can
	// segfault inside Type.enumConstructor for an ordinary Dynamic object;
	// its try/catch cannot intercept that native fault. Only inspect enums.
	switch( Type.typeof(v) ) {
	case TEnum(_):
		try {
			var name : String = Type.enumConstructor(v);
			return name == 'SBreak' || name == 'SContinue' || name == 'SReturn';
		} catch( e : Dynamic ) {
			return false;
		}
	default:
		return false;
	}
}

private enum Stop {"""
if old_enum in s:
    s = s.replace(old_enum, new_enum); ok += 1

# exprReturn: a non-Stop must propagate to the caller, not fall through.
old_exprreturn = """		} catch( e : Stop ) {
			switch( e ) {
			case SBreak: throw "Invalid break";
			case SContinue: throw "Invalid continue";
			case SReturn:
				var v = returnValue;
				returnValue = null;
				return v;
			}
		}"""
new_exprreturn = """		} catch( e : Dynamic ) {
			// DisappointingPlus local patch (hscript-stop-catch): rethrow
			// genuine script errors instead of silently ignoring them.
			if( !isHscriptStop(e) )
				throw e;
			switch( e ) {
			case SBreak: throw "Invalid break";
			case SContinue: throw "Invalid continue";
			case SReturn:
				var v = returnValue;
				returnValue = null;
				return v;
			}
		}"""
if old_exprreturn in s:
    s = s.replace(old_exprreturn, new_exprreturn); ok += 1

# ETry: one dynamic catch; real Stop signals rethrow, script errors reach the
# catch block (previously the Stop catch swallowed script errors entirely).
old_etry = """			} catch( err : Stop ) {
				inTry = oldTry;
				throw err;
			} catch( err : Dynamic ) {
				// restore vars
				restore(old);
				inTry = oldTry;
				// declare 'v'
				declared.push({ n : n, old : locals.get(n) });
				locals.set(n,{ r : err });
				var v : Dynamic = expr(ecatch);
				restore(old);
				return v;
			}"""
new_etry = """			} catch( err : Dynamic ) {
				inTry = oldTry;
				// DisappointingPlus local patch (hscript-stop-catch): real
				// Stop signals (break/continue/return) keep unwinding;
				// hscript.Error values from script errors reach the catch
				// block, which the hxcpp typed enum catch wrongly swallowed.
				if( isHscriptStop(err) )
					throw err;
				// restore vars
				restore(old);
				// declare 'v'
				declared.push({ n : n, old : locals.get(n) });
				locals.set(n,{ r : err });
				var v : Dynamic = expr(ecatch);
				restore(old);
				return v;
			}"""
if old_etry in s:
    s = s.replace(old_etry, new_etry); ok += 1

# loops: a non-Stop must propagate to the script's own try/catch instead of
# degrading into a phantom break/continue.
old_loop = """			} catch( err : Stop ) {
				switch(err) {
				case SContinue:
				case SBreak: break;
				case SReturn: throw err;
				}
			}"""
new_loop = """			} catch( err : Dynamic ) {
				// DisappointingPlus local patch (hscript-stop-catch): genuine
				// script errors propagate to the script's own try/catch
				// instead of becoming a phantom break/continue on hxcpp.
				if( !isHscriptStop(err) )
					throw err;
				var stop : Stop = err;
				switch(stop) {
				case SContinue:
				case SBreak: break;
				case SReturn: throw err;
				}
			}"""
count = s.count(old_loop)
if count >= 2:
    s = s.replace(old_loop, new_loop)
    ok += count

old_forloop = """			} catch( err : Stop ) {
				switch( err ) {
				case SContinue:
				case SBreak: break;
				case SReturn: throw err;
				}
			}"""
new_forloop = """			} catch( err : Dynamic ) {
				// DisappointingPlus local patch (hscript-stop-catch): genuine
				// script errors propagate to the script's own try/catch
				// instead of becoming a phantom break/continue on hxcpp.
				if( !isHscriptStop(err) )
					throw err;
				var stop : Stop = err;
				switch(stop) {
				case SContinue:
				case SBreak: break;
				case SReturn: throw err;
				}
			}"""
if old_forloop in s:
    s = s.replace(old_forloop, new_forloop); ok += 1

if ok == 6:
    open(p, 'w').write(s)
    print('>> patched hscript Stop catches with runtime type checks (6 sites)')
else:
    open(p, 'w').write(s)
    print('!! hscript Stop-catch patch matched only %d/6 patterns - Interp.hx changed upstream?' % ok)
PYEOF9
fi

# Upgrade hscript copies that already carry the older Stop matcher.  The game
# toolchain is pinned, but `.haxelib` is local and can survive a run.sh update.
if [ -f "$HS" ] && grep -q "hscript-stop-catch" "$HS" && ! grep -q "hscript-stop-safe-enum" "$HS"; then
    python3 - "$HS" <<'PYEOF9B'
import sys
p = sys.argv[1]
s = open(p).read()
start = s.find("function isHscriptStop( v : Dynamic ) : Bool {")
end = s.find("\nprivate enum Stop {", start)
if start < 0 or end < 0:
    print('hscript safe-enum matcher patch could not find the old Stop helper', file=sys.stderr)
    sys.exit(1)
replacement = """function isHscriptStop( v : Dynamic ) : Bool {
	// hxcpp's enum type resolution collapses distinct enums (both the typed
	// catch and the type checks above report hscript.Error values as Stop),
	// but each value keeps its constructor name, which never collides.
	if( v == null )
		return false;
	// DisappointingPlus local patch (hscript-stop-safe-enum): hxcpp can
	// segfault inside Type.enumConstructor for an ordinary Dynamic object;
	// its try/catch cannot intercept that native fault. Only inspect enums.
	switch( Type.typeof(v) ) {
	case TEnum(_):
		try {
			var name : String = Type.enumConstructor(v);
			return name == 'SBreak' || name == 'SContinue' || name == 'SReturn';
		} catch( e : Dynamic ) {
			return false;
		}
	default:
		return false;
	}
}"""
s = s[:start] + replacement + s[end:]
open(p, 'w').write(s)
print('>> patched hscript Stop matcher to type-check Dynamics before enum inspection')
PYEOF9B
fi

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
