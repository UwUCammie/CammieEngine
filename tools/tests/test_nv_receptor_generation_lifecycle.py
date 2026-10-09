"""Run the source generation lifecycle over real field/collection/signal adapters."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from nv_field_fixture_support import write_nv_field_dependencies
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]


class NvReceptorGenerationLifecycleTest(unittest.TestCase):
    def test_pinned_donor_order_and_ignored_cancellation(self):
        source = (ROOT.parent / 'fnf_sources/NightmareVision/source/funkin/states/PlayState.hx').read_text(encoding='utf-8')
        body = method(source, 'public function generatePlayfields()')
        anchors = ["if (generatedFields) return", "scripts.call('preReceptorGeneration', [strums, lane])",
                   'strums.generateReceptors()', 'strums.fadeIn(', 'strums.ID = lane', 'playFields.add(strums)',
                   'strums.showRatings = true', 'strums.noteSplashes = (lane == 0)', 'modManager.receptors =',
                   'generatedFields = true', "scripts.call('postReceptorGeneration')",
                   'modManager.registerEssentialModifiers()', 'modManager.registerScriptedModifiers()',
                   'modifiersRegistered = true', "scripts.call('postModifierRegister')"]
        positions = [body.index(anchor) for anchor in anchors]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('STOP_FUNC', body)
        self.assertIn('if (!genNotesBeforeCountdown) generatePlayfields();', method(source, 'public function startCountdown()'))

    def test_creation_countdown_and_empty_bank_integration(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        self.assertNotIn('buildNightmareVisionPlayFields', play)
        self.assertIn('genNotesBeforeCountdown = false;', method(method(play, 'function initializeNightmareVisionScripts()'), 'if (nightmareVisionLegacyFieldCameras) {'))
        eager = play[play.index("nightmareVisionScripts.loadScope('song');"):]
        self.assertLess(eager.index("callNightmareVision('preNoteGeneration', []);"), eager.index('if (genNotesBeforeCountdown) generatePlayfields();'))
        self.assertLess(eager.index('if (genNotesBeforeCountdown) generatePlayfields();'), eager.index('generateSong(SONG.song);'))
        countdown = method(play, 'public function startCountdown():Void')
        self.assertLess(countdown.index('if (sourceCountdownStopped)'), countdown.index('!genNotesBeforeCountdown) generatePlayfields();'))
        self.assertLess(countdown.index('!genNotesBeforeCountdown) generatePlayfields();'), countdown.index('startedCountdown = true;'))
        transitions = countdown[countdown.index("markStep('countdown:strum-transitions-begin')"):countdown.index("markStep('countdown:strum-transitions-complete')")]
        self.assertIn('if (nightmareVisionScripts == null)', transitions)
        generation = method(play, 'public function generatePlayfields():Void')
        order = ["callNightmareVision('postReceptorGeneration',", 'modManager.configureDimensions', 'modManager.registerEssentialModifiers()', 'modManager.registerDefaultModifiers()', 'modManager.registerScriptedModifiers()', 'modifiersRegistered = true', "callNightmareVision('postModifierRegister', [])"]
        indices = [generation.index(token) for token in order]
        self.assertEqual(indices, sorted(indices))
        self.assertIn('nightmareVisionDefaultGenerationDepth == 0', method(play, 'function syncNightmareVisionPlayFieldCollection('))
        self.assertIn('if (nightmareVisionScripts == null) {\n\t\t\tadd(enemyStrums);', play)
        self.assertIn('false, nightmareVisionScripts == null)', play)
        self.assertIn('arrowSkins = SONG.arrowSkins;', play)
        skin = method(play, 'function nightmareVisionDefaultSkinForField(field:Int')
        self.assertIn('var names = arrowSkins;', skin)
        self.assertNotIn('getFieldFromID', skin)
        constructor = method((ROOT / 'source/Strumline.hx').read_text(encoding='utf-8'), 'public function new(x:Float, y:Float, type:String')
        self.assertIn('?generateReceptors:Bool = true', constructor)
        self.assertIn('changeType(type, transition, false, generateReceptors)', constructor)
        self.assertIn('for (i in 0...(generateReceptors ? Note.NOTE_AMOUNT : 0))', (ROOT / 'source/Strumline.hx').read_text(encoding='utf-8'))

    def test_combo_break_feedback_waits_for_actual_receptor_geometry(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        methods = '\n'.join(method(play, sig) for sig in ['function comboBreakThingies(player:Int)', 'function syncNightmareVisionComboBreakGeometry(player:Int)', 'function comboBreak(dir:Int'])
        regeneration = method(play, 'function nightmareVisionGenerateFieldReceptors(')
        self.assertIn('if (field == getNightmareVisionField(0)) comboBreakThingies(1);', regeneration)
        self.assertIn('comboBreakThingies(1);', method(play, 'public function generatePlayfields():Void'))
        fixture = r'''
class FlxG {public static var height=720;}
class FlxColor {public static var WHITE=0xffffff;}
class Note {public static var NOTE_AMOUNT=4;}
class OptionsHandler {public static var options={showComboBreaks:true};}
class FlxTween {
 public static var shown=0;public static var cancelled=0;
 public static function cancelTweensOf(v:Dynamic):Void cancelled++;
 public static function tween(v:Dynamic,target:Dynamic,time:Float,options:Dynamic):Void shown++;
}
class FlxSprite {
 public var x:Float;public var width:Float=0;public var exists=true;public var visible=true;public var alpha=1.;public var color=0;public var destroyed=false;
 public function new(x:Float=0,y:Float=0)this.x=x;
 public function makeGraphic(w:Int,h:Int,c:Int):FlxSprite {width=w;color=c;return this;}
 public function destroy():Void destroyed=true;public function kill():Void {visible=false;exists=false;}
}
class Group {
 public var members:Array<FlxSprite>=[];public function new(){}
 public function add(s:FlxSprite):Void {var hole=members.indexOf(null);if(hole>=0)members[hole]=s;else members.push(s);}
 public function remove(s:FlxSprite,splice:Bool):Void members.remove(s);
 public function forEach(callback:FlxSprite->Void):Void for(s in members)callback(s);
}
typedef FeedbackField = {var members:Array<FlxSprite>;};
class Main {
 public var nightmareVisionScripts:Dynamic={};public var playerComboBreak:Group=new Group();public var enemyComboBreak:Group=new Group();
 public var fields:Map<Int,FeedbackField>=new Map();public var playerStrums:Dynamic={members:[]};
 public var missBreakColor=1;public var wayoffBreakColor=2;public var shitBreakColor=3;
 public function new(){}
 function getNightmareVisionField(id:Int):FeedbackField return fields.get(id);
 __METHODS__
 static function check(ok:Bool,label:String):Void if(!ok)throw label;
 static function main():Void {
  var h=new Main();h.comboBreakThingies(0);h.comboBreakThingies(1);h.comboBreak(0);h.comboBreak(0,false);
  check(h.playerComboBreak.members.length==0 && h.enemyComboBreak.members.length==0 && FlxTween.shown==0,'deferred or cancelled countdown has no receptor geometry yet');
  for(keys in [1,3]) {
   var receptors=[];for(i in 0...keys) {var r=new FlxSprite(100+i*90);r.width=70+i;receptors.push(r);}
   h.fields.set(0,{members:receptors});h.comboBreakThingies(1);
   check(h.playerComboBreak.members.length==keys,'feedback generated for actual key count');
   for(i in 0...keys) {var s=h.playerComboBreak.members[i];check(s.x==receptors[i].x && s.width==receptors[i].width && !s.visible,'per-key feedback uses actual geometry');h.comboBreak(i);check(s.visible && s.color==1,'user combo feedback remains functional');}
   var before=FlxTween.shown;h.comboBreak(keys);h.comboBreak(-1);check(FlxTween.shown==before,'unavailable source directions safely ignored');
   var old=h.playerComboBreak.members.copy();h.comboBreakThingies(1);for(s in old)check(s.destroyed,'regeneration disposes stale feedback and tweens');
  }
  var selected=h.fields.get(0);var previous=h.playerComboBreak.members.copy();
  selected.members=[];h.syncNightmareVisionComboBreakGeometry(1);check(h.playerComboBreak.members.length==0,'cleared source bank clears stale effects');
  selected.members=[new FlxSprite(500)];selected.members[0].width=80;h.syncNightmareVisionComboBreakGeometry(1);
  check(h.playerComboBreak.members.length==1 && h.playerComboBreak.members[0].x==500,'source receptors reappear with feedback');
  h.playerStrums={members:[new FlxSprite(999),new FlxSprite(777),new FlxSprite(666)]};selected.members[0].x=550;
  h.syncNightmareVisionComboBreakGeometry(1);check(h.playerComboBreak.members.length==1 && h.playerComboBreak.members[0].x==550,'selected source field determines geometry despite unrelated legacy alias');
  var retained=h.playerComboBreak.members[0];retained.visible=true;h.syncNightmareVisionComboBreakGeometry(1);
  check(h.playerComboBreak.members[0]==retained && retained.visible,'unchanged geometry preserves active feedback');
  selected.members.push(new FlxSprite(600));selected.members[1].width=90;h.comboBreak(1);
  check(h.playerComboBreak.members.length==2 && h.playerComboBreak.members[1].visible && h.playerComboBreak.members[1].width==90,'raw bank growth lazily restores functional effect');
  var left=new FlxSprite(100);left.width=70;var right=new FlxSprite(300);right.width=90;
  selected.members=[left,null,right];h.syncNightmareVisionComboBreakGeometry(1);
  check(h.playerComboBreak.members.length==3 && !h.playerComboBreak.members[1].exists,'null source direction retains inactive feedback slot');
  var slots=h.playerComboBreak.members.copy();var beforeHole=FlxTween.shown;
  h.comboBreak(1);check(FlxTween.shown==beforeHole && !slots[2].visible,'absent direction cannot flash the next receptor');
  h.comboBreak(2);check(slots[2].visible && slots[2].x==300 && slots[2].width==90,'later receptor keeps its direction');
  h.syncNightmareVisionComboBreakGeometry(1);for(i in 0...3)check(h.playerComboBreak.members[i]==slots[i],'unchanged null hole does not rebuild each update');
  var middle=new FlxSprite(200);middle.width=80;selected.members[1]=middle;h.comboBreak(1);
  check(h.playerComboBreak.members[1].exists && h.playerComboBreak.members[1].visible && h.playerComboBreak.members[1].x==200,'null direction replacement restores feedback');
  selected.members[1]=null;h.syncNightmareVisionComboBreakGeometry(1);check(!h.playerComboBreak.members[1].exists && !h.playerComboBreak.members[1].visible,'removed receptor retires its feedback');
  var absent=h.playerComboBreak.members[1];h.syncNightmareVisionComboBreakGeometry(1);check(h.playerComboBreak.members[1]==absent,'return to null stays stable');
  h.playerComboBreak.members[2]=null;h.syncNightmareVisionComboBreakGeometry(1);check(h.playerComboBreak.members[2]!=null && h.playerComboBreak.members[2].exists,'missing feedback slot repairs without direction truncation');
  h.fields.set(1,{members:[new FlxSprite(40)]});h.fields.get(1).members[0].width=66;h.comboBreakThingies(0);h.comboBreak(0,false,'shit');
  check(h.enemyComboBreak.members[0].x==40 && h.enemyComboBreak.members[0].width==66 && h.enemyComboBreak.members[0].color==3,'opponent feedback uses its own bank');
 }
}
'''.replace('__METHODS__', methods)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_deferred_camera_uses_the_donor_both_field_fallback(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        donor = (ROOT.parent / 'fnf_sources/NightmareVision/source/funkin/states/PlayState.hx').read_text(encoding='utf-8')
        local = method(play, 'public function moveCamera(isDad:Bool)')
        reference = method(donor, 'public function moveCamera(isDad:Bool)').replace('moveCamera(', 'referenceMoveCamera(', 1)
        fixture = r'''
class FlxPoint {public var x:Float;public var y:Float;public function new(x:Float=0,y:Float=0){this.x=x;this.y=y;}public function put():Void{}public function putWeak():Void{}}
class Character {public var x:Float;public function new(x:Float)this.x=x;public function getSingDisplacement():FlxPoint return new FlxPoint(5,7);}
class ClientPrefs {public static var camFollowsCharacters=false;}
class Field {public var owner:Character;public function new(owner:Character)this.owner=owner;}
class Target {public var x=0.;public var y=0.;public function new(){}public function setPosition(x:Float,y:Float):Void{this.x=x;this.y=y;}}
class Scripts {public var group:Scripts;public var whosTurn:String;public function new()group=this;public function set(key:String,value:String):Void whosTurn=value;}
class Main {
 public var nightmareVisionScripts:Scripts=new Scripts();public var scripts:Scripts;
 public var opponentStrums:Field;public var playerStrums:Field;
 public var dad:Character=new Character(10);public var boyfriend:Character=new Character(20);public var camCurTarget:Character;
 public var camFollow:Target=new Target();public function new(){scripts=nightmareVisionScripts;}
 function getNightmareVisionField(id:Int):Field return id==1?opponentStrums:playerStrums;
 function getCharacterCameraPos(actor:Character):FlxPoint return actor==null?new FlxPoint():new FlxPoint(actor.x,100);
 function setCameraFollowActor(actor:Character,label:String):Void camFollow.setPosition(actor.x,100);
 function applyNightmareVisionSingDisplacement(actor:Character):Void {if(actor!=null && ClientPrefs.camFollowsCharacters){var d=actor.getSingDisplacement();camFollow.x+=d.x;camFollow.y+=d.y;}}
 __LOCAL__
 __REFERENCE__
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var h=new Main();for(fields in [0,1,2,3])for(isDad in [false,true])for(displace in [false,true]) {
   h.opponentStrums=(fields&1)!=0?new Field(new Character(30)):null;
   h.playerStrums=(fields&2)!=0?new Field(new Character(40)):null;
   ClientPrefs.camFollowsCharacters=displace;h.moveCamera(isDad);var x=h.camFollow.x,y=h.camFollow.y;var turn=h.scripts.whosTurn;
   h.referenceMoveCamera(isDad);check(h.camFollow.x==x && h.camFollow.y==y && h.scripts.whosTurn==turn,'empty/single/full field camera matches pinned donor');
  }
  h.camCurTarget=new Character(50);h.opponentStrums=null;h.playerStrums=null;h.moveCamera(true);var x=h.camFollow.x;h.referenceMoveCamera(true);check(h.camFollow.x==x,'explicit camera target overrides deferred fallback');
  h.camCurTarget=null;ClientPrefs.camFollowsCharacters=false;h.opponentStrums=new Field(null);h.playerStrums=new Field(null);h.moveCamera(true);h.referenceMoveCamera(true);check(h.camFollow.x==0 && h.camFollow.y==0,'present null owner retains donor camera helper behavior');
 }
}
'''.replace('__LOCAL__', local).replace('__REFERENCE__', reference)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_executed_default_generation_mutations_publication_and_countdown(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        methods = '\n'.join(method(play, sig) for sig in [
            'public function generatePlayfields():Void', 'function generateNightmareVisionLegacyDefaultFields():Void', 'function createNightmareVisionDefaultField(lane:Int)',
            'function syncNightmareVisionPlayFieldCollection(', 'function publishNightmareVisionReceptorBanks():Void', 'function initializeNightmareVisionPlayFields():Void',
            'function nightmareVisionLaneCount():Int', 'function nightmareVisionKeyCount():Int', 'function nightmareVisionDefaultSkinForField(field:Int'])
        group_source = (ROOT / 'source/NightmareVisionScriptGroup.hx').read_text(encoding='utf-8')
        dispatch = method(group_source, 'public function call(event:String') + '\n' + method(group_source, 'public function callFiltered(').replace('NightmareVisionScriptModule', 'Module')
        countdown = method(play, 'public function startCountdown():Void')
        tail = countdown[countdown.index('var sourceCountdownStopped ='):countdown.index('\n\t\tif (duoMode)')]
        main = MAIN.replace('__METHODS__', methods).replace('__DISPATCH__', dispatch).replace('__COUNTDOWN__', tail)
        # Pure field-generation fixture isolates provider setup from its non-sprite bank stubs.
        main = main.replace('NightmareVisionSpriteMethods.bind', 'FixtureSpriteBinding.bind').replace('NightmareVisionSpriteRegistry.capture', 'FixtureSpriteBinding.capture')
        main += '\nclass FixtureSpriteBinding {public static function bind(object:Dynamic,owner:Dynamic):Void {} public static function capture(paths:Dynamic):Dynamic return null;}'
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            write_nv_field_dependencies(work)
            (work / 'NightmareVisionNoteSkin.hx').write_text('class NightmareVisionNoteSkin {public static function fromLegacyTexture(paths:Dynamic,texture:String,keys:Int,id:Int):NightmareVisionNoteSkin return new NightmareVisionNoteSkin(paths,texture,keys,id);public var name:String;public function new(path:Dynamic=null,name:String="custom",keys:Int=4,lane:Int=0)this.name=name;public function stringField(key:String,fallback:String):String return fallback;}', encoding='utf-8')
            (work / 'Main.hx').write_text(main, encoding='utf-8')
            (work / 'Strumline.hx').write_text(LINE, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work), '-main', 'Main', '--interp'], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('NV_RECEPTOR_LIFECYCLE_OK', result.stdout)


LINE = r'''
class Strumline {
 public var ID:Int=47;
 public var members:Array<StrumNote>=[];
 public var noteHoldCovers:Dynamic={cameras:[]};
 public var cameras:Array<Dynamic>=[];
 public var visible:Bool=true;
 public function new(x:Float,y:Float,type:String,transition:Bool=false,generate:Bool=true) { if(generate) make(4); }
 public function make(count:Int):Void { members.resize(0); for(i in 0...count)members.push(new StrumNote()); }
}
class StrumNote {
 public function new(){} public var resetAnim:Float=0;
 public function playAnim(name:String):Void {}
}
'''

MAIN = r'''
class Note {public static var NOTE_AMOUNT=4;public static var swagWidth=112.;}
class FlxG {public static var width=1280.;public static var height=720.;}
class RuntimeSmokeHarness {public static function markStep(label:String):Void {}}
class EngineCompat {public static function anyFunctionStop(values:Array<Dynamic>):Bool return values.indexOf(1)>=0;}
class Module {
 public var name='probe'; public var callback:(String,Array<Dynamic>)->Dynamic;
 public function new(callback:(String,Array<Dynamic>)->Dynamic) this.callback=callback;
 public function callValue(event:String,args:Array<Dynamic>):Dynamic return callback(event,args);
}
class Scripts {
 public static var CONTINUE_FUNC=0;public static var HALT_FUNC=2;
 public var released=false;public var members:Array<Module>=[];
 public function new(){}
 __DISPATCH__
}
class Main {
 function nightmareVisionLegacyGoodNoteHit(n:Dynamic,f:NightmareVisionPlayFieldView):Void {}
 function nightmareVisionLegacyOpponentNoteHit(n:Dynamic,f:NightmareVisionPlayFieldView):Void {}
 public var SONG:Dynamic={lanes:3,uiType:'normal'};
 public var nightmareVisionScripts:Scripts=new Scripts();
 public var nightmareVisionPrefs:Dynamic={view:{quants:false,opponentStrums:true,middleScroll:false}};
 public var modifiersRegistered=false;public var generatedFields=false;public var genNotesBeforeCountdown=true;public var skipArrowStartTween=false;
 public var nightmareVisionLegacyFieldCameras=false;
 public var nightmareVisionLegacyReceptors = new NightmareVisionLegacyReceptors();
 public var nightmareVisionDefaultGenerationDepth=0;
 public var skipCountdown=false;public var startOnTime=0.;public var isStoryMode=false;
 public var playerStrums:Strumline=new Strumline(0,0,'normal',false,false);
 public var enemyStrums:Strumline=new Strumline(0,0,'normal',false,false);
 public var strumLine:Dynamic={y:50};public var camHUD:Dynamic={};
 public var boyfriend:Dynamic={name:'bf'};public var dad:Dynamic={name:'dad'};public var cpuControlled=false;public var downscroll=false;
 public var nightmareVisionFields:Array<NightmareVisionPlayFieldView>=[];
 public var nightmareVisionStrumlines:Array<Strumline>=[];public var nightmareVisionOwnedStrumlines:Array<Strumline>=[];
 public var nightmareVisionOwnedFields:Array<NightmareVisionPlayFieldView>=[];
 public var playFields:NightmareVisionPlayFields;
 public var modManager:Dynamic={receptors:[],keys:4,lanes:3,
 configureDimensions:function(keys:Int,lanes:Int):Void {},
 registerEssentialModifiers:function():Void {},registerDefaultModifiers:function():Void {},registerScriptedModifiers:function():Void {}};
 public var events:Array<String>=[];public var display:Array<Strumline>=[];public var holdClaimUpdateCalls:Int=0;
 public var skin:NightmareVisionNoteSkin=new NightmareVisionNoteSkin();
 public var nightmareVisionPaths:Dynamic={root:"owner"};public var arrowSkins:Array<String>=["A","B","C"];
 public var nightmareVisionNoteSkins:Map<String,NightmareVisionNoteSkin>;
 public var psychMissingIntroRequest:Null<Int>=null;public var endingSong=false;public var accepted=false;
 public function new(){initializeNightmareVisionPlayFields();}
 function comboBreakThingies(player:Int):Void {}
 function psychVideoHandoff(serial:Int,a:Bool,b:Bool):Void {}
 function completeCountdown(countdownResults:Array<Dynamic>):Void {
  __COUNTDOWN__
  accepted=true;
 }
 function callNightmareVision(event:String,args:Array<Dynamic>):Dynamic return nightmareVisionScripts.call(event,args);

 function nightmareVisionSourceSkinRegistry():Dynamic return {noteskins:[]};
 function initializeNightmareVisionFieldSplashes(field:NightmareVisionPlayFieldView):Void {}
 function bindNightmareVisionPlayFieldLifecycle(f:NightmareVisionPlayFieldView):Void {
  nightmareVisionOwnedFields.push(f);
  f.bindNativeLifecycle({generateReceptors:function(field) {
   events.push('generate:'+field.player);field.strumline.make(field.keyCount);syncNightmareVisionPlayFieldCollection();
  },fadeIn:function(field,skip) events.push('fade:'+field.player+':'+skip),
  clearReceptors:function(field)field.strumline.members.resize(0)});
 }
 function nightmareVisionClearFieldReceptors(f:NightmareVisionPlayFieldView):Void f.clearReceptors();
 function attachNightmareVisionPlayField(f:NightmareVisionPlayFieldView):Void {events.push('add:'+f.ID);display.push(f.strumline);syncNightmareVisionPlayFieldCollection();}
 function detachNightmareVisionPlayField(f:NightmareVisionPlayFieldView):Void display.remove(f.strumline);
 function updateNightmareVisionHoldClaims():Void {holdClaimUpdateCalls++;}
 __METHODS__
 static function check(ok:Bool,msg:String):Void if(!ok)throw msg;
 static function main():Void {
  for(lanes in [1,3]) for(stop in [0,1,2]) {
   var h=new Main();h.SONG.lanes=lanes;h.skipCountdown=true;
   var oldBanks=h.modManager.receptors;
   var other=new NightmareVisionPlayFieldView(88,function()return false);other.strumline=new Strumline(0,0,'normal',false,false);
   h.playFields.add(other);oldBanks=h.modManager.receptors;
   h.events=[];var pre=0;var post=0;var later=0;
   h.nightmareVisionScripts.members.push(new Module(function(event,args) {
    if(event=='preReceptorGeneration') {
     var f:NightmareVisionPlayFieldView=args[0];var lane:Int=args[1];pre++;
     check(args.length==2 && f.members.length==0,'pre live empty payload');
     check(h.playFields.members.indexOf(f)<0 && h.display.indexOf(f.strumline)<0,'pre field not published');
     check(h.playFields.length==lane+1,'previous lanes published, custom field retained');
     check(h.modManager.receptors==oldBanks,'manager banks only published at end');
     check(f.owner==(lane==1?h.dad:h.boyfriend) && f.player==lane && f.isPlayer==(lane!=1),'constructor policy');
     check(!f.showRatings && !f.noteSplashes,'constructor flags before overwrite');
     check(f._skin.name==h.arrowSkins[lane],'default reads live arrowSkins rather than published custom field');
     f.ID=99;f.keyCount=3;f.owner=h.dad;f.playerControls=false;f.isPlayer=false;f._skin=h.skin;
     f.noteSplashes=true;h.events.push('pre:'+lane);return stop;
    }
    if(event=='postReceptorGeneration') {
     post++;check(args.length==0 && h.generatedFields,'post flag and empty payload');
     check(h.modManager.receptors.length==lanes+1 && h.modManager.receptors!=oldBanks,'post final bank table');
     for(i in 0...lanes) {
      var f=h.playFields.members[i+1];check(f.ID==i && f.showRatings && f.noteSplashes==(i==0),'post exact source overwrites');
      check(f.keyCount==3 && f.members.length==3 && f.owner==h.dad && !f.playerControls && !f.isPlayer && f._skin==h.skin,'authored retained mutations');
      check(h.modManager.receptors[i+1]==f.members,'live receptor identity');
     }
     h.generatePlayfields();h.events.push('post');
    }
    return 0;
   }));
   h.nightmareVisionScripts.members.push(new Module(function(event,args) {if(event=='preReceptorGeneration')later++;return 0;}));
   h.playFields.memberAdded.add(function(f) {
    if(f==other || h.nightmareVisionDefaultGenerationDepth==0)return;
    check(f.ID==pre-1 && !f.showRatings && f.noteSplashes,'add observer before overwrites');
    check(h.modManager.receptors==oldBanks,'memberAdded cannot see premature bank publication');
   });
   h.generatePlayfields();check(pre==lanes && post==1,'generation hooks once per lane and group');
   check(later==(stop==2?0:lanes),'HALT broadcast only, STOP continues');
   var expected=[];for(i in 0...lanes) {expected.push('pre:'+i);expected.push('generate:'+i);expected.push('fade:'+i+':true');expected.push('add:'+i);}expected.push('post');
   check(h.events.join('|')==expected.join('|'),'ordered actual lifecycle');
   h.generatePlayfields();check(pre==lanes && post==1,'idempotent repeat');
   check(h.enemyStrums.visible==(lanes!=1),'one lane hides unused alias');
   var replacement=new NightmareVisionPlayFieldView(10,function()return false);replacement.strumline=new Strumline(0,0,'normal');
   h.playFields.add(replacement);check(h.modManager.receptors.length==lanes+2,'ordinary live collection sync restored');
  }
  var recursive=new Main();recursive.SONG.lanes=1;var recurseOnce=false;var recursivePosts=0;
  recursive.nightmareVisionScripts.members.push(new Module(function(event,args) {
   if(event=='preReceptorGeneration' && !recurseOnce) {recurseOnce=true;recursive.generatePlayfields();}
   if(event=='postReceptorGeneration') {
    recursivePosts++;check(recursive.modManager.receptors.length==recursive.playFields.length,'each recursive completion publishes before post');
   }
   return 0;
  }));recursive.generatePlayfields();check(recursivePosts==2 && recursive.playFields.length==2 && recursive.nightmareVisionDefaultGenerationDepth==0,'finite source recursive generation is retained');
  check(recursive.holdClaimUpdateCalls>0,'field collection synchronization keeps hold-claim reconciliation observable');
  check(recursive.playFields.members[0].strumline!=recursive.playFields.members[1].strumline && recursive.playFields.members[0].members!=recursive.playFields.members[1].members,'recursive fields own distinct live banks');
  check(recursive.playFields.members[0]._skin!=recursive.playFields.members[1]._skin,'recursive fields own mutable skins');
  recursive.generatedFields=false;recursive.generatePlayfields();check(recursive.playFields.members[2].strumline!=recursive.playFields.members[1].strumline && recursive.playFields.members[2]._skin!=recursive.playFields.members[1]._skin,'explicit generation reset allocates distinct bank and skin');
  var changedSkin=new Main();changedSkin.arrowSkins=['replacement','B','C'];changedSkin.generatePlayfields();check(changedSkin.playFields.members[0]._skin.name=='replacement','source replaces public skin array before generation');
  var authored=new Main();authored.SONG.keys=3;authored.SONG.lanes=1;authored.generatePlayfields();
  check(authored.playFields.length==1 && authored.playFields.members[0].keyCount==3 && authored.playFields.members[0].members.length==3,'live source chart receptor dimensions');
  check(authored.modManager.keys==4 && authored.modManager.lanes==3,'manager registry dimensions remain an explicit separate contract');
  var ordinary=new Main();ordinary.generatePlayfields();check(ordinary.modManager.keys==4 && ordinary.modManager.lanes==ordinary.SONG.lanes,'unmodified manager and receptor dimensions agree');
  var delayed=new Main();delayed.genNotesBeforeCountdown=false;delayed.completeCountdown([1]);
  check(!delayed.generatedFields && delayed.playFields.length==0 && !delayed.accepted,'cancelled deferred countdown stays empty');
  delayed.completeCountdown([0]);check(delayed.generatedFields && delayed.accepted && delayed.playFields.length==3,'accepted deferred countdown generates');
  var native=new Main();native.nightmareVisionScripts=null;native.generatePlayfields();check(!native.generatedFields && native.playFields.length==0,'native and Psych generation untouched');
  var failed=new Main();failed.nightmareVisionScripts.members.push(new Module(function(event,args){if(event=='preReceptorGeneration')throw 'authored';return 0;}));
  var caught='';try failed.generatePlayfields() catch(e:Dynamic)caught=Std.string(e);
  check(caught=='authored' && !failed.generatedFields && failed.nightmareVisionDefaultGenerationDepth==0,'throw cleanup preserves error and pending flag');
  for(middle in [false,true]) for(shown in [false,true]) {
   var old=new Main();old.nightmareVisionLegacyFieldCameras=true;old.skipCountdown=true;
   old.nightmareVisionPrefs.view.middleScroll=middle;old.nightmareVisionPrefs.view.opponentStrums=shown;
   var preCalls=0,postCalls=0;var previousBanks=old.modManager.receptors;
   old.nightmareVisionScripts.members.push(new Module(function(event,args){
    if(event=='preReceptorGeneration') {
     preCalls++;old.events.push('legacy-pre');check(args.length==0,'historical single pre hook has no arguments');
     var p=old.nightmareVisionLegacyReceptors.player,o=old.nightmareVisionLegacyReceptors.opponent;
     check(p!=null&&o!=null&&p.members.length==0&&o.members.length==0&&old.playFields.length==0,'both empty captured fields before pre');
     check(o.baseAlpha==(!shown?0:middle?0.35:1),'opponent visibility set before authored pre');
     check(p.noteHitCallback!=null&&o.noteHitCallback!=null,'historical callbacks installed before source pre hook');
     o.noteHitCallback=null;
     var replaced=old.createNightmareVisionDefaultField(0);replaced.ID=9;replaced.keyCount=3;
     old.nightmareVisionLegacyReceptors.player=replaced;o.baseAlpha=0.7;
     return 1;
    }
    if(event=='postReceptorGeneration') {
     postCalls++;old.events.push('legacy-post');check(args.length==1&&args[0]==true,'historical post receives skip flag');
     var p=old.nightmareVisionLegacyReceptors.player,o=old.nightmareVisionLegacyReceptors.opponent;
     check(old.playFields.members[0]==o&&old.playFields.members[1]==p,'historical opponent/player display order');
     check(p.ID==9&&p.members.length==3&&o.members.length==4&&o.baseAlpha==0.7,'live pointer replacement and pre mutations retained');
     check(p.noteHitCallback==null&&o.noteHitCallback==null,'publication overwrote authored callback or invented one on replacement field');
     old.playFields.members.reverse();old.syncNightmareVisionPlayFieldCollection();
     check(old.modManager.receptors==previousBanks,'post callback still precedes modifier-bank publication');
    }
    if(event=='preModifierRegister') {
     old.events.push('legacy-modifiers');check(args.length==0&&postCalls==1,'pre modifier callback after post');
     check(old.modManager.receptors[0]==old.nightmareVisionLegacyReceptors.player.members&&old.modManager.receptors[1]==old.nightmareVisionLegacyReceptors.opponent.members,'modifier slots use player/opponent pointers despite order/ID changes');
    }
    return 0;
   }));
   old.generatePlayfields();check(preCalls==1&&postCalls==1&&old.nightmareVisionLaneCount()==2,'historical two fields and one hook pair');
   var order=['legacy-pre','generate:1','generate:0','fade:0:true','fade:1:true','add:1','add:9','legacy-post','legacy-modifiers'];
   var last=-1;for(e in order){var at=old.events.indexOf(e);check(at>last,'historical generation ordering '+e);last=at;}
   check(old.nightmareVisionDefaultGenerationDepth==0&&old.generatedFields&&old.modifiersRegistered,'historical lifecycle completed');
   old.generatePlayfields();check(preCalls==1,'historical repeated generation is idempotent');
  }
  var delayedOld=new Main();delayedOld.nightmareVisionLegacyFieldCameras=true;delayedOld.genNotesBeforeCountdown=false;
  delayedOld.completeCountdown([1]);check(!delayedOld.generatedFields&&delayedOld.playFields.length==0,'historical cancelled countdown does not generate fields');
  delayedOld.completeCountdown([0]);check(delayedOld.generatedFields&&delayedOld.playFields.length==2,'historical accepted countdown generates both fields');
  var failedOld=new Main();failedOld.nightmareVisionLegacyFieldCameras=true;
  failedOld.nightmareVisionScripts.members.push(new Module(function(event,args){if(event=='postReceptorGeneration')throw 'historical-post';return 0;}));
  caught='';try failedOld.generatePlayfields()catch(e:Dynamic)caught=Std.string(e);
  check(caught=='historical-post'&&failedOld.nightmareVisionDefaultGenerationDepth==0,'historical post throw releases publication guard');
  trace('NV_RECEPTOR_LIFECYCLE_OK');
 }
}
'''
