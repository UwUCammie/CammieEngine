"""Compare the historical hit control flow with pinned donor handlers."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_hit_order import extract_method

ROOT = Path(__file__).resolve().parents[2]
REV = '7f96eb3b5a60352413229bf134bd348b79ad5fe6'

class HistoricalDefaultHitFlowTest(unittest.TestCase):
    def test_source_order_flags_gates_and_fixed_family(self):
        donor = ROOT.parent / 'fnf_sources/NightmareVision'
        if not donor.is_dir():
            self.skipTest('pinned historical source unavailable')
        source = subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
        good = extract_method(source, 'function goodNoteHit(')
        opponent = extract_method(source, 'function opponentNoteHit(')
        # Bound the comparison to the default handler orchestration. Renderer,
        # animation/chord and miss internals are separate contracts, not faked parity.
        for name in ['good','opponent']:
            text = good if name == 'good' else opponent
            field = 'field' if name == 'good' else 'playfield'
            start = text.index('if ('+field+'.autoPlayed)')
            block = extract_method(text[start:], 'if ('+field+'.autoPlayed)')
            tail = text[start+len(block):]
            otherwise = extract_method(tail, 'else')
            text = text[:start]+'confirmNightmareVisionLegacyHit(note, '+field+');'+tail[tail.index(otherwise)+len(otherwise):]
            if name == 'good':
                block = extract_method(text, 'if(!note.noAnimation)')
                text = text.replace(block, 'prepareNightmareVisionHitSingers(note,field,field.ID,false);')
                text = text.replace(extract_method(text, "if(SONG.song.toLowerCase() == 'tri-torial')"), '')
                text = text.replace(extract_method(text, 'if(!note.noMissAnimation)'), 'hurtNightmareVisionLegacySinger(note,field);')
                text = text.replace("FlxG.sound.play(Paths.sound('hitsound'), ClientPrefs.hitsoundVolume);", 'playNightmareVisionLegacyHitSound(note);')
                text = text.replace('noteMiss(note);', 'noteMiss(note.noteData,true,note);')
                good = text
            else:
                text = text.replace("if (Paths.formatToSongPath(SONG.song) != 'tutorial')", '')
                begin = text.index('var char:Character')
                end = text.index('if (SONG.needsVoices)')
                text = text[:begin]+'prepareNightmareVisionHitSingers(note,playfield,playfield.ID,false);'+text[end:]
                opponent = text
        reference = ('class Reference extends PlayState { public function new(){super();}' + good + opponent + '}').replace('field:PlayField','field:NightmareVisionPlayFieldView').replace('playfield:PlayField','playfield:NightmareVisionPlayFieldView').replace('function goodNoteHit(', 'public function goodNoteHit(').replace('function opponentNoteHit(', 'public function opponentNoteHit(').replace('SONG.', 'PlayState.SONG.')
        note = r"""
class Note {
 public var wasGoodHit=false;public var hitByOpponent=false;public var nightmareVisionHitDispatched=false;
 public var ignoreNote=false;public var hitCausesMiss=false;public var canMiss=false;
 public var hitsoundDisabled=false;public var noMissAnimation=false;public var noteSplashDisabled=false;
 public var isSustainNote=false;public var doAutoSustain=false;public var noteData=0;public var ID=91;
 public var hitHealth=0.23;public var strumTime=100.;public var noteType='Hurt Note';public var noteScript:Dynamic=null;
 public var log:Array<String>;public function new(l:Array<String>){log=l;}
 public function kill(){log.push('kill');}public function destroy(){log.push('destroy');}
}
"""
        host = r"""
