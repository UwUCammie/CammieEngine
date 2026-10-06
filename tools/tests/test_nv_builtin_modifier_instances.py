"""Actual imported builtin constructors, no-ops, latches and virtual dispatch."""
from pathlib import Path
import unittest
import test_nv_custom_modifier_registration as modifier_support

class BuiltinModifierTest(unittest.TestCase):
    run_haxe = modifier_support.CustomModifierTest.run_haxe

    def test_real_iris_imports_constructors_class_identity_and_submodifier_noops(self):
        classes=['Reverse','Confusion','Perspective','Opponent','Flip','Invert','Drunk','Beat','Alpha','ReceptorScroll','Scale','Transform','InfinitePath','Path','Accel','X','Rotate','LocalRotate']
        program=''.join('import funkin.game.modchart.modifiers.'+name+'Modifier; record(new '+name+'Modifier(manager));' for name in classes)
        self.run_haxe(r'''
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import NightmareVisionModifier.ModifierType;
class Main {
 static function ok(v:Bool,m:String):Void if(!v)throw m;
 static function main() {
  var m=new NightmareVisionModManager(null,3,2,false);m.chartKeys=()->3;
  m.renderContext=()->new NightmareVisionModchartContext(1280,720,3,112);
  m.sourceRenderer=new NightmareVisionModchartRenderer(new NightmareVisionModchartTransform(m.registry));
  m.receptors=[[{}, {}, {}],[{}, {}, {}, {}, {}]];
  var i=new NightmareVisionScriptInterp();NightmareVisionModifierBindings.install(i);
  var made:Array<NightmareVisionModifier>=[];i.variables.set('manager',m);i.variables.set('record',(obj:NightmareVisionModifier)->made.push(obj));
  i.execute(new NightmareVisionScriptParser().parseString('__PROGRAM__'));
  ok(made.length==18&&!m.register.keys().hasNext(),'constructors must not register');
  ok(Std.isOfType(made[0],NightmareVisionReverseModifier)&&Std.isOfType(made[8],NightmareVisionAlphaModifier)&&Std.isOfType(made[12],NightmareVisionPathModifier),'real class identities');
  ok(made[0].getName()=='reverse'&&made[0].getOrder()==-2&&made[2].getOrder()==1100&&made[10].getOrder()==-3,'metadata');
  var pos=new NightmareVisionModchartVector(11,22,33);var unchanged:Dynamic={active:false,x:77,y:88,angle:99,alpha:0.3};
  for(mod in made) {
   for(sub in mod.submods) {
    ok(Std.isOfType(sub,NightmareVisionSubModifier)&&sub.parent==mod&&sub.getModType()==MISC_MOD&&sub.getOrder()==1000&&!sub.doesUpdate(),'real ordinary child');
    ok(sub.getPos(1,2,3,4,pos,0,0,unchanged)==pos,'child identity');
    sub.updateNote(1,unchanged,pos,0);sub.updateReceptor(1,unchanged,pos,0);sub.updateNoteSplash(1,unchanged,pos,0);sub.updateSustainSplash(1,unchanged,pos,0);
   }
  }
  ok(unchanged.x==77&&unchanged.y==88&&unchanged.angle==99&&unchanged.alpha==0.3,'child no-op callbacks');
  for(index in [1,8,10,15])ok(made[index].getPos(1,2,3,4,pos,0,0,unchanged)==pos&&pos.x==11,'root inherited position identity');
  for(index in [0,3,4,5,6,7,11,12,13,14,16,17]) {
   made[index].updateNote(1,unchanged,pos,0);made[index].updateReceptor(1,unchanged,pos,0);made[index].updateNoteSplash(1,unchanged,pos,0);made[index].updateSustainSplash(1,unchanged,pos,0);
  }
  made[1].updateNoteSplash(1,unchanged,pos,0);made[1].updateSustainSplash(1,unchanged,pos,0);
  ok(unchanged.x==77&&unchanged.angle==99,'root non-overridden callbacks no-op');
  m.registerEssentialModifiers();m.registerDefaultModifiers();
  ok(Std.isOfType(m.get('reverse'),NightmareVisionReverseModifier)&&Std.isOfType(m.get('mini'),NightmareVisionScaleModifier),'registration same real classes');
  var spawn=m.get('noteSpawnTime');ok(Std.isOfType(spawn,NightmareVisionSubModifier)&&spawn.parent==null&&spawn.getOrder()==1000&&!spawn.doesUpdate(),'standalone noteSpawnTime');
  ok(spawn.getPos(0,0,0,0,pos,0,0,unchanged)==pos,'spawn source noop');m.destroy();i.release();
 }
}
'''.replace('__PROGRAM__',program))

    def test_constructor_latches_mutable_helpers_prefix_path_and_inactive_direct_calls(self):
        self.run_haxe(r'''
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartTransform;
class Main {
 static function ok(v:Bool,m:String):Void if(!v)throw m;
 static function main() {
  var m=new NightmareVisionModManager(null,3,2,false);m.chartKeys=()->3;
  var ctx=new NightmareVisionModchartContext(1280,720,3,112,200,1,1,500,false,false);
  m.renderContext=()->ctx;m.sourceRenderer=new NightmareVisionModchartRenderer(new NightmareVisionModchartTransform(m.registry));
  m.receptors=[[{}, {}, {}],[{}, {}, {}, {}, {}]];
  var reverse=new NightmareVisionReverseModifier(m);reverse.setSubmodValue('split',1,1);
  ok(reverse.getReverseValue(2,1)==0&&reverse.getReverseValue(3,1)==1,'actual bank length instead of chart keys');
  reverse.setValue(1,0);var p=new NightmareVisionModchartVector(17,29,0);var fake:Dynamic={active:false,x:91,y:92,angle:93};
  ok(reverse.getPos(0,40,50,1,p,0,0,fake)==p&&p.x==17&&p.y==574,'inactive unregistered direct formula');
  ok(fake.x==91&&fake.y==92&&fake.angle==93,'direct position no object initialization');
  var scroll=new NightmareVisionReceptorScrollModifier(m);var perspective=new NightmareVisionPerspectiveModifier(m);
  var low=new NightmareVisionInfinitePathModifier(m,'curve');
  ok(scroll.formulaState.moveSpeed==1500&&perspective.formulaState.halfOffset.x==640&&low.formulaState.pathData[0].length==120,'construction state');
  ctx=new NightmareVisionModchartContext(1920,1080,3,112,600,3,1,250,false,true);
  var high=new NightmareVisionInfinitePathModifier(m,'other');
  ok(scroll.formulaState.moveSpeed==1500&&perspective.formulaState.halfOffset.x==640&&high.formulaState.pathData[0].length==24,'latched source state vs live construction');
  var origin=new NightmareVisionModchartVector(8,9,10);var rotate=new NightmareVisionRotateModifier(m,'test',origin);
  ok(rotate.getName()=='testrotateX'&&rotate.submods.exists('testrotate2Z')&&rotate.daOrigin==origin,'prefix/origin source shape');
  rotate.daOrigin=new NightmareVisionModchartVector(1,2,3);ok(rotate.leafEntry().state.origin==rotate.daOrigin,'mutable origin cache');
  var local=new NightmareVisionLocalRotateModifier(m,'near');ok(local.getName()=='nearrotateX'&&local.submods.exists('nearrotate1Y')&&local.getOrder()==-1,'local prefix constructor');
  var path=new NightmareVisionPathModifier(m,'custom');var a=new NightmareVisionModchartVector(0,0,0);var b=new NightmareVisionModchartVector(100,0,0);
  path.tracePath([[a,b]]);ok(path.formulaState.pathData[0][0].position==a&&path.formulaState.totalDists[0]==100,'path retains points/distances');
  path.setValue(1,0);var at=new NightmareVisionModchartVector();var out=path.getPos(0,0,2500,0,at,0,0,fake);
  ok(out.x==50&&out!=at,'mutable custom path interpolation replacement');path.tracePath([]);ok(path.getPos(0,0,2500,0,at,0,0,fake)==at,'clear path identity');
  var alpha=new NightmareVisionAlphaModifier(m);NightmareVisionAlphaModifier.fadeDistY=200;
  ok(alpha.getHiddenEnd(0)==340&&alpha.getSuddenEnd(0)==740,'public alpha helpers live source static');NightmareVisionAlphaModifier.fadeDistY=120;
  var marker:Dynamic={isSustainNote:false,noteData:0,lane:0,strumTime:100,multSpeed:1,wasGoodHit:true,alphaMod:1.0,garbage:false,active:false,x:12,y:13};
  scroll.setValue(1,0);scroll.updateNote(1,marker,new NightmareVisionModchartVector(),0);
  ok(marker.garbage&&marker.x==12&&marker.y==13,'source garbage direct mutation without spatial/disposal work');
  m.destroy();
 }
}
''')

    def test_ordered_pipeline_honors_actual_compiled_subclass_methods(self):
        self.run_haxe(r'''
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartVector;
import nightmarevision.modchart.NightmareVisionModchartRenderer;
import nightmarevision.modchart.NightmareVisionModchartTransform;
class CustomReverse extends NightmareVisionReverseModifier {
 public var calls:Int=0;public var updates:Int=0;
 public override function getName():String return 'virtualReverse';
 public override function getPos(time:Float,diff:Float,tDiff:Float,beat:Float,pos:NightmareVisionModchartVector,data:Int,player:Int,obj:Dynamic):NightmareVisionModchartVector {calls++;pos.x+=123;return pos;}
 public override function updateReceptor(beat:Float,obj:Dynamic,pos:NightmareVisionModchartVector,player:Int):Void {updates++;obj.angle=321;}
}
class Main {
 static function main() {
  var m=new NightmareVisionModManager(null,4,2,false);m.renderContext=()->new NightmareVisionModchartContext(1280,720,4,112);
  m.sourceRenderer=new NightmareVisionModchartRenderer(new NightmareVisionModchartTransform(m.registry));
  var custom=new CustomReverse(m);m.quickRegister(custom);
  var obj:Dynamic={active:true,ID:0,width:40.0,height:40.0,scale:{x:1.0,y:1.0},x:0.0,y:0.0,angle:0.0,alpha:1.0};
  var p=m.getPos(1,0,0,0,0,0,obj);if(custom.calls!=1||p.x!=m.getBaseX(0,0)+123)throw 'virtual position bypassed';
  m.updateObject(0,obj,p,0);if(custom.updates!=1||obj.angle!=321)throw 'virtual object bypassed';
  m.destroy();
 }
}
''')

    def test_actual_sprite_baseline_aliases_and_effect_rgb_draw(self):
        from test_nv_multifield_routes import method
        fixtures = []
        for file, name in [('Strumline.hx','ReceptorProbe'),('NoteSplash.hx','SplashProbe'),('NoteHoldCover.hx','CoverProbe')]:
            source=(Path(__file__).resolve().parents[2]/'source'/file).read_text(encoding='utf-8')
            start=source.index('class StrumNote') if file=='Strumline.hx' else 0
            source=source[start:]
            methods='\n'.join(method(source, marker) for marker in ['function get_baseScale(', 'function set_defScale(', 'function get_defScale(', 'override public function draw('])
            rgb=''
            if file!='Strumline.hx':
                rgb='public var rgbGraphics(get,never):NightmareVisionRGBGraphics;'+method(source,'function get_rgbGraphics(')
            fixtures.append('class '+name+' extends DisplayBase { public var nightmareVisionRGB:NightmareVisionRGBGraphics; var nightmareVisionBaseScalePoint:FlxPoint; public var baseScale(get,never):FlxPoint; public var defScale(get,set):FlxPoint; public function new(){super();}'+rgb+methods.replace('FlxPoint.get(', 'new FlxPoint(')+'}')
        self.run_haxe(r'''import flixel.math.FlxPoint;
class NightmareVisionRGBGraphics { public var enabled:Bool=true; public var alpha:Float=1; public var flash:Float=0; public function new(){} public function apply(o:DisplayBase):Void o.shader={alpha:alpha,flash:flash,enabled:enabled}; }
class DisplayBase { public var scale:FlxPoint=new FlxPoint(0.7,0.8); public var shader:Dynamic; public var draws:Int=0; public function new(){} public function draw():Void draws++; }
class Main { static function ok(v:Bool,m:String):Void if(!v)throw m; static function main(){
 for(o in [new ReceptorProbe(),new SplashProbe(),new CoverProbe()]) {
  var base:FlxPoint=Reflect.getProperty(o,'baseScale');ok(base.x==0.7&&base.y==0.8,'post-construction baseline');o.scale.set(2,3);ok(Reflect.getProperty(o,'baseScale')==base&&base.x==0.7,'scale mutation cannot recapture baseline');
  Reflect.setProperty(o,'defScale',new FlxPoint(0.9,1.1));ok(Reflect.getProperty(o,'baseScale')==base&&base.x==0.9&&base.y==1.1,'aliases retain baseline identity');
  var g=new NightmareVisionRGBGraphics();g.alpha=0.23;g.flash=0.4;Reflect.setField(o,'nightmareVisionRGB',g);o.draw();ok(o.draws==1&&o.shader.alpha==0.23&&o.shader.flash==0.4,'real RGB mutation reaches shader draw');
 }
 var splash=new SplashProbe();ok(!splash.rgbGraphics.enabled,'lazy facade preserves uncolored authored texture');ok(splash.rgbGraphics==splash.nightmareVisionRGB,'actual component identity');
 var cover=new CoverProbe();ok(!cover.rgbGraphics.enabled,'generic cover coloring is opt-in');
 }}
'''+ '\n'.join(fixtures))
