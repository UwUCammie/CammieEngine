"""Execute historical singer decisions against the pinned donor source."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_nv_hit_order import extract_method
ROOT=Path(__file__).resolve().parents[2]
REV='7f96eb3b5a60352413229bf134bd348b79ad5fe6'
class HistoricalSingingTest(unittest.TestCase):
 def test_pinned_singer_gates_chords_and_ghost_callbacks(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned historical source unavailable')
  source=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
  good=extract_method(source,'function goodNoteHit(');good=extract_method(good,'if(!note.noAnimation)')
  opponent=extract_method(source,'function opponentNoteHit(');opponent=opponent[opponent.index('var char:Character'):opponent.index('if (SONG.needsVoices)')]
  reference=('class Reference { public var gf:Character;public var singAnimations:Array<String>;public var noteRows:Array<Array<Array<Note>>>;public var ghostsAllowed:Bool;public var SONG:Dynamic;public var curSection=0;public var gate:(String,Note)->Dynamic;public function new(){}function callOnHScripts(n:String,a:Array<Dynamic>):Dynamic return gate(a[0],a[1]); public function good(note:Note,field:Dynamic){'+good+'}public function opponent(note:Note,playfield:Dynamic){'+opponent+'}}').replace('note.gfNote','note.forceGfSing')
  note="""class Note {public var noteData=1;public var row=4;public var mustPress=false;public var forceGfSing=false;public var noAnimation=false;public var isSustainNote=false;public var noteType='';public var nextNote:Note;public var prevNote:Note;public function new(){}}"""
  actor="""class Character {
   public var animOffsets:Map<String,Array<Float>>=[];public var animTimer=0.;public var voicelining=false;public var holdTimer=8.;public var specialAnim=false;public var heyTimer=0.;public var mostRecentRow=0;
   public var name:String;var log:Array<String>;public function new(n,l){name=n;log=l;}
   public function playAnim(n:String,f:Bool){log.push(name+':anim:'+n+':'+f);}
   public function playGhostAnim(i:Int,n:String,f:Bool){log.push(name+':ghost:'+i+':'+n+':'+f);}
   public function snapshot():String return haxe.Json.stringify([voicelining,holdTimer,specialAnim,heyTimer,mostRecentRow]);
  }"""
  main=r"""
class Globals {public static var Function_Stop=1;}
class Main {
 static function check(b:Bool,s:String){if(!b)throw s;}
 static function main(){
  for(player in [false,true])for(kind in ['', 'Alt Animation','Hey!','Ghost Note'])for(mask in 0...512)for(shape in 0...4)for(link in 0...3){
   var expected:Array<String>=[],actual:Array<String>=[];
   var a=new Character('owner',actual),ag=new Character('gf',actual),b=new Character('owner',expected),bg=new Character('gf',expected);
   for(c in [a,ag,b,bg]){
    c.animTimer=mask&8!=0?0.4:0;c.voicelining=mask&16!=0;c.mostRecentRow=mask&256!=0?4:0;
    if(mask&32!=0)c.animOffsets.set('hey',[0,0]);if(mask&64!=0)c.animOffsets.set('cheer',[0,0]);
   }
   var n=new Note();n.forceGfSing=mask&1!=0;n.noAnimation=mask&2!=0;n.isSustainNote=mask&4!=0;n.mustPress=player;n.noteType=kind;
   if(link>0){n.prevNote=new Note();n.nextNote=new Note();n.nextNote.isSustainNote=link==2;}
   var rows:Array<Array<Array<Note>>>=[[],[],[]];
   if(shape>0){var first=new Note();first.noteData=shape==3?1:0;rows[player?0:1][4]=shape==1?[n]:[first,n];}
   var section:Null<Bool>=(mask+shape)%3==0?null:(mask+shape)%3==1?false:true;
   var ref=new Reference();ref.gf=bg;ref.singAnimations=['singLEFT','singDOWN','singUP','singRIGHT'];ref.noteRows=rows;ref.ghostsAllowed=mask&128!=0;
   ref.SONG={notes:[section==null?null:{altAnim:section}]};ref.gate=function(name,note){check(note==n,'source live note');expected.push('gate:'+name);return mask%3;};
   if(player)ref.good(n,{owner:b});else ref.opponent(n,{owner:b});
   NightmareVisionLegacySinging.sing(n,a,ag,player,ref.singAnimations,rows,ref.ghostsAllowed,section,function(name,note){check(note==n,'host live note');actual.push('gate:'+name);return mask%3;});
   check(expected.join(',')==actual.join(','),'sing order '+player+'/'+kind+'/'+mask+'/'+shape+'/'+link+': '+expected+' != '+actual);
   check(a.snapshot()==b.snapshot()&&ag.snapshot()==bg.snapshot(),'singer state');
  }
 }
}
"""
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   work=FixturePath(directory)
   for name,text in {'Main':main,'Reference':reference,'Note':note,'Character':actor,'Globals':'class Globals {public static var Function_Stop=1;}','NightmareVisionLegacySinging':(ROOT/'source/NightmareVisionLegacySinging.hx').read_text()}.items():
    if name=='Main':text=text.replace('class Globals {public static var Function_Stop=1;}','')
    (work/(name+'.hx')).write_text(text,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
 def test_generated_row_membership_and_head_sustain_links(self):
  donor=ROOT.parent/'fnf_sources/NightmareVision'
  if not donor.is_dir():self.skipTest('pinned historical source unavailable')
  source=subprocess.check_output(['git','show',REV+':source/meta/states/PlayState.hx'],cwd=donor,text=True)
  start=source.index('swagNote.row = Conductor.secsToRow(daStrumTime);')
  reference=source[start:source.index('swagNote.mustPress = gottaHitNote;',start)]
  host=(ROOT/'source/PlayState.hx').read_text()
  start=host.index('swagNote.row = nightmareVisionConductor.secsToRow(daStrumTime);')
  actual=host[start:host.index('rows[swagNote.row].push(swagNote);',start)+len('rows[swagNote.row].push(swagNote);')]
  actual=actual.replace('nightmareVisionConductor.secsToRow','Conductor.secsToRow')
  constructor=(ROOT/'source/Note.hx').read_text()
  start=constructor.index('if (nightmareVisionLegacyGeometry) {',constructor.index('visualTime = PlayState.instance.sourceNoteVisualTime'))
  link=extract_method(constructor[start:],'if (nightmareVisionLegacyGeometry)')
  source_note=subprocess.check_output(['git','show',REV+':source/gameObjects/Note.hx'],cwd=donor,text=True)
  constructor_ref=extract_method(source_note,'public function new(strumTime:Float')
  first=constructor_ref[constructor_ref.index('if (prevNote == null)'):constructor_ref.index('this.player = player;')]
  last=constructor_ref[constructor_ref.index('if(prevNote!=null)'):constructor_ref.index('if (isSustainNote && prevNote != null)')]
  fixture="""
