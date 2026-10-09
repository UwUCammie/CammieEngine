"""Execute NV views with real Flixel signals and compare group mutations to source."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method
from nv_field_fixture_support import write_nv_field_sprite_stubs

ROOT = Path(__file__).resolve().parents[2]
FLIXEL = ROOT / '.haxelib/flixel/6,1,2'


class NvFieldMutationContractTest(unittest.TestCase):
    def compile(self, fixture):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'flixel/util').mkdir(parents=True)
            (work / 'flixel/util/FlxSignal.hx').write_text((FLIXEL / 'flixel/util/FlxSignal.hx').read_text(), newline='\n')
            (work / 'flixel/util/FlxDestroyUtil.hx').write_text('package flixel.util; class FlxDestroyUtil {public static function destroyArray<T:IFlxDestroyable>(items:Array<T>):Array<T> {if(items!=null){for(item in items)if(item!=null)item.destroy();items.resize(0);}return null;}} interface IFlxDestroyable {public function destroy():Void;}', newline='\n')
            write_nv_field_sprite_stubs(work)
            (work / 'Strumline.hx').write_text('''class Strumline {
 public var members:Array<StrumNote>=[];public var destroys:Int=0;
 public function new() {for(i in 0...3)members.push(new StrumNote(i));}
 public function destroy():Void destroys++;
}
class StrumNote {
 public var ID:Int;public var resetAnim:Float=1;public var name:String='confirm';
 public var calls:Int=0;
 public function new(id:Int)ID=id;
 public function playAnim(anim:String):Void {name=anim;calls++;}
}''', newline='\n')
            (work / 'NightmareVisionNoteSkin.hx').write_text('class NightmareVisionNoteSkin {public function new() {}}', newline='\n')
            (work / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory,
                                     '-main', 'Main', '-dce', 'full', '--interp'], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_collection_operations_match_real_group_members_results_and_signal_order(self):
        source = (FLIXEL / 'flixel/group/FlxGroup.hx').read_text()
        methods = '\n'.join(method(source, 'public function ' + name + '(') for name in ['add', 'insert', 'remove', 'replace', 'clear'])
        methods = methods.replace(':T', ':NightmareVisionPlayFieldView')
        fixture = r'''
class FlxG {public static var log={warn:function(message:String):Void {}};}
class FlxArrayUtil {public static function clearArray<T>(items:Array<T>):Void items.resize(0);}
class SourceGroup {
 public var members:Array<NightmareVisionPlayFieldView>=[];
 public var length:Int=0;public var maxSize:Int=0;
 public var events:Array<String>=[];
 var _memberRemoved:Bool=true;
 public function new() {}
 function getFirstNull():Int return members.indexOf(null);
 function onMemberAdd(field:NightmareVisionPlayFieldView):Void events.push('add:'+label(field)+':'+length+':'+snapshot());
 function onMemberRemove(field:NightmareVisionPlayFieldView):Void events.push('remove:'+label(field)+':'+length+':'+snapshot());
 function snapshot():String return [for(field in members)label(field)].join(',');
 function label(field:NightmareVisionPlayFieldView):String return field==null?'null':Std.string(field.ID);
 __GROUP_METHODS__
}
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function label(field:NightmareVisionPlayFieldView):String return field==null?'null':Std.string(field.ID);
 static function signature(members:Array<NightmareVisionPlayFieldView>):String return [for(field in members)label(field)].join(',');
 static function main() {
  var attached:Array<NightmareVisionPlayFieldView>=[];var changes=0;
  var actual=new NightmareVisionPlayFields(function(field) {if(!attached.contains(field))attached.push(field);},
   function(field)attached.remove(field),function()changes++);
  var source=new SourceGroup();var events:Array<String>=[];
  actual.memberAdded.add(function(field)events.push('add:'+label(field)+':'+actual.length+':'+signature(actual.members)));
  actual.memberRemoved.add(function(field)events.push('remove:'+label(field)+':'+actual.length+':'+signature(actual.members)));
  var a=new NightmareVisionPlayFieldView(0,function()return false);
  var b=new NightmareVisionPlayFieldView(1,function()return true);
  var c=new NightmareVisionPlayFieldView(2,function()return true);
  var d=new NightmareVisionPlayFieldView(3,function()return true);
  var compare=function() {
   check(signature(actual.members)==signature(source.members),'member/hole ordering differs from FlxTypedGroup');
   check(actual.length==source.length,'collection length differs');
   check(events.join(',')==source.events.join(','),'member signal ordering differs');
  };
  check(actual.add(null)==source.add(null),'null addition');compare();
  actual.add(a);source.add(a);compare();
  actual.add(b);source.add(b);compare();
  var before=changes;actual.add(a);source.add(a);compare();check(changes==before,'duplicate add invokes native hooks');
  actual.remove(a);source.remove(a);compare();check(actual.length==2&&actual.members[0]==null,'remove preserves hole');
  actual.add(c);source.add(c);compare();check(actual.members[0]==c,'add reuses first null hole');
  actual.insert(1,a);source.insert(1,a);compare();
  actual.remove(a,true);source.remove(a,true);compare();
  actual.remove(c);source.remove(c);compare();
  actual.insert(0,d);source.insert(0,d);compare();
  actual.replace(d,c);source.replace(d,c);compare();
  actual.replace(c,b);source.replace(c,b);compare(); // Donor replace allows a duplicate replacement.
  check(actual.replace(a,c)==source.replace(a,c),'absent replacement result');compare();
  var array=actual.members;actual.clear();source.clear();compare();
  check(actual.members==array&&actual.length==0&&attached.length==0,'clear preserves array identity and detaches without disposal');
  actual.members.push(a);source.members.push(a);compare();check(actual.length==0,'raw array append must not invent a logical group addition');
  actual.add(b);source.add(b);compare();actual.clear();source.clear();compare();
  actual.add(c);source.add(c);c.ID=7;
  check(actual.getFieldFromID(7)==c&&actual.getFieldFromID(0)==c&&actual.getFieldFromID(-1)==null,'mutable ID lookup/fallback');
  actual.destroy();check(actual.members.length==0,'collection teardown clears references');
 }
}
'''.replace('__GROUP_METHODS__', methods)
        self.compile(fixture)

    def test_field_control_notes_real_signals_hook_order_and_facade_teardown(self):
        fixture = r'''
class Main {
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function note(direction:Int,sustain:Bool):Dynamic return {
  noteData:direction,isSustainNote:sustain,alive:true,exists:true,wasGoodHit:false,tooLate:false,canBeHit:true
 };
 static function main() {
  var auto=false;var field=new NightmareVisionPlayFieldView(2,function()return auto);
  var line=new Strumline();field.strumline=line;var events:Array<String>=[];
  var generated=0;var cleared=0;var disposed=0;var skins=0;var faded=false;var alpha:Float=1;var quant=false;
  field.bindNativeLifecycle({
   generateReceptors:function(f) {generated++;check(f.keyCount==5,'setter stores key count before generation');},
   clearReceptors:function(f) {cleared++;f.strumline.members.resize(0);},
   addNote:function(f,n) {events.push('attach');Reflect.setField(n,'playField',f);},
   removeNote:function(f,n) {events.push('detach');Reflect.setField(n,'playField',null);},
   detachNote:function(f,n) {events.push('detach-only');Reflect.setField(n,'playField',null);},
   disposeNote:function(f,n) {disposed++;n.alive=false;Reflect.setField(n,'playField',null);},
   hit:function(n,f)events.push('native-hit'),miss:function(n,f)events.push('native-miss'),
   missPress:function(key)events.push('native-press:'+key),
   alpha:function(f,value)alpha=value,quants:function(f,value)quant=value,
   changeSkin:function(f,skin) {skins++;check(f._skin==skin&&f.hasChangedSkin,'skin metadata before native reload');},
   fadeIn:function(f,skip)faded=skip
  });
  field.onNoteHit.add(function(n,f)events.push('script-hit'));
  field.onNoteMiss.add(function(n,f)events.push('script-miss'));
  field.onMissPress.add(function(key)events.push('script-press:'+key));
  field.inControl=false;
  for(strum in line.members)check(strum.name=='static'&&strum.resetAnim==0&&strum.calls==1,'inControl false must reset every receptor');
  field.inControl=true;check(field.canInput(),'manual control recovered');
  field.owner={stunned:true};check(!field.canInput(),'owner stunned');
  field.owner=null;check(field.singers[0]==null&&field.singers.length==2,'donor null owner singer semantics');
  auto=true;check(!field.canInput(),'default autoplay live');field.autoPlayed=false;check(field.canInput(),'explicit autoplay override');
  field.keyCount=5;check(generated==1,'key count regenerates existing receptors');
  field.alpha=2;check(field.alpha==1&&alpha==1,'bounded source alpha');field.alpha=-1;check(alpha==0,'lower alpha bound');
  field.quants=true;check(quant,'quant hook');field.changeSkin(new NightmareVisionNoteSkin());check(skins==1,'skin hook');
  field.fadeIn(true);check(faded,'fade hook');
  var tap=note(1,false),hold=note(1,true),late=note(1,false),dead=note(1,false),wrong=note(0,false);
  late.tooLate=true;dead.alive=false;
  for(n in [tap,hold,late,dead,wrong])field.addNote(n);
  check(field.getNotes(1).length==2&&field.getTapNotes(1)[0]==tap&&field.getHoldNotes(1)[0]==hold,'eligible note queries');
  check(field.getNotes(1,function(n)return n.isSustainNote).length==1,'optional note query predicate');
  var alive=0;field.forEachAliveNote(function(n)alive++);check(alive==4,'alive note iteration');
  events=[];field.onNoteHit.dispatch(tap,field);field.onNoteMiss.dispatch(tap,field);field.onMissPress.dispatch(1);
  check(events.join(',')=='native-hit,script-hit,native-miss,script-miss,native-press:1,script-press:1','donor-first effect listener ordering');
  var once=0;var onceListener=function(n:Dynamic,f:NightmareVisionPlayFieldView)once++;
  var addOnce=Reflect.field(field.onNoteHit,'addOnce');check(addOnce!=null,'reflective signal addOnce retained');
  Reflect.callMethod(field.onNoteHit,addOnce,[onceListener]);
  field.onNoteHit.dispatch(tap,field);field.onNoteHit.dispatch(tap,field);
  check(once==1,'real source signal once/removal behavior');
  field.removeNote(tap);check(!field.notes.contains(tap)&&tap.playField==null,'native/global detach hook');
  field.addNote(tap);field.removeNote(tap,false);check(events[events.length-1]=='detach-only'&&!field.notes.contains(tap),'retirement detaches membership without another host removal');
  field.disposeNote(hold);check(disposed==1&&!hold.alive&&!field.notes.contains(hold),'dispose hook owns note kill/unlink');
  field.clearReceptors();check(cleared==1&&line.members.length==0,'receptor clear hook');
  field.keyCount=4;check(generated==1,'empty bank key count setter should not regenerate');
  field.destroy();field.destroy();
  check(line.destroys==0&&field.notes.length==0&&field.singers.length==0&&field.strumline==null&&!field.canInput(),'facade teardown must release references without destroying bank');
  var unbound=new NightmareVisionPlayFieldView(0,function()return false);var diagnosed=false;
  try unbound.generateReceptors() catch(error:Dynamic)diagnosed=Std.string(error).indexOf('Unbound native lifecycle')>=0;
  check(diagnosed,'missing lifecycle implementation must produce diagnostic');
 }
}
'''
        self.compile(fixture)


if __name__ == '__main__':
    unittest.main()