class PlayState {
 public static var SONG:Dynamic={needsVoices:true};public var health=1.;public var healthGain=1.5;
 public var combo=9999;public var camZooming=false;public var events:Array<String>=[];
 public var notes:Dynamic;public var modchartObjects:Dynamic;public var vocals:Voice;
 public function new(){
  vocals=new Voice(events);notes={members:[],remove:function(n:Note,b:Bool){events.push('remove');return n;}};
  modchartObjects={exists:function(k:String)return false,remove:function(k:String)return false};
 }
 public function setAllHaxeVar(n:String,v:Dynamic){}
 public function updateScoreBar(){events.push('scorebar');}
 public function playNightmareVisionLegacyHitSound(n:Note){if(ClientPrefs.hitsoundVolume>0&&!n.hitsoundDisabled)events.push('sound');}
 public function confirmNightmareVisionLegacyHit(n:Note,f:NightmareVisionPlayFieldView){events.push('confirm');}
 public function noteMiss(d:Int,p:Bool,n:Note){events.push('miss');health-=0.1;}
 public function spawnNoteSplashOnNote(n:Note){events.push('splash');}
 public function hurtNightmareVisionLegacySinger(n:Note,f:NightmareVisionPlayFieldView){if(!n.noMissAnimation&&n.noteType=='Hurt Note')events.push('hurt');}
 public function popUpScore(n:Dynamic,?note:Note,p:Bool=true,b:Bool=false,?f:NightmareVisionPlayFieldView){events.push('score');}
 public function prepareNightmareVisionHitSingers(n:Note,f:NightmareVisionPlayFieldView,id:Int,b:Bool){events.push('sing');}
 public function setSourceVocalVolume(role:String,v:Float){vocals.volume=v;}
 public function dispatchHistoricalNightmareNoteHit(n:Note,callback:String){callOnLuas(callback,[]);}
 public function callOnLuas(callback:String,args:Array<Dynamic>):Dynamic {
  var n:Note=notes.members[0];events.push(callback+':'+n.wasGoodHit+':'+n.hitByOpponent+':'+n.doAutoSustain);return 1;
 }
 public function callOnHScripts(n:String,args:Array<Dynamic>):Dynamic return 2;
 public function callScript(s:Dynamic,n:String,args:Array<Dynamic>){}
 public function finishNightmareVisionExternalHit(n:Note,p:Bool,f:NightmareVisionPlayFieldView,id:Int,a:Bool,b:Bool){}
 public function detachNightmareVisionTap(n:Note){n.kill();notes.remove(n,true);}
}
class Voice {public var volume(default,set):Float=0;var events:Array<String>;public function new(e){events=e;}function set_volume(v:Float){events.push('voice');return volume=v;}}
"""
        main = r"""
