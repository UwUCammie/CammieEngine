"""Pinned NV animation hook admission, receiver/super scope and sprite defaults."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class LegacyNoteAnimationsTest(unittest.TestCase):
 def test_pinned_callback_dispatch_and_defaults(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned source unavailable')
  source=subprocess.check_output(['git','show',REV+':source/gameObjects/Note.hx'],cwd=donor,text=True)
  normal=method(source,'public function loadNoteAnims()')
  pixel=method(source,'public function loadPixelNoteAnims()')
  defaults=method(source,'function _loadNoteAnims()').replace('function _loadNoteAnims()','public function sourceDefaults()')
  fixture=r"""import flixel.math.FlxPoint;
class PlayState {public static var SONG:Dynamic={keys:4};}
class FunkinHScript {
 public var scriptType='hscript';var module:NightmareVisionScriptModule;
 public function new(m:NightmareVisionScriptModule)module=m;
 public function exists(n:String):Bool return module.exists(n);
 public function get(n:String):Dynamic return module.get(n);
 public function executeFunc(n:String,args:Array<Dynamic>,receiver:Dynamic,?extra:Map<String,Dynamic>):Dynamic return module.executeFunc(n,args,receiver,extra);
}
class FakeAnim {
 public var rows:Map<String,Dynamic>=new Map();
 public function getByName(n:String):Dynamic return rows.get(n);
 public function add(n:String,frames:Array<Int>,fps:Float=30,loop:Bool=true,flipX:Bool=false,flipY:Bool=false):Void rows.set(n,{frames:frames,frameRate:fps,looped:loop,flipX:flipX,flipY:flipY});
 public function new(){}
 public function addByPrefix(n:String,p:String,fps:Float=30,loop:Bool=true):Void rows.set(n,{prefix:p,fps:fps,loop:loop});
}
class Reference {
 public var nightmareVisionTypeRuntime:Dynamic;
 public var noteData=0;
 public var noteScript:FunkinHScript;
 public var events:Array<String>=[];public var isSustainNote=false;public var width=161.;public var scale=new FlxPoint(1,1);public var baseScale=new FlxPoint();public var baseScaleX=1.;public var baseScaleY=1.;
 public var animation=new FakeAnim();
 public function new(){}
 public function setGraphicSize(w:Int):Void scale.set(w/width,w/width);
 public function updateHitbox():Void {}
 function _loadNoteAnims():Void events.push('normal-default');
 function _loadPixelNoteAnims():Void events.push('pixel-default');
 __NORMAL__
 __PIXEL__
 __DEFAULTS__
}
class Main {
 static function check(ok:Bool,s:String):Void if(!ok)throw s;
 static function module(code:String,errors:Array<String>):NightmareVisionScriptModule return NightmareVisionScriptModule.fromSource('type',code,null,null,null,function(n,p,e)errors.push(p));
 static function main(){
  var programs=[
   '',
   'function loadNoteAnims(n) { if (this != n) throw "receiver"; n.events.push("normal-custom"); super(); n.events.push("normal-after"); } function loadPixelNoteAnims(n) { n.events.push("pixel-custom"); super(); }',
   'function loadPixelNoteAnims(n) { n.events.push("pixel-only"); }',
   'loadNoteAnims = 7; function loadPixelNoteAnims(n) { n.events.push("pixel-custom"); }',
   'function loadNoteAnims(n) { n.events.push("replace"); } loadPixelNoteAnims = 5;',
   'function loadNoteAnims(n) { n.events.push("before-error"); throw "expected"; } function loadPixelNoteAnims(n) { throw "expected-pixel"; }',
   'function loadNoteAnims(n) { super(); super(); } function loadPixelNoteAnims(n) { super(); super(); }'
  ];
  for(code in programs)for(pixel in [false,true]){
   var expected=new Reference(),actual=new Reference();var expectedErrors=[],actualErrors=[];
   var a=module(code,expectedErrors),b=module(code,actualErrors);expected.noteScript=new FunkinHScript(a);
   var oldThis={marker:'owner'};var oldSuper=function(){};
   a.set('this',oldThis);b.set('this',oldThis);a.set('super',oldSuper);b.set('super',oldSuper);
   if(pixel)expected.loadPixelNoteAnims();else expected.loadNoteAnims();
   NightmareVisionLegacyNoteAnimations.dispatch(b,actual,pixel,function()actual.events.push(pixel?'pixel-default':'normal-default'));
   check(expected.events.join('|')==actual.events.join('|'),'callback source order '+code+' pixel='+pixel);
   check(expectedErrors.join('|')==actualErrors.join('|'),'source error/fallback behavior');
   check(b.get('this')==oldThis&&b.get('super')==oldSuper,'receiver and super restored');
   a.destroy();b.destroy();
  }
  for(keys in [4,7])for(hold in [false,true]){
   PlayState.SONG.keys=keys;var expected=new Reference(),actual=new Reference();expected.isSustainNote=actual.isSustainNote=hold;
   expected.sourceDefaults();NightmareVisionLegacyNoteAnimations.defaults(actual,keys);
   for(n in expected.animation.rows.keys()) {
    var a=expected.animation.rows.get(n),b=actual.animation.rows.get(n);
    check(b!=null&&a.prefix==b.prefix&&a.fps==b.fps&&a.loop==b.loop,'source default animation '+n);
   }
   check(expected.scale.x==actual.scale.x&&expected.baseScaleY==actual.baseScaleY,'source scale rounding');
  }
  for(lane in 0...7)for(hold in [false,true]) {
   var n=new Reference();n.noteData=lane;n.isSustainNote=hold;
   n.nightmareVisionTypeRuntime={loadLegacyAnimations:function(note:Dynamic,pixel:Bool,fallback:Void->Void){
    var color=['purple','blue','green','red','fx','LLAZER','RLAZER'][note.noteData];
    for(kind in (note.isSustainNote?['hold','holdend']:['Scroll'])) note.animation.add(color+kind,[7,2],17,false,true,true);
   }};
   NightmareVisionLegacyNoteAnimations.load(n,false,7);
   for(kind in (hold?['hold','holdend']:['Scroll'])) {
    var anim=n.animation.getByName(kind);
    check(anim!=null&&anim.frames.join(',')=='7,2'&&anim.frameRate==17&&!anim.looped&&anim.flipX&&anim.flipY,'custom source alias retained '+lane+kind);
   }
   check(n.scale.x==1,'replacement must not run defaults');
  }
  var a=module('function loadNoteAnims(n) { super(); n.events.push("outer"); }',[]);
  var b=module('function loadNoteAnims(n) { super(); n.events.push("inner"); }',[]);
  var first=new Reference(),second=new Reference();
  NightmareVisionLegacyNoteAnimations.dispatch(a,first,false,function(){NightmareVisionLegacyNoteAnimations.dispatch(b,second,false,function()second.events.push('inner-base'));first.events.push('outer-base');});
  check(first.events.join(',')=='outer-base,outer'&&second.events.join(',')=='inner-base,inner','nested callbacks retain independent receiver/super scopes');
  a.destroy();b.destroy();
 }
}
""".replace('__NORMAL__',normal).replace('__PIXEL__',pixel).replace('__DEFAULTS__',defaults)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
   work=FixturePath(d);write_flixel_point_stub(work);(work/'Main.hx').write_text(fixture)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript-iris/1,1,3'),'-cp',str(work),'--main','Main','--interp'],cwd=ROOT,capture_output=True,text=True,timeout=45)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
