"""Execute source Codename input-line ownership without launching the game."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameInputLineTest(unittest.TestCase):
    def test_donor_cpu_banks_mutation_refresh_and_release(self):
        fixture = r'''
class Main {
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function main():Void {
  var solo={name:'solo'},p1={name:'p1'},p2={name:'p2'},custom={name:'custom'};
  var slots:Map<Int,Array<String>>=[];
  var receptorSlots:Map<Int,Array<Dynamic>>=[];
  var visibility:Map<Int,Bool> = [];
  slots.set(0,['dad','dad-copy']);slots.set(1,['bf']);
  slots.set(2,['gf']);slots.set(3,['extra']);slots.set(4,['inferred']);
  for(index in 0...5) receptorSlots.set(index,[{source:index,exists:true,alive:true}]);
  var visibleCallback=function(index:Int,value:Bool):Void visibility.set(index,value);
  var lookup=function(index:Int):Array<String> return slots.get(index);
  for(opp in [false,true]) for(coop in [false,true]) {
   for(type in [null,0,1,2,3]) {
    var index=type==null?4:type;
    var line=new CodenameInputLine<String>(index,type,opp,coop,false,
     solo,p1,p2,lookup,null,function(sourceIndex:Int):Dynamic return receptorSlots.get(sourceIndex));
    var expectedCpu=type==2 || (!coop
     && !((type==1 && !opp) || (type==0 && opp)));
    var expectedBank=coop ? (((type==1)!=opp) ? p1 : p2) : solo;
    check(line.cpu==expectedCpu,'cpu formula '+type+':'+opp+':'+coop);
    check(line.controls==expectedBank,'control-bank formula '+type+':'+opp+':'+coop);
    check(line.canProcessInput()==!expectedCpu,'input ownership '+type+':'+opp+':'+coop);
    check(line.ID==index && line.lineIndex==index,'source identity');
    check(line.characters.length==slots.get(index).length
     && line.characters[0]==slots.get(index)[0],
     'initial actor slots');
    check(line.members==receptorSlots.get(index),
     'native receptor members were copied or resolved from another line');
   }
  }
  var line=new CodenameInputLine<String>(0,0,false,false,false,
   solo,p1,p2,lookup,null,function(sourceIndex:Int):Dynamic return receptorSlots.get(sourceIndex));
  var allLines:Array<Null<CodenameInputLine<String>>>=[line,null];
  var collection=new CodenameStrumLineCollection<String>(allLines);
  check(collection.members==allLines,'collection copied the live source lines');
  var visited=0;
  for(sourceLine in collection) {
   if(visited==0)check(sourceLine==line,'collection line order');
   if(visited==1)check(sourceLine==null,'collection lost an empty source slot');
   visited++;
  }
  check(visited==2,'collection iteration count');
  var auxHead={codenameOrigin:{engine:'codename',lineIndex:3},strumTime:30,color:0,alive:true};
  var auxEarly={codenameOrigin:{engine:'codename',lineIndex:3},strumTime:10,color:0,alive:true};
  var auxDynamic={codenameOrigin:{engine:'codename',lineIndex:3},strumTime:20,color:0,alive:true};
  var auxBoundary={codenameOrigin:{engine:'codename',lineIndex:3},strumTime:1500,color:0,alive:true};
  var auxFuture={codenameOrigin:{engine:'codename',lineIndex:3},strumTime:1501,color:0,alive:true};
  var unrelated={codenameOrigin:{engine:'codename',lineIndex:2},strumTime:20,color:0,alive:true};
  var pending:Array<Dynamic>=[auxHead,unrelated,auxBoundary,auxFuture,auxEarly];
  var active:Array<Dynamic>=[auxHead,auxDynamic,auxDynamic];
  var noteIndex=CodenameLineNoteQuery.index(pending);
  var resolveLineNotes=function(index:Int):Array<Dynamic>
   return CodenameLineNoteQuery.collectIndexed(index,noteIndex,active);
  var songPosition=0.0;
  var auxiliary=new CodenameInputLine<String>(3,2,false,false,false,
   solo,p1,p2,lookup,null,null,true,4,null,null,null,null,null,null,resolveLineNotes,
   function():Float return songPosition);
  var noteView=auxiliary.notes;
  check(CodenameInputLineScriptAccess.getNotes(auxiliary)==noteView,
   'typed Codename script access returned a detached notes group');
  check(noteView.limit==1500 && noteView.members.length==5 && noteView.get(0)==auxEarly
   && noteView.get(1)==auxDynamic && noteView.get(2)==auxHead
   && noteView.get(3)==auxBoundary && noteView.get(4)==auxFuture && noteView.length==5,
   'source notes view lost its type-2 line or chart order');
  noteView.get(0).color=0xFFFFE600;
  check(auxEarly.color==0xFFFFE600,
   'source notes view did not expose the live native note sprite');
  var visitedNotes=0;
  for(note in noteView) visitedNotes++;
  check(visitedNotes==5,'source notes view did not expose the full authored chart');
  var liveNotes:Array<Dynamic>=[];
  noteView.forEachAlive(function(note) liveNotes.push(note));
  check(liveNotes.length==4 && liveNotes[0]==auxEarly && liveNotes[1]==auxDynamic
   && liveNotes[2]==auxHead && liveNotes[3]==auxBoundary,
   'source notes group did not limit forEachAlive to the 1500ms lead-in window');
  songPosition=1;
  liveNotes.resize(0);
  noteView.forEachAlive(function(note) liveNotes.push(note));
  check(liveNotes.length==5 && liveNotes[4]==auxFuture,
   'source notes group did not use the live song clock at the inclusive window boundary');
  songPosition=1400;
  noteView.limit=100;
  liveNotes.resize(0);
  noteView.forEachAlive(function(note) liveNotes.push(note));
  check(liveNotes.length==4 && liveNotes[3]==auxBoundary,
   'mutable source note limit did not control forEachAlive visibility');
  pending.remove(auxEarly);active.push(auxEarly);
  check(noteView.members.length==5 && noteView.members[0]==auxEarly,
   'source notes view did not follow pending-to-active note movement');
  auxEarly.alive=false;
  check(noteView.members.length==4 && noteView.members[0]==auxDynamic
   && noteView.members[1]==auxHead,
   'source notes view retained a retired native note');
  liveNotes.resize(0);
  noteView.forEachAlive(function(note) liveNotes.push(note));
  check(liveNotes.length==3 && liveNotes[0]==auxDynamic && liveNotes[1]==auxHead
   && liveNotes[2]==auxBoundary,
   'source notes group callback included a retired or out-of-window note');
  auxiliary.release();
  check(noteView.members.length==0,
   'released source notes view retained its chart resolver');
  var scriptView=new CodenameStrumlineScriptView<String>();
  var bridgedLine=new CodenameInputLine<String>(1,1,false,false,false,
   solo,p1,p2,lookup,null,null,true,4,null,null,null,null,null,scriptView.onMiss);
  var bridgeMisses:Array<String>=[];
  var bridgeMiss=function(e:Dynamic) bridgeMisses.push(e.kind);
  check(bridgedLine.onMiss==scriptView.onMiss,'native and input-line miss signals differ');
  scriptView.cpu=true;
  scriptView.bind(bridgedLine);
  check(scriptView.cpu && bridgedLine.cpu && !bridgedLine.canProcessInput(),
   'pre-bind cpu assignment did not reach source input ownership');
  scriptView.onMiss.add(bridgeMiss);
  bridgedLine.onMiss.dispatch({kind:'shared'});
  check(bridgeMisses.join(',')=='shared','native onMiss listener did not receive line dispatch');
  bridgedLine.cpu=false;
  check(!scriptView.cpu && bridgedLine.canProcessInput(),
   'native cpu view did not read a live input-line mutation');
  scriptView.cpu=true;
  check(bridgedLine.cpu && !bridgedLine.canProcessInput(),
   'native cpu view did not update source input ownership');
  scriptView.unbind(bridgedLine);
  bridgedLine.release();
  check(!scriptView.cpu && !scriptView.onMiss.has(bridgeMiss)
   && !bridgedLine.onMiss.has(bridgeMiss),
   'strumline bridge cleanup retained CPU state or miss listeners');
  var demoScriptView=new CodenameStrumlineScriptView<String>();
  var demoLine=new CodenameInputLine<String>(1,1,false,false,true,
   solo,p1,p2,lookup,null,null,true,4,null,null,null,null,null,demoScriptView.onMiss);
  demoScriptView.bind(demoLine);
  check(demoScriptView.cpu && !demoLine.cpu && !demoLine.canProcessInput(),
   'first script callback must see effective CPU during constructor-selected demo botplay');
  demoScriptView.cpu=false;
  check(demoScriptView.cpu && !demoLine.cpu && demoLine.botplay,
   'script CPU ownership writes must not disable effective botplay or rewrite its flag');
  demoLine.botplay=false;
  check(!demoScriptView.cpu && !demoLine.cpu && demoLine.canProcessInput(),
   'effective script CPU must follow live botplay shutdown while preserving authored ownership');
  demoLine.cpu=true;
  check(demoScriptView.cpu && demoLine.cpu,
   'effective CPU view must still expose authored CPU ownership when botplay is off');
  demoLine.release();
  demoScriptView.unbind(demoLine);
  var order:Array<String>=[];
  var first=function(e:Dynamic) order.push('first:'+e.kind);
  var once=function(e:Dynamic) order.push('once:'+e.kind);
  line.onHit.add(first);line.onHit.add(first);line.onHit.addOnce(once);
  line.onHit.dispatch({kind:'tap'});line.onHit.dispatch({kind:'hold'});
  check(order.join(',')=='first:tap,once:tap,first:hold'&&line.onHit.has(first)
   &&!line.onHit.has(once),'hit signal order/once/dedup');
  line.onMiss.add(first);line.onMiss.dispatch({kind:'miss'});
  check(order[order.length-1]=='first:miss','miss signal');
  check(line.cpu && !line.canProcessInput(),'normal opponent CPU');
  check(line.animSuffix=='' && !line.altAnim
   && line.noteAnimSuffix(null)=='' && line.noteAnimSuffix('mine')=='mine',
   'source line suffix defaults');
  line.altAnim=true;
  check(line.altAnim && line.animSuffix=='-alt'
   && line.noteAnimSuffix(null)=='-alt' && line.noteAnimSuffix('')=='',
   'line alt suffix or explicit note override');
  line.defaultAnimSuffix='-alt2';
  check(!line.altAnim && line.animSuffix=='-alt',
   'changing default suffix unexpectedly rewrote the live suffix');
  line.altAnim=true;
  check(line.altAnim && line.animSuffix=='-alt2','reset did not use new default suffix');
  line.altAnim=false;
  check(!line.altAnim && line.animSuffix=='','disable did not clear suffix');
  line.cpu=false;line.controls=custom;line.ID=99;
  check(line.canProcessInput() && line.controls==custom && line.lineIndex==0,
   'script changes to cpu/controls/ID not retained');
  line.characters.push('script-added');
  check(line.characters[2]=='script-added','script actor edit vanished before refresh');
  check(line.commitScriptCharacters() && line.actorSlots[2]=='script-added',
   'script actor edit was not folded into the indexed engine slots');
  var sparse=new CodenameInputLine<String>(2,2,false,false,false,
   solo,p1,p2,function(_) return cast [null,'gf',null]);
  check(sparse.actorSlots.length==3 && sparse.actorSlots[0]==null
   && sparse.actorSlots[1]=='gf' && sparse.characters.length==1
   && sparse.characters[0]=='gf',
   'unresolved authored slots leaked into the script-facing actor list');
  sparse.characters[0]='replacement';
  check(sparse.commitScriptCharacters() && sparse.actorSlots.length==3
   && sparse.actorSlots[0]==null && sparse.actorSlots[1]=='replacement'
   && sparse.actorSlots[2]==null,
   'compact script replacement shifted the type-2 actor occurrence');
  sparse.characters.push('extra');
  sparse.commitScriptCharacters();
  check(sparse.actorSlots.length==4 && sparse.actorSlots[3]=='extra',
   'script append did not preserve the existing indexed slots');
  sparse.characters.push(null);
  check(sparse.characters.length==2 && sparse.characters[0]=='replacement'
   && sparse.characters[1]=='extra',
   'direct script mutation exposed a null actor during a callback');
  var firstReceptors=line.members;
  var replacementAlive={source:'replacement',exists:true,alive:true};
  var replacementDead={source:'dead',exists:true,alive:false};
  var replacementMissing={source:'missing',exists:false,alive:true};
  var replacementReceptors=[replacementAlive,replacementDead,replacementMissing,null];
  receptorSlots.set(0,replacementReceptors);
  check(line.members[0].source=='replacement' && firstReceptors[0].source==0,
   'receptor view did not follow the current native member array');
  var liveReceptors:Array<Dynamic>=[];
  line.forEachAlive(function(receptor) liveReceptors.push(receptor));
  check(liveReceptors.length==1 && liveReceptors[0]==replacementAlive,
   'source StrumLine forEachAlive did not filter dead, nonexistent, or null receptors');
  var iterated:Array<Dynamic>=[];
  for(receptor in line) iterated.push(receptor);
  check(iterated.length==4 && iterated[0].source=='replacement'
   && iterated[1]==replacementDead && iterated[3]==null,
   'source StrumLine iteration did not expose current receptors');
  var nestedChild={source:'nested-child',exists:true,alive:true};
  var nestedGroup:Dynamic={source:'nested-group',exists:true,alive:true,
   flixelType:2,members:[nestedChild]};
  Reflect.setField(nestedGroup,'forEachAlive',function(callback:Dynamic,recurse:Bool=false):Void {
   for(member in (cast nestedGroup.members:Array<Dynamic>)) if(member!=null&&member.exists&&member.alive)
    Reflect.callMethod(null,callback,[member]);
  });
  var nestedReceptors=[nestedGroup];receptorSlots.set(0,nestedReceptors);
  var shallow:Array<Dynamic>=[];
  line.forEachAlive(function(receptor) shallow.push(receptor));
  check(shallow.length==1 && shallow[0]==nestedGroup,
   'source StrumLine forEachAlive recursed without the recurse flag');
  var recursive:Array<Dynamic>=[];
  line.forEachAlive(function(receptor) recursive.push(receptor),true);
  check(recursive.length==2 && recursive[0]==nestedChild && recursive[1]==nestedGroup,
   'source StrumLine forEachAlive did not visit alive subgroup members before the group');
  slots.set(0,['new-dad','new-copy']);
  check(line.characters[0]=='dad','actor view changed without explicit refresh');
  var view=line;line.refreshActors();
  check(view==line && line.characters.join(',')=='new-dad,new-copy'
   && line.ID==99 && line.lineIndex==0,'swap refresh lost identity or kept stale actors');
  var bot=new CodenameInputLine<String>(1,1,false,false,true,
   solo,p1,p2,lookup);
  check(!bot.cpu && !bot.canProcessInput(),'botplay rewrote donor cpu or sampled keys');
  bot.botplay=false;check(bot.canProcessInput(),'live botplay switch');
  var gameGhost=false;
  var ghostLine=new CodenameInputLine<String>(1,1,false,false,false,
   solo,p1,p2,lookup,function() return gameGhost);
  check(ghostLine.ghostTapping==false,'disabled donor fallback');
  gameGhost=true;
  check(ghostLine.ghostTapping==true,'live donor fallback');
  ghostLine.ghostTapping=false;
  check(ghostLine.ghostTapping==false,'line override');
  ghostLine.ghostTapping=null;
  check(ghostLine.ghostTapping==true,'cleared line override');
  var authoredLine=new CodenameInputLine<String>(2,2,false,false,false,
   solo,p1,p2,lookup,null,function(sourceIndex:Int):Dynamic return receptorSlots.get(sourceIndex),
   false,6,0.4,[0,90],0.75,1.5,function(value:Bool):Void visibleCallback(2,value));
  check(authoredLine.visible==false && visibility.get(2)==false,
   'initial source visibility did not reach its unique receptor group');
  check(authoredLine.keyCount==6 && authoredLine.strumLinePos==0.4
   && authoredLine.strumPos[1]==90 && authoredLine.strumScale==0.75
   && authoredLine.strumSpacing==1.5,'source line geometry was not retained');
  authoredLine.visible=true;
  check(authoredLine.visible && visibility.get(2)==true,
   'mutable source visibility did not update its receptor group');
  authoredLine.release();
  ghostLine.release();
  line.release();line.release();
  check(!line.onHit.has(first)&&!line.onMiss.has(first),'release retained signal listener');
  check(line.released && line.characters.length==0 && line.controls==null
   && !line.canProcessInput() && line.members==null,
   'release retained actor/control/receptor references');
  var afterRelease=0;
  for(receptor in line) afterRelease++;
  check(afterRelease==0,'released source StrumLine remained iterable');
  slots.set(0,['later']);line.refreshActors();
  check(line.characters.length==0,'released line rebound actors');
  var invalid=false;
  try new CodenameInputLine<String>(-1,0,false,false,false,solo,p1,p2,lookup)
   catch(_:Dynamic) invalid=true;
  check(invalid,'negative source index accepted');
  invalid=false;
  try new CodenameInputLine<String>(1,-1,false,false,false,solo,p1,p2,lookup)
   catch(_:Dynamic) invalid=true;
  check(invalid,'negative source type accepted');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            folder = Path(work)
            (folder / 'Main.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'tools/tests/haxe_stubs'), '-cp', str(ROOT / 'source'),
                                     '-cp', str(folder), '--run', 'Main'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
