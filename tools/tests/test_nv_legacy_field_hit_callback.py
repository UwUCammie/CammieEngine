"""Historical field hit replacement and source admission over the production field."""
from pathlib import Path
import subprocess
import unittest
import test_nv_field_mutation_contract as field_fixture
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]
REV = "7f96eb3b5a60352413229bf134bd348b79ad5fe6"


class HistoricalFieldHitCallbackTest(unittest.TestCase):
    compile = field_fixture.NvFieldMutationContractTest.compile

    def test_pinned_auto_admission_and_replaceable_callback(self):
        donor = ROOT.parent / "fnf_sources/NightmareVision"
        if not donor.is_dir():
            self.skipTest("pinned source unavailable")
        source = subprocess.check_output(["git", "show", REV + ":source/meta/states/PlayState.hx"], cwd=donor, text=True)
        field = subprocess.check_output(["git", "show", REV + ":source/gameObjects/PlayField.hx"], cwd=donor, text=True)
        admission = method(source, "if(field.inControl && field.autoPlayed)")
        get_notes = method(field, "public function getNotes(").replace(":Note", ":Dynamic").replace("Array<Note>", "Array<Dynamic>").replace("Note->Bool", "Dynamic->Bool")
        fixture = r'''
class Conductor {public static var songPosition=100.;}
class WindowNote {
 public var alive=true;public var exists=true;public var noteData=0;
 public var wasGoodHit=false;public var ignoreNote=false;public var isSustainNote=true;
 public var strumTime=100.;public var tooLate=false;public var reads=0;
 public var inWindow=true;public var canBeHit(get,never):Bool;
 function get_canBeHit():Bool {reads++;return inWindow;}
 public function new(){}
}
class Donor {
 public var notes:Array<Dynamic>=[];
 public function new(){}
 __GET_NOTES__
 public function automatic(daNote:Dynamic, field:NightmareVisionPlayFieldView):Void {__SOURCE_AUTO__}
}
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function main() {
  var field=new NightmareVisionPlayFieldView(0,function()return false);
  field.legacyGroupCameras=true;
  var events:Array<String>=[];
  field.bindNativeLifecycle({hit:function(n,f)events.push('native-signal')});
  field.onNoteHit.add(function(n,f)events.push('listener'));
  check(field.noteHitCallback==null,'script-created historical field must not invent a callback');
  var donor=new Donor();
  var note:Dynamic={alive:true,exists:true,noteData:0,canBeHit:true,tooLate:false,
   wasGoodHit:false,ignoreNote:false,isSustainNote:false,strumTime:100.};
  donor.notes.push(note);
  // All source admission predicates, including early holds and late taps.
  for(mask in 0...256)for(time in [90.,100.,110.]) {
   field.inControl=(mask&1)!=0;field.autoPlayed=(mask&2)!=0;
   note.wasGoodHit=(mask&4)!=0;note.ignoreNote=(mask&8)!=0;
   note.isSustainNote=(mask&16)!=0;note.canBeHit=(mask&32)!=0;
   note.tooLate=(mask&64)!=0;note.alive=(mask&128)!=0;note.strumTime=time;
   var expected=false;field.noteHitCallback=function(n,f)expected=true;
   donor.automatic(note,field);
   check(field.canAutoHit(note,100)==expected,'source automatic admission mask '+mask+' time '+time);
   field.notes.resize(0);field.notes.push(note);
   check(field.getNotes(0).length==donor.getNotes(0).length,'manual source note query');
   field.legacyGroupCameras=false;
   var modern=field.inControl&&field.autoPlayed&&!note.wasGoodHit&&!note.ignoreNote&&time<=100;
   check(field.canAutoHit(note,100)==modern,'modern timestamp admission changed');
   field.legacyGroupCameras=true;
  }
  var computed=new WindowNote();field.inControl=true;field.autoPlayed=true;
  field.notes.resize(0);field.notes.push(computed);
  check(field.canAutoHit(computed,100)&&field.getNotes(0).length==1&&computed.reads==2,'computed getter admission');
  computed.inWindow=false;
  check(!field.canAutoHit(computed,100)&&field.getNotes(0).length==0&&computed.reads==4,'live getter rejection');
  events.resize(0);
  var first:(Dynamic,NightmareVisionPlayFieldView)->Void=null;
  var second=function(n:Dynamic,f:NightmareVisionPlayFieldView) {
   check(n==note&&f==field,'source callback payload identity');events.push('second');
  };
  first=function(n,f) {events.push('first');f.noteHitCallback=second;f.dispatchNoteHit(n);};
  field.noteHitCallback=first;
  field.dispatchNoteHit(note);field.dispatchNoteHit(note);
  check(events.join(',')=='first,second,second','replacement and reentrant dispatch must bypass native signal effects');
  field.bindNativeLifecycle({hit:function(n,f)events.push('rebound-native')});
  check(field.noteHitCallback==second,'lifecycle rebinding overwrote script callback');
  field.noteHitCallback=function(n,f)throw 'sentinel';
  var error='';try field.dispatchNoteHit(note) catch(e:Dynamic)error=Std.string(e);
  check(error=='sentinel','callback failure was swallowed or fell back');
  field.noteHitCallback=null;error='';try field.dispatchNoteHit(note)catch(e:Dynamic)error=Std.string(e);
  check(error.indexOf('noteHitCallback is null')>=0,'null callback should report an attributable source failure');
  check(events.join(',')=='first,second,second','null or throwing callback ran native fallback');
  field.legacyGroupCameras=false;field.dispatchNoteHit(note);
  check(events.join(',')=='first,second,second,rebound-native,listener','modern ordered signals must remain independent');
  field.noteHitCallback=first;field.destroy();
  check(field.noteHitCallback==null,'teardown retained source closure');
 }
}
'''.replace("__SOURCE_AUTO__", admission).replace("__GET_NOTES__", get_notes)
        self.compile(fixture)


if __name__ == "__main__":
    unittest.main()
