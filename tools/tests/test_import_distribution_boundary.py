"""Recognize packaged game roots without walking arbitrary tooling output."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP

ROOT = Path(__file__).resolve().parents[2]


class ImportDistributionBoundaryTest(unittest.TestCase):
    def run_haxe(self, folder, body, *args):
        (folder / "Main.hx").write_text("class Main { static function main() {" + body + "}}")
        result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder),
                                 "--run", "Main", *map(str, args)], cwd=ROOT,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def psych(self, root):
        (root / "data/track").mkdir(parents=True)
        (root / "songs/track").mkdir(parents=True)
        (root / "images").mkdir()
        (root / "pack.json").write_text(json.dumps({"name": "A supported game"}))
        (root / "data/track/track.json").write_text(json.dumps({"song": {
            "song": "track", "bpm": 120, "notes": [{"mustHitSection": True,
            "sectionNotes": [[1000, 0, 0]]}]}}))
        (root / "songs/track/Inst.ogg").write_bytes(b"fixture")

    def test_distribution_boundary_is_classified_once_and_tooling_stays_pruned(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            work = Path(temp)
            corpus = work / "corpus"
            for relative in ("download-a/BIN", "download-b/dist", "ordinary",
                             "ordinary/bin", ".tools/bin", "sdk/bin/deep/game", "sdk/dist/deep/game"):
                self.psych(corpus / relative)
            self.run_haxe(work, r"""
var root=StringTools.replace(Sys.args()[0], "\\", "/");
var visited:Array<String>=[];
var result=ImportRootScanner.scanDetailed(root,ImportEngine.AUTO,{
 onProgress:function(progress) visited.push(StringTools.replace(progress.current,"\\","/"))});
var expected=[root+"/download-a/BIN",root+"/download-b/dist",root+"/ordinary"];
var actual=[for(found in result.roots) StringTools.replace(found.root,"\\","/")];
actual.sort(Reflect.compare);expected.sort(Reflect.compare);
if(haxe.Json.stringify(actual)!=haxe.Json.stringify(expected))throw haxe.Json.stringify(actual);
if(result.truncated)throw "bounded distribution scan truncated";
for(path in visited) if(path.indexOf("/deep")>=0 || path.indexOf("/.tools")>=0 || path.indexOf("/ordinary/bin")>=0)
 throw "tool/build output descended: "+path;
if(visited.indexOf(root+"/sdk/bin")<0 || visited.indexOf(root+"/sdk/dist")<0)throw "boundary not inspected";
var explicit=ImportRootScanner.scan(root+"/ordinary/bin");
if(explicit.length!=1 || explicit[0].engine!=ImportEngine.PSYCH)throw "explicitly selected bin was lost";
""", corpus)

    def test_real_nested_game_download_is_detected_read_only(self):
        donor = ROOT.parent / "fnf_example_mods/psych/vs_fnaf_1_minecraft_mix_week_b_update"
        if not donor.is_dir():
            self.skipTest("nested real game download unavailable")
        sample = donor / "bin/VS FNAF 1 Minecraft Mix.exe"
        before = hashlib.sha256(sample.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            self.run_haxe(Path(temp), r"""
var root=StringTools.replace(Sys.args()[0],"\\","/");
var scan=ImportRootScanner.scanDetailed(root);
if(scan.truncated || scan.roots.length==0)throw "real nested game not detected";
var found=false;
for(candidate in scan.roots) if(StringTools.replace(candidate.root,"\\","/")==root+"/bin")found=true;
if(!found)throw "distribution root missing";
""", donor)
        self.assertEqual(hashlib.sha256(sample.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
