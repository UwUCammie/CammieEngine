from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest
import json

ROOT = Path(__file__).resolve().parents[2]

class GuyAssetsTest(unittest.TestCase):
    def test_manifest_shader_roots_are_isolated_and_preferred(self):
        source = (ROOT / 'source/ShaderPaths.hx').read_text()
        with tempfile.TemporaryDirectory() as folder:
            fixture_root = Path(folder)
            for namespace, marker in [('alpha', 'alpha'), ('beta', 'beta')]:
                shader = fixture_root / 'assets' / 'imported_mods' / namespace / 'shaders'
                shader.mkdir(parents=True)
                (shader / 'vignette.frag').write_text(marker, newline='\n')
            native = fixture_root / 'assets' / 'shaders'
            native.mkdir(parents=True)
            (native / 'legacy.frag').write_text('native', newline='\n')
            fixture = f'''import haxe.io.Path;
class FNFAssets {{
 static var root:String = {json.dumps(str(fixture_root))};
 public static function exists(path:String):Bool return sys.FileSystem.exists(Path.join([root, path]));
}}
class ShaderNamespaceTest {{
 static function main() {{
  var alpha = ShaderPaths.resolve('vignette', ['assets/imported_mods/alpha', 'assets/imported_mods/beta']);
  if (alpha != 'assets/imported_mods/alpha/shaders/vignette.frag') throw 'first manifest root was not preferred';
  var beta = ShaderPaths.resolve('vignette', ['assets/imported_mods/beta']);
  if (beta != 'assets/imported_mods/beta/shaders/vignette.frag') throw 'second manifest root leaked';
  if (ShaderPaths.resolve('vignette', ['/tmp/untrusted-root']) != null) throw 'unsafe root escaped';
  if (ShaderPaths.resolve('legacy') != 'assets/shaders/legacy.frag') throw 'native fallback changed';
 }}
}}
'''
            path = Path(folder)
            (path / 'ShaderNamespaceTest.hx').write_text(fixture, newline='\n')
            (path / 'ShaderPaths.hx').write_text(source.replace('FNFAssets.', 'ShaderNamespaceTest.FNFAssets.'), newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(path), '-main', 'ShaderNamespaceTest', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_json_extensions_and_legacy_shader_paths(self):
        fixtures = [
            ROOT / 'assets/data/guy/credits.json',
            ROOT / 'assets/images/custom_ui/ui_packs/ourple/credits.json',
            ROOT / 'assets/shaders/mosaic.frag',
            ROOT / 'assets/shaders/tixbro/radialBlur.frag',
        ]
        if not all(path.is_file() for path in fixtures):
            self.skipTest('mounted Guy asset fixtures unavailable: ' + ', '.join(str(path) for path in fixtures))
        source = (ROOT / 'source/FNFAssets.hx').read_text()
        start = source.index('\tstatic public function getJson(')
        method = source[start:source.index('\n\t}', start) + 3]
        fixture = '''import haxe.io.Path;
class CoolUtil {public static var JSON_EXT=['json','jsonc'];}
class AssetType {public static var TEXT=0;}
class FNFAssets {
 public static function exists(p:String)return sys.FileSystem.exists(p);
 public static function getText(p:String)return sys.io.File.getContent(p);
 static function getAmbigAsset(paths:Array<String>,exts:Array<String>,type:Int):String {
  for(p in paths)for(e in exts)if(exists(p+'.'+e))return getText(p+'.'+e);return null;
 }
''' + method + '''
}
class GuyAssetsTest {
 static function main(){
  for(path in ['assets/data/guy/credits','assets/images/custom_ui/ui_packs/ourple/credits']) {
   var a=FNFAssets.getJson(path);var b=FNFAssets.getJson(path+'.json');
   if(a==null||a!=b)throw 'Explicit JSON filename failed';
   var parsed=haxe.Json.parse(b);if(parsed.music==null||parsed.charter==null)throw 'Invalid credits';
  }
  for(name in ['mosaic','mosaic.frag','ourple/mosaic','assets/shaders/mosaic.frag'])
   if(ShaderPaths.resolve(name)!='assets/shaders/mosaic.frag')throw 'Shader path failed: '+name;
  if(ShaderPaths.resolve('tixbro/radialBlur')!='assets/shaders/tixbro/radialBlur.frag')throw 'Nested shader changed';
  if(ShaderPaths.resolve('nonexistent-test-shader')!=null)throw 'Missing shader must stay missing';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            (p/'GuyAssetsTest.hx').write_text(fixture, newline='\n')
            (p/'ShaderPaths.hx').write_text((ROOT/'source/ShaderPaths.hx').read_text().replace('FNFAssets.', 'GuyAssetsTest.FNFAssets.'), newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-main','GuyAssetsTest','--interp'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_ourple_layout_positions_both_icons(self):
        fixture_asset = ROOT / 'assets/images/custom_ui/ui_layouts/ourple.hscript'
        if not fixture_asset.is_file():
            self.skipTest(f'mounted Ourple layout fixture unavailable: {fixture_asset}')
        fixture=(ROOT/'tools/tests/fixtures/PostalLayoutTest.hx').read_text()
        fixture=fixture.replace('public var alpha:Float=1;', 'public var angle:Float=0;public var alpha:Float=1;')
        fixture=fixture.replace('public function new(?x:Float,?y:Float,?w:Float,?h:Dynamic,?z:Dynamic){}', 'public function new(?x:Float,?y:Float,?w:Float,?h:Dynamic,?z:Dynamic){this.x=x==null?0:x;this.y=y==null?0:y;}')
        fixture=fixture.replace('state={health:1.0,iconOverride:false}', 'state={health:1.0,iconOverride:false,healthBar:new UISprite(),healthBarBG:new UISprite(),dad:{enemyColor:0xff00ff}}')
        fixture=fixture.replace('w:Int,h:Int,min:', 'w:Float,h:Float,min:')
        fixture=fixture.replace("'Std'=>Std", "'FNFAssets'=>{exists:function(p:String)return FileSystem.exists(p),getJson:function(p:String)return sys.io.File.getContent(p)},'CoolUtil'=>{parseJson:function(s:String)return haxe.Json.parse(s)},'StringTools'=>StringTools,'Std'=>Std")
        fixture=fixture.replace("song:'postal'", "song:'guy'").replace("'curSong'=>'postal'", "'curSong'=>'guy'")
        fixture=fixture.replace('ui_layouts/postal.hscript','ui_layouts/ourple.hscript').replace("['postal']", "['guy']")
        fixture=fixture.replace("  Reflect.callMethod(null,i.variables.get('beatHit'),[1]);", '')
        fixture=fixture.replace("  if(!state.iconOverride", "  var p1:UISprite=vars.get('iconP1');var p2:UISprite=vars.get('iconP2');\n  if(p1.x!=855||p2.x!=275||p1.y!=575||p2.y!=575)throw 'Incorrect icon positions';\n  if(!state.iconOverride")
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'PostalLayoutTest.hx').write_text(fixture, newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-main','PostalLayoutTest','--interp'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_endohead_switch_only_shows_active_opponent(self):
        fixture_asset = ROOT / 'assets/data/guy/modchart.hscript'
        if not fixture_asset.is_file():
            self.skipTest(f'mounted Guy modchart fixture unavailable: {fixture_asset}')
        fixture='''class Test {
 static function main(){
  var interp=new hscript.Interp();var dad:Dynamic={visible:true};var endo:Dynamic={visible:false};var state:Dynamic={dad:dad};
  interp.variables.set('dad',dad);interp.variables.set('endoHead',endo);interp.variables.set('currentPlayState',state);
  interp.execute(new hscript.Parser().parseString(sys.io.File.getContent('assets/data/guy/modchart.hscript')));
  Reflect.callMethod(null,interp.variables.get('stepHit'),[1472]);
  if(dad.visible||!endo.visible||state.dad!=endo)throw 'Old opponent covers EndoHead';
  Reflect.callMethod(null,interp.variables.get('stepHit'),[1536]);
  if(!dad.visible||endo.visible||state.dad!=dad)throw 'Opponent did not restore';
 }
}'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'Test.hx').write_text(fixture, newline='\n')
            p=subprocess.run([*HAXE_COMMAND,'-cp',folder,'-cp',str(ROOT/'.haxelib/hscript/2,5,0'),'-main','Test','--interp'],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
