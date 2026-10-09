"""Compare historical visual transport with executable methods from the pinned donor."""
from pathlib import Path
import re
import subprocess
import unittest
import test_nv_custom_modifier_registration as support
from test_nv_multifield_routes import method
ROOT = Path(__file__).resolve().parents[2]
REV = '7f96eb3b5a60352413229bf134bd348b79ad5fe6'

class LegacyScrollVelocityTest(unittest.TestCase):
    run_haxe = support.CustomModifierTest.run_haxe

    def test_pinned_event_order_continuity_mutation_and_playback_clock(self):
        donor = ROOT.parent / 'fnf_sources/NightmareVision'
        if not donor.is_dir(): self.skipTest('pinned donor repository unavailable')
        src = subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
        funcs = method(src,'public function getNoteInitialTime(') + method(src,'public function getSV(')
        for name in ['getTimeFromSV','getVisualPosition']:
            funcs += re.search(r'public inline function '+name+r'\([^;]+;',src).group()
        pushed = method(src,'function eventPushed(')
        pushed = pushed[pushed.index('var speed:Float'):pushed.index("case 'Play Video':")]
        fixture = r"""
import NightmareVisionScrollVelocity.NightmareVisionSpeedEvent as SpeedEvent;
class Conductor {public static var songPosition:Float=0;}
class Donor {
 public var speedChanges:Array<SpeedEvent>=[NightmareVisionScrollVelocity.initial()];
 public var currentSV:SpeedEvent=NightmareVisionScrollVelocity.initial();
 public var songSpeed:Float=1.734;public var modManager=new NightmareVisionModManager();
 public function new(){}
 function svSort(a:SpeedEvent,b:SpeedEvent):Int return a.startTime<b.startTime?-1:a.startTime>b.startTime?1:0;
 public function push(event:Dynamic):Void { __PUSH__ }
 __FUNCTIONS__
}
class Main {
 static function near(a:Float,b:Float,m:String):Void {
  if(Math.isNaN(a)&&Math.isNaN(b))return;
  if(a==b)return;
  if(!Math.isFinite(a)||!Math.isFinite(b)||Math.abs(a-b)>.000001)throw m+': '+a+' != '+b;
 }
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  var ref=new Donor();var changes=[NightmareVisionScrollVelocity.initial()];
  var rows:Array<Dynamic>=[
   {event:'Mult SV',value1:'2',strumTime:1000.},
   {event:'Constant SV',value1:'4',strumTime:2000.},
   {event:'Mult SV',value1:'-1',strumTime:2500.},
   {event:'Mult SV',value1:'0',strumTime:3000.},
   {event:'Mult SV',value1:'junk',strumTime:4000.},
   {event:'Constant SV',value1:'junk',strumTime:4000.},
   {event:'Mult SV',value1:'3',strumTime:1500.},
   {event:'Mult SV',value1:'7',strumTime:-50.}
  ];
  for(row in rows){
   ref.push(row);NightmareVisionScrollVelocity.push(changes,row.event,row.value1,row.strumTime,ref.songSpeed);
   for(time in [-100.,0.,500.,999.,1000.,1499.,1500.,1999.,2000.,2499.,2500.,3000.,4000.,5000.]){
    var a=ref.getSV(time);var b=NightmareVisionScrollVelocity.select(time,changes);
    near(a.startTime,b.startTime,'source event selection');near(a.position,b.position,'event continuity');
    near(a.startSpeed,b.startSpeed,'lazy preceding speed');
    near(ref.getNoteInitialTime(time),NightmareVisionScrollVelocity.position(time,b),'captured visual time');
   }
  }
  for(fps in [30,60,144,1000])for(frame in 0...fps*5){
   Conductor.songPosition=frame*1000./fps;
   ref.currentSV=ref.getSV(Conductor.songPosition);
   near(ref.getVisualPosition(),NightmareVisionScrollVelocity.position(Conductor.songPosition,NightmareVisionScrollVelocity.select(Conductor.songPosition,changes)),'frame-independent visual clock');
  }
  var live:SpeedEvent={position:500.,startTime:100.,songTime:75.,speed:3.};
  changes=[live];var selected=NightmareVisionScrollVelocity.select(500,changes);
  check(selected==live && live.startSpeed==1,'live event identity and metadata');
  live.speed=-2;near(NightmareVisionScrollVelocity.position(500,selected),117.5,'live currentSV mutation');
  check(NightmareVisionScrollVelocity.select(-1,changes)!=live,'negative-time initial fallback');
  for(value in ['0','-2','2.5','invalid']){
   ref=new Donor();changes=[NightmareVisionScrollVelocity.initial()];
   var row={event:'Constant SV',value1:value,strumTime:100.};
   ref.push(row);NightmareVisionScrollVelocity.push(changes,row.event,row.value1,row.strumTime,ref.songSpeed);
   near(ref.getNoteInitialTime(500),NightmareVisionScrollVelocity.position(500,NightmareVisionScrollVelocity.select(500,changes)),'unclamped source Constant SV');
  }
 }
}
"""
        self.run_haxe(fixture.replace('__PUSH__',pushed).replace('__FUNCTIONS__',funcs))

    def test_live_host_surface_profile_isolation_and_source_order(self):
        source=(ROOT/'source/PlayState.hx').read_text(encoding='utf-8')
        # Compile the actual host delegates and profile guard, not a duplicate adapter.
        start=source.index('\t@:keep public var speedChanges:')
        stop=source.index('\n\t/** One real native receptor bank',start)
        host=source[start:stop]
        self.run_haxe(r"""
class Conductor {public static var songPosition:Float=1000;}
class Host {
 public var nightmareVisionLegacyFieldCameras:Bool;
 public var nightmareVisionConductor:Dynamic={visualPosition:0.};
 public function new(legacy:Bool){nightmareVisionLegacyFieldCameras=legacy;}
 public function tick():Void updateNightmareVisionVisualPosition();
 __HOST__
}
class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  var a=new Host(true),b=new Host(true),modern=new Host(false);
  a.speedChanges=[{position:45.,startTime:100.,songTime:100.,speed:2.}];
  a.tick();b.tick();modern.tick();
  check(a.currentSV==a.speedChanges[0] && a.nightmareVisionConductor.visualPosition==855,'host live timeline');
  check(b.nightmareVisionConductor.visualPosition==450 && modern.nightmareVisionConductor.visualPosition==0,'owner/profile isolation');
  check(a.sourceNoteVisualTime(1000)==855 && modern.sourceNoteVisualTime(1000)==0,'constructor profile');
  var interp=new NightmareVisionScriptInterp();interp.variables.set('game',a);
  interp.execute(new crowplexus.hscript.Parser().parseString("game.currentSV.speed = 3; var p = game.getVisualPosition(); if(p != 1260) throw 'live script event'; game.speedChanges = [{position:20.,startTime:0.,songTime:0.,speed:0.}];"));
  a.tick();check(a.nightmareVisionConductor.visualPosition==20,'script timeline replacement');interp.release();
 }
}
""".replace('__HOST__',host))
        generation=method(source,'private function generateSong(')
        prep=generation.index('if (nightmareVisionScripts != null && nightmareVisionLegacyFieldCameras)')
        self.assertLess(prep,generation.index('var generateChartNotes:Void->Void'))
        self.assertIn('speedChanges.sort(NightmareVisionScrollVelocity.sort)',generation[prep:])
        update=method(source,'override public function update(')
        self.assertLess(update.index('super.update(elapsed)'),update.index('updateNightmareVisionVisualPosition()'))
        note=(ROOT/'source/Note.hx').read_text()
        timing=method(note[note.index('this.strumTime = strumTime;'):], 'if (sourceTimingMode == 2) {')
        self.assertIn('visualTime = PlayState.instance.sourceNoteVisualTime(this.strumTime)',timing)
        self.assertIn('nightmareVisionLegacyGeometry = PlayState.instance.sourceUsesLegacyNoteGeometry()',timing)
        self.assertGreaterEqual(source.count('nightmareVisionConductor.visualPosition = 0'),2)
