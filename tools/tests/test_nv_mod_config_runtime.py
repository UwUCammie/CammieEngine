"""Actual native config adapter and Paths, with explicit window/RPC SDK fakes."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_package_family_paths import asset_stubs

ROOT = Path(__file__).resolve().parents[2]


class NvModConfigRuntimeTest(unittest.TestCase):
    def test_selected_assets_options_native_services_and_release(self):
        stubs = asset_stubs()
        stubs['flixel/FlxG.hx'] = stubs['flixel/FlxG.hx'].replace('class FlxG {', '''class FlxG {
 public static var stage:Dynamic={window:{title:'Host title',setIcon:function(image:Dynamic):Void Main.icons.push(image)}};
 public static var save:Dynamic={data:{nativeSentinel:42},flush:function():Void {if(Main.failSave) throw 'flush failure';}};
''')
        stubs['lime/graphics/Image.hx'] = '''package lime.graphics;
class Image {public var bytes:haxe.io.Bytes;public function new(b:haxe.io.Bytes){bytes=b;}
 public static function fromBytes(b:haxe.io.Bytes):Image return new Image(b);}
'''
        stubs['Discord.hx'] = '''class DiscordClient {
 public static var id:String='host-rpc'; public static var requested:Array<String>=[];
 public static function getClientId():String return id;
 public static function setClientId(value:String):Void {id=value;requested.push(value);}
}'''
        stubs['lime/app/Application.hx'] = '''package lime.app;
class Application {public static var current:Dynamic={meta:{get:function(key:String):String return 'Source title'}};}
'''
        main = r'''
import Discord.DiscordClient;
class Main {
 public static var icons:Array<Dynamic>=[];
 public static var failSave:Bool=false;
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main() {
  var a='assets/imported_mods/alpha'; var b='assets/imported_mods/beta';
  var family=new NightmareVisionModFamilySession('alpha',a,[{directory:'alpha',root:a},{directory:'beta',root:b}]);
  var mods=new NightmareVisionModsContext(a,'alpha',family);
  var paths=new NightmareVisionPaths(a,null,null,'alpha'); paths.bindModFamily(mods);
  var runtime=new NightmareVisionModConfigRuntime(mods,paths);
  mods.applyModConfig();
  check(flixel.FlxG.stage.window.title=='Alpha title','native title applied');
  check(paths.DEFAULT_FONT==a+'/fonts/custom.ttf','selected native font applied');
  check(paths.UI_PREFIX=='custom/' && paths.COMBO_PREFIX=='UI/combo/','existing prefix/fallback');
  check(runtime.transitionIn==NightmareVisionModTransition.FADE && runtime.transitionOut==runtime.transitionIn,'source transition variables');
  check(icons[0].bytes.toString()=='alpha icon','native image bytes');
  check(runtime.liveConfig==mods.currentModConfig,'redirect config live identity');
  var sourceOptions=mods.optionSession;
  sourceOptions.addForMod('alpha','score-display','bool',true);
  sourceOptions.setValue('score-display',false);
  var writesBefore=DiscordClient.requested.length;
  mods.currentModDirectory='beta';
  check(flixel.FlxG.stage.window.title=='Alpha title' && DiscordClient.requested.length==writesBefore,'assignment does not apply config or transition');
  mods.applyModConfig('alpha');
  check(runtime.selectedRoot==b && sourceOptions.currentMod=='beta','explicit config lookup keeps selected option/asset identity');
  check(icons[1].bytes.toString()=='beta icon','explicit lookup uses selected source Paths');
  check(paths.DEFAULT_FONT==b+'/fonts/vcr.ttf','missing configured font uses selected fallback');
  check(sourceOptions.get('score-display')==null,'options isolated by selected owner');
  sourceOptions.addForMod('beta','score-display','bool',true);
  mods.currentModDirectory='alpha'; mods.applyModConfig();
  check(sourceOptions.getValue('score-display')==false,'original owner value restored');
  var laterPaths=new NightmareVisionPaths(a,null,null,'alpha'); laterPaths.bindModFamily(mods);
  runtime.attachPaths(laterPaths);
  check(laterPaths.DEFAULT_FONT==paths.DEFAULT_FONT && laterPaths.UI_PREFIX==paths.UI_PREFIX,'next song retains source static configuration');
  mods.applyModConfig();
  check(laterPaths.DEFAULT_FONT==paths.DEFAULT_FONT && laterPaths.RATINGS_PREFIX==paths.RATINGS_PREFIX,'persistent plugin and current song share later assignments');
  failSave=true; var rejected=false;
  try runtime.release() catch(error:Dynamic) rejected=true;
  check(rejected && NightmareVisionModConfigRuntime.active==null,'teardown reports flush failure after releasing native ownership');
  check(flixel.FlxG.stage.window.title=='Host title' && DiscordClient.id=='host-rpc','native title/RPC restored');
  check(flixel.FlxG.save.data.nativeSentinel==42,'native settings untouched');
  check(icons[icons.length-1].bytes.toString()=='native icon','native branding restored');
  rejected=false; try sourceOptions.getValue('score-display') catch(error:Dynamic) rejected=true;
  check(rejected,'failed flush still retires source option view');
  mods.release();
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            folder = FixturePath(temp)
            for name, content in {**stubs, 'Main.hx': main}.items():
                target = folder / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding='utf-8')
            for name in ['alpha', 'beta']:
                base = folder / 'assets/imported_mods' / name
                for relative in ['images/branding/icon', 'images/custom', 'fonts', '__nmv_core/images', '__nmv_core/fonts']:
                    (base / relative).mkdir(parents=True, exist_ok=True)
                (base / 'images/branding/icon/icon64.png').write_bytes((name + ' icon').encode())
                (base / 'fonts/vcr.ttf').write_bytes(b'font')
            (folder / 'assets/imported_mods/alpha/fonts/custom.ttf').write_bytes(b'font')
            (folder / 'assets/imported_mods/alpha/meta.json').write_text('''{"name":"Alpha","windowTitle":"Alpha title","defaultFont":"custom.ttf","uiPrefix":"custom/","comboPrefix":"missing","defaultTransition":"FaDe"}''')
            (folder / 'assets/imported_mods/beta/meta.json').write_text('''{"name":"Beta"}''')
            (folder / 'native-icon.bin').write_bytes(b'native icon')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(folder),
                                     '-resource', str(folder / 'native-icon.bin') + '@cammie-native-window-icon',
                                     '--interp', '-main', 'Main'], cwd=temp, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
