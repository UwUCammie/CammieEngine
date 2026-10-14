"""Nightmare Vision stage object classes, the StageData view and FlxRuntimeShader in the script preset."""
import subprocess
import tempfile
import unittest

from base_helper_fixtures import extract_block
from haxe_test_support import HAXE_COMMAND
from haxe_test_support import FixturePath as Path
import test_nv_sprite_integration as sprite_support
from test_nv_sprite_integration import sprite_integration_files

ROOT = Path(__file__).resolve().parents[2]


class NightmareVisionStageObjectsTest(unittest.TestCase):
    def test_stage_objects_construct_from_their_owner_and_alternate_dances(self):
        files = sprite_integration_files()
        files['Main.hx'] = r'''
class Main {
 static function ok(value:Bool,message:String) {if(!value)throw message;}
 static function main() {
  NightmareVisionSpriteRegistry.enterSession('stage');
  var paths=new NightmareVisionPaths('stage','selected');var other=new NightmareVisionPaths('other','other');
  var owner=NightmareVisionSpriteRegistry.setup(paths);
  var interp=new NightmareVisionScriptInterp({});interp.sourceSpriteOwner=owner;
  NightmareVisionStageObjectBindings.install(interp,paths,owner);
  NightmareVisionSpriteRegistry.setup(other);
  var parser=new NightmareVisionScriptParser();
  interp.execute(parser.parseString("import funkin.objects.stageobjects.BackgroundGirls; girls=new BackgroundGirls(-300,400); first=girls.animation.curAnim.name; girls.dance(); second=girls.animation.curAnim.name; girls.dance(); third=girls.animation.curAnim.name; dancer=new BackgroundDancer(5,6); dancer.dance(); danced=dancer.animation.curAnim.name;"));
  var girls:NightmareVisionBackgroundGirls=cast interp.variables.get('girls');
  ok(Std.isOfType(girls,NightmareVisionFlxSprite)&&girls.x==-300&&girls.y==400,'qualified import builds the owner sprite at the source position');
  ok(paths.calls.join('|')=='selected:atlas:backgrounds/weeb/bgFreaks|selected:atlas:backgrounds/limo/limoDancer'&&other.calls.length==0,'default atlases load from the constructing owner');
  ok(interp.variables.get('first')=='danceLeft','the constructor ends on danceLeft as the source does');
  ok(interp.variables.get('second')=='danceLeft'&&interp.variables.get('third')=='danceRight','dance alternates after the constructor dance');
  ok(interp.variables.get('danced')=='danceRight','the dancer starts left and its first dance goes right');
  ok(girls.animation.exists('danceLeft')&&girls.animation.exists('danceRight'),'both dance halves are defined');
  girls.swapDanceType();
  ok(girls.animation.curAnim.name=='danceLeft','swapping the dance type redefines and dances again');
  owner.release();var rejected=false;
  try interp.execute(parser.parseString("new BackgroundGirls(0,0);")) catch (_:Dynamic) rejected=true;
  ok(rejected&&paths.calls.length==2,'a released owner cannot construct or load');
  var missing=false;try new NightmareVisionBackgroundDancer(0,0,null) catch (_:Dynamic) missing=true;
  ok(missing,'construction without owner paths is refused');
 }
}
'''
        # Same interpreter and no-compilation hxcpp run as the sprite integration tests.
        sprite_support.NVSpriteIntegrationTest.run_haxe(self, files)

    def test_stage_data_view_reads_owner_stages_and_shares_the_object_rule(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = Path(directory)
            owner = work / 'imported_mods/owner'
            (owner / 'data/stages/demo').mkdir(parents=True)
            (owner / 'data/stages/demo/data.json').write_text('{"origin":"directory","defaultZoom":0.9}', encoding='utf-8')
            (owner / 'stages').mkdir(parents=True)
            (owner / 'stages/flat.json').write_text('{"origin":"legacy-flat"}', encoding='utf-8')
            sibling = work / 'imported_mods/other/data/stages'
            sibling.mkdir(parents=True)
            (sibling / 'sibling.json').write_text('{"origin":"sibling"}', encoding='utf-8')
            (work / 'CoolUtil.hx').write_text('class CoolUtil {\n public static function parseJson(value:String):Dynamic return haxe.Json.parse(value);\n}\n', encoding='utf-8')
            (work / 'Main.hx').write_text(r'''
class Main {
 static function ok(value:Bool,message:String) {if(!value)throw message;}
 static function main() {
  var owner=Sys.args()[0];
  var asked:Array<String>=[];
  var view=new NightmareVisionStageDataView(owner,function(name) {asked.push(name);return name=='tiledsprite'?Main:null;});
  ok(view.getStageFile('demo').origin=='directory','data/stages directory form');
  ok(view.getStageFile('flat').origin=='legacy-flat','stages flat fallback');
  ok(view.getStageFile('../other/data/stages/sibling')==null&&view.getStageFile('sibling')==null,'other owners stay out of reach');
  ok(StringTools.endsWith(view.getStageFromDir('data/stages','demo'),'data/stages/demo/data.json'),'getStageFromDir returns the owner file');
  ok(view.getStageFromDir('data/stages','absent')==null,'a missing stage has no path');
  ok(view.getTemplateStageFile().defaultZoom==0.8,'source template');
  ok(view.resolveObjectInstance('tiledsprite')==Main&&view.resolveObjectInstance('other')==null&&asked.join(',')=='tiledsprite,other','object rule comes from the shared resolver');
  ok(view.resolveObjectInstance(null)==null&&new NightmareVisionStageDataView(owner).resolveObjectInstance('x')==null,'no name or no resolver gives null');
 }
}
''', encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(work), '--run', 'Main', str(owner)],
                                    cwd=work, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_preset_binds_stage_objects_stage_data_and_runtime_shader(self):
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        preset = extract_block(play, 'public static function seedNightmareVisionCommon(')
        self.assertIn('NightmareVisionStageObjectBindings.install(interp, paths, spriteOwner);', preset)
        self.assertIn("interp.variables.set('FlxRuntimeShader', NightmareVisionRuntimeShader);", preset)
        self.assertIn("bindStaticField(NightmareVisionRuntimeShader, 'fromPath'", preset)
        self.assertIn('NightmareVisionShaderFactory.fromPath(shaderOwner, fragFile, vertFile)', preset)
        self.assertIn('new NightmareVisionStageDataView(paths.root, NightmareVisionStage.resolveBuiltinObject)', preset)
        self.assertIn("interp.bindImport('funkin.data.StageData', stageData);", preset)
        stage = (ROOT / 'source/NightmareVisionStage.hx').read_text(encoding='utf-8')
        self.assertIn('public static function resolveBuiltinObject(name:String)', stage)


if __name__ == '__main__':
    unittest.main()
