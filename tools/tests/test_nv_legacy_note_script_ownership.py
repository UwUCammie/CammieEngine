"""Pinned historical note attachments through the shared script loader/interpreter."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from tools.haxe_flixel_math_stubs import write_flixel_point_stub
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]
REV = "7f96eb3b5a60352413229bf134bd348b79ad5fe6"


class HistoricalNoteScriptOwnershipTest(unittest.TestCase):
    def test_captured_identity_setter_reset_and_live_callback_replacement(self):
        donor = ROOT.parent / "fnf_sources/NightmareVision"
        if not donor.is_dir():
            self.skipTest("pinned source unavailable")
        source = subprocess.check_output(["git", "show", REV + ":source/gameObjects/Note.hx"], cwd=donor, text=True)
        setter = method(source, "private function set_noteType(").replace("private function set_noteType", "public function assign")
        native = (ROOT / 'source/Note.hx').read_text()
        native_setter = method(native, 'function set_noteType(')
        native_getter = method(native, 'function get_noteType(')
        native_initialize = method(native, 'public function initializeLegacyNoteType(')
        base = r'''
 public var noteScript:NightmareVisionScriptModule;
 public var noteType=''; public var noteData=0; public var inEditor=false;
 public var noteSplashTexture=''; public var isQuant=false;public var quant=4;public var quants=[4];
 public var noteSplashHue=0.;public var noteSplashSat=0.;public var noteSplashBrt=0.;
 public var ignoreNote=false;public var mustPress=true;public var isSustainNote=false;
 public var missHealth=0.;public var hitCausesMiss=false;public var noAnimation=false;public var noMissAnimation=false;
 public var forceGfSing=false;public var gfNote(get,set):Bool;function get_gfNote()return forceGfSing;function set_gfNote(v:Bool)return forceGfSing=v;public var alpha=1.;public var color=0;public var doSlam=true;
 public var events:Array<String>=[];
'''
        files = {
            "NightmareVisionLegacyColorSwap.hx": "class NightmareVisionLegacyColorSwap {public var hue=0.;public var saturation=0.;public var brightness=0.;public function new(){}}",
            "PlayState.hx": "class PlayState {public static var SONG:Dynamic={splashSkin:'noteSplashes'};public static var instance:Dynamic;} class ChartingState {public static var instance:Dynamic;}",
            "ClientPrefs.hx": "class ClientPrefs {public static var noteSkin='Vanilla';public static var arrowHSV=[[0.,0.,0.],[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]];public static var quantHSV=[[0.,0.,0.]];public static var quantStepmania=[[0.,0.,0.]];}",
            "Donor.hx": "import PlayState.ChartingState;typedef FunkinHScript=NightmareVisionScriptModule;class Donor {" + base + "public var colorSwap=new NightmareVisionLegacyColorSwap();public function new(){}public function reloadNote(s:String){events.push('reload:'+s+':'+(noteScript==null)+':'+noteType+':'+ignoreNote+':'+missHealth+':'+hitCausesMiss);}" + setter + "}",
            "Note.hx": "class Note {" + base.replace("public var noteType='';", "public var noteType(get,set):String; public var sourceKind(default,set):String='';public var sourceKindWrites=0;function set_sourceKind(v:String):String{sourceKindWrites++;sourceKind=v;return v;}") + native_setter + native_getter + native_initialize + r'''
 public var nightmareVisionTypeRuntime:NightmareVisionNoteTypeRuntime;public var runtime(get,set):NightmareVisionNoteTypeRuntime;function get_runtime()return nightmareVisionTypeRuntime;function set_runtime(v) return nightmareVisionTypeRuntime=v;
 public var nightmareVisionLegacyColors:NightmareVisionLegacyNoteColors;public var colors(get,set):NightmareVisionLegacyNoteColors;function get_colors()return nightmareVisionLegacyColors;function set_colors(v)return nightmareVisionLegacyColors=v;
 public var colorSwap(get,never):NightmareVisionLegacyColorSwap;
 function get_colorSwap()return colors.swap;
 public function new(prefs:Dynamic)colors=new NightmareVisionLegacyNoteColors(prefs);
 public function reloadNote(s:String){events.push('reload:'+s+':'+(noteScript==null)+':'+noteType+':'+ignoreNote+':'+missHealth+':'+hitCausesMiss);}
 public function assign(s:String){noteType=s;}
}''',
            "Main.hx": r'''
import NightmareVisionNoteTypeRuntime.NightmareVisionNoteApiBridge;
class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  var errors:Array<String>=[];var sources:Map<String,String>=[];
  for(name in ['one','two']) sources.set(name,
   "function setupNote(n){if(this!=n || n.noteScript!=script)throw 'setup receiver/attachment'; n.events.push('setup:"+name+"');}"
   +"function update(n,elapsed){if(this!=n)throw 'update receiver';n.events.push('update:"+name+"');}"
   +"function onReloadNote(n,p,t,s){n.events.push('pre:"+name+"');return 0;}"
   +"function postReloadNote(n,p,t,s){n.events.push('post:"+name+"');}"
   +"function loadNoteAnims(n){n.events.push('anim:"+name+"');}"
   +"function onDestroy(){destroyed=true;}");
  var plan:NightmareVisionScriptDiscovery.NightmareVisionScriptPlan={root:'owner',baseAssetsRoot:'',song:'fixture',stage:'fixture',coverageNotes:[],scripts:[
   for(name in ['one','two']) {scope:'notetype',name:name,path:name,relative:name+'.hx'}]};
  var map:Map<String,NightmareVisionScriptModule>=[];
  var scripts=new NightmareVisionGameplayScripts({},plan,function(path)return sources.get(path),
   function(i,e,a){},function(n,p,e)errors.push(n+':'+p+':'+Std.string(e)));
  scripts.legacyNoteRegistry=function()return map;
  scripts.loadNoteTypes();var one=map.get('one'),two=map.get('two');
  check(one!=null&&two!=null&&one==scripts.group.getScript('one')&&one==scripts.noteTypeGroup.getScript('one'),'one shared loaded module per source type');
  var api=new NightmareVisionNoteApiBridge(function(n)return 'sheet',function(n,path){n.events.push('atlas');return true;});
  var runtime=new NightmareVisionNoteTypeRuntime(scripts,api);runtime.legacyNoteScripts=true;
  var prefs:Dynamic={noteSkin:'Vanilla',arrowHSV:ClientPrefs.arrowHSV};
  runtime.prepareLegacyColors=function(v,force)return (cast v:Note).colors.prepare(cast v,force);
  runtime.finishLegacyColors=function(v)(cast v:Note).colors.finish(cast v);
  var actual=new Note(prefs);actual.runtime=runtime;var expected=new Donor();
  PlayState.instance={notetypeScripts:map};
  var compare=function(label:String){check(actual.noteScript==expected.noteScript,label+' attachment');check(actual.events.join(',')==expected.events.join(','),label+' events '+actual.events.join(',')+' != '+expected.events.join(','));};
  actual.assign('one');expected.assign('one');compare('initial setup');
  map.set('one',two); // Existing notes retain the earlier object, independently of map changes.
  runtime.update(actual,.1);expected.noteScript.executeFunc('update',[expected,.1],expected);compare('retained old module');
  runtime.loadLegacyAnimations(actual,false,function()throw 'unexpected default');
  expected.noteScript.executeFunc('loadNoteAnims',[expected],expected);compare('retained animation module');
  actual.assign('one');expected.assign('one');compare('same-value assignment clears attachment');
  check(actual.noteScript==null,'same assignment reselected map entry');
  runtime.update(actual,.1);runtime.loadLegacyAnimations(actual,false,function()actual.events.push('default'));
  expected.events.push('default');compare('cleared callbacks stay cleared');
  actual.assign('two');expected.assign('two');compare('changed type captures current map');
  actual.assign('Hurt Note');expected.assign('Hurt Note');compare('built-in reload sees cleared attachment');
  actual.assign('absent');expected.assign('absent');compare('missing type never falls back');
  actual.assign('two');expected.assign('two');compare('recover assignment');
  // A script-authored attachment is authoritative, even if its name differs from noteType.
  actual.noteScript=one;actual.events.resize(0);runtime.setupNote(actual);runtime.update(actual,.1);
  check(actual.noteScript==one&&actual.events.join(',')=='update:one','ordinary spawn setup replaced script-authored pointer');
  var replacement:Map<String,NightmareVisionScriptModule>=['one'=>one];map=replacement;
  actual.assign('one');check(actual.noteScript==one,'replacement source registry not used');
  scripts.noteTypeGroup.removeScript(one);runtime.update(actual,.1);
  check(actual.noteScript==one,'registry membership change detached existing note');
  var swap=NightmareVisionScriptModule.fromSource('swap',
   "function onReloadNote(n,p,t,s){n.events.push('swap');n.noteScript=next;return 0;}",null,null,
   function(i)i.variables.set('next',two),function(n,p,e)errors.push(Std.string(e)));
  actual.noteScript=swap;actual.events.resize(0);runtime.reloadNote(actual);
  check(actual.events.join(',')=='swap,atlas,post:two','post-reload did not reread the authored attachment');
  actual.events.resize(0);actual.noteScript=null;runtime.reloadNote(actual);
  check(actual.events.join(',')=='atlas','cleared script unexpectedly revived by noteType');

  // Execute the native getter/setter alongside the pinned donor, including reentrant setup.
  var nesting=NightmareVisionScriptModule.fromSource('nesting',
   "function setupNote(n){n.events.push('outer-before:'+n.noteType);n.assign('two');n.events.push('outer-after:'+n.noteType);n.colorSwap.hue=.625;}",null,null,null,
   function(n,p,e)errors.push(Std.string(e)));
  var inspect=NightmareVisionScriptModule.fromSource('inspect',
   "function setupNote(n){n.events.push('inner:'+n.noteType);n.colorSwap.hue=.375;}",null,null,null,
   function(n,p,e)errors.push(Std.string(e)));
  map=['nesting'=>nesting,'two'=>inspect];PlayState.instance={notetypeScripts:map};
  actual=new Note(prefs);actual.runtime=runtime;expected=new Donor();
  actual.assign('nesting');expected.assign('nesting');compare('nested assignment source order');
  check(actual.noteType==expected.noteType&&actual.noteType=='nesting','outer assignment commits last');
  check(actual.noteScript==inspect&&actual.noteSplashHue==expected.noteSplashHue&&actual.noteSplashHue==.625,
   'inner attachment survives outer commit, splash captures final callback HSV');
  check(actual.events.join(',')=='outer-before:,inner:,outer-after:two','setup observes old type until each nested commit');
  for(kind in ['Hurt Note','Hurt Note','No Animation','GF Sing','Ghost Note','Normal Slam','Half Slam Lane 1','Half Slam Lane 2','Half Slam Lane 3','Half Slam Lane 4','absent']) {
   actual.assign(kind);expected.assign(kind);compare('built-in '+kind);
   check(actual.noteType==expected.noteType&&actual.hitCausesMiss==expected.hitCausesMiss&&actual.ignoreNote==expected.ignoreNote
    &&actual.missHealth==expected.missHealth&&actual.noAnimation==expected.noAnimation&&actual.noMissAnimation==expected.noMissAnimation
    &&actual.forceGfSing==expected.forceGfSing&&actual.alpha==expected.alpha&&actual.color==expected.color&&actual.doSlam==expected.doSlam,
    'built-in side effects '+kind);
  }
  actual=new Note(prefs);actual.runtime=runtime;actual.sourceKind='nesting';expected=new Donor();
  actual.initializeLegacyNoteType();expected.assign('nesting');compare('first authored generation');
  var count=actual.events.length;actual.initializeLegacyNoteType();runtime.setupNote(actual);
  check(actual.events.length==count&&actual.noteScript==inspect,'repeated skin setup preserves nested attachment');
  for(pressed in [false,true]) for(sustain in [false,true]) {
   actual=new Note(prefs);actual.runtime=runtime;expected=new Donor();
   actual.mustPress=expected.mustPress=pressed;actual.isSustainNote=expected.isSustainNote=sustain;
   actual.assign('Hurt Note');expected.assign('Hurt Note');compare('hurt reload ordering');
   check(actual.ignoreNote==expected.ignoreNote&&actual.missHealth==expected.missHealth&&actual.hitCausesMiss==expected.hitCausesMiss,
    'player/opponent tap/hold damage');
  }
  var laneChange=NightmareVisionScriptModule.fromSource('laneChange',"function setupNote(n){n.noteData=-1;}",null,null,null,
   function(n,p,e)errors.push(Std.string(e)));
  map.set('laneChange',laneChange);actual=new Note(prefs);actual.runtime=runtime;expected=new Donor();
  actual.assign('laneChange');expected.assign('laneChange');compare('admission captured before callback');
  check(actual.noteType==expected.noteType&&actual.noteType=='laneChange','callback lane mutation must not change assignment admission');
  check(actual.sourceKindWrites==0,'historical commit must not replay other profile effects');
  laneChange.destroy();
  nesting.destroy();inspect.destroy();
  // Modern lookup intentionally follows its registry and remains independent of noteScript.
  var modern=new NightmareVisionNoteTypeRuntime(scripts,api);actual.noteData=0;actual.noteType='two';actual.events.resize(0);
  modern.update(actual,.1);check(actual.events.join(',')=='update:two','modern registry lookup changed');
  actual.noteScript=two;runtime.resetNote(actual,true);check(actual.noteScript==null&&!two.released,'reset owns pointer, not module');
  actual.noteScript=two;runtime.releaseNote(actual);check(actual.noteScript==null&&!two.released,'release destroyed shared module');
  actual.nightmareVisionLegacyColors=null;actual.runtime=modern;actual.noteType='modern';
  check(actual.noteType=='modern'&&actual.sourceKindWrites==1,'modern setter keeps existing profile effects');
  check(errors.length==0,errors.join(','));swap.destroy();scripts.destroy();
  check(one.released&&two.released,'shared main group retains final module ownership');
 }
}
'''
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = FixturePath(directory)
            write_flixel_point_stub(work)
            for name, text in files.items():
                (work / name).write_text(text, encoding="utf-8", newline="\n")
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(ROOT / ".haxelib/hscript-iris/1,1,3"), "-cp", str(work), "-main", "Main", "--interp"], cwd=ROOT, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
