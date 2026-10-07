"""Source stock bar fallback keeps owner art and native frames intact."""
import hashlib
import os
import struct
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from haxe_test_support import HAXE_COMMAND
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
HASHES={('psych','healthBar'):'8e162551c302133fac8210e1d9474dfe98dc4d5e382df9ce8648a029a11eab38',('psych','timeBar'):'935ea71c0219c9b7c999e691666967ba530d51294552f3c6108b05dd0ad3ce2c',('nightmare-vision','healthBar'):'41aa205c93bed307ccb1988151976b54485d349faf3a45498ba932087ab3dc6d',('nightmare-vision','timeBar'):'98823261a619d592d2c1825d4cd1a159e160dd18f3c8cee125d3ba1f1d1ddafe'}

def rgba_png(path):
 data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n';chunks=[];offset=8
 while offset<len(data):
  size=struct.unpack('>I',data[offset:offset+4])[0];kind=data[offset+4:offset+8];payload=data[offset+8:offset+8+size];chunks.append((kind,payload));offset+=size+12
 width,height,depth,color,comp,filt,interlace=struct.unpack('>IIBBBBB',dict(chunks)[b'IHDR']);assert (depth,color,comp,filt,interlace)==(8,6,0,0,0)
 packed=zlib.decompress(b''.join(payload for kind,payload in chunks if kind==b'IDAT'));stride=width*4;previous=bytearray(stride);rows=[]
 for row in range(height):
  start=row*(stride+1);filtertype=packed[start];current=bytearray(packed[start+1:start+stride+1])
  for x in range(stride):
   a=current[x-4] if x>=4 else 0;b=previous[x];c=previous[x-4] if x>=4 else 0
   if filtertype==1:prediction=a
   elif filtertype==2:prediction=b
   elif filtertype==3:prediction=(a+b)//2
   elif filtertype==4:
    p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c);prediction=a if pa<=pb and pa<=pc else b if pb<=pc else c
   else:assert filtertype==0;prediction=0
   current[x]=(current[x]+prediction)&255
  rows.append(current);previous=current
 return width,height,b''.join(rows)

