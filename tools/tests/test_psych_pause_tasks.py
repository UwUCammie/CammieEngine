"""Pinned Psych global task pause/resume ordering and activity semantics."""
from pathlib import Path
import re,subprocess,tempfile,unittest
from haxe_test_support import ROOT,HAXE_COMMAND
class PsychPauseTasksTest(unittest.TestCase):
 def test_all_unfinished_tasks_follow_source_transitions(self):
  source=subprocess.check_output(['git','-C',str(ROOT.parent/'fnf_sources/FNF-PsychEngine'),'show','5c67ced49e5a98535298a6daa3f8f4ec79ac8399:source/states/PlayState.hx'],text=True)
  statements=[]
  for active in ['false','true']:
   expr=[]
   for kind,var in [('FlxTimer','tmr'),('FlxTween','twn')]:
    pattern=rf'{kind}\.globalManager\.forEach\(function\({var}:{kind}\) if\(!{var}\.finished\) {var}\.active = {active}\);'
    expr.append(re.search(pattern,source).group(0))
   statements.append('public static function '+('pause' if active=='false' else 'resume')+'():Void {'+''.join(expr)+'}')
  files={
   'Donor.hx':'import flixel.util.FlxTimer;import flixel.tweens.FlxTween; class Donor {'+''.join(statements)+'}',
   'Task.hx':r"""class Task {public var id:String;public var finished:Bool;public var active(get,set):Bool;var value:Bool;public function new(i:String,a:Bool,f:Bool){id=i;value=a;finished=f;}function get_active():Bool return value;function set_active(v:Bool):Bool {Main.log.push(id+':'+v);return value=v;}}""",
   'Manager.hx':'class Manager<T> {public var tasks:Array<T>=[];public function new(){}public function forEach(f:T->Void):Void {for(t in tasks)f(t);}}',
   'flixel/util/FlxTimer.hx':'package flixel.util;class FlxTimer extends Task {public static var globalManager=new Manager<FlxTimer>();public function new(i:String,a:Bool,f:Bool){super(i,a,f);}}',
   'flixel/tweens/FlxTween.hx':'package flixel.tweens;class FlxTween extends Task {public static var globalManager=new Manager<FlxTween>();public function new(i:String,a:Bool,f:Bool){super(i,a,f);}}',
   'Main.hx':r"""import flixel.util.FlxTimer;import flixel.tweens.FlxTween;
class Main {public static var log:Array<String>;static function run(source:Bool,mask:Int,active:Bool):String {log=[];var timers=[for(i in 0...2)new FlxTimer('timer'+i,(mask&(1<<(i*2)))!=0,(mask&(2<<(i*2)))!=0)];var tweens=[for(i in 2...4)new FlxTween('tween'+i,(mask&(1<<(i*2)))!=0,(mask&(2<<(i*2)))!=0)];FlxTimer.globalManager.tasks=timers;FlxTween.globalManager.tasks=tweens;if(source){if(active)Donor.resume();else Donor.pause();}else SourcePauseTasks.setActive(active);return log.join('|')+';'+[for(t in timers)t.active].join(',')+';'+[for(t in tweens)t.active].join(',');}static function main(){for(mask in 0...256)for(active in [false,true]){var expected=run(true,mask,active),actual=run(false,mask,active);if(expected!=actual)throw mask+':'+active+' '+expected+' != '+actual;}trace('source-pause-tasks:512');}}
"""}
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
   work=Path(folder)
   for name,data in files.items():
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data,encoding='utf-8')
   r=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main'],capture_output=True,text=True,timeout=60)
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   self.assertIn('source-pause-tasks:512',r.stdout)
