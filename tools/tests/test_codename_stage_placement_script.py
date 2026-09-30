"""Run importer-generated placement HScript against live actor/slot boundaries."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameStagePlacementScriptTest(unittest.TestCase):
    def test_named_position_defaults_and_absent_position_survive_conversion(self):
        fixture = r'''import hscript.Parser;
import hscript.Interp;
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function actor(name:String):Dynamic return {kind:"actor",name:name,x:0.0,y:0.0,scrollFactor:new Point()};
 static function run(xml:String,lines:Array<Dynamic>,?offsets:Map<String,Array<Float>>,
  ?playerOffsets:Map<String,Bool>):Dynamic {
  var converted=CodenameImporter.parseStageXml(xml,Sys.args()[0],"fixture",offsets,null,lines,playerOffsets);
  var interp=new Interp();
  var dad=actor("dad");var bf=actor("bf");var gf=actor("gf");var slots:Map<String,Dynamic>=[];
  interp.variables.set("dad",dad);interp.variables.set("boyfriend",bf);interp.variables.set("gf",gf);
  interp.variables.set("FlxSprite",FlxSprite);
  interp.variables.set("hscriptPath","/generated/");
  interp.variables.set("setDefaultZoom",function(_:Float){});
  var stage=new StageHarness();
  stage.setOffsets=function(key:String,x:Float,y:Float,add:Bool){slots.set(key,{x:x,y:y});};
  stage.setScrollFactor=function(key:String,x:Float,y:Float){};
  interp.variables.set("stage",stage);
  interp.execute(new Parser().parseString(converted.hscript));
  interp.variables.get("start")("fixture");
  check(stage.placement != null && stage.placement.slots.exists("dad")
   && stage.placement.slots.exists("boyfriend"),"whole stage placement was not published");
  check(converted.hscript.indexOf("stage.setCodenamePlacement(")
   < converted.hscript.indexOf("stage.addCodenameAnchor("),"placement must publish before stage nodes");
  return {dad:dad,bf:bf,gf:gf,slots:slots,stage:stage};
 }
 static function main():Void {
  var lines=CodenameImporter.cameraStrumlines({strumLines:[
   {type:0,position:"shared",characters:["named"]},
   {type:1,position:"shared",characters:["hero"]},
   {type:2,characters:["companion"]}
  ]});
  check(lines[2].position==null,"absent position was converted to an explicit empty slot");
  var value=run('<stage><opponent x="10"/><player x="20"/><char name="shared" x="40" y="50" scroll=".7"/>'
   + '<character name="named" x="60" y="70" scrollx=".4"/></stage>',lines);
  check(value.dad.x==60 && value.dad.y==70,"named actor placeholder must beat chart position");
  check(value.bf.x==40 && value.bf.y==50,"player must use authored shared position");
  check(value.dad.scrollFactor.x==.4 && value.bf.scrollFactor.x==.7,"live scroll factors");
  check(value.gf.x==400 && value.gf.y==130 && value.gf.scrollFactor.x==.95,"omitted role placeholder defaults");
  var emptyFirst=CodenameImporter.cameraStrumlines({strumLines:[
   {type:0,position:"absent",characters:[]},
   {type:0,position:"shared",characters:["named"]}
  ]});
  var afterEmpty=run('<stage><char name="shared" x="60" y="70"/></stage>',emptyFirst);
  check(afterEmpty.dad.x==60 && afterEmpty.dad.y==70,
   "empty earlier role line must not hide the first authored actor occurrence");
  var defaults=run('<stage/>',null);
  check(defaults.bf.x==770 && defaults.bf.y==100,"Codename BF default must not use native y=450");
  check(defaults.slots.get("bf").y==100,"stored placement must agree with opening actor");
  var explicit=CodenameImporter.cameraStrumlines({strumLines:[{type:1,position:"",characters:["hero"]}]});
  check(explicit[0].position=="","explicit empty position was lost");
  var empty=run('<stage/>',explicit);
  check(empty.bf.x==0 && empty.bf.y==0,"unknown explicit position must not invent a role slot");
  var offsets:Map<String,Array<Float>>=["bf"=>[20.0,-10.0]];
  var playerOffsets:Map<String,Bool>=["bf"=>true];
  var aligned=run('<stage/>',null,offsets,playerOffsets);
  check(aligned.bf.x==790 && aligned.bf.y==90,"matching player offsets");
  var opposite=run('<stage><player flip="false"/></stage>',null,offsets,playerOffsets);
  check(opposite.bf.x==750 && opposite.bf.y==90,"slot flip must reverse global X only");
  var unspecified=run('<stage/>',null,offsets);
  check(unspecified.bf.x==750 && unspecified.bf.y==90,"absent XML playerOffsets defaults false");
  var emptyName=run('<stage><char name="" x="42"/></stage>',null);
  check(emptyName.bf.x==770 && emptyName.dad.x==100 && emptyName.gf.x==400,
   "empty named slot must not capture fallback roles without an explicit position");
  var explicitEmpty=CodenameImporter.cameraStrumlines({strumLines:[
   {type:1,position:"",characters:["hero"]}
  ]});
  var selectedEmpty=run('<stage><char name="" x="42"/></stage>',explicitEmpty);
  check(selectedEmpty.bf.x==42,"explicit empty position must select empty named slot");
  var supported=CodenameImporter.parseStageXml(
   '<stage><dad scale="1.25" alpha=".5" angle="10" skewx="3"/></stage>',
   Sys.args()[0],"supported");
  check([for(d in supported.diagnostics) if(d.code=="unsupported-stage-character-presentation") d].length==0,
   "supported presentation was still diagnosed as unavailable");
  var zoom=CodenameImporter.parseStageXml('<stage><dad zoomfactor="1.2"/></stage>',
   Sys.args()[0],"zoom");
  var zoomWarnings=[for(d in zoom.diagnostics) if(d.code=="unsupported-stage-character-presentation") d];
  check(zoomWarnings.length==1 && zoomWarnings[0].message.indexOf("zoomFactor")>=0,
   "unsupported per-character zoomFactor must remain diagnosed");
 }
}
class FlxSprite {
 public var x:Float;public var y:Float;public var tag:String="";public var alpha:Float=1;
 public var angle:Float=0;public var visible:Bool=true;public var antialiasing:Bool=true;
 public var flipX:Bool=false;public var flipY:Bool=false;public var scale:Point=new Point();
 public var scrollFactor:Point=new Point();
 public function new(?x:Float=0,?y:Float=0){this.x=x;this.y=y;}
 public function loadGraphic(path:String):FlxSprite {tag=path;return this;}
 public function updateHitbox():Void {}
}
class Point {
 public var x=1.0;public var y=1.0;
 public function new(){}
 public function set(x:Float,y:Float):Void {this.x=x;this.y=y;}
}
class StageHarness {
 public var members:Array<Dynamic>=[];public var elements:Map<String,Dynamic>=[];
 public var placement:Dynamic=null;
 public dynamic function setOffsets(key:String,x:Float,y:Float,add:Bool):Void {}
 public dynamic function setScrollFactor(key:String,x:Float,y:Float):Void {}
 public function new(){}
 public function setCodenamePlacement(data:Dynamic):Void {
  placement=CodenameStagePlacement.fromData(haxe.Json.parse(data));
 }
 public function addCodenameAnchor(key:String,ordinal:Int):Dynamic {
  var anchor={kind:"anchor",key:key,ordinal:ordinal};members.push(anchor);return anchor;
 }
 public function addCodenameProp(sprite:Dynamic,ordinal:Int):Void members.push(sprite);
 public function addElement(name:String,element:Dynamic):Void elements.set(name,element);
 public function placeCodenameActor(actor:Dynamic,key:String):Void {
  members.remove(actor);var last=-1;
  for(i in 0...members.length)
   if(Reflect.field(members[i],"kind")=="anchor" && Reflect.field(members[i],"key")==key) last=i;
  if(last<0)members.push(actor);else members.insert(last,actor);
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            assets = path / "images"
            assets.mkdir(parents=True)
            for name in ("back", "mid", "front"):
                (assets / f"{name}.png").write_bytes(b"fixture")
            (path / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", str(path), "--run", "Main",
                 str(path)],
                cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_stage_script_preserves_xml_interleaving_and_primary_order(self):
        fixture = r'''import hscript.Parser;
import hscript.Interp;
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function actor(name:String):Dynamic return {kind:"actor",name:name,x:0.0,y:0.0,scrollFactor:new Point()};
 static function label(value:Dynamic):String {
  if(Reflect.field(value,"kind")=="anchor")return "anchor:"+Reflect.field(value,"key")+":"+Reflect.field(value,"ordinal");
  if(Reflect.field(value,"kind")=="actor")return "actor:"+Reflect.field(value,"name");
  var tag=Std.string(Reflect.field(value,"tag"));
  var slash=tag.lastIndexOf("/");return "prop:"+tag.substr(sash(slash));
 }
 static function sash(value:Int):Int return value<0?0:value+1;
 static function main():Void {
  var xml='<stage><sprite name="back" sprite="back"/><dad/>'
   + '<sprite name="missing" sprite="missing"/><sprite name="mid" sprite="mid"/>'
   + '<character name="same"/><char name="same"/><sprite name="front" sprite="front"/></stage>';
  var lines=CodenameImporter.cameraStrumlines({strumLines:[
   {type:1,characters:["hero"]},{type:0,characters:["same"]},{type:2,characters:["companion"]}
  ]});
  var converted=CodenameImporter.parseStageXml(xml,Sys.args()[0],"fixture",null,null,lines);
  var interp=new Interp();var dad=actor("dad");var bf=actor("bf");var gf=actor("gf");
  var stage=new StageHarness();
  interp.variables.set("dad",dad);interp.variables.set("boyfriend",bf);interp.variables.set("gf",gf);
  interp.variables.set("FlxSprite",FlxSprite);interp.variables.set("hscriptPath","/generated/");
  interp.variables.set("setDefaultZoom",function(_:Float){});interp.variables.set("stage",stage);
  interp.execute(new Parser().parseString(converted.hscript));interp.variables.get("start")("fixture");
  var actual=[for(member in stage.members)label(member)].join("|");
  var expected="prop:prop-0.png|anchor:dad:1|prop:prop-2.png|anchor:same:4|actor:dad|anchor:same:5|prop:prop-3.png|actor:gf|anchor:girlfriend:7|actor:bf|anchor:boyfriend:8";
  check(actual==expected,"ordered stage members: "+actual);
  check(stage.elements.get("front")!=null,"named addElement binding lost");
  check(converted.assets.length==3,"missing asset should leave an ordinal gap: "+converted.assets.length);
  var codes=[for(d in converted.diagnostics)d.code];
  check(codes.indexOf("missing-prop-asset")>=0,"missing prop diagnostic");
  check(converted.hscript.indexOf("stage.addCodenameProp(codenameProp_mid_2, 3);")>=0,
   "XML ordinal must be independent from prop asset index");
  check(converted.hscript.indexOf("stage.placeCodenameActor(boyfriend, \"boyfriend\");")
    < converted.hscript.indexOf("stage.placeCodenameActor(dad, \"same\");")
    && converted.hscript.indexOf("stage.placeCodenameActor(dad, \"same\");")
    < converted.hscript.indexOf("stage.placeCodenameActor(gf, \"girlfriend\");"),
   "primary role placement must follow authored line order");
 }
}
class FlxSprite {
 public var x:Float;public var y:Float;public var tag:String="";public var alpha:Float=1;
 public var angle:Float=0;public var visible:Bool=true;public var antialiasing:Bool=true;
 public var flipX:Bool=false;public var flipY:Bool=false;public var scale:Point=new Point();
 public var scrollFactor:Point=new Point();
 public function new(?x:Float=0,?y:Float=0){this.x=x;this.y=y;}
 public function loadGraphic(path:String):FlxSprite {tag=path;return this;}
 public function updateHitbox():Void {}
}
class Point {
 public var x=1.0;public var y=1.0;public function new(){}
 public function set(x:Float,y:Float):Void{this.x=x;this.y=y;}
}
class StageHarness {
 public var members:Array<Dynamic>=[];public var elements:Map<String,Dynamic>=[];
 public var placement:Dynamic=null;
 public function new(){}
 public function setCodenamePlacement(data:Dynamic):Void {
  placement=CodenameStagePlacement.fromData(haxe.Json.parse(data));
 }
 public function setOffsets(key:String,x:Float,y:Float,add:Bool):Void{}
 public function setScrollFactor(key:String,x:Float,y:Float):Void{}
 public function addCodenameAnchor(key:String,ordinal:Int):Dynamic {
  var anchor={kind:"anchor",key:key,ordinal:ordinal};members.push(anchor);return anchor;
 }
 public function addCodenameProp(sprite:Dynamic,ordinal:Int):Void members.push(sprite);
 public function addElement(name:String,element:Dynamic):Void elements.set(name,element);
 public function placeCodenameActor(actor:Dynamic,key:String):Void {
  members.remove(actor);var last=-1;
  for(i in 0...members.length)if(Reflect.field(members[i],"kind")=="anchor"&&Reflect.field(members[i],"key")==key)last=i;
  if(last<0)members.push(actor);else members.insert(last,actor);
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            assets = path / "images"
            assets.mkdir(parents=True)
            for name in ("back", "mid", "front"):
                (assets / f"{name}.png").write_bytes(b"fixture")
            (path / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", str(ROOT / ".haxelib/hscript/2,5,0"), "-cp", str(path), "--run", "Main",
                 str(path)], cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
