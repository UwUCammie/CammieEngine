"""Engine presentation identities, readiness priority and bounded star behavior."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]
class FreeplayUxTest(unittest.TestCase):
 def test_favorite_duplicates_pending_priority_titles_and_trail(self):
  body=r"""import LibrarySort.LibrarySortRow;
class Main {
 static function check(ok:Bool,m:String) {if(!ok)throw m;}
 static function row(i:Int,f:Bool,p:Bool):LibrarySortRow return {index:i,id:'song'+i,title:'Title'+i,owner:'owner'+i,modTitle:'Mod'+i,engine:'Psych',ordinal:i,favorite:f,random:false,unavailable:p};
 static function main() {
  for(group in ['flat','mod','engine']) for(charts in ['az','za','default','npsHigh','recent']) {
   var songs=[row(0,true,true),row(1,true,false),row(2,false,false)];
   var rows=FreeplayChartRows.expand(songs,function(i)return [0,1],function(i,d)return {value:d*10+i,scale:'Difficulty Rating'},function(d)return d==0?'easy':'hard');
   var order=LibrarySort.order([for(r in rows)r.sort],group,'za',charts);
   var display=FreeplayChartRows.withFavorites(rows,order,true);
   check(display.length==8,'duplicate wrong count');
   check(rows[display[0]].key.indexOf('@favorite:')==0 && rows[display[0]].song==1,'pending favorite pinned');
   check(rows[display[1]].key.indexOf('@favorite:')==0 && rows[display[1]].song==1,'favorite chart missing');
   check(rows[display[6]].sort.unavailable==true && rows[display[7]].sort.unavailable==true,'pending not last');
   var regular=0;for(id in display)if(rows[id].song==1 && rows[id].key.indexOf('@favorite:')!=0)regular++;
   check(regular==2,'regular favorite charts missing');
   check(rows[display[0]].key!=rows[display[1]].key,'difficulty presentation identity collides');
   var only=FreeplayChartRows.expand(songs,function(i)return [],function(i,d)return null);
   check(FreeplayChartRows.withFavorites(only,[0,1,2],false).length==3,'favorites-only duplicates');
  }
  check(FreeplaySongTitle.display('swag-messiah')=='Swag Messiah','title display');
  check(FreeplaySongTitle.display('already-Capitalized')=='Already Capitalized','title casing');
  check(FreeplayStarTrail.opacity(0)>0 && FreeplayStarTrail.opacity(1/3)==0 && FreeplayStarTrail.opacity(1)==0,'trail fade endpoint');
 }
}"""
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
   (Path(temp)/'Main.hx').write_text(body)
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)

 def test_search_audio_shortcuts_wait_for_release(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
   root=Path(temp);(root/'flixel/input/keyboard').mkdir(parents=True)
   (root/'flixel/input/keyboard/FlxKey.hx').write_text('package flixel.input.keyboard; typedef FlxKey = Int;',encoding='utf-8')
   (root/'flixel/FlxG.hx').write_text('package flixel; class Keys {public var pressed=false; public var released=false; public function new() {} public function anyPressed(k:Array<Int>):Bool return pressed; public function anyJustReleased(k:Array<Int>):Bool return released;} class Signal {public var callbacks:Array<Void->Void>=[];public function new() {} public function add(fn:Void->Void):Void callbacks.push(fn);public function remove(fn:Void->Void):Void callbacks.remove(fn);public function fire():Void for(fn in callbacks.copy())fn();} class FlxG {public static var signals={postUpdate:new Signal()};public static var keys=new Keys();public static var sound={muteKeys:[77],volumeUpKeys:[43],volumeDownKeys:[45]};}',encoding='utf-8')
   (root/'FreeplaySearchSoundKeys.hx').write_text((ROOT/'source/FreeplaySearchSoundKeys.hx').read_text(encoding='utf-8'),encoding='utf-8')
   (root/'Main.hx').write_text("""class Main {static function check(ok:Bool) {if(!ok)throw 'search shortcut ownership';} static function main() {
    var original=flixel.FlxG.sound.muteKeys;var guard=new FreeplaySearchSoundKeys();
    guard.update(true);check(flixel.FlxG.sound.muteKeys.length==0);
    flixel.FlxG.keys.pressed=true;guard.update(false);check(flixel.FlxG.sound.muteKeys.length==0);
    flixel.FlxG.keys.pressed=false;flixel.FlxG.keys.released=true;flixel.FlxG.signals.postUpdate.fire();check(flixel.FlxG.sound.muteKeys.length==0);
    flixel.FlxG.keys.released=false;flixel.FlxG.signals.postUpdate.fire();check(flixel.FlxG.sound.muteKeys==original);
    guard.update(true);guard.restore();check(flixel.FlxG.sound.muteKeys==original);
   }}""",encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(root),'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)

 def test_unicode_and_literal_symbols_have_distinct_search_queries(self):
  from test_freeplay_random_difficulty import extract_method
  method=extract_method((ROOT/'source/FreeplayState.hx').read_text(encoding='utf-8'),'public static function searchNorm(')
  body='class Main {'+method+r"""static function check(ok:Bool) {if(!ok)throw 'search normalization';} static function main() {
   check(searchNorm('Bopeebo (B-Side)')==searchNorm('bopeebo bside'));
   check(searchNorm('\u65e5')!='' && searchNorm('\u65e5')!=searchNorm('\u6708'));
   check(searchNorm('\u00e9')!='' && searchNorm('\u00e9')!=searchNorm('e'));
   check(searchNorm('+')!='' && searchNorm('+')!=searchNorm('0'));
   check(searchNorm('a+b').indexOf(searchNorm('+'))>=0 && searchNorm('plain').indexOf(searchNorm('+'))<0);
  }}"""
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
   (Path(temp)/'Main.hx').write_text(body,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)

 def test_control_chords_survive_complete_key_release_between_updates(self):
  from test_freeplay_random_difficulty import extract_method
  source=(ROOT/'source/FreeplayState.hx').read_text(encoding='utf-8')
  down=extract_method(source,'function onSearchKeyDown(')
  up=extract_method(source,'function onSearchKeyUp(')
  body="""import flixel.input.keyboard.FlxKey;
