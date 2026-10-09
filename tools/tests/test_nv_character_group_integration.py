"""Actual group imports, captured construction and source scene caller boundaries."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from nv_character_group_fixture_support import nv_character_group_fixture_files
from test_source_attachment_integration import integration_files
from test_nv_multifield_routes import method

ROOT = Path(__file__).resolve().parents[2]

def connected_files():
    files = integration_files()
    files.update(nv_character_group_fixture_files())
    files['IconAnimation.hx'] = files['IconAnimation.hx'].replace('public var onFinish=', 'public var onLoop=new FlxTypedSignal<String->Void>();public var onFinish=')
    files['Character.hx'] = '''@:build(NightmareVisionSpriteMacro.build()) class Character extends flixel.FlxSprite {
 public var curCharacter:String;public var requestedCharacter:String;public var characterType:Dynamic;
 public var positionArray:Array<Float>=[3,5];public var danceEveryNumBeats=1;public var isPlayer=false;public var selectedRoot:String;
 public var holding:Bool=false;public var sourceActor:Bool=true;
 public function isNightmareVisionSourceActor():Bool return sourceActor;
 public function new(x=0.,y=0.,name="bf",player=false,?codename:Dynamic,?source:SourceCharacterConstruction){
  if(source!=null)source.requireActive();super(x,y);curCharacter=name;requestedCharacter=name;isPlayer=player;
  if(source!=null){selectedRoot=source.resolve(name).root;NightmareVisionSpriteMethods.bind(this,source.spriteOwner);}}
}'''
    files['NightmareVisionPaths.hx'] = '''class NightmareVisionPaths {public final root:String;public function new(r:String)root=r;
 public function getAtlasFrames(p:String):flixel.graphics.frames.FlxAtlasFrames return new flixel.graphics.frames.FlxAtlasFrames();}'''
    files['ImportEngine.hx'] = 'class ImportEngine {public static inline var NIGHTMARE_VISION="Nightmare Vision";}'
    files['Song.hx'] = '''class Song {public static var reads:Array<String>=[];public static var current="other-owner";
 public static function resolveCharacterVisualInManifest(name:String,root:String,nativeFallback:Bool,engine:String):Dynamic {reads.push(root+":"+name);return {root:root,name:name,complete:true};}}'''
    files['NightmareVisionPlayFieldView.hx'] = '''class NightmareVisionPlayFieldView {
 public var ID:Int;public var owner:Character;public var singers:Array<Character>=[];
 public var inControl:Bool=false;public var playerControls:Bool=false;public var autoPlayed:Bool=false;
 public function new(id:Int,c:Character){ID=id;owner=c;}
}'''
    files['SourceCharacterHoldLedger.hx'] = (ROOT / 'source/SourceCharacterHoldLedger.hx').read_text(encoding='utf-8')
    files['HoldInputFixture.hx'] = '''class HoldInputFixture {
 public var pressedActions:Array<Bool>;
 public function new(actions:Array<Bool>) pressedActions=actions;
 public function inputPressed(key:Int):Bool return key>=0 && key<pressedActions.length && pressedActions[key];
}'''
    files['HoldScopeFixture.hx'] = '''class HoldScopeFixture {
 public var ownerRoot:String;public var input:HoldInputFixture;
 public function new(owner:String,actions:Array<Bool>){ownerRoot=owner;input=new HoldInputFixture(actions);}
}'''
    return files

class NVCharacterGroupIntegrationTest(unittest.TestCase):
    def run_haxe(self, files, cpp=True):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            work = Path(folder)
            for name, content in files.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding='utf-8')
            env = os.environ.copy()
            env.update(HAXEPATH=str(ROOT / '.tools/haxe'), NEKOPATH=str(ROOT / '.tools/neko'), HAXELIB_PATH=str(ROOT / '.haxelib'))
            env['PATH'] = os.pathsep.join((env['HAXEPATH'], env['NEKOPATH'], env.get('PATH', '')))
            command = [*HAXE_COMMAND, '-D', 'flixel', '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'), '-cp', folder, '-main', 'Main']
            for target in ([['--interp'], ['-cpp', str(work / 'cpp'), '-D', 'no-compilation']] if cpp else [['--interp']]):
                result = subprocess.run(command + target, cwd=ROOT, env=env, capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-5000:])

    def test_actual_iris_group_factory_captured_roots_and_plain_parent(self):
        files = connected_files()
        files['Main.hx'] = r'''
class Main {static function ok(value:Bool,message:String):Void if(!value)throw message;
 static function main(){
  NightmareVisionSpriteRegistry.enterSession('a');var pa=new NightmareVisionPaths('a');var pb=new NightmareVisionPaths('b');
  NightmareVisionSpriteRegistry.setup(pa);NightmareVisionSpriteRegistry.setup(pb);
  var scene=new PlayState();var role=new Character(0,0,'old');scene.playFields.members=[new NightmareVisionPlayFieldView(0,role)];
  var a=new NightmareVisionScriptInterp(scene);var b=new NightmareVisionScriptInterp();
  var live=function()return {gfPosition:scene.gfPosition,playFields:scene.playFields};
  NightmareVisionCharacterGroupBindings.install(a,pa,live);NightmareVisionCharacterGroupBindings.install(b,pb,live);
  var parser=new NightmareVisionScriptParser();
  a.execute(parser.parseString("import funkin.objects.CharacterGroup;import funkin.objects.CharacterGroup.CharacterType;import funkin.objects.Character;import flixel.group.FlxSpriteGroup;import Type;import Reflect;group=new CharacterGroup(10,20,CharacterType.BF);actor=new Character(0,0,'one',true);group.addChar(actor);group.parent=actor;type=Type.resolveClass('funkin.objects.CharacterGroup');again=Type.createInstance(type,[7,8,CharacterType.DAD]);name=Type.getClassName(Type.getClass(again));other=group.addToList('two');"));
  var group:NightmareVisionCharacterGroup=cast a.variables.get('group');var actor:Character=cast a.variables.get('actor');var cached:Character=cast a.variables.get('other');
  ok(Std.isOfType(group,flixel.group.FlxSpriteGroup)&&a.variables.get('type')==NightmareVisionCharacterGroup&&a.variables.get('name')=='funkin.objects.CharacterGroup','actual group identity, canonical class and Type constructor');
  ok(actor.x==13&&actor.y==25&&actor.selectedRoot=='a'&&cached.selectedRoot=='a'&&cached.isPlayer,'captured owner and relative placement once');
  ok(group.parent==actor&&scene.playFields.members[0].owner==role,'plain parent assignment has no field or game activation');
  b.execute(parser.parseString("import funkin.objects.CharacterGroup;group=new CharacterGroup(0,0,1);child=group.addToList('one');"));
  ok((cast b.variables.get('child'):Character).selectedRoot=='b'&&Song.current=='other-owner','distinct source owner without global swap');
  var replacement=new NightmareVisionCharacterGroup(0,0,cast 0,NightmareVisionCharacterGroupBindings.owner(pa,live));
  a.variables.set('replacement',replacement);a.execute(parser.parseString("group=replacement;group.parent=null;"));
  ok(group.members.length==2&&group.parent==actor&&replacement.members.length==0,'replacing a public pointer never reconciles old container');
  var count=Song.reads.length;NightmareVisionSpriteRegistry.enterSession('new-owner');var failed=false;
  try group.addToList('stale')catch(error:Dynamic)failed=Std.string(error).indexOf('released')>=0;
  ok(failed&&Song.reads.length==count,'released capture rejected before definition/resolution IO');
  group.destroy();replacement.destroy();(cast b.variables.get('group'):NightmareVisionCharacterGroup).destroy();a.release();b.release();
 }
}'''
        self.run_haxe(files)

    def test_actual_nv_switch_bridge_retains_hidden_cache_or_destroys_explicitly(self):
        files = connected_files()
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        switch = method(play, 'public function switchToChar(')
        begin = switch.index("if (charState == 'bf'")
        end = switch.index('var previousStageActor:', begin)
        branch = switch[begin:end]
        hold_methods = '\n'.join(method(play, signature) for signature in (
            'function nightmareVisionHoldRoleGroup(',
            'function nightmareVisionGroupContainsActor(',
            'function releaseNightmareVisionHoldActors(',
            'function updateNightmareVisionHoldClaims(',
        ))
        files['PsychCharacterChangeEvent.hx'] = 'class PsychCharacterChangeEvent {public static function role(s:String):Int return s=="boyfriend"?0:s=="gf"?2:1;}'
        files['Bridge.hx'] = 'import SourceCharacterHoldLedger.SourceCharacterHoldClaim;\n' + '''class Bridge {
 public var nightmareVisionScripts:Dynamic={};public var nightmareVisionFields:Array<NightmareVisionPlayFieldView>=[];
 public var boyfriend:Character;public var dad:Character;public var gf:Character;public var hud=0;
 public var group:NightmareVisionCharacterGroup;public var boyfriendGroup:NightmareVisionCharacterGroup;
 public var dadGroup:NightmareVisionCharacterGroup;public var gfGroup:NightmareVisionCharacterGroup;
 public var nightmareVisionRoleGroups:Array<NightmareVisionCharacterGroup>=[];
 public var nightmareVisionHoldLedger:SourceCharacterHoldLedger=new SourceCharacterHoldLedger();
 public var nightmareVisionInputScope:HoldScopeFixture;public var inCutscene:Bool=false;public var SONG:Dynamic;
 public function new(g:NightmareVisionCharacterGroup){group=g;boyfriendGroup=g;}
 function nightmareVisionCharacterGroup(type:Int):NightmareVisionCharacterGroup return group;
 function refreshCharacterHUD():Void hud++;
''' + hold_methods + '''
 public function swap(daCharacter:Character,charState:String,destroy=false):Void {''' + branch + '}}'
        files['Main.hx'] = '''class Main {static function ok(b:Bool,s:String)if(!b)throw s;static function main(){
 var paths=new NightmareVisionPaths("a");NightmareVisionSpriteRegistry.enterSession("a");NightmareVisionSpriteRegistry.setup(paths);
 var group=new NightmareVisionCharacterGroup(10,20,cast 0,NightmareVisionCharacterGroupBindings.owner(paths,function()return null));
 var old=new Character(0,0,"old");group.addChar(old);group.parent=old;old.alpha=.6;
 var bridge=new Bridge(group);bridge.boyfriend=old;var field=new NightmareVisionPlayFieldView(0,old);field.inControl=true;field.playerControls=true;bridge.nightmareVisionFields=[field];
 bridge.nightmareVisionInputScope=new HoldScopeFixture("a",[true]);
 bridge.nightmareVisionHoldLedger.retain("a",field,group,old,false);old.holding=true;
 var next=new Character(0,0,"next");bridge.swap(next,"bf");ok(old.alpha==.0001&&next.alpha==.6&&old.destroyed==0,"retained old cache hidden with alpha transfer");
 ok(!old.holding&&!bridge.nightmareVisionHoldLedger.hasActorClaim(old),"hidden cached actor releases its hold when role ownership moves to the replacement");
 ok(group.members.length==2&&bridge.boyfriend==next&&group.parent==next&&field.owner==next&&bridge.hud==1,"group owns members once and host caller publishes role fields HUD");
 var third=new Character(0,0,"third");bridge.nightmareVisionHoldLedger.retain("a",field,group,next,false);next.holding=true;bridge.swap(third,"boyfriend",true);ok(next.destroyed==1&&group.members.indexOf(next)<0&&third.alpha==.6,"explicit destroy removes then destroys once");
 ok(!next.holding&&!bridge.nightmareVisionHoldLedger.hasActorClaim(next),"destroyed role actor is released and its lease is removed");
 bridge.swap(third,"bf");ok(third.alpha==.6&&third.destroyed==0&&group.members.length==2,"same actor not hidden or duplicated");group.destroy();ok(old.destroyed==1&&third.destroyed==1&&next.destroyed==1,"native group sole final destruction");}}
'''
        self.run_haxe(files)

    def test_actual_live_group_alias_bindings_preserve_replacements_and_null(self):
        files = connected_files()
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        bindings = '\n'.join(line.strip() for line in method(source, 'function seedNightmareVision(').splitlines()
                             if "interp.bindLiveValue('" in line and any("'" + role + "Group'" in line for role in ['boyfriend', 'dad', 'gf']))
        files['AliasHost.hx'] = '''class AliasHost {
 public var boyfriendGroup:NightmareVisionCharacterGroup;public var dadGroup:NightmareVisionCharacterGroup;public var gfGroup:NightmareVisionCharacterGroup;
 public var boyfriendPosition=new flixel.math.FlxPoint(770,100);
 public function new(){}public function bind(interp:NightmareVisionScriptInterp):Void {''' + bindings + '}}'
        files['Main.hx'] = '''class Main {static function ok(b:Bool,s:String)if(!b)throw s;static function main(){
 var host=new AliasHost();var original=new NightmareVisionCharacterGroup(1,2,cast 0);host.boyfriendGroup=original;
 var interp=new NightmareVisionScriptInterp(host);host.bind(interp);var paths=new NightmareVisionPaths("a");NightmareVisionSpriteRegistry.enterSession("a");NightmareVisionSpriteRegistry.setup(paths);
 NightmareVisionCharacterGroupBindings.install(interp,paths,function()return null);interp.variables.set("game",host);
 var parser=new NightmareVisionScriptParser();interp.execute(parser.parseString("import Reflect;game.boyfriendGroup=null;bareNull=boyfriendGroup;boyfriendGroup=new CharacterGroup(3,4,0);replacement=game.boyfriendGroup;reflected=Reflect.getProperty(game,'boyfriendGroup');point=boyfriendPosition;"));
 ok(interp.variables.get("bareNull")==null&&host.boyfriendGroup!=original&&interp.variables.get("replacement")==host.boyfriendGroup&&interp.variables.get("reflected")==host.boyfriendGroup,"bare/game/reflected aliases stay live with authored null and replacements");
 ok(original.members.length==0&&original.parent==null&&interp.variables.get("point")==host.boyfriendPosition,"public position identity and old container remain independent");
 original.destroy();host.boyfriendGroup.destroy();interp.release();}}
'''
        self.run_haxe(files)

    def test_scene_initialization_aliases_and_native_boundaries(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        init = method(source, 'function initializeNightmareVisionScripts(')
        self.assertLess(init.index('initializeNightmareVisionCharacterGroups();'), init.index("NightmareVisionStageScene.load(stage, nightmareVisionScripts.group)"))
        self.assertLess(init.index("onAddSpriteGroups"), init.index('NightmareVisionStageScene.mount(this, stage, [gfGroup, dadGroup, boyfriendGroup])'))
        self.assertLess(init.index('NightmareVisionStageScene.mount(this, stage, [gfGroup, dadGroup, boyfriendGroup])'), init.index("nightmareVisionScripts.loadScope('global')"))
        self.assertNotIn('nightmareVisionCharacterBank', source)
        self.assertNotIn('NightmareVisionCharacterGroupCompat', source)
        initial = source[source.index('initializeNightmareVisionScripts();', source.index('daScrollSpeed =')):]
        self.assertLess(initial.index('gfGroup.parent = gf'), initial.index('loadNightmareVisionCharacter(gf)'))
        for actor in ['dad', 'boyfriend']:
            self.assertLess(initial.index('loadNightmareVisionCharacter(' + actor + ')'), initial.index(actor + 'Group.addChar(' + actor + ')'))
        self.assertIn('if (nightmareVisionScripts == null && nightmareVisionAddActors)', initial)
        preload = method(source, 'function addNightmareVisionCharacterToList(')
        self.assertLess(preload.index('group.addToList(name)'), preload.index('loadNightmareVisionCharacter(actor)'))
        self.assertIn("loadScope('character', actor.curCharacter, actor)", method(source, 'function loadNightmareVisionCharacter('))
        seed = method(source, 'function seedNightmareVision(')
        for role in ['boyfriend', 'dad', 'gf']:
            self.assertIn("bindLiveValue('" + role + "Group'", seed)
        character = (ROOT / 'source/Character.hx').read_text(encoding='utf-8')
        constructor = method(character, 'public function new(x:Float, y:Float')
        self.assertLess(constructor.index('sourceConstruction.requireActive()'), constructor.index('super(x, y)'))
        self.assertIn('sourceConstruction == null ? Song.currentPsychCharacterRoot() : sourceConstruction.root', constructor)

if __name__ == '__main__':
    unittest.main()
