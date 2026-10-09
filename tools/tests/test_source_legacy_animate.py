"""Source-backed playback semantics of the published flxanimate 3.0.4 API."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]

class LegacyAnimateControllerTest(unittest.TestCase):
    def run_haxe(self, body):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
            p=Path(d)
            (p/'Main.hx').write_text('''class Main {
 static function check(v:Bool,s:String):Void {if(!v)throw s;}
 static function main() {'''+body+'''}}''')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',d,'--main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_source_signature_prefix_indices_callback_and_pause_contract(self):
        self.run_haxe(r'''
 var frames:Array<String>=[];var errors:Array<String>=[];var alive=true;
 var c=new SourceLegacyAnimateController(function(s,f) frames.push(s+":"+f),function(){if(!alive)throw "owner released";},function(e)errors.push(e));
 c.load("fixture",24,"stage",[{name:"stage",length:8},{name:"talk large",length:5},{name:"talk",length:3}]);
 check(c.stageSelected&&!c.isPlaying&&c.length==8&&frames[0]=="stage:0","initial source frame without autoplay");
 c.addBySymbol("clip","talk\\",0,false,12,-4);
 c.play("clip");
 check(c.length==3&&c.framerate==24&&c.instanceX==12&&c.instanceY== -4&&!c.stageSelected,"exact suffix, zero FPS metadata fallback, positional translation");
 c.update(1/24);check(c.curFrame==0,"strict source boundary");
 c.update(0.001);check(c.curFrame==1,"first delayed tick");
 c.pause();c.update(1);check(c.curFrame==1&&!c.isPlaying,"pause excludes elapsed time");
 var completions=0;
 c.onComplete=function(){completions++;check(c.isPlaying&&c.finished,"callback before pause");};
 c.play();c.update(0.05);check(completions==1&&c.curFrame==2&&!c.isPlaying,"one completion");
 c.update(2);check(completions==1,"no repeated finished callbacks");
 c.stop();check(c.curFrame==0&&!c.isPlaying,"stop rewinds");
 c.addBySymbolIndices("sequence","talk",[2,0,1],10,true,9,3);
 c.play("sequence");check(frames[frames.length-1]=="talk:2","indices select timeline frame");
 c.curFrame=1;check(frames[frames.length-1]=="talk:0","local index is not the native timeline index");
 c.play("sequence");check(c.curFrame==1,"replaying same indices definition preserves cursor");
 c.play("absent");check(errors.length==1&&c.isPlaying&&c.curFrame==1,"missing name logs and resumes current clip");
 c.addBySymbol("missing","nothing");check(errors.length==2,"missing symbol diagnostics");
 c.addByAnimIndices("main-sequence",[7,2],15);c.play("main-sequence");check(frames[frames.length-1]=="stage:7"&&c.framerate==15,"main timeline indices");
 var failed=false;try c.addBySymbolIndices("bad","talk",[12]) catch(_:Dynamic)failed=true;check(failed,"bad indices rejected before renderer");
 var captured=c.play;alive=false;failed=false;try captured("clip") catch(_:Dynamic)failed=true;check(failed,"captured method retains owner guard");
 c.destroy();c.destroy();alive=true;failed=false;try captured("clip") catch(_:Dynamic)failed=true;check(failed,"destroyed controller stays invalid after another owner is active");
''')

    def test_elapsed_clock_reverse_source_quirk_and_reentrant_completion(self):
        self.run_haxe(r'''
 for(fps in [60,1000]) {
  var c=new SourceLegacyAnimateController(function(s,f){},function(){},function(e){});
  c.load("fixture",24,"stage",[{name:"stage",length:8}]);c.play();
  var total=1.133;var count=Std.int(total*fps);
  for(i in 0...count)c.update(1.0/fps);c.update(total-count/fps);
  check(c.curFrame==3,"27 elapsed ticks at "+fps+" FPS");
  c.framerate=0;c.update(1);check(c.curFrame==3,"zero runtime framerate is stationary");
  c.framerate= -1;var failed=false;try c.update(0.1)catch(_:Dynamic)failed=true;check(failed,"negative rate cannot hang frame loop");
  c.destroy();
 }
 var rendered=-2;
 var c=new SourceLegacyAnimateController(function(s,f)rendered=f,function(){},function(e){});
 c.load("fixture",10,"stage",[{name:"stage",length:4}]);
 c.addBySymbol("once","stage\\",10,false);c.play("once",true,true,0);
 check(c.curFrame==0&&c.finished&&c.isPlaying,"historical reverse Frame-length clamps to zero for play-once");
 c.play("once",true,false,0);
 c.onComplete=function(){c.play("once",true);};c.update(0.31);
 check(c.curFrame==0&&!c.isPlaying,"source pauses after a completion callback that starts another animation");
 c.onComplete=function(){c.destroy();};c.play("once",true);c.update(0.4);check(!c.isPlaying,"completion can destroy its owner safely");
''')

    def test_stage_instance_first_frame_loop_reverse_and_scoped_reflection_cleanup(self):
        self.run_haxe(r'''
 var c=new SourceLegacyAnimateController(function(s,f){},function(){},function(e){});
 c.load("fixture",10,"stage",[{name:"stage",length:8}],5,"POR");
 check(c.curFrame==5&&c.reversed&&!c.finished,"stage instance first frame and reverse");
 c.addByAnimIndices("sequence",[5,3],10);c.play("sequence",true);c.update(0.11);
 check(c.finished&&!c.isPlaying,"indices inherit stage play-once");
 c.load("fixture",10,"stage",[{name:"stage",length:8}],12,"SF");
 check(c.curFrame==12&&!c.finished,"single-frame cursor is not clamped to play-once");
 var a:Dynamic={anim:"native-a"};var b:Dynamic={anim:"native-b"};
 var scope=new SourceNativeClassScope();scope.installReflectionBindings();
 scope.bindStaticField(a,"anim",function()return c,function(v){throw "readonly";return v;});
 scope.bindStaticField(b,"anim",function()return "other-owner");
 var reflect=scope.reflectFacade();
 check(reflect.field(a,"anim")==c&&reflect.getProperty(a,"anim")==c,"field and property share instance route");
 var failed=false;try reflect.setProperty(a,"anim",null)catch(_:Dynamic)failed=true;
 check(failed,"source anim route is readonly");
 scope.unbindStaticFields(a);
 check(!scope.hasBinding(a,"anim")&&scope.read(a,"anim")=="native-a","destroy detaches all instance closures");
 check(scope.read(b,"anim")=="other-owner"&&scope.hasBinding(Reflect,"field"),"cleanup preserves other instances and class routes");
 c.destroy();scope.release();
''')

    def test_owner_atlas_loader_uses_declared_ids_and_unique_owner_cache(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
            p=Path(d);(p/'animate').mkdir()
            (p/'animate/FlxAnimateFrames.hx').write_text('''package animate;
typedef SpritemapInput={source:Dynamic,json:String};
class FlxAnimateFrames {
 public var key:String;public var unique:Bool;public var maps:Array<SpritemapInput>;
 public function new(k:String,u:Bool,m:Array<SpritemapInput>){key=k;unique=u;maps=m;}
 public static function fromAnimate(a:String,s:Array<SpritemapInput>,m:String,k:String,u:Bool):FlxAnimateFrames return new FlxAnimateFrames(k,u,s);
}''')
            (p/'Main.hx').write_text(r'''class Main {
 static function check(v:Bool,s:String):Void {if(!v)throw s;}
 static function main(){
 var calls:Array<String>=[];var alive=true;
 var assets={getText:function(id:String):String{calls.push("text:"+id);return id.indexOf("spritemap")>=0 ? String.fromCharCode(0xFEFF)+haxe.Json.stringify({meta:{image:id.indexOf("spritemap1")>=0?"second.png":"pixels.png"}}) : "{}";},
  getBitmapData:function(id:String):Dynamic{calls.push("image:"+id);return id;},
  list:function(type:String):Array<String>{throw "partial owner catalogs cannot be enumerated";},
  exists:function(id:String,type:String):Bool return ["assets/a/spritemap.json","assets/a/spritemap1.json","assets/a/second.png","assets/a/pixels.png"].indexOf(id)>=0};
 var guard=function(){if(!alive)throw "released";};
 var a=SourceAnimateAtlasLoader.load("assets/a/",assets,guard,"owner-a");
 var b=SourceAnimateAtlasLoader.load("assets/a",assets,guard,"owner-b");
 check(a.frames.key!=b.frames.key&&a.frames.unique&&b.frames.unique,"owner and per-instance cache isolation");
 check(a.frames.maps.length==2&&a.frames.maps[0].source=="assets/a/pixels.png","all direct declared spritemaps in deterministic order");
 check(calls.indexOf("text:assets/other/spritemap.json")== -1,"no unrelated asset reads");
 var n=calls.length;alive=false;var failed=false;
 try SourceAnimateAtlasLoader.load("assets/a",assets,guard,"owner-a")catch(_:Dynamic)failed=true;
 check(failed&&calls.length==n,"released owner cannot perform IO");
 alive=true;assets.exists=function(id:String,type:String):Bool return id=="assets/a/spritemap.json";
 failed=false;try SourceAnimateAtlasLoader.load("assets/a",assets,guard,"owner-a")catch(_:Dynamic)failed=true;
 check(failed,"missing image fails with no global or filename guessing fallback");
 }
}''')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',d,'--main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
