"""The shared importer/refresh panel renders coordinator and manual job state."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from test_nv_multifield_routes import method
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


STUBS = {
    "haxe/Timer.hx": r'''package haxe;
class Timer { public static var now:Float=0; public static function stamp():Float return now; }''',
    "flixel/FlxBasic.hx": r'''package flixel;
class FlxBasic {
 public var active:Bool = true;
 public var visible:Bool = true; public var exists=true;
 public function new() {}
 public function update(elapsed:Float):Void {} public function destroy():Void {} public var draws=0;public function draw():Void draws++;
}''',
    "flixel/Point.hx": r'''package flixel;
class Point {
 public var x:Float; public var y:Float;
 public function new(x:Float=0,y:Float=0) { this.x=x; this.y=y; }
 public function set(x:Float=0,y:Float=0):Void { this.x=x; this.y=y; }
}''',
    "flixel/FlxSprite.hx": r'''package flixel;
class FlxSprite extends FlxBasic {
 public var x:Float=0; public var y:Float=0; public var width:Float=0; public var height:Float=0;
 public var alpha:Float=1; public var color:Int=0; public var scale:Point=new Point(1,1);
 public var origin:Point=new Point(); public var scrollFactor:Point=new Point();
 public function new(?x:Float=0,?y:Float=0) { super(); this.x=x; this.y=y; }
 public function makeGraphic(width:Int,height:Int,color:Int):FlxSprite {
  this.width=width; this.height=height; this.color=color; return this;
 }
 public function setPosition(x:Float=0,y:Float=0):Void { this.x=x; this.y=y; }
}''',
    "flixel/FlxG.hx": r'''package flixel;
class FlxG {public static var state:FlxState; public static var width:Int=1280; public static var height:Int=720; }''',
    "flixel/FlxState.hx": 'package flixel;class FlxState extends flixel.group.FlxGroup.FlxTypedGroup<FlxBasic> {public var subState:Dynamic;public var persistentDraw=true;public var persistentUpdate=false;public function new(){super();}}',
    "flixel/FlxCamera.hx": 'package flixel;class FlxCamera {public static var _defaultCameras:Array<FlxCamera>=[];}',
    "flixel/util/FlxColor.hx": r'''package flixel.util;
class FlxColor {
 public static inline var WHITE:Int=0xFFFFFFFF;
 public static function fromRGB(r:Int,g:Int,b:Int,a:Int=255):Int return (a<<24)|(r<<16)|(g<<8)|b;
}''',
    "flixel/text/FlxText.hx": r'''package flixel.text;
import flixel.FlxSprite;
class FlxText extends FlxSprite {
 var _text:String=""; public var writes:Int=0;
 public var text(get,set):String; public var wordWrap:Bool=true;
 public function new(x:Float=0,y:Float=0,width:Float=0,text:String="",size:Int=8) {
  super(x,y); this.width=width; this.text=text;
 }
 function get_text():String return _text;
 function set_text(value:String):String { writes++; _text=value; return value; }
}''',
    "flixel/group/FlxGroup.hx": r'''package flixel.group;
import flixel.FlxBasic;import flixel.FlxCamera;
class FlxTypedGroup<T:FlxBasic> extends FlxBasic {
 public var _cameras:Array<flixel.FlxCamera>;
 public var members:Array<T>=[];
 public function new(maxSize:Int=0) { super(); }
 public function add(value:T):T { members.push(value); return value; }
 override public function update(elapsed:Float):Void {
  for (member in members) if (member.active) member.update(elapsed);
 }
}''',
    "ImportRefreshManager.hx": r'''class ImportRefreshManager {
 public static var calls:Int=0;
 public static var failNext:Bool=false;public static var warnings:Array<String>=[];public static function reportFailure(message:String):Void warnings.push(message);
 public static var snapshot:Dynamic={busy:false,label:"",fraction:0.0,complete:false,changed:false,blocked:false};
 public static function browseTick():Dynamic {
  calls++;
  if(failNext) { failNext=false; throw "coordinator unavailable"; }
  return snapshot;
 }
 public static function setStatus(status:Dynamic):Void snapshot=status;
}''',
}
STUBS["ImportRefreshProgress.hx"] = (ROOT / "source/ImportRefreshProgress.hx").read_text(encoding="utf-8")

# Exercise actual pinned parent/group draw algorithms, including persistentDraw
# with parent update paused. Drawing stubs measure calls, not pixels.
_NATIVE = ROOT / '.haxelib/flixel/6,1,2/flixel'
_group_draw = method((_NATIVE / 'group/FlxGroup.hx').read_text(encoding='utf-8'), 'override public function draw(')
STUBS['flixel/group/FlxGroup.hx'] = STUBS['flixel/group/FlxGroup.hx'].replace(' override public function update(', _group_draw + '\n override public function update(')
_state_draw = method((_NATIVE / 'FlxState.hx').read_text(encoding='utf-8'), 'override function draw(')
STUBS['flixel/FlxState.hx'] = STUBS['flixel/FlxState.hx'].replace('public function new(){', _state_draw + 'public function new(){')


MAIN = r'''import flixel.FlxG;
import haxe.Timer;
class Main {
 static function check(value:Bool,message:String):Void if(!value) throw message;
 static function main():Void {
  var foreground=new flixel.FlxState();FlxG.state=foreground;
  var overlay=new ImportRefreshProgressBar(foreground);foreground.add(overlay);
  check(overlay.active&&!overlay.visible,"overlay must keep polling while hidden");
  overlay.update(0.016);
  check(ImportRefreshManager.calls==1&&!overlay.visible,"idle poll or visibility");

  var longPath="C:/import-cache/sources/abcdef123456/content/ModRoot/songs/a-very-long-folder-name/";
  for(i in 0...5) longPath+="more-nested-folders/";
  longPath+="a-song-with-a-long-name.ogg";
  ImportRefreshManager.setStatus({busy:true,label:"Readable Mod",phase:"retaining-source",
   current:longPath,completed:30,total:210,fraction:0.375,elapsedSeconds:75.8,
   activityAgeSeconds:18.3,phaseElapsedSeconds:23.2,etaSeconds:123.1,queueRemaining:2,
   complete:false,changed:false,blocked:false});
  overlay.update(0.25);
  check(overlay.visible&&overlay.active,"busy overlay was hidden or stopped polling");
  check(overlay.statusText.text=="Readable Mod","busy headline should be only the import name");
  check(overlay.phaseText.text.indexOf("Phase: ")>=0
   &&overlay.phaseText.text.indexOf(" | ")>=0
   &&overlay.phaseText.text.indexOf("30/210 done")>=0
   &&overlay.phaseText.text.indexOf("180 files left")>=0,"phase progress and remaining files were not clear");
  check(overlay.phaseText.text.indexOf("%")<0,"phase progress was presented as a whole-import estimate");
  check(overlay.currentFileText.text.indexOf("Current file: ModRoot/songs/")==0
   &&overlay.currentFileText.text.indexOf("import-cache")==-1
   &&overlay.currentFileText.text.indexOf("...")>=0
   &&overlay.currentFileText.text.length<=Std.int(overlay.currentFileText.width/(14*0.80)),
   "long current file path was not ellipsized: "+overlay.currentFileText.text);
  check(overlay.activityText.text.indexOf("19s ago")>=0,"age of the last actual progress update was not shown");
  check(overlay.timingText.text.indexOf("Elapsed 1m 15s")>=0
   &&overlay.timingText.text.indexOf(" | ")>=0
   &&overlay.timingText.text.indexOf("Phase ETA ~2m 04s")>=0
   &&overlay.timingText.text.indexOf("Queue 2")>=0,"elapsed time, phase ETA, or queue count was omitted");
  check(Math.abs(overlay.progressFraction()-0.375)<0.0001
   &&Math.abs(overlay.progressFill.scale.x-0.375)<0.0001,"phase fraction was not drawn");

  var second=new ImportRefreshProgressBar(foreground);
  second.update(0.016);
  check(second.visible&&ImportRefreshManager.calls==3,"multiple menu pollers did not share status");

  var statusWrites=overlay.statusText.writes;
  var longImportName="A very long imported mod name that is clipped safely when the menu window is narrow";
  ImportRefreshManager.snapshot.label=longImportName;
  overlay.update(0.10);
  overlay.update(0.14);
  check(overlay.statusText.writes==statusWrites,"text refreshed faster than four times per second");
  overlay.update(0.02);
  check(overlay.statusText.text.length<longImportName.length
   &&overlay.statusText.text.indexOf("Readable Mod")==-1
   &&overlay.statusText.text.indexOf("...")>=0
   &&overlay.statusText.text.length<=Std.int(overlay.statusText.width/(20*0.80)),
   "long import name was not ellipsized");
  ImportRefreshManager.snapshot.label="Changed name";
  overlay.update(0.25);
  check(overlay.statusText.text=="Changed name","throttled text did not refresh after 250ms");

  var oldTextWidth=overlay.statusText.width;
  FlxG.width=520;
  overlay.update(0.25);
  check(overlay.panel.x==22&&overlay.panel.scale.x<1&&overlay.statusText.width<oldTextWidth,
   "panel did not stay centered and responsive to a narrower viewport");

  ImportRefreshManager.setStatus({busy:true,label:"Readable Mod",phase:"scanning-retained-source",
   current:"",completed:0,total:0,fraction:0.375,elapsedSeconds:81,activityAgeSeconds:24,
   phaseElapsedSeconds:6,etaSeconds:-1,queueRemaining:1,complete:false,changed:false,blocked:false});
  overlay.update(0.25);
  var firstIndeterminateX=overlay.progressFill.x;
  check(overlay.phaseText.text.indexOf("total unknown")>=0
   &&overlay.currentFileText.text.indexOf("Waiting for")>=0
   &&overlay.timingText.text.indexOf("Phase ETA unavailable")>=0,
   "unknown phase totals or missing current-file details were not explained");
  check(overlay.progressFill.scale.x>0&&overlay.progressFill.scale.x<0.24,
   "unknown totals did not draw an indeterminate segment");
  overlay.update(0.25);
  check(overlay.progressFill.x!=firstIndeterminateX,"indeterminate fill did not animate");

  ImportRefreshManager.setStatus({busy:true,label:"Readable Mod",phase:"scan-roots",
   current:"songs",completed:4,total:0,fraction:0,elapsedSeconds:83,activityAgeSeconds:1,
   phaseElapsedSeconds:2,etaSeconds:-1,queueRemaining:0,complete:false,changed:false,blocked:false});
  overlay.update(0.25);
  check(overlay.phaseText.text.indexOf("Phase: Folders | 4 checked | unknown")==0,
   "unknown folder totals were described as file counts");

  FlxG.width=1280;
  overlay.update(0.25);

  ImportRefreshManager.setStatus({busy:true,label:"Readable Mod",phase:"scan-songs",
   current:"ModRoot/songs/test-song/chart.json",completed:3,total:12,fraction:0.25,
   elapsedSeconds:85,activityAgeSeconds:1,phaseElapsedSeconds:3,etaSeconds:-1,queueRemaining:0,
   complete:false,changed:false,blocked:false});
  overlay.update(0.25);
  check(overlay.phaseText.text.indexOf("Scanning songs")>=0,"song scan phase description was not mapped");
  ImportRefreshManager.setStatus({busy:true,label:"Readable Mod",phase:"scan-assets",
   current:"ModRoot/assets/images",completed:2,total:5,fraction:0.4,
   elapsedSeconds:86,activityAgeSeconds:1,phaseElapsedSeconds:4,etaSeconds:-1,queueRemaining:0,
   complete:false,changed:false,blocked:false});
  overlay.update(0.25);
  check(overlay.phaseText.text.indexOf("Scanning assets")>=0,"asset scan phase description was not mapped");

  ImportRefreshManager.setStatus({busy:false,label:"Local changes need review",fraction:0.0,
   complete:false,changed:false,blocked:true});
  overlay.update(0.25);
  check(!overlay.visible,"completed conflict must not persist as automatic popup");
  check(ImportRefreshManager.snapshot.label=="Local changes need review"&&ImportRefreshManager.snapshot.blocked,"warning diagnostics remain in coordinator");

  ImportRefreshManager.setStatus({busy:false,label:"",fraction:1.0,
   complete:true,changed:true,blocked:false});
  overlay.update(0.25);
  check(!overlay.visible,"completed background work never shows a success popup");
  var later=new ImportRefreshProgressBar(foreground);later.update(.016);check(!later.visible,"new overlay cannot replay completion");
  overlay.update(3.0);
  check(!overlay.visible,"terminal status became visible during the idle interval");
  var calls=ImportRefreshManager.calls;
  overlay.update(0.25);
  check(!overlay.visible&&ImportRefreshManager.calls==calls+1,
   "hidden overlay stopped polling for later queued work");

  ImportRefreshManager.failNext=true;
  overlay.update(0.25);
  check(!overlay.visible&&ImportRefreshManager.warnings[0]=="coordinator unavailable","failure popup retired while full diagnostics preserved");
  ImportRefreshManager.setStatus({busy:true,label:"Retry",fraction:0,complete:false,changed:false,blocked:false});
  overlay.update(.25);check(overlay.visible,"later active retry visible");
  ImportRefreshManager.setStatus({busy:true,backgroundBusy:false,label:"Old warning",fraction:0,complete:false,changed:false,blocked:true});
  overlay.update(.25);check(!overlay.visible,"manual busy gate cannot show stale automatic progress");
  ImportRefreshManager.setStatus({busy:true,backgroundBusy:true,label:"Background retry",fraction:0,complete:false,changed:false,blocked:false});
  overlay.update(.25);check(overlay.visible,"explicit background progress is shown");
  var pollCount=ImportRefreshManager.calls;
  foreground.draw();var childDraws=overlay.panel.draws;check(childDraws>0,"actual parent draws foreground progress");
  foreground.subState={draw:function(){}};
  foreground.draw();check(overlay.panel.draws==childDraws&&!overlay.visible&&ImportRefreshManager.calls==pollCount,"persistent parent draw without update cannot leak modal progress");
  ImportRefreshManager.setStatus({busy:false,backgroundBusy:false,label:"Imports refreshed.",fraction:1,complete:true,changed:true,blocked:false});
  foreground.subState=null;overlay.update(.016);check(!overlay.visible,"resume polls fresh idle snapshot rather than cached busy");
  ImportRefreshManager.setStatus({busy:true,backgroundBusy:true,label:"Background retry",fraction:0,complete:false,changed:false,blocked:false});overlay.update(.25);
  pollCount=ImportRefreshManager.calls;
  foreground.subState={modal:true};overlay.update(.25);check(!overlay.visible&&ImportRefreshManager.calls==pollCount,"modal foreground hides and does not poll stale owner");
  foreground.subState=null;FlxG.state=new flixel.FlxState();overlay.update(.25);check(!overlay.visible&&ImportRefreshManager.calls==pollCount,"departed screen cannot show or pump progress");
  var current=new ImportRefreshProgressBar(FlxG.state);current.update(.016);check(current.visible,"current screen can display real ongoing work");
  ImportRefreshManager.setStatus({busy:false,label:"Checking saved imports",fraction:0,complete:false,changed:false,blocked:false});current.update(.25);check(!current.visible,"idle inspection never remains visible");

  var importer=new flixel.FlxState();FlxG.state=importer;
  Timer.now=0;
  var localStatus:Dynamic={busy:true,label:"Scanning as psych",phase:"scan-assets",
   current:"selected-source/assets/images/characters/example.png",completed:7,total:20,fraction:0.35,
   complete:false,changed:false,blocked:false};
  var callsBeforeLocal=ImportRefreshManager.calls;
  var integrated=new ImportRefreshProgressBar(importer,function():Dynamic return localStatus,true);
  integrated.update(.016);
  check(integrated.visible&&integrated.panel.y==226,"manual work did not use the embedded shared panel");
  check(integrated.statusText.text=="Scanning as psych"
   &&integrated.phaseText.text.indexOf("Scanning assets")>=0
   &&integrated.phaseText.text.indexOf("7/20 done")>=0
   &&integrated.currentFileText.text.indexOf("Current file: selected-source/")==0
   &&integrated.currentFileText.text.indexOf("example.png")>=0,
   "manual scan did not reuse the automatic phase/count/file presentation: "
    +integrated.statusText.text+" | "+integrated.phaseText.text+" | "+integrated.currentFileText.text);
  check(integrated.activityText.text.indexOf("just now")>=0
   &&integrated.timingText.text.indexOf("Elapsed 0s")>=0
   &&integrated.timingText.text.indexOf("Phase ETA unavailable")>=0
   &&integrated.timingText.text.indexOf("Queue ")==-1,
   "manual elapsed/activity/unknown ETA or queue display was misleading");
  check(Math.abs(integrated.progressFraction()-0.35)<0.0001,
   "known local phase fraction was not kept from the shared progress tracker");
  Timer.now=4;
  localStatus.completed=8;
  integrated.update(0.25);
  check(integrated.activityText.text.indexOf("just now")>=0
   &&integrated.timingText.text.indexOf("Elapsed 4s")>=0
   &&integrated.timingText.text.indexOf("Phase ETA ~48s")>=0,
   "shared helper did not calculate a phase-only ETA from local activity");
  Timer.now=5;
  localStatus.phase="scan-roots";
  localStatus.current="selected-source";
  localStatus.completed=4;
  localStatus.total=100;
  integrated.update(0.25);
  check(integrated.phaseText.text.indexOf("4 folders checked | unknown")>=0
   &&integrated.timingText.text.indexOf("Phase ETA unavailable")>=0
   &&integrated.progressFraction()==0
   &&integrated.progressFill.scale.x>0&&integrated.progressFill.scale.x<=0.24,
   "local root scan safety caps were shown as a known total or whole-import fraction: "
    +integrated.phaseText.text+" | "+integrated.timingText.text+" | "+integrated.progressFraction()+" | "+integrated.progressFill.scale.x);
  check(ImportRefreshManager.calls==callsBeforeLocal,"local status must not poll or replace coordinator work");
  localStatus=null;integrated.invalidateStatus();integrated.update(.016);
  check(!integrated.visible,"consuming a manual job must not leave a completion toast");

  for(viewport in [1280,1024,800]) {
   FlxG.width=viewport;
   var lane=new ImportRefreshProgressBar(foreground);
   lane.setMenuLane(130,16,0.56,20);
   lane.update(.25);
   check(lane.panel.x==130&&lane.panel.y==16,
    "menu lane must leave the FPS corner clear");
   check(lane.panel.x+lane.panel.width*lane.panel.scale.x<=viewport*0.56-19,
    "menu lane overlaps the native score column");
   check(lane.panel.origin.x==0&&lane.progressTrack.origin.x==0,
    "scaled panel and track drift outside their reserved bounds");
  }
  FlxG.width=1280;
  foreground.active=false;FlxG.state=foreground;overlay.update(.25);check(!overlay.visible,"inactive owner hides");
 }
}'''


class ImportRefreshProgressBarTest(unittest.TestCase):
    def test_overlay_shows_foreground_busy_state_and_keeps_terminal_status_hidden(self):
        source = (ROOT / "source/ImportRefreshProgressBar.hx").read_text(encoding="utf-8")
        self.assertNotIn("\u00b7", source, "VCR UI text must use ASCII separators")
        self.assertNotIn("\u2026", source, "VCR UI text must use ASCII ellipses")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "ImportRefreshProgressBar.hx").write_text(
                source, encoding="utf-8", newline='\n')
            for relative, content in STUBS.items():
                target = base / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline='\n')
            (base / "Main.hx").write_text(MAIN, encoding="utf-8", newline='\n')
            process = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(base), "--run", "Main"],
                cwd=base, text=True, capture_output=True, timeout=60,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def test_import_settings_uses_the_shared_card_without_the_old_manual_bar(self):
        source = (ROOT / "source/ImportSettingsState.hx").read_text(encoding="utf-8")
        self.assertIn("public var progressPresentation(default, null):ImportRefreshProgressBar", source)
        self.assertIn("new ImportRefreshProgressBar(this, progressPresentationStatus, true)", source)
        self.assertNotIn("FlxBar", source)
        self.assertNotIn("progressText", source)
        self.assertNotIn("progressBar", source)


if __name__ == "__main__":
    unittest.main()
