class Animation {
 public var last:String='';
 public function new() {}
 public function addByPrefix(name:String,prefix:String,?fps:Int,?looped:Bool) {}
 public function play(name:String,?force:Bool) last=name;
 public function pause() {}
}
class Sprite {
 public var x:Float=0; public var y:Float=0; public var alpha:Float=1; public var visible=true; public var flipY=false;
 public var frames:Dynamic; public var antialiasing=false; public var animation=new Animation();
 public var scrollFactor={set:function(x:Float,y:Float){}};
 public function new(x:Float,y:Float,?unused:Bool) {this.x=x;this.y=y;}
 public function loadGraphic(p:String) {if(!sys.FileSystem.exists(p)) throw p;return this;}
 public function screenCenter() {}
 public function setPosition(x:Float,y:Float) {this.x=x;this.y=y;}
 public function getPosition() return {x:x,y:y};
}
class Timer {
 public static var queue:Array<Void->Void>=[];
 public function new() {}
 public function start(t:Float,cb:Dynamic->Void) {queue.push(function()cb(this));return this;}
}
class ChaosIntroTest {
 static function main() {
  var count=0;var sprites=0;var handoffs=0;
  var camera={focusOn:function(p:Dynamic){},zoom:0.7,flash:function(c:Int,t:Float){},fade:function(c:Int,t:Float,in_:Bool){},shake:function(a:Float,b:Float){}};
  var camFollow=new Sprite(0,0);var dad=new Sprite(0,0);var boyfriend=new Sprite(0,0);
  var state={defaultCamZoom:0.7,camFollow:camFollow,startCountdown:function(){count++;}};

  var stage=new hscript.Interp();
  var stageVars:Map<String,Dynamic>=[
   "FlxSprite"=>Sprite,"MetroSprite"=>Sprite,
   "FlxAtlasFrames"=>{fromSparrow:function(p:String,x:String){if(!sys.FileSystem.exists(p)||!sys.FileSystem.exists(x))throw p;return {}; }},
   "curSong"=>"chaos","hscriptPath"=>"assets/images/custom_stages/chamber/",
   "boyfriend"=>boyfriend,"dad"=>dad,"gf"=>new Sprite(0,0),"BEHIND_ALL"=>7,"BEHIND_NONE"=>0,
   "addSprite"=>function(s:Dynamic,p:Int){},"setDefaultZoom"=>function(z:Float){state.defaultCamZoom=z;}
  ];
  for(k=>v in stageVars)stage.variables.set(k,v);
  stage.execute(new hscript.Parser().parseString(sys.io.File.getContent('assets/images/custom_stages/chamber.hscript')));
  Reflect.callMethod(null,stage.variables.get('start'),['chaos']);
  for(name in ['floor','fleetwaybgshit','pebles','thechamber','emeraldbeam','emeraldbeamyellow'])
   if(!stage.variables.exists(name))throw 'Stage did not export '+name;

  var i=new hscript.Interp();
  var vars:Map<String,Dynamic>=[
  "FlxSprite"=>Sprite,"FlxTimer"=>Timer,"FlxG"=>{camera:camera},
   "FlxTween"=>{tween:function(a:Dynamic,b:Dynamic,t:Float,?o:Dynamic){}},
   "FlxEase"=>{circInOut:0,cubeOut:0},
   "ZoomCamera"=>function(info:Dynamic){camera.zoom=info.zoom == 1.5 ? state.defaultCamZoom * info.zoom : state.defaultCamZoom;},
   "FNFAssets"=>{getSound:function(p:String){if(!sys.FileSystem.exists(p))throw p;return p;}},
   "TitleState"=>{soundExt:".ogg"},"soundPlaySafe"=>function(s:Dynamic){},"preloadSound"=>function(s:Dynamic){return true;},
   "currentPlayState"=>state,"camHUD"=>{alpha:1.0},"gf"=>{alpha:1.0},"dad"=>dad,
   "hscriptPath"=>"assets/images/custom_cutscenes/fleetway/","BEHIND_NONE"=>0,
   "addSprite"=>function(s:Dynamic,p:Int){sprites++;},"removeSprite"=>function(s:Dynamic){sprites--;},
   "handoffCutsceneSprite"=>function(s:Dynamic,?release:Bool=false,?delay:Float=0){handoffs++;},
   "BEHIND_ALL"=>7
  ];
  for(k=>v in vars)i.variables.set(k,v);
  // Matches PlayState.inheritHscriptVariables: cutscene-owned names win,
  // while stage-created globals are shared by reference.
  for(k in stage.variables.keys())if(!i.variables.exists(k))i.variables.set(k,stage.variables.get(k));
  i.execute(new hscript.Parser().parseString(sys.io.File.getContent('assets/images/custom_cutscenes/fleetway.hscript')));
  Reflect.callMethod(null,i.variables.get('start'),['chaos']);
  while(Timer.queue.length>0)Timer.queue.shift()();

  var floor:Sprite=cast stage.variables.get('floor');var bg:Sprite=cast stage.variables.get('fleetwaybgshit');
  var pebles:Sprite=cast stage.variables.get('pebles');var chamber:Sprite=cast stage.variables.get('thechamber');
  var blueBeam:Sprite=cast stage.variables.get('emeraldbeam');var yellowBeam:Sprite=cast stage.variables.get('emeraldbeamyellow');
  if(count!=1||sprites!=2||handoffs!=2)throw 'Intro failed to finish cleanly';
  if(chamber.animation.last!='a')throw 'Sonic fall animation never played';
  if(floor.animation.last!='b'||bg.animation.last!='b'||pebles.animation.last!='b')throw 'Stage never changed to its charged state';
  if(blueBeam.visible||!yellowBeam.visible)throw 'Emerald beam never changed from blue to yellow';
  if(dad.visible)throw 'Fleetway should stay hidden until the song entrance';
  trace('Chaos stage globals drive the complete intro and countdown');
 }
}
