"""Botplay policy comes from declared note behavior, never content names."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NoteAutoplayPolicyTest(unittest.TestCase):
    def test_hazard_policy_and_selected_root_recovery(self):
        source = r'''
import sys.FileSystem;
import sys.io.File;
class Main {
 static function check(value:Bool, message:String):Void if(!value) throw message;
 static function script(hit:String,miss:String):String return
  'class UnexpectedName extends NoteKind { function new() {super("optional-spike","","arrows",[]);}'
  +'function onNoteHit(packet) {'+hit+'} function onNoteMiss(missed) {'+miss+'}}';
 static function main():Void {
  var harmful=script('if(packet.judgement=="perfect") return; PlayState.instance.health = -1;', 'missed.cancel();');
  check(HxcCompat.noteKindAvoidsHits(harmful),'lethal callback with cancelled misses');
  var analyzed=HxcCompat.analyze(harmful,'unrelated-filename.hxc');
  check(analyzed.nativeNoteDefinitions.length==1,'declared constructor kind');
  check(analyzed.nativeNoteDefinitions[0].avoidAutoHit==true,'new import policy');
  check(HxcCompat.noteKindAvoidsHits(script('PlayState.instance.health -= 0.25;','missed.cancel();')),'positive drain');
  check(HxcCompat.noteKindAvoidsHits(script('packet.healthChange = -0.2;','missed.cancel();')),'negative event health');
  check(!HxcCompat.noteKindAvoidsHits(script('PlayState.instance.health += 0.1;','missed.cancel();')),'healing notes');
  check(!HxcCompat.noteKindAvoidsHits(script('PlayState.instance.health -= 0;','missed.cancel();')),'zero drain');
  check(!HxcCompat.noteKindAvoidsHits(script('PlayState.instance.health = -1;','')),'required note is not inferred optional');
  check(!HxcCompat.noteKindAvoidsHits(script('trace("PlayState.instance.health = -1;");','missed.cancel();')),'text is not damage');
  check(!HxcCompat.noteKindAvoidsHits(script('// PlayState.instance.health = -1;\n','missed.cancel();')),'comment is not damage');
  check(!HxcCompat.noteKindAvoidsHits(script('', 'PlayState.instance.health = -1; missed.cancel();')),'miss damage is not hit damage');
  var root=Sys.args()[0];
  FileSystem.createDirectory(root+'/scripts');
  FileSystem.createDirectory(root+'/scripts/notekinds');
  FileSystem.createDirectory(root+'/scripts/notes');
  File.saveContent(root+'/scripts/notekinds/arbitrary.hxc',harmful);
  var definitions:Array<Dynamic>=[
   {sourceEngine:'V-Slice',sourceKind:'optional-spike'},
   {sourceEngine:'V-Slice',sourceKind:'unrelated'},
   {sourceEngine:'Psych',sourceKind:'optional-spike'},
   {sourceEngine:'V-Slice',sourceKind:'optional-spike',avoidAutoHit:false}];
  check(VSliceImporter.applyRuntimeNoteKindPolicies(definitions,root)==1,'only matching selected-root definition');
  check(definitions[0].avoidAutoHit==true,'stale import recovered in memory');
  check(definitions[1].avoidAutoHit==null && definitions[2].avoidAutoHit==null,'foreign identities untouched');
  check(definitions[3].avoidAutoHit==false,'explicit policy preserved');
  check(VSliceImporter.applyRuntimeNoteKindPolicies(definitions,root)==0,'idempotence');
 }
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            path = Path(folder)
            (path / 'Main.hx').write_text(source, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                 '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', folder,
                 '--run', 'Main', folder], cwd=ROOT, capture_output=True,
                text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
