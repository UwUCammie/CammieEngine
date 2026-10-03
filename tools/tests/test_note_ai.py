"""Exercise Note's actual timing/health methods without initializing a renderer."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class NoteAITest(unittest.TestCase):
    def test_ai_hits_hazards_but_human_players_still_take_damage(self):
        source = (ROOT / 'source/Note.hx').read_text()
        play = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn('if (!daNote.mustPress && daNote.wasGoodHit && !daNote.nightmareVisionHitDispatched && (daNote.codenameInputLine != null', play)
        self.assertIn(': daNote.isAutoPlayed())) {', play)
        update = source[source.index('\tpublic inline function isAutoPlayed('):source.index('\t// inline because')]
        health = source[source.index('\tpublic function getHealth('):source.rfind('}')]
        # Keep production method bodies intact; stub only rendering and globals.
        fixture = '''
class Base { public function new() {} public function update(elapsed:Float) {} }
class Conductor { public static var songPosition:Float = 999; }
class Judge {
 public static var wayoffJudge:Float = 180;
 public static var badJudge:Float = 100;
 public static var shitJudge:Float = 150;
}
class PlayState {
 public function new() {}
 public static var instance:PlayState=new PlayState();
 public static var healthGainMultiplier:Float = 1;
 public static var healthLossMultiplier:Float = 1;
 public var ratingManager:Dynamic={lastHitWindow:180.0};
}
class OptionsHandler { public static var options = {useKadeHealth:false}; }
class TestNote extends Base {
 public var mustPress=false; public var oppMode=false; public var duoMode=false;
 public var nightmareVisionTypeRuntime:Dynamic=null; public var canMiss=false;
 public var sourcePlayfieldPlayerControlled:Null<Bool>=null;
 public var sourcePlayfieldAutoPlay=false;
 public var codenameInputLine:Dynamic=null;
 public var earlyPressWindow:Float=1; public var latePressWindow:Float=1;
 public var funnyMode=false; public var dontCountNote=true; public var aiShouldHit=true;
 public var avoidAutoHit=false; public var autoHitSuppressed=false;
 public var canBeHit=false; public var wasGoodHit=false; public var tooLate=false;
 public var mineNote=false; public var nukeNote=false;
 public var ignoreNote=false; public var hitCausesMiss=false;
 public var blockHit=false;
 public var hitHealth:Null<Float>=null; public var missHealth:Null<Float>=null;
 public var strumTime:Float=1000; public var timingMultiplier:Float=1; public var alpha:Float=1;
 public var consistentHealth=true; public var healCutoff:String="miss";
 public var healAmount:Null<Float>=-0.25; public var damageAmount:Null<Float>=0;
 public var healMultiplier:Float=1; public var damageMultiplier:Float=1;
 public var ignoreHealthMods=false;
''' + update + health + '''
}
class TestNoteAI {
 static function check(ok:Bool, message:String) { if(!ok) throw message; }
 static function main() {
  var owned = new TestNote(); owned.codenameInputLine={cpu:false,botplay:false};
  check(!owned.isAutoPlayed(), "Source human line must override native opponent CPU");
  owned.codenameInputLine.cpu=true;
  check(owned.isAutoPlayed(), "Source CPU mutation must take effect");
  owned.mustPress=true; owned.duoMode=true;
  check(owned.isAutoPlayed(), "Source CPU must override native duo player");
  owned.codenameInputLine.cpu=false; owned.codenameInputLine.botplay=true;
  check(owned.isAutoPlayed(), "Source botplay gate");
  owned.codenameInputLine.botplay=false; owned.funnyMode=true;
  check(owned.isAutoPlayed(), "Demo still autoplays source notes");
  var codenameNmv = new TestNote(); codenameNmv.sourcePlayfieldAutoPlay=true;
  codenameNmv.codenameInputLine={cpu:false,botplay:false};
  check(!codenameNmv.isAutoPlayed(),
   "Codename line ownership keeps its explicit human CPU policy");
  codenameNmv.codenameInputLine.cpu=true;
  check(codenameNmv.isAutoPlayed(),
   "Codename line CPU setting remains authoritative for automatic hits");
  for (duoMode in [false, true]) for (opponentPlayer in [false, true])
   for (demoMode in [false, true]) {
    var ordinaryOpponent = new TestNote(); ordinaryOpponent.mustPress=false;
    ordinaryOpponent.duoMode=duoMode; ordinaryOpponent.oppMode=opponentPlayer;
    ordinaryOpponent.funnyMode=demoMode;
    var oldNativeGate = ((!duoMode && !opponentPlayer) || demoMode);
    check(ordinaryOpponent.isAutoPlayed() == oldNativeGate,
     "Ordinary opponent auto route must preserve the prior mode policy");
   }
  var nmvOpponentDuo = new TestNote(); nmvOpponentDuo.mustPress=false;
  nmvOpponentDuo.duoMode=true; nmvOpponentDuo.sourcePlayfieldAutoPlay=true;
  check(nmvOpponentDuo.isAutoPlayed(),
   "NMV field one keeps its source autoplay policy in duo mode");
  var nmvPlayer = new TestNote(); nmvPlayer.mustPress=true;
  nmvPlayer.sourcePlayfieldPlayerControlled=true;
  check(!nmvPlayer.isAutoPlayed() && nmvPlayer.isPlayerControlled(),
   "NMV field zero is BF-owned and human-played until botplay");
  nmvPlayer.funnyMode=true;
  check(nmvPlayer.isAutoPlayed(), "NMV field zero follows botplay");
  var nmvOpponent = new TestNote(); nmvOpponent.sourcePlayfieldPlayerControlled=false;
  nmvOpponent.sourcePlayfieldAutoPlay=true;
  check(nmvOpponent.isAutoPlayed() && !nmvOpponent.isPlayerControlled(),
   "NMV field one belongs to Dad and autoplays");
  var nmvExtra = new TestNote(); nmvExtra.sourcePlayfieldPlayerControlled=true;
  nmvExtra.sourcePlayfieldAutoPlay=true;
  check(nmvExtra.isAutoPlayed() && nmvExtra.isPlayerControlled(),
   "NMV extra fields belong to BF and autoplay despite the legacy hit side");
  var nmvCpuOff = new TestNote(); nmvCpuOff.nightmareVisionTypeRuntime={};
  nmvCpuOff.mustPress=false; nmvCpuOff.sourcePlayfieldPlayerControlled=true;
  nmvCpuOff.sourcePlayfieldAutoPlay=false;
  check(!nmvCpuOff.isAutoPlayed(),
   "NMV source CPU-off policy overrides native opponent autoplay fallback");
  nmvCpuOff.funnyMode=true;
  check(!nmvCpuOff.isAutoPlayed(),
   "NMV source CPU-off policy overrides global botplay fallback");
  var nmvCpuOverride = new TestNote(); nmvCpuOverride.nightmareVisionTypeRuntime={};
  nmvCpuOverride.mustPress=true; nmvCpuOverride.sourcePlayfieldAutoPlay=true;
  check(nmvCpuOverride.isAutoPlayed(),
   "NMV source CPU-on policy overrides the native player side");
  var nmvPlayerCanMiss = new TestNote(); nmvPlayerCanMiss.nightmareVisionTypeRuntime={};
  nmvPlayerCanMiss.mustPress=false; nmvPlayerCanMiss.sourcePlayfieldPlayerControlled=true;
  nmvPlayerCanMiss.canMiss=true;
  check(!nmvPlayerCanMiss.canAutoHit(),
   "NMV BF-owned field cannot autoplay a canMiss note despite native opponent ownership");
  var nmvPlayerHitCausesMiss = new TestNote(); nmvPlayerHitCausesMiss.nightmareVisionTypeRuntime={};
  nmvPlayerHitCausesMiss.mustPress=false; nmvPlayerHitCausesMiss.sourcePlayfieldPlayerControlled=true;
  nmvPlayerHitCausesMiss.hitCausesMiss=true;
  check(!nmvPlayerHitCausesMiss.canAutoHit(),
   "NMV BF-owned field cannot autoplay a hitCausesMiss note despite native opponent ownership");
  var nmvOpponentHazard = new TestNote(); nmvOpponentHazard.nightmareVisionTypeRuntime={};
  nmvOpponentHazard.mustPress=true; nmvOpponentHazard.sourcePlayfieldPlayerControlled=false;
  nmvOpponentHazard.canMiss=true; nmvOpponentHazard.hitCausesMiss=true;
  check(nmvOpponentHazard.canAutoHit(),
   "NMV Dad-owned field follows source ownership and may autoplay hazards");
  nmvOpponentHazard.ignoreNote=true;
  check(!nmvOpponentHazard.canAutoHit(),
   "NMV ignored notes remain excluded regardless of source field ownership");
  var mutableLegacy = new TestNote(); mutableLegacy.sourcePlayfieldPlayerControlled=null;
  mutableLegacy.mustPress=false;
  check(!mutableLegacy.isPlayerControlled(), "Legacy source owner falls back to mustPress");
  mutableLegacy.mustPress=true;
  check(mutableLegacy.isPlayerControlled(), "Legacy owner follows script-mutated mustPress");
  var ai = new TestNote();
  ai.update(0); check(!ai.wasGoodHit, "AI must wait until the note time");
  Conductor.songPosition=1000;
  ai.update(0); check(ai.wasGoodHit, "AI must hit opted-in danger notes");
  var player = new TestNote(); player.mustPress=true;
  player.update(0); check(!player.wasGoodHit && player.canBeHit, "Human hits require input");
  for(rating in ["sick","good","bad","shit","wayoff"])
   check(player.getHealth(rating)==-0.25, "Player danger hit must damage: "+rating);
  check(player.getHealth("miss")==0, "Avoiding danger must be safe");
  var reverseAI = new TestNote(); reverseAI.mustPress=true; reverseAI.oppMode=true;
  reverseAI.update(0); check(!reverseAI.wasGoodHit, "BF bot must avoid danger even in opposite mode");
  var reversePlayer = new TestNote(); reversePlayer.oppMode=true;
  reversePlayer.update(0); check(!reversePlayer.wasGoodHit, "Opposite mode human must not auto-hit");
  var duo = new TestNote(); duo.duoMode=true;
  duo.update(0); check(!duo.wasGoodHit, "Duo human must not auto-hit");
  var legacyHazard = new TestNote(); legacyHazard.aiShouldHit=false;
  legacyHazard.update(0); check(!legacyHazard.wasGoodHit, "Other hazards retain AI avoidance");
  // A 50x frame may jump beyond both the hit window and the screen.
  // Newly spawned/inactive notes must be judged without any sprite update.
  for(i in 0...1000) {
   var skippedFrame = new TestNote(); skippedFrame.funnyMode=true;
   skippedFrame.mustPress=i%2==0; skippedFrame.aiShouldHit=false;
   skippedFrame.dontCountNote=false; skippedFrame.healAmount=0.04; skippedFrame.strumTime=1000+i;
   skippedFrame.updateAutoHit(5000);
   check(skippedFrame.wasGoodHit, "All crossed notes must autoplay despite skipped frames");
  }
  for(kind in 0...4) {
   var danger=new TestNote();danger.mustPress=true;danger.funnyMode=true;
   danger.dontCountNote=false;danger.mineNote=kind==0;danger.nukeNote=kind==1;
   danger.healAmount=kind==2?-0.25:0.04;danger.dontCountNote=kind==3;
   danger.updateAutoHit(5000);check(!danger.wasGoodHit,"BF demo must avoid all hazards");
  }
  var future = new TestNote(); future.updateAutoHit(999);
  check(!future.wasGoodHit, "Autoplay must not hit future notes");
  player.updateAutoHit(5000);
  check(!player.wasGoodHit, "Direct timing checks must not auto-hit human notes");
  var ordinary = new TestNote(); ordinary.aiShouldHit=false; ordinary.dontCountNote=false;
  ordinary.update(0); check(ordinary.wasGoodHit, "Ordinary AI notes still work");
  var scriptedDanger = new TestNote(); scriptedDanger.mustPress=true;
  scriptedDanger.funnyMode=true; scriptedDanger.dontCountNote=false;
  scriptedDanger.healAmount=0.04; scriptedDanger.avoidAutoHit=true;
  scriptedDanger.updateAutoHit(5000);
  check(!scriptedDanger.wasGoodHit, "Explicit script danger skips BF autoplay");
  var ignored = new TestNote(); ignored.mustPress=true; ignored.funnyMode=true;
  ignored.dontCountNote=false; ignored.healAmount=0.04; ignored.ignoreNote=true;
  ignored.updateAutoHit(5000);
  check(!ignored.wasGoodHit, "Psych ignored player note skips BF autoplay");
  var hitMiss = new TestNote(); hitMiss.mustPress=true; hitMiss.funnyMode=true;
  hitMiss.dontCountNote=false; hitMiss.healAmount=0.04; hitMiss.hitCausesMiss=true;
  hitMiss.updateAutoHit(5000);
  check(!hitMiss.wasGoodHit, "Psych hit-causes-miss note skips BF autoplay");
  var blocked = new TestNote(); blocked.mustPress=true; blocked.funnyMode=true;
  blocked.dontCountNote=false; blocked.healAmount=0.04; blocked.blockHit=true;
  blocked.updateAutoHit(5000);
  check(!blocked.wasGoodHit, "Psych stage-blocked player note skips BF autoplay");
  var opponentDanger = new TestNote(); opponentDanger.avoidAutoHit=true;
  opponentDanger.dontCountNote=false;
  opponentDanger.updateAutoHit(5000);
  check(opponentDanger.wasGoodHit, "Opponent autoplay keeps its own rule");
  var canceledAutoHit = new TestNote(); canceledAutoHit.autoHitSuppressed=true;
  canceledAutoHit.updateAutoHit(5000);
  check(!canceledAutoHit.wasGoodHit, "Canceled computer hit must not retry");
  var sourceTiming = new TestNote(); sourceTiming.mustPress=true;
  sourceTiming.codenameInputLine={cpu:false,botplay:false};
  Conductor.songPosition=820; sourceTiming.update(0);
  check(!sourceTiming.canBeHit&&!sourceTiming.tooLate,
   "Codename early input edge must be strict");
  Conductor.songPosition=821; sourceTiming.update(0);
  check(sourceTiming.canBeHit, "Codename input must open inside early edge");
  Conductor.songPosition=1179; sourceTiming.update(0);
  check(sourceTiming.canBeHit, "Codename input must remain open before late edge");
  Conductor.songPosition=1180; sourceTiming.update(0);
  check(!sourceTiming.canBeHit&&!sourceTiming.tooLate,
   "Codename late input edge must be strict before miss");
  Conductor.songPosition=1181; sourceTiming.update(0);
  check(sourceTiming.tooLate, "Codename unscaled miss threshold");
  var scaled=new TestNote(); scaled.mustPress=true;
  scaled.codenameInputLine={cpu:false,botplay:false};
  scaled.earlyPressWindow=.5; scaled.latePressWindow=.5;
  Conductor.songPosition=909; scaled.update(0);
  check(!scaled.canBeHit, "Codename per-note early scale");
  Conductor.songPosition=911; scaled.update(0);
  check(scaled.canBeHit, "Codename scaled window opens");
  Conductor.songPosition=1091; scaled.update(0);
  check(!scaled.canBeHit&&!scaled.tooLate,
   "Codename per-note late scale does not change miss threshold");
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'TestNoteAI.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder,
                                     '-main', 'TestNoteAI', '--interp'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
