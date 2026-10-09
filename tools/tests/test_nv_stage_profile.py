"""Compiled class evidence, authenticated parent inheritance and runtime identity."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]
class NVStageProfileTest(unittest.TestCase):
 def test_class_markers_and_owner_bound_publication(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   work=Path(directory)
   for label,markers in [('old',b'Nightmare Vision Engine\0meta.data.scripts.IFunkinScript\0gameObjects.Stage\0'),('new',b'com.nmvTeam.nightmareEngine\0funkin.objects.Stage\0'),('mixed',b'com.nmvTeam.nightmareEngine\0gameObjects.Stage\0funkin.objects.Stage\0'),('prefix',b'com.nmvTeam.nightmareEngine\0gameObjects.StageData\0'),('unproven',b'gameObjects.Stage\0')]:
    root=work/label;(root/'assets/data/song').mkdir(parents=True);(root/'content/pack').mkdir(parents=True);(root/'assets/images').mkdir()
    (root/'assets/data/song/song.json').write_text('{"song":{"song":"song","notes":[],"bpm":120}}')
    (root/'game.exe').write_bytes(b'MZ\0'+markers)
    (root/'content/pack/meta.json').write_text('{"name":"Authored package"}')
   # A helper executable containing a class name cannot hide the real game.
   (work/'old/0-helper.exe').write_bytes(b'MZ\0funkin.objects.Stage\0')
   (work/'Main.hx').write_text(r'''
class Main {
 static function ok(b:Bool,s:String)if(!b)throw s;
 static function main(){
  var base=Sys.args()[0];
  for(pair in [["old","legacy-group"],["new","modern-container"],["mixed","unknown"],["prefix","unknown"],["unproven","unknown"]]) {
   ok(ImportRootScanner.nightmareVisionStageApi(base+"/"+pair[0])==pair[1],"class proof "+pair[0]);
  }
  var installed=base+"/runtime";sys.FileSystem.createDirectory(installed);
  var payload=NightmareVisionStageImportProfile.capture(base+"/old/content/pack",installed);
  ok(haxe.Json.parse(payload).stageApi=="legacy-group","authenticated parent identity");
  ok(ImportGeneratedOutput.write(installed+"/"+NightmareVisionStageProfile.FILE_NAME,payload,true),"generated profile write");
  ok(NightmareVisionStageProfile.read(installed)=="legacy-group","runtime profile read");
  var conflict=false;try ImportGeneratedOutput.write(installed+"/"+NightmareVisionStageProfile.FILE_NAME,"{}",true)catch(e:Dynamic)conflict=true;
  ok(conflict&&NightmareVisionStageProfile.read(installed)=="legacy-group","existing metadata preserved on conflict");
  var other=base+"/other";sys.FileSystem.createDirectory(other);sys.io.File.saveContent(other+"/"+NightmareVisionStageProfile.FILE_NAME,payload);
  ok(NightmareVisionStageProfile.read(other)=="unknown","profile copied across owners must not bind");
  ok(haxe.Json.parse(NightmareVisionStageImportProfile.capture(base+"/unproven/content/pack",other)).stageApi=="unknown","unproven ancestor cannot choose dialect");
  ok(haxe.Json.parse(NightmareVisionStageImportProfile.capture(base+"/new/assets",other)).stageApi=="modern-container","explicit authenticated core identity");
  sys.io.File.saveContent(other+"/"+NightmareVisionStageProfile.FILE_NAME,"bad");ok(NightmareVisionStageProfile.read(other)=="unknown","invalid metadata");
 }
}
''')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',directory,'--run','Main',directory.replace('\\','/')],cwd=work,capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
