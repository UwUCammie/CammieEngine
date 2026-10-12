"""Owner-scoped authored menu order, stable registry slots and portable import metadata."""
from pathlib import Path
import json,subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]
class AuthoredFreeplayOrderTest(unittest.TestCase):
    def test_owner_menu_metadata_and_stable_presentation_slots(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as td:
            base=Path(td)
            def put(path,value):
                file=base/path;file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text(value if isinstance(value,str) else json.dumps(value),encoding="utf-8")
            put('psych/weeks/weekList.txt','second\nfirst\nsecond\n../other\n')
            put('psych/weeks/first.json',{'songs':[['Dad Battle'],['Bopeebo']]})
            put('psych/weeks/second.json',{'songs':[['Fresh'],['Dad Battle']]})
            put('psych/weeks/extra.json',{'songs':[['Extra']]})
            put('psych/weeks/hidden.json',{'songs':[['Hidden']],'hideFreeplay':True})
            put('psych/weeks/broken.json','not json')
            put('nv/data/weeks/w1.json',{'songs':[['Blue Guy'],['Red Guy']]})
            put('nv/data/weeks/w2.json',{'songs':[['Green Guy']]})
            put('nv/data/freeplay.json',{'tabs':[{'songs':['Intro'], 'fromWeeks':['w2']},
                                                  {'fromWeeks':['w1','missing'],'songs':['Blue Guy','Outro']}]})
            put('other/weeks/w1.json',{'songs':[['Sibling']]})
            put('bad/data/freeplay.json',{'tabs':'invalid'})
            put('bad/data/weeks/weekList.txt','../other\n')
            before={str(f):f.read_bytes() for f in base.rglob('*') if f.is_file()}
            body=r"""import LibrarySort.LibrarySortRow;
class Main {
 static function check(v:Bool,m:String){if(!v)throw m;}
 static function row(i:Int,owner:String,rank:Null<Int>):LibrarySortRow
  return {index:i,id:'id'+i,title:'Title'+i,owner:owner,modTitle:owner,engine:'Psych',ordinal:i,favorite:false,random:false,authored:rank};
 static function main(){
  var base=Sys.args()[0];
  var psych=PsychFreeplayOrder.read(base+'/psych',base+'/psych',base+'/psych/data',false,haxe.Json.parse);
  check(psych.get('fresh')==0 && psych.get('dad-battle')==1 && psych.get('bopeebo')==2 && psych.get('extra')==3,'week precedence or first appearance wrong');
  check(!psych.exists('hidden') && !psych.exists('sibling'),'hidden or foreign owner menu entries leaked');
  var nv=PsychFreeplayOrder.read(base+'/nv',base+'/nv',null,true,haxe.Json.parse);
  check(nv.get('green-guy')==0 && nv.get('intro')==1 && nv.get('blue-guy')==2 && nv.get('red-guy')==3 && nv.get('outro')==4,'NV tab/fromWeeks/songs order wrong');
  var bad=PsychFreeplayOrder.read(base+'/bad',base+'/other',null,true,haxe.Json.parse);
  check(!bad.keys().hasNext(),'out-of-owner content root leaked');
  check(FreeplayAuthoredOrder.rank(-1)==null && FreeplayAuthoredOrder.rank('1')==null && FreeplayAuthoredOrder.rank(1.5)==null && FreeplayAuthoredOrder.rank(0)==0,'malformed rank accepted');
  var rows=[row(0,'a',2),row(1,'b',null),row(2,'a',0),row(3,'c',null),row(4,'a',null),row(5,'b',1),row(6,'a',1)];
  var original=haxe.Json.stringify(rows);
  check(LibrarySort.order(rows,'flat','default','default').join(',')=='2,5,6,3,0,1,4','authored rows escaped owner slots or unknowns lost fallback');
  check(LibrarySort.order(rows,'mod','default','default').join(',')=='2,6,0,4,5,1,3','default group order used local ranks instead of registry');
  check(LibrarySort.order(rows,'mod','za','default').join(',')=='3,5,1,2,6,0,4','group order not independent');
  check(LibrarySort.order(rows,'flat','default','az').join(',')=='0,1,2,3,4,5,6','authored order overrode explicit chart choice');
  check(haxe.Json.stringify(rows)==original,'presentation changed registry');
  var expected=LibrarySort.order(rows,'flat','default','default').join(',');
  rows.reverse();check(LibrarySort.order(rows,'flat','default','default').join(',')==expected,'input enumeration changed order');
  var random=row(7,'a',0);random.random=true;rows.push(random);
  check(LibrarySort.order(rows,'flat','default','default')[0]==7,'Random action lost pinned position');
  // Missing menu metadata leaves the registry exactly as it was.
  for(row in rows)row.authored=null;
  check(LibrarySort.order(rows,'flat','default','default').join(',')=='7,0,1,2,3,4,5,6','legacy fallback changed');
 }
}"""
            (base/'Main.hx').write_text(body)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(base),'--run','Main',str(base)],cwd=ROOT,text=True,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            for name,value in before.items():self.assertEqual(Path(name).read_bytes(),value)

    def test_actual_discovery_annotation_and_registry_payload(self):
        source=(ROOT/'source/ModuleFunctions.hx').read_text()
        start=source.index('\t\t\tvar ownerOrders:Map')
        stop=source.index('\n\t\t\t\tvar key = StringTools.trim(song.name)',start)
        annotation=source[start:stop]+'\n}\n'
        start=source.index('\t\tvar authoredOrder = FreeplayAuthoredOrder.rank')
        stop=source.index('\n\t\tvar authoredRatings =',start)
        publication=source[start:stop]
        body=r"""class Main {
 static function importPathKey(p:String):String return p==null?'':haxe.io.Path.normalize(p);
 static function annotate(root:Dynamic,songs:Array<Dynamic>):Void { ANNOTATION }
 static function publish(songData:Dynamic):Dynamic {
  var freeplayEntry:Dynamic={name:songData.name};
  PUBLICATION
  return haxe.Json.parse(haxe.Json.stringify(freeplayEntry));
 }
 static function check(v:Bool,m:String){if(!v)throw m;}
 static function main(){
  var base=Sys.args()[0];var root={root:base,contentRoot:base, data:base+'/data',engine:ImportEngine.PSYCH};
  var songs:Array<Dynamic>=[{name:'renamed-destination',sourceRoot:base,sourceFolder:'fresh'},
   {name:'fresh--child',sourceRoot:base+'/child',sourceFolder:'fresh'},
   {name:'old',sourceRoot:base,sourceFolder:'unlisted'}];
  annotate(root,songs);
  check(publish(songs[0]).authoredFreeplayOrder==0,'parent rank lost between discovery and registry');
  check(publish(songs[1]).authoredFreeplayOrder==1,'child inherited parent rank or destination name became identity');
  check(!Reflect.hasField(publish(songs[2]),'authoredFreeplayOrder'),'unlisted rank fabricated');
  var refresh=haxe.Json.parse(haxe.Json.stringify(songs));
  annotate(root,refresh);
  check(haxe.Json.stringify(publish(refresh[1]))==haxe.Json.stringify(publish(songs[1])),'repeat discovery changed metadata');
  root.engine=ImportEngine.CODENAME;
  var other:Array<Dynamic>=[{name:'fresh',sourceRoot:base,sourceFolder:'fresh'}];annotate(root,other);
  check(!Reflect.hasField(publish(other[0]),'authoredFreeplayOrder'),'Psych metadata applied to other engine');
 }
}""".replace('ANNOTATION',annotation).replace('PUBLICATION',publication)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as td:
            base=Path(td)
            for folder,songs in [('',['Fresh']),('child',['First','Fresh'])]:
                weeks=base/folder/'weeks';weeks.mkdir(parents=True)
                (weeks/'one.json').write_text(json.dumps({'songs':[[name] for name in songs]}))
            (base/'Main.hx').write_text(body)
            (base/'CoolUtil.hx').write_text('class CoolUtil {public static function parseJson(s:String):Dynamic return haxe.Json.parse(s);}')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(base),'--run','Main',str(base)],cwd=ROOT,text=True,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
