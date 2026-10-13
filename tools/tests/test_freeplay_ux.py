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
  check(FreeplayStarTrail.STARS>=300 && FreeplayStarTrail.GHOSTS>=1 && FreeplayStarTrail.PERIOD<=1.3 && FreeplayStarTrail.PERIOD>=0.7,'star field too sparse, slow or fast');
  check(FreeplayStarTrail.distance(0)==0 && Math.abs(FreeplayStarTrail.distance(1)-FreeplayStarTrail.REACH)<1e-9 && FreeplayStarTrail.entered(1)<=0.5 && FreeplayStarTrail.entered(1)>=0.35,'field does not end before the middle of the card');
  check(FreeplayStarTrail.START>0 && FreeplayStarTrail.START<=0.06 && FreeplayStarTrail.entered(0)<0 && FreeplayStarTrail.opacity(0.03)==0 && FreeplayStarTrail.entered(0.5)>0 && FreeplayStarTrail.opacity(FreeplayStarTrail.START/FreeplayStarTrail.REACH+0.01)>0.3 && FreeplayStarTrail.GLOW<=0.6,'stars do not start beyond the right edge or are dim when they enter');
  check(Math.abs(FreeplayStarTrail.distance(0.2)-FreeplayStarTrail.distance(0.1)-(FreeplayStarTrail.distance(0.9)-FreeplayStarTrail.distance(0.8)))<1e-9,'stars do not share one speed');
  check(FreeplayStarTrail.HEIGHT>=1.4 && FreeplayStarTrail.HEIGHT<=2.5,'emitter is not much taller than the card');
  var gap=1/FreeplayStarTrail.STARS; var shown=0; var top=0.0; var bottom=0.0; var steps=0; var bands=[0,0,0,0];
  for(i in 0...FreeplayStarTrail.STARS) {
   var row=FreeplayStarTrail.spread(i);
   check(Math.abs(row)<=FreeplayStarTrail.HEIGHT,'row leaves the field');
   // A staircase is neighbours in time sitting in neighbouring rows.
   if(Math.abs(row-FreeplayStarTrail.spread(i+1))<0.2)steps++;
   if(FreeplayStarTrail.inside(row)) { shown++; top=Math.min(top,row); bottom=Math.max(bottom,row); bands[Std.int(Math.min(3,(row+1)*2))]++; }
   for(clock in [0.0,0.37,1.25,9.5]) {
    var p=FreeplayStarTrail.life(clock,i);check(p>=0 && p<1,'life range');
    var behind=p-FreeplayStarTrail.life(clock,(i+1)%FreeplayStarTrail.STARS);if(behind<0)behind+=1;
    check(Math.abs(behind-gap)<1e-9,'spawn interval is not uniform');
   }
  }
  check(!FreeplayStarTrail.inside(1.01) && !FreeplayStarTrail.inside(-1.2) && FreeplayStarTrail.inside(1) && FreeplayStarTrail.inside(0) && !FreeplayStarTrail.inside(0.95,0.1),'stars outside the card are drawn');
  check(shown>=150 && shown<=FreeplayStarTrail.STARS*0.75 && top< -0.9 && bottom>0.9,'field does not fill the card edge to edge: '+shown+' '+top+' '+bottom);
  for(count in bands) check(count>=shown/4-18 && count<=shown/4+18,'field is uneven from top to bottom');
  check(steps<=FreeplayStarTrail.STARS*0.2,'field forms steps');
  // Evenly stepped rows weave a grid with the even spawn times: gaps between neighbours must vary.
  var gaps=new Map<Int,Int>();
  for(i in 0...FreeplayStarTrail.STARS-1) { var g=Std.int(Math.round((FreeplayStarTrail.direction(i+1)-FreeplayStarTrail.direction(i))*50)); gaps.set(g,(gaps.exists(g)?gaps.get(g):0)+1); }
  var distinct=0; var most=0; for(g in gaps.keys()) { distinct++; if(gaps.get(g)>most)most=gaps.get(g); }
  check(distinct>=60 && most<=FreeplayStarTrail.STARS*0.06,'rows repeat one step and weave a grid: '+distinct+' '+most);
  var up=0; var down=0; var eligible=0;
  for(i in 0...FreeplayStarTrail.STARS) {
   var b=FreeplayStarTrail.bend(i); check(b>=-1 && b<1,'bend range'); if(b<0)up++; else down++;
   check(FreeplayStarTrail.offset(i,0)==FreeplayStarTrail.spread(i) && Math.abs(FreeplayStarTrail.offset(i,1)-FreeplayStarTrail.spread(i))<=FreeplayStarTrail.ARC+1e-9,'arc is not slight or starts off its row');
   check(Math.abs(FreeplayStarTrail.offset(i,0.5)-FreeplayStarTrail.spread(i))<Math.abs(FreeplayStarTrail.offset(i,1)-FreeplayStarTrail.spread(i))+1e-12,'arc does not grow along the path');
   if(FreeplayStarTrail.reachesCard(i))eligible++; else for(l in [0.0,0.5,1.0]) check(!FreeplayStarTrail.inside(FreeplayStarTrail.offset(i,l), -FreeplayStarTrail.OVERHANG),'a star without a sprite can enter the card');
  }
  check(Math.abs(up-down)<=FreeplayStarTrail.STARS*0.08 && FreeplayStarTrail.ARC>0 && FreeplayStarTrail.ARC<=0.3 && eligible>=shown,'bends lean one way or are not slight');
  check(FreeplayStarTrail.opacity(0)==0 && FreeplayStarTrail.opacity(1)==0 && FreeplayStarTrail.opacity(0.7)<FreeplayStarTrail.opacity(0.25)*0.4 && FreeplayStarTrail.opacity(0.85)<0.07,'stars do not fade out early');
  check(FreeplayStarTrail.scale(1)<FreeplayStarTrail.scale(0) && FreeplayStarTrail.scale(0)==FreeplayStarTrail.SIZE,'stars do not shrink as they fade');
  for(g in 1...FreeplayStarTrail.GHOSTS)
   check(FreeplayStarTrail.ghostOpacity(0.4,g)<FreeplayStarTrail.ghostOpacity(0.4,g-1) && FreeplayStarTrail.ghostLag(g)>FreeplayStarTrail.ghostLag(g-1),'tail does not fade behind the star');
  check(FreeplayStarTrail.ghostOpacity(0.4,0)<FreeplayStarTrail.opacity(0.4) && FreeplayStarTrail.ghostOpacity(0.005,0)==0,'tail outruns its star');
  check(FreeplayStarTrail.ghostLag(FreeplayStarTrail.GHOSTS-1)<=0.02,'tail too long');
  check(FreeplayStarTrail.SIZE>0 && FreeplayStarTrail.SPIN>=90,'star does not rotate');
  var f=FreeplayStarTrail.FRAME;
  check(FreeplayStarTrail.TURNS>=18 && FreeplayStarTrail.turnFrame(0)==0 && FreeplayStarTrail.turnFrame(72)==0 && FreeplayStarTrail.turnFrame(36)==Std.int(FreeplayStarTrail.TURNS/2) && FreeplayStarTrail.turnFrame(-3)==FreeplayStarTrail.TURNS-1 && FreeplayStarTrail.turnFrame(71.99)==FreeplayStarTrail.TURNS-1,'turn frames');
  // A star half across the right edge keeps its left half; one inside keeps all of itself.
  check(FreeplayStarTrail.clipFrom(100,1,50)==0 && FreeplayStarTrail.clipTo(100,1,109)==9 && FreeplayStarTrail.clipTo(100,1,500)==f,'right edge cut');
  check(FreeplayStarTrail.clipFrom(40,1,50)==10 && FreeplayStarTrail.clipFrom(40,0.5,50)==f && FreeplayStarTrail.clipFrom(46,0.5,50)==8 && FreeplayStarTrail.clipTo(40,0.5,44)==8,'top edge cut at a smaller size');
  check(FreeplayStarTrail.clipTo(100,1,90)==0 && FreeplayStarTrail.clipFrom(100,0,50)==f && FreeplayStarTrail.clipTo(100,0,500)==0,'star wholly outside is not empty');
  var partialRows=0; for(i in 0...FreeplayStarTrail.STARS) if(FreeplayStarTrail.reachesCard(i) && !FreeplayStarTrail.inside(FreeplayStarTrail.spread(i))) partialRows++;
  check(FreeplayStarTrail.OVERHANG>0 && partialRows>=10,'no stars sit across the top or bottom edge');
  var trailSource=sys.io.File.getContent('source/FreeplayStarTrail.hx')+sys.io.File.getContent('source/FreeplayBrowserRow.hx');
  check(trailSource.indexOf('random')<0 && trailSource.indexOf('Math.sin(star')<0,'star stream uses randomness');
  var sections=FreeplayDetailSections.layout();
  for(i in 0...sections.length) {
   check(sections[i].title!='' && sections[i].height>=100,'detail card missing heading or body');
   if(i>0) check(sections[i].y>=sections[i-1].y+sections[i-1].height+FreeplayDetailSections.GAP && sections[i].color!=sections[i-1].color,'detail cards overlap or share an accent');
  }
  check(sections[0].y>FreeplayDetailSections.METER_FLOOR && sections[sections.length-1].y+sections[sections.length-1].height<=720-68,'detail cards collide with meters or search bar');
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
   check(searchNorm(' Week-2	[B] (C)·d
')=='week2bcd' && searchNorm('---')=='' && searchNorm(null)=='' && searchNorm('plain')=='plain');
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
