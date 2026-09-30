"""The HXC state factory must resolve each root/kind/name lookup once.

Translated imported modules legitimately call hxcStateInit/hxcSubStateInit from
per-frame callbacks (CatFightFreeplayFix's update arms its confirm popup every
frame).  HxcStateFactory.find() therefore memoizes the whole-tree walk per
(root, kind, name) - both hits and misses - or every update frame re-reads and
re-analyzes the entire imported tree and menu frames take seconds.

This suite extracts the real cache-bearing members of source/HxcStateFactory.hx
(everything that touches no flixel type) and runs them under the portable
interpreter against a throwaway manifest root, with the real HxcCompat
analyzer classifying the fixture scripts.
"""

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"

STATE_HXC = """class CacheProbeState extends MusicBeatState {
	public function new() {
		super();
	}
}
"""

SUBSTATE_HXC = """class CacheProbePopup extends MusicBeatSubState {
	public function new() {
		super();
	}
}
"""


def extract_factory_module() -> str:
    """Assemble a compilable HxcStateFactory from the real source members.

    Only members free of flixel references are kept: the lookup cache, find(),
    its path helpers and fail().  The real HxcCompat, HxcScriptDiscovery and
    CompatScriptManifest modules come from source/ and do the actual work.
    """
    source = (ROOT / "source/HxcStateFactory.hx").read_text()
    typedefs = source[
        source.index("typedef HxcStateFactoryEntry") : source.index("/**\n\tResolve the narrow state factory vocabulary")
    ]
    cache_block = source[
        source.index("\tstatic var lookupCache") : source.index("\tstatic function safeManifestRoot")
    ]
    helper_start = source.index("\tstatic function safeManifestRoot")
    helper_end = source.index("\n\t#end", source.index("\tstatic function relativeTo"))
    helpers = source[helper_start:helper_end]
    fail_fn = source[source.index("\tstatic function fail") : source.rindex("\n}")]
    return "\n".join(
        [
            "import haxe.io.Path;",
            "import sys.FileSystem;",
            "import sys.io.File;",
            "import HxcMenuSpec.HxcMenuSpecData;",
            "using StringTools;",
            "",
            typedefs,
            "class HxcStateFactory {",
            "\tpublic static var lastDiagnostic(default, null):String = '';",
            cache_block,
            helpers,
            fail_fn,
            "}",
        ]
    )


def run_fixture(main: str, cwd: Path) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(prefix="hxc-factory-cache-") as folder:
        temp = Path(folder)
        (temp / "Main.hx").write_text(main)
        (temp / "HxcStateFactory.hx").write_text(extract_factory_module())
        state_dir = temp / "assets/imported_mods/cacheprobe/scripts/states"
        substate_dir = temp / "assets/imported_mods/cacheprobe/scripts/substates"
        other_dir = temp / "assets/imported_mods/otherprobe/scripts/states"
        state_dir.mkdir(parents=True)
        substate_dir.mkdir(parents=True)
        other_dir.mkdir(parents=True)
        (state_dir / "CacheProbeState.hxc").write_text(STATE_HXC)
        (substate_dir / "CacheProbePopup.hxc").write_text(SUBSTATE_HXC)
        (other_dir / "CacheProbeState.hxc").write_text(STATE_HXC)
        return subprocess.run(
            [
                str(HAXE),
                "-cp", str(ROOT / "source"),
                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                "-cp", str(temp),
                "-main", "Main",
                "--interp",
            ],
            cwd=temp,
            capture_output=True,
            text=True,
            timeout=300,
        )


MAIN = r'''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var root = "assets/imported_mods/cacheprobe";

    // First resolve walks the tree exactly once and lands on the fixture state.
    var first = HxcStateFactory.find(root, "CacheProbeState", "state");
    if (first == null) fail("first find failed: " + HxcStateFactory.lastDiagnostic);
    if (first.path.indexOf("CacheProbeState.hxc") < 0) fail("wrong entry: " + first.path);
    if (HxcStateFactory.lookupCacheMisses != 1) fail("first find walked " + HxcStateFactory.lookupCacheMisses + " times");

    // A repeated lookup - the per-frame update case - must not re-walk.
    var second = HxcStateFactory.find(root, "CacheProbeState", "state");
    if (second == null || second.path != first.path) fail("cached find changed entry");
    if (HxcStateFactory.lookupCacheMisses != 1) fail("cached find re-walked the tree");

    // Misses are cached too: a name absent from the tree costs one walk ever.
    var missing = HxcStateFactory.find(root, "MissingState", "state");
    if (missing != null) fail("missing state resolved");
    if (HxcStateFactory.lastDiagnostic.indexOf("No manifest-owned") < 0) fail("miss diagnostic lost");
    var missesAfterMiss = HxcStateFactory.lookupCacheMisses;
    HxcStateFactory.find(root, "MissingState", "state");
    if (HxcStateFactory.lastDiagnostic.indexOf("No manifest-owned") < 0) fail("cached miss lost its diagnostic");
    if (HxcStateFactory.lookupCacheMisses != missesAfterMiss) fail("cached miss re-walked the tree");

    // Kind participates in the key: the substate resolves through its own slot.
    var popup = HxcStateFactory.find(root, "CacheProbePopup", "substate");
    if (popup == null) fail("substate find failed: " + HxcStateFactory.lastDiagnostic);
    var popupAgain = HxcStateFactory.find(root, "CacheProbePopup", "substate");
    if (popupAgain == null || popupAgain.path != popup.path) fail("substate cache hit changed entry");

    // clearLookupCache is the explicit invalidation: exactly one re-walk.
    HxcStateFactory.clearLookupCache();
    var cleared = HxcStateFactory.find(root, "CacheProbeState", "state");
    if (cleared == null || cleared.path != first.path) fail("post-clear entry changed");
    if (HxcStateFactory.lookupCacheMisses != missesAfterMiss + 2) fail("clear did not reset the cache");

    // Roots are isolated: the same name in another manifest root never
    // resolves to a sibling tree's cached entry.
    var other = HxcStateFactory.find("assets/imported_mods/otherprobe", "CacheProbeState", "state");
    if (other == null || other.path == first.path) fail("cross-root cache leaked");

    Sys.println("hxc-state-factory-cache-ok");
  }
}'''


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain unavailable; run ./run.sh once")
class HxcStateFactoryCacheTest(unittest.TestCase):
    def test_find_memoizes_walks_hits_misses_and_roots(self):
        result = run_fixture(MAIN, ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("hxc-state-factory-cache-ok", result.stdout)

    def test_factory_source_keeps_the_cache_on_the_find_path(self):
        source = (ROOT / "source/HxcStateFactory.hx").read_text()
        # The memoization sits inside find() itself, before the tree walk, and
        # records both outcomes so repeated failures never re-scan either.
        find_body = source[source.index("public static function find") :]
        self.assertLess(
            find_body.index("lookupCache.exists(key)"),
            find_body.index("discoverRoot(cleanRoot"),
            "cache check must precede the directory walk",
        )
        self.assertIn("lookupCache.set(key, {entry: null, diagnostic: missing})", source)
        self.assertIn("lookupCache.set(key, {entry: selected, diagnostic: ''})", source)
        self.assertIn("public static function clearLookupCache", source)


if __name__ == "__main__":
    unittest.main()
