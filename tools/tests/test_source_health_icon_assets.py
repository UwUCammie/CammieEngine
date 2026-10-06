"""Owner-local Psych icon GPU preparation and immutable source face fallbacks."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]
class SourceHealthIconAssetsTest(unittest.TestCase):
 def test_gpu_hint_pref_cache_and_owner_isolation(self):
  files={
   'flixel/FlxG.hx':'package flixel;class FlxG {public static var stage={context3D:"ctx"};}',
   'openfl/display/BitmapData.hx':'''package openfl.display;
class BitmapData {public var image(default,null):Dynamic={premultiplied:false,data:"cpu"};private var __texture:Dynamic;public var readable(default,null)=false;public var log:Array<String>=[];public var destroyed=false;public function new(){}public function clone():BitmapData {var b=new BitmapData();return b;}public function lock(){log.push("lock");}public function getTexture(v:Dynamic){log.push("texture");__texture=v;}public function getSurface(){log.push("surface");}public function disposeImage(){log.push("dispose");}public function destroy(){destroyed=true;}}
''',
   'flixel/graphics/FlxGraphic.hx':'''package flixel.graphics;import openfl.display.BitmapData;class FlxGraphic {public var bitmap:BitmapData;public var persist=false;public var destroyOnNoUse=true;public var destroyed=false;public function new(){bitmap=new BitmapData();}public static function fromBitmapData(b:BitmapData,u:Bool,k:String,c:Bool):FlxGraphic {if(c)throw "shared cache";var g=new FlxGraphic();g.bitmap=b;return g;}public function destroy(){destroyed=true;bitmap.destroy();}}
''',
   'Main.hx':'''import flixel.graphics.FlxGraphic;class Main {static function ok(v:Bool,m:String)if(!v)throw m;static function main(){for(gpu in [false,true])for(pref in [false,true]){var source=new FlxGraphic();var a=new SourceHealthIconAssets();var calls=0;var g=a.psychImage("face",()->{calls++;return source;},gpu,pref);ok(g!=source&&g.bitmap!=source.bitmap,"local clone");ok(source.bitmap.image!=null&&source.bitmap.log.length==0,"original untouched");ok(g.persist&&!g.destroyOnNoUse,"source retention");if(gpu&&pref){ok(g.bitmap.log.join(",")=="lock,texture,surface,dispose","source GPU order");ok(g.bitmap.image==null&&g.bitmap.readable,"source disposal");}else ok(g.bitmap.image!=null&&g.bitmap.log.length==0,"both guards required");var again=a.psychImage("face",()->{calls++;return source;},!gpu,!pref);ok(again==g&&calls==1,"first cached load wins");var b=new SourceHealthIconAssets();var other=b.psychImage("face",()->source,false,false);ok(other!=g&&other.bitmap.image!=null,"owner isolated");a.release();a.release();ok(g.destroyed&&!other.destroyed&&!source.destroyed,"owned teardown");var threw=false;try a.psychImage("new",()->source,false,false)catch(e:Dynamic)threw=true;ok(threw,"released guard");b.release();}}}'''
  }
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   for name,content in files.items():
    p=Path(tmp)/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
   env=os.environ.copy();env['HAXEPATH']=str(ROOT/'.tools/haxe');env['NEKOPATH']=str(ROOT/'.tools/neko');env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['PATH']=os.pathsep.join((env['HAXEPATH'],env['NEKOPATH'],env.get('PATH','')))
   common=[*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',tmp,'-main','Main']
   for args in [['--interp'],['-cpp',str(Path(tmp)/'cpp'),'-D','no-compilation']]:
    r=subprocess.run(common+args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    self.assertEqual(r.returncode,0,str(args)+(r.stdout+r.stderr)[-2500:])
 def test_source_faces_match_immutable_donors(self):
  for engine,donor in [('psych','FNF-PsychEngine/assets/shared/images/icons/icon-face.png'),('nightmare-vision','NightmareVision/assets/game/images/UI/icons/icon-face.png')]:
   actual=(ROOT/f'assets/images/source_compat/{engine}/icon-face.png').read_bytes()
   self.assertEqual(actual,(ROOT.parent/'fnf_sources'/donor).read_bytes())
   self.assertEqual(actual[:8],b'\x89PNG\r\n\x1a\n')
  owner=(ROOT/'source/PlayState.hx').read_text()
  self.assertIn("psychClientPrefs.data.cacheOnGPU == true",owner)
  self.assertIn(".image(name, null, gpu)",owner)
  self.assertIn("name == 'icons/icon-face' || name == 'UI/icons/icon-face'",owner)
if __name__=='__main__':unittest.main()
