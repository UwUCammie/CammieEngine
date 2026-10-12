"""Authored alternate song audio is scoped and separate for each chart difficulty."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT=Path(__file__).resolve().parents[2]
class DifficultySongMediaTest(unittest.TestCase):
 def test_alternate_audio_and_vocal_metadata(self):
  fixture=r'''import sys.FileSystem as FS;import sys.io.File;
class Main {static function check(v:Bool,s:String):Void if(!v)throw s;
 static function main(){var root=Sys.args()[0];FS.createDirectory(root+'/songs/track');FS.createDirectory(root+'/songs/track-remix');
  File.saveContent(root+'/songs/track/Inst.ogg','base');File.saveContent(root+'/songs/track-remix/Inst.ogg','alternate');
  File.saveContent(root+'/songs/track-remix/Voices-Player.ogg','player');File.saveContent(root+'/songs/track-remix/Voices-Opponent.ogg','opponent');
  var p=DifficultySongMedia.plan(root+'/songs','track','Track Remix','track-demon.json','track');
  check(p!=null && p.files.length==3 && p.files[0].destination=='Inst-demon.ogg','alternate media absent');
  check(File.getContent(p.files[0].source)=='alternate','base audio reused');
  check(p.stems.length==2 && p.stems[0].role=='opponent' && p.stems[1].role=='player','split voice roles missing');
  check(p.stems[0].file=='Voices-opponent-demon.ogg','wrong named voice file');
  check(DifficultySongMedia.plan(root+'/songs','track','track','track-hard.json','track')==null,'base changed');
  check(DifficultySongMedia.plan(root+'/songs','track','../outside','track-hard.json','track')==null,'unsafe authored name escaped');
  FS.deleteFile(root+'/songs/track-remix/Inst.ogg');var rejected=false;
  try DifficultySongMedia.plan(root+'/songs','track','track-remix','track-demon.json','track') catch(_:Dynamic) rejected=true;
  check(rejected,'missing alternate instrumental silently fell back');
 }}'''
  with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
   work=Path(temp);(work/'Main.hx').write_text(fixture);install=work/'install';install.mkdir()
   r=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main',str(install)],cwd=work,capture_output=True,text=True,timeout=60)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
