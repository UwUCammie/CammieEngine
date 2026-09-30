"""Psych skin metadata survives native difficulty selection without losing resets."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_difficulty_visual_fallback import extract_method

ROOT = Path(__file__).resolve().parents[2]


class PsychSkinMetadataTest(unittest.TestCase):
    def test_source_skin_values_and_difficulty_precedence(self):
        source = (ROOT / 'source/Song.hx').read_text()
        fields = source[source.index('\tstatic var gameplayFields'):source.index('\tstatic var registryCache')]
        methods = '\n'.join(extract_method(source, marker) for marker in (
            '\tstatic function chartHasValue(',
            '\tstatic function isValidVisualValue(',
            '\tstatic function visualValueIsValid(',
            '\tpublic static function resolveChartData(',
        ))
        fixture = 'using StringTools;\nclass SkinMetadata {\n' + fields + methods + '''
 static function validCharacter(v:String):Bool return true;
 static function validStage(v:String):Bool return true;
 static function validUIType(v:String):Bool return true;
 static function validCutscene(v:String):Bool return true;
 static function validLayout(v:String):Bool return true;
 static function check(v:Bool, message:String):Void { if (!v) throw message; }
 static function main() {
  var inherited = resolveChartData({}, [{arrowSkin:'other',disableNoteRGB:false}],
   {arrowSkin:'base',splashSkin:'baseSplash',disableNoteRGB:true});
  check(inherited.arrowSkin == 'base' && inherited.splashSkin == 'baseSplash'
   && inherited.disableNoteRGB == true, 'default skin inheritance');
  var explicit = resolveChartData({arrowSkin:'selected',splashSkin:'selectedSplash',disableNoteRGB:false}, [],
   {arrowSkin:'base',splashSkin:'baseSplash',disableNoteRGB:true});
  check(explicit.arrowSkin == 'selected' && explicit.splashSkin == 'selectedSplash'
   && explicit.disableNoteRGB == false, 'selected difficulty must win including false');
  var reset = resolveChartData({arrowSkin:'',splashSkin:''}, [{arrowSkin:'sibling'}],
   {arrowSkin:'base',splashSkin:'baseSplash'});
  check(reset.arrowSkin == '' && reset.splashSkin == '', 'empty source skin resets must win');
  var sparse = resolveChartData({}, [{arrowSkin:'fallback',disableNoteRGB:false}]);
  check(sparse.arrowSkin == 'fallback' && sparse.disableNoteRGB == false, 'missing skin inheritance');
  var missing = resolveChartData({}, []);
  check(!Reflect.hasField(missing,'arrowSkin') && !Reflect.hasField(missing,'disableNoteRGB'),
   'native charts must not acquire source settings');
  check(!chartHasValue({arrowSkin:null},'arrowSkin') && !chartHasValue({arrowSkin:3},'arrowSkin'),
   'null and invalid IDs are not authored resets');
  check(!isValidVisualValue('disableNoteRGB','false'), 'string boolean is not valid');
  check(!chartHasValue({stage:''},'stage'), 'empty native visual semantics unchanged');
  var validity = new Map<String,Bool>();
  validity.set('arrowSkin=', true); validity.set('disableNoteRGB=false',true);
  var withMap = resolveChartData({arrowSkin:'',disableNoteRGB:false}, [], {}, validity);
  check(withMap.arrowSkin == '' && withMap.disableNoteRGB == false, 'prevalidated values lost');
 }
}
'''
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp', prefix='psych-skin-metadata-') as folder:
            (Path(folder) / 'SkinMetadata.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', folder,
                                     '-main', 'SkinMetadata', '--interp'], cwd=ROOT,
                                    capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
