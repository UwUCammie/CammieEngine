"""Psych-family songs fall back to global siblings, the mods folder and game assets from the same import."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath
from tools.haxe_import_io_stubs import install_import_io_dependencies

ROOT = Path(__file__).resolve().parents[2]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


class PsychFamilyModChainTest(unittest.TestCase):
    def run_haxe(self, folder, body, *args):
        (folder / 'Main.hx').write_text('class Main {static function main(){\n' + body + '\n}}', encoding='utf-8')
        result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(folder),
            '--run', 'Main', *map(str, args)], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def release(self, base, container, manifest, flag):
        release = base / container.capitalize()
        write(release / 'assets/data/tutorial/tutorial.json', '{}')
        write(release / container / 'scripts/global.lua', 'function onCreate() end')
        write(release / container / 'G' / manifest, '{"name":"G","%s":true}' % flag)
        write(release / container / 'H' / manifest, '{"name":"H","%s":true}' % flag)
        write(release / container / 'Off' / manifest, '{"name":"Off","%s":true}' % flag)
        write(release / container / 'Local' / manifest, '{"name":"Local","%s":false}' % flag)
        write(release / container / 'A/data/song/song.json', '{}')
        write(release / container / 'B/data/song/song.json', '{}')
        # H is listed first, Off is switched off, G is not listed at all.
        write(release / 'modsList.txt', 'H|1\nA|1\nOff|0\nB|0\n')
        return release

    def test_chain_order_and_filters_match_for_both_engines(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            scratch = FixturePath(temp)
            psych = self.release(scratch, 'mods', 'pack.json', 'runsGlobally')
            nv = self.release(scratch, 'content', 'meta.json', 'global')
            output = self.run_haxe(scratch, r'''
var args = Sys.args();
function names(release:String, container:String, engine:String, self:String, ?extra:Array<PsychFamilyModChain.PsychFamilyModChainRoot>):String {
	var batch:Array<PsychFamilyModChain.PsychFamilyModChainRoot> = [
		{root:release + '/assets', engine:engine},
		{root:release + '/' + container, engine:engine}
	];
	for (name in ['A', 'B', 'G', 'H', 'Off', 'Local']) batch.push({root:release + '/' + container + '/' + name, engine:engine});
	if (extra != null) for (entry in extra) batch.push(entry);
	var out = [];
	for (entry in PsychFamilyModChain.resolve(self, engine, batch)) {
		if (entry.engine != engine) throw 'engine label changed: ' + entry.engine;
		out.push(StringTools.replace(entry.root, release + '/', ''));
	}
	return out.join(',');
}
var psych = args[0];
var nv = args[1];
Sys.println('psych=' + names(psych, 'mods', 'Psych Engine', psych + '/mods/A'));
Sys.println('nv=' + names(nv, 'content', 'Nightmare Vision', nv + '/content/A'));
Sys.println('top=' + names(psych, 'mods', 'Psych Engine', psych + '/mods'));
Sys.println('assets=' + names(psych, 'mods', 'Psych Engine', psych + '/assets'));
// A sibling detected as another engine, or a root from somewhere else, never joins.
Sys.println('foreign=' + names(psych, 'mods', 'Psych Engine', psych + '/mods/A',
	[{root:psych + '/mods/Other', engine:'V-Slice'}, {root:args[2] + '/mods/G', engine:'Psych Engine'}]));
Sys.println('outside=' + names(psych, 'mods', 'Codename Engine', psych + '/mods/A'));
''', psych, nv, scratch / 'elsewhere')
            lines = dict(line.split('=', 1) for line in output.strip().splitlines())
            expected = 'mods/H,mods/G,mods,assets'
            self.assertEqual(lines['psych'], expected)
            self.assertEqual(lines['nv'], expected.replace('mods', 'content'))
            self.assertEqual(lines['top'], 'mods/H,mods/G,assets')
            self.assertEqual(lines['assets'], 'mods/H,mods/G,mods')
            self.assertEqual(lines['foreign'], expected)
            self.assertEqual(lines['outside'], '')

    def test_family_roots_become_ordered_dependencies_behind_the_owner(self):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            folder = FixturePath(temp)
            install_import_io_dependencies(folder)
            for name in ('ImportEngine.hx', 'CompatScriptManifest.hx', 'ImportSongOwnership.hx'):
                (folder / name).write_text((ROOT / 'source' / name).read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
            (folder / 'Main.hx').write_text(r'''class Main {static function main(){
	var owner = '/game/mods/A';
	var data = CompatScriptManifest.create(owner, 'Psych Engine');
	CompatScriptManifest.addDependencyRoots(data, [
		{root:'/game/mods/H', engine:'Psych Engine'}, null, {root:'', engine:'Psych Engine'},
		{root:owner, engine:'Psych Engine'}, {root:'/game/mods', engine:'Psych Engine'},
		{root:'/game/assets', engine:'Psych Engine'}]);
	CompatScriptManifest.addDependencyRoots(data, null);
	var normalized = CompatScriptManifest.normalize(data);
	var own = CompatScriptManifest.destinationRoot(owner, 'Psych Engine');
	if (normalized.selectedRoot != own) throw 'owner lost: ' + normalized.selectedRoot;
	var expected = [own, CompatScriptManifest.destinationRoot('/game/mods/H', 'Psych Engine'),
		CompatScriptManifest.destinationRoot('/game/mods', 'Psych Engine'),
		CompatScriptManifest.destinationRoot('/game/assets', 'Psych Engine')];
	var ordered = CompatScriptManifest.rootsInPrecedence(normalized);
	if (ordered.length != expected.length) throw 'roots: ' + haxe.Json.stringify(ordered);
	for (i in 0...expected.length) {
		if (ordered[i].path != expected[i]) throw 'order ' + i + ': ' + haxe.Json.stringify(ordered);
		if ((ordered[i].dependency == true) != (i > 0)) throw 'dependency flag ' + i + ': ' + haxe.Json.stringify(ordered);
	}
}}''', encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(folder), '--run', 'Main'],
                cwd=folder, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_lists_family_roots_as_dependencies_in_order(self):
        source = (ROOT / 'source/ModuleFunctions.hx').read_text(encoding='utf-8')
        start = source.index('static function writeCompatScriptManifest(')
        body = source[start:source.index('desired = CompatScriptManifest.normalize(desired);', start)]
        family = body.index("CompatScriptManifest.addDependencyRoots(desired, Reflect.field(songData, 'familyDependencyRoots'))")
        installed = body.index("'installedDependencyRoots'")
        # The same-import chain comes before the inferred installed base.
        self.assertLess(family, installed)
        discovery = source[source.index('static public function discoverSongImportsDetailed('):]
        discovery = discovery[:discovery.index('static function hxcStageAssetReferences(')]
        self.assertIn('PsychFamilyModChain.resolve(candidate.root, candidate.engine, chainBatch)', discovery)


if __name__ == '__main__':
    unittest.main()
