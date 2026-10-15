"""A chart in a game's content package searches that package before the base assets."""
from haxe_test_support import HAXE_COMMAND

from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from test_import_workflow import extract_method


ROOT = Path(__file__).resolve().parents[2]


class ImportWorkflowPackageScopeTest(unittest.TestCase):
    def test_content_package_chart_scopes_package_then_base_assets(self):
        source = (ROOT / "source/ImportWorkflow.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "static function normalized", "static function pathKey", "static function pathWithin",
            "static function uniquePush(", "static function chartPackageRoot",
            "static function dependencyRootsForChart"))
        fixture = f'''import haxe.io.Path;
import sys.FileSystem;
using StringTools;

typedef ImportRoot = {{root:String, contentRoot:String, data:String}};

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    return Path.normalize(StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/'));
  }}
}}

class ImportWorkflow {{
{methods}
  static function check(value:Bool, message:String) if (!value) throw message;
  static function main() {{
    var game = Sys.args()[0] + '/game';
    var assets = game + '/assets';
    var pack = game + '/content/Pack';
    for (path in [assets + '/data', pack + '/data/song', pack + '/stages', game + '/data/loose',
        pack + '/songs/other/data'])
      FileSystem.createDirectory(path);
    var descriptors:Array<ImportRoot> = [{{root:game, contentRoot:assets, data:assets + '/data'}}];
    var packScopes = dependencyRootsForChart(descriptors, pack + '/data/song/song.json');
    check(packScopes.length == 2, 'package chart scopes: ' + packScopes.join(','));
    check(pathKey(packScopes[0]) == pathKey(pack), 'package must be searched first: ' + packScopes.join(','));
    check(pathKey(packScopes[1]) == pathKey(assets), 'base assets stay a scope: ' + packScopes.join(','));
    // Charts kept below the song folder still scope the whole package, never
    // the song folder (whose charts would then be read as stage definitions).
    var nestedScopes = dependencyRootsForChart(descriptors, pack + '/songs/other/data/normal.json');
    check(nestedScopes.length == 2 && pathKey(nestedScopes[0]) == pathKey(pack),
      'nested chart package scope: ' + nestedScopes.join(','));
    var baseScopes = dependencyRootsForChart(descriptors, assets + '/data/song/song.json');
    check(baseScopes.length == 1 && pathKey(baseScopes[0]) == pathKey(assets),
      'a base-assets chart gains no extra scope: ' + baseScopes.join(','));
    // A data folder directly under the game root is not a package of its own.
    var looseScopes = dependencyRootsForChart(descriptors, game + '/data/loose/song.json');
    check(looseScopes.length == 1 && pathKey(looseScopes[0]) == pathKey(assets),
      'the game root itself is never a package scope: ' + looseScopes.join(','));
    check(pathKey(chartPackageRoot(pack + '/charts/song.json', game)) == pathKey(pack),
      'any chart inside a content package belongs to it');
    check(chartPackageRoot(game + '/elsewhere/data/song/song.json', game) == null,
      'a chart outside a content folder has no package root');
  }}
}}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            (Path(folder) / "ImportWorkflow.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", folder, "--run", "ImportWorkflow", folder],
                                    cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
