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
        base = r'''
 public var noteScript:NightmareVisionScriptModule;
 public var noteType=''; public var noteData=0; public var inEditor=false;
 public var noteSplashTexture=''; public var isQuant=false;public var quant=4;public var quants=[4];
 public var noteSplashHue=0.;public var noteSplashSat=0.;public var noteSplashBrt=0.;
 public var ignoreNote=false;public var mustPress=true;public var isSustainNote=false;
 public var missHealth=0.;public var hitCausesMiss=false;public var noAnimation=false;public var noMissAnimation=false;
 public var gfNote=false;public var alpha=1.;public var color=0;public var doSlam=true;
 public var events:Array<String>=[];
'''
        files = {
            "NightmareVisionLegacyColorSwap.hx": "class NightmareVisionLegacyColorSwap {public var hue=0.;public var saturation=0.;public var brightness=0.;public function new(){}}",
            "PlayState.hx": "class PlayState {public static var SONG:Dynamic={splashSkin:'noteSplashes'};public static var instance:Dynamic;} class ChartingState {public static var instance:Dynamic;}",
            "ClientPrefs.hx": "class ClientPrefs {public static var noteSkin='Vanilla';public static var arrowHSV=[[0.,0.,0.],[0.,0.,0.],[0.,0.,0.],[0.,0.,0.]];public static var quantHSV=[[0.,0.,0.]];public static var quantStepmania=[[0.,0.,0.]];}",
            "Donor.hx": "import PlayState.ChartingState;typedef FunkinHScript=NightmareVisionScriptModule;class Donor {" + base + "public var colorSwap=new NightmareVisionLegacyColorSwap();public function new(){}public function reloadNote(s:String){events.push('reload:'+s+':'+(noteScript==null));}" + setter + "}",
            "Note.hx": "class Note {" + base + r'''
 public var runtime:NightmareVisionNoteTypeRuntime;
 public var colors:NightmareVisionLegacyNoteColors;
 public var colorSwap(get,never):NightmareVisionLegacyColorSwap;
 function get_colorSwap()return colors.swap;
 public function new(prefs:Dynamic)colors=new NightmareVisionLegacyNoteColors(prefs);
 public function reloadNote(s:String){events.push('reload:'+s+':'+(noteScript==null));}
 public function assign(s:String){noteType=s;runtime.setupNote(this,true);}
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
  // Modern lookup intentionally follows its registry and remains independent of noteScript.
  var modern=new NightmareVisionNoteTypeRuntime(scripts,api);actual.noteType='two';actual.events.resize(0);
  modern.update(actual,.1);check(actual.events.join(',')=='update:two','modern registry lookup changed');
  actual.noteScript=two;runtime.resetNote(actual,true);check(actual.noteScript==null&&!two.released,'reset owns pointer, not module');
  actual.noteScript=two;runtime.releaseNote(actual);check(actual.noteScript==null&&!two.released,'release destroyed shared module');
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