class Main {var searchControlDown=false; var searchControlUsed=false; public function new() {} """+down+up+"""
 static function check(ok:Bool) {if(!ok)throw 'control chord ownership';}
 static function main() {
 var menu=new Main();
 function event(code:Int,ctrl:Bool=false) return new openfl.events.KeyboardEvent(code,ctrl);
 menu.onSearchKeyDown(event(17));menu.onSearchKeyUp(event(17));check(!menu.searchControlUsed);
 menu.onSearchKeyDown(event(17));menu.onSearchKeyDown(event(65,true));menu.onSearchKeyUp(event(65,true));menu.onSearchKeyUp(event(17));
 check(menu.searchControlUsed && !menu.searchControlDown);
 menu.onSearchKeyDown(event(17));check(!menu.searchControlUsed);
 menu.onSearchKeyDown(event(65,true));menu.onSearchKeyDown(event(17));check(menu.searchControlUsed);
 menu.onSearchKeyUp(event(17));menu.onSearchKeyDown(event(86,true));check(menu.searchControlUsed);
 }
}"""
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
   root=Path(temp);(root/'openfl/events').mkdir(parents=True);(root/'flixel/input/keyboard').mkdir(parents=True)
   (root/'openfl/events/KeyboardEvent.hx').write_text('package openfl.events; class KeyboardEvent {public var keyCode:Int;public var ctrlKey:Bool;public function new(code:Int,ctrl:Bool) {keyCode=code;ctrlKey=ctrl;}}',encoding='utf-8')
   (root/'flixel/input/keyboard/FlxKey.hx').write_text('package flixel.input.keyboard; enum abstract FlxKey(Int) from Int to Int {var CONTROL=17;}',encoding='utf-8')
   (root/'Main.hx').write_text(body,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
