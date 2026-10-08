"""Collision-qualified destination IDs retain source difficulty identities."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND
from test_freeplay_random_difficulty import extract_method

ROOT = Path(__file__).resolve().parents[2]


class ImportChartCollisionNamesTest(unittest.TestCase):
    def test_source_folder_default_and_custom_difficulty_mapping(self):
        source = (ROOT/'source/ModuleFunctions.hx').read_text()
        method = extract_method(source, 'static function importedChartFileName(')
        main = '''import haxe.io.Path;
using StringTools;
class Main {
static function getImportDifficultyNames():Array<String> return ["easy","normal","hard"];
''' + method + '''
static function main() {
var target="source-song--psych-engine-owner";
var inputs=["source-song.json","source-song-easy.json","source-song-hard.json","source-song-expert.jsonc"];
var expected=[target+".json",target+"-easy.json",target+"-hard.json",target+"-expert.json"];
for(i in 0...inputs.length) {
 if(importedChartFileName(target,"assets/data/source-song/"+inputs[i],i,"source-song")!=expected[i])
   throw "collision changed authoritative source difficulty";
}
if(importedChartFileName("source-song","source-song-hard.json",2)!="source-song-hard.json") throw "legacy default caller changed";
if(importedChartFileName(target,"normal.json",1,"source-song")!=target+".json") throw "bare normal alias changed";
if(importedChartFileName(target,"source-song-normal.json",1,"source-song")!=target+".json") throw "source-prefixed normal alias lost";
if(importedChartFileName("source-song","source-song-normal.json",1,"source-song")!="source-song.json") throw "unqualified source-prefixed normal alias lost";
if(importedChartFileName(target,"special-night.json",0,"source-song")!=target+"-special-night.json") throw "custom source suffix lost";
if(importedChartFileName(target,"source-song.json",0)!=target+"-source-song.json") throw "optional absent source identity guessed";
if(importedChartFileName(target,"source-song.json",0,"../source-song")!=target+"-source-song.json") throw "unsafe source identity accepted";
if(importedChartFileName(target,"SOURCE-SONG-HARD.JSON",0,"Source-Song")!=target+"-hard.json") throw "case insensitive source identity lost";
for(engine in ["Psych Engine","Nightmare Vision","Kade Engine","Modding Plus","FPS Plus","Legacy FNF/Polymod"]) {
 var current=ImportRevision.current(engine);
 var minimumNamingRevision=engine=="Nightmare Vision"?5:2;
 if(current.engineRevision<minimumNamingRevision || current.commonRevision<3) throw "affected naming importer stamp too old";
 current.engineRevision=1;
 if(ImportRevision.assess(current,engine).status!=ImportRevision.OUTDATED) throw "prior naming importer remained current";
}
var priorNmv={schemaVersion:1,commonRevision:3,sourceEngine:"Nightmare Vision",engineRevision:3};
if(ImportRevision.assess(priorNmv,"Nightmare Vision").status!=ImportRevision.OUTDATED)
 throw "prior Nightmare Vision package-family receipts were not scheduled for refresh";
if(ImportRevision.current("V-Slice").engineRevision!=2)
 throw "V-Slice variation discovery revision was not recorded";
if(ImportRevision.current("Codename Engine").engineRevision!=1)
 throw "unaffected Codename importer was forced to refresh";
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text(main)
            result = subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],
                cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_song_import_calls_supply_authoritative_source_folder(self):
        source=(ROOT/'source/ModuleFunctions.hx').read_text()
        calls=[line.strip() for line in source.splitlines() if 'importedChartFileName(' in line and 'function ' not in line]
        self.assertEqual(len(calls),4)
        self.assertTrue(all("Reflect.field(songData, 'sourceFolder')" in line for line in calls),calls)


if __name__=='__main__':
    unittest.main()