class Main {
 static function check(b:Bool,s:String){if(!b)throw s;}
 static function configure(n:Note,mask:Int){
  n.wasGoodHit=mask&1!=0;n.ignoreNote=mask&2!=0;n.hitCausesMiss=mask&4!=0;
  n.isSustainNote=mask&8!=0;n.canMiss=mask&16!=0;n.noteSplashDisabled=mask&32!=0;
  n.hitsoundDisabled=mask&64!=0;n.noMissAnimation=mask&128!=0;
 }
 static function main(){
  for(player in [false,true])for(auto in [false,true])for(controls in [false,true])for(voice in [false,true])for(lane in [0,5])for(mask in 0...256){
   PlayState.SONG.needsVoices=voice;ClientPrefs.hitsoundVolume=0.5;
   var a=new PlayState(),b=new Reference();var an=new Note(a.events),bn=new Note(b.events);
   configure(an,mask);configure(bn,mask);an.noteData=bn.noteData=lane;
   a.notes.members=[an];b.notes.members=[bn];var field=new NightmareVisionPlayFieldView();field.autoPlayed=auto;field.playerControls=controls;
   NightmareVisionLegacyHitFlow.hit(a,an,field,player);
   if(player)b.goodNoteHit(bn,field);else b.opponentNoteHit(bn,field);
   check(a.events.join(',')==b.events.join(','),'order '+player+'/'+auto+'/'+mask+': '+a.events+' != '+b.events);
   check(a.health==b.health&&a.combo==b.combo&&a.camZooming==b.camZooming,'native effects');
   check(an.wasGoodHit==bn.wasGoodHit&&an.hitByOpponent==bn.hitByOpponent&&an.doAutoSustain==bn.doAutoSustain,'source flags');
   NightmareVisionLegacyHitFlow.updateFlags(an);if(bn.hitByOpponent)bn.wasGoodHit=true;
   check(an.wasGoodHit==bn.wasGoodHit,'deferred opponent flag');
  }
 }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            work=FixturePath(folder)
            for name, text in {'Main':main,'Reference':reference,'PlayState':host,'Note':note,
                'NightmareVisionPlayFieldView':'class NightmareVisionPlayFieldView {public var ID=7;public var autoPlayed=false;public var playerControls=false;public function new(){}}',
                'ClientPrefs':'class ClientPrefs {public static var hitsoundVolume=0.;}',
                'NightmareVisionLegacyHitFlow':(ROOT/'source/NightmareVisionLegacyHitFlow.hx').read_text()}.items():
                (work/(name+'.hx')).write_text(text,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_source_receptor_confirmation(self):
        donor=ROOT.parent/'fnf_sources/NightmareVision'
        if not donor.is_dir(): self.skipTest('pinned historical source unavailable')
        source=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
        hit=extract_method(source,'function goodNoteHit(')
        first=extract_method(hit,'if (field.autoPlayed)')
        tail=hit[hit.index(first)+len(first):]
        second=extract_method(tail,'else')
        reference='public function confirm(note:Note,field:Field):Void {'+first+second+'}'
        reference+=extract_method(source,'function StrumPlayAnim(').replace('PlayField','Field')
        actual=extract_method((ROOT/'source/PlayState.hx').read_text(),'function confirmNightmareVisionLegacyHit(').replace('function confirmNightmareVisionLegacyHit(', 'public function confirm(').replace('NightmareVisionPlayFieldView','Field')
        fixture=r"""
using StringTools;
class Note {public var noteData=0;public var isSustainNote=false;public var animation:{curAnim:{name:String}}={curAnim:{name:'hold'}};public function new(){}}
class StrumNote {public var ID:Int;public var resetAnim=3.;public var calls=0;public function new(i){ID=i;}public function playAnim(n:String,f:Bool,note:Note){calls++;}}
class Field {public var autoPlayed=false;public var playAnims=false;public var members:Array<StrumNote>=[];public function new(){}public function forEach(f:StrumNote->Void){for(s in members)f(s);}}
class Reference {var SONG:{keys:Int};public function new(k:Int){SONG={keys:k};}__REFERENCE__}
class Actual {var keys:Int;public var playbackRate=4.;public function new(k){keys=k;}function nightmareVisionKeyCount()return keys;__ACTUAL__}
class Main {
 static function main(){
  for(keys in [4,7])for(auto in [false,true])for(sustain in [false,true])for(end in [false,true])for(reverse in [false,true])for(lane in 0...11){
   var a=new Field(),b=new Field();a.autoPlayed=b.autoPlayed=auto;
   for(i in 0...keys){a.members.push(new StrumNote(reverse?keys-i-1:i));b.members.push(new StrumNote(reverse?keys-i-1:i));}
   var note=new Note();note.noteData=lane;note.isSustainNote=sustain;note.animation.curAnim.name=end?'holdend':'hold';
   new Reference(keys).confirm(note,a);new Actual(keys).confirm(note,b);
   for(i in 0...keys)if(a.members[i].calls!=b.members[i].calls||a.members[i].resetAnim!=b.members[i].resetAnim)throw 'receptor confirmation mismatch';
  }
 }
}
""".replace('__REFERENCE__',reference).replace('__ACTUAL__',actual)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            work=FixturePath(folder);(work/'Main.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__': unittest.main()