class SourceBarAssetTest(unittest.TestCase):
 def test_immutable_donor_frame_pixels_dimensions_and_native_difference(self):
  native=ROOT/'assets/images/healthBar.png';native_hash=hashlib.sha256(native.read_bytes()).hexdigest()
  for (engine,name),expected in HASHES.items():
   path=ROOT/'assets/images/source_compat'/engine/(name+'.png');raw=path.read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),expected)
   width,height,pixels=rgba_png(path);self.assertEqual((width,height),(601 if name=='healthBar' else 400,19));self.assertEqual(pixels[((height//2)*width+width//2)*4+3],0)
  width,height,pixels=rgba_png(native);self.assertEqual(pixels[((height//2)*width+width//2)*4+3],255);self.assertEqual(hashlib.sha256(native.read_bytes()).hexdigest(),native_hash)

 def test_actual_psych_resolver_and_nv_bar_owner_fallback_precedence(self):
  psych=method((ROOT/'source/PsychOwnerPaths.hx').read_text(),'static function image(').replace('static function image','public static function image',1)
  owner=method((ROOT/'source/PlayState.hx').read_text(),'function sourceBarOwner(').replace('function sourceBarOwner','public function sourceBarOwner',1)
  files={
   'flixel/graphics/FlxGraphic.hx':'package flixel.graphics;class FlxGraphic {public var path:String;public function new(p:String)path=p;}',
   'FNFAssets.hx':'class FNFAssets {public static var available:Map<String,Bool>=[];public static function exists(p:String)return available.exists(p)||sys.FileSystem.exists(p);public static function getFlxGraphic(p:String):flixel.graphics.FlxGraphic return new flixel.graphics.FlxGraphic(p);}',
   'Paths.hx':'class Paths {public static function file(p:String,t:Dynamic,l:String)return "native/"+p;}',
   'PsychOwnerAssetPath.hx':'class PsychOwnerAssetPath {public static function cleanId(k:String):String return k;}',
   'PsychOwnerPaths.hx':'import flixel.graphics.FlxGraphic;class PsychOwnerPaths {static var IMAGE=0;public static var selected:String;static function ownerAsset(o:String,k:String,l:String,c:String):String return selected;static function graphic(p:String):FlxGraphic return FNFAssets.getFlxGraphic(p);public static function create(o:String,?l:String):Dynamic return {image:(key:String)->image(o,key,l,l)};'+psych+'}',
   'NightmareVisionPaths.hx':'class NightmareVisionPaths {public var root="fixture";public function getAtlasFrames(p:String):flixel.graphics.frames.FlxAtlasFrames return new flixel.graphics.frames.FlxAtlasFrames();public var available=false;public function new(){}public function getPath(p:String,?f:String,mods:Bool=false)return "owner-core/"+p;public function exists(p:String)return available;public function image(k:String):flixel.graphics.FlxGraphic {if(!available)throw "missing source";return new flixel.graphics.FlxGraphic("selected/"+k);}}',
   'OptionsHandler.hx':'class OptionsHandler {public static var options={antialiasing:true};}',
   'Main.hx':'''class Host {public var nightmareVisionPaths=new NightmareVisionPaths();public var psychStageLibrary:String;public var psychClientPrefs:Dynamic;public function new(){}function selectedPsychSkinRoot()return "owner";__OWNER__}
class Main {static function ok(v:Bool,m:String):Void if(!v)throw m;static function main(){for(key in ["healthBar","timeBar"]){PsychOwnerPaths.selected="authored/"+key;var owned=PsychOwnerPaths.image("owner",key,null,null);ok(owned.path=="authored/"+key,"authored Psych image first");PsychOwnerPaths.selected=null;var fallback=PsychOwnerPaths.image("owner",key,null,null);ok(fallback.path==SourceBarAssets.coreImage("psych",key),"stock source fallback before opaque native");}FNFAssets.available.set("native/images/custom.png",true);ok(PsychOwnerPaths.image("owner","custom",null,null).path=="native/images/custom.png","unrelated legacyfallback intact");var host=new Host();var captured=host.nightmareVisionPaths;captured.available=true;var nv=host.sourceBarOwner(true);ok(nv.image("UI/healthBar").path=="selected/UI/healthBar","selected NV owner/core first");captured.available=false;ok(nv.image("UI/healthBar").path==SourceBarAssets.coreImage("nightmare-vision","UI/healthBar"),"missing NV stock frame fallback");ok(nv.image("UI/core/timeBar").path==SourceBarAssets.coreImage("nightmare-vision","UI/core/timeBar"),"profile stock time frame fallback");var rejected=false;try nv.image("custom")catch(_:Dynamic)rejected=true;ok(rejected,"missing custom sourceimage notrewritten");host.nightmareVisionPaths=new NightmareVisionPaths();captured.available=true;ok(nv.image("UI/timeBar").path=="selected/UI/timeBar","captured owner retained");ok(SourceBarAssets.coreImage("psych","../healthBar")==null&&SourceBarAssets.coreImage("psych","custom/healthBar")==null&&SourceBarAssets.coreImage("native","healthBar")==null,"only scoped source stockkeys");}}
'''.replace('__OWNER__',owner)}
  files['flixel/graphics/frames/FlxAtlasFrames.hx']='package flixel.graphics.frames;class FlxAtlasFrames {public function new(){}}'
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as tmp:
   work=Path(tmp)
   for name,content in files.items():
    path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8')
   env=os.environ.copy();env['HAXELIB_PATH']=str(ROOT/'.haxelib');env['NEKOPATH']=str(ROOT/'.tools/neko');env['PATH']=str(ROOT/'.tools/haxe')+os.pathsep+str(ROOT/'.tools/neko')+os.pathsep+env.get('PATH','')
   for target in [['--interp'],['-cpp',str(work/'cpp'),'-D','no-compilation']]:
    result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',tmp,'-main','Main',*target],cwd=ROOT,env=env,capture_output=True,text=True,timeout=35)
    self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-4000:])
