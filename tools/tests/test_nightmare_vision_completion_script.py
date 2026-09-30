"""Execute the unchanged release completion script with an isolated save double.

This covers its import and callback contract, not the plugin implementation or
native gameplay integration.
"""

from pathlib import Path
import hashlib
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
DONOR = (ROOT.parent / "FNF-Example-Mods/nightmare-vision/dsides_r_11_final"
         / "content/new-dsides/scripts/Completion.hx")


class NightmareVisionCompletionScriptTest(unittest.TestCase):
    @unittest.skipUnless(DONOR.is_file(), "mounted NMV completion script unavailable")
    def test_real_completion_import_callbacks_reloads_and_owner_isolation(self):
        before = hashlib.sha256(DONOR.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(r'''
class Main {
 static var errors:Array<String> = [];
 static function eq(actual:Dynamic, expected:Dynamic):Void {
  if (actual != expected) throw 'expected '+expected+', got '+actual;
 }
 static function main():Void {
  var source = sys.io.File.getContent(Sys.args()[0]);
  var ownerA:Dynamic = {completedSongs:['existing-song']};
  var ownerB:Dynamic = {completedSongs:null};
  var flushes = 0;
  var pluginCalls = 0;
  function load(data:Dynamic):NightmareVisionScriptGroup {
   var group = new NightmareVisionScriptGroup(null, function(n,p,e):Void errors.push(n+'#'+p+': '+e));
   var module = group.loadSource('Completion.hx',source,function(interp):Void {
    interp.bindImport('funkin.scripting.PluginsManager', {
     callPluginFunc:function(plugin:String, method:String, args:Array<Dynamic>):Void {
      eq(plugin,'Utils'); eq(method,'saveFix'); eq(args.length,0);
      pluginCalls++;
      if (data.completedSongs == null) data.completedSongs=[];
     }
    });
    interp.variables.set('Paths', {sanitize:function(value:String):String
     return StringTools.replace(value.toLowerCase(),' ','-')});
    interp.variables.set('PlayState', {SONG:{song:'Contract Fixture'}});
    interp.variables.set('FlxG', {save:{data:data, flush:function():Void {flushes++;}}});
    interp.variables.set('ScriptConstants', {CONTINUE_FUNC:0});
   });
   if (module == null) throw errors.join('\n');
   return group;
  }
  var first=load(ownerA);
  eq(pluginCalls,1); eq(ownerA.completedSongs.length,1);
  eq(first.call('onEndSong'),0);
  eq(ownerA.completedSongs.join(','),'existing-song,contract-fixture');
  eq(flushes,1);
  first.destroy();
  var reloaded=load(ownerA);
  eq(reloaded.call('onEndSong'),0);
  eq(flushes,1); eq(ownerA.completedSongs.length,2);
  var other=load(ownerB);
  eq(ownerB.completedSongs.length,0);
  eq(other.call('onEndSong'),0);
  eq(ownerB.completedSongs.join(','),'contract-fixture');
  eq(ownerA.completedSongs.join(','),'existing-song,contract-fixture');
  eq(pluginCalls,3); eq(flushes,2);
  reloaded.destroy(); other.destroy(); eq(errors.length,0);
 }
}''')
            for flags in ([], ["-D", "hscriptPos"]):
                with self.subTest(flags=flags):
                    result = subprocess.run(
                        [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                         "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"),
                         "-cp", str(work)] + flags + ["--run", "Main", str(DONOR)],
                        cwd=ROOT, capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(hashlib.sha256(DONOR.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
