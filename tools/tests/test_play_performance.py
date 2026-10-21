"""Stats must belong to the score being displayed, including legacy/zero cases."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
from test_freeplay_random_difficulty import extract_method
ROOT=Path(__file__).resolve().parents[2]
class PlayPerformanceTest(unittest.TestCase):
 def test_score_categories_keep_their_own_play(self):
  source=(ROOT/'source/Highscore.hx').read_text()
  methods='\n'.join(extract_method(source,x) for x in ['public static function saveScore(', 'static function setPerformance(', 'static function setDetail(', 'public static function formatSong('])
  methods += '\n' + source[source.index('public static function peekPerformance('):source.index('\n\tstatic function songFlush', source.index('public static function peekPerformance('))]
  stub='''import PlayPerformance.PlayPerformanceRecord;
   import StandardScore.ScoreDetail;
   typedef Jury=Int; typedef FCLevel=Int;
   class Highscore {
    public static var songScores:Map<String,Int>=[];
    public static var songAccuracy:Map<String,Float>=[];
    public static var songFCLevels:Map<String,Int>=[];
    public static var songPerformance:Map<String,PlayPerformanceRecord>=[];
    public static var songDetails:Map<String,ScoreDetail>=[];
    static function setScore(k:String,v:Int) songScores.set(k,v);
    static function setAccuracy(k:String,v:Float) songAccuracy.set(k,v);
    static function setFCLevel(k:String,v:Int) songFCLevels.set(k,v);
    static function setJudge(k:String,v:Dynamic) {}
    static function setOptionsUsed(k:String,v:Dynamic) {}
    static function setModifiersUsed(k:String,v:Dynamic) {}
    static function songFlush() {}
   '''+methods+'}'
  main='''class Main {static function check(v:Bool,s:String){if(!v)throw s;}
   static function main(){
    var a={misses:2,maxCombo:80,totalPlayerNotes:100};var b={misses:0,maxCombo:100,totalPlayerNotes:100};
    Highscore.saveScore('owner-a',100,0,0.8,1,0,a);
    Highscore.saveScore('owner-a',90,0,0.99,2,0,b);
    check(Highscore.peekPerformance('owner-a',0).misses==2,'lower score overwrote best play');
    check(Highscore.peekPerformance('owner-a',0,'recent').misses==0,'recent missing');
    check(Highscore.peekPerformance('owner-a',0,'best-accuracy').maxCombo==100,'accuracy stats mismatched');
    check(Highscore.peekPerformance('owner-b',0)==null && Highscore.peekPerformance('owner-a',1)==null,'owner/difficulty leak');
    Highscore.saveScore('owner-a',101,0,0.7,1,0);
    check(Highscore.peekPerformance('owner-a',0)==null,'old caller inherited previous play stats');
    Highscore.saveScore('zero',0,0,0,0,0,a);
    check(Highscore.peekPerformance('zero',0).misses==2,'zero score dropped');
   }}'''
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
   files={'Highscore.hx':stub,'Main.hx':main,'OptionsHandler.hx':'class OptionsHandler {public static var options:Dynamic={};}',
    'ModifierState.hx':'class ModifierState {public static var namedModifiers:Dynamic={}; public static function snapshot():Dynamic return {};}',
    'DifficultyIcons.hx':'class DifficultyIcons {public static function getEndingFP(i:Int):String return i==0?"":"-hard";}'}
   for name,text in files.items():Path(temp,name).write_text(text)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
