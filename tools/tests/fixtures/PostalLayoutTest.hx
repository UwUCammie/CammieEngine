import sys.FileSystem;
class UISprite {
 public var x:Float=0;public var y:Float=0;public var width:Float=1280;public var height:Float=40;
 public var alpha:Float=1;public var zoom:Float=1;public var visible=true;public var flipX=false;public var antialiasing=false;
 public var cameras:Array<Dynamic>;public var color:Int;public var bgColor:Int;public var frames:Dynamic;
 public var text="";public var font="";public var fieldWidth:Float;public var alignment="";public var size=16;
 public var borderSize:Float=1;public var borderStyle:Dynamic;public var borderColor:Int;public var numDivisions:Int;
 public var scale={x:1.0,y:1.0,set:function(x:Float,y:Float){}};
 public var scrollFactor={set:function(?x:Float,?y:Float){}};
 public var animation={addByPrefix:function(n:String,p:String,?fps:Int,?loop:Bool){},play:function(n:String,?force:Bool){}};
 public function new(?x:Float,?y:Float,?w:Float,?h:Dynamic,?z:Dynamic){}
 public function loadGraphic(path:String){if(!FileSystem.exists(path))throw path;return this;}
 public function screenCenter(){}
 public function setGraphicSize(w:Int,?h:Int){}
}
// Eval does not expose IntIterator's inline methods through reflection.
class TestInterp extends hscript.Interp {
 override function makeIterator(value:Dynamic):Iterator<Dynamic> {
  if(Std.isOfType(value,IntIterator)) {
   var it:IntIterator=cast value;
   return {hasNext:function()return it.hasNext(),next:function():Dynamic return it.next()};
  }
  return super.makeIterator(value);
 }
}
class PostalLayoutTest {
 static function main(){
  var i=new TestInterp();var globals=new Map<String,Dynamic>();var state={health:1.0,iconOverride:false};
  var vars:Map<String,Dynamic>=[
   'FlxSprite'=>UISprite,'FlxText'=>UISprite,'FlxCamera'=>UISprite,
   'FlxAtlasFrames'=>{fromSparrow:function(p:String,x:String){if(!FileSystem.exists(p)||!FileSystem.exists(x))throw p;return {};}},
   'FlxG'=>{width:1280,height:720,cameras:{remove:function(c:Dynamic,d:Bool){},add:function(c:Dynamic){}},sound:{music:{time:0.0,length:1000.0}}},
   'PlayState'=>{SONG:{song:'postal'},misses:0,sicks:0,goods:0,bads:0,shits:0},'currentPlayState'=>state,
   'addSprite'=>function(s:Dynamic){},'removeSprite'=>function(s:Dynamic){},
   'disableScoreChange'=>function(b:Bool){},'setGlobalSprite'=>function(n:String,s:Dynamic){globals.set(n,s);},
   'NewBar'=>function(x:Float,y:Float,w:Int,h:Int,min:Float,max:Float,?color:Bool)return new UISprite(),
   'Std'=>Std,'Math'=>Math,'HelperFunctions'=>{truncateFloat:function(x:Float,n:Int)return x},
   'downscroll'=>false,'demoMode'=>false,'useSongBar'=>true,'curSong'=>'postal','songScore'=>0,'accuracy'=>0.0,
   'sicks'=>0,'goods'=>0,'bads'=>0,'shits'=>0
  ];
  for(n in ['healthBar','healthBarBG','camHUD','iconP1','iconP2','difficTxt','scoreTxt','songName','songPosBG','songPosBar'])vars.set(n,new UISprite());
  for(k=>v in vars)i.variables.set(k,v);
  i.execute(new hscript.Parser().parseString(sys.io.File.getContent('assets/images/custom_ui/ui_layouts/postal.hscript')));
  Reflect.callMethod(null,i.variables.get('start'),['postal']);
  Reflect.callMethod(null,i.variables.get('stepHit'),[1]);
  Reflect.callMethod(null,i.variables.get('update'),[0.016]);
  Reflect.callMethod(null,i.variables.get('beatHit'),[1]);
  if(!state.iconOverride||!globals.exists('timeBar'))throw 'Postal layout did not initialize';
 }
}
