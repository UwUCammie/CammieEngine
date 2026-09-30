"""Execute the owner-scoped Nightmare Vision StageData adapter."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionStageDataTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=ROOT / 'tmp')
        self.addCleanup(self.scratch.cleanup)
        self.work = Path(self.scratch.name)
        self.owner = self.work / 'game/assets/imported_mods/nmv-owner'
        self.owner.mkdir(parents=True)
        self.sibling = self.work / 'game/assets/imported_mods/other-owner'
        self.sibling.mkdir(parents=True)
        (self.work / 'CoolUtil.hx').write_text('''package;
class CoolUtil {
 public static function parseJson(value:String):Dynamic return tjson.TJSON.parse(value);
}
''')
        (self.work / 'Main.hx').write_text('''package;
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function same(actual:Dynamic, expected:Dynamic, message:String):Void
  check(haxe.Json.stringify(actual) == haxe.Json.stringify(expected), message + ': ' + haxe.Json.stringify(actual));
 static function main():Void {
  var args = Sys.args();
  var owner = args[0];
  var sibling = args[1];
  var stage = NightmareVisionStageData.load(owner, 'demo');
  check(stage != null && stage.origin == 'primary-directory', 'data/stages directory file precedence');
  check(stage.defaultZoom == 0.9 && stage.hide_girlfriend == true && stage.camera_speed == 1.25,
   'authored stage scalar fields');
  same(stage.boyfriend, [770,100], 'boyfriend positions');
  same(stage.girlfriend, [400,130], 'girlfriend positions');
  same(stage.opponent, [100,100], 'opponent positions');
  same(stage.camera_boyfriend, [1.5,-2], 'boyfriend camera offset');
  same(stage.camera_opponent, [3,-4], 'opponent camera offset');
  same(stage.camera_girlfriend, [5,-6], 'girlfriend camera offset');
  check(NightmareVisionStageData.getStageFromDir(owner, 'data/stages', 'demo')
   == owner + '/data/stages/demo/data.json', 'source getStageFromDir first candidate');
  check(NightmareVisionStageData.getStageFile(owner, 'flat').origin == 'primary-flat-only',
   'data/stages flat JSON fallback');
  check(NightmareVisionStageData.getStageFile(owner, 'legacy').origin == 'legacy-directory',
   'stages directory fallback');
  check(NightmareVisionStageData.getStageFile(owner, 'legacy-flat').origin == 'legacy-flat-only',
   'stages flat JSON fallback');
  check(NightmareVisionStageData.getStageFile(owner, 'sibling-only') == null,
   'lookup must not escape the selected owner');
  check(NightmareVisionStageData.getStageFile(owner, 'Case') != null
   && NightmareVisionStageData.getStageFile(owner, 'case') == null, 'stage path spelling is exact');
  check(NightmareVisionStageData.getStageFile(owner, '../other-owner/sibling-only') == null,
   'unsafe stage traversal is rejected');
  check(NightmareVisionStageData.normalizeStageId('  nested/demo  ') == 'nested/demo'
   && NightmareVisionStageData.normalizeStageId('../demo') == '', 'stage ID normalization');
  check(NightmareVisionStageData.getStageFile(owner, 'core-first').origin == 'core-directory',
   'core directory candidate precedes owner flat candidate');
  check(NightmareVisionStageData.getStageFile(owner, 'core-only').origin == 'core-only',
   'installed core stage fallback');
  var template = NightmareVisionStageData.getTemplateStageFile();
  check(template.defaultZoom == 0.8 && template.hide_girlfriend == false && template.camera_speed == 1,
   'source StageData template scalars');
  same(template.boyfriend, [500,100], 'template boyfriend position');
  same(template.girlfriend, [0,100], 'template girlfriend position');
  same(template.opponent, [-500,100], 'template opponent position');
  same(template.camera_boyfriend, [0,0], 'template boyfriend camera offset');
  same(template.camera_opponent, [0,0], 'template opponent camera offset');
  same(template.camera_girlfriend, [0,0], 'template girlfriend camera offset');
  check(template.stageObjects == null && template.dadZIndex == null,
   'template leaves optional fields unset like source');
  Sys.println('nightmare-vision-stage-data-ok');
 }
}
''')

    def write(self, root, relative, value):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        return path

    def test_stage_data_lookup_template_and_owner_boundary(self):
        self.write(self.owner, 'data/stages/demo/data.json', '''{
 // StageData checks this directory-form file before flat JSON.
 origin: "primary-directory",
 defaultZoom: 0.9,
 boyfriend: [770, 100],
 girlfriend: [400, 130],
 opponent: [100, 100],
 hide_girlfriend: true,
 camera_boyfriend: [1.5, -2],
 camera_opponent: [3, -4],
 camera_girlfriend: [5, -6],
 camera_speed: 1.25,
}''')
        self.write(self.owner, 'data/stages/demo.json', '{"origin":"primary-flat"}')
        self.write(self.owner, 'stages/demo/data.json', '{"origin":"legacy-directory"}')
        self.write(self.owner, 'stages/demo.json', '{"origin":"legacy-flat"}')
        self.write(self.owner, 'data/stages/flat.json', '{"origin":"primary-flat-only"}')
        self.write(self.owner, 'stages/legacy/data.json', '{"origin":"legacy-directory"}')
        self.write(self.owner, 'stages/legacy-flat.json', '{"origin":"legacy-flat-only"}')
        self.write(self.owner, 'data/stages/Case/data.json', '{"origin":"exact-case"}')
        self.write(self.sibling, 'data/stages/sibling-only/data.json', '{"origin":"sibling"}')

        self.write(self.owner, '__nmv_core/data/stages/core-first/data.json', '{"origin":"core-directory"}')
        self.write(self.owner, 'data/stages/core-first.json', '{"origin":"owner-flat"}')
        self.write(self.owner, '__nmv_core/stages/core-only.json', '{"origin":"core-only"}')

        result = subprocess.run(
            [str(ROOT / '.tools/haxe/haxe'), '-cp', str(ROOT / 'source'), '-cp', str(self.work),
             '-cp', str(ROOT / '.haxelib/tjson/1,4,0'), '--run', 'Main', str(self.owner), str(self.sibling)],
            cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('nightmare-vision-stage-data-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
