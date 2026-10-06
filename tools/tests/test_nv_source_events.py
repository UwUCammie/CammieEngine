"""Actual source event imports, captured values, registration and owner lifecycle."""
import unittest
import test_nv_custom_modifier_registration as support

class SourceEventsTest(unittest.TestCase):
    run_haxe = support.CustomModifierTest.run_haxe

    def test_actual_iris_imports_constructor_inheritance_mutable_fields_and_direct_callbacks(self):
        self.run_haxe(r'''class Main {
 static function ok(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  var m=new NightmareVisionModManager();var i=new NightmareVisionScriptInterp();NightmareVisionModifierBindings.install(i);i.variables.set('m',m);var result:Array<Dynamic>=[];i.variables.set('save',(o:Dynamic)->result.push(o));
  i.execute(new crowplexus.hscript.Parser().parseString("import funkin.game.modchart.EventTimeline; import funkin.game.modchart.events.BaseEvent; import funkin.game.modchart.events.ModEvent; import funkin.game.modchart.events.SetEvent; import funkin.game.modchart.events.EaseEvent; import funkin.game.modchart.events.CallbackEvent; import funkin.game.modchart.events.StepCallbackEvent; save(new EventTimeline()); save(new BaseEvent(1,m)); save(new ModEvent(2,'reverse',0.5,0,m)); save(new SetEvent(3,'reverse',0.6,0,m)); save(new EaseEvent(4,8,'reverse',1,t->t,0,m,0.2)); save(new CallbackEvent(5,(event,step)->save(event),m)); save(new StepCallbackEvent(6,7,(event,step)->save(step),m));"));
  ok(Std.isOfType(result[0],NightmareVisionEventTimeline),'timeline constructor identity');ok(Std.isOfType(result[2],NightmareVisionModEvent)&&Std.isOfType(result[2],NightmareVisionBaseEvent),'real ModEvent inheritance');ok(Std.isOfType(result[3],NightmareVisionModEvent)&&Std.isOfType(result[4],NightmareVisionModEvent),'value-event inheritance');ok(Std.isOfType(result[6],NightmareVisionCallbackEvent),'step inheritance');
  var b:NightmareVisionBaseEvent=cast result[1];b.run(100);ok(!b.finished&&b.executionStep==1&&b.manager==m,'BaseEvent noop');
  var e:NightmareVisionEaseEvent=cast result[4];e.run(6);ok(e.startVal==0.2&&Math.abs(m.getValue('reverse',0)-0.6)<0.00001&&!e.finished,'explicit direct start');
  var callback:NightmareVisionCallbackEvent=cast result[5];callback.run(50);ok(result[7]==callback&&callback.finished,'actual callback identity');
  var repeat:NightmareVisionStepCallbackEvent=cast result[6];repeat.run(7);ok(result[8]==7&&!repeat.finished,'inclusive endpoint');repeat.run(8);ok(repeat.finished&&result.length==9,'strict end retirement');
  for(c in [new NightmareVisionCallbackEvent(0,null,m),new NightmareVisionStepCallbackEvent(0,2,null,m)]) {var failed=false;try c.run(0)catch(_:Dynamic)failed=true;ok(failed&&!c.finished,'direct invalid callback throws unfinished');}
  i.release();m.destroy();
 }
}''')

    def test_captured_modifier_live_name_write_latched_length_and_queue_omission(self):
        self.run_haxe(r'''import NightmareVisionModifier.ModifierType;
class Custom extends NightmareVisionModifier {var n:String;var k:ModifierType;public function new(m,n,k){this.n=n;this.k=k;super(m);}override public function getName()return n;override public function getModType()return k;}
class Main {
 static function ok(v:Bool,m:String):Void if(!v)throw m;
 static function near(a:Float,b:Float,m:String):Void ok(Math.abs(a-b)<0.00001,m);
 static function main(){var m=new NightmareVisionModManager(null,4,2,false);var old=new Custom(m,'v',NOTE_MOD);m.quickRegister(old);old.setValue(0.4,0);var e=new NightmareVisionEaseEvent(2,6,'v',1,t->t,0,m);var replacement=new Custom(m,'v',MISC_MOD);m.quickRegister(replacement);e.run(4);near(e.startVal,0.4,'captured old start');near(replacement.getValue(0),0.7,'live replacement write');near(old.getValue(0),0.4,'old object unchanged');
  e.endStep=10;e.executionStep=0;e.easeFunc=t->t*t;e.run(2);ok(e.length==4,'duration latched independently');near(replacement.getValue(0),0.55,'mutated ease/currentstep but latched length');
  var other=new Custom(m,'target',NOTE_MOD);m.quickRegister(other);e.modName='target';e.endVal=0.8;e.run(11);ok(e.finished&&other.getValue(0)==0.8,'mutable name endpoint writes live');
  m.queueEase(15,17,'target',1,flixel.tweens.FlxEase.quadIn,0);var identity:NightmareVisionEaseEvent=cast m.timeline.modEvents.get('target')[0];ok(Reflect.compareMethods(identity.easeFunc,flixel.tweens.FlxEase.quadIn),'queue retains easing function identity');m.timeline.addMod('target');m.setValue('target',0.3,0);m.queueEase(20,24,'target',1,'linear',0,0.9);var q:NightmareVisionEaseEvent=cast m.timeline.modEvents.get('target')[0];ok(q.startVal==null,'queue omitted explicit start');m.updateTimeline(20);near(q.startVal,0.3,'queue captures live instance value');
  m.queueSetP(30,'target',75);m.updateTimeline(30);near(other.getValue(0),0.75,'percent/all player queue');near(other.getValue(1),0.75,'allplayer lane1');
  var ignored=new NightmareVisionEaseEvent(40,44,'target',1,t->t,0,m,0.2);ignored.ignoreExecution=true;m.timeline.addEvent(ignored);m.updateTimeline(42);ok(ignored.startVal==0.2&&!ignored.finished,'ignored explicit start');ignored.ignoreExecution=false;m.updateTimeline(43);near(other.getValue(0),0.8,'resume ease');m.updateTimeline(44);ok(!ignored.finished,'ease endpoint not retired');m.updateTimeline(45);ok(ignored.finished,'ease after endpoint retired');m.destroy();
 }
}''')

    def test_accepted_registration_reset_rejected_retention_replacement_and_teardown(self):
        self.run_haxe(r'''import NightmareVisionModifier.ModifierType;
class Custom extends NightmareVisionModifier {var n:String;var k:ModifierType;public function new(m,n,k){this.n=n;this.k=k;super(m);}override public function getName()return n;override public function getModType()return k;}
class Main {static function ok(v:Bool,m:String):Void if(!v)throw m;static function main(){
 var m=new NightmareVisionModManager(null,4,2,false);var original=m.timeline;var first=new Custom(m,'v',NOTE_MOD);m.quickRegister(first);m.queueSet(1,'v',1,0);var bucket=m.timeline.modEvents.get('v');m.quickRegister(new Custom(m,'v',NOTE_MOD));ok(m.timeline.modEvents.get('v')==bucket&&bucket.length==1,'rejected registration retains bucket');m.quickRegister(new Custom(m,'v',MISC_MOD));ok(m.timeline.modEvents.get('v')!=bucket&&m.timeline.modEvents.get('v').length==0,'accepted crosskind resets schedule');
 var replacement=new NightmareVisionEventTimeline();m.timeline=replacement;ok(m.modifierTimeline==replacement,'alias follows authoritative public timeline');var called=0;original.addEvent(new NightmareVisionCallbackEvent(0,(_,s)->called+=10,m));m.queueFuncOnce(0,(_,s)->called++,m); // corrected below
 }}'''.replace('m.queueFuncOnce(0,(_,s)->called++,m); // corrected below','m.queueFuncOnce(0,(_,s)->called++);m.updateTimeline(0);ok(called==1,"replaced timeline is only scheduler");m.queueFuncOnce(9,(_,s)->called++);m.destroy();ok(original.events.length==0&&replacement.events.length==0,"owned/current schedules released");original.update(10);replacement.update(10);ok(called==1,"destroyed timelines inert");'))

    def test_callback_only_owner_safeguard_and_value_exceptions(self):
        self.run_haxe(r'''class Main {static function ok(v:Bool,m:String):Void if(!v)throw m;static function main(){
 var reports=0;var calls=0;var m=new NightmareVisionModManager((e,error)->reports++);m.queueFuncOnce(0,(_,s)->{throw 'callback';});m.queueFuncOnce(1,(_,s)->calls++);m.updateTimeline(1);ok(reports==1&&calls==1&&m.timeline.events.length==0,'owner callback containment');
 var direct=new NightmareVisionEventTimeline();var c=new NightmareVisionCallbackEvent(0,(_,s)->{throw 'direct';},m);direct.addEvent(c);var failed=false;try direct.update(0)catch(_:Dynamic)failed=true;ok(failed&&!c.finished&&direct.events[0]==c,'standalone source errors retained');
 var missing=new NightmareVisionEaseEvent(2,4,'missing',1,t->t,0,m);m.timeline.addEvent(missing);failed=false;try m.updateTimeline(3)catch(_:Dynamic)failed=true;ok(failed&&!missing.finished&&reports==1,'value exceptions not contained');m.destroy();direct.destroy();
 }}''')
