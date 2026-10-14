"""Thin Psych addons need independent chart, callback and week evidence."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]


class ThinPsychAutoDetectionTest(unittest.TestCase):
    def test_structural_evidence_and_ambiguity_guards(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            base=Path(temp)
            for name in ['complete','formatted-week-title','no-week','no-lua','no-chart','unrelated-week','legacy-lua','comment-lua','oversized-lua']:
                root=base/name
                song_folder='dad-battle' if name=='formatted-week-title' else 'track'
                song_title='Dad Battle!' if name=='formatted-week-title' else 'Track'
                (root/'data'/song_folder).mkdir(parents=True)
                (root/'songs'/song_folder).mkdir(parents=True)
                (root/'weeks').mkdir()
                (root/'songs'/song_folder/'Inst.ogg').write_bytes(b'fixture')
                chart={'song':{'song':song_title,'bpm':120,'notes':[{'sectionNotes':[[0,0,0]],'mustHitSection':True}]}}
                if name=='no-chart': chart={'song':{'bpm':120,'notes':[{'wrong':[]}]}}
                (root/'data'/song_folder/(song_folder+'.json')).write_text(json.dumps(chart))
                lua='function onStartCountdown()\n return Function_Continue\nend\n'
                if name=='legacy-lua': lua='function start(song)\nend\n'
                if name=='comment-lua': lua='--[[\nfunction onStartCountdown()\nend\n]]\n'
                if name=='oversized-lua': lua += '-'*(1024*1024)
                if name!='no-lua': (root/'data'/song_folder/'script.lua').write_text(lua)
                if name!='no-week':
                    week={'songs':[['Different' if name=='unrelated-week' else song_title,'actor',[1,2,3]]],'weekCharacters':['','','']}
                    (root/'weeks/week.json').write_text(json.dumps(week))
            (base/'Main.hx').write_text('''class Main { static function main() {
var root=Sys.args()[0];
var found=ImportRootScanner.inspectRoot(root+"/complete",ImportEngine.AUTO);
if(found==null || found.engine!=ImportEngine.PSYCH) throw "thin Psych package was not classified";
if(found.evidence.join(";").indexOf("section chart + callback Lua + week metadata")<0) throw "structural classification evidence absent";
var formatted=ImportRootScanner.detectEngine(root+"/formatted-week-title");
if(formatted!=ImportEngine.PSYCH) throw "Psych display title normalization was not applied";
// A chart with a callback script and nothing else still names no engine.
if(ImportRootScanner.detectEngine(root+"/no-week")==ImportEngine.PSYCH) throw "ambiguous thin package guessed Psych: no-week";
// A Psych week file is format evidence of its own, so these are found through
// it. None of them may claim the chart + callback + week contract they lack.
var thin="section chart + callback Lua + week metadata";
for(name in ["no-lua","legacy-lua","comment-lua","oversized-lua"]) {
 var match=ImportRootScanner.inspectRoot(root+"/"+name,ImportEngine.AUTO);
 if(match==null || match.engine!=ImportEngine.PSYCH) throw "week file listing a charted song was not classified: "+name;
 var evidence=match.evidence.join(";");
 if(evidence.indexOf(thin)>=0) throw "thin contract claimed without a callback script: "+name;
 if(evidence.indexOf("Psych Engine week file listing a charted song: weeks/*.json")<0) throw "week evidence absent: "+name;
}
for(name in ["no-chart","unrelated-week"]) {
 var match=ImportRootScanner.inspectRoot(root+"/"+name,ImportEngine.AUTO);
 if(match==null || match.engine!=ImportEngine.PSYCH) throw "Psych week file was not classified: "+name;
 var evidence=match.evidence.join(";");
 if(evidence.indexOf(thin)>=0) throw "thin contract claimed without a week-listed chart: "+name;
 if(evidence.indexOf("listing a charted song")>=0) throw "week was credited with a chart it does not list: "+name;
 if(evidence.indexOf("Psych Engine week file: weeks/*.json")<0) throw "week evidence absent: "+name;
}
}}
''')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main',temp],
                cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_real_addon_is_read_only_psych_evidence(self):
        addon=ROOT.parent/'fnf_example_mods/psych/Ugh Moment'
        if not addon.is_dir(): self.skipTest('external addon fixture unavailable')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text('''class Main {static function main(){
if(ImportRootScanner.detectEngine(Sys.args()[0])!=ImportEngine.PSYCH) throw "actual thin addon detection failed";
}}
''')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main',str(addon)],
                cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__=='__main__': unittest.main()
