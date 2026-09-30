"""Execute Codename event provenance through conversion, collection and editing."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameEventMetadataTest(unittest.TestCase):
    def test_authored_payload_identity_and_editor_roundtrip(self):
        fixture = r'''class Main {
 static function check(ok:Bool, message:String):Void if(!ok) throw message;
 static function main():Void {
  var meta:Dynamic={difficulties:["hard"],displayName:"Event Test",bpm:120,stepsPerBeat:4};
  var chart:Dynamic={codenameChart:true,scrollSpeed:1,stage:"stage",strumLines:[],
   events:[
    {name:"Play Animation",time:100.00001,params:([0,"sing",true,"NONE"]:Array<Dynamic>)},
    {name:"Camera Zoom",time:100.00002,params:([false,1.25,"camGame",4,"linear","In","direct",false]:Array<Dynamic>)}
   ]};
  var shared:Dynamic={events:[
   {name:"Play Animation",time:100.00001,params:([0,"sing",false,"DANCE"]:Array<Dynamic>),global:true}
  ]};
  var converted=CodenameImporter.convert(meta,chart,"hard","",shared);
  var groups:Array<Dynamic>=converted.charts[0].chart.song.events;
  check(groups.length==2,"nearby authored timestamps were grouped");
  check(groups[0][0]==100.00001 && groups[1][0]==100.00002,"timestamp precision changed");
  var first:Array<Dynamic>=groups[0][1][0];
  var second:Array<Dynamic>=groups[0][1][1];
  var third:Array<Dynamic>=groups[1][1][0];
  check(first[0]==second[0] && first[1]==second[1] && first[2]==second[2],
   "collision fixture did not share native route");
  var a:Dynamic=CodenameEventMetadata.read(first,100.00001);
  var b:Dynamic=CodenameEventMetadata.read(second,100.00001);
  var c:Dynamic=CodenameEventMetadata.read(third,100.00002);
  check(a!=null && a.id=="chart:0" && a.source=="chart" && a.order==0
   && a.global==false && a.params[2]==true,"chart authored payload lost");
  check(b!=null && b.id=="shared:0" && b.source=="shared" && b.global==true
   && b.params[2]==false && b.params[3]=="DANCE","shared typed params lost");
  check(c!=null && c.id=="chart:1" && c.params[0]==false && c.params[1]==1.25,
   "float/bool payload lost");
  var collected=SongEvents.collect(groups,null);
  check(collected.length==3,"same-time distinct authored events collapsed");
  check(collected[0].codename.id=="chart:0" && collected[1].codename.id=="shared:0"
   && collected[2].time==100.00002,"authored order changed");
  check(SongEvents.collect(groups,groups).length==3,"same rows dispatched twice");
  var distinct:Array<Dynamic>=first.copy();
  distinct[4]=haxe.Json.parse(haxe.Json.stringify(first[4]));
  distinct[4].params[3]="OTHER";
  check(SongEvents.collect(groups,[[100.00001,[distinct]]]).length==4,
   "same ordinal in a different companion discarded distinct payload");
  var fromCompanion:Dynamic={events:[]};
  var companion:Dynamic={events:[groups[0]]};
  ChartEventModel.mergeCompanion(fromCompanion,companion);
  ChartEventModel.mergeCompanion(fromCompanion,companion);
  var imported=ChartEventModel.list(fromCompanion.events);
  check(imported.length==2 && CodenameEventMetadata.read(imported[1].event,imported[1].time)!=null,
   "companion merge lost provenance or duplicated native rows");
  var song:Dynamic={events:groups,notes:[]};
  ChartEventModel.normalizeSong(song);
  var restored:Dynamic=haxe.Json.parse(haxe.Json.stringify(song));
  var refs=ChartEventModel.list(restored.events);
  check(refs.length==3 && CodenameEventMetadata.read(refs[1].event,refs[1].time)!=null,
   "editor JSON roundtrip lost metadata");
  var moved=refs[0];
  check(ChartEventModel.update(restored.events,moved,101.125,"Play Animation","sing","dad",""),
   "time-only edit failed");
  check(CodenameEventMetadata.read(moved.event,101.125)!=null
   && moved.event[4].time==101.125,"time-only edit did not synchronize provenance");
  check(ChartEventModel.update(restored.events,
   ChartEventModel.list(restored.events)[2],101.125,"Changed","sing","dad",""),
   "content edit failed");
  var edited=ChartEventModel.list(restored.events);
  var invalidated=false;
  for(ref in edited) if(ref.event[0]=="Changed")
   invalidated=ref.event.length==4 && CodenameEventMetadata.read(ref.event,ref.time)==null;
  check(invalidated,"manual native edit retained stale authored identity");
  var extended:Array<Dynamic>=first.copy(); extended.push("opaque-extension");
  var extensionGroups:Array<Dynamic>=[[100.00001,[extended]]];
  ChartEventModel.update(extensionGroups,ChartEventModel.list(extensionGroups)[0],
   100.00001,"Edited","sing","dad","");
  check(extended.length==6 && extended[4]==null && extended[5]=="opaque-extension",
   "invalidating provenance shifted unrelated extension columns");
  var cloned:Array<Dynamic>=first.copy(); cloned[1]="tampered";
  check(CodenameEventMetadata.read(cloned,100.00001)==null,"stale route accepted");
  var legacy:Array<Dynamic>=[[100.00001,[["Play Animation","sing","dad",""]]]];
  check(SongEvents.collect(legacy,legacy).length==1,"legacy dedupe changed");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", work, "--run", "Main"], cwd=ROOT, text=True,
                capture_output=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