class Conductor { public static function secsToRow(t:Float):Int return Std.int(t/10); }
class Note {
 public var id:Int; public var row=0; public var prevNote:Note; public var nextNote:Note;
 public function new(id:Int) this.id=id;
 public function link(legacy:Bool,sustain:Bool,previous:Note):Void {
  var nightmareVisionLegacyGeometry=legacy;var isSustainNote=sustain;
  this.prevNote=previous==null?this:previous;
  __LINK__
 }
 public function reference(prevNote:Note):Void { __FIRST__ __LAST__ }
}
class Main {
 static function actual(noteRows:Array<Array<Array<Note>>>,swagNote:Note,gottaHitNote:Bool,daStrumTime:Float){__ACTUAL__}
 static function reference(noteRows:Array<Array<Array<Note>>>,swagNote:Note,gottaHitNote:Bool,daStrumTime:Float){__REFERENCE__}
 static function check(b:Bool,s:String){if(!b)throw s;}
 static function main(){
  var a:Array<Array<Array<Note>>>=[[],[]],b:Array<Array<Array<Note>>>=[[],[]];
  for(i in 0...200){var n=new Note(i),m=new Note(i);var time=(i%17)*13.5;
   actual(a,n,i%3==0,time);reference(b,m,i%3==0,time);
   check(n.row==m.row,'row conversion differs');
  }
  for(side in 0...2) for(row in 0...a[side].length){
   var ar=a[side][row],br=b[side][row];
   check((ar==null)==(br==null),'sparse row admission');
   if(ar!=null) check([for(n in ar)n.id].join(',')==[for(n in br)n.id].join(','),'side/order/membership');
  }
  var previous=new Note(-1);
  var head=new Note(0),refHead=new Note(0);
  head.link(true,false,previous);refHead.reference(null);
  check(head.prevNote==head && head.nextNote==head && refHead.prevNote==refHead && refHead.nextNote==refHead,'head self links');
  var cursor=head,refCursor=refHead;
  for(i in 1...9){
   var tail=new Note(i),refTail=new Note(i);
   tail.link(true,true,cursor);refTail.reference(refCursor);
   check(tail.prevNote.id==refTail.prevNote.id && cursor.nextNote==tail && refCursor.nextNote==refTail,'sustain links');
   cursor=tail;refCursor=refTail;
  }
  check(cursor.nextNote==null && refCursor.nextNote==null && previous.nextNote==null,'tail/other head boundaries');
  var modern=new Note(99);modern.link(false,false,previous);
  check(modern.prevNote==previous && modern.nextNote==null && previous.nextNote==null,'modern links unchanged');
 }
}
"""
  for key,value in {'LINK':link,'FIRST':first,'LAST':last,'ACTUAL':actual,'REFERENCE':reference}.items():fixture=fixture.replace('__'+key+'__',value)
  with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
   work=FixturePath(directory);(work/'Main.hx').write_text(fixture,encoding='utf-8')
   result=subprocess.run([*HAXE_COMMAND,'-cp',str(work),'-main','Main','--interp'],cwd=ROOT,text=True,capture_output=True,timeout=60)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__':unittest.main()
