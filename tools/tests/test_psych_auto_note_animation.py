"""Actual automatic-hit blocks respect live per-note animation suppression."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_source_gameplay_lifecycle import extract_method

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT.parent / 'fnf_sources/FNF-PsychEngine/source/states/PlayState.hx'


class PsychAutoNoteAnimationTest(unittest.TestCase):
    def test_extracted_auto_routes_keep_custom_callbacks_effects_and_retirement(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        note = (ROOT / 'source/Note.hx').read_text(encoding='utf-8')
        opponent = extract_method(play, 'if (!sourceScoreNightmare && !daNote.mustPress && daNote.wasGoodHit')
        player = extract_method(play, 'if (!sourceScoreNightmare && daNote.mustPress && daNote.wasGoodHit')
        allows = extract_method(note, 'public function allowsAnimation(')
        number_array = extract_method((ROOT / 'source/CoolUtil.hx').read_text(encoding='utf-8'), 'public static function numberArray(')
        fixture = r'''using StringTools;
class CoolUtil { __NUMBER_ARRAY__ }
class Note {
 public static var NOTE_AMOUNT=4;public var noteData=0;public var noAnimation=false;public var noMissAnimation=false;
 public var noteType='Delegated';public var isSustainNote=false;public var mustPress=false;public var wasGoodHit=true;
 public var nightmareVisionHitDispatched=false;public var psychHitDispatched=false;public var codenameHitDispatched=false;
 public var codenameInputLine:Dynamic=null;public var ignoreNote=false;public var hitCausesMiss=false;
 public var forceGfSing=false;public var altNote=false;public var altNum=0;public var aiShouldHit=false;public var shouldBeSung=true;
 public var oppntSing:Dynamic=null;public var dontStrum=false;public var noteHit:Dynamic=null;public var killed=false;public var destroyed=false;
 public function new(){}public function isAutoPlayed():Bool return true;
 public function kill():Void killed=true;public function destroy():Void destroyed=true;
 __ALLOWS__
}
class Character {
 public var altAnim='';public var altNum=0;public var holdTimer=2.;public var anim='idle';public var sings=0;
 public function new(){}public function sing(n:Int,m:Bool,a:Int):Void {anim='singLEFT';sings++;}
 public function playAnim(n:String,f:Bool):Void {anim=n;sings++;}
 public static function animationName(c:Character):String return c.anim;
}
class Notes {public var members:Array<Note>=[];public function new(){}public function remove(n:Note,s:Bool):Void members.remove(n);}
class Strums {public var receptor=new Strumline.StrumNote();public function new(){}public function forEachReceptor(f:Strumline.StrumNote->Void):Void f(receptor);}
class Host {
 public var sourceScoreNightmare=false;public var nightmareVisionScripts:Dynamic=null;public var opponentPlayer=true;public var demoMode=true;
 public var SONG:Dynamic={notes:[null],needsVoices:true};public var curSection=0;public var camZooming=false;
 public var gf:Character=null;public var dad=new Character();public var boyfriend=new Character();public var extra=new Character();
 public var currentKey:Dynamic={getSing:function(n:Int):String return 'singLEFT'};
 public var enemyStrums=new Strums();public var playerStrums=new Strums();public var notes=new Notes();public var lua=new LuaCompatInterp();
 public var postCalls=0;public var clips=0;public var lifetimes=0;public var vocals=0;public var crossfades=0;
 public function new(){
  lua.variables.set('Std',Std);lua.variables.set('makeRangeArray',CoolUtil.numberArray);
  lua.variables.set('getProperty',function(p:String):Dynamic return p=='unspawnNotes.length'?notes.members.length:null);
  lua.variables.set('getPropertyFromGroup',function(g:String,i:Int,p:String):Dynamic return Reflect.getProperty(notes.members[i],p));
  lua.variables.set('setPropertyFromGroup',function(g:String,i:Int,p:String,v:Dynamic):Void Reflect.setProperty(notes.members[i],p,v));
  lua.variables.set('setProperty',function(p:String,v:Dynamic):Void {if(p=='extra.anim')extra.anim=v;});
 }
 function sourceScoreLedgerActive():Bool return true;function dispatchHxcAutoNoteHit(n:Note,p:Bool):Bool return true;
 function hitCodenameNote(n:Note,p:Bool):Void{}function updatePsychNoteLifetime(n:Note):Void lifetimes++;
 function nightmareVisionFieldForNote(n:Note):Dynamic return {playerControls:false};function scoreSourceAutoNote(n:Note,p:Bool):Void{}
 function applyDemoHealth(n:Note):Void{}function dispatchHitCausesMiss(n:Note,p:Bool):Void{}function finishGoodNoteHit(n:Note,p:Bool,e:Dynamic,r:Bool):Void{}
 function getOpponentSinger():Character return dad;function noteSingerForSide(n:Note,p:Bool):Character return boyfriend;
 function callAllHScript(n:String,a:Array<Dynamic>):Void{}function callCutsceneOpponentSing():Void{}
 function singCodenameNoteActors(n:Note,l:Int,p:Bool,a:Int):Bool return false;
 function spawnCrossFade(c:Character,n:Note):Void crossfades++;function sustain2(i:Int,s:Strumline.StrumNote,n:Note):Void{}
 function callHscript(f:Dynamic,a:Array<Dynamic>,n:String):Void{}function restoreSourceHitVocals(n:Note,p:Bool):Void vocals++;
 function dispatchNightmareVisionNoteHit(n:Note):Void{}
 function dispatchPsychNoteHit(n:Note,p:Bool):Void {
  postCalls++;PsychNoteCallbacks.dispatch(p?'goodNoteHit':'opponentNoteHit',n,notes.members.indexOf(n),n.noteData,
   function(name,args,family):Dynamic {if(family=='Luas')return Reflect.callMethod(null,lua.variables.get(name),args);return null;});
 }
 function applyPsychNoteClip(n:Note,s:Dynamic):Void clips++;function nightmareVisionRemoveFieldNoteMembership(n:Note):Void{}
 public function opponent(n:Note):Void {var daNote=n;var modernSustain=false;var daNoteStrums:Dynamic=null;__OPPONENT__}
 public function player(n:Note):Void {var daNote=n;var modernSustain=false;var daNoteStrums:Dynamic=null;__PLAYER__}
}
class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main(){
  for(player in [false,true])for(sustain in [false,true])for(force in [false,true])for(requested in [false,true])for(suppress in [false,true]) {
   var host=new Host();var n=new Note();n.mustPress=player;n.isSustainNote=sustain;n.aiShouldHit=force;n.shouldBeSung=requested;
   host.notes.members=[n];
   var typeScript="function onCreatePost()\n for i=0,getProperty('unspawnNotes.length')-1 do\n  if getPropertyFromGroup('unspawnNotes',i,'noteType')=='Delegated' then\n   setPropertyFromGroup('unspawnNotes',i,'noAnimation',true);\n  end\n end\nend";
   var converted=LuaCompat.translate(typeScript,'generic-custom-type.lua');check(converted.supported,'customtype translation');
   host.lua.execute(new hscript.Parser().parseString(converted.hscript));
   if(suppress) Reflect.callMethod(null,host.lua.variables.get('onCreatePost'),[]);
   check(n.noAnimation==suppress,'live customtype noAnimation setter');
   var callbacks=LuaCompat.translate("function opponentNoteHit(i,l,t,s)\n setProperty('extra.anim','singLEFT');\nend\nfunction goodNoteHit(i,l,t,s)\n setProperty('extra.anim','singLEFT');\nend",'generic-actor.lua');
   host.lua.execute(new hscript.Parser().parseString(callbacks.hscript));
   if(player)host.player(n) else host.opponent(n);
   var actor=player?host.boyfriend:host.dad;var sings=(force||requested)&&!suppress;
   check(actor.sings==(sings?1:0),'default actor animation gate');
   check(actor.holdTimer==(sings?0.:2.),'default hold timer only resets with animation');
   check(host.extra.anim=='singLEFT'&&host.postCalls==1,'customactor callback still runs');
   check(host.vocals==1&&(player?host.playerStrums.receptor.calls:host.enemyStrums.receptor.calls)==1,'hit effects preserved');
   check(sustain?!n.destroyed&&host.clips==1&&host.lifetimes==1:n.destroyed&&n.killed&&host.notes.members.length==0,'source note lifetime preserved');
   check(host.crossfades==(sings?1:0),'suppressed native crossfade');
  }
 }
}'''.replace('__NUMBER_ARRAY__', number_array).replace('__ALLOWS__', allows).replace('__OPPONENT__', opponent).replace('__PLAYER__', player)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            temp = Path(directory)
            (temp / 'Main.hx').write_text(fixture, encoding='utf-8')
            (temp / 'Strumline.hx').write_text('class StrumNote {public var ID=0;public var calls=0;public function new(){}public function playConfirm(s:Bool,b:Bool):Void calls++;}', encoding='utf-8')
            command = [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(ROOT / '.haxelib/hscript/2,5,0'), '-cp', str(temp), '-main', 'Main']
            result = subprocess.run([*command, '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-4000:])

    def test_pinned_opponent_suppression_keeps_post_callback_outside_gate(self):
        donor = DONOR.read_text(encoding='utf-8')
        opponent = extract_method(donor, 'function opponentNoteHit(')
        self.assertIn('else if(!note.noAnimation)', opponent)
        self.assertLess(opponent.index('else if(!note.noAnimation)'), opponent.index("callOnLuas('opponentNoteHit',"))
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        for marker in ['if (!sourceScoreNightmare && !daNote.mustPress && daNote.wasGoodHit', 'if (!sourceScoreNightmare && daNote.mustPress && daNote.wasGoodHit']:
            route = extract_method(play, marker)
            self.assertIn('(daNote.aiShouldHit || daNote.shouldBeSung) && daNote.allowsAnimation()', route)
            self.assertLess(route.index('daNote.allowsAnimation()'), route.index('dispatchPsychNoteHit(daNote,'))


if __name__ == '__main__':
    unittest.main()
