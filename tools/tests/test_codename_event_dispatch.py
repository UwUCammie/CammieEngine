"""Execute structured Codename callbacks with actual HScript and native routing."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

class CodenameEventDispatchTest(unittest.TestCase):
    def test_play_animation_default_action_matches_donor_contract(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('\tpublic function applyCodenameNativeEvent(')
        brace = source.index('{', start)
        depth = 0
        for index in range(brace, len(source)):
            depth += (source[index] == '{') - (source[index] == '}')
            if depth == 0:
                method = source[start:index + 1]
                break
        else:
            self.fail('could not extract applyCodenameNativeEvent')
        self.assertIn('CodenameEventDispatch.applyPlayAnimation(event', method)
        self.assertIn('actor.codenamePlayAnim(animationName, force, context)', method)

        fixture = r'''class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static var actors:Array<Dynamic>=[
  {name:"grab-only",animations:["grab"]},
  {name:"grab-and-idle",animations:["grab","idle"]},
  {name:"idle-only",animations:["idle"]}
 ];
 static function charactersAt(index:Int):Array<Dynamic> return index==0 ? actors : null;
 static function hasAnimation(actor:Dynamic,name:String):Bool {
  var animations:Array<String>=cast Reflect.field(actor,"animations");
  return animations.indexOf(name)>=0;
 }
 static function play(actor:Dynamic,name:String,force:Null<Bool>,context:Dynamic,
   output:Array<Dynamic>):Void output.push({actor:Reflect.field(actor,"name"),name:name,force:force,context:context});
 static function apply(event:Dynamic,output:Array<Dynamic>):Bool
  return CodenameEventDispatch.applyPlayAnimation(event,charactersAt,hasAnimation,
   function(actor:Dynamic,name:String,force:Null<Bool>,context:Dynamic):Void
    play(actor,name,force,context,output));
 static function main():Void {
  var played:Array<Dynamic>=[];
  var authored:Dynamic={name:"Play Animation",time:87867.5921451479,
   params:([0,"idle",false,"NONE"]:Array<Dynamic>)};
  CodenameEventDispatch.run(authored,function(name:String,event:CodenameGameEvent) {
   if(name=="onEvent") {
    event.event.params[1]="grab";
    event.event.params[2]=true;
    event.event.params[3]="LOCK";
   }
  },function(event:Dynamic) {
   check(apply(event,played),"Play Animation was not handled");
  });
  check(played.length==2,"did not visit every actor with the animation");
  check(played[0].actor=="grab-only" && played[1].actor=="grab-and-idle",
   "line order or hasAnim filtering changed");
  for (entry in played)
   check(entry.name=="grab" && entry.force==true && entry.context=="LOCK",
    "post-callback force/context was not preserved");

  played.resize(0);
  check(apply({name:"Play Animation",time:0,
   params:([0,"idle",false,"NONE"]:Array<Dynamic>)},played),"NONE event not handled");
  check(played.length==2 && played[0].actor=="grab-and-idle" && played[1].actor=="idle-only",
   "NONE animation did not visit matching actors");
  for (entry in played)
   check(entry.force==false && entry.context==null,"NONE/false semantics changed");

  played.resize(0);
  check(apply({name:"Play Animation",time:0,
   params:([99,"grab",true,"LOCK"]:Array<Dynamic>)},played) && played.length==0,
   "missing strumline was not a handled no-op");
  check(!apply({name:"Camera Zoom",time:0,params:[]},played),
   "unrelated event was claimed");

  var cancelled:Dynamic={name:"Play Animation",time:0,
   params:([0,"grab",true,"LOCK"]:Array<Dynamic>)};
  CodenameEventDispatch.run(cancelled,function(name:String,event:CodenameGameEvent) {
   if(name=="onEvent") event.preventDefault();
  },function(event:Dynamic) apply(event,played));
  check(played.length==0,"cancelled event ran its default action");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            p = Path(work)
            (p / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'),
                 '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', str(p),
                 '--run', 'Main'], cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actual_playstate_owner_gate_and_scope_changes(self):
        source=(ROOT/'source/PlayState.hx').read_text()
        self.assertIn("interp.variables.set('executeEvent', function(event:Dynamic):Void executeCodenameEvent(event));", source)
        def method(name):
            start=source.index('\tfunction '+name+'(')
            brace=source.index('{',start); depth=0
            for index in range(brace,len(source)):
                depth+=(source[index]=='{')-(source[index]=='}')
                if depth==0:return source[start:index+1]
            raise AssertionError(name)
        helpers='\n'.join(method(name) for name in ('callCodenameEvent','executeCodenameEvent','fireSongEvent'))
        fixture=r'''class Main {
 var nightmareVisionScripts:Dynamic=null;
 var codenameScriptScopes:Array<Dynamic>=[];
 var codenameCharacterScopes:Array<Dynamic>=[];
 var codenameEventDiagnostics:Map<String,Bool>=[];
 var selected=false;
 var log:Array<String>=[];
 var nativeEvents:Array<Dynamic>=[];
 public function new() {}
 // This Codename event fixture has no selected Nightmare Vision owner; keep
 // the foreign callback path inactive while exercising the real Codename gate.
 function callNightmareVision(_event:String, ?_args:Array<Dynamic>):Dynamic return null;
 function codenameSelectedRoot():String return selected ? "owner" : "";
 function markCodenameRuntimeVisuals(scope:Dynamic,callback:String,
  ?event:CodenameGameEvent):Void {}
 // Event dispatch tests isolate callback routing; actor line reconciliation is
 // covered by the dedicated actor-runtime tests.
 function reconcileCodenameScriptLineActors():Void {}
 function applyCodenameNativeEvent(e:Dynamic):Bool return false;
 function fireNativeSongEvent(e:Dynamic):Void {nativeEvents.push(e);log.push("native");}
 function callCodenameScript(scope:Dynamic,name:String,args:Array<Dynamic>):Bool {
  var i:hscript.Interp=scope.interp;
  if(i.variables.exists(name)) Reflect.callMethod(null,i.variables.get(name),args);
  return true;
 }
 function scope(code:String):Dynamic {
  var i=new hscript.Interp();i.variables.set("log",log);
  i.execute(new hscript.Parser().parseString(code));return {interp:i};
 }
''' + helpers + r'''
 function run():Void {
  // Input uses the same scene-then-character dispatch contract, including
  // the donor rule that character scopes still receive a cancelled event.
  var inputLine={ID:99,lineIndex:2};
  var input=new CodenameInputEvent([false],[false],[false],inputLine,2);
  codenameScriptScopes=[scope('function onInputUpdate(e) { log.push("input-scene"); e.pressed=[true]; e.justPressed=[true]; e.justReleased=null; e.preventDefault(); }'),
   scope('function onInputUpdate(e) { throw "stopped scene reached"; }')];
  codenameCharacterScopes=[{runtime:{event:function(name:String,e:CodenameGameEvent) {
   var typed:CodenameInputEvent=cast e;
   if(name!="onInputUpdate" || !typed.pressed[0] || !typed.justPressed[0]
    || typed.justReleased!=null || typed.strumLineID!=2 || typed.strumLine!=inputLine)
    throw "input payload lost across scopes";
   log.push("input-character");
  }}}];
  callCodenameEvent("onInputUpdate",input);
  if(!input.cancelled || log.join(",")!="input-scene,input-character")
   throw "input cancellation/dispatch order";
  log.resize(0);codenameCharacterScopes=[];
  var rows=CodenameImporter.convertEvents([
   {name:"Play Animation",time:100,params:([0,"idle",true,"NONE"]:Array<Dynamic>)}
  ],[],"synthetic","normal");
  var native:Dynamic=SongEvents.collect(rows,null)[0];
  var first=scope('function onEvent(e) { log.push("on"); e.event.params[1]="sing"; } function onPostEvent(e) { log.push("post"); }');
  codenameScriptScopes=[first];
  fireSongEvent(native);
  if(log.join(",")!="native" || nativeEvents[0].v1!="idle") throw "foreign owner dispatched Codename scripts";
  log.resize(0);nativeEvents.resize(0);selected=true;
  fireSongEvent(native);
  if(log.join(",")!="on,native,post" || nativeEvents.length!=1 || nativeEvents[0].v1!="sing") throw "structured integration";
  log.resize(0);nativeEvents.resize(0);
  executeCodenameEvent({name:"Play Animation",time:0,
   params:([0,"script",true,"NONE"]:Array<Dynamic>)});
  if(log.join(",")!="on,native,post" || nativeEvents.length!=1
   || nativeEvents[0].v1!="sing") throw "script-created event bypassed mutable dispatch";
  log.resize(0);nativeEvents.resize(0);
  codenameScriptScopes=[scope('function onEvent(e) { log.push("cancel");e.preventDefault(); } function onPostEvent(e) { throw "cancelled post"; }'),first];
  fireSongEvent(native);
  if(log.join(",")!="cancel" || nativeEvents.length!=0) throw "cancelled default ran";
  log.resize(0);
  var removed=scope('function onEvent(e) { throw "released scope called"; }');
  var fresh=scope('function onPostEvent(e) { log.push("fresh-post"); }');
  var swapper=scope('function onEvent(e) { swap(); }');
  swapper.interp.variables.set("swap",function(){codenameScriptScopes.remove(removed);codenameScriptScopes.push(fresh);});
  codenameScriptScopes=[swapper,removed];
  fireSongEvent(native);
  if(log.join(",")!="native,fresh-post") throw "stage scope snapshot lifetime";
  nativeEvents.resize(0);log.resize(0);
  fireSongEvent({name:"Legacy",time:0,v1:"a",v2:"",v3:""});
  if(log.join(",")!="native" || nativeEvents[0].name!="Legacy") throw "legacy dispatch changed";
 }
 static function main():Void new Main().run();
}'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as work:
            p=Path(work);(p/'Main.hx').write_text(fixture, newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(p),'--run','Main'],cwd=ROOT,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_payload_mutation_cancellation_and_replay(self):
        fixture = r'''class Main {
 static var log:Array<String>=[];
 static var scripts:Array<hscript.Interp>=[];
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function script(source:String):hscript.Interp {
  var i=new hscript.Interp(); i.variables.set("log",log);
  i.execute(new hscript.Parser().parseString(source)); return i;
 }
 static function notify(name:String,e:CodenameGameEvent):Void {
  for(i in scripts) {
   if(i.variables.exists(name)) Reflect.callMethod(null,i.variables.get(name),[e]);
   if(e.stopsPropagation()) break;
  }
 }
 static function event():Dynamic return {name:"Play Animation",time:12.5,
  params:([0,"idle",false,"DANCE"]:Array<Dynamic>),global:false};
 static function main():Void {
  scripts=[script('function onEvent(e) { log.push("first"); e.event.params[1]="sing"; e.data.token=42; } function onPostEvent(e) { if(e.data.token != 42) throw "lost data"; log.push("post-first"); }'),
   script('function onEvent(e) { if(e.event.params[2] != false || e.data.token != 42) throw "lost payload"; log.push("second"); } function onPostEvent(e) { log.push("post-second"); }')];
  var count=0;
  CodenameEventDispatch.run(event(),notify,function(e) {
   count++; var route=CodenameEventDispatch.nativeRoute(e);
   check(route.name=="Play Animation" && route.v1=="sing" && route.time==12.5,"mutation did not route");
   log.push("native");
  });
  check(count==1 && log.join(",")=="first,second,native,post-first,post-second","callback order");
  for(expression in ["preventDefault()","cancel()","preventDefault(true)","cancel(false)"]) {
   log.resize(0); count=0;
   scripts=[script('function onEvent(e) { log.push("first"); e.'+expression+'; } function onPostEvent(e) { log.push("post"); }'),
    script('function onEvent(e) { log.push("second"); }')];
   CodenameEventDispatch.run(event(),notify,function(_) count++);
   var continues=expression=="cancel()" || expression=="preventDefault(true)";
   check(count==0 && log.join(",")==(continues?"first,second":"first"),"cancellation "+expression);
  }
  log.resize(0); count=0;
  scripts=[script('function onEvent(e) { e.event={name:"Camera Position", time:99.125, params:[12,34,false,0,"linear","In"]}; e.data.ok=true; } function onPostEvent(e) { if(e.event.time!=99.125 || !e.data.ok) throw "replacement wrapper lost"; log.push("post"); }')];
  CodenameEventDispatch.run(event(),notify,function(e) {
   count++; var route=CodenameEventDispatch.nativeRoute(e);
   check(route.name=="Focus Camera" && route.v1=="12" && route.time==99.125,"replacement did not reroute");
  });
  check(count==1 && log.join(",")=="post","replacement default/post count");
  check(CodenameEventDispatch.nativeRoute({name:"Set GF Speed",time:0,params:[9]})==null,
   "custom name leaked into unrelated native API");
  check(CodenameEventDispatch.nativeRoute({name:"Change Character",time:0,params:([0,"bf"]:Array<Dynamic>)})==null
   && CodenameEventDispatch.nativeRoute({name:"Change Scroll Speed",time:0,params:[2,4]})==null
   && CodenameEventDispatch.nativeRoute({name:"camera zoom",time:0,params:[true]})==null,
   "custom or case-mismatched event borrowed a legacy converter route");
  scripts=[script('function onEvent(e) { e.event=null; }')];
  var rejected=false;
  try CodenameEventDispatch.run(event(),notify,function(_) count++) catch(_:Dynamic) rejected=true;
  check(rejected && count==1,"invalid replacement executed native action");

  var rows=CodenameImporter.convertEvents([event()],[],"synthetic","normal");
  var native:Dynamic=SongEvents.collect(rows,null)[0];
  var authored:Dynamic=CodenameEventDispatch.fromNative(native);
  check(authored!=null && authored.params[2]==false,"native metadata not adapted");
  authored.params[1]="in-place";
  check(CodenameEventDispatch.fromNative(native)==authored
   && CodenameEventDispatch.fromNative(native).params[1]=="in-place","runtime event identity lost on replay");
  check(native.codename.params[1]=="idle","runtime edits mutated serialized provenance");
  scripts=[script('function onEvent(e) { e.event={name:"New",time:0,params:[]}; }')];
  CodenameEventDispatch.run(authored,notify,function(_) {});
  check(CodenameEventDispatch.fromNative(native)==authored && authored.name=="Play Animation",
   "replacing one wrapper replaced source event on replay");
  native.v1="edited";
  check(CodenameEventDispatch.fromNative(native)==null,"stale provenance enabled structured dispatch");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as work:
            p=Path(work); (p/'Main.hx').write_text(fixture, newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-cp',str(p),'--run','Main'],cwd=ROOT,text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__ == '__main__':
    unittest.main()
