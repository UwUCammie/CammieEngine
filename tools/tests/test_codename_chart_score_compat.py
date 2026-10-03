"""Codename Chart.parse, score records, and aliased import compatibility."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


def run_haxe(source: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
        main = Path(folder) / "Main.hx"
        main.write_text(source, newline='\n')
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder,
             "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
             "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"), "--run", "Main"],
            cwd=ROOT, capture_output=True, text=True, timeout=30)


class CodenameChartScoreCompatTest(unittest.TestCase):
    def test_highscore_change_alias_import_and_enum_values_execute(self):
        parser = (ROOT / "source/CodenameScriptParser.hx").read_text()
        self.assertIn("parseImportArgument(mask.substring(cursor, end))", parser)
        self.assertIn("'var ' + alias + ' = ' + argument.split('.').pop() + ';'", parser)
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn("bindings.set('funkin.savedata.HighscoreChange', highscoreChangeConstants());", bindings)
        source = r'''import hscript.Interp;
class Main {
 static function main():Void {
  var constants:Dynamic={CCoopMode:'CCoopMode',COpponentMode:'COpponentMode'};
  var allowed:Map<String,Dynamic>=new Map();
  allowed.set('funkin.savedata.HighscoreChange',constants);
  var src='import funkin.savedata.HighscoreChange as HC;\n'
    +'import funkin.savedata.HighscoreChange as MuchLongerHighscoreChangeAlias;\n'
    +'function getMode() return HC.COpponentMode;\n'
    +'function getLongMode() return MuchLongerHighscoreChangeAlias.COpponentMode;\n'
    +'function getCoop() return HC.CCoopMode;';
  var imports=CodenameScriptParser.importPaths(src);
  if(imports.length!=1 || imports[0]!='funkin.savedata.HighscoreChange')
   throw 'import path lost alias: '+imports;
  var parsed=CodenameScriptParser.prepare(src,allowed);
  if(parsed.program==null || parsed.diagnostics.length!=0)
   throw parsed.diagnostics.length==0 ? 'no parsed script' : parsed.diagnostics[0].message;
  if(parsed.source.indexOf('HC = HighscoreChange;')<0)
   throw 'alias was not lowered to its bound value: '+parsed.source;
  var interp=new Interp();
  interp.variables.set('HighscoreChange',constants);
  interp.execute(parsed.program);
  var getMode:Dynamic=interp.variables.get('getMode');
  var getLongMode:Dynamic=interp.variables.get('getLongMode');
  var getCoop:Dynamic=interp.variables.get('getCoop');
  if(getMode()!='COpponentMode' || getLongMode()!='COpponentMode' || getCoop()!='CCoopMode')
   throw 'aliased enum values changed';
 }
}'''
        result = run_haxe(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_codename_source_and_native_chart_views_keep_metadata_provenance(self):
        source = r'''import haxe.Json;
class Main {
 static function main():Void {
  var source:Dynamic=Json.parse('{"codenameChart":true,"scrollSpeed":1.25,'
    +'"stage":"campus","strumLines":[{"notes":[]}],"meta":{"bpm":132,'
    +'"displayName":"Inline","nullable":null},"events":[{"type":2,"time":10}]}');
  var metadata:Dynamic={name:'song',displayName:'Base',bpm:124,icon:'gf'};
  var parsed=CodenameChartDataCompat.fromSource('song','hard',null,source,metadata,
    {stage:'default-stage',scrollSpeed:0.9});
  if(parsed.meta.bpm!=132 || parsed.meta.displayName!='Inline' || parsed.meta.name!='song'
     || parsed.meta.icon!='gf' || parsed.sourceChartAvailable!=true
     || parsed.strumLines[0].keyCount!=4 || parsed.stage!='campus' || parsed.scrollSpeed!=1.25)
    throw 'source ChartData metadata/default projection changed';
  if(source.strumLines[0].keyCount!=null || source.meta.name!=null)
    throw 'source chart object was mutated';
  var native:Dynamic={song:'song',bpm:131,speed:1.1,stage:'native-stage',events:[]};
  var fallback=CodenameChartDataCompat.fromNative('song','hard',null,native,metadata);
  if(fallback.meta.bpm!=124 || fallback.meta.displayName!='Base'
     || fallback.sourceChartAvailable!=false || fallback.strumLines!=null
     || fallback.nativeChart!=native || fallback.events.length!=0)
    throw 'converted-chart fallback hid authored metadata or source-data gap';
  var rejected=false;
  try CodenameChartDataCompat.fromNative('song','hard','encore',native,metadata)
  catch (_:Dynamic) rejected=true;
  if(!rejected) throw 'unimported variant was silently projected';
 }
}'''
        result = run_haxe(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_score_default_variant_partition_and_source_replacement_rule(self):
        compat = (ROOT / "source/CodenameFunkinSaveCompat.hx").read_text()
        self.assertIn("CodenameHighscoreDataCompat.emptyRecord()", compat)
        self.assertIn("CodenameHighscoreDataCompat.shouldReplace", compat)
        source = r'''class Main {
 static function main():Void {
  var empty=CodenameHighscoreDataCompat.emptyRecord();
  if(empty.score!=0 || empty.accuracy!=0 || empty.misses!=0
     || !Std.isOfType(empty.hits,Array) || empty.hits.length!=0 || empty.date!=null)
   throw 'Codename empty SongScore defaults changed';
  var base=CodenameHighscoreDataCompat.key('Song','Hard',null,[]);
  var same=CodenameHighscoreDataCompat.key('song','hard','',null);
  var variant=CodenameHighscoreDataCompat.key('song','hard','encore',[]);
  var opponent=CodenameHighscoreDataCompat.key('song','hard',null,['COpponentMode']);
  var coop=CodenameHighscoreDataCompat.key('song','hard',null,['CCoopMode']);
  if(base!='song|hard' || same!=base || variant==base || opponent==base
     || coop==base || opponent==coop)
   throw 'score variation and change keys collided';
  var old={score:900,date:'yesterday'};
  if(!CodenameHighscoreDataCompat.shouldReplace(empty,{score:0,date:null})
     || CodenameHighscoreDataCompat.shouldReplace(old,{score:900,date:'today'})
     || !CodenameHighscoreDataCompat.shouldReplace(old,{score:901,date:'today'})
     || !CodenameHighscoreDataCompat.shouldReplace(old,{score:0,date:'today'},true))
   throw 'Codename highscore replacement semantics changed';
  var record={score:17,accuracy:0.98,misses:2,hits:{sick:12},date:'now'};
  var snapshot=CodenameHighscoreDataCompat.snapshot(record);
  snapshot.hits.sick=1;
  if(record.hits.sick!=12) throw 'score snapshot shares mutable nested state';
 }
}'''
        result = run_haxe(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_chart_and_score_bindings_are_shared_across_codename_contexts(self):
        bindings = (ROOT / "source/CodenameImportBindings.hx").read_text()
        self.assertIn("CodenameChartCompat.facade(paths)", bindings)
        self.assertIn("bindings.set('funkin.backend.chart.Chart'", bindings)
        self.assertIn("bindings.set('funkin.savedata.FunkinSave', CodenameFunkinSaveCompat);", bindings)
        self.assertIn("highscoreChangeConstants()", bindings)
        for host in ("source/CodenameModBindings.hx", "source/PlayState.hx"):
            self.assertIn("CodenameImportBindings.addShared", (ROOT / host).read_text())


if __name__ == "__main__":
    unittest.main()
